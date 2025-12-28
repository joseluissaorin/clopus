"""Stats panel widget for displaying metrics"""

from textual.app import ComposeResult
from textual.widgets import Static, Label
from textual.containers import Horizontal, Vertical, Grid
from textual.reactive import reactive
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class StatItem:
    """Single statistic item"""
    label: str
    value: Any
    unit: str = ""
    color: str = "white"
    trend: Optional[str] = None  # "up", "down", "stable"


class StatsPanel(Static):
    """Panel displaying multiple statistics"""

    DEFAULT_CSS = """
    StatsPanel {
        width: 100%;
        height: auto;
        layout: grid;
        grid-size: 4 1;
        grid-gutter: 1;
        padding: 1;
    }

    StatsPanel .stat-card {
        width: 100%;
        height: 5;
        border: solid $primary;
        padding: 0 1;
    }

    StatsPanel .stat-value {
        width: 100%;
        height: 2;
        text-style: bold;
        content-align: center middle;
    }

    StatsPanel .stat-label {
        width: 100%;
        height: 1;
        color: $text-muted;
        content-align: center middle;
    }

    StatsPanel .stat-trend {
        width: 100%;
        height: 1;
        content-align: center middle;
    }

    StatsPanel .trend-up {
        color: $success;
    }

    StatsPanel .trend-down {
        color: $error;
    }

    StatsPanel .trend-stable {
        color: $text-muted;
    }
    """

    def __init__(self, stats: Dict[str, StatItem] = None, columns: int = 4, **kwargs):
        super().__init__(**kwargs)
        self._stats = stats or {}
        self._columns = columns

    def compose(self) -> ComposeResult:
        for key, stat in self._stats.items():
            with Vertical(classes="stat-card", id=f"stat-{key}"):
                value_text = f"{stat.value}{stat.unit}"
                yield Label(f"[{stat.color}]{value_text}[/]", classes="stat-value")
                yield Label(stat.label, classes="stat-label")
                if stat.trend:
                    trend_icon = self._get_trend_icon(stat.trend)
                    yield Label(trend_icon, classes=f"stat-trend trend-{stat.trend}")

    def _get_trend_icon(self, trend: str) -> str:
        """Get trend indicator"""
        icons = {
            "up": "↑",
            "down": "↓",
            "stable": "→",
        }
        return icons.get(trend, "")

    def update_stat(self, key: str, value: Any, trend: Optional[str] = None) -> None:
        """Update a single statistic"""
        if key in self._stats:
            self._stats[key].value = value
            if trend:
                self._stats[key].trend = trend
            self.refresh()

    def update_stats(self, stats: Dict[str, StatItem]) -> None:
        """Update all statistics"""
        self._stats = stats
        self.refresh()


class SystemHealth(Static):
    """System health overview widget"""

    DEFAULT_CSS = """
    SystemHealth {
        width: 100%;
        height: auto;
        padding: 1;
    }

    SystemHealth .health-header {
        width: 100%;
        height: 1;
        text-style: bold;
        margin-bottom: 1;
    }

    SystemHealth .health-grid {
        width: 100%;
        height: auto;
        layout: grid;
        grid-size: 2 3;
        grid-gutter: 1;
    }

    SystemHealth .health-item {
        width: 100%;
        height: 2;
        border: solid $surface-lighten-1;
        padding: 0 1;
    }

    SystemHealth .health-ok {
        border: solid $success;
    }

    SystemHealth .health-warn {
        border: solid $warning;
    }

    SystemHealth .health-error {
        border: solid $error;
    }
    """

    def __init__(
        self,
        orchestrator: str = "unknown",
        postgres: str = "unknown",
        redis: str = "unknown",
        chromadb: str = "unknown",
        workers_online: int = 0,
        workers_total: int = 11,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._health = {
            "Orchestrator": orchestrator,
            "PostgreSQL": postgres,
            "Redis": redis,
            "ChromaDB": chromadb,
            "Workers": f"{workers_online}/{workers_total}",
        }
        self._workers_online = workers_online
        self._workers_total = workers_total

    def compose(self) -> ComposeResult:
        yield Label("System Health", classes="health-header")

        with Grid(classes="health-grid"):
            for name, status in self._health.items():
                css_class = self._get_status_class(name, status)
                icon = self._get_status_icon(status)
                with Vertical(classes=f"health-item {css_class}"):
                    yield Label(f"{icon} {name}: {status}")

    def _get_status_class(self, name: str, status: str) -> str:
        """Get CSS class based on status"""
        if name == "Workers":
            ratio = self._workers_online / max(1, self._workers_total)
            if ratio >= 0.8:
                return "health-ok"
            elif ratio >= 0.5:
                return "health-warn"
            else:
                return "health-error"

        if status in ("running", "connected", "healthy", "ok"):
            return "health-ok"
        elif status in ("degraded", "slow"):
            return "health-warn"
        else:
            return "health-error"

    def _get_status_icon(self, status: str) -> str:
        """Get status icon"""
        if status in ("running", "connected", "healthy", "ok"):
            return "[green]●[/]"
        elif status in ("degraded", "slow"):
            return "[yellow]●[/]"
        else:
            return "[red]●[/]"

    def update_health(self, **kwargs) -> None:
        """Update health status"""
        for key, value in kwargs.items():
            if key in self._health:
                self._health[key] = value
            elif key == "workers_online":
                self._workers_online = value
                self._health["Workers"] = f"{value}/{self._workers_total}"
            elif key == "workers_total":
                self._workers_total = value
                self._health["Workers"] = f"{self._workers_online}/{value}"
        self.refresh()
