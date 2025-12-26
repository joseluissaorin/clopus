"""
Unit tests for Memory System
"""

import pytest
from memory.short_term import ShortTermMemory, Objective, Task, Worker


class TestShortTermMemory:
    """Tests for ShortTermMemory class."""

    @pytest.mark.asyncio
    async def test_create_objective(self, short_term_memory):
        """Test creating a new objective."""
        objective = await short_term_memory.create_objective(
            description="Build a todo app",
            priority=1,
        )

        assert objective.id is not None
        assert objective.description == "Build a todo app"
        assert objective.status == "pending"
        assert objective.priority == 1

    @pytest.mark.asyncio
    async def test_get_objective(self, short_term_memory):
        """Test retrieving an objective."""
        created = await short_term_memory.create_objective(
            description="Test objective",
            priority=1,
        )

        retrieved = await short_term_memory.get_objective(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.description == created.description

    @pytest.mark.asyncio
    async def test_update_objective_status(self, short_term_memory):
        """Test updating objective status."""
        objective = await short_term_memory.create_objective(
            description="Test objective",
            priority=1,
        )

        await short_term_memory.update_objective_status(objective.id, "in_progress")

        updated = await short_term_memory.get_objective(objective.id)
        assert updated.status == "in_progress"

    @pytest.mark.asyncio
    async def test_create_task(self, short_term_memory):
        """Test creating a task."""
        objective = await short_term_memory.create_objective(
            description="Test objective",
            priority=1,
        )

        task = await short_term_memory.create_task(
            objective_id=objective.id,
            description="Test task",
            task_type="development",
            priority=1,
        )

        assert task.id is not None
        assert task.objective_id == objective.id
        assert task.description == "Test task"
        assert task.status == "pending"

    @pytest.mark.asyncio
    async def test_get_pending_tasks(self, short_term_memory):
        """Test getting pending tasks."""
        objective = await short_term_memory.create_objective(
            description="Test objective",
            priority=1,
        )

        await short_term_memory.create_task(
            objective_id=objective.id,
            description="Task 1",
            task_type="development",
            priority=1,
        )

        await short_term_memory.create_task(
            objective_id=objective.id,
            description="Task 2",
            task_type="testing",
            priority=2,
        )

        pending = await short_term_memory.get_pending_tasks()

        assert len(pending) >= 2
        assert all(t.status == "pending" for t in pending)

    @pytest.mark.asyncio
    async def test_assign_task_to_worker(self, short_term_memory):
        """Test assigning a task to a worker."""
        objective = await short_term_memory.create_objective(
            description="Test",
            priority=1,
        )

        task = await short_term_memory.create_task(
            objective_id=objective.id,
            description="Test task",
            task_type="development",
            priority=1,
        )

        await short_term_memory.assign_task(task.id, "worker-1")

        updated = await short_term_memory.get_task(task.id)
        assert updated.assigned_worker == "worker-1"
        assert updated.status == "in_progress"

    @pytest.mark.asyncio
    async def test_register_worker(self, short_term_memory):
        """Test registering a worker."""
        worker = await short_term_memory.register_worker(
            worker_id="worker-1",
            role="coder",
        )

        assert worker.id == "worker-1"
        assert worker.role == "coder"
        assert worker.status == "idle"

    @pytest.mark.asyncio
    async def test_get_available_workers(self, short_term_memory):
        """Test getting available workers."""
        await short_term_memory.register_worker("worker-1", "coder")
        await short_term_memory.register_worker("worker-2", "tester")

        available = await short_term_memory.get_available_workers()

        assert len(available) >= 2
        assert all(w.status == "idle" for w in available)


class TestObjectiveDataclass:
    """Tests for Objective dataclass."""

    def test_objective_creation(self):
        """Test Objective dataclass."""
        obj = Objective(
            id="obj_1",
            description="Test",
            status="pending",
            priority=1,
            created_at="2024-01-01T00:00:00Z",
        )

        assert obj.id == "obj_1"
        assert obj.description == "Test"


class TestTaskDataclass:
    """Tests for Task dataclass."""

    def test_task_creation(self):
        """Test Task dataclass."""
        task = Task(
            id="task_1",
            objective_id="obj_1",
            description="Test task",
            task_type="development",
            status="pending",
            priority=1,
            created_at="2024-01-01T00:00:00Z",
        )

        assert task.id == "task_1"
        assert task.objective_id == "obj_1"


class TestWorkerDataclass:
    """Tests for Worker dataclass."""

    def test_worker_creation(self):
        """Test Worker dataclass."""
        worker = Worker(
            id="worker-1",
            role="coder",
            status="idle",
            current_task=None,
            last_heartbeat="2024-01-01T00:00:00Z",
        )

        assert worker.id == "worker-1"
        assert worker.role == "coder"
        assert worker.current_task is None
