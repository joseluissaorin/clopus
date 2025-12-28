"""Task table widget with filtering and actions"""

from textual.app import ComposeResult
from textual.widgets import DataTable, Static, Input, Select
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.message import Message
from typing import List, Optional, Any
from dataclasses import dataclass


@dataclass
class TaskRow:
    """Task data for table display"""
    id: str
    title: str
    status: str
    priority: int
    worker_id: Optional[int]
    objective_id: str
    created_at: str
    project: str = ""


class TaskTable(Static):
    """Filterable task table with actions"""

    DEFAULT_CSS = """
    TaskTable {
        width: 100%;
        height: 100%;
    }

    TaskTable .filters {
        width: 100%;
        height: 3;
        margin-bottom: 1;
    }

    TaskTable .filter-input {
        width: 1fr;
        margin-right: 1;
    }

    TaskTable .filter-select {
        width: 20;
    }

    TaskTable DataTable {
        width: 100%;
        height: 1fr;
    }
    """

    class TaskSelected(Message):
        """Sent when a task is selected"""
        def __init__(self, task_id: str) -> None:
            self.task_id = task_id
            super().__init__()

    class TaskAction(Message):
        """Sent when an action is requested on a task"""
        def __init__(self, task_id: str, action: str) -> None:
            self.task_id = task_id
            self.action = action
            super().__init__()

    filter_text: reactive[str] = reactive("")
    filter_status: reactive[str] = reactive("all")

    def __init__(self, tasks: List[TaskRow] = None, **kwargs):
        super().__init__(**kwargs)
        self._tasks = tasks or []
        self._filtered_tasks = self._tasks

    def compose(self) -> ComposeResult:
        with Horizontal(classes="filters"):
            yield Input(
                placeholder="Search tasks...",
                classes="filter-input",
                id="task-search",
            )
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
                classes="filter-select",
                id="status-filter",
            )

        table = DataTable(id="task-table")
        table.cursor_type = "row"
        yield table

    def on_mount(self) -> None:
        """Set up table columns"""
        table = self.query_one("#task-table", DataTable)
        table.add_columns(
            "ID",
            "Title",
            "Status",
            "Priority",
            "Worker",
            "Project",
        )
        self._refresh_table()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes"""
        if event.input.id == "task-search":
            self.filter_text = event.value
            self._apply_filters()

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle status filter changes"""
        if event.select.id == "status-filter":
            self.filter_status = event.value
            self._apply_filters()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection"""
        if event.row_key:
            self.post_message(self.TaskSelected(str(event.row_key.value)))

    def _apply_filters(self) -> None:
        """Apply current filters to tasks"""
        self._filtered_tasks = []
        for task in self._tasks:
            # Status filter
            if self.filter_status != "all" and task.status != self.filter_status:
                continue
            # Text filter
            if self.filter_text:
                search = self.filter_text.lower()
                if (
                    search not in task.title.lower()
                    and search not in task.id.lower()
                    and search not in task.project.lower()
                ):
                    continue
            self._filtered_tasks.append(task)
        self._refresh_table()

    def _refresh_table(self) -> None:
        """Refresh table with current filtered tasks"""
        table = self.query_one("#task-table", DataTable)
        table.clear()

        for task in self._filtered_tasks:
            status_display = self._format_status(task.status)
            priority_display = self._format_priority(task.priority)
            worker_display = str(task.worker_id) if task.worker_id else "-"

            table.add_row(
                task.id[:8],
                task.title[:40] + "..." if len(task.title) > 40 else task.title,
                status_display,
                priority_display,
                worker_display,
                task.project[:15] if task.project else "-",
                key=task.id,
            )

    def _format_status(self, status: str) -> str:
        """Format status with color"""
        status_colors = {
            "pending": "[yellow]Pending[/]",
            "in_progress": "[blue]In Progress[/]",
            "completed": "[green]Completed[/]",
            "failed": "[red]Failed[/]",
            "blocked": "[magenta]Blocked[/]",
            "cancelled": "[gray]Cancelled[/]",
        }
        return status_colors.get(status, status)

    def _format_priority(self, priority: int) -> str:
        """Format priority with color"""
        if priority >= 8:
            return f"[red]{priority}[/]"
        elif priority >= 5:
            return f"[yellow]{priority}[/]"
        else:
            return f"[green]{priority}[/]"

    def update_tasks(self, tasks: List[TaskRow]) -> None:
        """Update task list"""
        self._tasks = tasks
        self._apply_filters()

    def get_selected_task_id(self) -> Optional[str]:
        """Get currently selected task ID"""
        table = self.query_one("#task-table", DataTable)
        if table.cursor_row is not None and self._filtered_tasks:
            return self._filtered_tasks[table.cursor_row].id
        return None
