"""Orchestrator API client"""

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class OrchestratorStatus:
    running: bool
    uptime_seconds: float
    version: str
    workers_total: int
    workers_busy: int
    tasks_pending: int
    tasks_completed: int
    objectives_active: int


class OrchestratorClient:
    """Client for orchestrator operations"""

    def __init__(self):
        self._objectives_path = Path.home() / "Dev/clopus/objectives"
        self._answers_path = Path.home() / "Dev/clopus/answers"
        self._questions_path = Path.home() / "Dev/clopus/questions"

    async def submit_objective(self, content: str, priority: int = 5) -> str:
        """Submit a new objective"""
        import uuid
        from datetime import datetime

        objective_id = str(uuid.uuid4())[:8]
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{objective_id}.md"

        # Ensure directory exists
        self._objectives_path.mkdir(parents=True, exist_ok=True)

        # Write objective file
        objective_file = self._objectives_path / filename
        objective_file.write_text(content)

        return objective_id

    async def cancel_objective(self, objective_id: str) -> bool:
        """Cancel an objective by moving its file"""
        # Find the objective file
        for f in self._objectives_path.glob("*.md"):
            if objective_id in f.name:
                cancelled_path = self._objectives_path / "cancelled"
                cancelled_path.mkdir(exist_ok=True)
                f.rename(cancelled_path / f.name)
                return True
        return False

    async def answer_question(self, question_id: str, answer: str) -> bool:
        """Answer a pending question"""
        self._answers_path.mkdir(parents=True, exist_ok=True)
        answer_file = self._answers_path / f"{question_id}.md"
        answer_file.write_text(answer)
        return True

    async def get_pending_questions_from_files(self) -> List[Dict[str, Any]]:
        """Get pending questions from files"""
        questions = []
        if not self._questions_path.exists():
            return questions

        for f in self._questions_path.glob("*.md"):
            try:
                content = f.read_text()
                # Parse question file format
                questions.append({
                    "id": f.stem,
                    "content": content,
                    "file": str(f),
                })
            except Exception:
                pass
        return questions

    async def force_self_healing(self) -> bool:
        """Trigger self-healing cycle"""
        # This would need an API endpoint in the orchestrator
        # For now, we can restart the orchestrator
        import subprocess
        try:
            result = subprocess.run(
                ["docker", "exec", "clopus-orchestrator",
                 "python3", "-c",
                 "from orchestrator.memory_client import MemoryClient; "
                 "import asyncio; "
                 "async def heal(): "
                 "  m = MemoryClient(); "
                 "  await m.initialize(); "
                 "  await m.cleanup_stale_tasks(30); "
                 "asyncio.run(heal())"],
                capture_output=True, timeout=30
            )
            return result.returncode == 0
        except Exception:
            return False

    async def get_workspace_projects(self) -> List[Dict[str, Any]]:
        """Get list of projects in workspace"""
        workspace = Path.home() / "Dev/clopus-projects"
        if not workspace.exists():
            return []

        projects = []
        for p in workspace.iterdir():
            if p.is_dir() and not p.name.startswith("."):
                project_info = {
                    "name": p.name,
                    "path": str(p),
                    "has_package_json": (p / "package.json").exists(),
                    "has_requirements": (p / "requirements.txt").exists(),
                    "has_clopus": (p / ".clopus").exists(),
                }

                # Try to get port from .clopus/project_state.json
                state_file = p / ".clopus" / "project_state.json"
                if state_file.exists():
                    try:
                        state = json.loads(state_file.read_text())
                        project_info["status"] = state.get("status", "unknown")
                        project_info["port"] = state.get("dev_server", {}).get("port")
                    except Exception:
                        pass

                projects.append(project_info)

        return projects

    async def delete_project(self, project_path: str) -> bool:
        """Delete a project (move to trash)"""
        import shutil
        from datetime import datetime

        project = Path(project_path)
        if not project.exists():
            return False

        trash = Path.home() / "Dev/clopus-projects/.trash"
        trash.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = trash / f"{project.name}_{timestamp}"

        shutil.move(str(project), str(dest))
        return True

    async def start_dev_server(self, project_path: str) -> Optional[int]:
        """Start dev server for a project"""
        # This would run npm run dev or uvicorn in the background
        # For now, return the expected port
        return None

    async def stop_dev_server(self, project_path: str) -> bool:
        """Stop dev server for a project"""
        return True
