"""Progress bar widget for tasks and objectives"""

from textual.widgets import Static, ProgressBar as TextualProgressBar
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from rich.text import Text


class TaskProgressBar(Static):
    """Progress bar showing task completion with stats"""

    DEFAULT_CSS = """
    TaskProgressBar {
        width: 100%;
        height: auto;
        padding: 1;
    }

    TaskProgressBar .progress-label {
        width: 100%;
        height: 1;
        margin-bottom: 1;
    }

    TaskProgressBar .progress-stats {
        width: 100%;
        height: 1;
        margin-top: 1;
    }

    TaskProgressBar .stat-item {
        width: auto;
        margin-right: 3;
    }

    TaskProgressBar .stat-completed {
        color: $success;
    }

    TaskProgressBar .stat-pending {
        color: $warning;
    }

    TaskProgressBar .stat-failed {
        color: $error;
    }

    TaskProgressBar .stat-running {
        color: $primary;
    }
    """

    total: reactive[int] = reactive(0)
    completed: reactive[int] = reactive(0)
    failed: reactive[int] = reactive(0)
    running: reactive[int] = reactive(0)
    pending: reactive[int] = reactive(0)
    label: reactive[str] = reactive("Progress")

    def __init__(
        self,
        total: int = 0,
        completed: int = 0,
        failed: int = 0,
        running: int = 0,
        label: str = "Progress",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.total = total
        self.completed = completed
        self.failed = failed
        self.running = running
        self.pending = max(0, total - completed - failed - running)
        self.label = label

    def compose(self) -> ComposeResult:
        yield Static(self.label, classes="progress-label")
        yield TextualProgressBar(total=max(1, self.total), show_eta=False)
        with Horizontal(classes="progress-stats"):
            yield Static(
                f"[green]Completed: {self.completed}[/]",
                classes="stat-item stat-completed",
            )
            yield Static(
                f"[blue]Running: {self.running}[/]",
                classes="stat-item stat-running",
            )
            yield Static(
                f"[yellow]Pending: {self.pending}[/]",
                classes="stat-item stat-pending",
            )
            yield Static(
                f"[red]Failed: {self.failed}[/]",
                classes="stat-item stat-failed",
            )

    def on_mount(self) -> None:
        """Update progress bar on mount"""
        self._update_progress()

    def _update_progress(self) -> None:
        """Update the progress bar value"""
        bar = self.query_one(TextualProgressBar)
        bar.total = max(1, self.total)
        bar.progress = self.completed

    def update_stats(
        self,
        total: int,
        completed: int,
        failed: int = 0,
        running: int = 0,
    ) -> None:
        """Update all stats"""
        self.total = total
        self.completed = completed
        self.failed = failed
        self.running = running
        self.pending = max(0, total - completed - failed - running)
        self._update_progress()
        self.refresh()


class ValidationProgressBar(Static):
    """Progress bar for validation pipeline stages"""

    DEFAULT_CSS = """
    ValidationProgressBar {
        width: 100%;
        height: auto;
        padding: 1;
    }

    ValidationProgressBar .stage {
        width: 100%;
        height: 1;
        margin-bottom: 1;
    }

    ValidationProgressBar .stage-name {
        width: 20;
    }

    ValidationProgressBar .stage-status {
        width: auto;
    }

    ValidationProgressBar .stage-passed {
        color: $success;
    }

    ValidationProgressBar .stage-failed {
        color: $error;
    }

    ValidationProgressBar .stage-running {
        color: $warning;
    }

    ValidationProgressBar .stage-pending {
        color: $text-muted;
    }
    """

    VALIDATION_STAGES = [
        "syntax",
        "lint",
        "build",
        "unit_tests",
        "integration_tests",
        "e2e_tests",
        "security",
        "review",
    ]

    def __init__(self, stage_results: dict = None, **kwargs):
        super().__init__(**kwargs)
        self.stage_results = stage_results or {}

    def compose(self) -> ComposeResult:
        for stage in self.VALIDATION_STAGES:
            status = self.stage_results.get(stage, "pending")
            status_icon = self._get_status_icon(status)
            status_class = f"stage-{status}"

            with Horizontal(classes="stage"):
                yield Static(stage.replace("_", " ").title(), classes="stage-name")
                yield Static(status_icon, classes=f"stage-status {status_class}")

    def _get_status_icon(self, status: str) -> str:
        icons = {
            "passed": "[green]✓ Passed[/]",
            "failed": "[red]✗ Failed[/]",
            "running": "[yellow]● Running[/]",
            "pending": "[gray]○ Pending[/]",
            "skipped": "[gray]- Skipped[/]",
        }
        return icons.get(status, "[gray]? Unknown[/]")

    def update_stages(self, stage_results: dict) -> None:
        """Update stage results"""
        self.stage_results = stage_results
        self.refresh()
