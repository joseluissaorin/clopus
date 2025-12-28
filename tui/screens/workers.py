"""Workers screen - worker management"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Header, Footer, Label, Button, DataTable
from textual.containers import Horizontal, Vertical, Container, ScrollableContainer
from textual.reactive import reactive
from typing import Optional, List
import asyncio

from ..widgets.worker_card import WorkerCard
from ..widgets.log_viewer import LogViewer
from ..services.ipc import IPCMonitor, WorkerStatus
from ..services.docker_client import DockerClient


class WorkersScreen(Screen):
    """Worker management screen"""

    CSS = """
    WorkersScreen {
        layout: grid;
        grid-size: 2 1;
        grid-gutter: 1;
        padding: 1;
    }

    #workers-list {
        column-span: 1;
        border: solid $primary;
        padding: 1;
    }

    #worker-detail {
        column-span: 1;
        border: solid $primary;
        padding: 1;
    }

    .panel-title {
        text-style: bold;
        margin-bottom: 1;
    }

    .worker-grid {
        height: 1fr;
    }

    #worker-actions {
        height: 3;
        margin-top: 1;
    }

    #worker-actions Button {
        margin-right: 1;
    }

    #worker-logs {
        height: 1fr;
        margin-top: 1;
    }

    .role-coder { color: $primary; }
    .role-tester { color: $success; }
    .role-reviewer { color: $warning; }
    .role-researcher { color: cyan; }
    .role-debugger { color: $error; }
    .role-designer { color: magenta; }
    """

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("escape", "go_back", "Back"),
        ("1", "select_worker(1)", "Worker 1"),
        ("2", "select_worker(2)", "Worker 2"),
        ("3", "select_worker(3)", "Worker 3"),
        ("4", "select_worker(4)", "Worker 4"),
        ("5", "select_worker(5)", "Worker 5"),
    ]

    selected_worker: reactive[Optional[int]] = reactive(None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ipc = IPCMonitor()
        self._docker = DockerClient()
        self._refresh_task: Optional[asyncio.Task] = None
        self._workers: List[WorkerStatus] = []

    def compose(self) -> ComposeResult:
        yield Header()

        with Container(id="workers-list"):
            yield Label("Workers", classes="panel-title")
            yield DataTable(id="workers-table")

        with Container(id="worker-detail"):
            yield Label("Worker Details", classes="panel-title")
            yield Static(id="worker-info")
            with Horizontal(id="worker-actions"):
                yield Button("Restart", id="btn-restart", variant="warning")
                yield Button("Stop", id="btn-stop", variant="error")
                yield Button("View Logs", id="btn-logs")
            yield LogViewer(id="worker-logs", max_lines=200)

        yield Footer()

    async def on_mount(self) -> None:
        """Set up table and start refresh"""
        table = self.query_one("#workers-table", DataTable)
        table.add_columns("ID", "Role", "Status", "Task", "Model")
        table.cursor_type = "row"

        await self._refresh_workers()
        self._refresh_task = asyncio.create_task(self._refresh_loop())

    async def on_unmount(self) -> None:
        """Stop refresh loop"""
        if self._refresh_task:
            self._refresh_task.cancel()

    async def _refresh_loop(self) -> None:
        """Periodically refresh worker data"""
        while True:
            try:
                await asyncio.sleep(2)
                await self._refresh_workers()
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    async def _refresh_workers(self) -> None:
        """Refresh worker status"""
        try:
            self._workers = await self._ipc.get_all_worker_status()

            table = self.query_one("#workers-table", DataTable)
            table.clear()

            for worker in self._workers:
                status_display = self._format_status(worker.status)
                task_display = worker.task_id[:8] if worker.task_id else "-"
                model_display = worker.model or "-"

                table.add_row(
                    str(worker.id),
                    worker.role.upper(),
                    status_display,
                    task_display,
                    model_display,
                    key=str(worker.id),
                )

            # Update detail if worker selected
            if self.selected_worker:
                await self._update_worker_detail()

        except Exception:
            pass

    def _format_status(self, status: str) -> str:
        """Format status with color"""
        status_colors = {
            "idle": "[green]IDLE[/]",
            "busy": "[yellow]BUSY[/]",
            "offline": "[red]OFFLINE[/]",
        }
        return status_colors.get(status, status)

    async def _update_worker_detail(self) -> None:
        """Update worker detail panel"""
        if not self.selected_worker:
            return

        worker = next(
            (w for w in self._workers if w.id == self.selected_worker),
            None
        )

        if not worker:
            return

        info = self.query_one("#worker-info", Static)

        detail_lines = [
            f"[bold]Worker {worker.id}[/]",
            f"Role: [{self._get_role_color(worker.role)}]{worker.role.upper()}[/]",
            f"Status: {self._format_status(worker.status)}",
            f"Model: {worker.model or 'N/A'}",
        ]

        if worker.task_id:
            detail_lines.append(f"Task: {worker.task_id}")
        if worker.task_started:
            detail_lines.append(f"Started: {worker.task_started}")
        if worker.session_id:
            detail_lines.append(f"Session: {worker.session_id[:16]}...")

        info.update("\n".join(detail_lines))

    def _get_role_color(self, role: str) -> str:
        """Get color for role"""
        colors = {
            "coder": "blue",
            "tester": "green",
            "reviewer": "yellow",
            "researcher": "cyan",
            "debugger": "red",
            "designer": "magenta",
            "heartbeat": "white",
            "verificator": "white",
            "browser-headless": "cyan",
            "browser-chrome": "cyan",
            "services": "magenta",
        }
        return colors.get(role, "white")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle worker selection"""
        if event.row_key:
            self.selected_worker = int(event.row_key.value)
            asyncio.create_task(self._update_worker_detail())
            asyncio.create_task(self._load_worker_logs())

    async def _load_worker_logs(self) -> None:
        """Load logs for selected worker"""
        if not self.selected_worker:
            return

        logs = await self._ipc.get_worker_logs(self.selected_worker, lines=100)
        log_viewer = self.query_one("#worker-logs", LogViewer)
        log_viewer.clear()
        log_viewer.add_logs(logs)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if not self.selected_worker:
            return

        if event.button.id == "btn-restart":
            asyncio.create_task(self._restart_worker())
        elif event.button.id == "btn-stop":
            asyncio.create_task(self._stop_worker())
        elif event.button.id == "btn-logs":
            asyncio.create_task(self._load_worker_logs())

    async def _restart_worker(self) -> None:
        """Restart selected worker"""
        if self.selected_worker:
            success = await self._docker.restart_worker(self.selected_worker)
            if success:
                self.notify(f"Worker {self.selected_worker} restarted")
            else:
                self.notify(f"Failed to restart worker {self.selected_worker}", severity="error")

    async def _stop_worker(self) -> None:
        """Stop selected worker"""
        if self.selected_worker:
            success = await self._docker.stop_worker(self.selected_worker)
            if success:
                self.notify(f"Worker {self.selected_worker} stopped")
            else:
                self.notify(f"Failed to stop worker {self.selected_worker}", severity="error")

    def action_refresh(self) -> None:
        """Refresh workers"""
        asyncio.create_task(self._refresh_workers())

    def action_go_back(self) -> None:
        """Go back to dashboard"""
        self.app.switch_screen("dashboard")

    def action_select_worker(self, worker_id: int) -> None:
        """Select a worker by number"""
        self.selected_worker = worker_id
        asyncio.create_task(self._update_worker_detail())
        asyncio.create_task(self._load_worker_logs())
