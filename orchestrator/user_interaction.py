# =============================================================================
# CLOPUS v3 User Interaction Handler
# =============================================================================
"""
Handles user questions, answers, and clarifications.
Manages the bidirectional communication with users.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger("clopus.user_interaction")


class UserInteractionHandler:
    """Handle user interactions and clarifications."""

    def __init__(
        self,
        memory_client,
        confidence_engine,
        questions_dir: Path,
        answers_dir: Path
    ):
        self.memory = memory_client
        self.confidence = confidence_engine
        self.questions_dir = questions_dir
        self.answers_dir = answers_dir

        # Ensure directories exist
        self.questions_dir.mkdir(parents=True, exist_ok=True)
        self.answers_dir.mkdir(parents=True, exist_ok=True)

        # Pending questions waiting for answers
        self._pending: Dict[str, Dict] = {}
        self._answer_callbacks: Dict[str, asyncio.Future] = {}

    async def ask_clarification(
        self,
        question: str,
        context: Optional[str] = None,
        task_id: Optional[str] = None,
        objective_id: Optional[str] = None,
        confidence_score: Optional[float] = None,
        options: Optional[List[str]] = None,
        timeout: Optional[float] = None
    ) -> Optional[str]:
        """Ask user for clarification and wait for response."""
        # Create question in memory
        question_id = await self.memory.ask_user(
            question=question,
            context=context,
            task_id=task_id,
            objective_id=objective_id,
            confidence_score=confidence_score
        )

        # Write question file
        await self._write_question_file(
            question_id=question_id,
            question=question,
            context=context,
            options=options,
            confidence_score=confidence_score
        )

        # Store pending question
        self._pending[question_id] = {
            "question": question,
            "context": context,
            "task_id": task_id,
            "objective_id": objective_id,
            "asked_at": datetime.now(),
            "options": options
        }

        logger.info(f"Asked question {question_id}: {question[:50]}...")

        # Wait for answer if timeout specified
        if timeout:
            answer = await self._wait_for_answer(question_id, timeout)
            return answer

        return question_id

    async def _write_question_file(
        self,
        question_id: str,
        question: str,
        context: Optional[str],
        options: Optional[List[str]],
        confidence_score: Optional[float]
    ) -> None:
        """Write question to file for user."""
        lines = [
            "# Question",
            "",
            question,
            ""
        ]

        if context:
            lines.extend([
                "## Context",
                "",
                context,
                ""
            ])

        if options:
            lines.extend([
                "## Options",
                ""
            ])
            for i, option in enumerate(options, 1):
                lines.append(f"{i}. {option}")
            lines.append("")

        if confidence_score is not None:
            lines.extend([
                "---",
                f"Confidence: {confidence_score:.0%}",
                ""
            ])

        lines.extend([
            "---",
            f"Question ID: {question_id}",
            f"Asked at: {datetime.now().isoformat()}",
            "",
            "To answer, create a file in the answers directory with this ID as the filename."
        ])

        question_file = self.questions_dir / f"{question_id}.md"
        question_file.write_text("\n".join(lines))

    async def _wait_for_answer(
        self,
        question_id: str,
        timeout: float
    ) -> Optional[str]:
        """Wait for an answer to a specific question."""
        # Create a future for this question
        future = asyncio.get_event_loop().create_future()
        self._answer_callbacks[question_id] = future

        try:
            answer = await asyncio.wait_for(future, timeout=timeout)
            return answer
        except asyncio.TimeoutError:
            logger.warning(f"Question {question_id} timed out after {timeout}s")
            # Mark as timed out
            await self.memory.short_term.answer_question(question_id, "[TIMEOUT]")
            return None
        finally:
            self._answer_callbacks.pop(question_id, None)

    async def receive_answer(self, question_id: str, answer: str) -> None:
        """Process a received answer."""
        if question_id not in self._pending:
            logger.warning(f"Received answer for unknown question: {question_id}")
            return

        # Record answer in memory
        await self.memory.answer(question_id, answer)

        # Remove question file
        question_file = self.questions_dir / f"{question_id}.md"
        if question_file.exists():
            question_file.unlink()

        # Resolve any waiting futures
        if question_id in self._answer_callbacks:
            future = self._answer_callbacks[question_id]
            if not future.done():
                future.set_result(answer)

        # Remove from pending
        self._pending.pop(question_id, None)

        logger.info(f"Received answer for {question_id}")

    async def get_pending_questions(self) -> List[Dict]:
        """Get all pending questions."""
        return list(self._pending.values())

    async def check_for_answers(self) -> List[str]:
        """Check for new answer files and process them."""
        processed = []

        for answer_file in self.answers_dir.glob("*.md"):
            question_id = answer_file.stem

            if question_id in self._pending:
                # Read answer
                content = answer_file.read_text()

                # Extract answer text (skip markdown headers and metadata)
                lines = content.strip().split("\n")
                answer_lines = []
                for line in lines:
                    if not line.startswith("#") and not line.startswith("---"):
                        answer_lines.append(line)

                answer = "\n".join(answer_lines).strip()

                if answer:
                    await self.receive_answer(question_id, answer)
                    processed.append(question_id)

                # Remove answer file
                answer_file.unlink()

        return processed

    async def ask_choice(
        self,
        question: str,
        options: List[str],
        context: Optional[str] = None,
        default: Optional[int] = None,
        task_id: Optional[str] = None,
        objective_id: Optional[str] = None
    ) -> Optional[int]:
        """Ask user to choose from options."""
        formatted_question = question + "\n\nOptions:\n"
        for i, option in enumerate(options, 1):
            formatted_question += f"  {i}. {option}\n"

        if default is not None:
            formatted_question += f"\nDefault: {default + 1}"

        question_id = await self.ask_clarification(
            question=formatted_question,
            context=context,
            task_id=task_id,
            objective_id=objective_id,
            options=options
        )

        # Note: For async operation, return question_id
        # Caller should wait for answer separately
        return None

    async def ask_confirmation(
        self,
        question: str,
        context: Optional[str] = None,
        task_id: Optional[str] = None,
        objective_id: Optional[str] = None,
        timeout: float = 300
    ) -> Optional[bool]:
        """Ask user for yes/no confirmation."""
        answer = await self.ask_clarification(
            question=f"{question}\n\nPlease answer 'yes' or 'no'.",
            context=context,
            task_id=task_id,
            objective_id=objective_id,
            options=["Yes", "No"],
            timeout=timeout
        )

        if answer:
            return answer.lower().strip() in ("yes", "y", "true", "1")
        return None

    async def notify(
        self,
        message: str,
        level: str = "info"
    ) -> None:
        """Send a notification to the user (non-blocking)."""
        await self.memory.short_term.log_activity(
            source="notification",
            action=level,
            details={"message": message}
        )

        # Could also write to a notifications file
        logger.log(
            getattr(logging, level.upper(), logging.INFO),
            f"[NOTIFICATION] {message}"
        )

    async def report_progress(
        self,
        objective_id: str,
        message: str,
        percentage: Optional[float] = None
    ) -> None:
        """Report progress to user."""
        progress_msg = message
        if percentage is not None:
            progress_msg = f"[{percentage:.0%}] {message}"

        await self.notify(progress_msg, level="info")

    async def report_completion(
        self,
        objective_id: str,
        summary: str,
        output_path: Optional[str] = None
    ) -> None:
        """Report objective completion to user."""
        message = f"Completed: {summary}"
        if output_path:
            message += f"\nOutput: {output_path}"

        await self.notify(message, level="info")

        # Could trigger additional actions like email notification
