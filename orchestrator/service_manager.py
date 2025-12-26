# =============================================================================
# CLOPUS v3 Service Manager
# =============================================================================
"""
Manages on-demand services (Tier 2).
Starts/stops database, messaging, and other services as needed.
"""

import asyncio
import subprocess
from typing import Any, Dict, List, Optional, Set
import logging

logger = logging.getLogger("clopus.service_manager")


class ServiceManager:
    """Manage on-demand services."""

    # Available services and their Docker Compose profiles
    SERVICES = {
        "mongodb": {
            "profile": "mongodb",
            "port": 27017,
            "description": "MongoDB document database"
        },
        "mysql": {
            "profile": "mysql",
            "port": 3306,
            "description": "MySQL relational database"
        },
        "elasticsearch": {
            "profile": "elasticsearch",
            "port": 9200,
            "description": "Elasticsearch search engine"
        },
        "rabbitmq": {
            "profile": "rabbitmq",
            "port": 5672,
            "description": "RabbitMQ message broker"
        },
        "kafka": {
            "profile": "kafka",
            "port": 9092,
            "description": "Apache Kafka streaming"
        },
        "wordpress": {
            "profile": "wordpress",
            "port": 8082,
            "description": "WordPress CMS",
            "depends": ["mysql"]
        },
        "keycloak": {
            "profile": "keycloak",
            "port": 8081,
            "description": "Keycloak identity management"
        }
    }

    def __init__(self, config):
        self.config = config
        self._active_services: Set[str] = set()
        self._compose_file = "/app/docker-compose.yml"

    async def start_service(self, service_name: str) -> bool:
        """Start an on-demand service."""
        if service_name not in self.SERVICES:
            logger.error(f"Unknown service: {service_name}")
            return False

        if service_name in self._active_services:
            logger.info(f"Service {service_name} is already running")
            return True

        service_info = self.SERVICES[service_name]

        # Start dependencies first
        for dep in service_info.get("depends", []):
            if dep not in self._active_services:
                await self.start_service(dep)

        try:
            # Start service using docker compose with profile
            await self._run_compose([
                "--profile", service_info["profile"],
                "up", "-d", service_name
            ])

            self._active_services.add(service_name)
            logger.info(f"Started service: {service_name}")

            # Wait for service to be ready
            await self._wait_for_service(service_name, service_info["port"])

            return True

        except Exception as e:
            logger.error(f"Error starting service {service_name}: {e}")
            return False

    async def stop_service(self, service_name: str) -> bool:
        """Stop an on-demand service."""
        if service_name not in self._active_services:
            logger.info(f"Service {service_name} is not running")
            return True

        try:
            # Check if other services depend on this one
            dependents = [
                name for name, info in self.SERVICES.items()
                if service_name in info.get("depends", [])
                and name in self._active_services
            ]

            if dependents:
                logger.warning(
                    f"Cannot stop {service_name}: required by {dependents}"
                )
                return False

            # Stop service
            await self._run_compose(["stop", service_name])

            self._active_services.remove(service_name)
            logger.info(f"Stopped service: {service_name}")
            return True

        except Exception as e:
            logger.error(f"Error stopping service {service_name}: {e}")
            return False

    async def _run_compose(self, args: List[str]) -> str:
        """Run docker compose command."""
        command = [
            "docker", "compose",
            "-f", self._compose_file
        ] + args

        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise subprocess.CalledProcessError(
                process.returncode,
                command,
                stdout,
                stderr
            )

        return stdout.decode()

    async def _wait_for_service(
        self,
        service_name: str,
        port: int,
        timeout: int = 60
    ) -> bool:
        """Wait for a service to be ready."""
        import socket

        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                sock.close()

                if result == 0:
                    logger.info(f"Service {service_name} is ready on port {port}")
                    return True

            except Exception:
                pass

            await asyncio.sleep(1)

        logger.warning(f"Timeout waiting for {service_name}")
        return False

    async def get_service_status(self, service_name: str) -> Dict:
        """Get status of a service."""
        if service_name not in self.SERVICES:
            return {"error": "Unknown service"}

        service_info = self.SERVICES[service_name]

        return {
            "name": service_name,
            "running": service_name in self._active_services,
            "port": service_info["port"],
            "description": service_info["description"]
        }

    async def get_all_status(self) -> List[Dict]:
        """Get status of all services."""
        return [
            await self.get_service_status(name)
            for name in self.SERVICES
        ]

    async def ensure_services(self, required: List[str]) -> bool:
        """Ensure all required services are running."""
        all_started = True

        for service in required:
            if service not in self._active_services:
                if not await self.start_service(service):
                    all_started = False

        return all_started

    async def detect_required_services(self, project_path: str) -> List[str]:
        """Detect services required by a project."""
        required = []

        # Check for common config files and dependencies
        from pathlib import Path
        path = Path(project_path)

        # MongoDB
        if any(path.rglob("*mongo*")) or "mongoose" in self._read_package_deps(path):
            required.append("mongodb")

        # MySQL
        if any(path.rglob("*mysql*")) or "mysql" in self._read_package_deps(path):
            required.append("mysql")

        # Elasticsearch
        if "elasticsearch" in self._read_package_deps(path):
            required.append("elasticsearch")

        # RabbitMQ
        if "amqplib" in self._read_package_deps(path) or any(path.rglob("*rabbit*")):
            required.append("rabbitmq")

        # Kafka
        if "kafkajs" in self._read_package_deps(path) or "kafka-python" in self._read_requirements(path):
            required.append("kafka")

        return required

    def _read_package_deps(self, path) -> Set[str]:
        """Read package.json dependencies."""
        import json
        package_file = path / "package.json"
        if package_file.exists():
            try:
                data = json.loads(package_file.read_text())
                deps = set(data.get("dependencies", {}).keys())
                deps.update(data.get("devDependencies", {}).keys())
                return deps
            except Exception:
                pass
        return set()

    def _read_requirements(self, path) -> Set[str]:
        """Read Python requirements."""
        requirements_file = path / "requirements.txt"
        if requirements_file.exists():
            try:
                content = requirements_file.read_text()
                return set(
                    line.split("==")[0].split(">=")[0].strip().lower()
                    for line in content.split("\n")
                    if line.strip() and not line.startswith("#")
                )
            except Exception:
                pass
        return set()

    async def cleanup(self) -> None:
        """Stop all running services."""
        for service in list(self._active_services):
            await self.stop_service(service)
