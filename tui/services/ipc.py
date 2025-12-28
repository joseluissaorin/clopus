"""IPC Monitor for worker status"""

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
import time


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

    def __init__(self, ipc_path: str = "/app/ipc"):
        # Handle both container and host paths
        self.ipc_path = Path(ipc_path)
        if not self.ipc_path.exists():
            # Try via Docker
            self._use_docker = True
        else:
            self._use_docker = False

        self._callbacks: List[Callable] = []
        self._running = False
        self._worker_count = 11

    def on_update(self, callback: Callable) -> None:
        """Register callback for status updates"""
        self._callbacks.append(callback)

    async def get_worker_status(self, worker_id: int) -> Optional[WorkerStatus]:
        """Get status for a single worker"""
        status_file = self.ipc_path / "tasks" / str(worker_id) / "status.json"

        try:
            if self._use_docker:
                # Read via Docker exec
                import subprocess
                result = subprocess.run(
                    ["docker", "exec", "clopus-orchestrator", "cat",
                     f"/app/ipc/tasks/{worker_id}/status.json"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                else:
                    return WorkerStatus(
                        id=worker_id,
                        role="unknown",
                        status="offline"
                    )
            else:
                if not status_file.exists():
                    return WorkerStatus(
                        id=worker_id,
                        role="unknown",
                        status="offline"
                    )
                data = json.loads(status_file.read_text())

            return WorkerStatus(
                id=worker_id,
                role=data.get("role", "unknown"),
                status=data.get("status", "unknown"),
                model=data.get("model"),
                task_id=data.get("task_id"),
                task_started=data.get("task_started"),
                updated_at=data.get("updated_at"),
                started_at=data.get("started_at"),
                session_id=data.get("last_session"),
            )
        except Exception as e:
            return WorkerStatus(
                id=worker_id,
                role="unknown",
                status="offline"
            )

    async def get_all_worker_status(self) -> List[WorkerStatus]:
        """Get status for all workers"""
        workers = []
        for i in range(1, self._worker_count + 1):
            status = await self.get_worker_status(i)
            if status:
                workers.append(status)
        return workers

    async def get_worker_logs(self, worker_id: int, lines: int = 50) -> List[str]:
        """Get recent logs from a worker"""
        try:
            import subprocess
            result = subprocess.run(
                ["docker", "logs", f"clopus-worker-{worker_id}",
                 "--tail", str(lines)],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip().split("\n")
            return []
        except Exception:
            return []

    async def get_pending_task(self, worker_id: int) -> Optional[Dict[str, Any]]:
        """Get pending task for a worker if any"""
        pending_file = self.ipc_path / "tasks" / str(worker_id) / "pending.json"

        try:
            if self._use_docker:
                import subprocess
                result = subprocess.run(
                    ["docker", "exec", "clopus-orchestrator", "cat",
                     f"/app/ipc/tasks/{worker_id}/pending.json"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    return json.loads(result.stdout)
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

        return {
            "total_workers": len(workers),
            "busy": busy_count,
            "idle": idle_count,
            "offline": offline_count,
            "healthy": offline_count == 0,
            "utilization": busy_count / len(workers) if workers else 0,
        }
