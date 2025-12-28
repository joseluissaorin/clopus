"""Sparkline widget for mini charts"""

from textual.widgets import Static
from textual.reactive import reactive
from typing import List, Optional
from collections import deque


class Sparkline(Static):
    """Mini inline chart for showing trends"""

    DEFAULT_CSS = """
    Sparkline {
        width: 100%;
        height: 1;
    }
    """

    # Unicode block characters for sparklines
    BLOCKS = " ▁▂▃▄▅▆▇█"

    data: reactive[List[float]] = reactive([])
    max_points: reactive[int] = reactive(50)
    color: reactive[str] = reactive("green")

    def __init__(
        self,
        data: List[float] = None,
        max_points: int = 50,
        color: str = "green",
        label: str = "",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._data = deque(data or [], maxlen=max_points)
        self.max_points = max_points
        self.color = color
        self.label = label

    def render(self) -> str:
        """Render the sparkline"""
        if not self._data:
            return f"[dim]{self.label}: No data[/]" if self.label else "[dim]No data[/]"

        # Normalize data to 0-8 range for block selection
        data_list = list(self._data)
        min_val = min(data_list)
        max_val = max(data_list)
        range_val = max_val - min_val if max_val != min_val else 1

        sparkline = ""
        for value in data_list:
            normalized = (value - min_val) / range_val
            block_index = int(normalized * 8)
            block_index = max(0, min(8, block_index))
            sparkline += self.BLOCKS[block_index]

        # Format with label and current value
        current = data_list[-1] if data_list else 0
        result = f"[{self.color}]{sparkline}[/]"

        if self.label:
            result = f"{self.label}: {result} [{self.color}]{current:.1f}[/]"

        return result

    def add_value(self, value: float) -> None:
        """Add a new value to the sparkline"""
        self._data.append(value)
        self.refresh()

    def add_values(self, values: List[float]) -> None:
        """Add multiple values"""
        for value in values:
            self._data.append(value)
        self.refresh()

    def clear(self) -> None:
        """Clear all data"""
        self._data.clear()
        self.refresh()

    def set_data(self, data: List[float]) -> None:
        """Replace all data"""
        self._data = deque(data, maxlen=self.max_points)
        self.refresh()


class MultiSparkline(Static):
    """Multiple sparklines stacked vertically"""

    DEFAULT_CSS = """
    MultiSparkline {
        width: 100%;
        height: auto;
    }

    MultiSparkline .sparkline-row {
        width: 100%;
        height: 1;
    }
    """

    def __init__(self, series: dict = None, max_points: int = 50, **kwargs):
        super().__init__(**kwargs)
        self._series = series or {}
        self._max_points = max_points
        self._data: dict[str, deque] = {
            name: deque(maxlen=max_points) for name in self._series
        }

    def compose(self):
        for name, config in self._series.items():
            yield Sparkline(
                label=config.get("label", name),
                color=config.get("color", "green"),
                max_points=self._max_points,
                id=f"spark-{name}",
                classes="sparkline-row",
            )

    def add_value(self, series_name: str, value: float) -> None:
        """Add value to a specific series"""
        try:
            sparkline = self.query_one(f"#spark-{series_name}", Sparkline)
            sparkline.add_value(value)
        except Exception:
            pass

    def add_values(self, values: dict) -> None:
        """Add values to multiple series"""
        for name, value in values.items():
            self.add_value(name, value)


class ActivityChart(Static):
    """Activity chart showing recent activity levels"""

    DEFAULT_CSS = """
    ActivityChart {
        width: 100%;
        height: 4;
        padding: 0 1;
    }

    ActivityChart .chart-title {
        width: 100%;
        height: 1;
        text-style: bold;
    }

    ActivityChart .chart-legend {
        width: 100%;
        height: 1;
        color: $text-muted;
    }
    """

    ACTIVITY_BLOCKS = ["░", "▒", "▓", "█"]

    def __init__(
        self,
        title: str = "Activity",
        data: List[int] = None,
        max_activity: int = 10,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.title = title
        self._data = data or []
        self._max_activity = max_activity

    def render(self) -> str:
        """Render the activity chart"""
        lines = [f"[bold]{self.title}[/]"]

        # Create activity bars
        if self._data:
            chart = ""
            for value in self._data[-60:]:  # Last 60 data points
                normalized = min(value / max(1, self._max_activity), 1.0)
                block_idx = int(normalized * 3)
                block_idx = max(0, min(3, block_idx))

                # Color based on activity level
                if normalized < 0.25:
                    color = "dim"
                elif normalized < 0.5:
                    color = "green"
                elif normalized < 0.75:
                    color = "yellow"
                else:
                    color = "red"

                chart += f"[{color}]{self.ACTIVITY_BLOCKS[block_idx]}[/]"

            lines.append(chart)
        else:
            lines.append("[dim]No activity data[/]")

        # Legend
        lines.append("[dim]Low ░▒▓█ High[/]")

        return "\n".join(lines)

    def add_activity(self, value: int) -> None:
        """Add an activity value"""
        self._data.append(value)
        if len(self._data) > 120:
            self._data = self._data[-120:]
        self.refresh()

    def set_data(self, data: List[int]) -> None:
        """Set activity data"""
        self._data = data[-120:] if len(data) > 120 else data
        self.refresh()
