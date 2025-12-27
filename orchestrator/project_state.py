# =============================================================================
# CLOPUS v3 Project State Manager
# =============================================================================
"""
Manages project state for continuity across restarts.
Tracks progress, validation status, dev server state, and enables resumption.
"""

import json
import os
import signal
import socket
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict, fields
from enum import Enum
import logging

logger = logging.getLogger("clopus.project_state")


class ProjectStatus(Enum):
    """Overall project status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class StageStatus(Enum):
    """Status for individual stages."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    PARTIAL = "partial"


@dataclass
class ValidationState:
    """Tracks validation pipeline progress."""
    status: str = "pending"
    stages_passed: List[str] = field(default_factory=list)
    stages_failed: List[str] = field(default_factory=list)
    stages_pending: List[str] = field(default_factory=lambda: [
        "syntax", "lint", "build", "unit_tests",
        "integration_tests", "e2e_tests", "security", "review"
    ])
    last_run: Optional[str] = None
    errors: List[str] = field(default_factory=list)


@dataclass
class DevServerState:
    """Tracks dev server status."""
    running: bool = False
    port: Optional[int] = None
    allocated_port: Optional[int] = None
    pid: Optional[int] = None
    url: Optional[str] = None
    started_at: Optional[str] = None
    needs_restart: bool = False


@dataclass
class StageState:
    """State for a project stage."""
    status: str = "pending"
    completed_at: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProjectState:
    """Complete project state."""
    project_name: str
    project_path: str
    objective_id: Optional[str] = None
    objective_content: Optional[str] = None
    status: str = "pending"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_activity: str = field(default_factory=lambda: datetime.now().isoformat())

    # Stage tracking
    stages: Dict[str, Dict] = field(default_factory=lambda: {
        "setup": {"status": "pending"},
        "design": {"status": "pending"},
        "implementation": {"status": "pending"},
        "validation": {"status": "pending"},
        "e2e_testing": {"status": "pending", "screenshots": []},
        "documentation": {"status": "pending"}
    })

    # Detailed validation state
    validation: Dict = field(default_factory=lambda: {
        "status": "pending",
        "stages_passed": [],
        "stages_failed": [],
        "stages_pending": [
            "syntax", "lint", "build", "unit_tests",
            "integration_tests", "e2e_tests", "security", "review"
        ],
        "last_run": None,
        "errors": []
    })

    # Dev server state
    dev_server: Dict = field(default_factory=lambda: {
        "running": False,
        "port": None,
        "allocated_port": None,
        "pid": None,
        "url": None,
        "started_at": None,
        "needs_restart": False
    })

    # Tasks completed
    tasks_completed: List[Dict] = field(default_factory=list)
    tasks_pending: List[Dict] = field(default_factory=list)

    # Design system
    has_design_system: bool = False

    # Branding
    branding: Optional[Dict] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "ProjectState":
        """Create from dictionary, ignoring unknown fields."""
        # Get valid field names from the dataclass
        valid_fields = {f.name for f in fields(cls)}
        # Filter out unknown fields
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)

    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now().isoformat()

    def is_complete(self) -> bool:
        """Check if project is complete."""
        return (
            self.status == "completed" or
            (
                self.stages.get("validation", {}).get("status") == "completed" and
                self.stages.get("e2e_testing", {}).get("status") in ("completed", "skipped") and
                self.stages.get("documentation", {}).get("status") == "completed"
            )
        )

    def get_pending_work(self) -> List[str]:
        """Get list of pending work items."""
        pending = []

        if self.stages.get("setup", {}).get("status") != "completed":
            pending.append("setup")
        if self.stages.get("design", {}).get("status") != "completed":
            pending.append("design")
        if self.stages.get("implementation", {}).get("status") != "completed":
            pending.append("implementation")
        if self.validation.get("status") not in ("completed", "passed"):
            pending.append("validation")
        if self.stages.get("e2e_testing", {}).get("status") not in ("completed", "skipped"):
            pending.append("e2e_testing")
        if self.stages.get("documentation", {}).get("status") != "completed":
            pending.append("documentation")

        # Check dev server
        if self.dev_server.get("needs_restart"):
            pending.append("restart_dev_server")
        elif not self.dev_server.get("running"):
            pending.append("start_dev_server")

        return pending


