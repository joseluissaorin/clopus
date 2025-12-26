# =============================================================================
# CLOPUS v3 Short-Term Memory (SQLite)
# =============================================================================
"""
SQLite-based short-term memory for operational state.
Handles tasks, workers, objectives, validation results, and session data.
"""

import asyncio
import aiosqlite
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class ObjectiveStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class TaskStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    VALIDATION = "validation"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class WorkerStatus(str, Enum):
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"


class ValidationStage(str, Enum):
    SYNTAX = "syntax"
    LINT = "lint"
    BUILD = "build"
    UNIT_TESTS = "unit_tests"
    INTEGRATION_TESTS = "integration_tests"
    E2E_TESTS = "e2e_tests"
    SECURITY = "security"
    REVIEW = "review"


@dataclass
class Objective:
    id: str
    content: str
    status: ObjectiveStatus = ObjectiveStatus.PENDING
    priority: int = 5
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Optional[Dict] = None


@dataclass
class Task:
    id: str
    objective_id: str
    title: str
    description: Optional[str] = None
    parent_task_id: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    worker_id: Optional[int] = None
    worker_role: Optional[str] = None
    priority: int = 5
    dependencies: List[str] = None
    created_at: Optional[datetime] = None
    assigned_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class Worker:
    id: int
    role: str
    status: WorkerStatus = WorkerStatus.IDLE
    current_task_id: Optional[str] = None
    last_heartbeat: Optional[datetime] = None
    started_at: Optional[datetime] = None
    tasks_completed: int = 0
    tasks_failed: int = 0
    metadata: Optional[Dict] = None


