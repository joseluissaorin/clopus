"""Questions screen - pending questions management"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Header, Footer, Label, Button, DataTable, TextArea
from textual.containers import Horizontal, Vertical, Container
from textual.reactive import reactive
from typing import Optional, List, Dict, Any
import asyncio

from ..services.orchestrator import OrchestratorClient
from ..services.notifications import NotificationService


class QuestionsScreen(Screen):
    """Pending questions management screen"""

    CSS = """
    QuestionsScreen {
        layout: grid;
        grid-size: 2 1;
        grid-gutter: 1;
        padding: 1;
    }

    #question-list {
        column-span: 1;
        border: solid $primary;
        padding: 1;
    }

    #question-answer {
        column-span: 1;
        border: solid $primary;
        padding: 1;
    }

    .panel-title {
        text-style: bold;
        margin-bottom: 1;
    }

    #questions-table {
        height: 1fr;
    }

    #question-content {
        height: auto;
        max-height: 15;
        border: solid $surface;
        padding: 1;
        margin-bottom: 1;
        overflow-y: auto;
    }

    #answer-input {
        height: 8;
        margin-bottom: 1;
    }

    .answer-actions {
        height: 3;
    }

    .answer-actions Button {
        margin-right: 1;
    }

    .quick-answers {
        height: auto;
        margin-top: 1;
    }

    .quick-answers Button {
        margin-right: 1;
        margin-bottom: 1;
    }

    .pending-badge {
        background: $warning;
        color: $background;
        padding: 0 1;
    }
    """

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("escape", "go_back", "Back"),
        ("enter", "submit_answer", "Submit"),
        ("s", "skip_question", "Skip"),
    ]

    selected_question: reactive[Optional[Dict[str, Any]]] = reactive(None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._orchestrator = OrchestratorClient()
        self._notifications = NotificationService()
        self._questions: List[Dict[str, Any]] = []
        self._refresh_task: Optional[asyncio.Task] = None

    def compose(self) -> ComposeResult:
        yield Header()

        with Container(id="question-list"):
            yield Label("Pending Questions", classes="panel-title")
            yield DataTable(id="questions-table")
            with Horizontal(classes="answer-actions"):
                yield Button("Refresh", id="btn-refresh")
                yield Button("Skip All", id="btn-skip-all", variant="error")

        with Container(id="question-answer"):
            yield Label("Answer Question", classes="panel-title")
            yield Static(id="question-content")
            yield Label("Your Answer:", classes="panel-title")
            yield TextArea(id="answer-input")
            with Horizontal(classes="answer-actions"):
                yield Button("Submit", id="btn-submit", variant="primary")
                yield Button("Skip", id="btn-skip")
                yield Button("Escalate", id="btn-escalate", variant="warning")

            yield Label("Quick Answers:", classes="panel-title")
            with Horizontal(classes="quick-answers"):
                yield Button("Yes", id="btn-yes")
                yield Button("No", id="btn-no")
                yield Button("Use default", id="btn-default")
                yield Button("Proceed autonomously", id="btn-autonomous")

        yield Footer()

    async def on_mount(self) -> None:
        """Set up table and start refresh"""
        table = self.query_one("#questions-table", DataTable)
        table.add_columns("ID", "Context", "Age")
        table.cursor_type = "row"

        await self._refresh_questions()
        self._refresh_task = asyncio.create_task(self._refresh_loop())

    async def on_unmount(self) -> None:
        """Stop refresh loop"""
        if self._refresh_task:
            self._refresh_task.cancel()

    async def _refresh_loop(self) -> None:
        """Periodically check for new questions"""
        while True:
            try:
                await asyncio.sleep(5)
                old_count = len(self._questions)
                await self._refresh_questions()
                new_count = len(self._questions)

                if new_count > old_count:
                    await self._notifications.notify_question_pending(
                        f"{new_count - old_count} new question(s) pending"
                    )

            except asyncio.CancelledError:
                break
            except Exception:
                pass

    async def _refresh_questions(self) -> None:
        """Refresh question list"""
        try:
            self._questions = await self._orchestrator.get_pending_questions_from_files()

            table = self.query_one("#questions-table", DataTable)
            table.clear()

            for q in self._questions:
                q_id = q.get("id", "")[:8]
                content = q.get("content", "")
                # Extract context from content (first line usually)
                context = content.split("\n")[0][:30] if content else "Unknown"
                age = self._format_age(q.get("file", ""))

                table.add_row(
                    q_id,
                    context,
                    age,
                    key=q.get("id", ""),
                )

        except Exception:
            pass

    def _format_age(self, filepath: str) -> str:
        """Get file age as relative time"""
        try:
            from pathlib import Path
            from datetime import datetime
            import os

            if not filepath:
                return "Unknown"

            mtime = os.path.getmtime(filepath)
            created = datetime.fromtimestamp(mtime)
            now = datetime.now()
            delta = now - created

            if delta.days > 0:
                return f"{delta.days}d"
            elif delta.seconds > 3600:
                return f"{delta.seconds // 3600}h"
            elif delta.seconds > 60:
                return f"{delta.seconds // 60}m"
            else:
                return "Now"
        except Exception:
            return "Unknown"

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle question selection"""
        if event.row_key:
            question = next(
                (q for q in self._questions if q.get("id") == event.row_key.value),
                None
            )
            if question:
                self.selected_question = question
                self._show_question_content()

    def _show_question_content(self) -> None:
        """Show selected question content"""
        if not self.selected_question:
            return

        content_widget = self.query_one("#question-content", Static)
        content = self.selected_question.get("content", "No content")

        # Parse and format the question
        lines = content.split("\n")
        formatted = []

        for line in lines:
            if line.startswith("# "):
                formatted.append(f"[bold]{line[2:]}[/]")
            elif line.startswith("## "):
                formatted.append(f"\n[dim]{line[3:]}[/]")
            elif line.startswith("- "):
                formatted.append(f"  • {line[2:]}")
            elif line.startswith("Confidence:"):
                formatted.append(f"\n[yellow]{line}[/]")
            else:
                formatted.append(line)

        content_widget.update("\n".join(formatted))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        handlers = {
            "btn-refresh": lambda: asyncio.create_task(self._refresh_questions()),
            "btn-submit": lambda: asyncio.create_task(self._submit_answer()),
            "btn-skip": lambda: asyncio.create_task(self._skip_question()),
            "btn-skip-all": lambda: asyncio.create_task(self._skip_all_questions()),
            "btn-escalate": lambda: asyncio.create_task(self._escalate_question()),
            "btn-yes": lambda: self._quick_answer("Yes"),
            "btn-no": lambda: self._quick_answer("No"),
            "btn-default": lambda: self._quick_answer("Use the default option"),
            "btn-autonomous": lambda: self._quick_answer("Proceed autonomously with your best judgment"),
        }

        handler = handlers.get(event.button.id)
        if handler:
            handler()

    def _quick_answer(self, answer: str) -> None:
        """Set a quick answer"""
        answer_input = self.query_one("#answer-input", TextArea)
        answer_input.text = answer

    async def _submit_answer(self) -> None:
        """Submit answer to selected question"""
        if not self.selected_question:
            self.notify("No question selected", severity="warning")
            return

        answer_input = self.query_one("#answer-input", TextArea)
        answer = answer_input.text.strip()

        if not answer:
            self.notify("Please enter an answer", severity="warning")
            return

        try:
            success = await self._orchestrator.answer_question(
                self.selected_question.get("id", ""),
                answer
            )

            if success:
                self.notify("Answer submitted")
                answer_input.text = ""
                await self._refresh_questions()
            else:
                self.notify("Failed to submit answer", severity="error")

        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    async def _skip_question(self) -> None:
        """Skip the selected question"""
        if not self.selected_question:
            return

        await self._orchestrator.answer_question(
            self.selected_question.get("id", ""),
            "SKIP: User chose to skip this question"
        )
        self.notify("Question skipped")
        await self._refresh_questions()

    async def _skip_all_questions(self) -> None:
        """Skip all pending questions"""
        for q in self._questions:
            await self._orchestrator.answer_question(
                q.get("id", ""),
                "SKIP: User chose to skip all questions"
            )

        self.notify(f"Skipped {len(self._questions)} questions")
        await self._refresh_questions()

    async def _escalate_question(self) -> None:
        """Escalate question for manual intervention"""
        if not self.selected_question:
            return

        await self._orchestrator.answer_question(
            self.selected_question.get("id", ""),
            "ESCALATE: User requested manual intervention. Please stop and wait for human input."
        )
        self.notify("Question escalated")
        await self._refresh_questions()

    def action_refresh(self) -> None:
        """Refresh questions"""
        asyncio.create_task(self._refresh_questions())

    def action_go_back(self) -> None:
        """Go back to dashboard"""
        self.app.switch_screen("dashboard")

    def action_submit_answer(self) -> None:
        """Submit current answer"""
        asyncio.create_task(self._submit_answer())

    def action_skip_question(self) -> None:
        """Skip current question"""
        asyncio.create_task(self._skip_question())