class ProjectStateManager:
    """
    Manages project state persistence and reconciliation.
    Enables CLOPUS to resume incomplete projects across restarts.
    """

    STATE_FILENAME = "project_state.json"

    def __init__(self, workspace_path: str = "/workspace"):
        self.workspace = Path(workspace_path)
        self._states: Dict[str, ProjectState] = {}

    # =========================================================================
    # STATE PERSISTENCE
    # =========================================================================

    def get_state_path(self, project_path: str) -> Path:
        """Get path to state file for a project."""
        return Path(project_path) / ".clopus" / self.STATE_FILENAME

    async def load_state(self, project_path: str) -> Optional[ProjectState]:
        """Load project state from disk."""
        state_file = self.get_state_path(project_path)

        if not state_file.exists():
            return None

        try:
            data = json.loads(state_file.read_text())
            state = ProjectState.from_dict(data)
            self._states[project_path] = state
            return state
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Error loading state for {project_path}: {e}")
            return None

    async def save_state(self, state: ProjectState) -> None:
        """Save project state to disk."""
        state_file = self.get_state_path(state.project_path)
        state_file.parent.mkdir(parents=True, exist_ok=True)

        state.update_activity()
        state_file.write_text(json.dumps(state.to_dict(), indent=2))
        self._states[state.project_path] = state

        logger.debug(f"Saved state for {state.project_name}")

    async def create_state(
        self,
        project_path: str,
        objective_id: Optional[str] = None,
        objective_content: Optional[str] = None
    ) -> ProjectState:
        """Create a new project state."""
        project = Path(project_path)

        state = ProjectState(
            project_name=project.name,
            project_path=str(project),
            objective_id=objective_id,
            objective_content=objective_content,
            status="in_progress"
        )

        await self.save_state(state)
        return state

    # =========================================================================
    # PROJECT SCANNING
    # =========================================================================

    async def scan_workspace(self) -> List[ProjectState]:
        """
        Scan workspace for all projects and load their states.
        Returns list of projects that need resumption.
        """
        if not self.workspace.exists():
            logger.warning(f"Workspace not found: {self.workspace}")
            return []

        incomplete_projects = []

        for project_dir in self.workspace.iterdir():
            if not project_dir.is_dir():
                continue
            if project_dir.name.startswith('.'):
                continue

            # Check if it's a valid project
            is_project = (
                (project_dir / "package.json").exists() or
                (project_dir / "requirements.txt").exists() or
                (project_dir / "Cargo.toml").exists() or
                (project_dir / "go.mod").exists() or
                (project_dir / ".clopus").exists()
            )

            if not is_project:
                continue

            # Load or create state
            state = await self.load_state(str(project_dir))

            if state is None:
                # Project exists but has no state - create one
                state = await self._infer_state(project_dir)

            # Reconcile state with reality
            state = await self.reconcile_state(state)

            # Check if incomplete
            if not state.is_complete():
                incomplete_projects.append(state)
                logger.info(f"Found incomplete project: {state.project_name}")

        # Sort by last activity (most recent first)
        incomplete_projects.sort(
            key=lambda s: s.last_activity,
            reverse=True
        )

        return incomplete_projects

    async def _infer_state(self, project_dir: Path) -> ProjectState:
        """Infer project state from filesystem when no state file exists."""
        state = ProjectState(
            project_name=project_dir.name,
            project_path=str(project_dir),
            status="in_progress"
        )

        # Check for design system
        if (project_dir / ".clopus" / "design" / "DESIGN_SYSTEM.md").exists():
            state.stages["design"]["status"] = "completed"
            state.has_design_system = True

        # Check for source code (implementation started)
        src_dir = project_dir / "src"
        if src_dir.exists() and any(src_dir.rglob("*.tsx")) or any(src_dir.rglob("*.ts")):
            state.stages["setup"]["status"] = "completed"
            state.stages["implementation"]["status"] = "in_progress"

        # Check for build artifacts
        if (project_dir / "dist").exists() or (project_dir / "build").exists():
            state.stages["implementation"]["status"] = "completed"
            state.validation["stages_passed"].append("build")
            if "build" in state.validation["stages_pending"]:
                state.validation["stages_pending"].remove("build")

        # Check for test files
        if any(project_dir.rglob("*.test.ts")) or any(project_dir.rglob("*.spec.ts")):
            state.validation["stages_passed"].append("unit_tests")
            if "unit_tests" in state.validation["stages_pending"]:
                state.validation["stages_pending"].remove("unit_tests")

        # Check for screenshots
        screenshots_dir = project_dir / ".clopus" / "screenshots"
        if screenshots_dir.exists():
            screenshots = list(screenshots_dir.glob("*.png"))
            if screenshots:
                state.stages["e2e_testing"]["screenshots"] = [str(s) for s in screenshots]

        # Check for PROJECT.md
        if (project_dir / "PROJECT.md").exists():
            state.stages["documentation"]["status"] = "completed"

        await self.save_state(state)
        return state

    # =========================================================================
    # STATE RECONCILIATION
    # =========================================================================

    async def reconcile_state(self, state: ProjectState) -> ProjectState:
        """
        Reconcile saved state with actual filesystem and running processes.
        Detects discrepancies and updates state accordingly.
        """
        project = Path(state.project_path)

        if not project.exists():
            state.status = "failed"
            state.stages["setup"]["error"] = "Project directory not found"
            return state

        # Reconcile dev server state
        state = await self._reconcile_dev_server(state)

        # Reconcile validation state
        state = await self._reconcile_validation(state)

        # Reconcile design system
        if (project / ".clopus" / "design" / "DESIGN_SYSTEM.md").exists():
            state.has_design_system = True
            state.stages["design"]["status"] = "completed"

        # Reconcile documentation
        if (project / "PROJECT.md").exists():
            state.stages["documentation"]["status"] = "completed"

        await self.save_state(state)
        return state

    async def _reconcile_dev_server(self, state: ProjectState) -> ProjectState:
        """Reconcile dev server state with running processes."""
        project = Path(state.project_path)

        # Check if PID file exists
        pid_file = project / ".clopus" / "dev_server.pid"
        saved_pid = None
        if pid_file.exists():
            try:
                saved_pid = int(pid_file.read_text().strip())
            except ValueError:
                pass

        # Check if process is running
        process_running = False
        actual_port = None

        if saved_pid:
            process_running = self._is_process_running(saved_pid)

        # Check what port is actually being used
        if state.dev_server.get("port"):
            port_in_use = self._is_port_in_use(state.dev_server["port"])
            if port_in_use:
                actual_port = state.dev_server["port"]

        # Also check server_info.json
        server_info_file = project / ".clopus" / "server_info.json"
        if server_info_file.exists():
            try:
                server_info = json.loads(server_info_file.read_text())
                info_port = server_info.get("port")
                if info_port and self._is_port_in_use(info_port):
                    actual_port = info_port
                    process_running = True
            except json.JSONDecodeError:
                pass

        # Update state
        state.dev_server["running"] = process_running
        state.dev_server["port"] = actual_port
        state.dev_server["pid"] = saved_pid if process_running else None

        # Check if port needs to be reallocated
        allocated = state.dev_server.get("allocated_port")
        if actual_port and allocated and actual_port != allocated:
            state.dev_server["needs_restart"] = True
            logger.info(
                f"{state.project_name}: Running on {actual_port} but allocated {allocated}"
            )
        elif not process_running and allocated:
            state.dev_server["needs_restart"] = True

        return state

    async def _reconcile_validation(self, state: ProjectState) -> ProjectState:
        """Reconcile validation state."""
        project = Path(state.project_path)

        # Check for validation results file
        results_file = project / ".clopus" / "validation_results.json"
        if results_file.exists():
            try:
                results = json.loads(results_file.read_text())

                # Update validation state from results
                for stage_result in results.get("stages", []):
                    stage_name = stage_result.get("stage", "").lower()
                    passed = stage_result.get("passed", False)

                    if passed and stage_name not in state.validation["stages_passed"]:
                        state.validation["stages_passed"].append(stage_name)
                    if not passed and stage_name not in state.validation["stages_failed"]:
                        state.validation["stages_failed"].append(stage_name)

                    if stage_name in state.validation["stages_pending"]:
                        state.validation["stages_pending"].remove(stage_name)

                # Update overall validation status
                if results.get("overall_passed"):
                    state.validation["status"] = "completed"
                    state.stages["validation"]["status"] = "completed"
                elif state.validation["stages_failed"]:
                    state.validation["status"] = "failed"
                elif state.validation["stages_passed"]:
                    state.validation["status"] = "partial"

            except json.JSONDecodeError:
                pass

        return state

    # =========================================================================
    # PROCESS MANAGEMENT
    # =========================================================================

    def _is_process_running(self, pid: int) -> bool:
        """Check if a process is running."""
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False

    def _is_port_in_use(self, port: int) -> bool:
        """Check if a port is in use."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            return result == 0
        except Exception:
            return False

    async def kill_dev_server(self, state: ProjectState) -> bool:
        """Kill the dev server for a project."""
        pid = state.dev_server.get("pid")
        port = state.dev_server.get("port")

        killed = False

        # Try to kill by PID
        if pid and self._is_process_running(pid):
            try:
                os.kill(pid, signal.SIGTERM)
                killed = True
                logger.info(f"Killed dev server (PID {pid}) for {state.project_name}")
            except OSError as e:
                logger.warning(f"Failed to kill PID {pid}: {e}")

        # If still running on port, try to find and kill the process
        if port and self._is_port_in_use(port):
            try:
                # Find process using the port
                result = subprocess.run(
                    ["lsof", "-ti", f":{port}"],
                    capture_output=True,
                    text=True
                )
                if result.stdout.strip():
                    pids = result.stdout.strip().split('\n')
                    for p in pids:
                        try:
                            os.kill(int(p), signal.SIGTERM)
                            killed = True
                            logger.info(f"Killed process {p} on port {port}")
                        except (OSError, ValueError):
                            pass
            except Exception as e:
                logger.warning(f"Failed to find process on port {port}: {e}")

        # Update state
        if killed:
            state.dev_server["running"] = False
            state.dev_server["pid"] = None
            state.dev_server["needs_restart"] = True
            await self.save_state(state)

        return killed

    # =========================================================================
    # STATE UPDATES
    # =========================================================================

    async def update_stage(
        self,
        project_path: str,
        stage: str,
        status: str,
        metadata: Optional[Dict] = None
    ) -> None:
        """Update a stage's status."""
        state = self._states.get(project_path)
        if not state:
            state = await self.load_state(project_path)
        if not state:
            return

        if stage not in state.stages:
            state.stages[stage] = {}

        state.stages[stage]["status"] = status
        if status == "completed":
            state.stages[stage]["completed_at"] = datetime.now().isoformat()
        if metadata:
            state.stages[stage].update(metadata)

        await self.save_state(state)

    async def update_validation(
        self,
        project_path: str,
        stage_name: str,
        passed: bool,
        error: Optional[str] = None
    ) -> None:
        """Update validation stage result."""
        state = self._states.get(project_path)
        if not state:
            state = await self.load_state(project_path)
        if not state:
            return

        # Update stage lists
        if passed:
            if stage_name not in state.validation["stages_passed"]:
                state.validation["stages_passed"].append(stage_name)
            if stage_name in state.validation["stages_failed"]:
                state.validation["stages_failed"].remove(stage_name)
        else:
            if stage_name not in state.validation["stages_failed"]:
                state.validation["stages_failed"].append(stage_name)
                if error:
                    state.validation["errors"].append(f"{stage_name}: {error}")

        if stage_name in state.validation["stages_pending"]:
            state.validation["stages_pending"].remove(stage_name)

        state.validation["last_run"] = datetime.now().isoformat()

        # Update overall status
        if not state.validation["stages_pending"] and not state.validation["stages_failed"]:
            state.validation["status"] = "completed"
            state.stages["validation"]["status"] = "completed"
        elif state.validation["stages_failed"]:
            state.validation["status"] = "failed"
        else:
            state.validation["status"] = "partial"

        await self.save_state(state)

    async def update_dev_server(
        self,
        project_path: str,
        running: bool,
        port: Optional[int] = None,
        pid: Optional[int] = None,
        allocated_port: Optional[int] = None
    ) -> None:
        """Update dev server state."""
        state = self._states.get(project_path)
        if not state:
            state = await self.load_state(project_path)
        if not state:
            return

        state.dev_server["running"] = running
        if port:
            state.dev_server["port"] = port
        if pid:
            state.dev_server["pid"] = pid
        if allocated_port:
            state.dev_server["allocated_port"] = allocated_port
        if running:
            state.dev_server["started_at"] = datetime.now().isoformat()
            state.dev_server["url"] = f"http://0.0.0.0:{port or allocated_port}"
            state.dev_server["needs_restart"] = False

        await self.save_state(state)

    async def mark_complete(self, project_path: str) -> None:
        """Mark a project as complete."""
        state = self._states.get(project_path)
        if not state:
            state = await self.load_state(project_path)
        if not state:
            return

        state.status = "completed"
        state.stages["documentation"]["status"] = "completed"
        state.stages["documentation"]["completed_at"] = datetime.now().isoformat()

        await self.save_state(state)

    async def add_screenshot(
        self,
        project_path: str,
        screenshot_path: str
    ) -> None:
        """Add a screenshot to the E2E testing stage."""
        state = self._states.get(project_path)
        if not state:
            state = await self.load_state(project_path)
        if not state:
            return

        if "screenshots" not in state.stages["e2e_testing"]:
            state.stages["e2e_testing"]["screenshots"] = []

        state.stages["e2e_testing"]["screenshots"].append(screenshot_path)
        state.stages["e2e_testing"]["status"] = "in_progress"

        await self.save_state(state)


# Singleton instance
_state_manager: Optional[ProjectStateManager] = None


def get_state_manager(workspace_path: str = "/workspace") -> ProjectStateManager:
    """Get the project state manager instance."""
    global _state_manager
    if _state_manager is None:
        _state_manager = ProjectStateManager(workspace_path)
    return _state_manager
