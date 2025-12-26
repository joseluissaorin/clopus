"""
Unit tests for Task Planner
"""

import pytest
from orchestrator.task_planner import TaskPlanner, PlannedTask


class TestTaskPlanner:
    """Tests for TaskPlanner class."""

    @pytest.fixture
    def planner(self, config):
        return TaskPlanner(config)

    def test_detect_project_type_react(self, planner):
        """Test React project type detection."""
        objective = "Build a React application with TypeScript"
        project_type = planner._detect_project_type(objective)
        assert project_type == "react"

    def test_detect_project_type_python(self, planner):
        """Test Python project type detection."""
        objective = "Create a FastAPI backend with PostgreSQL"
        project_type = planner._detect_project_type(objective)
        assert project_type == "python"

    def test_detect_project_type_nextjs(self, planner):
        """Test Next.js project type detection."""
        objective = "Build a Next.js app with authentication"
        project_type = planner._detect_project_type(objective)
        assert project_type == "nextjs"

    def test_detect_project_type_unknown(self, planner):
        """Test unknown project type defaults to generic."""
        objective = "Do something vague"
        project_type = planner._detect_project_type(objective)
        assert project_type == "generic"

    @pytest.mark.asyncio
    async def test_plan_objective_creates_tasks(self, planner, sample_objective):
        """Test that planning creates appropriate tasks."""
        tasks = await planner.plan_objective(sample_objective)

        assert len(tasks) > 0
        assert all(isinstance(t, PlannedTask) for t in tasks)

    @pytest.mark.asyncio
    async def test_plan_objective_sets_dependencies(self, planner, sample_objective):
        """Test that tasks have proper dependencies."""
        tasks = await planner.plan_objective(sample_objective)

        # First task should have no dependencies
        assert tasks[0].dependencies == []

        # Later tasks may depend on earlier ones
        for i, task in enumerate(tasks[1:], 1):
            for dep in task.dependencies:
                # Dependencies should reference earlier tasks
                dep_indices = [j for j, t in enumerate(tasks) if t.id == dep]
                assert all(idx < i for idx in dep_indices)

    @pytest.mark.asyncio
    async def test_plan_objective_assigns_workers(self, planner, sample_objective):
        """Test that tasks are assigned to appropriate workers."""
        tasks = await planner.plan_objective(sample_objective)

        valid_roles = {"coder", "tester", "reviewer", "researcher", "debugger"}

        for task in tasks:
            if task.assigned_worker:
                assert task.assigned_worker in valid_roles


class TestPlannedTask:
    """Tests for PlannedTask dataclass."""

    def test_task_creation(self):
        """Test basic task creation."""
        task = PlannedTask(
            id="task_1",
            description="Test task",
            type="development",
            priority=1,
            dependencies=[],
        )

        assert task.id == "task_1"
        assert task.description == "Test task"
        assert task.type == "development"
        assert task.priority == 1
        assert task.dependencies == []

    def test_task_with_dependencies(self):
        """Test task with dependencies."""
        task = PlannedTask(
            id="task_2",
            description="Dependent task",
            type="testing",
            priority=2,
            dependencies=["task_1"],
        )

        assert "task_1" in task.dependencies
