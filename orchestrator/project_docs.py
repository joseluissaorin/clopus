# =============================================================================
# CLOPUS v3 Project Documentation Generator
# =============================================================================
"""
Auto-generates project documentation with features, stack, process, and branding.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger("clopus.project_docs")


class ProjectDocsGenerator:
    """Generates project documentation automatically."""

    def __init__(self):
        pass

    async def generate_project_docs(
        self,
        project_path: str,
        objective: str,
        tasks_completed: List[Dict[str, Any]],
        validation_results: Dict[str, Any],
        port: int,
        branding: Optional[Dict[str, Any]] = None,
        project_state: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a comprehensive project documentation file.

        Returns the path to the generated documentation.
        """
        project = Path(project_path)
        project_name = project.name

        # Detect stack
        stack = await self._detect_stack(project)

        # Build documentation
        doc = self._build_documentation(
            project_name=project_name,
            objective=objective,
            tasks_completed=tasks_completed,
            validation_results=validation_results,
            port=port,
            stack=stack,
            branding=branding,
            project_state=project_state
        )

        # Write documentation
        docs_path = project / "PROJECT.md"
        docs_path.write_text(doc)

        logger.info(f"Generated project documentation: {docs_path}")
        return str(docs_path)

    async def _detect_stack(self, project: Path) -> Dict[str, Any]:
        """Detect the technology stack used in the project."""
        stack = {
            "frontend": [],
            "backend": [],
            "database": [],
            "tools": [],
            "testing": [],
            "styling": []
        }

        # Check for package.json (Node.js projects)
        pkg_path = project / "package.json"
        if pkg_path.exists():
            try:
                pkg = json.loads(pkg_path.read_text())

                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

                # Frontend frameworks
                if "react" in deps:
                    version = deps.get("react", "").lstrip("^~")
                    stack["frontend"].append(f"React {version.split('.')[0] if version else ''}")
                if "vue" in deps:
                    stack["frontend"].append("Vue.js")
                if "next" in deps:
                    stack["frontend"].append("Next.js")
                if "svelte" in deps:
                    stack["frontend"].append("Svelte")
                if "solid-js" in deps:
                    stack["frontend"].append("Solid.js")

                # Build tools
                if "vite" in deps:
                    stack["tools"].append("Vite")
                if "webpack" in deps:
                    stack["tools"].append("Webpack")
                if "esbuild" in deps:
                    stack["tools"].append("esbuild")

                # TypeScript
                if "typescript" in deps:
                    stack["tools"].append("TypeScript")

                # Styling
                if "tailwindcss" in deps:
                    stack["styling"].append("Tailwind CSS")
                if "@emotion/react" in deps or "styled-components" in deps:
                    stack["styling"].append("CSS-in-JS")
                if "sass" in deps:
                    stack["styling"].append("Sass")

                # Testing
                if "vitest" in deps:
                    stack["testing"].append("Vitest")
                if "jest" in deps:
                    stack["testing"].append("Jest")
                if "@testing-library/react" in deps:
                    stack["testing"].append("React Testing Library")
                if "playwright" in deps or "@playwright/test" in deps:
                    stack["testing"].append("Playwright")
                if "cypress" in deps:
                    stack["testing"].append("Cypress")

                # Backend (Node)
                if "express" in deps:
                    stack["backend"].append("Express.js")
                if "fastify" in deps:
                    stack["backend"].append("Fastify")

            except Exception as e:
                logger.warning(f"Error parsing package.json: {e}")

        # Check for Python projects
        requirements = project / "requirements.txt"
        pyproject = project / "pyproject.toml"

        if requirements.exists() or pyproject.exists():
            # Python stack
            stack["backend"].append("Python")

            if (project / "manage.py").exists():
                stack["backend"].append("Django")
            elif (project / "app.py").exists() or (project / "main.py").exists():
                if requirements.exists():
                    req_text = requirements.read_text().lower()
                    if "fastapi" in req_text:
                        stack["backend"].append("FastAPI")
                    elif "flask" in req_text:
                        stack["backend"].append("Flask")

            stack["testing"].append("Pytest")

        # Check for Rust
        if (project / "Cargo.toml").exists():
            stack["backend"].append("Rust")
            stack["tools"].append("Cargo")

        # Check for Go
        if (project / "go.mod").exists():
            stack["backend"].append("Go")

        return stack

    def _build_documentation(
        self,
        project_name: str,
        objective: str,
        tasks_completed: List[Dict[str, Any]],
        validation_results: Dict[str, Any],
        port: int,
        stack: Dict[str, Any],
        branding: Optional[Dict[str, Any]] = None,
        project_state: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build the documentation markdown."""

        # Format stack sections
        stack_sections = []
        for category, items in stack.items():
            if items:
                stack_sections.append(f"**{category.title()}:** {', '.join(items)}")

        stack_text = "\n".join(f"- {s}" for s in stack_sections) if stack_sections else "- Standard web technologies"

        # Format tasks
        tasks_text = ""
        if tasks_completed:
            for task in tasks_completed[:10]:  # Limit to 10 tasks
                status_icon = "x" if task.get("success") else " "
                tasks_text += f"- [{status_icon}] {task.get('title', 'Unknown task')}\n"
        else:
            tasks_text = "- Project setup and implementation\n"

        # Build status section from project state
        status_section = ""
        if project_state:
            overall_status = project_state.get("status", "unknown").upper()
            stages = project_state.get("stages", {})
            validation = project_state.get("validation", {})
            dev_server = project_state.get("dev_server", {})

            # Stage status table
            stage_rows = []
            for stage_name in ["setup", "design", "implementation", "validation", "e2e_testing", "documentation"]:
                stage_info = stages.get(stage_name, {})
                status = stage_info.get("status", "pending")
                icon = "x" if status == "completed" else "~" if status == "in_progress" else " "
                stage_rows.append(f"| {stage_name.replace('_', ' ').title()} | [{icon}] {status.title()} |")

            # Validation details
            val_passed = validation.get("stages_passed", [])
            val_failed = validation.get("stages_failed", [])
            val_pending = validation.get("stages_pending", [])
            val_count = f"{len(val_passed)}/{len(val_passed) + len(val_failed) + len(val_pending)}"

            # Dev server info
            server_status = "Running" if dev_server.get("running") else "Stopped"
            server_port = dev_server.get("port") or dev_server.get("allocated_port") or port
            server_url = dev_server.get("url") or f"http://localhost:{server_port}"

            status_section = f"""
## Current Status

> **Overall: {overall_status}** | Validation: {val_count} passed

### Stage Progress

| Stage | Status |
|-------|--------|
{chr(10).join(stage_rows)}

### Validation Details

| Stage | Status |
|-------|--------|
{"".join(f'| {s.title()} | Passed |{chr(10)}' for s in val_passed)}{"".join(f'| {s.title()} | **FAILED** |{chr(10)}' for s in val_failed)}{"".join(f'| {s.title()} | Pending |{chr(10)}' for s in val_pending)}

### Dev Server

- **Status:** {server_status}
- **Port:** {server_port}
- **URL:** {server_url}

---
"""
        else:
            # Simple status if no state available
            status_section = f"""
## Dev Server

- **Port:** {port}
- **URL:** http://localhost:{port}
- **Network:** http://<your-ip>:{port}

---
"""

        # Branding section
        branding_text = ""
        if branding:
            branding_text = f"""
## Branding

- **Name:** {branding.get('name', project_name)}
- **Primary Color:** {branding.get('primary_color', '#3B82F6')}
- **Secondary Color:** {branding.get('secondary_color', '#6366F1')}
- **Accent Color:** {branding.get('accent_color', '#22D3EE')}
- **Font:** {branding.get('font', 'Inter')}

---
"""

        # Build the full document
        doc = f"""# {project_name.replace('-', ' ').title()}

> Auto-generated by CLOPUS on {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

## Overview

{objective}

---
{status_section}
## Technology Stack

{stack_text}

---

## Features Implemented

{tasks_text}

---
{branding_text}
## Project Structure

```
{project_name}/
├── src/           # Source code
├── public/        # Static assets
├── tests/         # Test files
├── .clopus/       # CLOPUS metadata
│   ├── design/    # Design system
│   └── project_state.json
└── package.json   # Dependencies
```

---

## Development Notes

This project was autonomously created by CLOPUS (Claude Orchestrated Parallel Universal System).

### Decision Log

1. **Framework Choice:** Selected based on objective requirements and performance considerations
2. **Styling:** Chosen for rapid development and consistency
3. **Testing:** Configured for comprehensive coverage

---

*Generated by CLOPUS v3*
"""
        return doc


class BrandingGenerator:
    """Generates branding (name, colors) for projects."""

    # Color palettes for different project types
    COLOR_PALETTES = {
        "todo": {
            "primary": "#3B82F6",    # Blue
            "secondary": "#6366F1",   # Indigo
            "accent": "#22D3EE"       # Cyan
        },
        "dashboard": {
            "primary": "#6366F1",    # Indigo
            "secondary": "#8B5CF6",   # Purple
            "accent": "#F59E0B"       # Amber
        },
        "ecommerce": {
            "primary": "#10B981",    # Emerald
            "secondary": "#059669",   # Green
            "accent": "#F97316"       # Orange
        },
        "social": {
            "primary": "#EC4899",    # Pink
            "secondary": "#F43F5E",   # Rose
            "accent": "#8B5CF6"       # Purple
        },
        "productivity": {
            "primary": "#0EA5E9",    # Sky
            "secondary": "#3B82F6",   # Blue
            "accent": "#22C55E"       # Green
        },
        "default": {
            "primary": "#3B82F6",    # Blue
            "secondary": "#6366F1",   # Indigo
            "accent": "#22D3EE"       # Cyan
        }
    }

    # Font suggestions
    FONTS = ["Inter", "Poppins", "Roboto", "Open Sans", "Montserrat"]

    def __init__(self):
        pass

    def generate_branding(
        self,
        project_name: str,
        project_type: str,
        objective: str
    ) -> Dict[str, str]:
        """Generate branding for a project."""

        # Determine project category from objective
        objective_lower = objective.lower()
        category = "default"

        if any(word in objective_lower for word in ["todo", "task", "checklist", "list"]):
            category = "todo"
        elif any(word in objective_lower for word in ["dashboard", "admin", "analytics", "panel"]):
            category = "dashboard"
        elif any(word in objective_lower for word in ["shop", "store", "ecommerce", "cart", "product"]):
            category = "ecommerce"
        elif any(word in objective_lower for word in ["social", "chat", "message", "community"]):
            category = "social"
        elif any(word in objective_lower for word in ["productivity", "notes", "calendar", "schedule"]):
            category = "productivity"

        colors = self.COLOR_PALETTES.get(category, self.COLOR_PALETTES["default"])

        # Generate a display name
        display_name = self._generate_display_name(project_name)

        # Select a font based on category
        font_index = hash(project_name) % len(self.FONTS)
        font = self.FONTS[font_index]

        return {
            "name": display_name,
            "primary_color": colors["primary"],
            "secondary_color": colors["secondary"],
            "accent_color": colors["accent"],
            "font": font,
            "category": category
        }

    def _generate_display_name(self, project_name: str) -> str:
        """Generate a display name from project name."""
        # Clean up project name
        name = project_name.replace("-", " ").replace("_", " ")

        # Title case
        words = name.split()
        formatted = " ".join(word.capitalize() for word in words)

        return formatted

    def create_brand_config(
        self,
        project_path: str,
        branding: Dict[str, str]
    ) -> str:
        """Create a branding configuration file for the project."""
        project = Path(project_path)

        # Create branding config
        config = {
            "brand": {
                "name": branding["name"],
                "colors": {
                    "primary": branding["primary_color"],
                    "secondary": branding["secondary_color"],
                    "accent": branding["accent_color"]
                },
                "font": branding["font"]
            },
            "generated_by": "CLOPUS v3",
            "generated_at": datetime.now().isoformat()
        }

        # Write config file
        config_path = project / ".clopus" / "branding.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(config, indent=2))

        logger.info(f"Created branding config: {config_path}")
        return str(config_path)


# Singleton instances
_docs_generator: Optional[ProjectDocsGenerator] = None
_branding_generator: Optional[BrandingGenerator] = None


def get_docs_generator() -> ProjectDocsGenerator:
    """Get the documentation generator instance."""
    global _docs_generator
    if _docs_generator is None:
        _docs_generator = ProjectDocsGenerator()
    return _docs_generator


def get_branding_generator() -> BrandingGenerator:
    """Get the branding generator instance."""
    global _branding_generator
    if _branding_generator is None:
        _branding_generator = BrandingGenerator()
    return _branding_generator
