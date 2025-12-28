"""Log viewer widget with filtering and auto-scroll"""

from textual.app import ComposeResult
from textual.widgets import Static, Input, RichLog, Checkbox
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.message import Message
from typing import List, Optional
from datetime import datetime
import re


class LogViewer(Static):
    """Real-time log viewer with filtering"""

    DEFAULT_CSS = """
    LogViewer {
        width: 100%;
        height: 100%;
    }

    LogViewer .log-controls {
        width: 100%;
        height: 3;
        margin-bottom: 1;
    }

    LogViewer .log-search {
        width: 1fr;
        margin-right: 1;
    }

    LogViewer .log-checkbox {
        width: auto;
        margin-right: 2;
    }

    LogViewer RichLog {
        width: 100%;
        height: 1fr;
        border: solid $primary;
    }
    """

    auto_scroll: reactive[bool] = reactive(True)
    filter_text: reactive[str] = reactive("")
    show_debug: reactive[bool] = reactive(False)
    show_info: reactive[bool] = reactive(True)
    show_warning: reactive[bool] = reactive(True)
    show_error: reactive[bool] = reactive(True)

    # Log level patterns
    LEVEL_PATTERNS = {
        "debug": re.compile(r"\bDEBUG\b", re.IGNORECASE),
        "info": re.compile(r"\bINFO\b", re.IGNORECASE),
        "warning": re.compile(r"\b(WARNING|WARN)\b", re.IGNORECASE),
        "error": re.compile(r"\b(ERROR|CRITICAL|FATAL)\b", re.IGNORECASE),
    }

    def __init__(self, max_lines: int = 1000, **kwargs):
        super().__init__(**kwargs)
        self._max_lines = max_lines
        self._all_logs: List[str] = []

    def compose(self) -> ComposeResult:
        with Horizontal(classes="log-controls"):
            yield Input(
                placeholder="Filter logs...",
                classes="log-search",
                id="log-filter",
            )
            yield Checkbox("Debug", value=self.show_debug, id="show-debug", classes="log-checkbox")
            yield Checkbox("Info", value=self.show_info, id="show-info", classes="log-checkbox")
            yield Checkbox("Warn", value=self.show_warning, id="show-warn", classes="log-checkbox")
            yield Checkbox("Error", value=self.show_error, id="show-error", classes="log-checkbox")
            yield Checkbox("Auto-scroll", value=self.auto_scroll, id="auto-scroll", classes="log-checkbox")

        yield RichLog(id="log-output", highlight=True, markup=True)

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle filter input changes"""
        if event.input.id == "log-filter":
            self.filter_text = event.value
            self._refresh_logs()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle checkbox changes"""
        checkbox_map = {
            "show-debug": "show_debug",
            "show-info": "show_info",
            "show-warn": "show_warning",
            "show-error": "show_error",
            "auto-scroll": "auto_scroll",
        }
        if event.checkbox.id in checkbox_map:
            setattr(self, checkbox_map[event.checkbox.id], event.value)
            if event.checkbox.id != "auto-scroll":
                self._refresh_logs()

    def add_log(self, line: str, timestamp: Optional[datetime] = None) -> None:
        """Add a log line"""
        if timestamp:
            line = f"[dim]{timestamp.strftime('%H:%M:%S')}[/] {line}"

        self._all_logs.append(line)

        # Trim if over max
        if len(self._all_logs) > self._max_lines:
            self._all_logs = self._all_logs[-self._max_lines:]

        # Check if line should be displayed
        if self._should_show_log(line):
            log = self.query_one("#log-output", RichLog)
            log.write(self._colorize_log(line))

            if self.auto_scroll:
                log.scroll_end(animate=False)

    def add_logs(self, lines: List[str]) -> None:
        """Add multiple log lines"""
        for line in lines:
            self.add_log(line)

    def _should_show_log(self, line: str) -> bool:
        """Check if log line should be shown based on filters"""
        # Text filter
        if self.filter_text and self.filter_text.lower() not in line.lower():
            return False

        # Level filters
        level = self._get_log_level(line)
        if level == "debug" and not self.show_debug:
            return False
        if level == "info" and not self.show_info:
            return False
        if level == "warning" and not self.show_warning:
            return False
        if level == "error" and not self.show_error:
            return False

        return True

    def _get_log_level(self, line: str) -> str:
        """Detect log level from line"""
        for level, pattern in self.LEVEL_PATTERNS.items():
            if pattern.search(line):
                return level
        return "info"

    def _colorize_log(self, line: str) -> str:
        """Add color markup to log line"""
        level = self._get_log_level(line)
        colors = {
            "debug": "dim",
            "info": "white",
            "warning": "yellow",
            "error": "red",
        }
        color = colors.get(level, "white")

        # Highlight keywords
        line = re.sub(r"\bERROR\b", "[bold red]ERROR[/]", line, flags=re.IGNORECASE)
        line = re.sub(r"\bWARNING\b", "[bold yellow]WARNING[/]", line, flags=re.IGNORECASE)
        line = re.sub(r"\bWARN\b", "[bold yellow]WARN[/]", line, flags=re.IGNORECASE)
        line = re.sub(r"\bINFO\b", "[bold blue]INFO[/]", line, flags=re.IGNORECASE)
        line = re.sub(r"\bDEBUG\b", "[dim]DEBUG[/]", line, flags=re.IGNORECASE)

        return line

    def _refresh_logs(self) -> None:
        """Refresh log display with current filters"""
        log = self.query_one("#log-output", RichLog)
        log.clear()

        for line in self._all_logs:
            if self._should_show_log(line):
                log.write(self._colorize_log(line))

        if self.auto_scroll:
            log.scroll_end(animate=False)

    def clear(self) -> None:
        """Clear all logs"""
        self._all_logs.clear()
        log = self.query_one("#log-output", RichLog)
        log.clear()
