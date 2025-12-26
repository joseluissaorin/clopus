# =============================================================================
# CLOPUS v3 Template Extractor
# =============================================================================
"""
Extracts reusable templates from completed projects.
Abstracts project-specific details into parameterized scaffolds.
"""

import asyncio
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import logging

logger = logging.getLogger("clopus.template_extractor")


class TemplateExtractor:
    """Extract templates from completed projects."""

    def __init__(
        self,
        memory_client,
        github_sync,
        templates_path: str = "/app/templates"
    ):
        self.memory = memory_client
        self.github_sync = github_sync
        self.templates_path = Path(templates_path)
        self.core_path = self.templates_path / "core"
        self.extracted_path = self.templates_path / "extracted"

        # Ensure directories exist
        self.core_path.mkdir(parents=True, exist_ok=True)
        self.extracted_path.mkdir(parents=True, exist_ok=True)

        # Files/patterns to exclude from templates
        self.exclude_patterns = {
            ".git",
            "node_modules",
            "__pycache__",
            ".next",
            "dist",
            "build",
            ".env",
            ".env.local",
            "*.log",
            "*.pyc",
            ".DS_Store",
        }

        # Patterns to parameterize
        self.parameterize_patterns = {
            "project_name": [],
            "author": [],
            "description": [],
            "version": ["1.0.0", "0.1.0"],
        }

    async def extract_template(
        self,
        project_path: str,
        template_name: str,
        description: Optional[str] = None
    ) -> Optional[Path]:
        """Extract a template from a project."""
        source_path = Path(project_path)
        if not source_path.exists():
            logger.error(f"Project path does not exist: {project_path}")
            return None

        logger.info(f"Extracting template '{template_name}' from {project_path}")

        # Create template directory
        template_dir = self.extracted_path / template_name
        if template_dir.exists():
            shutil.rmtree(template_dir)
        template_dir.mkdir(parents=True)

        # Analyze project structure
        project_info = await self._analyze_project(source_path)

        # Copy and process files
        await self._copy_and_process(source_path, template_dir, project_info)

        # Generate TEMPLATE.md
        await self._generate_template_md(
            template_dir, template_name, description, project_info
        )

        # Generate template.json
        await self._generate_template_json(
            template_dir, template_name, description, project_info
        )

        # Store in memory
        await self.memory.long_term.store(
            memory_type="template",
            content=f"Extracted template: {template_name}\n{description or ''}\nType: {project_info.get('type')}",
            metadata={
                "template_name": template_name,
                "project_type": project_info.get("type"),
                "extracted_from": str(source_path)
            }
        )

        # Sync to GitHub
        if self.github_sync:
            await self.github_sync.sync_templates()

        logger.info(f"Template extracted to: {template_dir}")
        return template_dir

    async def _analyze_project(self, path: Path) -> Dict:
        """Analyze project structure and detect patterns."""
        info = {
            "type": "unknown",
            "technologies": [],
            "files": [],
            "directories": [],
            "config_files": [],
            "project_name": path.name,
            "parameters": {}
        }

        # Detect project type
        if (path / "package.json").exists():
            pkg = json.loads((path / "package.json").read_text())
            info["project_name"] = pkg.get("name", path.name)
            info["parameters"]["description"] = pkg.get("description", "")

            deps = set(pkg.get("dependencies", {}).keys())
            deps.update(pkg.get("devDependencies", {}).keys())

            if "next" in deps:
                info["type"] = "nextjs"
            elif "expo" in deps:
                info["type"] = "expo"
            elif "react" in deps:
                info["type"] = "react"
            elif "vue" in deps:
                info["type"] = "vue"
            else:
                info["type"] = "nodejs"

            info["technologies"] = list(deps)[:20]

        elif (path / "pyproject.toml").exists():
            info["type"] = "python"
            if (path / "manage.py").exists():
                info["type"] = "django"

        elif (path / "Cargo.toml").exists():
            info["type"] = "rust"

        elif (path / "go.mod").exists():
            info["type"] = "go"

        # Collect file structure
        for item in path.rglob("*"):
            if self._should_exclude(item, path):
                continue

            rel_path = item.relative_to(path)

            if item.is_file():
                info["files"].append(str(rel_path))
                if item.name in ["package.json", "pyproject.toml", "Cargo.toml",
                                 "tsconfig.json", ".eslintrc.js", "tailwind.config.js"]:
                    info["config_files"].append(str(rel_path))
            elif item.is_dir():
                info["directories"].append(str(rel_path))

        return info

    def _should_exclude(self, path: Path, root: Path) -> bool:
        """Check if path should be excluded."""
        rel_path = str(path.relative_to(root))

        for pattern in self.exclude_patterns:
            if pattern.startswith("*"):
                if path.suffix == pattern[1:]:
                    return True
            elif pattern in rel_path:
                return True

        return False

    async def _copy_and_process(
        self,
        source: Path,
        dest: Path,
        project_info: Dict
    ) -> None:
        """Copy files and process them for templating."""
        project_name = project_info.get("project_name", "project")

        for item in source.rglob("*"):
            if self._should_exclude(item, source):
                continue

            rel_path = item.relative_to(source)
            dest_path = dest / rel_path

            if item.is_dir():
                dest_path.mkdir(parents=True, exist_ok=True)
            elif item.is_file():
                dest_path.parent.mkdir(parents=True, exist_ok=True)

                # Read and process content
                try:
                    content = item.read_text()
                    processed = self._process_content(content, project_info)
                    dest_path.write_text(processed)
                except UnicodeDecodeError:
                    # Binary file, copy as-is
                    shutil.copy2(item, dest_path)

    def _process_content(self, content: str, project_info: Dict) -> str:
        """Process file content for templating."""
        project_name = project_info.get("project_name", "project")
        description = project_info.get("parameters", {}).get("description", "")

        # Replace project-specific values with template variables
        replacements = [
            (project_name, "{{PROJECT_NAME}}"),
            (description, "{{DESCRIPTION}}"),
            (re.compile(r'"version":\s*"[\d.]+"'), '"version": "{{VERSION}}"'),
        ]

        processed = content
        for pattern, replacement in replacements:
            if isinstance(pattern, str) and pattern:
                processed = processed.replace(pattern, replacement)
            elif hasattr(pattern, 'sub'):
                processed = pattern.sub(replacement, processed)

        return processed

    async def _generate_template_md(
        self,
        template_dir: Path,
        name: str,
        description: Optional[str],
        project_info: Dict
    ) -> None:
        """Generate TEMPLATE.md documentation."""
        content = f'''# {name}

{description or f"Template for {project_info.get('type')} projects."}

## Project Type

{project_info.get('type', 'unknown')}

## Technologies

{', '.join(project_info.get('technologies', [])[:10]) or 'N/A'}

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| PROJECT_NAME | Project name | my-project |
| DESCRIPTION | Project description | A new project |
| VERSION | Initial version | 1.0.0 |

## Structure

```
{chr(10).join(project_info.get('directories', [])[:15])}
```

## Usage

```bash
# Clone the template
clopus template use {name} my-new-project

# Or manually
cp -r templates/extracted/{name} ./my-new-project
cd my-new-project
# Replace {{{{PROJECT_NAME}}}}, {{{{DESCRIPTION}}}}, etc.
```

## Files

{len(project_info.get('files', []))} files included.

---
Extracted by CLOPUS on {datetime.now().strftime("%Y-%m-%d")}
'''

        (template_dir / "TEMPLATE.md").write_text(content)

    async def _generate_template_json(
        self,
        template_dir: Path,
        name: str,
        description: Optional[str],
        project_info: Dict
    ) -> None:
        """Generate template.json manifest."""
        manifest = {
            "name": name,
            "description": description or f"Template for {project_info.get('type')}",
            "version": "1.0.0",
            "type": project_info.get("type"),
            "author": "CLOPUS",
            "created_at": datetime.now().isoformat(),
            "parameters": {
                "PROJECT_NAME": {
                    "description": "Project name",
                    "default": "my-project",
                    "required": True
                },
                "DESCRIPTION": {
                    "description": "Project description",
                    "default": "A new project",
                    "required": False
                },
                "VERSION": {
                    "description": "Initial version",
                    "default": "1.0.0",
                    "required": False
                }
            },
            "files_count": len(project_info.get("files", [])),
            "technologies": project_info.get("technologies", [])[:20]
        }

        (template_dir / "template.json").write_text(
            json.dumps(manifest, indent=2)
        )

    async def discover_templates(self) -> List[Dict]:
        """Discover all available templates."""
        templates = []

        for template_dir in self.core_path.iterdir():
            if template_dir.is_dir():
                template = self._load_template_info(template_dir)
                if template:
                    template["source"] = "core"
                    templates.append(template)

        for template_dir in self.extracted_path.iterdir():
            if template_dir.is_dir():
                template = self._load_template_info(template_dir)
                if template:
                    template["source"] = "extracted"
                    templates.append(template)

        return templates

    def _load_template_info(self, template_dir: Path) -> Optional[Dict]:
        """Load template info from directory."""
        manifest_file = template_dir / "template.json"
        if manifest_file.exists():
            try:
                return json.loads(manifest_file.read_text())
            except:
                pass

        # Fallback to TEMPLATE.md
        template_md = template_dir / "TEMPLATE.md"
        if template_md.exists():
            return {
                "name": template_dir.name,
                "path": str(template_dir)
            }

        return None

    async def apply_template(
        self,
        template_name: str,
        dest_path: str,
        parameters: Dict[str, str]
    ) -> bool:
        """Apply a template to create a new project."""
        # Find template
        template_dir = None
        for search_path in [self.core_path, self.extracted_path]:
            candidate = search_path / template_name
            if candidate.exists():
                template_dir = candidate
                break

        if not template_dir:
            logger.error(f"Template not found: {template_name}")
            return False

        dest = Path(dest_path)
        dest.mkdir(parents=True, exist_ok=True)

        # Copy and replace parameters
        for item in template_dir.rglob("*"):
            if item.name in ["TEMPLATE.md", "template.json"]:
                continue

            rel_path = item.relative_to(template_dir)
            dest_item = dest / rel_path

            if item.is_dir():
                dest_item.mkdir(parents=True, exist_ok=True)
            elif item.is_file():
                dest_item.parent.mkdir(parents=True, exist_ok=True)

                try:
                    content = item.read_text()
                    # Replace parameters
                    for key, value in parameters.items():
                        content = content.replace(f"{{{{{key}}}}}", value)
                    dest_item.write_text(content)
                except UnicodeDecodeError:
                    shutil.copy2(item, dest_item)

        logger.info(f"Applied template {template_name} to {dest_path}")
        return True
