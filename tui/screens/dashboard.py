"""Dashboard screen - main overview"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Header, Footer, Label, Button
from textual.containers import Horizontal, Vertical, Container, Grid
from textual.reactive import reactive
from typing import Optional
import asyncio

from ..widgets.stats_panel import StatsPanel, StatItem, SystemHealth
from ..widgets.progress_bar import TaskProgressBar
from ..widgets.sparkline import Sparkline, ActivityChart
from ..services.database import DatabaseClient
from ..services.ipc import IPCMonitor


class DashboardScreen(Screen):
    """Main dashboard with system overview"""

    CSS = """
    DashboardScreen {
        layout: grid;
        grid-size: 2 3;
        grid-gutter: 1;
        padding: 1;
    }

    #health-panel {
        column-span: 1;
        row-span: 1;
        border: solid $primary;
        padding: 1;
    }

    #stats-panel {
        column-span: 1;
        row-span: 1;
        border: solid $primary;
        padding: 1;
    }

    #progress-panel {
        column-span: 2;
        row-span: 1;
        border: solid $primary;
        padding: 1;
    }

    #activity-panel {
        column-span: 1;
        row-span: 1;
        border: solid $primary;
        padding: 1;
    }

    #recent-panel {
        column-span: 1;
        row-span: 1;
        border: solid $primary;
        padding: 1;
    }

    .panel-title {
        text-style: bold;
        margin-bottom: 1;
    }

    .recent-item {
        height: 1;
        margin-bottom: 0;
    }

    .quick-actions {
        height: 3;
        margin-top: 1;
    }

    .quick-actions Button {
        margin-right: 1;
    }
    """

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("n", "new_objective", "New Objective"),
        ("w", "show_workers", "Workers"),
        ("p", "show_projects", "Projects"),
        ("t", "show_tasks", "Tasks"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._db = DatabaseClient()
        self._ipc = IPCMonitor()
        self._refresh_task: Optional[asyncio.Task] = None

    def compose(self) -> ComposeResult:
        yield Header()

        with Container(id="health-panel"):
            yield Label("System Health", classes="panel-title")
            yield SystemHealth(id="health-widget")

        with Container(id="stats-panel"):
            yield Label("Statistics", classes="panel-title")
            yield StatsPanel(
                stats={
                    "tasks": StatItem("Total Tasks", 0, color="blue"),
                    "completed": StatItem("Completed", 0, color="green"),
                    "workers": StatItem("Active Workers", 0, color="yellow"),
                    "projects": StatItem("Projects", 0, color="magenta"),
                },
                id="stats-widget",
            )

        with Container(id="progress-panel"):
            yield Label("Task Progress", classes="panel-title")
            yield TaskProgressBar(label="Overall Progress", id="task-progress")
            with Horizontal(classes="quick-actions"):
                yield Button("New Objective", id="btn-new-objective", variant="primary")
                yield Button("View Tasks", id="btn-view-tasks")
                yield Button("View Logs", id="btn-view-logs")

        with Container(id="activity-panel"):
            yield Label("Activity", classes="panel-title")
            yield ActivityChart(title="Task Completions", id="activity-chart")
            yield Sparkline(label="Workers Busy", color="yellow", id="worker-spark")

        with Container(id="recent-panel"):
            yield Label("Recent Activity", classes="panel-title")
            yield Static(id="recent-list")

        yield Footer()

    async def on_mount(self) -> None:
        """Start data refresh loop"""
        await self._db.connect()
        await self._refresh_data()
        self._refresh_task = asyncio.create_task(self._refresh_loop())

    async def on_unmount(self) -> None:
        """Stop refresh loop"""
        if self._refresh_task:
            self._refresh_task.cancel()
        await self._db.close()

    async def _refresh_loop(self) -> None:
        """Periodically refresh data"""
        while True:
            try:
                await asyncio.sleep(2)
                await self._refresh_data()
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    async def _refresh_data(self) -> None:
        """Refresh all dashboard data"""
        try:
            # Get task stats
            stats = await self._db.get_task_stats()

            # Update progress bar
            progress = self.query_one("#task-progress", TaskProgressBar)
            progress.update_stats(
                total=stats.get("total", 0),
                completed=stats.get("completed", 0),
                failed=stats.get("failed", 0),
                running=stats.get("running", 0),
            )

            # Update stats panel
            stats_widget = self.query_one("#stats-widget", StatsPanel)
            stats_widget.update_stat("tasks", stats.get("total", 0))
            stats_widget.update_stat("completed", stats.get("completed", 0))

            # Get worker stats
            workers = await self._ipc.get_all_worker_status()
            busy_count = sum(1 for w in workers if w.status == "busy")
            online_count = sum(1 for w in workers if w.status != "offline")

            stats_widget.update_stat("workers", f"{busy_count}/{online_count}")

            # Update health widget
            health = await self._ipc.get_system_health()
            health_widget = self.query_one("#health-widget", SystemHealth)
            health_widget.update_health(
                workers_online=online_count,
                workers_total=len(workers),
            )

            # Update activity sparkline
            worker_spark = self.query_one("#worker-spark", Sparkline)
            worker_spark.add_value(busy_count)

            # Update activity chart
            activity = self.query_one("#activity-chart", ActivityChart)
            activity.add_activity(stats.get("completed", 0))

            # Update recent activity
            recent = await self._get_recent_activity()
            recent_list = self.query_one("#recent-list", Static)
            recent_list.update(recent)

        except Exception as e:
            pass

    async def _get_recent_activity(self) -> str:
        """Get recent activity text"""
        try:
            tasks = await self._db.get_tasks(limit=5)
            lines = []
            for task in tasks[:5]:
                status_icon = {
                    "completed": "[green]✓[/]",
                    "failed": "[red]✗[/]",
                    "in_progress": "[yellow]●[/]",
                    "pending": "[dim]○[/]",
                }.get(task.status, "?")

                title = task.title[:35] + "..." if len(task.title) > 35 else task.title
                lines.append(f"{status_icon} {title}")

            return "\n".join(lines) if lines else "[dim]No recent activity[/]"
        except Exception:
            return "[dim]Unable to load activity[/]"

    def action_refresh(self) -> None:
        """Refresh data"""
        asyncio.create_task(self._refresh_data())

    def action_new_objective(self) -> None:
        """Show new objective dialog"""
        self.app.push_screen("objectives")

    def action_show_workers(self) -> None:
        """Switch to workers screen"""
        self.app.switch_screen("workers")

    def action_show_projects(self) -> None:
        """Switch to projects screen"""
        self.app.switch_screen("projects")

    def action_show_tasks(self) -> None:
        """Switch to tasks screen"""
        self.app.switch_screen("tasks")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        button_actions = {
            "btn-new-objective": lambda: self.app.push_screen("objectives"),
            "btn-view-tasks": lambda: self.app.switch_screen("tasks"),
            "btn-view-logs": lambda: self.app.switch_screen("logs"),
        }
        action = button_actions.get(event.button.id)
        if action:
            action()
