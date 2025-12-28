"""Config screen - system configuration"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Header, Footer, Label, Button, Input, Switch, Select
from textual.containers import Horizontal, Vertical, Container, ScrollableContainer
from textual.reactive import reactive
from typing import Optional, Dict, Any
import asyncio
from pathlib import Path
import json


class ConfigScreen(Screen):
    """System configuration screen"""

    CSS = """
    ConfigScreen {
        layout: grid;
        grid-size: 2 1;
        grid-gutter: 1;
        padding: 1;
    }

    #config-general {
        column-span: 1;
        border: solid $primary;
        padding: 1;
        overflow-y: auto;
    }

    #config-workers {
        column-span: 1;
        border: solid $primary;
        padding: 1;
        overflow-y: auto;
    }

    .panel-title {
        text-style: bold;
        margin-bottom: 1;
    }

    .config-section {
        margin-bottom: 2;
    }

    .config-row {
        height: 3;
        margin-bottom: 1;
    }

    .config-row Label {
        width: 20;
    }

    .config-row Input {
        width: 1fr;
    }

    .config-row Switch {
        width: auto;
    }

    .config-row Select {
        width: 1fr;
    }

    .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
        margin-top: 1;
    }

    .save-row {
        height: 3;
        margin-top: 2;
    }

    .save-row Button {
        margin-right: 1;
    }

    .config-info {
        color: $text-muted;
        margin-top: 1;
    }
    """

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("s", "save_config", "Save"),
        ("r", "reload_config", "Reload"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._config: Dict[str, Any] = {}
        self._config_path = Path.home() / "Dev/clopus/config.yaml"

    def compose(self) -> ComposeResult:
        yield Header()

        with ScrollableContainer(id="config-general"):
            yield Label("General Configuration", classes="panel-title")

            yield Label("Theme Settings", classes="section-title")
            with Horizontal(classes="config-row"):
                yield Label("Theme")
                yield Select(
                    [("Dark", "dark"), ("Light", "light")],
                    value="dark",
                    id="theme-select",
                )
            with Horizontal(classes="config-row"):
                yield Label("Notifications")
                yield Switch(value=True, id="notifications-switch")

            yield Label("Confidence Engine", classes="section-title")
            with Horizontal(classes="config-row"):
                yield Label("Threshold")
                yield Input(value="0.4", id="confidence-threshold")
            with Horizontal(classes="config-row"):
                yield Label("Auto-proceed")
                yield Switch(value=True, id="auto-proceed-switch")

            yield Label("Heartbeat Agent", classes="section-title")
            with Horizontal(classes="config-row"):
                yield Label("Enabled")
                yield Switch(value=True, id="heartbeat-enabled")
            with Horizontal(classes="config-row"):
                yield Label("Interval (sec)")
                yield Input(value="300", id="heartbeat-interval")
            with Horizontal(classes="config-row"):
                yield Label("Integration Tests")
                yield Switch(value=True, id="heartbeat-integration")

            yield Label("Validation Pipeline", classes="section-title")
            with Horizontal(classes="config-row"):
                yield Label("Strict Mode")
                yield Switch(value=True, id="validation-strict")
            with Horizontal(classes="config-row"):
                yield Label("Max Retries")
                yield Input(value="3", id="validation-retries")

            with Horizontal(classes="save-row"):
                yield Button("Save", id="btn-save", variant="primary")
                yield Button("Reset", id="btn-reset")
                yield Button("Reload", id="btn-reload")

        with ScrollableContainer(id="config-workers"):
            yield Label("Worker Configuration", classes="panel-title")

            yield Label("Worker Pool", classes="section-title")
            with Horizontal(classes="config-row"):
                yield Label("Active Workers")
                yield Input(value="11", id="worker-count")
            with Horizontal(classes="config-row"):
                yield Label("Timeout (sec)")
                yield Input(value="3600", id="worker-timeout")

            yield Label("Worker Roles", classes="section-title")
            for i, role in enumerate([
                "coder", "tester", "reviewer", "researcher",
                "debugger", "designer", "heartbeat", "verificator",
                "browser-headless", "browser-chrome", "services"
            ], 1):
                with Horizontal(classes="config-row"):
                    yield Label(f"Worker {i}")
                    yield Select(
                        [
                            ("Coder", "coder"),
                            ("Tester", "tester"),
                            ("Reviewer", "reviewer"),
                            ("Researcher", "researcher"),
                            ("Debugger", "debugger"),
                            ("Designer", "designer"),
                            ("Heartbeat", "heartbeat"),
                            ("Verificator", "verificator"),
                            ("Browser Headless", "browser-headless"),
                            ("Browser Chrome", "browser-chrome"),
                            ("Services", "services"),
                        ],
                        value=role,
                        id=f"worker-{i}-role",
                    )

            yield Label("Docker Settings", classes="section-title")
            with Horizontal(classes="config-row"):
                yield Label("Compose File")
                yield Input(value="docker-compose.yml", id="compose-file")
            with Horizontal(classes="config-row"):
                yield Label("Network")
                yield Input(value="clopus-network", id="docker-network")

            yield Static(
                "[dim]Note: Worker role changes require container restart[/]",
                classes="config-info"
            )

        yield Footer()

    async def on_mount(self) -> None:
        """Load current configuration"""
        await self._load_config()

    async def _load_config(self) -> None:
        """Load configuration from file"""
        try:
            if self._config_path.exists():
                import yaml
                with open(self._config_path) as f:
                    self._config = yaml.safe_load(f) or {}

                # Update UI with config values
                self._apply_config_to_ui()
        except Exception as e:
            self.notify(f"Error loading config: {e}", severity="error")

    def _apply_config_to_ui(self) -> None:
        """Apply loaded config to UI elements"""
        try:
            # Confidence engine
            if "confidence" in self._config:
                conf = self._config["confidence"]
                threshold_input = self.query_one("#confidence-threshold", Input)
                threshold_input.value = str(conf.get("threshold", 0.4))

            # Heartbeat
            if "heartbeat" in self._config:
                hb = self._config["heartbeat"]
                enabled = self.query_one("#heartbeat-enabled", Switch)
                enabled.value = hb.get("enabled", True)
                interval = self.query_one("#heartbeat-interval", Input)
                interval.value = str(hb.get("interval_seconds", 300))

            # Validation
            if "validation" in self._config:
                val = self._config["validation"]
                strict = self.query_one("#validation-strict", Switch)
                strict.value = val.get("strict_mode", True)
                retries = self.query_one("#validation-retries", Input)
                retries.value = str(val.get("max_retries", 3))

        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "btn-save":
            asyncio.create_task(self._save_config())
        elif event.button.id == "btn-reset":
            asyncio.create_task(self._reset_config())
        elif event.button.id == "btn-reload":
            asyncio.create_task(self._load_config())

    async def _save_config(self) -> None:
        """Save configuration to file"""
        try:
            # Gather values from UI
            config = self._gather_config_from_ui()

            # Merge with existing config
            self._config.update(config)

            # Save to file
            import yaml
            with open(self._config_path, "w") as f:
                yaml.dump(self._config, f, default_flow_style=False)

            self.notify("Configuration saved")

        except Exception as e:
            self.notify(f"Error saving config: {e}", severity="error")

    def _gather_config_from_ui(self) -> Dict[str, Any]:
        """Gather configuration values from UI"""
        config = {}

        try:
            # Confidence engine
            threshold = self.query_one("#confidence-threshold", Input)
            auto_proceed = self.query_one("#auto-proceed-switch", Switch)
            config["confidence"] = {
                "threshold": float(threshold.value),
                "auto_proceed": auto_proceed.value,
            }

            # Heartbeat
            hb_enabled = self.query_one("#heartbeat-enabled", Switch)
            hb_interval = self.query_one("#heartbeat-interval", Input)
            hb_integration = self.query_one("#heartbeat-integration", Switch)
            config["heartbeat"] = {
                "enabled": hb_enabled.value,
                "interval_seconds": int(hb_interval.value),
                "integration_testing": {"enabled": hb_integration.value},
            }

            # Validation
            val_strict = self.query_one("#validation-strict", Switch)
            val_retries = self.query_one("#validation-retries", Input)
            config["validation"] = {
                "strict_mode": val_strict.value,
                "max_retries": int(val_retries.value),
            }

            # Workers
            worker_timeout = self.query_one("#worker-timeout", Input)
            config["workers"] = {
                "timeout_seconds": int(worker_timeout.value),
            }

        except Exception:
            pass

        return config

    async def _reset_config(self) -> None:
        """Reset to default configuration"""
        defaults = {
            "confidence": {"threshold": 0.4, "auto_proceed": True},
            "heartbeat": {
                "enabled": True,
                "interval_seconds": 300,
                "integration_testing": {"enabled": True},
            },
            "validation": {"strict_mode": True, "max_retries": 3},
            "workers": {"timeout_seconds": 3600},
        }

        self._config = defaults
        self._apply_config_to_ui()
        self.notify("Configuration reset to defaults")

    def on_switch_changed(self, event: Switch.Changed) -> None:
        """Handle switch changes"""
        # Auto-save or mark as changed
        pass

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select changes"""
        if event.select.id == "theme-select":
            # Apply theme immediately
            theme = event.value
            if theme == "dark":
                self.app.dark = True
            else:
                self.app.dark = False

    def action_go_back(self) -> None:
        """Go back to dashboard"""
        self.app.switch_screen("dashboard")

    def action_save_config(self) -> None:
        """Save configuration"""
        asyncio.create_task(self._save_config())

    def action_reload_config(self) -> None:
        """Reload configuration"""
        asyncio.create_task(self._load_config())
