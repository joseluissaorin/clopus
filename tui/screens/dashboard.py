"""Dashboard screen - Information-dense modern overview"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Header, Footer, Label, Button, ProgressBar
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.reactive import reactive
from typing import Optional, List, Dict, Any
import asyncio

from ..services.database import DatabaseClient
from ..services.ipc import IPCMonitor, WorkerStatus
from ..services.orchestrator import OrchestratorClient


class MiniStat(Static):
    """Compact stat widget"""
    DEFAULT_CSS = """
    MiniStat {
        width: 1fr;
        height: 3;
        background: $panel;
        border: round $secondary 30%;
        padding: 0 1;
        content-align: center middle;
    }
    """

    def __init__(self, label: str, value: Any = 0, color: str = "primary", **kwargs):
        super().__init__(**kwargs)
        self._label = label
        self._value = value
        self._color = color

    def render(self) -> str:
        return f"[{self._color} bold]{self._value}[/] {self._label}"

    def update_value(self, value: Any):
        self._value = value
        self.refresh()


class WorkerRow(Static):
    """Single worker status row"""
    DEFAULT_CSS = """
    WorkerRow { height: 1; width: 100%; }
    """

    def __init__(self, worker_id: int, role: str, status: str, task_id: str = "", **kwargs):
        super().__init__(**kwargs)
        self.worker_id = worker_id
        self.worker_role = role
        self.worker_status = status
        self.task_id_short = task_id

    def render(self) -> str:
        status_icons = {"busy": "[yellow]●[/]", "idle": "[green]●[/]", "offline": "[red]●[/]"}
        icon = status_icons.get(self.worker_status, "[dim]●[/]")
        role_short = str(self.worker_role)[:6].ljust(6) if self.worker_role else "?".ljust(6)
        task_display = self.task_id_short[:8] if self.task_id_short else "-"
        return f"{icon} {self.worker_id:2d} {role_short} {task_display}"


class ProjectRow(Static):
    """Single project status row"""
    DEFAULT_CSS = """
    ProjectRow { height: 1; width: 100%; }
    """

    def __init__(self, name: str, status: str, stack: str = "", **kwargs):
        super().__init__(**kwargs)
        self._name = name
        self._status = status
        self._stack = stack

    def render(self) -> str:
        status_icons = {
            "in_progress": "[yellow]●[/]",
            "completed": "[green]●[/]",
            "failed": "[red]●[/]",
            "active": "[cyan]●[/]",
            "unknown": "[dim]●[/]",
        }
        icon = status_icons.get(self._status, "[dim]●[/]")
        name_short = self._name[:20] + ".." if len(self._name) > 22 else self._name.ljust(22)
        stack_short = f"[dim]{self._stack[:6]}[/]" if self._stack else ""
        return f"{icon} {name_short} {stack_short}"


class TaskRow(Static):
    """Single task status row"""
    DEFAULT_CSS = """
    TaskRow { height: 1; width: 100%; }
    """

    def __init__(self, title: str, status: str, **kwargs):
        super().__init__(**kwargs)
        self._title = title
        self._status = status

    def render(self) -> str:
        icons = {
            "completed": "[green]✓[/]",
            "failed": "[red]✗[/]",
            "in_progress": "[yellow]●[/]",
            "assigned": "[yellow]●[/]",
            "pending": "[dim]○[/]",
        }
        icon = icons.get(self._status, "[dim]?[/]")
        title = self._title[:38] + ".." if len(self._title) > 40 else self._title
        return f"{icon} {title}"


class ServiceDot(Static):
    """Compact service status indicator"""
    DEFAULT_CSS = """
    ServiceDot { width: auto; height: 1; margin-right: 2; }
    """

    def __init__(self, name: str, status: str = "unknown", **kwargs):
        super().__init__(**kwargs)
        self._name = name
        self._status = status

    def render(self) -> str:
        colors = {"running": "green", "healthy": "green", "stopped": "red", "offline": "red", "unknown": "dim"}
        color = colors.get(self._status, "dim")
        return f"[{color}]●[/] {self._name}"

    def update_status(self, status: str):
        self._status = status
        self.refresh()


class DashboardScreen(Screen):
    """Main dashboard - information dense 3-column layout"""

    CSS = """
    DashboardScreen {
        padding: 0 1;
    }

    #main-container {
        width: 100%;
        height: 100%;
    }

    /* Top stats bar */
    #stats-bar {
        height: 3;
        width: 100%;
        margin-bottom: 1;
    }

    /* Main content - 3 columns */
    #content-row {
        height: 1fr;
        width: 100%;
    }

    #workers-col {
        width: 28;
        background: $surface;
        border: round $primary;
        padding: 0 1;
        margin-right: 1;
    }

    #projects-col {
        width: 1fr;
        background: $surface;
        border: round $primary;
        padding: 0 1;
        margin-right: 1;
    }

    #tasks-col {
        width: 1fr;
        background: $surface;
        border: round $primary;
        padding: 0 1;
    }

    .col-header {
        height: 2;
        text-style: bold;
        color: $primary;
        border-bottom: solid $secondary 30%;
    }

    .col-content {
        height: 1fr;
    }

    /* Bottom bar - services + progress */
    #bottom-bar {
        height: 4;
        width: 100%;
        margin-top: 1;
        background: $surface;
        border: round $primary;
        padding: 0 1;
    }

    #services-row {
        height: 1;
    }

    #progress-row {
        height: 2;
        margin-top: 1;
    }

    #progress-bar {
        width: 1fr;
    }

    #progress-stats {
        width: auto;
        margin-left: 2;
    }

    /* Actions row */
    #actions-row {
        height: 3;
        margin-top: 1;
    }

    #actions-row Button {
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
        self._orchestrator = OrchestratorClient()
        self._refresh_task: Optional[asyncio.Task] = None
        self._workers: List[WorkerStatus] = []
        self._projects: List[Dict] = []

    def compose(self) -> ComposeResult:
        yield Header()

        with Vertical(id="main-container"):
            # Stats bar
            with Horizontal(id="stats-bar"):
                yield MiniStat("Tasks", "0", color="blue", id="stat-tasks")
                yield MiniStat("Done", "0", color="green", id="stat-done")
                yield MiniStat("Run", "0", color="yellow", id="stat-run")
                yield MiniStat("Fail", "0", color="red", id="stat-fail")
                yield MiniStat("Workers", "0/11", color="cyan", id="stat-workers")
                yield MiniStat("Projects", "0", color="magenta", id="stat-projects")

            # Main 3-column content
            with Horizontal(id="content-row"):
                # Workers column
                with Vertical(id="workers-col"):
                    yield Static("Workers", classes="col-header")
                    with ScrollableContainer(classes="col-content", id="workers-list"):
                        yield Static("[dim]Loading...[/]")

                # Projects column
                with Vertical(id="projects-col"):
                    yield Static("Projects (filesystem)", classes="col-header")
                    with ScrollableContainer(classes="col-content", id="projects-list"):
                        yield Static("[dim]Loading...[/]")

                # Tasks column
                with Vertical(id="tasks-col"):
                    yield Static("Recent Tasks", classes="col-header")
                    with ScrollableContainer(classes="col-content", id="tasks-list"):
                        yield Static("[dim]Loading...[/]")

            # Bottom bar
            with Vertical(id="bottom-bar"):
                with Horizontal(id="services-row"):
                    yield ServiceDot("Orchestrator", id="svc-orch")
                    yield ServiceDot("PostgreSQL", id="svc-pg")
                    yield ServiceDot("Redis", id="svc-redis")
                    yield ServiceDot("Database", id="svc-db")
                    yield Static("", id="connection-info")

                with Horizontal(id="progress-row"):
                    yield ProgressBar(total=100, show_eta=False, id="progress-bar")
                    yield Static("[green]0[/]/[blue]0[/] tasks", id="progress-stats")

            # Actions
            with Horizontal(id="actions-row"):
                yield Button("New Objective", id="btn-objective", variant="primary")
                yield Button("Workers", id="btn-workers")
                yield Button("Projects", id="btn-projects")
                yield Button("Tasks", id="btn-tasks")
                yield Button("Logs", id="btn-logs")

        yield Footer()

    async def on_mount(self) -> None:
        """Initialize and start refresh"""
        await self._db.connect()
        await self._refresh_data()
        self._refresh_task = asyncio.create_task(self._refresh_loop())

    async def on_unmount(self) -> None:
        """Cleanup"""
        if self._refresh_task:
            self._refresh_task.cancel()
        await self._db.close()

    async def _refresh_loop(self) -> None:
        """Periodic refresh"""
        while True:
            try:
                await asyncio.sleep(2)
                await self._refresh_data()
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    async def _refresh_data(self) -> None:
        """Refresh all data"""
        try:
            # Task stats
            stats = await self._db.get_task_stats()
            total = stats.get("total", 0)
            completed = stats.get("completed", 0)
            failed = stats.get("failed", 0)
            running = stats.get("running", 0) + stats.get("in_progress", 0)

            self._update_stat("stat-tasks", total)
            self._update_stat("stat-done", completed)
            self._update_stat("stat-run", running)
            self._update_stat("stat-fail", failed)

            # Progress bar
            progress = self.query_one("#progress-bar", ProgressBar)
            progress.total = max(1, total)
            progress.progress = completed

            self._update_static("#progress-stats", f"[green]{completed}[/]/[blue]{total}[/] tasks")

            # Workers
            self._workers = await self._ipc.get_all_worker_status()
            online = sum(1 for w in self._workers if w.status != "offline")
            self._update_stat("stat-workers", f"{online}/11")
            await self._update_workers_list()

            # Projects from filesystem
            self._projects = await self._orchestrator.get_workspace_projects()
            self._update_stat("stat-projects", len(self._projects))
            await self._update_projects_list()

            # Recent tasks
            await self._update_tasks_list()

            # Services
            services = await self._ipc.get_docker_services_status()
            self._update_service("svc-orch", services.get("orchestrator", "unknown"))
            self._update_service("svc-pg", services.get("postgres", "unknown"))
            self._update_service("svc-redis", services.get("redis", "unknown"))
            db_status = "healthy" if self._db.is_connected else "offline"
            self._update_service("svc-db", db_status)

            # Connection info
            busy = sum(1 for w in self._workers if w.status == "busy")
            self._update_static("#connection-info", f"[dim]| {busy} busy, {len(self._projects)} projects[/]")

        except Exception:
            pass

    def _update_stat(self, stat_id: str, value: Any) -> None:
        try:
            stat = self.query_one(f"#{stat_id}", MiniStat)
            stat.update_value(value)
        except Exception:
            pass

    def _update_static(self, selector: str, content: str) -> None:
        try:
            widget = self.query_one(selector, Static)
            widget.update(content)
        except Exception:
            pass

    def _update_service(self, service_id: str, status: str) -> None:
        try:
            svc = self.query_one(f"#{service_id}", ServiceDot)
            svc.update_status(status)
        except Exception:
            pass

    async def _update_workers_list(self) -> None:
        """Update workers list"""
        try:
            container = self.query_one("#workers-list", ScrollableContainer)
            container.remove_children()

            if not self._workers:
                container.mount(Static("[dim]No workers found[/]"))
                return

            for w in self._workers:
                # Ensure task_id is a string - handle any unexpected types
                raw_task = w.task_id
                if raw_task is None:
                    task_short = ""
                elif isinstance(raw_task, str):
                    task_short = raw_task[:8]
                else:
                    # Log unexpected types and convert
                    task_short = ""
                container.mount(WorkerRow(w.id, w.role or "unknown", w.status or "unknown", task_short))
        except Exception:
            pass

    async def _update_projects_list(self) -> None:
        """Update projects list from filesystem"""
        try:
            container = self.query_one("#projects-list", ScrollableContainer)
            container.remove_children()

            if not self._projects:
                container.mount(Static("[dim]No projects in ~/Dev/clopus-projects/[/]"))
                return

            for p in self._projects[:15]:  # Limit to 15
                stack = ""
                if p.get("has_package_json"):
                    stack = "Node"
                elif p.get("has_requirements"):
                    stack = "Python"
                status = p.get("status", "unknown")
                container.mount(ProjectRow(p["name"], status, stack))
        except Exception:
            pass

    async def _update_tasks_list(self) -> None:
        """Update tasks list"""
        try:
            tasks = await self._db.get_tasks(limit=15)
            container = self.query_one("#tasks-list", ScrollableContainer)
            container.remove_children()

            if not tasks:
                container.mount(Static("[dim]No tasks in database[/]"))
                return

            for t in tasks:
                container.mount(TaskRow(t.title, t.status))
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        actions = {
            "btn-objective": lambda: self.app.push_screen("objectives"),
            "btn-workers": lambda: self.app.switch_screen("workers"),
            "btn-projects": lambda: self.app.switch_screen("projects"),
            "btn-tasks": lambda: self.app.switch_screen("tasks"),
            "btn-logs": lambda: self.app.switch_screen("logs"),
        }
        action = actions.get(event.button.id)
        if action:
            action()

    def action_refresh(self) -> None:
        asyncio.create_task(self._refresh_data())
        self.notify("Refreshing...")

    def action_new_objective(self) -> None:
        self.app.push_screen("objectives")

    def action_show_workers(self) -> None:
        self.app.switch_screen("workers")

    def action_show_projects(self) -> None:
        self.app.switch_screen("projects")

    def action_show_tasks(self) -> None:
        self.app.switch_screen("tasks")
