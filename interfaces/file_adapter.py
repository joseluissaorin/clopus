# =============================================================================
# CLOPUS v3 File Adapter
# =============================================================================
"""
File-based interface for CLOPUS.
Watches directories for objectives and answers.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Set
from .base import InterfaceAdapter


class FileAdapter(InterfaceAdapter):
    """File-based interface adapter."""

    def __init__(
        self,
        orchestrator,
        objectives_dir: str = "/app/objectives",
        questions_dir: str = "/app/questions",
        answers_dir: str = "/app/answers",
        status_file: str = "/app/ipc/status.json"
    ):
        super().__init__(orchestrator)
        self.objectives_dir = Path(objectives_dir)
        self.questions_dir = Path(questions_dir)
        self.answers_dir = Path(answers_dir)
        self.status_file = Path(status_file)

        # Track processed files
        self._processed_objectives: Set[str] = set()
        self._processed_answers: Set[str] = set()

        # Ensure directories exist
        self.objectives_dir.mkdir(parents=True, exist_ok=True)
        self.questions_dir.mkdir(parents=True, exist_ok=True)
        self.answers_dir.mkdir(parents=True, exist_ok=True)
        self.status_file.parent.mkdir(parents=True, exist_ok=True)

    async def start(self) -> None:
        """Start file watcher."""
        self._running = True

        # Start watching tasks
        await asyncio.gather(
            self._watch_objectives(),
            self._watch_answers(),
            self._update_status_file()
        )

    async def stop(self) -> None:
        """Stop file watcher."""
        self._running = False

    async def _watch_objectives(self) -> None:
        """Watch for new objective files."""
        while self._running:
            try:
                for file in self.objectives_dir.glob("*.md"):
                    if file.name not in self._processed_objectives:
                        await self._process_objective_file(file)
                        self._processed_objectives.add(file.name)

                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                await asyncio.sleep(5)

    async def _process_objective_file(self, file: Path) -> None:
        """Process an objective file."""
        content = file.read_text()

        # Extract objective text (skip markdown headers and metadata)
        lines = content.strip().split("\n")
        objective_lines = []
        in_metadata = False

        for line in lines:
            if line.strip() == "---":
                in_metadata = not in_metadata
                continue
            if in_metadata:
                continue
            if line.startswith("#"):
                continue
            objective_lines.append(line)

        objective_text = "\n".join(objective_lines).strip()

        if objective_text:
            objective_id = await self.receive_objective(objective_text)

            # Move file to processed
            processed_dir = self.objectives_dir / "processed"
            processed_dir.mkdir(exist_ok=True)
            file.rename(processed_dir / file.name)

    async def _watch_answers(self) -> None:
        """Watch for answer files."""
        while self._running:
            try:
                for file in self.answers_dir.glob("*.md"):
                    if file.name not in self._processed_answers:
                        await self._process_answer_file(file)
                        self._processed_answers.add(file.name)

                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                await asyncio.sleep(5)

    async def _process_answer_file(self, file: Path) -> None:
        """Process an answer file."""
        question_id = file.stem
        content = file.read_text()

        # Extract answer text
        lines = content.strip().split("\n")
        answer_lines = []

        for line in lines:
            if line.startswith("#") or line.strip() == "---":
                continue
            answer_lines.append(line)

        answer_text = "\n".join(answer_lines).strip()

        if answer_text:
            await self.receive_answer(question_id, answer_text)
            # Remove answer file
            file.unlink()

    async def _update_status_file(self) -> None:
        """Periodically update status file."""
        while self._running:
            try:
                if self.orchestrator.status_reporter:
                    status = await self.orchestrator.status_reporter.get_status()
                    self.status_file.write_text(
                        json.dumps(status, indent=2, default=str)
                    )
                await asyncio.sleep(2)
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(5)

    async def send_status(self, status: Dict) -> None:
        """Update status file."""
        try:
            existing = {}
            if self.status_file.exists():
                existing = json.loads(self.status_file.read_text())

            existing.update(status)
            existing["updated_at"] = datetime.now().isoformat()

            self.status_file.write_text(json.dumps(existing, indent=2))
        except Exception:
            pass

    async def send_question(self, question_id: str, question: str) -> None:
        """Write question to file."""
        question_file = self.questions_dir / f"{question_id}.md"

        content = f"""# Question

{question}

---
Question ID: {question_id}
Asked at: {datetime.now().isoformat()}

To answer, create a file: {self.answers_dir}/{question_id}.md
"""

        question_file.write_text(content)

    async def send_notification(self, message: str, level: str = "info") -> None:
        """Append notification to log file."""
        log_file = self.status_file.parent / "notifications.log"

        with open(log_file, "a") as f:
            timestamp = datetime.now().isoformat()
            f.write(f"[{timestamp}] [{level.upper()}] {message}\n")
