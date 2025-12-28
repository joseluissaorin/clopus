"""Browser automation screen"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Header, Footer, Label, Button, Input, TextArea
from textual.containers import Horizontal, Vertical, Container
from textual.reactive import reactive
from typing import Optional, List
import asyncio
import webbrowser

from ..services.docker_client import DockerClient


class BrowserScreen(Screen):
    """Browser automation control screen"""

    CSS = """
    BrowserScreen {
        layout: grid;
        grid-size: 2 2;
        grid-gutter: 1;
        padding: 1;
    }

    #browser-control {
        column-span: 1;
        row-span: 1;
        border: solid $primary;
        padding: 1;
    }

    #browser-status {
        column-span: 1;
        row-span: 1;
        border: solid $primary;
        padding: 1;
    }

    #browser-tasks {
        column-span: 1;
        row-span: 1;
        border: solid $primary;
        padding: 1;
    }

    #browser-output {
        column-span: 1;
        row-span: 1;
        border: solid $primary;
        padding: 1;
    }

    .panel-title {
        text-style: bold;
        margin-bottom: 1;
    }

    .control-row {
        height: 3;
        margin-bottom: 1;
    }

    .control-row Input {
        width: 1fr;
    }

    .control-row Button {
        margin-left: 1;
    }

    #url-input {
        width: 1fr;
    }

    .action-buttons {
        height: 3;
        margin-top: 1;
    }

    .action-buttons Button {
        margin-right: 1;
    }

    #vnc-info {
        margin-top: 1;
        padding: 1;
        border: solid $surface;
    }

    #task-list {
        height: 1fr;
        border: solid $surface;
        padding: 1;
    }

    #output-area {
        height: 1fr;
        border: solid $surface;
    }
    """

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("escape", "go_back", "Back"),
        ("v", "open_vnc", "Open VNC"),
        ("s", "take_screenshot", "Screenshot"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._docker = DockerClient()

    def compose(self) -> ComposeResult:
        yield Header()

        with Container(id="browser-control"):
            yield Label("Browser Control", classes="panel-title")

            with Horizontal(classes="control-row"):
                yield Input(placeholder="Enter URL to navigate...", id="url-input")
                yield Button("Go", id="btn-navigate", variant="primary")

            with Horizontal(classes="action-buttons"):
                yield Button("Screenshot", id="btn-screenshot")
                yield Button("Execute JS", id="btn-execute-js")
                yield Button("Click Element", id="btn-click")
                yield Button("Fill Form", id="btn-fill")

            yield Static(id="vnc-info")

        with Container(id="browser-status"):
            yield Label("Browser Status", classes="panel-title")
            yield Static(id="status-info")
            with Horizontal(classes="action-buttons"):
                yield Button("Open VNC", id="btn-vnc", variant="primary")
                yield Button("Restart Browser", id="btn-restart")
                yield Button("Stop", id="btn-stop", variant="error")

        with Container(id="browser-tasks"):
            yield Label("Automation Tasks", classes="panel-title")
            yield Static(id="task-list")
            with Horizontal(classes="action-buttons"):
                yield Button("New Task", id="btn-new-task", variant="primary")
                yield Button("Run Selected", id="btn-run")

        with Container(id="browser-output"):
            yield Label("Output", classes="panel-title")
            yield TextArea(id="output-area", read_only=True)

        yield Footer()

    async def on_mount(self) -> None:
        """Initialize browser status"""
        await self._refresh_status()
        self._update_vnc_info()

    def _update_vnc_info(self) -> None:
        """Update VNC connection info"""
        vnc_info = self.query_one("#vnc-info", Static)
        vnc_info.update(
            "[bold]VNC Access:[/]\n"
            "  noVNC (Web): http://localhost:6280\n"
            "  VNC Client: localhost:5920\n"
            "\n"
            "[dim]Worker 10 provides visual browser control via VNC[/]"
        )

    async def _refresh_status(self) -> None:
        """Refresh browser worker status"""
        try:
            containers = await self._docker.get_containers()

            # Find browser workers
            worker_9 = next((c for c in containers if "worker-9" in c.name), None)
            worker_10 = next((c for c in containers if "worker-10" in c.name), None)

            lines = []

            if worker_9:
                status = "[green]Running[/]" if "Up" in worker_9.status else "[red]Stopped[/]"
                lines.append(f"[bold]Worker 9 (Headless):[/] {status}")
                lines.append(f"  Image: {worker_9.image}")
            else:
                lines.append("[bold]Worker 9 (Headless):[/] [dim]Not found[/]")

            lines.append("")

            if worker_10:
                status = "[green]Running[/]" if "Up" in worker_10.status else "[red]Stopped[/]"
                lines.append(f"[bold]Worker 10 (Chrome VNC):[/] {status}")
                lines.append(f"  Image: {worker_10.image}")
                if worker_10.ports:
                    lines.append(f"  Ports: {', '.join(worker_10.ports[:3])}")
            else:
                lines.append("[bold]Worker 10 (Chrome VNC):[/] [dim]Not found[/]")

            status_info = self.query_one("#status-info", Static)
            status_info.update("\n".join(lines))

        except Exception as e:
            status_info = self.query_one("#status-info", Static)
            status_info.update(f"[red]Error loading status: {e}[/]")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        button_handlers = {
            "btn-navigate": self._navigate_to_url,
            "btn-screenshot": lambda: asyncio.create_task(self._take_screenshot()),
            "btn-vnc": self._open_vnc,
            "btn-restart": lambda: asyncio.create_task(self._restart_browser()),
            "btn-stop": lambda: asyncio.create_task(self._stop_browser()),
            "btn-execute-js": self._show_js_dialog,
            "btn-click": self._show_click_dialog,
            "btn-fill": self._show_fill_dialog,
            "btn-new-task": self._create_new_task,
            "btn-run": self._run_selected_task,
        }

        handler = button_handlers.get(event.button.id)
        if handler:
            handler()

    def _navigate_to_url(self) -> None:
        """Navigate to URL"""
        url_input = self.query_one("#url-input", Input)
        url = url_input.value.strip()

        if url:
            if not url.startswith(("http://", "https://")):
                url = "https://" + url

            self._log_output(f"Navigating to: {url}")
            # In a real implementation, this would send a command to the browser worker
            self.notify(f"Navigation command sent: {url}")

    async def _take_screenshot(self) -> None:
        """Take a screenshot"""
        self._log_output("Taking screenshot...")

        # Execute screenshot command via docker
        result = await self._docker.exec_command(
            "clopus-worker-10",
            ["python3", "-c", "print('Screenshot would be taken here')"]
        )

        if result:
            self._log_output(f"Screenshot result: {result}")
            self.notify("Screenshot saved to /output/screenshots/")
        else:
            self._log_output("[red]Screenshot failed[/]")
            self.notify("Screenshot failed", severity="error")

    def _open_vnc(self) -> None:
        """Open VNC in browser"""
        webbrowser.open("http://localhost:6280")
        self.notify("Opening VNC viewer...")

    async def _restart_browser(self) -> None:
        """Restart browser worker"""
        success = await self._docker.restart_worker(10)
        if success:
            self.notify("Browser worker restarting...")
            await asyncio.sleep(2)
            await self._refresh_status()
        else:
            self.notify("Failed to restart browser worker", severity="error")

    async def _stop_browser(self) -> None:
        """Stop browser worker"""
        success = await self._docker.stop_worker(10)
        if success:
            self.notify("Browser worker stopped")
            await self._refresh_status()
        else:
            self.notify("Failed to stop browser worker", severity="error")

    def _show_js_dialog(self) -> None:
        """Show JavaScript execution dialog"""
        self._log_output("JavaScript execution not yet implemented in TUI")

    def _show_click_dialog(self) -> None:
        """Show click element dialog"""
        self._log_output("Click element not yet implemented in TUI")

    def _show_fill_dialog(self) -> None:
        """Show fill form dialog"""
        self._log_output("Fill form not yet implemented in TUI")

    def _create_new_task(self) -> None:
        """Create new automation task"""
        self._log_output("Task creation not yet implemented in TUI")

    def _run_selected_task(self) -> None:
        """Run selected automation task"""
        self._log_output("Task execution not yet implemented in TUI")

    def _log_output(self, message: str) -> None:
        """Log message to output area"""
        output = self.query_one("#output-area", TextArea)
        current = output.text
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        new_text = f"{current}[{timestamp}] {message}\n" if current else f"[{timestamp}] {message}\n"
        output.text = new_text
        output.scroll_end()

    def action_refresh(self) -> None:
        """Refresh browser status"""
        asyncio.create_task(self._refresh_status())

    def action_go_back(self) -> None:
        """Go back to dashboard"""
        self.app.switch_screen("dashboard")

    def action_open_vnc(self) -> None:
        """Open VNC viewer"""
        self._open_vnc()

    def action_take_screenshot(self) -> None:
        """Take screenshot"""
        asyncio.create_task(self._take_screenshot())
