"""IPC Monitor for worker status"""

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime


@dataclass
class WorkerStatus:
    id: int
    role: str
    status: str  # idle, busy, offline
    model: Optional[str] = None
    task_id: Optional[str] = None
    task_started: Optional[str] = None
    updated_at: Optional[str] = None
    started_at: Optional[str] = None
    session_id: Optional[str] = None


class IPCMonitor:
    """Monitor worker IPC files for real-time status"""

    # Worker roles by ID
    WORKER_ROLES = {
        1: "coder",
        2: "tester",
        3: "reviewer",
        4: "researcher",
        5: "debugger",
        6: "designer",
        7: "heartbeat",
        8: "verificator",
        9: "browser-headless",
        10: "browser-chrome",
        11: "services",
    }

    def __init__(self, ipc_path: Optional[str] = None):
        self.ipc_path = self._find_ipc_path(ipc_path)
        self._use_docker = not self.ipc_path.exists()
        self._callbacks: List[Callable] = []
        self._running = False
        self._worker_count = 11

    def _find_ipc_path(self, ipc_path: Optional[str] = None) -> Path:
        """Find IPC path in various locations"""
        if ipc_path:
            return Path(ipc_path)

        candidates = [
            Path(__file__).parent.parent.parent / "ipc",
            Path.home() / "Dev" / "clopus" / "ipc",
            Path("/app/ipc"),
        ]

        for path in candidates:
            if path.exists():
                return path

        return Path.home() / "Dev" / "clopus" / "ipc"

    def on_update(self, callback: Callable) -> None:
        """Register callback for status updates"""
        self._callbacks.append(callback)

    async def get_worker_status(self, worker_id: int) -> WorkerStatus:
        """Get status for a single worker"""
        status_file = self.ipc_path / "tasks" / str(worker_id) / "status.json"

        try:
            if self._use_docker:
                # Try to read via Docker exec
                result = await asyncio.create_subprocess_exec(
                    "docker", "exec", "clopus-orchestrator", "cat",
                    f"/app/ipc/tasks/{worker_id}/status.json",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await asyncio.wait_for(result.communicate(), timeout=5.0)
                if result.returncode == 0:
                    data = json.loads(stdout.decode())
                    return self._parse_worker_status(worker_id, data)
            else:
                if status_file.exists():
                    data = json.loads(status_file.read_text())
                    return self._parse_worker_status(worker_id, data)

        except asyncio.TimeoutError:
            pass
        except json.JSONDecodeError:
            pass
        except Exception:
            pass

        # Return offline status with default role
        return WorkerStatus(
            id=worker_id,
            role=self.WORKER_ROLES.get(worker_id, "unknown"),
            status="offline"
        )

    def _parse_worker_status(self, worker_id: int, data: Dict[str, Any]) -> WorkerStatus:
        """Parse worker status data"""
        return WorkerStatus(
            id=worker_id,
            role=data.get("role", self.WORKER_ROLES.get(worker_id, "unknown")),
            status=data.get("status", "unknown"),
            model=data.get("model"),
            task_id=data.get("task_id"),
            task_started=data.get("task_started"),
            updated_at=data.get("updated_at"),
            started_at=data.get("started_at"),
            session_id=data.get("last_session"),
        )

    async def get_all_worker_status(self) -> List[WorkerStatus]:
        """Get status for all workers"""
        workers = []
        tasks = [self.get_worker_status(i) for i in range(1, self._worker_count + 1)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results, 1):
            if isinstance(result, WorkerStatus):
                workers.append(result)
            else:
                workers.append(WorkerStatus(
                    id=i,
                    role=self.WORKER_ROLES.get(i, "unknown"),
                    status="offline"
                ))

        return workers

    async def get_worker_logs(self, worker_id: int, lines: int = 50) -> List[str]:
        """Get recent logs from a worker"""
        try:
            result = await asyncio.create_subprocess_exec(
                "docker", "logs", f"clopus-worker-{worker_id}",
                "--tail", str(lines),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            stdout, _ = await asyncio.wait_for(result.communicate(), timeout=10.0)
            if result.returncode == 0:
                return stdout.decode(errors='replace').strip().split("\n")
        except asyncio.TimeoutError:
            return ["Error: Timeout fetching logs"]
        except Exception as e:
            return [f"Error: {str(e)}"]
        return []

    async def get_pending_task(self, worker_id: int) -> Optional[Dict[str, Any]]:
        """Get pending task for a worker if any"""
        pending_file = self.ipc_path / "tasks" / str(worker_id) / "pending.json"

        try:
            if self._use_docker:
                result = await asyncio.create_subprocess_exec(
                    "docker", "exec", "clopus-orchestrator", "cat",
                    f"/app/ipc/tasks/{worker_id}/pending.json",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await asyncio.wait_for(result.communicate(), timeout=5.0)
                if result.returncode == 0:
                    return json.loads(stdout.decode())
            else:
                if pending_file.exists():
                    return json.loads(pending_file.read_text())
        except Exception:
            pass
        return None

    async def start_monitoring(self, interval: float = 1.0) -> None:
        """Start continuous monitoring"""
        self._running = True
        while self._running:
            workers = await self.get_all_worker_status()
            for callback in self._callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(workers)
                    else:
                        callback(workers)
                except Exception:
                    pass
            await asyncio.sleep(interval)

    def stop_monitoring(self) -> None:
        """Stop monitoring"""
        self._running = False

    async def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health metrics"""
        workers = await self.get_all_worker_status()

        busy_count = sum(1 for w in workers if w.status == "busy")
        idle_count = sum(1 for w in workers if w.status == "idle")
        offline_count = sum(1 for w in workers if w.status == "offline")
        online_count = len(workers) - offline_count

        return {
            "total_workers": len(workers),
            "online": online_count,
            "busy": busy_count,
            "idle": idle_count,
            "offline": offline_count,
            "healthy": offline_count == 0,
            "utilization": busy_count / max(1, online_count) if online_count else 0,
        }

    async def get_docker_services_status(self) -> Dict[str, str]:
        """Get status of Docker services"""
        services = {
            "orchestrator": "unknown",
            "postgres": "unknown",
            "redis": "unknown",
            "chromadb": "unknown",
        }

        try:
            result = await asyncio.create_subprocess_exec(
                "docker", "ps", "--format", "{{.Names}}|{{.Status}}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(result.communicate(), timeout=5.0)

            if result.returncode == 0:
                for line in stdout.decode().strip().split("\n"):
                    if not line:
                        continue
                    parts = line.split("|")
                    if len(parts) < 2:
                        continue

                    name, status = parts[0], parts[1]

                    if "clopus-orchestrator" in name:
                        services["orchestrator"] = "running" if "Up" in status else "stopped"
                    elif "clopus-postgres" in name:
                        services["postgres"] = "healthy" if "healthy" in status else ("running" if "Up" in status else "stopped")
                    elif "clopus-redis" in name:
                        services["redis"] = "running" if "Up" in status else "stopped"
                    elif "clopus-chromadb" in name:
                        services["chromadb"] = "running" if "Up" in status else "stopped"

        except asyncio.TimeoutError:
            pass
        except Exception:
            pass

        return services
