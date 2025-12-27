# =============================================================================
# CLOPUS v3 Design System
# =============================================================================
"""
Design system management for the Designer worker.
Handles design documentation, existing branding discovery, and design consultation.
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger("clopus.design_system")


class DesignSystem:
    """
    Manages design documentation and branding for CLOPUS projects.

    The Designer worker uses this to:
    - Create comprehensive design documentation
    - Discover existing project branding
    - Provide design consultation to other workers
    - Give feedback on screenshots
    """

    def __init__(self, memory_client=None):
        self.memory = memory_client

    # =========================================================================
    # DESIGN DOCUMENTATION GENERATION
    # =========================================================================

    async def create_design_task_description(
        self,
        project_path: str,
        objective: str,
        project_type: str,
        features: List[str]
    ) -> str:
        """
        Create a detailed task description for the Designer worker.
        This is assigned early in the project (after setup, before implementation).
        """
        project = Path(project_path)
        is_existing = await self._is_existing_project(project)

        if is_existing:
            return self._create_existing_project_task(project, objective, features)
        else:
            return self._create_new_project_task(project, objective, project_type, features)

    def _create_new_project_task(
        self,
        project: Path,
        objective: str,
        project_type: str,
        features: List[str]
    ) -> str:
        """Create design task for a new project."""
        features_text = "\n".join(f"- {f}" for f in features[:10]) if features else "- See objective above"

        return f"""# Design System Creation Task

## Project Context
**Objective:** {objective}
**Project Type:** {project_type}
**Path:** {project}

## Features to Design For:
{features_text}

## Your Task: Create Complete Design System

Create a comprehensive design system that other workers will follow. Save all documentation to `.clopus/design/`.

### Required Deliverables:

#### 1. DESIGN_SYSTEM.md (Main Reference)
Create `.clopus/design/DESIGN_SYSTEM.md` with:

```markdown
# [Project Name] Design System

## Brand Identity
- **Project Name:** [A memorable, relevant name]
- **Tagline:** [Brief description of what the project does]
- **Brand Personality:** [2-3 adjectives that describe the feel]

## Color Palette
| Role | Color | Hex | Usage |
|------|-------|-----|-------|
| Primary | [name] | #XXXXXX | Main actions, brand color |
| Secondary | [name] | #XXXXXX | Supporting elements |
| Accent | [name] | #XXXXXX | Highlights, CTAs |
| Background | [name] | #XXXXXX | Page backgrounds |
| Surface | [name] | #XXXXXX | Cards, elevated elements |
| Text Primary | [name] | #XXXXXX | Main text |
| Text Secondary | [name] | #XXXXXX | Muted text |
| Border | [name] | #XXXXXX | Dividers, borders |
| Error | [name] | #XXXXXX | Error states |
| Success | [name] | #XXXXXX | Success states |

### Dark Mode Colors
[Include dark mode variants for all colors above]

## Typography
- **Heading Font:** [Font family] - [Google Font link or system font]
- **Body Font:** [Font family]
- **Monospace Font:** [Font family for code]

### Type Scale
| Element | Size | Weight | Line Height |
|---------|------|--------|-------------|
| H1 | 2.5rem | 700 | 1.2 |
| H2 | 2rem | 600 | 1.3 |
| H3 | 1.5rem | 600 | 1.4 |
| Body | 1rem | 400 | 1.6 |
| Small | 0.875rem | 400 | 1.5 |
| Caption | 0.75rem | 400 | 1.4 |

## Spacing System
Base unit: 4px (0.25rem)
- xs: 4px (0.25rem)
- sm: 8px (0.5rem)
- md: 16px (1rem)
- lg: 24px (1.5rem)
- xl: 32px (2rem)
- 2xl: 48px (3rem)

## Border Radius
- none: 0
- sm: 4px
- md: 8px
- lg: 12px
- xl: 16px
- full: 9999px

## Shadows
- sm: 0 1px 2px rgba(0,0,0,0.05)
- md: 0 4px 6px rgba(0,0,0,0.1)
- lg: 0 10px 15px rgba(0,0,0,0.1)
- xl: 0 20px 25px rgba(0,0,0,0.15)

## Component Styles

### Buttons
[Describe primary, secondary, ghost, destructive button styles]

### Inputs
[Describe input fields, select boxes, checkboxes, etc.]

### Cards
[Describe card layouts, padding, shadows]

### Navigation
[Describe header, sidebar, mobile menu styles]

## Animation Guidelines
- Transitions: 150ms ease-in-out for hover states
- Page transitions: 200ms for content changes
- Use subtle animations, avoid excessive motion
```

