"""Database client for TUI - Direct SQLite access"""

import asyncio
import aiosqlite
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class TaskInfo:
    id: str
    title: str
    status: str
    worker_id: Optional[int]
    priority: int
    created_at: Optional[str]
    completed_at: Optional[str]
    description: Optional[str] = None
    result: Optional[str] = None
    objective_id: Optional[str] = None
    error: Optional[str] = None
    retry_count: int = 0


@dataclass
class ObjectiveInfo:
    id: str
    content: str
    status: str
    priority: int
    created_at: Optional[str]
    completed_at: Optional[str]
    task_count: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0


@dataclass
class ProjectInfo:
    id: str
    name: str
    path: str
    status: str
    created_at: Optional[str]
    objective_id: Optional[str] = None
    task_count: int = 0
    completed_tasks: int = 0


class DatabaseClient:
    """Direct SQLite database access for TUI"""

    def __init__(self, db_path: str = "/app/data/sqlite/clopus.db"):
        # Handle both container and host paths
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            # Try host path
            host_path = Path.home() / "Dev/clopus/data/sqlite/clopus.db"
            if host_path.exists():
                self.db_path = host_path
        self._connection: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        """Connect to database"""
        if self._connection is None:
            self._connection = await aiosqlite.connect(self.db_path)
            self._connection.row_factory = aiosqlite.Row

    async def close(self) -> None:
        """Close database connection"""
        if self._connection:
            await self._connection.close()
            self._connection = None

    async def _get_conn(self) -> aiosqlite.Connection:
        """Get or create connection"""
        if self._connection is None:
            await self.connect()
        return self._connection

    async def get_task_stats(self) -> Dict[str, int]:
        """Get task status counts"""
        conn = await self._get_conn()
        stats = {"total": 0}
        async with conn.execute(
            "SELECT status, COUNT(*) as cnt FROM tasks GROUP BY status"
        ) as cursor:
            async for row in cursor:
                stats[row["status"]] = row["cnt"]
                stats["total"] += row["cnt"]
        return stats

    async def get_objective_stats(self) -> Dict[str, int]:
        """Get objective status counts"""
        conn = await self._get_conn()
        stats = {}
        async with conn.execute(
            "SELECT status, COUNT(*) as cnt FROM objectives GROUP BY status"
        ) as cursor:
            async for row in cursor:
                stats[row["status"]] = row["cnt"]
        return stats

    async def get_tasks(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[TaskInfo]:
        """Get tasks with optional status filter"""
        conn = await self._get_conn()

        if status:
            query = """
                SELECT id, title, status, worker_id, priority,
                       created_at, completed_at, description, result,
                       objective_id, error, retry_count
                FROM tasks WHERE status = ?
                ORDER BY priority DESC, created_at DESC
                LIMIT ? OFFSET ?
            """
            params = (status, limit, offset)
        else:
            query = """
                SELECT id, title, status, worker_id, priority,
                       created_at, completed_at, description, result,
                       objective_id, error, retry_count
                FROM tasks
                ORDER BY priority DESC, created_at DESC
                LIMIT ? OFFSET ?
            """
            params = (limit, offset)

        tasks = []
        async with conn.execute(query, params) as cursor:
            async for row in cursor:
                tasks.append(TaskInfo(
                    id=row["id"],
                    title=row["title"],
                    status=row["status"],
                    worker_id=row["worker_id"],
                    priority=row["priority"] or 0,
                    created_at=row["created_at"],
                    completed_at=row["completed_at"],
                    description=row["description"],
                    result=row["result"],
                    objective_id=row["objective_id"],
                    error=row["error"],
                    retry_count=row["retry_count"] or 0,
                ))
        return tasks

    async def get_objectives(
        self,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[ObjectiveInfo]:
        """Get objectives with task counts"""
        conn = await self._get_conn()

        if status:
            query = """
                SELECT o.id, o.content, o.status, o.priority, o.created_at, o.completed_at,
                       COUNT(t.id) as task_count,
                       SUM(CASE WHEN t.status = 'completed' THEN 1 ELSE 0 END) as completed_tasks
                FROM objectives o
                LEFT JOIN tasks t ON t.objective_id = o.id
                WHERE o.status = ?
                GROUP BY o.id
                ORDER BY o.priority DESC, o.created_at DESC
                LIMIT ?
            """
            params = (status, limit)
        else:
            query = """
                SELECT o.id, o.content, o.status, o.priority, o.created_at, o.completed_at,
                       COUNT(t.id) as task_count,
                       SUM(CASE WHEN t.status = 'completed' THEN 1 ELSE 0 END) as completed_tasks
                FROM objectives o
                LEFT JOIN tasks t ON t.objective_id = o.id
                GROUP BY o.id
                ORDER BY o.priority DESC, o.created_at DESC
                LIMIT ?
            """
            params = (limit,)

        objectives = []
        async with conn.execute(query, params) as cursor:
            async for row in cursor:
                objectives.append(ObjectiveInfo(
                    id=row["id"],
                    content=row["content"],
                    status=row["status"],
                    priority=row["priority"] or 0,
                    created_at=row["created_at"],
                    completed_at=row["completed_at"],
                    task_count=row["task_count"] or 0,
                    completed_tasks=row["completed_tasks"] or 0,
                ))
        return objectives

    async def get_projects(self) -> List[ProjectInfo]:
        """Get all projects with task counts"""
        conn = await self._get_conn()

        query = """
            SELECT p.id, p.name, p.local_path, p.status, p.created_at, p.objective_id,
                   COUNT(t.id) as task_count,
                   SUM(CASE WHEN t.status = 'completed' THEN 1 ELSE 0 END) as completed_tasks
            FROM projects p
            LEFT JOIN tasks t ON t.objective_id = p.objective_id
            GROUP BY p.id
            ORDER BY p.created_at DESC
        """

        projects = []
        async with conn.execute(query) as cursor:
            async for row in cursor:
                projects.append(ProjectInfo(
                    id=row["id"],
                    name=row["name"],
                    path=row["local_path"] or "",
                    status=row["status"],
                    created_at=row["created_at"],
                    objective_id=row["objective_id"],
                    task_count=row["task_count"] or 0,
                    completed_tasks=row["completed_tasks"] or 0,
                ))
        return projects

    async def get_recent_activity(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent completed tasks"""
        conn = await self._get_conn()

        query = """
            SELECT id, title, status, completed_at
            FROM tasks
            WHERE status = 'completed'
            ORDER BY completed_at DESC
            LIMIT ?
        """

        activities = []
        async with conn.execute(query, (limit,)) as cursor:
            async for row in cursor:
                activities.append({
                    "id": row["id"],
                    "title": row["title"],
                    "status": row["status"],
                    "completed_at": row["completed_at"],
                })
        return activities

    async def get_pending_questions(self) -> List[Dict[str, Any]]:
        """Get pending questions"""
        conn = await self._get_conn()

        query = """
            SELECT id, question, context, created_at, confidence_score
            FROM questions
            WHERE status = 'pending'
            ORDER BY created_at ASC
        """

        questions = []
        async with conn.execute(query) as cursor:
            async for row in cursor:
                questions.append({
                    "id": row["id"],
                    "content": row["question"],
                    "context": row["context"],
                    "created_at": row["created_at"],
                    "confidence": row["confidence_score"],
                })
        return questions

    async def retry_task(self, task_id: str) -> bool:
        """Retry a failed task by setting it back to pending"""
        conn = await self._get_conn()
        try:
            await conn.execute(
                "UPDATE tasks SET status = 'pending', worker_id = NULL WHERE id = ?",
                (task_id,)
            )
            await conn.commit()
            return True
        except Exception:
            return False

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a task"""
        conn = await self._get_conn()
        try:
            await conn.execute(
                "UPDATE tasks SET status = 'cancelled' WHERE id = ?",
                (task_id,)
            )
            await conn.commit()
            return True
        except Exception:
            return False

    async def update_task_priority(self, task_id: str, priority: int) -> bool:
        """Update task priority"""
        conn = await self._get_conn()
        try:
            await conn.execute(
                "UPDATE tasks SET priority = ? WHERE id = ?",
                (priority, task_id)
            )
            await conn.commit()
            return True
        except Exception:
            return False

    async def answer_question(self, question_id: str, answer: str) -> bool:
        """Answer a pending question"""
        conn = await self._get_conn()
        try:
            await conn.execute(
                """UPDATE questions SET status = 'answered', answer = ?,
                   answered_at = datetime('now') WHERE id = ?""",
                (answer, question_id)
            )
            await conn.commit()
            return True
        except Exception:
            return False

    async def get_project_info(self, project_name: str) -> Optional[ProjectInfo]:
        """Get project info by name"""
        conn = await self._get_conn()
        try:
            async with conn.execute(
                """SELECT p.id, p.name, p.local_path, p.status, p.created_at, p.objective_id,
                          COUNT(t.id) as task_count,
                          SUM(CASE WHEN t.status = 'completed' THEN 1 ELSE 0 END) as completed_tasks
                   FROM projects p
                   LEFT JOIN tasks t ON t.objective_id = p.objective_id
                   WHERE p.name = ?
                   GROUP BY p.id""",
                (project_name,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return ProjectInfo(
                        id=row["id"],
                        name=row["name"],
                        path=row["local_path"] or "",
                        status=row["status"],
                        created_at=row["created_at"],
                        objective_id=row["objective_id"],
                        task_count=row["task_count"] or 0,
                        completed_tasks=row["completed_tasks"] or 0,
                    )
        except Exception:
            pass
        return None

    async def get_project_tasks(self, project_name: str, limit: int = 50) -> List[TaskInfo]:
        """Get tasks for a specific project"""
        conn = await self._get_conn()
        tasks = []
        try:
            async with conn.execute(
                """SELECT t.id, t.title, t.status, t.worker_id,
                          t.priority, t.created_at, t.completed_at, t.description,
                          t.result, t.objective_id, t.error, t.retry_count
                   FROM tasks t
                   JOIN projects p ON t.objective_id = p.objective_id
                   WHERE p.name = ?
                   ORDER BY t.priority DESC, t.created_at DESC
                   LIMIT ?""",
                (project_name, limit)
            ) as cursor:
                async for row in cursor:
                    tasks.append(TaskInfo(
                        id=row["id"],
                        title=row["title"],
                        status=row["status"],
                        worker_id=row["worker_id"],
                        priority=row["priority"] or 0,
                        created_at=row["created_at"],
                        completed_at=row["completed_at"],
                        description=row["description"],
                        result=row["result"],
                        objective_id=row["objective_id"],
                        error=row["error"],
                        retry_count=row["retry_count"] or 0,
                    ))
        except Exception:
            pass
        return tasks

    async def get_memory_stats(self) -> Dict[str, int]:
        """Get memory system statistics"""
        conn = await self._get_conn()
        stats = {"tasks": 0, "objectives": 0, "decisions": 0, "questions": 0}
        try:
            # Count tasks
            async with conn.execute("SELECT COUNT(*) as cnt FROM tasks") as cursor:
                row = await cursor.fetchone()
                stats["tasks"] = row["cnt"] if row else 0

            # Count objectives
            async with conn.execute("SELECT COUNT(*) as cnt FROM objectives") as cursor:
                row = await cursor.fetchone()
                stats["objectives"] = row["cnt"] if row else 0

            # Count decisions
            async with conn.execute("SELECT COUNT(*) as cnt FROM decisions") as cursor:
                row = await cursor.fetchone()
                stats["decisions"] = row["cnt"] if row else 0

            # Count questions
            async with conn.execute("SELECT COUNT(*) as cnt FROM questions") as cursor:
                row = await cursor.fetchone()
                stats["questions"] = row["cnt"] if row else 0

        except Exception:
            pass
        return stats

    async def get_recent_memories(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent activity log entries"""
        conn = await self._get_conn()
        memories = []
        try:
            async with conn.execute(
                """SELECT id, source, action, details, created_at
                   FROM activity_log
                   ORDER BY created_at DESC
                   LIMIT ?""",
                (limit,)
            ) as cursor:
                async for row in cursor:
                    memories.append({
                        "id": row["id"],
                        "type": row["source"],
                        "key": row["action"],
                        "value": row["details"],
                        "created_at": row["created_at"],
                    })
        except Exception:
            pass
        return memories

    async def search_memories(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search activity log by action or details"""
        conn = await self._get_conn()
        memories = []
        try:
            async with conn.execute(
                """SELECT id, source, action, details, created_at
                   FROM activity_log
                   WHERE action LIKE ? OR details LIKE ?
                   ORDER BY created_at DESC
                   LIMIT ?""",
                (f"%{query}%", f"%{query}%", limit)
            ) as cursor:
                async for row in cursor:
                    memories.append({
                        "id": row["id"],
                        "type": row["source"],
                        "key": row["action"],
                        "value": row["details"],
                        "created_at": row["created_at"],
                    })
        except Exception:
            pass
        return memories

    async def cleanup_old_memories(self, days: int = 30) -> int:
        """Cleanup activity log older than specified days"""
        conn = await self._get_conn()
        try:
            result = await conn.execute(
                """DELETE FROM activity_log
                   WHERE created_at < datetime('now', '-' || ? || ' days')""",
                (days,)
            )
            await conn.commit()
            return result.rowcount
        except Exception:
            return 0
