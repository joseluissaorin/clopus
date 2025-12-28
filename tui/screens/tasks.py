"""Tasks screen - task management and monitoring"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Header, Footer, Label, Button, DataTable, Input, Select
from textual.containers import Horizontal, Vertical, Container
from textual.reactive import reactive
from typing import Optional, List
import asyncio

from ..widgets.task_table import TaskTable, TaskRow
from ..services.database import DatabaseClient, TaskInfo


class TasksScreen(Screen):
    """Task management screen"""

    CSS = """
    TasksScreen {
        layout: grid;
        grid-size: 2 1;
        grid-gutter: 1;
        padding: 1;
    }

    #task-list {
        column-span: 1;
        border: solid $primary;
        padding: 1;
    }

    #task-detail {
        column-span: 1;
        border: solid $primary;
        padding: 1;
    }

    .panel-title {
        text-style: bold;
        margin-bottom: 1;
    }

    #task-filters {
        height: 3;
        margin-bottom: 1;
    }

    #task-filters Input {
        width: 1fr;
        margin-right: 1;
    }

    #task-filters Select {
        width: 20;
    }

    #tasks-table {
        height: 1fr;
    }

    #task-info {
        height: auto;
    }

    #task-actions {
        height: 3;
        margin-top: 1;
    }

    #task-actions Button {
        margin-right: 1;
    }

    #task-output {
        height: 1fr;
        border: solid $surface;
        margin-top: 1;
        padding: 1;
        overflow-y: auto;
    }
    """

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("escape", "go_back", "Back"),
        ("f", "focus_filter", "Filter"),
        ("c", "cancel_task", "Cancel"),
        ("y", "retry_task", "Retry"),
    ]

    selected_task: reactive[Optional[TaskInfo]] = reactive(None)
    filter_status: reactive[str] = reactive("all")
    filter_text: reactive[str] = reactive("")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._db = DatabaseClient()
        self._refresh_task: Optional[asyncio.Task] = None
        self._tasks: List[TaskInfo] = []

    def compose(self) -> ComposeResult:
        yield Header()

        with Container(id="task-list"):
            yield Label("Tasks", classes="panel-title")
            with Horizontal(id="task-filters"):
                yield Input(placeholder="Search tasks...", id="task-search")
                yield Select(
                    [
                        ("All", "all"),
                        ("Pending", "pending"),
                        ("In Progress", "in_progress"),
                        ("Completed", "completed"),
                        ("Failed", "failed"),
                        ("Blocked", "blocked"),
                    ],
                    value="all",
                    id="status-filter",
                )
            yield DataTable(id="tasks-table")

        with Container(id="task-detail"):
            yield Label("Task Details", classes="panel-title")
            yield Static(id="task-info")
            with Horizontal(id="task-actions"):
                yield Button("Retry", id="btn-retry", variant="primary")
                yield Button("Cancel", id="btn-cancel", variant="error")
                yield Button("View Output", id="btn-output")
                yield Button("Increase Priority", id="btn-priority-up")
            yield Label("Output", classes="panel-title")
            yield Static(id="task-output")

        yield Footer()

    async def on_mount(self) -> None:
        """Set up table and start refresh"""
        table = self.query_one("#tasks-table", DataTable)
        table.add_columns("ID", "Title", "Status", "Priority", "Worker")
        table.cursor_type = "row"

        await self._db.connect()
        await self._refresh_tasks()
        self._refresh_task = asyncio.create_task(self._refresh_loop())

    async def on_unmount(self) -> None:
        """Stop refresh loop"""
        if self._refresh_task:
            self._refresh_task.cancel()
        await self._db.close()

    async def _refresh_loop(self) -> None:
        """Periodically refresh task data"""
        while True:
            try:
                await asyncio.sleep(3)
                await self._refresh_tasks()
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    async def _refresh_tasks(self) -> None:
        """Refresh task list"""
        try:
            status = self.filter_status if self.filter_status != "all" else None
            self._tasks = await self._db.get_tasks(status=status, limit=100)

            # Apply text filter
            if self.filter_text:
                search = self.filter_text.lower()
                self._tasks = [
                    t for t in self._tasks
                    if search in t.title.lower() or search in t.id.lower()
                ]

            table = self.query_one("#tasks-table", DataTable)
            table.clear()

            for task in self._tasks:
                status_display = self._format_status(task.status)
                priority_display = self._format_priority(task.priority)
                worker_display = str(task.worker_id) if task.worker_id else "-"
                title = task.title[:40] + "..." if len(task.title) > 40 else task.title

                table.add_row(
                    task.id[:8],
                    title,
                    status_display,
                    priority_display,
                    worker_display,
                    key=task.id,
                )

        except Exception:
            pass

    def _format_status(self, status: str) -> str:
        """Format status with color"""
        colors = {
            "pending": "[yellow]Pending[/]",
            "in_progress": "[blue]Running[/]",
            "completed": "[green]Done[/]",
            "failed": "[red]Failed[/]",
            "blocked": "[magenta]Blocked[/]",
            "cancelled": "[dim]Cancelled[/]",
        }
        return colors.get(status, status)

    def _format_priority(self, priority: int) -> str:
        """Format priority with color"""
        if priority >= 8:
            return f"[red]{priority}[/]"
        elif priority >= 5:
            return f"[yellow]{priority}[/]"
        else:
            return f"[green]{priority}[/]"

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input"""
        if event.input.id == "task-search":
            self.filter_text = event.value
            asyncio.create_task(self._refresh_tasks())

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle status filter change"""
        if event.select.id == "status-filter":
            self.filter_status = event.value
            asyncio.create_task(self._refresh_tasks())

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle task selection"""
        if event.row_key:
            task = next(
                (t for t in self._tasks if t.id == event.row_key.value),
                None
            )
            if task:
                self.selected_task = task
                self._update_task_detail()

    def _update_task_detail(self) -> None:
        """Update task detail panel"""
        if not self.selected_task:
            return

        t = self.selected_task
        info = self.query_one("#task-info", Static)

        lines = [
            f"[bold]{t.title}[/]",
            f"",
            f"[dim]ID:[/] {t.id}",
            f"[dim]Status:[/] {self._format_status(t.status)}",
            f"[dim]Priority:[/] {self._format_priority(t.priority)}",
            f"[dim]Objective:[/] {t.objective_id[:8] if t.objective_id else 'N/A'}",
        ]

        if t.worker_id:
            lines.append(f"[dim]Worker:[/] {t.worker_id}")
        if t.created_at:
            lines.append(f"[dim]Created:[/] {t.created_at}")
        if t.retry_count and t.retry_count > 0:
            lines.append(f"[dim]Retries:[/] {t.retry_count}")

        info.update("\n".join(lines))

        # Update output
        output = self.query_one("#task-output", Static)
        if t.result:
            output.update(t.result[:2000])  # Limit output display
        elif t.error:
            output.update(f"[red]Error:[/]\n{t.error[:2000]}")
        else:
            output.update("[dim]No output available[/]")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if not self.selected_task:
            return

        if event.button.id == "btn-retry":
            asyncio.create_task(self._retry_task())
        elif event.button.id == "btn-cancel":
            asyncio.create_task(self._cancel_task())
        elif event.button.id == "btn-priority-up":
            asyncio.create_task(self._increase_priority())
        elif event.button.id == "btn-output":
            self._show_full_output()

    async def _retry_task(self) -> None:
        """Retry the selected task"""
        if self.selected_task:
            success = await self._db.retry_task(self.selected_task.id)
            if success:
                self.notify(f"Task {self.selected_task.id[:8]} queued for retry")
                await self._refresh_tasks()
            else:
                self.notify("Failed to retry task", severity="error")

    async def _cancel_task(self) -> None:
        """Cancel the selected task"""
        if self.selected_task:
            success = await self._db.cancel_task(self.selected_task.id)
            if success:
                self.notify(f"Task {self.selected_task.id[:8]} cancelled")
                await self._refresh_tasks()
            else:
                self.notify("Failed to cancel task", severity="error")

    async def _increase_priority(self) -> None:
        """Increase task priority"""
        if self.selected_task:
            new_priority = min(10, self.selected_task.priority + 1)
            success = await self._db.update_task_priority(
                self.selected_task.id,
                new_priority
            )
            if success:
                self.notify(f"Priority increased to {new_priority}")
                await self._refresh_tasks()
            else:
                self.notify("Failed to update priority", severity="error")

    def _show_full_output(self) -> None:
        """Show full task output in a modal"""
        # For now, just scroll to output
        output = self.query_one("#task-output", Static)
        output.scroll_visible()

    def action_refresh(self) -> None:
        """Refresh tasks"""
        asyncio.create_task(self._refresh_tasks())

    def action_go_back(self) -> None:
        """Go back to dashboard"""
        self.app.switch_screen("dashboard")

    def action_focus_filter(self) -> None:
        """Focus the filter input"""
        self.query_one("#task-search", Input).focus()

    def action_cancel_task(self) -> None:
        """Cancel selected task"""
        asyncio.create_task(self._cancel_task())

    def action_retry_task(self) -> None:
        """Retry selected task"""
        asyncio.create_task(self._retry_task())