#### 2. tailwind.config.js Theme Extension (if using Tailwind)
If the project uses Tailwind CSS, create `.clopus/design/tailwind-theme.js`:

```javascript
// Copy this to your tailwind.config.js theme.extend
{{
  colors: {{
    primary: {{ ... }},
    secondary: {{ ... }},
    // ... all colors
  }},
  fontFamily: {{ ... }},
  // ... other extensions
}}
```

#### 3. CSS Variables (if not using Tailwind)
Create `.clopus/design/variables.css` with CSS custom properties.

### Design Principles for This Project:

Based on the project type "{project_type}", consider:
- What emotions should the UI evoke?
- What is the target audience?
- Should it feel professional, playful, minimal, rich?
- What similar successful products can inspire (but not copy)?

### Important Notes:
- Choose colors that are accessible (WCAG AA contrast)
- Consider both light and dark modes
- Design must work on mobile, tablet, and desktop
- Keep it simple but distinctive

Begin by analyzing the objective and creating the complete design system.
"""

    def _create_existing_project_task(
        self,
        project: Path,
        objective: str,
        features: List[str]
    ) -> str:
        """Create design task for an existing project."""
        features_text = "\n".join(f"- {f}" for f in features[:10]) if features else "- See objective above"

        return f"""# Design System Discovery Task

## Project Context
**Objective:** {objective}
**Path:** {project}
**Status:** EXISTING PROJECT - Learn and document current design

## New Features Being Added:
{features_text}

## Your Task: Discover and Document Existing Design

This is an existing project. You must:

### 1. Analyze Existing Styles
Look at these locations for design information:
- CSS/SCSS files
- Tailwind config (if exists)
- Component files (look for inline styles, className patterns)
- Any existing design tokens or theme files
- package.json for UI libraries in use

