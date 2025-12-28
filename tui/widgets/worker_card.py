"""Worker status card widget"""

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Static, Button, Label
from textual.reactive import reactive
from rich.text import Text
from typing import Optional


class WorkerCard(Static):
    """Card displaying worker status with actions"""

    DEFAULT_CSS = """
    WorkerCard {
        width: 100%;
        height: auto;
        min-height: 5;
        border: solid $primary;
        padding: 1;
        margin-bottom: 1;
    }

    WorkerCard.idle {
        border: solid $success;
    }

    WorkerCard.busy {
        border: solid $warning;
    }

    WorkerCard.offline {
        border: solid $error;
    }

    WorkerCard .worker-header {
        width: 100%;
        height: 1;
    }

    WorkerCard .worker-id {
        width: auto;
        text-style: bold;
    }

    WorkerCard .worker-role {
        width: auto;
        margin-left: 2;
        color: $text-muted;
    }

    WorkerCard .worker-status {
        width: auto;
        dock: right;
    }

    WorkerCard .worker-task {
        width: 100%;
        height: 1;
        margin-top: 1;
        color: $text-muted;
    }

    WorkerCard .worker-actions {
        width: 100%;
        height: auto;
        margin-top: 1;
    }

    WorkerCard .worker-actions Button {
        width: auto;
        min-width: 8;
        margin-right: 1;
    }
    """

    worker_id: reactive[int] = reactive(0)
    role: reactive[str] = reactive("unknown")
    status: reactive[str] = reactive("offline")
    task_id: reactive[Optional[str]] = reactive(None)
    task_started: reactive[Optional[str]] = reactive(None)
    model: reactive[Optional[str]] = reactive(None)

    def __init__(
        self,
        worker_id: int,
        role: str = "unknown",
        status: str = "offline",
        task_id: Optional[str] = None,
        task_started: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.worker_id = worker_id
        self.role = role
        self.status = status
        self.task_id = task_id
        self.task_started = task_started
        self.model = model

    def compose(self) -> ComposeResult:
        with Horizontal(classes="worker-header"):
            yield Label(f"Worker {self.worker_id}", classes="worker-id")
            yield Label(self.role.upper(), classes="worker-role")
            yield Label(self._get_status_text(), classes="worker-status")

        task_text = self._get_task_text()
        yield Label(task_text, classes="worker-task")

        with Horizontal(classes="worker-actions"):
            yield Button("Restart", id=f"restart-{self.worker_id}", variant="default")
            yield Button("Logs", id=f"logs-{self.worker_id}", variant="default")
            if self.status == "busy":
                yield Button("Cancel", id=f"cancel-{self.worker_id}", variant="error")

    def _get_status_text(self) -> str:
        status_icons = {
            "idle": "[green]● IDLE[/]",
            "busy": "[yellow]● BUSY[/]",
            "offline": "[red]● OFFLINE[/]",
        }
        return status_icons.get(self.status, "[gray]● UNKNOWN[/]")

    def _get_task_text(self) -> str:
        if self.task_id:
            text = f"Task: {self.task_id[:8]}..."
            if self.task_started:
                text += f" (started: {self.task_started})"
            return text
        return "No active task"

    def watch_status(self, new_status: str) -> None:
        """Update CSS class when status changes"""
        self.remove_class("idle", "busy", "offline")
        self.add_class(new_status)

    def update_status(
        self,
        status: str,
        task_id: Optional[str] = None,
        task_started: Optional[str] = None,
        role: Optional[str] = None,
    ) -> None:
        """Update worker status"""
        self.status = status
        if task_id is not None:
            self.task_id = task_id
        if task_started is not None:
            self.task_started = task_started
        if role is not None:
            self.role = role
        self.refresh()