class ShortTermMemory:
    """SQLite-based short-term memory manager."""

    def __init__(self, db_path: str = "/app/data/sqlite/clopus.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize database with schema."""
        schema_path = Path(__file__).parent / "schema.sql"
        conn = await self._get_connection()
        with open(schema_path, "r") as f:
            await conn.executescript(f.read())
        await conn.commit()

    async def _get_connection(self) -> aiosqlite.Connection:
        """Get or create database connection."""
        if self._connection is None:
            self._connection = await aiosqlite.connect(self.db_path)
            self._connection.row_factory = aiosqlite.Row
        return self._connection

    async def close(self) -> None:
        """Close database connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None

    # =========================================================================
    # OBJECTIVES
    # =========================================================================

    async def create_objective(self, content: str, priority: int = 5, metadata: Optional[Dict] = None) -> Objective:
        """Create a new objective."""
        objective = Objective(
            id=str(uuid.uuid4()),
            content=content,
            priority=priority,
            created_at=datetime.now(),
            metadata=metadata
        )

        async with self._lock:
            conn = await self._get_connection()
            await conn.execute(
                """INSERT INTO objectives (id, content, status, priority, created_at, metadata)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (objective.id, objective.content, objective.status.value,
                 objective.priority, objective.created_at, json.dumps(objective.metadata))
            )
            await conn.commit()

        return objective

    async def get_objective(self, objective_id: str) -> Optional[Objective]:
        """Get objective by ID."""
        conn = await self._get_connection()
        async with conn.execute(
            "SELECT * FROM objectives WHERE id = ?", (objective_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return self._row_to_objective(row)
        return None

    async def get_pending_objectives(self) -> List[Objective]:
        """Get all pending objectives ordered by priority."""
        conn = await self._get_connection()
        async with conn.execute(
            "SELECT * FROM objectives WHERE status = 'pending' ORDER BY priority DESC, created_at ASC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [self._row_to_objective(row) for row in rows]

    async def update_objective_status(self, objective_id: str, status: ObjectiveStatus) -> None:
        """Update objective status."""
        async with self._lock:
            conn = await self._get_connection()
            updates = {"status": status.value}
            if status == ObjectiveStatus.IN_PROGRESS:
                updates["started_at"] = datetime.now().isoformat()
            elif status in (ObjectiveStatus.COMPLETED, ObjectiveStatus.FAILED):
                updates["completed_at"] = datetime.now().isoformat()

            set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
            await conn.execute(
                f"UPDATE objectives SET {set_clause} WHERE id = ?",
                (*updates.values(), objective_id)
            )
            await conn.commit()

    def _row_to_objective(self, row) -> Objective:
        return Objective(
            id=row["id"],
            content=row["content"],
            status=ObjectiveStatus(row["status"]),
            priority=row["priority"],
            created_at=row["created_at"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else None
        )

    # =========================================================================
    # TASKS
    # =========================================================================

    async def create_task(
        self,
        objective_id: str,
        title: str,
        description: Optional[str] = None,
        parent_task_id: Optional[str] = None,
        priority: int = 5,
        dependencies: Optional[List[str]] = None,
        worker_role: Optional[str] = None
    ) -> Task:
        """Create a new task."""
        task = Task(
            id=str(uuid.uuid4()),
            objective_id=objective_id,
            title=title,
            description=description,
            parent_task_id=parent_task_id,
            priority=priority,
            dependencies=dependencies or [],
            worker_role=worker_role,
            created_at=datetime.now()
        )

        async with self._lock:
            conn = await self._get_connection()
            await conn.execute(
                """INSERT INTO tasks
                   (id, objective_id, parent_task_id, title, description, status,
                    worker_role, priority, dependencies, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (task.id, task.objective_id, task.parent_task_id, task.title,
                 task.description, task.status.value, task.worker_role,
                 task.priority, json.dumps(task.dependencies), task.created_at)
            )
            await conn.commit()

        return task

    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        conn = await self._get_connection()
        async with conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return self._row_to_task(row)
        return None

    async def get_tasks_for_objective(self, objective_id: str) -> List[Task]:
        """Get all tasks for an objective."""
        conn = await self._get_connection()
        async with conn.execute(
            "SELECT * FROM tasks WHERE objective_id = ? ORDER BY created_at ASC",
            (objective_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [self._row_to_task(row) for row in rows]

    async def get_pending_tasks(self, worker_role: Optional[str] = None) -> List[Task]:
        """Get pending tasks, optionally filtered by worker role."""
        conn = await self._get_connection()
        if worker_role:
            query = """SELECT * FROM tasks
                       WHERE status = 'pending' AND (worker_role IS NULL OR worker_role = ?)
                       ORDER BY priority DESC, created_at ASC"""
            params = (worker_role,)
        else:
            query = "SELECT * FROM tasks WHERE status = 'pending' ORDER BY priority DESC, created_at ASC"
            params = ()

        async with conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [self._row_to_task(row) for row in rows]

    async def assign_task(self, task_id: str, worker_id: int, worker_role: str) -> None:
        """Assign task to a worker."""
        async with self._lock:
            conn = await self._get_connection()
            await conn.execute(
                """UPDATE tasks SET status = 'assigned', worker_id = ?, worker_role = ?, assigned_at = ?
                   WHERE id = ?""",
                (worker_id, worker_role, datetime.now().isoformat(), task_id)
            )
            await conn.commit()

    async def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        result: Optional[Dict] = None,
        error: Optional[str] = None
    ) -> None:
        """Update task status."""
        async with self._lock:
            conn = await self._get_connection()
            updates = {"status": status.value}

            if status == TaskStatus.IN_PROGRESS:
                updates["started_at"] = datetime.now().isoformat()
            elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                updates["completed_at"] = datetime.now().isoformat()
                if result:
                    updates["result"] = json.dumps(result)
                if error:
                    updates["error"] = error

            set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
            await conn.execute(
                f"UPDATE tasks SET {set_clause} WHERE id = ?",
                (*updates.values(), task_id)
            )
            await conn.commit()

    async def increment_task_retry(self, task_id: str) -> int:
        """Increment task retry count and return new count."""
        async with self._lock:
            conn = await self._get_connection()
            await conn.execute(
                "UPDATE tasks SET retry_count = retry_count + 1, status = 'pending' WHERE id = ?",
                (task_id,)
            )
            await conn.commit()

            async with conn.execute("SELECT retry_count FROM tasks WHERE id = ?", (task_id,)) as cursor:
                row = await cursor.fetchone()
                return row["retry_count"] if row else 0

    def _row_to_task(self, row) -> Task:
        return Task(
            id=row["id"],
            objective_id=row["objective_id"],
            parent_task_id=row["parent_task_id"],
            title=row["title"],
            description=row["description"],
            status=TaskStatus(row["status"]),
            worker_id=row["worker_id"],
            worker_role=row["worker_role"],
            priority=row["priority"],
            dependencies=json.loads(row["dependencies"]) if row["dependencies"] else [],
            created_at=row["created_at"],
            assigned_at=row["assigned_at"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            result=json.loads(row["result"]) if row["result"] else None,
            error=row["error"],
            retry_count=row["retry_count"],
            max_retries=row["max_retries"]
        )

    # =========================================================================
    # WORKERS
    # =========================================================================

    async def register_worker(self, worker_id: int, role: str) -> Worker:
        """Register or update a worker."""
        worker = Worker(
            id=worker_id,
            role=role,
            status=WorkerStatus.IDLE,
            started_at=datetime.now(),
            last_heartbeat=datetime.now()
        )

        async with self._lock:
            conn = await self._get_connection()
            await conn.execute(
                """INSERT OR REPLACE INTO workers (id, role, status, last_heartbeat, started_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (worker.id, worker.role, worker.status.value,
                 worker.last_heartbeat, worker.started_at)
            )
            await conn.commit()

        return worker

    async def update_worker_status(
        self,
        worker_id: int,
        status: WorkerStatus,
        current_task_id: Optional[str] = None
    ) -> None:
        """Update worker status."""
        async with self._lock:
            conn = await self._get_connection()
            await conn.execute(
                """UPDATE workers SET status = ?, current_task_id = ?, last_heartbeat = ?
                   WHERE id = ?""",
                (status.value, current_task_id, datetime.now().isoformat(), worker_id)
            )
            await conn.commit()

    async def worker_heartbeat(self, worker_id: int) -> None:
        """Update worker heartbeat."""
        async with self._lock:
            conn = await self._get_connection()
            await conn.execute(
                "UPDATE workers SET last_heartbeat = ? WHERE id = ?",
                (datetime.now().isoformat(), worker_id)
            )
            await conn.commit()

    async def get_worker(self, worker_id: int) -> Optional[Worker]:
        """Get worker by ID."""
        conn = await self._get_connection()
        async with conn.execute("SELECT * FROM workers WHERE id = ?", (worker_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return self._row_to_worker(row)
        return None

    async def get_idle_workers(self, role: Optional[str] = None) -> List[Worker]:
        """Get idle workers, optionally filtered by role."""
        conn = await self._get_connection()
        if role:
            query = "SELECT * FROM workers WHERE status = 'idle' AND role = ?"
            params = (role,)
        else:
            query = "SELECT * FROM workers WHERE status = 'idle'"
            params = ()

        async with conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [self._row_to_worker(row) for row in rows]

    async def increment_worker_stats(self, worker_id: int, completed: bool = True) -> None:
        """Increment worker task statistics."""
        async with self._lock:
            conn = await self._get_connection()
            if completed:
                await conn.execute(
                    "UPDATE workers SET tasks_completed = tasks_completed + 1 WHERE id = ?",
                    (worker_id,)
                )
            else:
                await conn.execute(
                    "UPDATE workers SET tasks_failed = tasks_failed + 1 WHERE id = ?",
                    (worker_id,)
                )
            await conn.commit()

    def _row_to_worker(self, row) -> Worker:
        return Worker(
            id=row["id"],
            role=row["role"],
            status=WorkerStatus(row["status"]),
            current_task_id=row["current_task_id"],
            last_heartbeat=row["last_heartbeat"],
            started_at=row["started_at"],
            tasks_completed=row["tasks_completed"],
            tasks_failed=row["tasks_failed"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else None
        )

    # =========================================================================
    # QUESTIONS
    # =========================================================================

    async def create_question(
        self,
        question: str,
        context: Optional[str] = None,
        task_id: Optional[str] = None,
        objective_id: Optional[str] = None,
        confidence_score: Optional[float] = None
    ) -> str:
        """Create a question for user."""
        question_id = str(uuid.uuid4())

        async with self._lock:
            conn = await self._get_connection()
            await conn.execute(
                """INSERT INTO questions (id, task_id, objective_id, question, context, confidence_score, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (question_id, task_id, objective_id, question, context,
                 confidence_score, datetime.now().isoformat())
            )
            await conn.commit()

        return question_id

    async def get_pending_questions(self) -> List[Dict]:
        """Get all pending questions."""
        conn = await self._get_connection()
        async with conn.execute(
            "SELECT * FROM questions WHERE status = 'pending' ORDER BY created_at ASC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def answer_question(self, question_id: str, answer: str) -> Optional[str]:
        """Record answer to a question and re-queue linked objective."""
        async with self._lock:
            conn = await self._get_connection()

            # Get the question to find linked objective
            async with conn.execute(
                "SELECT objective_id FROM questions WHERE id = ?",
                (question_id,)
            ) as cursor:
                row = await cursor.fetchone()
                objective_id = row["objective_id"] if row else None

            # Update question status
            await conn.execute(
                "UPDATE questions SET status = 'answered', answer = ?, answered_at = ? WHERE id = ?",
                (answer, datetime.now().isoformat(), question_id)
            )

            # If linked to objective, re-queue it with clarification
            if objective_id:
                # Get current metadata
                async with conn.execute(
                    "SELECT metadata FROM objectives WHERE id = ?",
                    (objective_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if not row:
                        # Objective doesn't exist anymore
                        await conn.commit()
                        return None

                    # Parse metadata safely
                    metadata = {}
                    if row["metadata"]:
                        try:
                            metadata = json.loads(row["metadata"])
                            if metadata is None:
                                metadata = {}
                        except (json.JSONDecodeError, TypeError):
                            metadata = {}

                # Add clarification to metadata
                if not isinstance(metadata, dict):
                    metadata = {}
                if "clarifications" not in metadata:
                    metadata["clarifications"] = []
                metadata["clarifications"].append({
                    "question_id": question_id,
                    "answer": answer,
                    "answered_at": datetime.now().isoformat()
                })

                # Reset objective to pending for reprocessing
                await conn.execute(
                    "UPDATE objectives SET status = 'pending', metadata = ? WHERE id = ?",
                    (json.dumps(metadata), objective_id)
                )

            await conn.commit()
            return objective_id

    # =========================================================================
    # DECISIONS
    # =========================================================================

    async def record_decision(
        self,
        decision_type: str,
        options: List[str],
        chosen_option: str,
        confidence_score: float,
        reasoning: Optional[str] = None,
        task_id: Optional[str] = None
    ) -> str:
        """Record a decision for learning."""
        decision_id = str(uuid.uuid4())

        async with self._lock:
            conn = await self._get_connection()
            await conn.execute(
                """INSERT INTO decisions
                   (id, task_id, decision_type, options, chosen_option, confidence_score, reasoning, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (decision_id, task_id, decision_type, json.dumps(options),
                 chosen_option, confidence_score, reasoning, datetime.now().isoformat())
            )
            await conn.commit()

        return decision_id

    async def update_decision_outcome(self, decision_id: str, outcome: str) -> None:
        """Update decision outcome for learning."""
        async with self._lock:
            conn = await self._get_connection()
            await conn.execute(
                "UPDATE decisions SET outcome = ?, evaluated_at = ? WHERE id = ?",
                (outcome, datetime.now().isoformat(), decision_id)
            )
            await conn.commit()

    # =========================================================================
    # SESSION STATE
    # =========================================================================

    async def set_state(self, key: str, value: Any) -> None:
        """Set session state value."""
        async with self._lock:
            conn = await self._get_connection()
            await conn.execute(
                "INSERT OR REPLACE INTO session_state (key, value, updated_at) VALUES (?, ?, ?)",
                (key, json.dumps(value), datetime.now().isoformat())
            )
            await conn.commit()

    async def get_state(self, key: str, default: Any = None) -> Any:
        """Get session state value."""
        conn = await self._get_connection()
        async with conn.execute(
            "SELECT value FROM session_state WHERE key = ?", (key,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return json.loads(row["value"])
        return default

    # =========================================================================
    # ACTIVITY LOG
    # =========================================================================

    async def log_activity(
        self,
        source: str,
        action: str,
        details: Optional[Dict] = None,
        level: str = "info",
        objective_id: Optional[str] = None,
        task_id: Optional[str] = None,
        worker_id: Optional[int] = None
    ) -> None:
        """Log activity."""
        async with self._lock:
            conn = await self._get_connection()
            await conn.execute(
                """INSERT INTO activity_log
                   (level, source, action, details, objective_id, task_id, worker_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (level, source, action, json.dumps(details) if details else None,
                 objective_id, task_id, worker_id)
            )
            await conn.commit()

    async def get_recent_activity(self, limit: int = 100, level: Optional[str] = None) -> List[Dict]:
        """Get recent activity."""
        conn = await self._get_connection()
        if level:
            query = f"SELECT * FROM activity_log WHERE level = ? ORDER BY timestamp DESC LIMIT {limit}"
            params = (level,)
        else:
            query = f"SELECT * FROM activity_log ORDER BY timestamp DESC LIMIT {limit}"
            params = ()

        async with conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
