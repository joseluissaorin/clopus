# =============================================================================
# CLOPUS v3 Service Manager
# =============================================================================
"""
Manages shared services infrastructure.
Auto-provisions Tier 2 services when projects need them.
"""

import asyncio
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Set

logger = logging.getLogger("clopus.service_manager")


# Service tier definitions
TIER_1_SERVICES = {
    "postgres", "redis", "minio", "chromadb", "browser",
    "traefik", "mailhog", "prometheus", "grafana"
}

TIER_2_SERVICES = {
    "mongodb": {"profile": "mongodb", "port": 27017},
    "mysql": {"profile": "mysql", "port": 3306},
    "elasticsearch": {"profile": "elasticsearch", "port": 9200},
    "rabbitmq": {"profile": "rabbitmq", "port": 5672},
    "kafka": {"profile": "kafka", "port": 9092},
    "wordpress": {"profile": "wordpress", "port": 80},
    "keycloak": {"profile": "keycloak", "port": 8080},
}

# Dependency detection patterns
DEPENDENCY_PATTERNS = {
    "mongodb": ["mongoose", "mongodb", "mongo", "@types/mongodb"],
    "mysql": ["mysql", "mysql2", "sequelize", "typeorm"],
    "elasticsearch": ["elasticsearch", "@elastic/elasticsearch", "elastic"],
    "rabbitmq": ["amqp", "amqplib", "rabbitmq", "bull"],
    "kafka": ["kafka", "kafkajs", "kafka-node"],
    "redis": ["redis", "ioredis", "bull", "bullmq"],
    "postgres": ["pg", "postgres", "postgresql", "prisma", "typeorm", "sequelize"],
}

# External service credential requirements
EXTERNAL_SERVICES = {
    "stripe": ["STRIPE_SECRET_KEY", "STRIPE_PUBLISHABLE_KEY"],
    "twilio": ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN"],
    "resend": ["RESEND_API_KEY"],
    "sendgrid": ["SENDGRID_API_KEY"],
    "aws": ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"],
    "openai": ["OPENAI_API_KEY"],
}


class ServiceManager:
    """Manages shared services infrastructure."""

    def __init__(self, compose_file: str = "/app/docker-compose.yml"):
        self.compose_file = Path(compose_file)
        self.running_services: Set[str] = set()
        self._lock = asyncio.Lock()

    async def analyze_project_needs(
        self,
        project_path: str,
        parsed_objective: Optional[Dict] = None
    ) -> Dict[str, List[str]]:
        """Analyze what services a project needs."""
        path = Path(project_path)
        needs = {
            "databases": [],
            "queues": [],
            "external": [],
            "missing_credentials": [],
        }

        # Check package.json
        pkg_json = path / "package.json"
        if pkg_json.exists():
            try:
                pkg = json.loads(pkg_json.read_text())
                deps = set(pkg.get("dependencies", {}).keys())
                deps.update(pkg.get("devDependencies", {}).keys())

                for service, patterns in DEPENDENCY_PATTERNS.items():
                    if any(p in deps for p in patterns):
                        if service in ("rabbitmq", "kafka"):
                            needs["queues"].append(service)
                        else:
                            needs["databases"].append(service)

            except Exception as e:
                logger.warning(f"Error parsing package.json: {e}")

        # Check requirements.txt
        req_txt = path / "requirements.txt"
        if req_txt.exists():
            try:
                content = req_txt.read_text().lower()
                if "pymongo" in content:
                    needs["databases"].append("mongodb")
                if "psycopg" in content:
                    needs["databases"].append("postgres")
                if "redis" in content:
                    needs["databases"].append("redis")

            except Exception as e:
                logger.warning(f"Error parsing requirements.txt: {e}")

        # Deduplicate
        needs["databases"] = list(set(needs["databases"]))
        needs["queues"] = list(set(needs["queues"]))

        return needs

    async def provision_services(self, needs: Dict[str, List[str]]) -> Dict[str, bool]:
        """Start required services."""
        results = {}

        all_services = needs.get("databases", []) + needs.get("queues", [])

        for service in all_services:
            if service in TIER_1_SERVICES:
                results[service] = True
                continue

            if service in TIER_2_SERVICES:
                success = await self._start_tier2_service(service)
                results[service] = success

        return results

    async def _start_tier2_service(self, service: str) -> bool:
        """Start a Tier 2 service using docker-compose profiles."""
        async with self._lock:
            if service in self.running_services:
                return True

            service_config = TIER_2_SERVICES.get(service)
            if not service_config:
                return False

            profile = service_config["profile"]

            try:
                logger.info(f"Starting Tier 2 service: {service}")

                result = await asyncio.to_thread(
                    subprocess.run,
                    ["docker", "compose", "-f", str(self.compose_file),
                     "--profile", profile, "up", "-d", service],
                    capture_output=True, text=True, timeout=120
                )

                if result.returncode == 0:
                    self.running_services.add(service)
                    logger.info(f"Started {service} successfully")
                    return True

                logger.error(f"Failed to start {service}: {result.stderr}")
                return False

            except Exception as e:
                logger.error(f"Error starting {service}: {e}")
                return False

    async def get_connection_info(self, service: str) -> Optional[Dict]:
        """Get connection info for a service."""
        info = {
            "postgres": {"host": "postgres", "port": 5432, "user": "clopus", "password": "clopus"},
            "redis": {"host": "redis", "port": 6379},
            "mongodb": {"host": "mongodb", "port": 27017, "user": "clopus", "password": "clopus"},
            "mysql": {"host": "mysql", "port": 3306, "user": "root", "password": "clopus"},
            "chromadb": {"host": "chromadb", "port": 8000},
            "minio": {"host": "minio", "port": 9000},
        }
        return info.get(service)
