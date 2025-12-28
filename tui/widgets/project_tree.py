"""Project tree widget for browsing projects"""

from textual.app import ComposeResult
from textual.widgets import Static, Tree, Label
from textual.containers import Vertical
from textual.reactive import reactive
from textual.message import Message
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ProjectInfo:
    """Project information for tree display"""
    name: str
    path: str
    status: str = "unknown"
    port: Optional[int] = None
    has_package_json: bool = False
    has_requirements: bool = False
    has_clopus: bool = False
    task_count: int = 0
    completed_tasks: int = 0


class ProjectTree(Static):
    """Tree view of workspace projects"""

    DEFAULT_CSS = """
    ProjectTree {
        width: 100%;
        height: 100%;
    }

    ProjectTree .project-header {
        width: 100%;
        height: 2;
        background: $surface;
        padding: 0 1;
    }

    ProjectTree Tree {
        width: 100%;
        height: 1fr;
    }

    ProjectTree Tree:focus {
        border: solid $primary;
    }
    """

    class ProjectSelected(Message):
        """Sent when a project is selected"""
        def __init__(self, project: ProjectInfo) -> None:
            self.project = project
            super().__init__()

    class ProjectAction(Message):
        """Sent when an action is requested on a project"""
        def __init__(self, project_path: str, action: str) -> None:
            self.project_path = project_path
            self.action = action
            super().__init__()

    def __init__(self, projects: List[ProjectInfo] = None, **kwargs):
        super().__init__(**kwargs)
        self._projects = projects or []

    def compose(self) -> ComposeResult:
        with Vertical(classes="project-header"):
            yield Label("Workspace Projects")

        tree = Tree("Projects", id="project-tree")
        tree.root.expand()
        yield tree

    def on_mount(self) -> None:
        """Populate tree with projects"""
        self._refresh_tree()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle node selection"""
        if event.node.data and isinstance(event.node.data, ProjectInfo):
            self.post_message(self.ProjectSelected(event.node.data))

    def _refresh_tree(self) -> None:
        """Refresh tree with current projects"""
        tree = self.query_one("#project-tree", Tree)
        tree.clear()
        tree.root.expand()

        # Group projects by status
        active = [p for p in self._projects if p.status == "in_progress"]
        completed = [p for p in self._projects if p.status == "completed"]
        other = [p for p in self._projects if p.status not in ("in_progress", "completed")]

        if active:
            active_node = tree.root.add("Active", expand=True)
            for project in active:
                self._add_project_node(active_node, project)

        if other:
            other_node = tree.root.add("Pending/Other", expand=True)
            for project in other:
                self._add_project_node(other_node, project)

        if completed:
            completed_node = tree.root.add("Completed", expand=False)
            for project in completed:
                self._add_project_node(completed_node, project)

    def _add_project_node(self, parent, project: ProjectInfo) -> None:
        """Add a project node with details"""
        # Status icon
        status_icons = {
            "in_progress": "🔄",
            "completed": "✅",
            "failed": "❌",
            "pending": "⏳",
            "unknown": "❓",
        }
        icon = status_icons.get(project.status, "📁")

        # Project label
        label = f"{icon} {project.name}"
        if project.port:
            label += f" [:3{project.port}]"

        node = parent.add(label, data=project, expand=False)

        # Add project details as children
        if project.has_package_json:
            node.add("📦 package.json")
        if project.has_requirements:
            node.add("🐍 requirements.txt")
        if project.has_clopus:
            node.add("⚙️ .clopus/")

        # Task progress
        if project.task_count > 0:
            progress = f"📋 Tasks: {project.completed_tasks}/{project.task_count}"
            node.add(progress)

        # Port info
        if project.port:
            node.add(f"🌐 http://localhost:{project.port}")

    def update_projects(self, projects: List[ProjectInfo]) -> None:
        """Update project list"""
        self._projects = projects
        self._refresh_tree()

    def get_selected_project(self) -> Optional[ProjectInfo]:
        """Get currently selected project"""
        tree = self.query_one("#project-tree", Tree)
        if tree.cursor_node and tree.cursor_node.data:
            return tree.cursor_node.data
        return None


class ProjectDetails(Static):
    """Detailed view of a single project"""

    DEFAULT_CSS = """
    ProjectDetails {
        width: 100%;
        height: auto;
        padding: 1;
        border: solid $primary;
    }

    ProjectDetails .detail-row {
        width: 100%;
        height: 1;
    }

    ProjectDetails .detail-label {
        width: 15;
        color: $text-muted;
    }

    ProjectDetails .detail-value {
        width: 1fr;
    }
    """

    def __init__(self, project: Optional[ProjectInfo] = None, **kwargs):
        super().__init__(**kwargs)
        self._project = project

    def compose(self) -> ComposeResult:
        if not self._project:
            yield Label("No project selected")
            return

        p = self._project

        yield Label(f"[bold]{p.name}[/]")
        yield Label("")

        yield Label(f"[dim]Path:[/] {p.path}")
        yield Label(f"[dim]Status:[/] {p.status}")

        if p.port:
            yield Label(f"[dim]URL:[/] http://localhost:{p.port}")

        if p.task_count > 0:
            percent = (p.completed_tasks / p.task_count) * 100
            yield Label(f"[dim]Progress:[/] {p.completed_tasks}/{p.task_count} ({percent:.0f}%)")

        # Tech stack
        stack = []
        if p.has_package_json:
            stack.append("Node.js")
        if p.has_requirements:
            stack.append("Python")
        if stack:
            yield Label(f"[dim]Stack:[/] {', '.join(stack)}")

    def update_project(self, project: Optional[ProjectInfo]) -> None:
        """Update displayed project"""
        self._project = project
        self.refresh()
