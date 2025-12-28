"""Memory screen - memory system viewer"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Header, Footer, Label, Button, DataTable, Input
from textual.containers import Horizontal, Vertical, Container
from textual.reactive import reactive
from typing import Optional, List, Dict, Any
import asyncio

from ..services.database import DatabaseClient


class MemoryScreen(Screen):
    """Memory system viewer screen"""

    CSS = """
    MemoryScreen {
        layout: grid;
        grid-size: 2 2;
        grid-gutter: 1;
        padding: 1;
    }

    #memory-stats {
        column-span: 2;
        row-span: 1;
        border: solid $primary;
        padding: 1;
    }

    #short-term {
        column-span: 1;
        row-span: 1;
        border: solid $primary;
        padding: 1;
    }

    #long-term {
        column-span: 1;
        row-span: 1;
        border: solid $primary;
        padding: 1;
    }

    .panel-title {
        text-style: bold;
        margin-bottom: 1;
    }

    .stats-grid {
        layout: grid;
        grid-size: 4 1;
        grid-gutter: 1;
        height: 5;
    }

    .stat-card {
        border: solid $surface;
        padding: 1;
        content-align: center middle;
    }

    .stat-value {
        text-style: bold;
    }

    #search-row {
        height: 3;
        margin-bottom: 1;
    }

    #search-row Input {
        width: 1fr;
        margin-right: 1;
    }

    #memories-table {
        height: 1fr;
    }

    #memory-detail {
        height: 1fr;
        border: solid $surface;
        padding: 1;
        overflow-y: auto;
    }

    .memory-actions {
        height: 3;
        margin-top: 1;
    }

    .memory-actions Button {
        margin-right: 1;
    }
    """

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("escape", "go_back", "Back"),
        ("s", "search", "Search"),
        ("c", "cleanup", "Cleanup"),
    ]

    search_query: reactive[str] = reactive("")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._db = DatabaseClient()
        self._memories: List[Dict[str, Any]] = []

    def compose(self) -> ComposeResult:
        yield Header()

        with Container(id="memory-stats"):
            yield Label("Memory System Overview", classes="panel-title")
            with Horizontal(classes="stats-grid"):
                with Vertical(classes="stat-card"):
                    yield Label("Short-term", classes="stat-label")
                    yield Label("0 entries", id="st-count", classes="stat-value")
                with Vertical(classes="stat-card"):
                    yield Label("Long-term", classes="stat-label")
                    yield Label("0 entries", id="lt-count", classes="stat-value")
                with Vertical(classes="stat-card"):
                    yield Label("Decisions", classes="stat-label")
                    yield Label("0", id="decisions-count", classes="stat-value")
                with Vertical(classes="stat-card"):
                    yield Label("Solutions", classes="stat-label")
                    yield Label("0", id="solutions-count", classes="stat-value")

        with Container(id="short-term"):
            yield Label("Short-term Memory (SQLite)", classes="panel-title")
            with Horizontal(id="search-row"):
                yield Input(placeholder="Search memories...", id="memory-search")
                yield Button("Search", id="btn-search")
            yield DataTable(id="memories-table")
            with Horizontal(classes="memory-actions"):
                yield Button("Clear Old", id="btn-clear-old")
                yield Button("Export", id="btn-export")

        with Container(id="long-term"):
            yield Label("Long-term Memory (ChromaDB)", classes="panel-title")
            yield Static(id="memory-detail")
            with Horizontal(classes="memory-actions"):
                yield Button("Query Similar", id="btn-similar")
                yield Button("Consolidate", id="btn-consolidate")

        yield Footer()

    async def on_mount(self) -> None:
        """Set up table and load data"""
        table = self.query_one("#memories-table", DataTable)
        table.add_columns("Type", "Key", "Age", "Size")
        table.cursor_type = "row"

        await self._db.connect()
        await self._refresh_stats()
        await self._load_memories()

    async def on_unmount(self) -> None:
        """Cleanup"""
        await self._db.close()

    async def _refresh_stats(self) -> None:
        """Refresh memory statistics"""
        try:
            stats = await self._db.get_memory_stats()

            st_count = self.query_one("#st-count", Label)
            lt_count = self.query_one("#lt-count", Label)
            decisions = self.query_one("#decisions-count", Label)
            solutions = self.query_one("#solutions-count", Label)

            st_count.update(f"{stats.get('tasks', 0)} entries")
            lt_count.update(f"{stats.get('objectives', 0)} entries")
            decisions.update(str(stats.get('decisions', 0)))
            solutions.update(str(stats.get('questions', 0)))

        except Exception:
            pass

    async def _load_memories(self) -> None:
        """Load memory entries"""
        try:
            self._memories = await self._db.get_recent_memories(limit=50)

            table = self.query_one("#memories-table", DataTable)
            table.clear()

            for memory in self._memories:
                mem_type = memory.get("type", "unknown")
                key = memory.get("key", "")[:20]
                age = self._format_age(memory.get("created_at", ""))
                size = f"{len(str(memory.get('value', '')))} chars"

                table.add_row(
                    mem_type,
                    key,
                    age,
                    size,
                    key=memory.get("id", ""),
                )

        except Exception:
            pass

    def _format_age(self, timestamp: str) -> str:
        """Format timestamp as relative age"""
        if not timestamp:
            return "Unknown"

        try:
            from datetime import datetime
            created = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            now = datetime.now(created.tzinfo) if created.tzinfo else datetime.now()
            delta = now - created

            if delta.days > 0:
                return f"{delta.days}d ago"
            elif delta.seconds > 3600:
                return f"{delta.seconds // 3600}h ago"
            elif delta.seconds > 60:
                return f"{delta.seconds // 60}m ago"
            else:
                return "Just now"
        except Exception:
            return timestamp[:10]

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle memory selection"""
        if event.row_key:
            memory = next(
                (m for m in self._memories if m.get("id") == event.row_key.value),
                None
            )
            if memory:
                self._show_memory_detail(memory)

    def _show_memory_detail(self, memory: Dict[str, Any]) -> None:
        """Show memory details"""
        detail = self.query_one("#memory-detail", Static)

        lines = [
            f"[bold]Memory Entry[/]",
            f"",
            f"[dim]ID:[/] {memory.get('id', 'N/A')}",
            f"[dim]Type:[/] {memory.get('type', 'Unknown')}",
            f"[dim]Key:[/] {memory.get('key', 'N/A')}",
            f"[dim]Created:[/] {memory.get('created_at', 'Unknown')}",
            f"",
            f"[dim]Value:[/]",
        ]

        value = memory.get("value", "")
        if isinstance(value, dict):
            import json
            value = json.dumps(value, indent=2)
        elif isinstance(value, str) and len(value) > 500:
            value = value[:500] + "..."

        lines.append(str(value))

        detail.update("\n".join(lines))

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input"""
        if event.input.id == "memory-search":
            self.search_query = event.value

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "btn-search":
            asyncio.create_task(self._search_memories())
        elif event.button.id == "btn-clear-old":
            asyncio.create_task(self._clear_old_memories())
        elif event.button.id == "btn-export":
            asyncio.create_task(self._export_memories())
        elif event.button.id == "btn-similar":
            asyncio.create_task(self._find_similar())
        elif event.button.id == "btn-consolidate":
            asyncio.create_task(self._consolidate_memories())

    async def _search_memories(self) -> None:
        """Search memories"""
        if self.search_query:
            self._memories = await self._db.search_memories(self.search_query)
            await self._load_memories()
        else:
            await self._load_memories()

    async def _clear_old_memories(self) -> None:
        """Clear old memory entries"""
        count = await self._db.cleanup_old_memories(days=30)
        self.notify(f"Cleared {count} old memory entries")
        await self._refresh_stats()
        await self._load_memories()

    async def _export_memories(self) -> None:
        """Export memories to file"""
        from pathlib import Path
        import json
        from datetime import datetime

        export_dir = Path.home() / "Dev/clopus/exports"
        export_dir.mkdir(exist_ok=True)

        filename = f"memories_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        export_path = export_dir / filename

        with open(export_path, "w") as f:
            json.dump(self._memories, f, indent=2, default=str)

        self.notify(f"Exported to {export_path}")

    async def _find_similar(self) -> None:
        """Find similar memories using vector search"""
        # This would use ChromaDB vector search
        self.notify("Vector search not yet implemented in TUI")

    async def _consolidate_memories(self) -> None:
        """Consolidate short-term to long-term memory"""
        # This would trigger memory consolidation
        self.notify("Memory consolidation not yet implemented in TUI")

    def action_refresh(self) -> None:
        """Refresh data"""
        asyncio.create_task(self._refresh_stats())
        asyncio.create_task(self._load_memories())

    def action_go_back(self) -> None:
        """Go back to dashboard"""
        self.app.switch_screen("dashboard")

    def action_search(self) -> None:
        """Focus search input"""
        self.query_one("#memory-search", Input).focus()

    def action_cleanup(self) -> None:
        """Cleanup old memories"""
        asyncio.create_task(self._clear_old_memories())
