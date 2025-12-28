"""Projects screen - project management"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Header, Footer, Label, Button, DataTable, Input
from textual.containers import Horizontal, Vertical, Container
from textual.reactive import reactive
from typing import Optional, List
import asyncio
import webbrowser

from ..widgets.project_tree import ProjectTree, ProjectInfo, ProjectDetails
from ..widgets.progress_bar import ValidationProgressBar
from ..services.orchestrator import OrchestratorClient
from ..services.database import DatabaseClient


class ProjectsScreen(Screen):
    """Project management screen"""

    CSS = """
    ProjectsScreen {
        layout: grid;
        grid-size: 3 1;
        grid-gutter: 1;
        padding: 1;
    }

    #project-list {
        column-span: 1;
        border: solid $primary;
        padding: 1;
    }

    #project-detail {
        column-span: 1;
        border: solid $primary;
        padding: 1;
    }

    #project-tasks {
        column-span: 1;
        border: solid $primary;
        padding: 1;
    }

    .panel-title {
        text-style: bold;
        margin-bottom: 1;
    }

    #project-actions {
        height: auto;
        margin-top: 1;
    }

    #project-actions Button {
        margin-right: 1;
        margin-bottom: 1;
    }

    #validation-status {
        margin-top: 1;
    }

    .status-running { color: $warning; }
    .status-completed { color: $success; }
    .status-failed { color: $error; }
    """

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("escape", "go_back", "Back"),
        ("o", "open_browser", "Open in Browser"),
        ("d", "delete_project", "Delete"),
    ]

    selected_project: reactive[Optional[ProjectInfo]] = reactive(None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._orchestrator = OrchestratorClient()
        self._db = DatabaseClient()
        self._refresh_task: Optional[asyncio.Task] = None
        self._projects: List[ProjectInfo] = []

    def compose(self) -> ComposeResult:
        yield Header()

        with Container(id="project-list"):
            yield Label("Projects", classes="panel-title")
            yield DataTable(id="projects-table")

        with Container(id="project-detail"):
            yield Label("Project Details", classes="panel-title")
            yield Static(id="project-info")
            with Horizontal(id="project-actions"):
                yield Button("Open", id="btn-open", variant="primary")
                yield Button("Start Server", id="btn-start")
                yield Button("Stop Server", id="btn-stop")
                yield Button("Delete", id="btn-delete", variant="error")
            yield Label("Validation", classes="panel-title", id="validation-title")
            yield ValidationProgressBar(id="validation-status")

        with Container(id="project-tasks"):
            yield Label("Project Tasks", classes="panel-title")
            yield DataTable(id="project-tasks-table")

        yield Footer()

    async def on_mount(self) -> None:
        """Set up tables and start refresh"""
        # Projects table
        table = self.query_one("#projects-table", DataTable)
        table.add_columns("Name", "Status", "Port", "Progress")
        table.cursor_type = "row"

        # Tasks table
        tasks_table = self.query_one("#project-tasks-table", DataTable)
        tasks_table.add_columns("Title", "Status")
        tasks_table.cursor_type = "row"

        await self._db.connect()
        await self._refresh_projects()
        self._refresh_task = asyncio.create_task(self._refresh_loop())

    async def on_unmount(self) -> None:
        """Stop refresh loop"""
        if self._refresh_task:
            self._refresh_task.cancel()
        await self._db.close()

    async def _refresh_loop(self) -> None:
        """Periodically refresh project data"""
        while True:
            try:
                await asyncio.sleep(5)
                await self._refresh_projects()
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    async def _refresh_projects(self) -> None:
        """Refresh project list"""
        try:
            raw_projects = await self._orchestrator.get_workspace_projects()

            self._projects = []
            for p in raw_projects:
                # Get task counts from database
                project_info = await self._db.get_project_info(p["name"])

                self._projects.append(ProjectInfo(
                    name=p["name"],
                    path=p["path"],
                    status=p.get("status", "unknown"),
                    port=p.get("port"),
                    has_package_json=p.get("has_package_json", False),
                    has_requirements=p.get("has_requirements", False),
                    has_clopus=p.get("has_clopus", False),
                    task_count=project_info.task_count if project_info else 0,
                    completed_tasks=project_info.completed_tasks if project_info else 0,
                ))

            table = self.query_one("#projects-table", DataTable)
            table.clear()

            for project in self._projects:
                status_display = self._format_status(project.status)
                port_display = str(project.port) if project.port else "-"
                progress = f"{project.completed_tasks}/{project.task_count}"

                table.add_row(
                    project.name,
                    status_display,
                    port_display,
                    progress,
                    key=project.path,
                )

        except Exception:
            pass

    def _format_status(self, status: str) -> str:
        """Format status with color"""
        status_colors = {
            "in_progress": "[yellow]In Progress[/]",
            "completed": "[green]Completed[/]",
            "failed": "[red]Failed[/]",
            "pending": "[dim]Pending[/]",
        }
        return status_colors.get(status, status)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle project selection"""
        if event.row_key and event.data_table.id == "projects-table":
            project = next(
                (p for p in self._projects if p.path == event.row_key.value),
                None
            )
            if project:
                self.selected_project = project
                asyncio.create_task(self._update_project_detail())
                asyncio.create_task(self._load_project_tasks())

    async def _update_project_detail(self) -> None:
        """Update project detail panel"""
        if not self.selected_project:
            return

        p = self.selected_project
        info = self.query_one("#project-info", Static)

        lines = [
            f"[bold]{p.name}[/]",
            f"",
            f"[dim]Path:[/] {p.path}",
            f"[dim]Status:[/] {self._format_status(p.status)}",
        ]

        if p.port:
            lines.append(f"[dim]URL:[/] http://localhost:{p.port}")

        stack = []
        if p.has_package_json:
            stack.append("Node.js")
        if p.has_requirements:
            stack.append("Python")
        if stack:
            lines.append(f"[dim]Stack:[/] {', '.join(stack)}")

        if p.task_count > 0:
            percent = (p.completed_tasks / p.task_count) * 100
            lines.append(f"[dim]Progress:[/] {p.completed_tasks}/{p.task_count} ({percent:.0f}%)")

        info.update("\n".join(lines))

        # Update validation status
        validation = await self._get_validation_status()
        val_widget = self.query_one("#validation-status", ValidationProgressBar)
        val_widget.update_stages(validation)

    async def _get_validation_status(self) -> dict:
        """Get validation status for selected project"""
        # This would come from the project state file
        return {
            "syntax": "passed",
            "lint": "passed",
            "build": "passed",
            "unit_tests": "passed",
            "integration_tests": "pending",
            "e2e_tests": "pending",
            "security": "pending",
            "review": "pending",
        }

    async def _load_project_tasks(self) -> None:
        """Load tasks for selected project"""
        if not self.selected_project:
            return

        tasks = await self._db.get_project_tasks(self.selected_project.name)

        table = self.query_one("#project-tasks-table", DataTable)
        table.clear()

        for task in tasks[:20]:  # Limit to 20
            status_display = self._format_task_status(task.status)
            title = task.title[:30] + "..." if len(task.title) > 30 else task.title
            table.add_row(title, status_display, key=task.id)

    def _format_task_status(self, status: str) -> str:
        """Format task status"""
        colors = {
            "completed": "[green]Done[/]",
            "in_progress": "[yellow]Running[/]",
            "failed": "[red]Failed[/]",
            "pending": "[dim]Pending[/]",
        }
        return colors.get(status, status)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if not self.selected_project:
            return

        if event.button.id == "btn-open":
            self._open_in_browser()
        elif event.button.id == "btn-start":
            asyncio.create_task(self._start_server())
        elif event.button.id == "btn-stop":
            asyncio.create_task(self._stop_server())
        elif event.button.id == "btn-delete":
            asyncio.create_task(self._delete_project())

    def _open_in_browser(self) -> None:
        """Open project in browser"""
        if self.selected_project and self.selected_project.port:
            url = f"http://localhost:{self.selected_project.port}"
            webbrowser.open(url)
            self.notify(f"Opening {url}")

    async def _start_server(self) -> None:
        """Start dev server"""
        if self.selected_project:
            port = await self._orchestrator.start_dev_server(self.selected_project.path)
            if port:
                self.notify(f"Server started on port {port}")
            else:
                self.notify("Failed to start server", severity="error")

    async def _stop_server(self) -> None:
        """Stop dev server"""
        if self.selected_project:
            success = await self._orchestrator.stop_dev_server(self.selected_project.path)
            if success:
                self.notify("Server stopped")
            else:
                self.notify("Failed to stop server", severity="error")

    async def _delete_project(self) -> None:
        """Delete project (move to trash)"""
        if self.selected_project:
            success = await self._orchestrator.delete_project(self.selected_project.path)
            if success:
                self.notify(f"Project {self.selected_project.name} deleted")
                await self._refresh_projects()
            else:
                self.notify("Failed to delete project", severity="error")

    def action_refresh(self) -> None:
        """Refresh projects"""
        asyncio.create_task(self._refresh_projects())

    def action_go_back(self) -> None:
        """Go back to dashboard"""
        self.app.switch_screen("dashboard")

    def action_open_browser(self) -> None:
        """Open in browser"""
        self._open_in_browser()

    def action_delete_project(self) -> None:
        """Delete project"""
        asyncio.create_task(self._delete_project())
