# =============================================================================
# CLOPUS v3 Base Interface Adapter
# =============================================================================
"""
Abstract base class for interface adapters.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional


class InterfaceAdapter(ABC):
    """Base class for CLOPUS interface adapters."""

    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self._running = False

    @abstractmethod
    async def start(self) -> None:
        """Start the interface adapter."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the interface adapter."""
        pass

    @abstractmethod
    async def send_status(self, status: Dict) -> None:
        """Send status update to interface."""
        pass

    @abstractmethod
    async def send_question(self, question_id: str, question: str) -> None:
        """Send a question to the user."""
        pass

    @abstractmethod
    async def send_notification(self, message: str, level: str = "info") -> None:
        """Send a notification."""
        pass

    async def receive_objective(self, content: str) -> str:
        """Receive and process a new objective."""
        objective = await self.orchestrator.memory.create_objective(content)
        return objective.id

    async def receive_answer(self, question_id: str, answer: str) -> None:
        """Receive an answer to a question."""
        await self.orchestrator.memory.answer(question_id, answer)
