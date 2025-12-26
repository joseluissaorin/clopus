# =============================================================================
# CLOPUS v3 Status Reporter
# =============================================================================
"""
Continuous status reporting for CLOPUS operations.
Provides real-time visibility into system state.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger("clopus.status_reporter")


class StatusReporter:
    """Report system status continuously."""

    def __init__(
        self,
        memory_client,
        worker_pool,
        status_file: str = "/app/ipc/status.json"
    ):
        self.memory = memory_client
        self.worker_pool = worker_pool
        self.status_file = Path(status_file)
        self._last_status: Optional[Dict] = None

    async def get_status(self) -> Dict[str, Any]:
        """Get complete system status."""
        status = {
            "timestamp": datetime.now().isoformat(),
            "system": await self._get_system_status(),
            "objectives": await self._get_objectives_status(),
            "tasks": await self._get_tasks_status(),
            "workers": await self._get_workers_status(),
            "questions": await self._get_questions_status(),
            "memory": await self._get_memory_status()
        }

        self._last_status = status
        return status

    async def _get_system_status(self) -> Dict:
        """Get overall system status."""
        workers = await self.worker_pool.get_all_status()

        idle_count = sum(1 for w in workers if w.get("status") == "idle")
        busy_count = sum(1 for w in workers if w.get("status") == "busy")
        offline_count = sum(1 for w in workers if w.get("status") == "offline")

        if offline_count > 0:
            health = "degraded"
        elif busy_count == len(workers):
            health = "busy"
        else:
            health = "healthy"

        return {
            "health": health,
            "workers_total": len(workers),
            "workers_idle": idle_count,
            "workers_busy": busy_count,
            "workers_offline": offline_count
        }

    async def _get_objectives_status(self) -> Dict:
        """Get objectives status."""
        # Get from short-term memory
        pending = await self.memory.short_term.get_pending_objectives()

        return {
            "pending": len(pending),
            "active": len([o for o in pending if o.status.value == "in_progress"]),
            "recent": [
                {
                    "id": o.id,
                    "summary": o.content[:100],
                    "status": o.status.value,
                    "created_at": o.created_at.isoformat() if hasattr(o.created_at, 'isoformat') else o.created_at
                }
                for o in pending[:5]
            ]
        }

    async def _get_tasks_status(self) -> Dict:
        """Get tasks status."""
        # Get pending tasks
        pending = await self.memory.short_term.get_pending_tasks()

        # Group by status
        status_counts = {}
        for task in pending:
            status = task.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_pending": len(pending),
            "by_status": status_counts,
            "recent": [
                {
                    "id": t.id,
                    "title": t.title,
                    "status": t.status.value,
                    "worker_role": t.worker_role,
                    "priority": t.priority
                }
                for t in pending[:10]
            ]
        }

    async def _get_workers_status(self) -> List[Dict]:
        """Get workers status."""
        return await self.worker_pool.get_all_status()

    async def _get_questions_status(self) -> Dict:
        """Get pending questions status."""
        questions = await self.memory.get_pending_questions()

        return {
            "pending": len(questions),
            "questions": [
                {
                    "id": q.get("id"),
                    "question": q.get("question", "")[:200],
                    "confidence": q.get("confidence_score"),
                    "created_at": q.get("created_at")
                }
                for q in questions[:5]
            ]
        }

    async def _get_memory_status(self) -> Dict:
        """Get memory system status."""
        stats = await self.memory.get_statistics()
        return stats

    async def write_status_file(self, status: Optional[Dict] = None) -> None:
        """Write status to file."""
        if status is None:
            status = await self.get_status()

        self.status_file.parent.mkdir(parents=True, exist_ok=True)
        self.status_file.write_text(json.dumps(status, indent=2, default=str))

    async def get_summary(self) -> str:
        """Get a text summary of current status."""
        status = await self.get_status()

        lines = [
            "=== CLOPUS Status ===",
            f"Time: {status['timestamp']}",
            "",
            f"System Health: {status['system']['health'].upper()}",
            f"Workers: {status['system']['workers_busy']}/{status['system']['workers_total']} busy",
            "",
            f"Objectives: {status['objectives']['pending']} pending, {status['objectives']['active']} active",
            f"Tasks: {status['tasks']['total_pending']} pending",
            f"Questions: {status['questions']['pending']} awaiting answer",
            "",
            "--- Workers ---"
        ]

        for worker in status['workers']:
            role = worker.get('role', 'unknown')
            worker_status = worker.get('status', 'unknown')
            current = worker.get('current_task', '-')
            lines.append(f"  Worker {worker['id']} ({role}): {worker_status}")
            if current and current != '-':
                lines.append(f"    Current: {current}")

        if status['questions']['pending'] > 0:
            lines.append("")
            lines.append("--- Pending Questions ---")
            for q in status['questions']['questions']:
                lines.append(f"  [{q['id'][:8]}...] {q['question'][:60]}...")

        return "\n".join(lines)

    async def log_progress(
        self,
        objective_id: str,
        message: str,
        percentage: Optional[float] = None
    ) -> None:
        """Log progress for an objective."""
        await self.memory.short_term.log_activity(
            source="progress",
            action="update",
            details={
                "message": message,
                "percentage": percentage
            },
            objective_id=objective_id
        )

        logger.info(f"[{objective_id[:8]}] {message}" + (f" ({percentage:.0%})" if percentage else ""))

    async def report_error(
        self,
        source: str,
        error: str,
        context: Optional[Dict] = None
    ) -> None:
        """Report an error."""
        await self.memory.short_term.log_activity(
            source=source,
            action="error",
            details={"error": error, "context": context},
            level="error"
        )

        logger.error(f"[{source}] {error}")

    async def report_milestone(
        self,
        objective_id: str,
        milestone: str
    ) -> None:
        """Report a milestone achievement."""
        await self.memory.short_term.log_activity(
            source="milestone",
            action=milestone,
            objective_id=objective_id
        )

        logger.info(f"[MILESTONE] {objective_id[:8]}: {milestone}")
