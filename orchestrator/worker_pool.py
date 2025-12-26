# =============================================================================
# CLOPUS v3 Worker Pool
# =============================================================================
"""
Manages the pool of Claude Code worker instances.
Handles task dispatch, result collection, and worker health monitoring.
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import logging

from .config import WorkerConfig

logger = logging.getLogger("clopus.worker_pool")


class WorkerPool:
    """Manage Claude Code worker instances."""

    def __init__(
        self,
        memory_client,
        config: WorkerConfig,
        ipc_path: str = "/app/ipc"
    ):
        self.memory = memory_client
        self.config = config
        self.ipc_path = Path(ipc_path)
        self.workers: Dict[int, Dict] = {}
        self._running = False

    async def initialize(self) -> None:
        """Initialize worker pool."""
        logger.info(f"Initializing worker pool with {self.config.count} workers")

        # Create IPC directories
        self.ipc_path.mkdir(parents=True, exist_ok=True)

        for i in range(1, self.config.count + 1):
            role = self.config.roles[(i - 1) % len(self.config.roles)]

            # Create worker IPC directory
            worker_dir = self.ipc_path / "tasks" / str(i)
            worker_dir.mkdir(parents=True, exist_ok=True)

            # Register worker
            worker = await self.memory.register_worker(i, role)
            self.workers[i] = {
                "id": i,
                "role": role,
                "status": "idle",
                "current_task": None,
                "ipc_dir": worker_dir,
                "last_heartbeat": datetime.now()
            }

            logger.info(f"Registered worker {i} with role: {role}")

        self._running = True

    async def shutdown(self) -> None:
        """Shutdown worker pool."""
        logger.info("Shutting down worker pool")
        self._running = False

        # Clear pending tasks
        for worker_id, worker in self.workers.items():
            pending_file = worker["ipc_dir"] / "pending.json"
            if pending_file.exists():
                pending_file.unlink()

    async def dispatch_task(
        self,
        worker_id: int,
        task_id: str,
        title: str,
        description: Optional[str] = None,
        cwd: str = "/workspace"
    ) -> bool:
        """Dispatch a task to a worker."""
        if worker_id not in self.workers:
            logger.error(f"Worker {worker_id} not found")
            return False

        worker = self.workers[worker_id]

        if worker["status"] != "idle":
            logger.warning(f"Worker {worker_id} is not idle (status: {worker['status']})")
            return False

        # Build prompt for Claude Code
        prompt = self._build_task_prompt(title, description, worker["role"])

        # Create task file
        task_data = {
            "task_id": task_id,
            "prompt": prompt,
            "cwd": cwd,
            "dispatched_at": datetime.now().isoformat()
        }

        pending_file = worker["ipc_dir"] / "pending.json"
        pending_file.write_text(json.dumps(task_data, indent=2))

        # Update worker state
        worker["status"] = "busy"
        worker["current_task"] = task_id

        logger.info(f"Dispatched task {task_id} to worker {worker_id}")
        return True

    def _build_task_prompt(self, title: str, description: Optional[str], role: str) -> str:
        """Build a prompt for Claude Code."""
        role_instructions = {
            "coder": "You are implementing code. Focus on clean, working code that follows best practices.",
            "tester": "You are writing tests. Ensure comprehensive coverage and edge case handling.",
            "reviewer": "You are reviewing code. Check for bugs, security issues, and best practices.",
            "researcher": "You are researching. Find relevant information, docs, and solutions.",
            "debugger": "You are debugging. Identify root causes and implement fixes.",
        }

        instruction = role_instructions.get(role, role_instructions["coder"])

        prompt_parts = [
            f"# Task: {title}",
            "",
            instruction,
            "",
        ]

        if description:
            prompt_parts.extend([
                "## Details",
                description,
                "",
            ])

        prompt_parts.extend([
            "## Requirements",
            "- Complete the task fully",
            "- Ensure code passes linting",
            "- Write clean, readable code",
            "- Handle errors appropriately",
            "",
            "Begin working on this task now."
        ])

        return "\n".join(prompt_parts)

    async def collect_results(self) -> Dict[int, Dict]:
        """Collect completed task results from workers."""
        results = {}

        for worker_id, worker in self.workers.items():
            if worker["status"] != "busy":
                continue

            result_file = worker["ipc_dir"] / "result.json"

            if result_file.exists():
                try:
                    result_data = json.loads(result_file.read_text())
                    results[worker_id] = result_data

                    # Clear result file
                    result_file.unlink()

                    # Update worker state
                    worker["status"] = "idle"
                    worker["current_task"] = None
                    worker["last_heartbeat"] = datetime.now()

                    logger.info(f"Collected result from worker {worker_id}: {result_data.get('task_id')}")

                except json.JSONDecodeError as e:
                    logger.error(f"Invalid result JSON from worker {worker_id}: {e}")

        return results

    async def check_heartbeats(self) -> List[int]:
        """Check worker heartbeats and return stale workers."""
        stale_workers = []
        timeout = timedelta(seconds=self.config.heartbeat_interval_s * 3)

        for worker_id, worker in self.workers.items():
            # Check status file for heartbeat
            status_file = worker["ipc_dir"] / "status.json"

            if status_file.exists():
                try:
                    status_data = json.loads(status_file.read_text())
                    updated_at = status_data.get("updated_at") or status_data.get("started_at")

                    if updated_at:
                        last_update = datetime.fromisoformat(updated_at)
                        # Ensure both datetimes are timezone-aware
                        now = datetime.now(timezone.utc)
                        if last_update.tzinfo is None:
                            last_update = last_update.replace(tzinfo=timezone.utc)
                        if now - last_update > timeout:
                            stale_workers.append(worker_id)
                            worker["status"] = "offline"
                        else:
                            worker["last_heartbeat"] = last_update
                            # Reset to idle if worker was offline but is now responding
                            if worker["status"] == "offline":
                                worker["status"] = "idle"
                                logger.info(f"Worker {worker_id} back online")

                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Error reading status for worker {worker_id}: {e}")

        if stale_workers:
            logger.warning(f"Stale workers detected: {stale_workers}")

        return stale_workers

    async def get_idle_workers(self, role: Optional[str] = None) -> List[Dict]:
        """Get list of idle workers."""
        idle = []

        for worker_id, worker in self.workers.items():
            if worker["status"] == "idle":
                if role is None or worker["role"] == role:
                    idle.append(worker)

        return idle

    async def get_worker_status(self, worker_id: int) -> Optional[Dict]:
        """Get status of a specific worker."""
        if worker_id not in self.workers:
            return None

        worker = self.workers[worker_id]
        status_file = worker["ipc_dir"] / "status.json"

        status = {
            "id": worker_id,
            "role": worker["role"],
            "status": worker["status"],
            "current_task": worker["current_task"],
            "last_heartbeat": worker["last_heartbeat"].isoformat()
        }

        if status_file.exists():
            try:
                file_status = json.loads(status_file.read_text())
                status.update(file_status)
            except json.JSONDecodeError:
                pass

        return status

    async def get_all_status(self) -> List[Dict]:
        """Get status of all workers."""
        statuses = []
        for worker_id in self.workers:
            status = await self.get_worker_status(worker_id)
            if status:
                statuses.append(status)
        return statuses

    async def cancel_task(self, worker_id: int) -> bool:
        """Cancel the current task for a worker."""
        if worker_id not in self.workers:
            return False

        worker = self.workers[worker_id]

        # Remove pending file if exists
        pending_file = worker["ipc_dir"] / "pending.json"
        if pending_file.exists():
            pending_file.unlink()

        # Write cancel signal
        cancel_file = worker["ipc_dir"] / "cancel"
        cancel_file.touch()

        # Update status
        worker["status"] = "idle"
        worker["current_task"] = None

        logger.info(f"Cancelled task for worker {worker_id}")
        return True

    async def reassign_task(self, from_worker: int, to_worker: int) -> bool:
        """Reassign a task from one worker to another."""
        if from_worker not in self.workers or to_worker not in self.workers:
            return False

        from_worker_data = self.workers[from_worker]
        to_worker_data = self.workers[to_worker]

        if to_worker_data["status"] != "idle":
            return False

        # Read pending task
        pending_file = from_worker_data["ipc_dir"] / "pending.json"
        if not pending_file.exists():
            return False

        task_data = json.loads(pending_file.read_text())

        # Move to new worker
        new_pending_file = to_worker_data["ipc_dir"] / "pending.json"
        new_pending_file.write_text(json.dumps(task_data, indent=2))

        # Clean up old worker
        pending_file.unlink()
        from_worker_data["status"] = "idle"
        from_worker_data["current_task"] = None

        # Update new worker
        to_worker_data["status"] = "busy"
        to_worker_data["current_task"] = task_data.get("task_id")

        logger.info(f"Reassigned task from worker {from_worker} to {to_worker}")
        return True

    def get_worker_by_role(self, role: str) -> Optional[int]:
        """Get a worker ID by role preference."""
        # First try exact role match
        for worker_id, worker in self.workers.items():
            if worker["role"] == role and worker["status"] == "idle":
                return worker_id

        # Fall back to any idle worker
        for worker_id, worker in self.workers.items():
            if worker["status"] == "idle":
                return worker_id

        return None
