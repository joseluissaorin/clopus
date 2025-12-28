"""TUI Screens"""

from .dashboard import DashboardScreen
from .workers import WorkersScreen
from .projects import ProjectsScreen
from .tasks import TasksScreen
from .browser import BrowserScreen
from .logs import LogsScreen
from .objectives import ObjectivesScreen
from .memory import MemoryScreen
from .questions import QuestionsScreen
from .config import ConfigScreen

__all__ = [
    "DashboardScreen",
    "WorkersScreen",
    "ProjectsScreen",
    "TasksScreen",
    "BrowserScreen",
    "LogsScreen",
    "ObjectivesScreen",
    "MemoryScreen",
    "QuestionsScreen",
    "ConfigScreen",
]
