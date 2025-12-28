"""CLOPUS TUI Main Application - Modern UI"""

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static
from textual.binding import Binding
from textual.screen import Screen
from textual.design import ColorSystem
from textual.theme import Theme
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
from .services.notifications import NotificationService


# Modern light theme colors
CLOPUS_LIGHT = Theme(
    name="clopus-light",
    primary="#2563eb",
    secondary="#6366f1",
    accent="#0891b2",
    foreground="#1e293b",
    background="#f8fafc",
    surface="#ffffff",
    panel="#f1f5f9",
    warning="#d97706",
    error="#dc2626",
    success="#16a34a",
    dark=False,
)

# Modern dark theme colors
CLOPUS_DARK = Theme(
    name="clopus-dark",
    primary="#3b82f6",
    secondary="#8b5cf6",
    accent="#22d3ee",
    foreground="#f8fafc",
    background="#0f172a",
    surface="#1e293b",
    panel="#334155",
    warning="#f59e0b",
    error="#ef4444",
    success="#22c55e",
    dark=True,
)


class CLOPUSApp(App):
    """CLOPUS Terminal User Interface - Modern Design"""

    TITLE = "CLOPUS"
    SUB_TITLE = "Claude Orchestrated Parallel Universal System"

    # Modern CSS styling
    CSS = """
    Screen {
        background: $background;
    }

    Header {
        dock: top;
        height: 3;
        background: $surface;
        color: $foreground;
    }

    Footer {
        dock: bottom;
        height: 1;
        background: $surface;
    }

    /* Panel styling */
    .panel {
        background: $surface;
        border: round $primary;
        padding: 1 2;
        margin: 0 1 1 1;
    }

    .panel-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    /* Card styling */
    .card {
        background: $panel;
        border: round $secondary 50%;
        padding: 1;
        margin: 0 0 1 0;
    }

    /* Status indicators */
    .status-running { color: $success; }
    .status-busy { color: $warning; }
    .status-idle { color: $secondary; }
    .status-offline { color: $error; }
    .status-completed { color: $success; }
    .status-failed { color: $error; }
    .status-pending { color: $warning; }

    /* Buttons */
    Button {
        margin: 0 1 0 0;
    }

    Button.primary {
        background: $primary;
    }

    Button.success {
        background: $success;
    }

    Button.warning {
        background: $warning;
    }

    Button.danger {
        background: $error;
    }

    /* Data table styling */
    DataTable {
        background: $surface;
    }

    DataTable > .datatable--header {
        background: $panel;
        text-style: bold;
    }

    DataTable > .datatable--cursor {
        background: $primary;
    }

    /* Input styling */
    Input {
        background: $panel;
        border: tall $secondary 50%;
    }

    Input:focus {
        border: tall $primary;
    }

    /* Log viewer */
    Log, RichLog {
        background: $surface;
        border: round $secondary 50%;
    }

    /* Tree view */
    Tree {
        background: $surface;
    }

    Tree > .tree--cursor {
        background: $primary;
    }

    /* Progress bars */
    ProgressBar > .bar--bar {
        color: $primary;
    }

    ProgressBar > .bar--complete {
        color: $success;
    }

    /* Tabs */
    Tabs {
        background: $surface;
    }

    Tab {
        background: $surface;
        padding: 0 2;
    }

    Tab.-active {
        background: $panel;
        text-style: bold;
    }

    /* Scrollbars */
    Scrollbar {
        background: $panel;
    }

    ScrollBar > .scrollbar--bar {
        color: $secondary 50%;
    }

    ScrollBar > .scrollbar--bar:hover {
        color: $primary;
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
        Binding("question_mark", "switch_screen('questions')", "Questions", show=False),
        Binding("c", "switch_screen('config')", "Config", show=False),
        Binding("f1", "show_help", "Help", show=True),
        Binding("ctrl+q", "quit", "Quit", show=True),
        Binding("ctrl+t", "toggle_theme", "Theme", show=True),
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

    def __init__(self, *args, use_websocket: bool = False, start_dark: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self._use_websocket = use_websocket
        self._start_dark = start_dark
        self._ws_client: Optional[WebSocketClient] = None
        self._notification_svc = NotificationService(enable_desktop=True)
        self._ws_task: Optional[asyncio.Task] = None

        # Register custom themes
        self.register_theme(CLOPUS_LIGHT)
        self.register_theme(CLOPUS_DARK)

    def on_mount(self) -> None:
        """Initialize app on mount"""
        # Set initial theme
        self.theme = "clopus-dark" if self._start_dark else "clopus-light"

        # Push to dashboard
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
        """Show help notification"""
        help_text = """[bold]CLOPUS TUI - Keyboard Shortcuts[/]

[bold cyan]Navigation:[/]
  d  Dashboard    w  Workers    p  Projects
  t  Tasks        l  Logs       o  Objectives
  m  Memory       ?  Questions  c  Config

[bold cyan]Actions:[/]
  r        Refresh current view
  Ctrl+T   Toggle dark/light theme
  Ctrl+Q   Quit

[bold cyan]Screen-specific:[/]
  Enter    Select/Confirm
  Escape   Go back / Cancel
  Tab      Next field
  /        Search (where available)"""
        self.notify(help_text, timeout=15)

    def action_toggle_theme(self) -> None:
        """Toggle between dark and light theme"""
        if self.theme == "clopus-dark":
            self.theme = "clopus-light"
            self.notify("Switched to Light theme")
        else:
            self.theme = "clopus-dark"
            self.notify("Switched to Dark theme")

    def action_quit(self) -> None:
        """Quit the application"""
        self.exit()


def run_tui(use_websocket: bool = False, dark: bool = False):
    """Run the CLOPUS TUI application"""
    app = CLOPUSApp(use_websocket=use_websocket, start_dark=dark)
    app.run()


if __name__ == "__main__":
    run_tui()
