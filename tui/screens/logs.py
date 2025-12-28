"""Logs screen - system log viewer"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Header, Footer, Label, Button, Select
from textual.containers import Horizontal, Vertical, Container
from textual.reactive import reactive
from typing import Optional, List
import asyncio

from ..widgets.log_viewer import LogViewer
from ..services.docker_client import DockerClient


class LogsScreen(Screen):
    """System logs viewer screen"""

    CSS = """
    LogsScreen {
        layout: vertical;
        padding: 1;
    }

    #log-controls {
        height: 3;
        margin-bottom: 1;
    }

    #log-controls Select {
        width: 25;
        margin-right: 1;
    }

    #log-controls Button {
        margin-right: 1;
    }

    #log-container {
        height: 1fr;
        border: solid $primary;
    }
    """

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("escape", "go_back", "Back"),
        ("c", "clear_logs", "Clear"),
        ("f", "toggle_follow", "Follow"),
        ("1", "show_orchestrator", "Orchestrator"),
        ("2", "show_workers", "Workers"),
    ]

    selected_source: reactive[str] = reactive("orchestrator")
    follow_logs: reactive[bool] = reactive(True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._docker = DockerClient()
        self._refresh_task: Optional[asyncio.Task] = None

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal(id="log-controls"):
            yield Select(
                [
                    ("Orchestrator", "orchestrator"),
                    ("All Workers", "workers"),
                    ("Worker 1 (Coder)", "worker-1"),
                    ("Worker 2 (Tester)", "worker-2"),
                    ("Worker 3 (Reviewer)", "worker-3"),
                    ("Worker 4 (Researcher)", "worker-4"),
                    ("Worker 5 (Debugger)", "worker-5"),
                    ("Worker 6 (Designer)", "worker-6"),
                    ("Worker 7 (Heartbeat)", "worker-7"),
                    ("Worker 8 (Verificator)", "worker-8"),
                    ("Worker 9 (Browser Headless)", "worker-9"),
                    ("Worker 10 (Browser Chrome)", "worker-10"),
                    ("Worker 11 (Services)", "worker-11"),
                    ("PostgreSQL", "postgres"),
                    ("Redis", "redis"),
                ],
                value="orchestrator",
                id="source-select",
            )
            yield Button("Refresh", id="btn-refresh")
            yield Button("Clear", id="btn-clear")
            yield Button("Follow", id="btn-follow", variant="primary")
            yield Button("Export", id="btn-export")

        with Container(id="log-container"):
            yield LogViewer(id="log-viewer", max_lines=2000)

        yield Footer()

    async def on_mount(self) -> None:
        """Start log streaming"""
        await self._load_logs()
        self._refresh_task = asyncio.create_task(self._refresh_loop())

    async def on_unmount(self) -> None:
        """Stop log streaming"""
        if self._refresh_task:
            self._refresh_task.cancel()

    async def _refresh_loop(self) -> None:
        """Periodically refresh logs if following"""
        while True:
            try:
                await asyncio.sleep(2)
                if self.follow_logs:
                    await self._load_new_logs()
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    async def _load_logs(self) -> None:
        """Load logs for selected source"""
        log_viewer = self.query_one("#log-viewer", LogViewer)
        log_viewer.clear()

        source = self.selected_source

        try:
            if source == "orchestrator":
                logs = await self._docker.get_orchestrator_logs(lines=500)
            elif source == "workers":
                # Get logs from all workers
                logs = []
                for i in range(1, 12):
                    worker_logs = await self._docker.get_logs(f"clopus-worker-{i}", lines=50)
                    for line in worker_logs:
                        logs.append(f"[W{i}] {line}")
            elif source.startswith("worker-"):
                worker_id = source.split("-")[1]
                logs = await self._docker.get_logs(f"clopus-worker-{worker_id}", lines=500)
            elif source == "postgres":
                logs = await self._docker.get_logs("clopus-postgres", lines=500)
            elif source == "redis":
                logs = await self._docker.get_logs("clopus-redis", lines=500)
            else:
                logs = []

            log_viewer.add_logs(logs)

        except Exception as e:
            log_viewer.add_log(f"[red]Error loading logs: {e}[/]")

    async def _load_new_logs(self) -> None:
        """Load only new logs (for following)"""
        # In a real implementation, this would only fetch new lines
        # For now, we just reload all logs
        await self._load_logs()

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle source selection change"""
        if event.select.id == "source-select":
            self.selected_source = event.value
            asyncio.create_task(self._load_logs())

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "btn-refresh":
            asyncio.create_task(self._load_logs())
        elif event.button.id == "btn-clear":
            log_viewer = self.query_one("#log-viewer", LogViewer)
            log_viewer.clear()
        elif event.button.id == "btn-follow":
            self.follow_logs = not self.follow_logs
            event.button.variant = "primary" if self.follow_logs else "default"
            event.button.label = "Following" if self.follow_logs else "Follow"
        elif event.button.id == "btn-export":
            self._export_logs()

    def _export_logs(self) -> None:
        """Export logs to file"""
        log_viewer = self.query_one("#log-viewer", LogViewer)
        logs = log_viewer._all_logs

        if logs:
            from pathlib import Path
            from datetime import datetime

            export_dir = Path.home() / "Dev/clopus/logs"
            export_dir.mkdir(exist_ok=True)

            filename = f"{self.selected_source}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            export_path = export_dir / filename

            with open(export_path, "w") as f:
                f.write("\n".join(logs))

            self.notify(f"Logs exported to {export_path}")
        else:
            self.notify("No logs to export", severity="warning")

    def action_refresh(self) -> None:
        """Refresh logs"""
        asyncio.create_task(self._load_logs())

    def action_go_back(self) -> None:
        """Go back to dashboard"""
        self.app.switch_screen("dashboard")

    def action_clear_logs(self) -> None:
        """Clear log display"""
        log_viewer = self.query_one("#log-viewer", LogViewer)
        log_viewer.clear()

    def action_toggle_follow(self) -> None:
        """Toggle log following"""
        self.follow_logs = not self.follow_logs
        btn = self.query_one("#btn-follow", Button)
        btn.variant = "primary" if self.follow_logs else "default"
        btn.label = "Following" if self.follow_logs else "Follow"

    def action_show_orchestrator(self) -> None:
        """Show orchestrator logs"""
        self.selected_source = "orchestrator"
        select = self.query_one("#source-select", Select)
        select.value = "orchestrator"
        asyncio.create_task(self._load_logs())

    def action_show_workers(self) -> None:
        """Show all worker logs"""
        self.selected_source = "workers"
        select = self.query_one("#source-select", Select)
        select.value = "workers"
        asyncio.create_task(self._load_logs())
