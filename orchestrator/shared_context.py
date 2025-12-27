# =============================================================================
# CLOPUS v3 Shared Context Manager
# =============================================================================
"""
Manages shared context between related projects.
Enables cross-project data sharing for multi-project objectives.

Example use cases:
- API project exports OpenAPI spec for frontend to consume
- Shared design tokens between frontend and mobile apps
- Common configuration across microservices
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("clopus.shared_context")

SHARED_DIR = "/workspace/.shared"


@dataclass
class ProjectLink:
    """Defines a link between two projects."""
    source_project: str
    target_project: str
    link_type: str  # "api_consumer", "shared_design", "microservice"
    shared_artifacts: List[str] = field(default_factory=list)


@dataclass
class SharedArtifact:
    """A shared artifact between projects."""
    name: str
    source_project: str
    path: str
    artifact_type: str  # "openapi", "design_tokens", "config", "types"
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)


class SharedContextManager:
    """Manages shared context between related projects."""

    def __init__(self, workspace_path: str = "/workspace"):
        self.workspace = Path(workspace_path)
        self.shared_dir = Path(SHARED_DIR)
        self._ensure_shared_dir()

    def _ensure_shared_dir(self) -> None:
        """Create shared directory if it doesn't exist."""
        self.shared_dir.mkdir(parents=True, exist_ok=True)

        # Create index file if missing
        index_path = self.shared_dir / "index.json"
        if not index_path.exists():
            index_path.write_text(json.dumps({
                "version": "1.0",
                "created_at": datetime.now().isoformat(),
                "projects": {},
                "links": []
            }, indent=2))

    def get_project_shared_dir(self, project_name: str) -> Path:
        """Get the shared directory for a specific project."""
        project_dir = self.shared_dir / project_name
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir

    def publish_artifact(
        self,
        project_name: str,
        artifact_name: str,
        artifact_type: str,
        content: Any,
        metadata: Optional[Dict] = None
    ) -> Path:
        """
        Publish an artifact from a project to the shared context.

        Args:
            project_name: Source project name
            artifact_name: Name of the artifact (e.g., "openapi.json")
            artifact_type: Type of artifact ("openapi", "design_tokens", etc.)
            content: Content to write (dict will be JSON-serialized)
            metadata: Optional metadata about the artifact

        Returns:
            Path to the published artifact
        """
        project_dir = self.get_project_shared_dir(project_name)
        artifact_path = project_dir / artifact_name

        # Write content
        if isinstance(content, (dict, list)):
            artifact_path.write_text(json.dumps(content, indent=2))
        else:
            artifact_path.write_text(str(content))

        # Update index
        self._update_index(project_name, artifact_name, artifact_type, metadata)

        logger.info(f"Published artifact: {project_name}/{artifact_name}")
        return artifact_path

    def get_artifact(
        self,
        project_name: str,
        artifact_name: str
    ) -> Optional[Any]:
        """
        Get a shared artifact from a project.

        Args:
            project_name: Source project name
            artifact_name: Name of the artifact

        Returns:
            Content of the artifact (parsed as JSON if applicable)
        """
        artifact_path = self.shared_dir / project_name / artifact_name

        if not artifact_path.exists():
            logger.warning(f"Artifact not found: {project_name}/{artifact_name}")
            return None

        content = artifact_path.read_text()

        # Try to parse as JSON
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return content

    def link_projects(
        self,
        source_project: str,
        target_project: str,
        link_type: str,
        shared_artifacts: Optional[List[str]] = None
    ) -> None:
        """
        Create a link between two projects.

        Args:
            source_project: Project that provides artifacts
            target_project: Project that consumes artifacts
            link_type: Type of relationship
            shared_artifacts: List of artifact names to share
        """
        index = self._load_index()

        link = {
            "source": source_project,
            "target": target_project,
            "type": link_type,
            "artifacts": shared_artifacts or [],
            "created_at": datetime.now().isoformat()
        }

        # Remove existing link if present
        index["links"] = [
            l for l in index["links"]
            if not (l["source"] == source_project and l["target"] == target_project)
        ]

        index["links"].append(link)
        self._save_index(index)

        logger.info(f"Linked projects: {source_project} -> {target_project} ({link_type})")

    def get_project_dependencies(self, project_name: str) -> List[Dict]:
        """Get all projects that this project depends on."""
        index = self._load_index()
        return [
            {"project": l["source"], "type": l["type"], "artifacts": l["artifacts"]}
            for l in index["links"]
            if l["target"] == project_name
        ]

    def get_project_dependents(self, project_name: str) -> List[Dict]:
        """Get all projects that depend on this project."""
        index = self._load_index()
        return [
            {"project": l["target"], "type": l["type"], "artifacts": l["artifacts"]}
            for l in index["links"]
            if l["source"] == project_name
        ]

    def get_linked_projects(self, project_name: str) -> List[str]:
        """
        Get all projects linked to this project (both dependencies and dependents).

        Returns:
            List of project names that are linked to this project
        """
        linked = set()

        # Add dependencies
        for dep in self.get_project_dependencies(project_name):
            linked.add(dep["project"])

        # Add dependents
        for dep in self.get_project_dependents(project_name):
            linked.add(dep["project"])

        return list(linked)

    def get_shared_context_for_project(self, project_name: str) -> str:
        """
        Generate a context string for workers about shared data.

        Returns a markdown string describing available shared artifacts
        and project dependencies.
        """
        dependencies = self.get_project_dependencies(project_name)
        dependents = self.get_project_dependents(project_name)

        if not dependencies and not dependents:
            return ""

        lines = ["## Shared Project Context\n"]

        if dependencies:
            lines.append("### Dependencies (this project consumes from):\n")
            for dep in dependencies:
                lines.append(f"- **{dep['project']}** ({dep['type']})")
                if dep['artifacts']:
                    lines.append(f"  - Artifacts: {', '.join(dep['artifacts'])}")
                    for artifact in dep['artifacts']:
                        artifact_path = self.shared_dir / dep['project'] / artifact
                        if artifact_path.exists():
                            lines.append(f"  - Available at: {artifact_path}")
            lines.append("")

        if dependents:
            lines.append("### Dependents (projects that consume from this):\n")
            for dep in dependents:
                lines.append(f"- **{dep['project']}** ({dep['type']})")
                if dep['artifacts']:
                    lines.append(f"  - Expected artifacts: {', '.join(dep['artifacts'])}")
            lines.append("")

        return "\n".join(lines)

    def _load_index(self) -> Dict:
        """Load the shared context index."""
        index_path = self.shared_dir / "index.json"
        if index_path.exists():
            return json.loads(index_path.read_text())
        return {"version": "1.0", "projects": {}, "links": []}

    def _save_index(self, index: Dict) -> None:
        """Save the shared context index."""
        index_path = self.shared_dir / "index.json"
        index_path.write_text(json.dumps(index, indent=2))

    def _update_index(
        self,
        project_name: str,
        artifact_name: str,
        artifact_type: str,
        metadata: Optional[Dict] = None
    ) -> None:
        """Update the index with a new artifact."""
        index = self._load_index()

        if project_name not in index["projects"]:
            index["projects"][project_name] = {"artifacts": []}

        # Update or add artifact
        artifacts = index["projects"][project_name]["artifacts"]
        existing = next((a for a in artifacts if a["name"] == artifact_name), None)

        artifact_info = {
            "name": artifact_name,
            "type": artifact_type,
            "updated_at": datetime.now().isoformat(),
            "metadata": metadata or {}
        }

        if existing:
            artifacts.remove(existing)
        artifacts.append(artifact_info)

        self._save_index(index)


# Singleton instance
_shared_context_manager: Optional[SharedContextManager] = None


def get_shared_context() -> SharedContextManager:
    """Get the shared context manager singleton."""
    global _shared_context_manager
    if _shared_context_manager is None:
        _shared_context_manager = SharedContextManager()
    return _shared_context_manager
