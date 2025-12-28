# =============================================================================
# CLOPUS v3 Memory Client
# =============================================================================
"""
Unified memory interface for the orchestrator.
Combines short-term (SQLite) and long-term (ChromaDB) memory access.
"""

import asyncio
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from memory import ShortTermMemory, LongTermMemory, EmbeddingEngine
from memory.short_term import (
    Objective, Task, Worker,
    ObjectiveStatus, TaskStatus, WorkerStatus, ValidationStage
)
from memory.long_term import Memory, MemoryType


@dataclass
class MemorySearchResult:
    """Combined search result from both memory systems."""
    short_term: List[Dict]
    long_term: List[Memory]
    total_count: int


class MemoryClient:
    """Unified memory access for CLOPUS orchestrator."""

    def __init__(
        self,
        sqlite_path: str = "/app/data/sqlite/clopus.db",
        chromadb_host: str = "chromadb",
        chromadb_port: int = 8000
    ):
        self.embedding_engine = EmbeddingEngine()
        self.short_term = ShortTermMemory(sqlite_path)
        self.long_term = LongTermMemory(
            chromadb_host,
            chromadb_port,
            self.embedding_engine
        )
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize both memory systems."""
        if not self._initialized:
            await asyncio.gather(
                self.short_term.initialize(),
                self.long_term.initialize()
            )
            self._initialized = True

    async def close(self) -> None:
        """Close connections."""
        await self.short_term.close()

    # =========================================================================
    # OBJECTIVE OPERATIONS
    # =========================================================================

    async def create_objective(
        self,
        content: str,
        priority: int = 5,
        metadata: Optional[Dict] = None
    ) -> Objective:
        """Create a new objective."""
        objective = await self.short_term.create_objective(content, priority, metadata)

        # Log activity
        await self.short_term.log_activity(
            source="orchestrator",
            action="objective_created",
            details={"content": content[:100], "priority": priority},
            objective_id=objective.id
        )

        return objective

    async def get_next_objective(self) -> Optional[Objective]:
        """Get the next pending objective."""
        objectives = await self.short_term.get_pending_objectives()
        return objectives[0] if objectives else None

    async def start_objective(self, objective_id: str) -> None:
        """Mark objective as in progress."""
        await self.short_term.update_objective_status(
            objective_id,
            ObjectiveStatus.IN_PROGRESS
        )
        await self.short_term.log_activity(
            source="orchestrator",
            action="objective_started",
            objective_id=objective_id
        )

    async def complete_objective(
        self,
        objective_id: str,
        success: bool = True,
        lessons: Optional[List[str]] = None
    ) -> None:
        """Complete an objective and extract learnings."""
        status = ObjectiveStatus.COMPLETED if success else ObjectiveStatus.FAILED

        await self.short_term.update_objective_status(objective_id, status)

        # Get objective details for learning
        objective = await self.short_term.get_objective(objective_id)
        if objective and lessons:
            await self.long_term.learn_from_task(
                objective.content,
                {"status": status.value},
                success,
                lessons
            )

        await self.short_term.log_activity(
            source="orchestrator",
            action="objective_completed",
            details={"success": success},
            objective_id=objective_id
        )

    # =========================================================================
    # TASK OPERATIONS
    # =========================================================================

    async def create_tasks(
        self,
        objective_id: str,
        tasks: List[Dict]
    ) -> List[Task]:
        """Create multiple tasks for an objective with deduplication.

        Tasks with the same title that already exist (and are not completed/failed)
        will be skipped to prevent duplicate task creation on orchestrator restart.
        """
        created_tasks = []

        # Get existing tasks for this objective to prevent duplicates
        existing_tasks = await self.short_term.get_tasks_for_objective(objective_id)
        existing_titles = {
            task.title for task in existing_tasks
            if task.status not in (TaskStatus.COMPLETED, TaskStatus.FAILED)
        }

        for task_def in tasks:
            title = task_def["title"]

            # Skip if task with this title already exists (and is not completed/failed)
            if title in existing_titles:
                await self.short_term.log_activity(
                    source="orchestrator",
                    action="task_skipped_duplicate",
                    details={"title": title, "reason": "duplicate"},
                    objective_id=objective_id
                )
                continue

            task = await self.short_term.create_task(
                objective_id=objective_id,
                title=title,
                description=task_def.get("description"),
                priority=task_def.get("priority", 5),
                dependencies=task_def.get("dependencies", []),
                worker_role=task_def.get("worker_role"),
                expected_artifacts=task_def.get("expected_artifacts", [])
            )
            created_tasks.append(task)
            existing_titles.add(title)  # Prevent duplicates within same batch

            await self.short_term.log_activity(
                source="orchestrator",
                action="task_created",
                details={"title": task.title},
                objective_id=objective_id,
                task_id=task.id
            )

        return created_tasks

    async def get_assignable_tasks(self, worker_role: Optional[str] = None) -> List[Task]:
        """Get tasks that can be assigned to workers."""
        pending = await self.short_term.get_pending_tasks(worker_role)

        # Filter out tasks with unmet dependencies
        assignable = []
        for task in pending:
            if not task.dependencies:
                assignable.append(task)
            else:
                # Check if all dependencies are completed
                all_completed = True
                for dep_id in task.dependencies:
                    dep_task = await self.short_term.get_task(dep_id)
                    if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                        all_completed = False
                        break
                if all_completed:
                    assignable.append(task)

        return assignable

    async def assign_task_to_worker(
        self,
        task_id: str,
        worker_id: int,
        worker_role: str
    ) -> None:
        """Assign a task to a worker."""
        await self.short_term.assign_task(task_id, worker_id, worker_role)
        await self.short_term.update_worker_status(
            worker_id,
            WorkerStatus.BUSY,
            task_id
        )

        await self.short_term.log_activity(
            source="orchestrator",
            action="task_assigned",
            details={"worker_id": worker_id, "worker_role": worker_role},
            task_id=task_id,
            worker_id=worker_id
        )

    async def complete_task(
        self,
        task_id: str,
        worker_id: int,
        success: bool,
        result: Optional[Dict] = None,
        error: Optional[str] = None
    ) -> None:
        """Complete a task."""
        status = TaskStatus.COMPLETED if success else TaskStatus.FAILED

        await self.short_term.update_task_status(task_id, status, result, error)
        await self.short_term.update_worker_status(worker_id, WorkerStatus.IDLE)
        await self.short_term.increment_worker_stats(worker_id, success)

        # If failed and can retry
        if not success:
            task = await self.short_term.get_task(task_id)
            if task and task.retry_count < task.max_retries:
                await self.short_term.increment_task_retry(task_id)
                await self.short_term.log_activity(
                    source="orchestrator",
                    action="task_retry_scheduled",
                    details={"retry_count": task.retry_count + 1},
                    task_id=task_id
                )

        await self.short_term.log_activity(
            source="orchestrator",
            action="task_completed" if success else "task_failed",
            details={"result": str(result)[:200] if result else None, "error": error},
            task_id=task_id,
            worker_id=worker_id
        )

    # =========================================================================
    # WORKER OPERATIONS
    # =========================================================================

    async def register_worker(self, worker_id: int, role: str) -> Worker:
        """Register a worker."""
        return await self.short_term.register_worker(worker_id, role)

    async def get_idle_worker(self, preferred_role: Optional[str] = None) -> Optional[Worker]:
        """Get an idle worker, preferring specified role."""
        # First try preferred role
        if preferred_role:
            workers = await self.short_term.get_idle_workers(preferred_role)
            if workers:
                return workers[0]

        # Fall back to any idle worker
        workers = await self.short_term.get_idle_workers()
        return workers[0] if workers else None

    async def heartbeat(self, worker_id: int) -> None:
        """Update worker heartbeat."""
        await self.short_term.worker_heartbeat(worker_id)

    # =========================================================================
    # QUESTION/ANSWER OPERATIONS
    # =========================================================================

    async def ask_user(
        self,
        question: str,
        context: Optional[str] = None,
        task_id: Optional[str] = None,
        objective_id: Optional[str] = None,
        confidence_score: Optional[float] = None
    ) -> str:
        """Create a question for the user."""
        question_id = await self.short_term.create_question(
            question, context, task_id, objective_id, confidence_score
        )

        await self.short_term.log_activity(
            source="orchestrator",
            action="question_asked",
            details={"question": question[:200], "confidence": confidence_score},
            task_id=task_id,
            objective_id=objective_id
        )

        return question_id

    async def get_pending_questions(self) -> List[Dict]:
        """Get all pending questions."""
        return await self.short_term.get_pending_questions()

    async def answer(self, question_id: str, answer: str) -> Optional[str]:
        """Record an answer to a question. Returns objective_id if re-queued."""
        return await self.short_term.answer_question(question_id, answer)

    # =========================================================================
    # DECISION TRACKING
    # =========================================================================

    async def record_decision(
        self,
        decision_type: str,
        options: List[str],
        chosen: str,
        confidence: float,
        reasoning: Optional[str] = None,
        task_id: Optional[str] = None
    ) -> str:
        """Record a decision for learning."""
        decision_id = await self.short_term.record_decision(
            decision_type, options, chosen, confidence, reasoning, task_id
        )

        # Store in long-term memory for pattern learning
        await self.long_term.store_decision(
            decision=f"{decision_type}: {chosen}",
            reasoning=reasoning or "No reasoning provided",
            outcome="pending",
            context=f"Options: {', '.join(options)}",
            tags=["automated", decision_type]
        )

        return decision_id

    async def update_decision_outcome(self, decision_id: str, success: bool) -> None:
        """Update decision outcome for learning."""
        outcome = "success" if success else "failure"
        await self.short_term.update_decision_outcome(decision_id, outcome)

    # =========================================================================
    # CONTEXT & SEARCH
    # =========================================================================

    async def get_relevant_context(
        self,
        query: str,
        include_short_term: bool = True,
        include_long_term: bool = True,
        n_results: int = 5
    ) -> str:
        """Get relevant context for a task or decision."""
        context_parts = []

        if include_long_term:
            long_term_context = await self.long_term.get_relevant_context(query, n_results)
            if long_term_context:
                context_parts.append(long_term_context)

        if include_short_term:
            # Get recent activity related to query
            recent = await self.short_term.get_recent_activity(limit=20)
            if recent:
                activity_lines = []
                for item in recent[:5]:
                    activity_lines.append(f"- {item['action']}: {item.get('details', '')}")
                if activity_lines:
                    context_parts.append("Recent activity:\n" + "\n".join(activity_lines))

        return "\n\n".join(context_parts)

    async def search_memories(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        n_results: int = 10
    ) -> List[Memory]:
        """Search long-term memories."""
        return await self.long_term.search(query, memory_type, n_results)

    # =========================================================================
    # LEARNING
    # =========================================================================

    async def store_learning(
        self,
        content: str,
        task_id: Optional[str] = None,
        objective_id: Optional[str] = None,
        outcome: str = "success",
        tags: Optional[List[str]] = None
    ) -> str:
        """Store a learning."""
        return await self.long_term.store_learning(
            content, task_id, objective_id, outcome, tags
        )

    async def store_error_fix(
        self,
        error_message: str,
        context: str,
        fix: str,
        language: Optional[str] = None
    ) -> str:
        """Store an error fix for future reference."""
        return await self.long_term.store_error_fix(
            error_message, context, fix, language
        )

    async def find_similar_errors(
        self,
        error_message: str,
        language: Optional[str] = None,
        n_results: int = 3
    ) -> List[Memory]:
        """Find similar past errors and their fixes."""
        return await self.long_term.search_error_fixes(
            error_message, language, n_results
        )

    # =========================================================================
    # STATE MANAGEMENT
    # =========================================================================

    async def set_state(self, key: str, value: Any) -> None:
        """Set session state."""
        await self.short_term.set_state(key, value)

    async def get_state(self, key: str, default: Any = None) -> Any:
        """Get session state."""
        return await self.short_term.get_state(key, default)

    # =========================================================================
    # ACTIVITY LOGGING
    # =========================================================================

    async def log_activity(
        self,
        source: str,
        action: str,
        details: Optional[Dict] = None,
        objective_id: Optional[str] = None,
        task_id: Optional[str] = None,
        worker_id: Optional[int] = None
    ) -> None:
        """Log an activity to short-term memory."""
        await self.short_term.log_activity(
            source=source,
            action=action,
            details=details,
            objective_id=objective_id,
            task_id=task_id,
            worker_id=worker_id
        )

    # =========================================================================
    # STATISTICS
    # =========================================================================

    async def get_statistics(self) -> Dict:
        """Get memory statistics."""
        return {
            "long_term_memories": await self.long_term.count(),
            "embedding_cache_size": len(self.embedding_engine._cache)
        }
