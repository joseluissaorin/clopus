"""
CLOPUS Test Configuration and Fixtures
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================================================
# Async Event Loop
# ============================================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Environment Setup
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    os.environ.setdefault("CLOPUS_ENV", "test")
    os.environ.setdefault("CLOPUS_LOG_LEVEL", "DEBUG")
    os.environ.setdefault("SQLITE_PATH", ":memory:")
    os.environ.setdefault("CHROMADB_PATH", "/tmp/clopus_test_chromadb")
    yield
    # Cleanup


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest_asyncio.fixture
async def memory_client():
    """Create a test memory client."""
    from orchestrator.memory_client import MemoryClient

    client = MemoryClient()
    await client.initialize()
    yield client
    await client.close()


@pytest_asyncio.fixture
async def short_term_memory():
    """Create a test short-term memory instance."""
    from memory.short_term import ShortTermMemory

    memory = ShortTermMemory(":memory:")
    await memory.initialize()
    yield memory
    await memory.close()


# ============================================================================
# Orchestrator Fixtures
# ============================================================================

@pytest_asyncio.fixture
async def config():
    """Create a test configuration."""
    from orchestrator.config import Config

    return Config(
        workers={"count": 2, "heartbeat_interval": 5, "task_timeout": 60},
        memory={"sqlite_path": ":memory:", "chromadb_path": "/tmp/test_chromadb"},
        validation={"strict_mode": True},
        confidence={"threshold": 0.7},
    )


@pytest_asyncio.fixture
async def task_planner(config):
    """Create a test task planner."""
    from orchestrator.task_planner import TaskPlanner

    return TaskPlanner(config)


@pytest_asyncio.fixture
async def confidence_engine(short_term_memory):
    """Create a test confidence engine."""
    from orchestrator.confidence_engine import ConfidenceEngine

    return ConfidenceEngine(short_term_memory)


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_worker():
    """Create a mock worker."""
    from unittest.mock import AsyncMock, MagicMock

    worker = MagicMock()
    worker.id = "worker-test-1"
    worker.role = "coder"
    worker.status = "idle"
    worker.execute_task = AsyncMock(return_value={"success": True, "output": "test"})
    return worker


@pytest.fixture
def sample_objective():
    """Create a sample objective for testing."""
    return {
        "id": "obj_test_123",
        "description": "Build a simple todo app with React",
        "status": "pending",
        "created_at": "2024-01-15T10:00:00Z",
    }


@pytest.fixture
def sample_task():
    """Create a sample task for testing."""
    return {
        "id": "task_test_123",
        "objective_id": "obj_test_123",
        "description": "Set up React project with Vite",
        "type": "setup",
        "status": "pending",
        "priority": 1,
        "dependencies": [],
    }


# ============================================================================
# Validation Fixtures
# ============================================================================

@pytest.fixture
def sample_project_path(tmp_path):
    """Create a sample project for validation testing."""
    project = tmp_path / "test_project"
    project.mkdir()

    # Create package.json
    (project / "package.json").write_text("""
{
  "name": "test-project",
  "version": "1.0.0",
  "scripts": {
    "build": "echo 'build'",
    "test": "echo 'test'"
  }
}
""")

    # Create src directory
    src = project / "src"
    src.mkdir()

    # Create a simple TypeScript file
    (src / "index.ts").write_text("""
export function hello(name: string): string {
  return `Hello, ${name}!`;
}
""")

    return project