### 2. Extract Color Palette
Find all colors used in the project:
- Search for hex codes (#XXXXXX)
- Look for RGB/HSL values
- Check for CSS variables (--color-*)
- Find Tailwind color classes

### 3. Identify Typography
- What fonts are being used?
- What are the heading and body sizes?
- Check for @import or Google Fonts links

### 4. Document Component Patterns
- How are buttons styled?
- What do cards look like?
- How is navigation structured?

### 5. Create Design Documentation
Save to `.clopus/design/DESIGN_SYSTEM.md`:
- Document everything you discover
- Note any inconsistencies found
- Provide guidance for new features to match existing style

### Important:
- DO NOT change the existing design
- New features must match the existing visual language
- If the existing design is inconsistent, document it and recommend which pattern to follow

Begin by reading the existing code and extracting the design system.
"""

    async def _is_existing_project(self, project: Path) -> bool:
        """Check if this is an existing project with code."""
        if not project.exists():
            return False

        # Check for source code
        indicators = [
            project / "src" / "App.tsx",
            project / "src" / "App.jsx",
            project / "src" / "index.tsx",
            project / "app" / "page.tsx",
            project / "pages" / "index.tsx",
            project / "main.py",
            project / "app.py",
        ]

        for indicator in indicators:
            if indicator.exists():
                return True

        # Check if src directory has files
        src_dir = project / "src"
        if src_dir.exists() and any(src_dir.iterdir()):
            return True

        return False

    # =========================================================================
    # DESIGN CONSULTATION
    # =========================================================================

    async def create_design_consultation_task(
        self,
        project_path: str,
        question: str,
        context: Optional[str] = None,
        screenshot_path: Optional[str] = None
    ) -> str:
        """
        Create a task for the Designer to consult on a design question.
        Other workers can request this when they need design guidance.
        """
        project = Path(project_path)

        task = f"""# Design Consultation Request

## Question
{question}

## Project
**Path:** {project}

"""
        if context:
            task += f"""## Context
{context}

"""

        if screenshot_path:
            task += f"""## Screenshot to Review
Please analyze the screenshot at: {screenshot_path}

Provide feedback on:
- Visual consistency with design system
- Layout and spacing issues
- Color usage correctness
- Typography adherence
- Accessibility concerns
- Suggested improvements

"""

        task += """## Your Response
1. Answer the design question directly
2. Reference the design system in `.clopus/design/DESIGN_SYSTEM.md`
3. Provide specific guidance (colors, spacing values, component patterns)
4. If recommending changes, explain why

Keep your response actionable for the developer.
"""
        return task

    # =========================================================================
    # SCREENSHOT FEEDBACK
    # =========================================================================

    async def create_screenshot_review_task(
        self,
        project_path: str,
        screenshot_path: str,
        component_name: Optional[str] = None
    ) -> str:
        """
        Create a task for the Designer to review a screenshot.
        Used during E2E testing to verify visual quality.
        """
        return f"""# Screenshot Design Review

## Screenshot
**Path:** {screenshot_path}
**Component:** {component_name or "Full page"}
**Project:** {project_path}

## Review Checklist

Please analyze this screenshot and provide feedback on:

### 1. Brand Consistency
- [ ] Colors match the design system
- [ ] Typography follows the type scale
- [ ] Spacing is consistent with the system

### 2. Visual Hierarchy
- [ ] Important elements stand out
- [ ] Reading order is clear
- [ ] Call-to-actions are visible

### 3. Layout Quality
- [ ] Alignment is consistent
- [ ] Whitespace is balanced
- [ ] No awkward gaps or cramped areas

### 4. Component Correctness
- [ ] Buttons look correct
- [ ] Inputs are styled properly
- [ ] Cards have correct shadows/borders

### 5. Accessibility
- [ ] Text is readable (contrast)
- [ ] Interactive elements are visible
- [ ] Focus states appear correct

### 6. Responsiveness (if applicable)
- [ ] Layout works for this viewport
- [ ] No horizontal overflow
- [ ] Touch targets appear adequate

## Output Format

```json
{{
  "overall_score": 8,  // 1-10
  "issues": [
    {{
      "severity": "high|medium|low",
      "element": "what element",
      "issue": "what's wrong",
      "fix": "how to fix it"
    }}
  ],
  "positive": ["what looks good"],
  "recommendations": ["suggestions for improvement"]
}}
```

Review the screenshot and provide your assessment.
"""

    # =========================================================================
    # DESIGN SYSTEM READER
    # =========================================================================

    async def get_design_system(self, project_path: str) -> Optional[Dict[str, Any]]:
        """
        Read the design system documentation for a project.
        Other workers can use this to understand the design.
        """
        project = Path(project_path)
        design_dir = project / ".clopus" / "design"

        if not design_dir.exists():
            return None

        design_system = {}

        # Read main design system doc
        main_doc = design_dir / "DESIGN_SYSTEM.md"
        if main_doc.exists():
            design_system["documentation"] = main_doc.read_text()

        # Read tailwind theme if exists
        tailwind_theme = design_dir / "tailwind-theme.js"
        if tailwind_theme.exists():
            design_system["tailwind_theme"] = tailwind_theme.read_text()

        # Read CSS variables if exists
        css_vars = design_dir / "variables.css"
        if css_vars.exists():
            design_system["css_variables"] = css_vars.read_text()

        # Read branding config if exists
        branding = design_dir.parent / "branding.json"
        if branding.exists():
            try:
                design_system["branding"] = json.loads(branding.read_text())
            except json.JSONDecodeError:
                pass

        return design_system if design_system else None

    async def extract_colors_from_design_system(
        self,
        project_path: str
    ) -> Dict[str, str]:
        """Extract color definitions from the design system."""
        design = await self.get_design_system(project_path)
        if not design or "documentation" not in design:
            return {}

        colors = {}
        doc = design["documentation"]

        # Extract hex colors from markdown tables or text
        hex_pattern = r'#([0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})\b'
        matches = re.findall(hex_pattern, doc)

        # Try to find labeled colors
        color_line_pattern = r'\|\s*(\w+)\s*\|[^|]*\|\s*#([0-9A-Fa-f]{6})\s*\|'
        labeled_matches = re.findall(color_line_pattern, doc)

        for name, hex_val in labeled_matches:
            colors[name.lower()] = f"#{hex_val}"

        return colors


class DesignConsultationQueue:
    """
    Queue for design consultations between workers.
    Other workers can submit questions, Designer answers them.
    """

    def __init__(self, ipc_path: str = "/app/ipc"):
        self.ipc_path = Path(ipc_path)
        self.queue_file = self.ipc_path / "design_consultations.json"

    async def submit_question(
        self,
        worker_id: int,
        project_path: str,
        question: str,
        context: Optional[str] = None,
        priority: int = 5
    ) -> str:
        """Submit a design question to the queue."""
        import uuid

        consultation_id = str(uuid.uuid4())[:8]

        consultation = {
            "id": consultation_id,
            "worker_id": worker_id,
            "project_path": project_path,
            "question": question,
            "context": context,
            "priority": priority,
            "status": "pending",
            "submitted_at": datetime.now().isoformat(),
            "response": None
        }

        # Load existing queue
        queue = self._load_queue()
        queue.append(consultation)
        self._save_queue(queue)

        logger.info(f"Design consultation submitted: {consultation_id}")
        return consultation_id

    async def get_pending_consultations(self) -> List[Dict]:
        """Get all pending design consultations."""
        queue = self._load_queue()
        pending = [c for c in queue if c["status"] == "pending"]
        return sorted(pending, key=lambda x: x["priority"], reverse=True)

    async def respond_to_consultation(
        self,
        consultation_id: str,
        response: str
    ) -> bool:
        """Respond to a design consultation."""
        queue = self._load_queue()

        for consultation in queue:
            if consultation["id"] == consultation_id:
                consultation["status"] = "completed"
                consultation["response"] = response
                consultation["completed_at"] = datetime.now().isoformat()
                self._save_queue(queue)
                logger.info(f"Design consultation completed: {consultation_id}")
                return True

        return False

    async def get_response(self, consultation_id: str) -> Optional[str]:
        """Get the response for a consultation."""
        queue = self._load_queue()

        for consultation in queue:
            if consultation["id"] == consultation_id:
                return consultation.get("response")

        return None

    def _load_queue(self) -> List[Dict]:
        """Load the consultation queue."""
        if self.queue_file.exists():
            try:
                return json.loads(self.queue_file.read_text())
            except json.JSONDecodeError:
                return []
        return []

    def _save_queue(self, queue: List[Dict]) -> None:
        """Save the consultation queue."""
        self.queue_file.parent.mkdir(parents=True, exist_ok=True)
        self.queue_file.write_text(json.dumps(queue, indent=2))


# Singleton instances
_design_system: Optional[DesignSystem] = None
_consultation_queue: Optional[DesignConsultationQueue] = None


def get_design_system(memory_client=None) -> DesignSystem:
    """Get the design system instance."""
    global _design_system
    if _design_system is None:
        _design_system = DesignSystem(memory_client)
    return _design_system


def get_consultation_queue() -> DesignConsultationQueue:
    """Get the consultation queue instance."""
    global _consultation_queue
    if _consultation_queue is None:
        _consultation_queue = DesignConsultationQueue()
    return _consultation_queue
