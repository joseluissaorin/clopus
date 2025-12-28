"""Objectives screen - objective management"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Header, Footer, Label, Button, DataTable, TextArea, Input
from textual.containers import Horizontal, Vertical, Container
from textual.reactive import reactive
from typing import Optional, List
import asyncio

from ..widgets.progress_bar import TaskProgressBar
from ..services.database import DatabaseClient, ObjectiveInfo
from ..services.orchestrator import OrchestratorClient


class ObjectivesScreen(Screen):
    """Objective management screen"""

    CSS = """
    ObjectivesScreen {
        layout: grid;
        grid-size: 2 2;
        grid-gutter: 1;
        padding: 1;
    }

    #new-objective {
        column-span: 2;
        row-span: 1;
        border: solid $primary;
        padding: 1;
    }

    #objective-list {
        column-span: 1;
        row-span: 1;
        border: solid $primary;
        padding: 1;
    }

    #objective-detail {
        column-span: 1;
        row-span: 1;
        border: solid $primary;
        padding: 1;
    }

    .panel-title {
        text-style: bold;
        margin-bottom: 1;
    }

    #objective-input {
        height: 5;
        margin-bottom: 1;
    }

    .submit-row {
        height: 3;
    }

    .submit-row Input {
        width: 10;
        margin-right: 1;
    }

    .submit-row Button {
        margin-right: 1;
    }

    #objectives-table {
        height: 1fr;
    }

    #objective-actions {
        height: 3;
        margin-top: 1;
    }

    #objective-actions Button {
        margin-right: 1;
    }
    """

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("escape", "go_back", "Back"),
        ("n", "new_objective", "New"),
        ("c", "cancel_objective", "Cancel"),
    ]

    selected_objective: reactive[Optional[ObjectiveInfo]] = reactive(None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._db = DatabaseClient()
        self._orchestrator = OrchestratorClient()
        self._refresh_task: Optional[asyncio.Task] = None
        self._objectives: List[ObjectiveInfo] = []

    def compose(self) -> ComposeResult:
        yield Header()

        with Container(id="new-objective"):
            yield Label("Submit New Objective", classes="panel-title")
            yield TextArea(id="objective-input", language=None)
            with Horizontal(classes="submit-row"):
                yield Input(placeholder="Priority (1-10)", id="priority-input", value="5")
                yield Button("Submit", id="btn-submit", variant="primary")
                yield Button("Clear", id="btn-clear")

        with Container(id="objective-list"):
            yield Label("Objectives", classes="panel-title")
            yield DataTable(id="objectives-table")

        with Container(id="objective-detail"):
            yield Label("Objective Details", classes="panel-title")
            yield Static(id="objective-info")
            yield TaskProgressBar(label="Tasks", id="objective-progress")
            with Horizontal(id="objective-actions"):
                yield Button("Cancel", id="btn-cancel", variant="error")
                yield Button("Retry Failed", id="btn-retry")
                yield Button("View Tasks", id="btn-view-tasks")

        yield Footer()

    async def on_mount(self) -> None:
        """Set up table and start refresh"""
        table = self.query_one("#objectives-table", DataTable)
        table.add_columns("ID", "Status", "Tasks", "Created")
        table.cursor_type = "row"

        await self._db.connect()
        await self._refresh_objectives()
        self._refresh_task = asyncio.create_task(self._refresh_loop())

    async def on_unmount(self) -> None:
        """Stop refresh loop"""
        if self._refresh_task:
            self._refresh_task.cancel()
        await self._db.close()

    async def _refresh_loop(self) -> None:
        """Periodically refresh objectives"""
        while True:
            try:
                await asyncio.sleep(5)
                await self._refresh_objectives()
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    async def _refresh_objectives(self) -> None:
        """Refresh objective list"""
        try:
            self._objectives = await self._db.get_objectives(limit=50)

            table = self.query_one("#objectives-table", DataTable)
            table.clear()

            for obj in self._objectives:
                status_display = self._format_status(obj.status)
                tasks_display = f"{obj.completed_tasks}/{obj.task_count}"
                created = obj.created_at[:10] if obj.created_at else "-"

                table.add_row(
                    obj.id[:8],
                    status_display,
                    tasks_display,
                    created,
                    key=obj.id,
                )

        except Exception:
            pass

    def _format_status(self, status: str) -> str:
        """Format status with color"""
        colors = {
            "pending": "[yellow]Pending[/]",
            "in_progress": "[blue]In Progress[/]",
            "completed": "[green]Completed[/]",
            "failed": "[red]Failed[/]",
            "cancelled": "[dim]Cancelled[/]",
        }
        return colors.get(status, status)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle objective selection"""
        if event.row_key:
            obj = next(
                (o for o in self._objectives if o.id == event.row_key.value),
                None
            )
            if obj:
                self.selected_objective = obj
                self._update_objective_detail()

    def _update_objective_detail(self) -> None:
        """Update objective detail panel"""
        if not self.selected_objective:
            return

        obj = self.selected_objective
        info = self.query_one("#objective-info", Static)

        lines = [
            f"[bold]Objective {obj.id[:8]}[/]",
            f"",
            f"[dim]Status:[/] {self._format_status(obj.status)}",
            f"[dim]Created:[/] {obj.created_at or 'Unknown'}",
            f"",
            f"[dim]Content:[/]",
            obj.content[:200] + "..." if len(obj.content) > 200 else obj.content,
        ]

        info.update("\n".join(lines))

        # Update progress bar
        progress = self.query_one("#objective-progress", TaskProgressBar)
        progress.update_stats(
            total=obj.task_count,
            completed=obj.completed_tasks,
            failed=obj.failed_tasks,
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "btn-submit":
            asyncio.create_task(self._submit_objective())
        elif event.button.id == "btn-clear":
            self._clear_input()
        elif event.button.id == "btn-cancel":
            asyncio.create_task(self._cancel_objective())
        elif event.button.id == "btn-retry":
            asyncio.create_task(self._retry_failed())
        elif event.button.id == "btn-view-tasks":
            self._view_tasks()

    async def _submit_objective(self) -> None:
        """Submit new objective"""
        input_area = self.query_one("#objective-input", TextArea)
        priority_input = self.query_one("#priority-input", Input)

        content = input_area.text.strip()
        if not content:
            self.notify("Please enter an objective", severity="warning")
            return

        try:
            priority = int(priority_input.value)
            priority = max(1, min(10, priority))
        except ValueError:
            priority = 5

        try:
            objective_id = await self._orchestrator.submit_objective(content, priority)
            self.notify(f"Objective submitted: {objective_id}")
            self._clear_input()
            await self._refresh_objectives()
        except Exception as e:
            self.notify(f"Failed to submit: {e}", severity="error")

    def _clear_input(self) -> None:
        """Clear input fields"""
        input_area = self.query_one("#objective-input", TextArea)
        priority_input = self.query_one("#priority-input", Input)
        input_area.text = ""
        priority_input.value = "5"

    async def _cancel_objective(self) -> None:
        """Cancel selected objective"""
        if not self.selected_objective:
            return

        success = await self._orchestrator.cancel_objective(self.selected_objective.id)
        if success:
            self.notify(f"Objective {self.selected_objective.id[:8]} cancelled")
            await self._refresh_objectives()
        else:
            self.notify("Failed to cancel objective", severity="error")

    async def _retry_failed(self) -> None:
        """Retry failed tasks for selected objective"""
        if not self.selected_objective:
            return

        # This would call the database to reset failed tasks
        self.notify("Retry failed tasks not yet implemented")

    def _view_tasks(self) -> None:
        """Switch to tasks screen filtered by objective"""
        if self.selected_objective:
            # In a real implementation, we'd pass the filter to tasks screen
            self.app.switch_screen("tasks")

    def action_refresh(self) -> None:
        """Refresh objectives"""
        asyncio.create_task(self._refresh_objectives())

    def action_go_back(self) -> None:
        """Go back to dashboard"""
        self.app.switch_screen("dashboard")

    def action_new_objective(self) -> None:
        """Focus objective input"""
        self.query_one("#objective-input", TextArea).focus()

    def action_cancel_objective(self) -> None:
        """Cancel selected objective"""
        asyncio.create_task(self._cancel_objective())
