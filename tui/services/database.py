"""Database client for TUI - Direct SQLite access"""

import asyncio
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

try:
    import aiosqlite
except ImportError:
    aiosqlite = None


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

    def __init__(self, db_path: Optional[str] = None):
        # Auto-detect database path
        self.db_path = self._find_database(db_path)
        self._connection = None
        self._connected = False

    def _find_database(self, db_path: Optional[str] = None) -> Path:
        """Find the CLOPUS database in various locations"""
        candidates = []

        if db_path:
            candidates.append(Path(db_path))

        # Get the clopus directory (assuming TUI is in /clopus/tui/)
        clopus_dir = Path(__file__).parent.parent.parent

        # Priority order for database locations
        candidates.extend([
            clopus_dir / "data" / "sqlite" / "clopus.db",
            clopus_dir / "memory" / "short_term.db",
            Path.home() / "Dev" / "clopus" / "data" / "sqlite" / "clopus.db",
            Path.home() / "Dev" / "clopus" / "memory" / "short_term.db",
            Path("/app/data/sqlite/clopus.db"),  # Container path
        ])

        for path in candidates:
            if path.exists():
                return path

        # Return the most likely path even if it doesn't exist yet
        return clopus_dir / "data" / "sqlite" / "clopus.db"

    async def connect(self) -> bool:
        """Connect to database"""
        if aiosqlite is None:
            return False

        if self._connection is not None:
            return True

        try:
            if not self.db_path.exists():
                self._connected = False
                return False

            self._connection = await aiosqlite.connect(str(self.db_path))
            self._connection.row_factory = aiosqlite.Row
            self._connected = True
            return True
        except Exception as e:
            self._connected = False
            return False

    async def close(self) -> None:
        """Close database connection"""
        if self._connection:
            try:
                await self._connection.close()
            except Exception:
                pass
            self._connection = None
            self._connected = False

    async def _get_conn(self):
        """Get or create connection"""
        if not self._connected:
            await self.connect()
        return self._connection

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def get_task_stats(self) -> Dict[str, int]:
        """Get task status counts"""
        stats = {"total": 0, "completed": 0, "failed": 0, "pending": 0, "in_progress": 0, "running": 0}

        conn = await self._get_conn()
        if not conn:
            return stats

        try:
            async with conn.execute(
                "SELECT status, COUNT(*) as cnt FROM tasks GROUP BY status"
            ) as cursor:
                async for row in cursor:
                    status = row["status"]
                    count = row["cnt"]
                    stats[status] = count
                    stats["total"] += count
                    # Map status variants
                    if status in ("in_progress", "assigned"):
                        stats["running"] += count
        except Exception:
            pass
        return stats

    async def get_objective_stats(self) -> Dict[str, int]:
        """Get objective status counts"""
        stats = {"total": 0, "pending": 0, "in_progress": 0, "completed": 0}

        conn = await self._get_conn()
        if not conn:
            return stats

        try:
            async with conn.execute(
                "SELECT status, COUNT(*) as cnt FROM objectives GROUP BY status"
            ) as cursor:
                async for row in cursor:
                    stats[row["status"]] = row["cnt"]
                    stats["total"] += row["cnt"]
        except Exception:
            pass
        return stats

    async def get_tasks(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[TaskInfo]:
        """Get tasks with optional status filter"""
        conn = await self._get_conn()
        if not conn:
            return []

        try:
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
        except Exception:
            return []

    async def get_objectives(
        self,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[ObjectiveInfo]:
        """Get objectives with task counts"""
        conn = await self._get_conn()
        if not conn:
            return []

        try:
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
        except Exception:
            return []

    async def get_projects(self) -> List[ProjectInfo]:
        """Get all projects with task counts"""
        conn = await self._get_conn()
        if not conn:
            return []

        try:
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
        except Exception:
            return []

    async def get_recent_activity(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent completed tasks"""
        conn = await self._get_conn()
        if not conn:
            return []

        try:
            query = """
                SELECT id, title, status, completed_at
                FROM tasks
                WHERE status IN ('completed', 'failed')
                ORDER BY COALESCE(completed_at, created_at) DESC
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
        except Exception:
            return []

    async def get_pending_questions(self) -> List[Dict[str, Any]]:
        """Get pending questions"""
        conn = await self._get_conn()
        if not conn:
            return []

        try:
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
        except Exception:
            return []

    async def retry_task(self, task_id: str) -> bool:
        """Retry a failed task by setting it back to pending"""
        conn = await self._get_conn()
        if not conn:
            return False

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
        if not conn:
            return False

        try:
            await conn.execute(
                "UPDATE tasks SET status = 'cancelled' WHERE id = ?",
                (task_id,)
            )
            await conn.commit()
            return True
        except Exception:
            return False

    async def get_memory_stats(self) -> Dict[str, int]:
        """Get memory system statistics"""
        stats = {"tasks": 0, "objectives": 0, "decisions": 0, "questions": 0, "projects": 0}

        conn = await self._get_conn()
        if not conn:
            return stats

        try:
            tables = ["tasks", "objectives", "questions", "projects"]
            for table in tables:
                try:
                    async with conn.execute(f"SELECT COUNT(*) as cnt FROM {table}") as cursor:
                        row = await cursor.fetchone()
                        stats[table] = row["cnt"] if row else 0
                except Exception:
                    pass
        except Exception:
            pass
        return stats

    async def get_project_info(self, project_name: str) -> Optional[ProjectInfo]:
        """Get project info from database by name"""
        conn = await self._get_conn()
        if not conn:
            return None

        try:
            query = """
                SELECT p.id, p.name, p.local_path, p.status, p.created_at, p.objective_id,
                       COUNT(t.id) as task_count,
                       SUM(CASE WHEN t.status = 'completed' THEN 1 ELSE 0 END) as completed_tasks
                FROM projects p
                LEFT JOIN tasks t ON t.objective_id = p.objective_id
                WHERE p.name = ?
                GROUP BY p.id
            """

            async with conn.execute(query, (project_name,)) as cursor:
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

    async def get_project_tasks(self, project_name: str) -> List[TaskInfo]:
        """Get tasks associated with a project"""
        conn = await self._get_conn()
        if not conn:
            return []

        try:
            # First try to find by project name in task descriptions
            query = """
                SELECT id, title, status, worker_id, priority,
                       created_at, completed_at, description, result,
                       objective_id, error, retry_count
                FROM tasks
                WHERE description LIKE ? OR title LIKE ?
                ORDER BY priority DESC, created_at DESC
                LIMIT 50
            """
            pattern = f"%{project_name}%"

            tasks = []
            async with conn.execute(query, (pattern, pattern)) as cursor:
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
        except Exception:
            return []

    async def get_objectives_with_projects(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get objectives with project info for dashboard"""
        conn = await self._get_conn()
        if not conn:
            return []

        try:
            query = """
                SELECT o.id, o.content, o.status, o.priority, o.created_at,
                       p.name as project_name, p.local_path as project_path,
                       COUNT(t.id) as task_count,
                       SUM(CASE WHEN t.status = 'completed' THEN 1 ELSE 0 END) as completed_tasks,
                       SUM(CASE WHEN t.status = 'failed' THEN 1 ELSE 0 END) as failed_tasks,
                       SUM(CASE WHEN t.status IN ('in_progress', 'assigned') THEN 1 ELSE 0 END) as running_tasks
                FROM objectives o
                LEFT JOIN projects p ON p.objective_id = o.id
                LEFT JOIN tasks t ON t.objective_id = o.id
                GROUP BY o.id
                ORDER BY o.created_at DESC
                LIMIT ?
            """

            results = []
            async with conn.execute(query, (limit,)) as cursor:
                async for row in cursor:
                    results.append({
                        "id": row["id"],
                        "content": row["content"],
                        "status": row["status"],
                        "priority": row["priority"],
                        "created_at": row["created_at"],
                        "project_name": row["project_name"],
                        "project_path": row["project_path"],
                        "task_count": row["task_count"] or 0,
                        "completed_tasks": row["completed_tasks"] or 0,
                        "failed_tasks": row["failed_tasks"] or 0,
                        "running_tasks": row["running_tasks"] or 0,
                    })
            return results
        except Exception:
            return []
