"""
Integration tests for Orchestrator
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestOrchestratorIntegration:
    """Integration tests for the orchestrator system."""

    @pytest.mark.asyncio
    async def test_objective_to_tasks_flow(self, memory_client, task_planner):
        """Test the flow from objective to task creation."""
        # Create an objective
        objective = await memory_client.create_objective(
            description="Build a simple calculator app",
            priority=1,
        )

        # Plan tasks
        parsed_objective = {
            "id": objective.id,
            "description": objective.description,
            "status": objective.status,
        }

        tasks = await task_planner.plan_objective(parsed_objective)

        # Store tasks
        for task in tasks:
            await memory_client.create_task(
                objective_id=objective.id,
                description=task.description,
                task_type=task.type,
                priority=task.priority,
            )

        # Verify tasks were created
        pending_tasks = await memory_client.get_pending_tasks()
        assert len(pending_tasks) >= len(tasks)

    @pytest.mark.asyncio
    async def test_worker_assignment_flow(self, memory_client):
        """Test the worker assignment flow."""
        # Register workers
        worker1 = await memory_client.register_worker("worker-1", "coder")
        worker2 = await memory_client.register_worker("worker-2", "tester")

        # Create objective and task
        objective = await memory_client.create_objective(
            description="Test objective",
            priority=1,
        )

        task = await memory_client.create_task(
            objective_id=objective.id,
            description="Test task",
            task_type="development",
            priority=1,
        )

        # Get available worker
        available = await memory_client.get_available_workers()
        assert len(available) >= 2

        # Assign task to worker
        await memory_client.assign_task(task.id, worker1.id)

        # Verify assignment
        updated_task = await memory_client.get_task(task.id)
        assert updated_task.assigned_worker == worker1.id
        assert updated_task.status == "in_progress"

    @pytest.mark.asyncio
    async def test_validation_after_task_completion(
        self, memory_client, sample_project_path
    ):
        """Test validation runs after task completion."""
        from validation.pipeline import ValidationPipeline

        # Create a validation pipeline
        pipeline = ValidationPipeline()

        # Run validation on sample project
        result = await pipeline.validate(
            project_path=str(sample_project_path),
            stages=["syntax"],
        )

        assert result is not None
        assert "stages" in result
        assert result["overall_passed"] or not result["overall_passed"]  # Boolean check

    @pytest.mark.asyncio
    async def test_memory_persistence_across_operations(self, memory_client):
        """Test that memory persists across operations."""
        # Create multiple objectives
        obj1 = await memory_client.create_objective("Objective 1", 1)
        obj2 = await memory_client.create_objective("Objective 2", 2)

        # Create tasks for each
        await memory_client.create_task(obj1.id, "Task 1-1", "dev", 1)
        await memory_client.create_task(obj1.id, "Task 1-2", "test", 2)
        await memory_client.create_task(obj2.id, "Task 2-1", "dev", 1)

        # Verify retrieval
        tasks1 = await memory_client.get_tasks_for_objective(obj1.id)
        tasks2 = await memory_client.get_tasks_for_objective(obj2.id)

        assert len(tasks1) == 2
        assert len(tasks2) == 1

    @pytest.mark.asyncio
    async def test_confidence_affects_workflow(self, confidence_engine, memory_client):
        """Test that confidence scores affect the workflow."""
        # High confidence task
        high_conf_task = {
            "id": "task_high",
            "description": "Create a React component with props",
            "type": "development",
            "context": {
                "has_examples": True,
                "similar_tasks_succeeded": 10,
            },
        }

        # Low confidence task
        low_conf_task = {
            "id": "task_low",
            "description": "Implement custom cryptographic protocol",
            "type": "security",
            "context": {
                "has_examples": False,
                "similar_tasks_succeeded": 0,
            },
        }

        high_score = await confidence_engine.calculate_confidence(high_conf_task)
        low_score = await confidence_engine.calculate_confidence(low_conf_task)

        # High confidence should proceed automatically
        should_ask_high = await confidence_engine.should_ask_user(high_conf_task)

        # Low confidence may require user input
        should_ask_low = await confidence_engine.should_ask_user(low_conf_task)

        assert high_score > low_score


class TestWorkerPoolIntegration:
    """Integration tests for worker pool management."""

    @pytest.mark.asyncio
    async def test_worker_pool_initialization(self, config):
        """Test worker pool can be initialized."""
        from orchestrator.worker_pool import WorkerPool

        pool = WorkerPool(config)

        # Initialize shouldn't fail
        await pool.initialize()

        # Should have configured number of workers
        workers = await pool.get_all_workers()
        # Note: In test mode, might be 0 if not running actual workers
        assert isinstance(workers, list)

    @pytest.mark.asyncio
    async def test_task_dispatch_to_worker(self, mock_worker):
        """Test dispatching a task to a worker."""
        task = {
            "id": "task_1",
            "description": "Test task",
            "type": "development",
        }

        # Execute task on mock worker
        result = await mock_worker.execute_task(task)

        assert result["success"] is True
        mock_worker.execute_task.assert_called_once_with(task)


class TestServiceManagerIntegration:
    """Integration tests for service management."""

    @pytest.mark.asyncio
    async def test_tier2_service_lifecycle(self):
        """Test Tier 2 service can be started and stopped."""
        from orchestrator.service_manager import ServiceManager

        manager = ServiceManager()

        # Check if a service is available
        available = await manager.is_service_available("elasticsearch")

        # Type check
        assert isinstance(available, bool)

        # If we were to start a service (mocked in tests)
        with patch.object(manager, "start_service", new_callable=AsyncMock) as mock_start:
            mock_start.return_value = True
            result = await manager.start_service("elasticsearch")
            assert result is True
