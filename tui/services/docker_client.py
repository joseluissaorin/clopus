"""Docker client for container management"""

import asyncio
import subprocess
import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ContainerInfo:
    name: str
    status: str
    ports: List[str]
    created: str
    image: str


class DockerClient:
    """Docker container management for TUI"""

    def __init__(self):
        self._compose_file = None

    async def get_containers(self, filter_prefix: str = "clopus-") -> List[ContainerInfo]:
        """Get all CLOPUS containers"""
        try:
            result = await asyncio.create_subprocess_exec(
                "docker", "ps", "-a", "--format",
                "{{.Names}}|{{.Status}}|{{.Ports}}|{{.CreatedAt}}|{{.Image}}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await result.communicate()

            containers = []
            for line in stdout.decode().strip().split("\n"):
                if not line or filter_prefix not in line:
                    continue
                parts = line.split("|")
                if len(parts) >= 5:
                    containers.append(ContainerInfo(
                        name=parts[0],
                        status=parts[1],
                        ports=parts[2].split(", ") if parts[2] else [],
                        created=parts[3],
                        image=parts[4],
                    ))
            return containers
        except Exception:
            return []

    async def restart_container(self, name: str) -> bool:
        """Restart a container"""
        try:
            result = await asyncio.create_subprocess_exec(
                "docker", "restart", name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
            return result.returncode == 0
        except Exception:
            return False

    async def stop_container(self, name: str) -> bool:
        """Stop a container"""
        try:
            result = await asyncio.create_subprocess_exec(
                "docker", "stop", name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
            return result.returncode == 0
        except Exception:
            return False

    async def start_container(self, name: str) -> bool:
        """Start a container"""
        try:
            result = await asyncio.create_subprocess_exec(
                "docker", "start", name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
            return result.returncode == 0
        except Exception:
            return False

    async def get_logs(self, name: str, lines: int = 100) -> List[str]:
        """Get container logs"""
        try:
            result = await asyncio.create_subprocess_exec(
                "docker", "logs", name, "--tail", str(lines),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            stdout, _ = await result.communicate()
            return stdout.decode().strip().split("\n")
        except Exception:
            return []

    async def get_orchestrator_logs(self, lines: int = 100,
                                     follow: bool = False) -> List[str]:
        """Get orchestrator logs"""
        return await self.get_logs("clopus-orchestrator", lines)

    async def restart_worker(self, worker_id: int) -> bool:
        """Restart a specific worker"""
        return await self.restart_container(f"clopus-worker-{worker_id}")

    async def stop_worker(self, worker_id: int) -> bool:
        """Stop a specific worker"""
        return await self.stop_container(f"clopus-worker-{worker_id}")

    async def start_worker(self, worker_id: int) -> bool:
        """Start a specific worker"""
        return await self.start_container(f"clopus-worker-{worker_id}")

    async def restart_orchestrator(self) -> bool:
        """Restart the orchestrator"""
        return await self.restart_container("clopus-orchestrator")

    async def get_service_status(self) -> Dict[str, str]:
        """Get status of all core services"""
        services = [
            "clopus-orchestrator",
            "clopus-postgres",
            "clopus-redis",
            "clopus-chromadb",
        ]

        status = {}
        containers = await self.get_containers()
        container_map = {c.name: c for c in containers}

        for service in services:
            if service in container_map:
                c = container_map[service]
                if "Up" in c.status:
                    status[service] = "running"
                elif "Exited" in c.status:
                    status[service] = "stopped"
                else:
                    status[service] = "unknown"
            else:
                status[service] = "not_found"

        return status

    async def compose_up(self) -> bool:
        """Start all services with docker compose"""
        try:
            result = await asyncio.create_subprocess_exec(
                "docker", "compose", "up", "-d",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
            return result.returncode == 0
        except Exception:
            return False

    async def compose_down(self) -> bool:
        """Stop all services with docker compose"""
        try:
            result = await asyncio.create_subprocess_exec(
                "docker", "compose", "down",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
            return result.returncode == 0
        except Exception:
            return False

    async def exec_command(self, container: str, command: List[str]) -> Optional[str]:
        """Execute a command in a container"""
        try:
            result = await asyncio.create_subprocess_exec(
                "docker", "exec", container, *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await result.communicate()
            if result.returncode == 0:
                return stdout.decode()
            return None
        except Exception:
            return None
