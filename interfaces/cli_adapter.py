# =============================================================================
# CLOPUS v3 CLI Adapter
# =============================================================================
"""
Interactive CLI interface for CLOPUS.
"""

import asyncio
import sys
from typing import Dict
from .base import InterfaceAdapter


class CLIAdapter(InterfaceAdapter):
    """Interactive CLI adapter."""

    def __init__(self, orchestrator):
        super().__init__(orchestrator)
        self._input_queue = asyncio.Queue()

    async def start(self) -> None:
        """Start CLI interface."""
        self._running = True
        print("\n=== CLOPUS Interactive CLI ===")
        print("Type 'help' for commands, 'quit' to exit\n")

        # Start input reader
        asyncio.create_task(self._read_input())

        # Process input
        while self._running:
            try:
                line = await asyncio.wait_for(
                    self._input_queue.get(),
                    timeout=0.5
                )
                await self._process_command(line)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

    async def stop(self) -> None:
        """Stop CLI interface."""
        self._running = False
        print("\nGoodbye!")

    async def _read_input(self) -> None:
        """Read input from stdin."""
        loop = asyncio.get_event_loop()
        while self._running:
            try:
                line = await loop.run_in_executor(
                    None,
                    lambda: input("clopus> ")
                )
                await self._input_queue.put(line)
            except EOFError:
                break

    async def _process_command(self, line: str) -> None:
        """Process a CLI command."""
        parts = line.strip().split(maxsplit=1)
        if not parts:
            return

        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if command == "help":
            self._show_help()
        elif command == "quit" or command == "exit":
            self._running = False
        elif command == "objective" or command == "obj":
            await self._add_objective(args)
        elif command == "status":
            await self._show_status()
        elif command == "workers":
            await self._show_workers()
        elif command == "questions":
            await self._show_questions()
        elif command == "answer":
            await self._answer_question(args)
        else:
            print(f"Unknown command: {command}")
            print("Type 'help' for available commands")

    def _show_help(self) -> None:
        """Show help text."""
        print("""
Available commands:
  objective <text>    Add a new objective
  status              Show system status
  workers             Show worker status
  questions           Show pending questions
  answer <id> <text>  Answer a question
  help                Show this help
  quit                Exit CLOPUS
""")

    async def _add_objective(self, content: str) -> None:
        """Add a new objective."""
        if not content:
            print("Usage: objective <description>")
            return

        objective_id = await self.receive_objective(content)
        print(f"Objective created: {objective_id[:8]}...")

    async def _show_status(self) -> None:
        """Show system status."""
        if self.orchestrator.status_reporter:
            summary = await self.orchestrator.status_reporter.get_summary()
            print(summary)
        else:
            print("Status reporter not available")

    async def _show_workers(self) -> None:
        """Show worker status."""
        if self.orchestrator.worker_pool:
            statuses = await self.orchestrator.worker_pool.get_all_status()
            print("\nWorker Status:")
            for status in statuses:
                print(f"  Worker {status['id']} ({status.get('role', '?')}): {status.get('status', '?')}")
        else:
            print("Worker pool not available")

    async def _show_questions(self) -> None:
        """Show pending questions."""
        questions = await self.orchestrator.memory.get_pending_questions()
        if not questions:
            print("No pending questions")
            return

        print("\nPending Questions:")
        for q in questions:
            print(f"  [{q['id'][:8]}...] {q['question'][:60]}...")

    async def _answer_question(self, args: str) -> None:
        """Answer a question."""
        parts = args.split(maxsplit=1)
        if len(parts) < 2:
            print("Usage: answer <question_id> <answer_text>")
            return

        question_id, answer = parts
        await self.receive_answer(question_id, answer)
        print(f"Answer recorded for {question_id[:8]}...")

    async def send_status(self, status: Dict) -> None:
        """Send status update."""
        # In CLI, we just print important updates
        if status.get("type") == "objective_completed":
            print(f"\n[COMPLETED] {status.get('message', '')}")
        elif status.get("type") == "error":
            print(f"\n[ERROR] {status.get('message', '')}")

    async def send_question(self, question_id: str, question: str) -> None:
        """Send a question to user."""
        print(f"\n[QUESTION] {question}")
        print(f"  Answer with: answer {question_id[:8]} <your answer>")

    async def send_notification(self, message: str, level: str = "info") -> None:
        """Send notification."""
        prefix = {"info": "INFO", "warning": "WARN", "error": "ERROR"}.get(level, "INFO")
        print(f"[{prefix}] {message}")
