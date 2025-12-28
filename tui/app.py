"""CLOPUS TUI Main Application"""

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static
from textual.binding import Binding
from textual.screen import Screen
from typing import Optional
import asyncio

from .screens.dashboard import DashboardScreen
from .screens.workers import WorkersScreen
from .screens.projects import ProjectsScreen
from .screens.tasks import TasksScreen
from .screens.browser import BrowserScreen
from .screens.logs import LogsScreen
from .screens.objectives import ObjectivesScreen
from .screens.memory import MemoryScreen
from .screens.questions import QuestionsScreen
from .screens.config import ConfigScreen

from .services.websocket_client import WebSocketClient, MockWebSocketClient, EventType
from .services.notifications import NotificationService, NotificationType
from .themes.dark import DARK_THEME
from .themes.light import LIGHT_THEME


class CLOPUSApp(App):
    """CLOPUS Terminal User Interface"""

    TITLE = "CLOPUS"
    SUB_TITLE = "Claude Orchestrated Parallel Universal System"

    CSS = """
    Screen {
        background: $background;
    }

    Header {
        dock: top;
    }

    Footer {
        dock: bottom;
    }
    """

    BINDINGS = [
        Binding("d", "switch_screen('dashboard')", "Dashboard", show=True),
        Binding("w", "switch_screen('workers')", "Workers", show=True),
        Binding("p", "switch_screen('projects')", "Projects", show=True),
        Binding("t", "switch_screen('tasks')", "Tasks", show=True),
        Binding("b", "switch_screen('browser')", "Browser", show=False),
        Binding("l", "switch_screen('logs')", "Logs", show=True),
        Binding("o", "switch_screen('objectives')", "Objectives", show=False),
        Binding("m", "switch_screen('memory')", "Memory", show=False),
        Binding("q", "switch_screen('questions')", "Questions", show=False),
        Binding("c", "switch_screen('config')", "Config", show=False),
        Binding("?", "show_help", "Help", show=True),
        Binding("ctrl+q", "quit", "Quit", show=True),
        Binding("ctrl+t", "toggle_theme", "Toggle Theme", show=False),
    ]

    SCREENS = {
        "dashboard": DashboardScreen,
        "workers": WorkersScreen,
        "projects": ProjectsScreen,
        "tasks": TasksScreen,
        "browser": BrowserScreen,
        "logs": LogsScreen,
        "objectives": ObjectivesScreen,
        "memory": MemoryScreen,
        "questions": QuestionsScreen,
        "config": ConfigScreen,
    }

    def __init__(self, *args, use_websocket: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self._use_websocket = use_websocket
        self._ws_client: Optional[WebSocketClient] = None
        self._notification_svc = NotificationService(enable_desktop=True)
        self._ws_task: Optional[asyncio.Task] = None

    def on_mount(self) -> None:
        """Initialize app on mount"""
        # SCREENS dict auto-registers screens, just push to dashboard
        self.push_screen("dashboard")

        # Start WebSocket or mock client
        if self._use_websocket:
            self._ws_client = WebSocketClient()
        else:
            self._ws_client = MockWebSocketClient()

        # Register event handlers
        self._ws_client.on(EventType.TASK_COMPLETED, self._on_task_completed)
        self._ws_client.on(EventType.TASK_FAILED, self._on_task_failed)
        self._ws_client.on(EventType.QUESTION_PENDING, self._on_question_pending)
        self._ws_client.on(EventType.WORKER_STATUS, self._on_worker_status)

        # Start WebSocket listener
        self._ws_task = asyncio.create_task(self._ws_client.start())

    async def on_unmount(self) -> None:
        """Cleanup on unmount"""
        if self._ws_client:
            await self._ws_client.disconnect()
        if self._ws_task:
            self._ws_task.cancel()

    async def _on_task_completed(self, event) -> None:
        """Handle task completed event"""
        await self._notification_svc.notify_task_completed(
            task_title=event.data.get("title", "Unknown task"),
            project=event.data.get("project", ""),
        )

    async def _on_task_failed(self, event) -> None:
        """Handle task failed event"""
        await self._notification_svc.notify_task_failed(
            task_title=event.data.get("title", "Unknown task"),
            error=event.data.get("error", ""),
        )

    async def _on_question_pending(self, event) -> None:
        """Handle pending question event"""
        await self._notification_svc.notify_question_pending(
            question=event.data.get("content", "New question pending"),
        )
        self.notify("New question pending! Press 'q' to view.")

    async def _on_worker_status(self, event) -> None:
        """Handle worker status change"""
        if event.data.get("status") == "offline":
            await self._notification_svc.notify_worker_offline(
                worker_id=event.data.get("worker_id", 0),
                role=event.data.get("role", "unknown"),
            )

    def action_switch_screen(self, screen_name: str) -> None:
        """Switch to a screen"""
        if screen_name in self.SCREENS:
            self.switch_screen(screen_name)

    def action_show_help(self) -> None:
        """Show help screen"""
        help_text = """
[bold]CLOPUS TUI - Keyboard Shortcuts[/]

[bold]Navigation:[/]
  d     Dashboard
  w     Workers
  p     Projects
  t     Tasks
  l     Logs
  o     Objectives
  m     Memory
  q     Questions
  c     Config
  b     Browser

[bold]Actions:[/]
  r         Refresh current view
  Ctrl+T    Toggle dark/light theme
  Ctrl+Q    Quit

[bold]Screen-specific:[/]
  Enter     Select/Confirm
  Escape    Go back / Cancel
  Tab       Next field
  /         Search (where available)

Press any key to close this help.
        """
        self.notify(help_text, timeout=10)

    def action_toggle_theme(self) -> None:
        """Toggle between dark and light theme"""
        self.dark = not self.dark
        theme_name = "Dark" if self.dark else "Light"
        self.notify(f"Switched to {theme_name} theme")

    def action_quit(self) -> None:
        """Quit the application"""
        self.exit()


class HelpScreen(Screen):
    """Help screen showing keyboard shortcuts"""

    CSS = """
    HelpScreen {
        align: center middle;
    }

    #help-container {
        width: 60;
        height: auto;
        border: solid $primary;
        padding: 2;
        background: $surface;
    }

    #help-title {
        text-style: bold;
        text-align: center;
        margin-bottom: 1;
    }

    .help-section {
        margin-bottom: 1;
    }

    .help-section-title {
        text-style: bold;
        color: $primary;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("enter", "dismiss", "Close"),
        Binding("any", "dismiss", "Close"),
    ]

    def compose(self) -> ComposeResult:
        from textual.containers import Container, Vertical
        from textual.widgets import Label

        with Container(id="help-container"):
            yield Label("CLOPUS TUI Help", id="help-title")

            with Vertical(classes="help-section"):
                yield Label("[bold]Navigation[/]", classes="help-section-title")
                yield Label("d - Dashboard")
                yield Label("w - Workers")
                yield Label("p - Projects")
                yield Label("t - Tasks")
                yield Label("l - Logs")
                yield Label("o - Objectives")

            with Vertical(classes="help-section"):
                yield Label("[bold]Actions[/]", classes="help-section-title")
                yield Label("r - Refresh")
                yield Label("Ctrl+T - Toggle Theme")
                yield Label("Ctrl+Q - Quit")

            yield Label("\nPress any key to close", id="help-footer")

    def action_dismiss(self) -> None:
        """Dismiss help screen"""
        self.app.pop_screen()


def run_tui(use_websocket: bool = False):
    """Run the CLOPUS TUI application"""
    app = CLOPUSApp(use_websocket=use_websocket)
    app.run()


if __name__ == "__main__":
    run_tui()
