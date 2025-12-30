# =============================================================================
# CLOPUS v3 Task Planner
# =============================================================================
"""
Breaks down objectives into executable tasks with dependencies.

NEW IN v3.1: AI-First Planning
- Uses Claude Code intelligence to analyze ANY objective
- Generates custom tasks tailored to specific requirements
- Supports multi-project objectives
- Falls back to templates only when AI is unavailable

NEW IN v3.2: AI-First Dependency Analysis
- Uses AI intelligence for semantic dependency detection
- Falls back to explicit dependencies when AI unavailable

The template-based approach is DEPRECATED and only used as fallback.
"""

import asyncio
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple, TYPE_CHECKING
from dataclasses import dataclass, field
import logging

if TYPE_CHECKING:
    from .ai_first import AIFirstEngine

logger = logging.getLogger("clopus.task_planner")


@dataclass
class PlannedTask:
    """A planned task with metadata."""
    id: str
    title: str
    description: str
    worker_role: str
    priority: int
    dependencies: List[str] = field(default_factory=list)
    estimated_duration: str = "medium"  # short, medium, long
    validation_required: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)  # Task-specific metadata


class TaskPlanner:
    """
    Plan and decompose objectives into tasks.

    AI-FIRST APPROACH:
    This planner now primarily uses Claude Code intelligence to:
    1. Analyze objectives without pattern matching
    2. Generate custom project structures
    3. Create tailored tasks for ANY type of objective
    4. Support multi-project objectives

    NEW IN v3.2: AI-First Dependency Analysis
    - Uses AI intelligence for semantic dependency detection
    - Falls back to explicit dependencies when AI unavailable

    The template-based approach is kept ONLY as a fallback when AI is unavailable.
    """

    def __init__(self, memory_client, confidence_engine, objective_parser):
        self.memory = memory_client
        self.confidence = confidence_engine
        self.parser = objective_parser

        # AI Planner - PRIMARY approach (set by orchestrator)
        self.ai_planner = None

        # AI-First Engine (set by orchestrator, NEW in v3.2)
        self.ai_engine: Optional["AIFirstEngine"] = None

        # Skills engine and template extractor (set by orchestrator)
        self.skills_engine = None
        self.template_extractor = None

        # Worker pool for AI planning (set by orchestrator)
        self.worker_pool = None

    def set_ai_engine(self, ai_engine: "AIFirstEngine") -> None:
        """Set the AI-first engine for intelligent dependency analysis."""
        self.ai_engine = ai_engine
        logger.info("AI-First Engine connected to task planner")

        # DEPRECATED: Template-based patterns (kept for fallback only)
        self.project_templates = {
            "todo_app": self._todo_app_tasks,
            "api": self._api_tasks,
            "dashboard": self._dashboard_tasks,
            "mobile": self._mobile_tasks,
            "cli": self._cli_tasks,
            "website": self._website_tasks,
            "ecommerce": self._ecommerce_tasks,
            "scraper": self._scraper_tasks,
            "custom": self._custom_tasks,
        }

        # Worker role capabilities
        self.role_capabilities = {
            "coder": ["implementation", "feature", "refactoring", "architecture"],
            "tester": ["testing", "unit_tests", "integration_tests", "e2e_tests"],
            "reviewer": ["code_review", "security_review", "documentation"],
            "researcher": ["research", "api_docs", "dependencies", "investigation"],
            "debugger": ["debugging", "error_fixing", "performance", "troubleshooting"],
            "designer": ["design_system", "branding", "ui_ux", "visual_design", "screenshot_review"],
        }

        # Design system for creating design tasks
        self.design_system = None

    def set_worker_pool(self, worker_pool) -> None:
        """Set worker pool for AI planning."""
        self.worker_pool = worker_pool
        logger.info("Worker pool connected to task planner")

    def set_ai_planner(self, ai_planner) -> None:
        """Set the AI planner for intelligent task generation."""
        self.ai_planner = ai_planner
        logger.info("AI Planner connected - using AI-first task generation")

    async def plan(self, objective_id: str, parsed_objective: Dict) -> List[Dict]:
        """
        Create a task plan for an objective.

        PRIMARY: Uses AI Planner for intelligent task generation
        FALLBACK: Uses templates only when AI is unavailable
        """
        logger.info(f"Planning tasks for objective: {objective_id}")

        # Get the original objective text
        original_objective = parsed_objective.get("original", "")
        if not original_objective:
            original_objective = parsed_objective.get("description", "")
            if not original_objective:
                original_objective = parsed_objective.get("summary", "")

        # =====================================================================
        # AI-FIRST PLANNING (PRIMARY APPROACH)
        # =====================================================================
        if self.ai_planner or self.worker_pool:
            try:
                logger.info("Using AI-first planning approach")
                tasks = await self._plan_with_ai(objective_id, original_objective, parsed_objective)
                if tasks:
                    logger.info(f"AI planning generated {len(tasks)} tasks")
                    return tasks
                logger.warning("AI planning returned no tasks, falling back to templates")
            except Exception as e:
                logger.error(f"AI planning failed: {e}, falling back to templates")

        # =====================================================================
        # FALLBACK: Template-based planning (DEPRECATED)
        # =====================================================================
        logger.warning("Using DEPRECATED template-based planning - AI planner unavailable")
        return await self._plan_with_templates(objective_id, parsed_objective)

    async def _plan_with_ai(
        self,
        objective_id: str,
        objective_text: str,
        parsed_objective: Dict
    ) -> List[Dict]:
        """
        Use AI Planner for intelligent task generation.

        This is the PRIMARY approach that uses Claude Code intelligence.
        """
        # Initialize AI planner if needed
        if not self.ai_planner and self.worker_pool:
            from .ai_planner import AIPlanner
            self.ai_planner = AIPlanner(self.worker_pool, self.memory)
            logger.info("Initialized AI Planner on-demand")

        if not self.ai_planner:
            return []

        # Let AI analyze the objective and generate projects + tasks
        projects, ai_tasks = await self.ai_planner.plan_objective(
            objective_text,
            objective_id
        )

        if not ai_tasks:
            return []

        # Convert AI tasks to the expected format
        from .ai_planner import convert_ai_tasks_to_planned_tasks
        task_dicts = convert_ai_tasks_to_planned_tasks(ai_tasks, projects)

        # Store project information in parsed_objective for other systems
        parsed_objective["_ai_projects"] = [
            {
                "id": p.id,
                "name": p.name,
                "path": p.path,
                "technologies": p.technologies,
                "depends_on": p.depends_on
            }
            for p in projects
        ]

        return task_dicts

    async def _plan_with_templates(
        self,
        objective_id: str,
        parsed_objective: Dict
    ) -> List[Dict]:
        """
        DEPRECATED: Template-based planning.

        Only used as fallback when AI planner is unavailable.
        """
        project_type = parsed_objective.get("project_type", "custom")
        technologies = parsed_objective.get("technologies", [])
        features = parsed_objective.get("features", [])
        complexity = parsed_objective.get("estimated_complexity", "medium")
        objective_description = parsed_objective.get("description", "")

        # =====================================================================
        # CHECK FOR EXISTING TEMPLATES
        # =====================================================================
        applied_template = None
        if self.template_extractor:
            try:
                matching_templates = await self._find_matching_templates(
                    project_type, technologies, objective_description
                )
                if matching_templates:
                    applied_template = matching_templates[0]
                    logger.info(f"Found matching template: {applied_template.get('name')}")
            except Exception as e:
                logger.warning(f"Error searching templates: {e}")

        # =====================================================================
        # FIND RELEVANT SKILLS
        # =====================================================================
        relevant_skills = []
        if self.skills_engine:
            try:
                # Search for skills matching project type and technologies
                search_terms = [project_type] + technologies[:3]
                for term in search_terms:
                    skills = await self.skills_engine.search_skills(term)
                    for skill in skills[:2]:  # Top 2 per term
                        if skill not in relevant_skills:
                            relevant_skills.append(skill)
                if relevant_skills:
                    logger.info(f"Found {len(relevant_skills)} relevant skills for planning")
            except Exception as e:
                logger.warning(f"Error searching skills: {e}")

        # Get template-based tasks
        template_fn = self.project_templates.get(project_type, self._custom_tasks)
        base_tasks = template_fn(parsed_objective)

        # If we have a template, use its structure instead
        if applied_template:
            template_tasks = await self._tasks_from_template(applied_template, parsed_objective)
            if template_tasks:
                base_tasks = template_tasks
                logger.info(f"Using {len(template_tasks)} tasks from template")

        # =====================================================================
        # ADD DESIGN TASK EARLY (Designer creates branding before implementation)
        # =====================================================================
        design_task = await self._create_design_task(
            project_type=project_type,
            objective_description=objective_description,
            features=features,
            base_tasks=base_tasks
        )
        if design_task:
            # Insert design task near the beginning (after setup/research, before implementation)
            base_tasks.insert(min(2, len(base_tasks)), design_task)
            logger.info("Added design task to plan")

        # Add feature-specific tasks
        feature_tasks = self._plan_feature_tasks(features, technologies)
        base_tasks.extend(feature_tasks)

        # Get relevant past patterns from memory
        context = await self.memory.get_relevant_context(
            f"task planning for {project_type} with {technologies}"
        )

        # Store relevant skills in task metadata for workers
        if relevant_skills:
            parsed_objective["_relevant_skills"] = [
                {"name": s["name"], "path": s["path"]}
                for s in relevant_skills[:5]
            ]

        # Add testing tasks (includes E2E for all web projects)
        test_tasks = self._plan_testing_tasks(base_tasks, complexity, project_type, technologies)
        base_tasks.extend(test_tasks)

        # Add review task
        base_tasks.append(PlannedTask(
            id=str(uuid.uuid4()),
            title="Final code review",
            description="Review all code for quality, security, and best practices",
            worker_role="reviewer",
            priority=3,
            dependencies=[t.id for t in base_tasks if t.worker_role == "coder"],
            validation_required=True
        ))

        # Set proper dependencies (use async for AI-first)
        tasks_with_deps = await self._resolve_dependencies_async(base_tasks)

        # Convert to dictionaries
        return [self._task_to_dict(t) for t in tasks_with_deps]

    def _task_to_dict(self, task: PlannedTask) -> Dict:
        """Convert PlannedTask to dictionary."""
        return {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "worker_role": task.worker_role,
            "priority": task.priority,
            "dependencies": task.dependencies,
            "estimated_duration": task.estimated_duration,
            "validation_required": task.validation_required,
            "metadata": task.metadata
        }

    async def _resolve_dependencies_async(self, tasks: List[PlannedTask]) -> List[PlannedTask]:
        """
        Ensure dependencies are properly ordered.

        NEW IN v3.2: AI-First approach
        Priority:
        1. AI-First Engine (semantic dependency analysis)
        2. Explicit dependencies with cycle detection (fallback)

        Detects and handles circular dependencies by removing the problematic
        dependency links.
        """
        # Try AI-First Engine for semantic dependency analysis
        if self.ai_engine:
            try:
                task_data = [
                    {"id": t.id, "title": t.title, "description": t.description[:200]}
                    for t in tasks
                ]
                result = await self.ai_engine.analyze_task_dependencies(task_data)
                if result.success and result.result:
                    dependency_graph = result.result.get("dependency_graph", {})
                    if dependency_graph:
                        # Update task dependencies from AI analysis
                        for task in tasks:
                            ai_deps = dependency_graph.get(task.id, [])
                            if ai_deps:
                                # Merge AI-detected deps with explicit deps
                                task.dependencies = list(set(task.dependencies + ai_deps))
                        logger.debug(f"AI-first analyzed dependencies for {len(tasks)} tasks")
            except Exception as e:
                logger.debug(f"AI-first dependency analysis failed: {e}")

        # Continue with explicit dependency resolution
        return self._explicit_resolve_dependencies(tasks)

    def _resolve_dependencies(self, tasks: List[PlannedTask]) -> List[PlannedTask]:
        """Sync wrapper for backward compatibility."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # In async context, skip AI and use explicit resolution
                return self._explicit_resolve_dependencies(tasks)
            return loop.run_until_complete(
                self._resolve_dependencies_async(tasks)
            )
        except RuntimeError:
            return self._explicit_resolve_dependencies(tasks)

    def _explicit_resolve_dependencies(self, tasks: List[PlannedTask]) -> List[PlannedTask]:
        """DEPRECATED: Explicit dependency resolution. Use AI-first instead."""
        # Build dependency graph
        task_map = {t.id: t for t in tasks}

        # Assign priorities based on dependencies
        for task in tasks:
            if not task.dependencies:
                task.priority = max(task.priority, 8)  # High priority for no deps
            else:
                try:
                    # Priority based on dependency chain depth
                    depth = self._get_dependency_depth(task, task_map)
                    task.priority = max(1, 10 - depth)
                except ValueError as e:
                    # Circular dependency detected - log and break the cycle
                    logger.error(f"Circular dependency detected: {e}")
                    logger.warning(f"Breaking dependency cycle for task: {task.title}")

                    # Remove the last dependency to break the cycle
                    if task.dependencies:
                        removed_dep = task.dependencies.pop()
                        logger.info(f"Removed dependency {removed_dep} from task {task.id}")

                    # Set moderate priority since we can't calculate depth
                    task.priority = 5

        return sorted(tasks, key=lambda t: (-t.priority, len(t.dependencies)))

    def _get_dependency_depth(self, task: PlannedTask, task_map: Dict, visited: Optional[set] = None) -> int:
        """Get the depth of dependencies with cycle detection.

        Args:
            task: The task to calculate depth for
            task_map: Map of task IDs to PlannedTask objects
            visited: Set of already visited task IDs (for cycle detection)

        Returns:
            The maximum depth of the dependency chain

        Raises:
            ValueError: If a circular dependency is detected
        """
        if visited is None:
            visited = set()

        # Detect circular dependency
        if task.id in visited:
            raise ValueError(f"Circular dependency detected involving task: {task.id} ({task.title})")

        if not task.dependencies:
            return 0

        # Add current task to visited set
        visited.add(task.id)

        max_depth = 0
        for dep_id in task.dependencies:
            if dep_id in task_map:
                # Pass a copy of visited set to allow parallel branches
                depth = self._get_dependency_depth(task_map[dep_id], task_map, visited.copy())
                max_depth = max(max_depth, depth + 1)

        return max_depth

    # =========================================================================
    # DESIGN TASK CREATION
    # =========================================================================

    async def _create_design_task(
        self,
        project_type: str,
        objective_description: str,
        features: List[Dict],
        base_tasks: List[PlannedTask]
    ) -> Optional[PlannedTask]:
        """
        Create a design task that runs early in the project.
        The Designer will create comprehensive branding and design documentation.
        """
        # Only add design task for UI projects
        ui_project_types = [
            "todo_app", "dashboard", "website", "ecommerce",
            "mobile", "react", "nextjs", "vue", "angular"
        ]

        # Check if project has UI component
        has_ui = (
            project_type in ui_project_types or
            any(t.worker_role == "coder" and "ui" in t.title.lower() for t in base_tasks) or
            "ui" in objective_description.lower() or
            "frontend" in objective_description.lower() or
            "react" in objective_description.lower() or
            "website" in objective_description.lower() or
            "app" in objective_description.lower()
        )

        if not has_ui:
            return None

        # Get setup task ID for dependency
        setup_task_ids = [
            t.id for t in base_tasks
            if "setup" in t.title.lower() or "init" in t.title.lower()
        ]

        # Extract feature descriptions
        feature_descriptions = [
            f.get("description", "") for f in features[:10]
        ] if features else []

        # Create comprehensive design task description
        description = f"""Create comprehensive design system and branding documentation.

## Project Context
**Type:** {project_type}
**Objective:** {objective_description[:500]}

## Features to Design For:
{chr(10).join(f'- {f}' for f in feature_descriptions) if feature_descriptions else '- See objective above'}

## Required Outputs (save to .clopus/design/):

### 1. DESIGN_SYSTEM.md
Complete design documentation including:
- Brand identity (name, tagline, personality)
- Color palette (primary, secondary, accent, backgrounds, text, states)
- Dark mode colors
- Typography (fonts, type scale, weights)
- Spacing system
- Border radius scale
- Shadow definitions
- Component styles (buttons, inputs, cards, navigation)
- Animation guidelines

### 2. tailwind-theme.js (if using Tailwind)
Ready-to-copy theme configuration

### 3. variables.css (if not using Tailwind)
CSS custom properties for all design tokens

## Design Principles:
- Unique, memorable brand that matches the project purpose
- Accessible colors (WCAG AA contrast)
- Responsive design support
- Consistent visual language
- Modern but timeless aesthetic

## Important:
This design system will be followed by ALL other workers.
Be specific with values (exact hex codes, rem values, etc).
"""

        return PlannedTask(
            id=str(uuid.uuid4()),
            title="Create design system and branding",
            description=description,
            worker_role="designer",
            priority=9,  # High priority, runs early
            dependencies=setup_task_ids[:1] if setup_task_ids else [],
            estimated_duration="medium",
            validation_required=False  # Design docs don't need code validation
        )

    # =========================================================================
    # PROJECT TYPE TEMPLATES
    # =========================================================================

    def _todo_app_tasks(self, parsed: Dict) -> List[PlannedTask]:
        """Tasks for a todo app."""
        tasks = []

        setup_id = str(uuid.uuid4())
        tasks.append(PlannedTask(
            id=setup_id,
            title="Project setup and configuration",
            description="Initialize React/TypeScript project with required dependencies",
            worker_role="coder",
            priority=10,
            estimated_duration="short"
        ))

        model_id = str(uuid.uuid4())
        tasks.append(PlannedTask(
            id=model_id,
            title="Create data models and types",
            description="Define Todo interface, status types, and data structures",
            worker_role="coder",
            priority=9,
            dependencies=[setup_id],
            estimated_duration="short"
        ))

        state_id = str(uuid.uuid4())
        tasks.append(PlannedTask(
            id=state_id,
            title="Implement state management",
            description="Create todo store/context with CRUD operations",
            worker_role="coder",
            priority=8,
            dependencies=[model_id],
            estimated_duration="medium"
        ))

        ui_id = str(uuid.uuid4())
        tasks.append(PlannedTask(
            id=ui_id,
            title="Build UI components",
            description="Create TodoList, TodoItem, AddTodo, and Filter components",
            worker_role="coder",
            priority=7,
            dependencies=[state_id],
            estimated_duration="medium"
        ))

        tasks.append(PlannedTask(
            id=str(uuid.uuid4()),
            title="Add persistence",
            description="Implement localStorage or API persistence for todos",
            worker_role="coder",
            priority=6,
            dependencies=[state_id],
            estimated_duration="short"
        ))

        tasks.append(PlannedTask(
            id=str(uuid.uuid4()),
            title="Style application",
            description="Add CSS/Tailwind styling for all components",
            worker_role="coder",
            priority=5,
            dependencies=[ui_id],
            estimated_duration="short"
        ))

        return tasks

    def _api_tasks(self, parsed: Dict) -> List[PlannedTask]:
        """Tasks for an API project."""
        tasks = []

        # Database requirements warning to inject into all endpoint tasks
        db_requirement_warning = """
## CRITICAL: Database Integration Required

You MUST use SQLAlchemy with the PostgreSQL database. DO NOT use in-memory storage.

### Required Pattern:
```python
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.{resource} import {Resource}

@router.post("", response_model={Resource}Response)
async def create_{resource}(
    data: {Resource}Create,
    db: Session = Depends(get_db)  # <-- REQUIRED
):
    db_obj = {Resource}(**data.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj
```

### FORBIDDEN Patterns (will be REJECTED):
- `_db: dict = {}`  # In-memory storage
- `_storage = {}`   # In-memory storage
- Missing `Depends(get_db)` in endpoints
- Importing models but not using them
"""

        setup_id = str(uuid.uuid4())
        tasks.append(PlannedTask(
            id=setup_id,
            title="API project setup",
            description="Initialize FastAPI project with dependencies and configuration. Include SQLAlchemy, asyncpg, and alembic for database.",
            worker_role="coder",
            priority=10,
            estimated_duration="short",
            metadata={"database_required": True}
        ))

        research_id = str(uuid.uuid4())
        tasks.append(PlannedTask(
            id=research_id,
            title="Research API requirements",
            description="Analyze required endpoints, data models, and integrations",
            worker_role="researcher",
            priority=10,
            estimated_duration="short"
        ))

        models_id = str(uuid.uuid4())
        tasks.append(PlannedTask(
            id=models_id,
            title="Create SQLAlchemy data models",
            description=f"""Define SQLAlchemy ORM models in app/models/ and Pydantic schemas in app/schemas/.

{db_requirement_warning}

Each model MUST:
1. Inherit from Base (SQLAlchemy declarative base)
2. Have proper table name and columns
3. Be exported in app/models/__init__.py
""",
            worker_role="coder",
            priority=9,
            dependencies=[setup_id, research_id],
            estimated_duration="medium",
            metadata={"database_required": True, "expected_artifacts": ["app/models/"]}
        ))

        db_id = str(uuid.uuid4())
        tasks.append(PlannedTask(
            id=db_id,
            title="Implement database layer",
            description="""Set up PostgreSQL database connection and session management.

Create:
1. app/db/session.py - Database engine and session factory
2. app/db/base.py - SQLAlchemy Base class
3. get_db() dependency function for FastAPI

The database URL should come from environment variable DATABASE_URL.
""",
            worker_role="coder",
            priority=8,
            dependencies=[models_id],
            estimated_duration="medium",
            metadata={"database_required": True}
        ))

        endpoints_id = str(uuid.uuid4())
        tasks.append(PlannedTask(
            id=endpoints_id,
            title="Implement API endpoints",
            description=f"""Create all required REST endpoints with validation.

{db_requirement_warning}

EVERY endpoint that creates, reads, updates, or deletes data MUST:
1. Have `db: Session = Depends(get_db)` in its signature
2. Use the SQLAlchemy models from app/models/
3. Use session.add(), session.commit(), session.query() for data operations
""",
            worker_role="coder",
            priority=7,
            dependencies=[db_id],
            estimated_duration="long",
            metadata={"database_required": True}
        ))

        tasks.append(PlannedTask(
            id=str(uuid.uuid4()),
            title="Add authentication",
            description="Implement JWT or OAuth authentication",
            worker_role="coder",
            priority=6,
            dependencies=[endpoints_id],
            estimated_duration="medium"
        ))

        tasks.append(PlannedTask(
            id=str(uuid.uuid4()),
            title="Add API documentation",
            description="Configure OpenAPI docs and add descriptions",
            worker_role="coder",
            priority=4,
            dependencies=[endpoints_id],
            estimated_duration="short"
        ))

        return tasks

    def _dashboard_tasks(self, parsed: Dict) -> List[PlannedTask]:
        """Tasks for a dashboard project."""
        tasks = []

        setup_id = str(uuid.uuid4())
        tasks.append(PlannedTask(
            id=setup_id,
            title="Dashboard project setup",
            description="Initialize React project with charting libraries",
            worker_role="coder",
            priority=10,
            estimated_duration="short"
        ))

        tasks.append(PlannedTask(
            id=str(uuid.uuid4()),
            title="Create layout components",
            description="Build sidebar, header, and main content area",
            worker_role="coder",
            priority=9,
            dependencies=[setup_id],
            estimated_duration="medium"
        ))

        tasks.append(PlannedTask(
            id=str(uuid.uuid4()),
            title="Implement data fetching",
            description="Create API client and data hooks",
            worker_role="coder",
            priority=8,
            dependencies=[setup_id],
            estimated_duration="medium"
        ))

        tasks.append(PlannedTask(
            id=str(uuid.uuid4()),
            title="Build chart components",
            description="Create reusable chart components with various types",
            worker_role="coder",
            priority=7,
            dependencies=[setup_id],
            estimated_duration="long"
        ))

        tasks.append(PlannedTask(
            id=str(uuid.uuid4()),
            title="Add data tables",
            description="Implement sortable, filterable data tables",
            worker_role="coder",
            priority=6,
            dependencies=[setup_id],
            estimated_duration="medium"
        ))

        return tasks

    def _mobile_tasks(self, parsed: Dict) -> List[PlannedTask]:
        """Tasks for a mobile app project."""
        tasks = []

        setup_id = str(uuid.uuid4())
        tasks.append(PlannedTask(
            id=setup_id,
            title="Initialize Expo project",
            description="Set up Expo with TypeScript and required dependencies",
            worker_role="coder",
            priority=10,
            estimated_duration="short"
        ))

        tasks.append(PlannedTask(
            id=str(uuid.uuid4()),
            title="Set up navigation",
            description="Configure React Navigation with screens",
            worker_role="coder",
            priority=9,
            dependencies=[setup_id],
            estimated_duration="medium"
        ))

        tasks.append(PlannedTask(
            id=str(uuid.uuid4()),
            title="Create core screens",
            description="Build main app screens with layouts",
            worker_role="coder",
            priority=8,
            dependencies=[setup_id],
            estimated_duration="long"
        ))

        tasks.append(PlannedTask(
            id=str(uuid.uuid4()),
            title="Implement state management",
            description="Set up Zustand or Redux for app state",
            worker_role="coder",
            priority=7,
            dependencies=[setup_id],
            estimated_duration="medium"
        ))

        return tasks

    def _cli_tasks(self, parsed: Dict) -> List[PlannedTask]:
        """Tasks for a CLI tool project."""
        tasks = []

        setup_id = str(uuid.uuid4())
        tasks.append(PlannedTask(
            id=setup_id,
            title="CLI project setup",
            description="Initialize Python project with Click framework",
            worker_role="coder",
            priority=10,
            estimated_duration="short"
        ))

        tasks.append(PlannedTask(
            id=str(uuid.uuid4()),
            title="Define CLI commands",
            description="Create command structure and arguments",
            worker_role="coder",
            priority=9,
            dependencies=[setup_id],
            estimated_duration="medium"
        ))

        tasks.append(PlannedTask(
            id=str(uuid.uuid4()),
            title="Implement core logic",
            description="Build the main functionality for each command",
            worker_role="coder",
            priority=8,
            dependencies=[setup_id],
            estimated_duration="long"
        ))

        tasks.append(PlannedTask(
            id=str(uuid.uuid4()),
            title="Add output formatting",
            description="Implement colored output and progress bars",
            worker_role="coder",
            priority=6,
            dependencies=[setup_id],
            estimated_duration="short"
        ))

        return tasks

    def _website_tasks(self, parsed: Dict) -> List[PlannedTask]:
        """Tasks for a website project."""
        tasks = []

        setup_id = str(uuid.uuid4())
        tasks.append(PlannedTask(
            id=setup_id,
            title="Website project setup",
            description="Initialize Next.js project with Tailwind CSS",
            worker_role="coder",
            priority=10,
            estimated_duration="short"
        ))

        tasks.append(PlannedTask(
            id=str(uuid.uuid4()),
            title="Create page layouts",
            description="Build header, footer, and page templates",
            worker_role="coder",
            priority=9,
            dependencies=[setup_id],
            estimated_duration="medium"
        ))

        tasks.append(PlannedTask(
            id=str(uuid.uuid4()),
            title="Build page components",
            description="Create hero, features, testimonials sections",
            worker_role="coder",
            priority=8,
            dependencies=[setup_id],
            estimated_duration="medium"
        ))

        tasks.append(PlannedTask(
            id=str(uuid.uuid4()),
            title="Add responsive design",
            description="Ensure mobile and tablet responsiveness",
            worker_role="coder",
            priority=7,
            dependencies=[setup_id],
            estimated_duration="medium"
        ))

        tasks.append(PlannedTask(
            id=str(uuid.uuid4()),
            title="Optimize for SEO",
            description="Add meta tags, sitemap, and structured data",
            worker_role="coder",
            priority=5,
            dependencies=[setup_id],
            estimated_duration="short"
        ))

        return tasks

    def _ecommerce_tasks(self, parsed: Dict) -> List[PlannedTask]:
        """Tasks for an e-commerce project."""
        tasks = []

        setup_id = str(uuid.uuid4())
        tasks.append(PlannedTask(
            id=setup_id,
            title="E-commerce project setup",
            description="Initialize Next.js with Stripe and database",
            worker_role="coder",
            priority=10,
            estimated_duration="medium"
        ))

        tasks.append(PlannedTask(
            id=str(uuid.uuid4()),
            title="Create product catalog",
            description="Build product listing and detail pages",
            worker_role="coder",
            priority=9,
            dependencies=[setup_id],
            estimated_duration="long"
        ))

        tasks.append(PlannedTask(
            id=str(uuid.uuid4()),
            title="Implement shopping cart",
            description="Create cart functionality with persistence",
            worker_role="coder",
            priority=8,
            dependencies=[setup_id],
            estimated_duration="medium"
        ))

        tasks.append(PlannedTask(
            id=str(uuid.uuid4()),
            title="Build checkout flow",
            description="Integrate Stripe checkout and payment",
            worker_role="coder",
            priority=7,
            dependencies=[setup_id],
            estimated_duration="long"
        ))

        return tasks

    def _scraper_tasks(self, parsed: Dict) -> List[PlannedTask]:
        """Tasks for a web scraper project."""
        tasks = []

        research_id = str(uuid.uuid4())
        tasks.append(PlannedTask(
            id=research_id,
            title="Analyze target website",
            description="Research site structure, anti-bot measures, data format",
            worker_role="researcher",
            priority=10,
            estimated_duration="medium"
        ))

        setup_id = str(uuid.uuid4())
        tasks.append(PlannedTask(
            id=setup_id,
            title="Scraper project setup",
            description="Initialize Python project with Playwright/requests",
            worker_role="coder",
            priority=9,
            estimated_duration="short"
        ))

        tasks.append(PlannedTask(
            id=str(uuid.uuid4()),
            title="Implement scraping logic",
            description="Build page navigation and data extraction",
            worker_role="coder",
            priority=8,
            dependencies=[setup_id, research_id],
            estimated_duration="long"
        ))

        tasks.append(PlannedTask(
            id=str(uuid.uuid4()),
            title="Add data processing",
            description="Clean and structure scraped data",
            worker_role="coder",
            priority=7,
            dependencies=[setup_id],
            estimated_duration="medium"
        ))

        tasks.append(PlannedTask(
            id=str(uuid.uuid4()),
            title="Handle rate limiting",
            description="Add delays, retries, and proxy rotation",
            worker_role="coder",
            priority=6,
            dependencies=[setup_id],
            estimated_duration="short"
        ))

        return tasks

    def _custom_tasks(self, parsed: Dict) -> List[PlannedTask]:
        """Tasks for a custom project type."""
        tasks = []

        research_id = str(uuid.uuid4())
        tasks.append(PlannedTask(
            id=research_id,
            title="Research and planning",
            description="Analyze requirements and plan implementation approach",
            worker_role="researcher",
            priority=10,
            estimated_duration="medium"
        ))

        setup_id = str(uuid.uuid4())
        tasks.append(PlannedTask(
            id=setup_id,
            title="Project setup",
            description="Initialize project with required dependencies",
            worker_role="coder",
            priority=9,
            dependencies=[research_id],
            estimated_duration="short"
        ))

        tasks.append(PlannedTask(
            id=str(uuid.uuid4()),
            title="Core implementation",
            description="Implement main functionality based on requirements",
            worker_role="coder",
            priority=8,
            dependencies=[setup_id],
            estimated_duration="long"
        ))

        return tasks

    # =========================================================================
    # FEATURE & TESTING TASKS
    # =========================================================================

    def _plan_feature_tasks(
        self,
        features: List[Dict],
        technologies: List[str]
    ) -> List[PlannedTask]:
        """Create tasks for specific features."""
        tasks = []

        for i, feature in enumerate(features[:10]):  # Limit to 10 features
            desc = feature.get("description", "")
            priority = {"high": 7, "medium": 5, "low": 3}.get(
                feature.get("priority", "medium"), 5
            )

            tasks.append(PlannedTask(
                id=str(uuid.uuid4()),
                title=f"Implement feature: {desc[:50]}",
                description=desc,
                worker_role="coder",
                priority=priority,
                estimated_duration="medium"
            ))

        return tasks

    # Web-related project types that should ALWAYS have E2E tests
    WEB_PROJECT_TYPES = {
        "react", "nextjs", "vue", "angular", "svelte", "solid",
        "web", "frontend", "dashboard", "spa", "pwa",
        "todo", "app", "webapp", "website", "landing",
        "admin", "portal", "ui", "interface"
    }

    # Web-related technologies that indicate E2E tests are needed
    WEB_TECHNOLOGIES = {
        "react", "vue", "angular", "svelte", "solid", "next", "nuxt",
        "vite", "webpack", "parcel", "rollup",
        "tailwind", "css", "sass", "scss", "styled-components",
        "html", "dom", "browser", "web"
    }

    def _is_web_project(self, project_type: str, technologies: List[str]) -> bool:
        """Determine if this is a web project that needs E2E tests."""
        # Check project type
        project_type_lower = project_type.lower() if project_type else ""
        for web_type in self.WEB_PROJECT_TYPES:
            if web_type in project_type_lower:
                return True

        # Check technologies
        techs_lower = [t.lower() for t in (technologies or [])]
        for tech in techs_lower:
            for web_tech in self.WEB_TECHNOLOGIES:
                if web_tech in tech:
                    return True

        return False

    def _plan_testing_tasks(
        self,
        implementation_tasks: List[PlannedTask],
        complexity: str,
        project_type: str = "",
        technologies: List[str] = None
    ) -> List[PlannedTask]:
        """Create testing tasks. ALL web projects get E2E tests with Playwright."""
        tasks = []
        technologies = technologies or []

        coder_task_ids = [t.id for t in implementation_tasks if t.worker_role == "coder"]

        # Check if this is a web project
        is_web = self._is_web_project(project_type, technologies)

        # Unit tests (always)
        tasks.append(PlannedTask(
            id=str(uuid.uuid4()),
            title="Write unit tests",
            description="Create unit tests for all core functions",
            worker_role="tester",
            priority=5,
            dependencies=coder_task_ids[:3],  # Depend on first few coding tasks
            estimated_duration="medium"
        ))

        # Integration tests for medium+ complexity
        if complexity in ("medium", "high", "very_high"):
            tasks.append(PlannedTask(
                id=str(uuid.uuid4()),
                title="Write integration tests",
                description="Create integration tests for component interactions",
                worker_role="tester",
                priority=4,
                dependencies=coder_task_ids,
                estimated_duration="medium"
            ))

        # =================================================================
        # E2E TESTS WITH PLAYWRIGHT - FOR ALL WEB PROJECTS
        # =================================================================
        # Any project that looks like web (React, Vue, dashboard, app, etc.)
        # gets full Playwright E2E testing regardless of complexity
        if is_web:
            # First, setup Playwright configuration
            playwright_setup_id = str(uuid.uuid4())
            tasks.append(PlannedTask(
                id=playwright_setup_id,
                title="Setup Playwright for E2E testing",
                description="""Setup Playwright E2E testing infrastructure:
1. Install @playwright/test as dev dependency: npm install -D @playwright/test
2. Create playwright.config.ts with proper configuration:
   - Set baseURL to the dev server URL
   - Configure browser(s) to test (chromium at minimum)
   - Set up screenshot on failure
   - Configure test directory
3. Create tests/ or e2e/ directory structure
4. Add scripts to package.json:
   - "test:e2e": "playwright test"
   - "test:e2e:ui": "playwright test --ui"
5. Run: npx playwright install chromium

CRITICAL: The playwright.config.ts file MUST be created at the project root.
This is REQUIRED for the validation pipeline to run E2E tests.""",
                worker_role="tester",
                priority=4,  # Higher priority - do this early
                dependencies=coder_task_ids[:1],  # Only depends on first setup task
                estimated_duration="short"
            ))

            # Then write comprehensive E2E tests
            tasks.append(PlannedTask(
                id=str(uuid.uuid4()),
                title="Write E2E tests with Playwright",
                description="""Create comprehensive end-to-end tests using Playwright:

1. TEST ALL USER FLOWS:
   - Main functionality (CRUD operations if applicable)
   - Navigation between pages/views
   - Form submissions and validations
   - Error states and edge cases

2. VISUAL TESTING:
   - Take screenshots at key states
   - Test responsive design (mobile, tablet, desktop)
   - Test dark mode if applicable

3. INTERACTION TESTING:
   - Button clicks and form inputs
   - Keyboard navigation
   - Hover states and tooltips

4. RUN AND VERIFY:
   - Run: npx playwright test
   - All tests must pass
   - Screenshots saved in test-results/

Tests should be in tests/ or e2e/ directory with .spec.ts extension.""",
                worker_role="tester",
                priority=3,
                dependencies=[playwright_setup_id],
                estimated_duration="medium"
            ))

            # Browser-based visual verification task
            tasks.append(PlannedTask(
                id=str(uuid.uuid4()),
                title="Run browser verification and take screenshots",
                description="""Use Playwright to visually verify the application:

1. Start the dev server
2. Open the application in a browser
3. Take screenshots of:
   - Main page/dashboard
   - All major features
   - Mobile responsive view
   - Any error states
4. Save screenshots to /output/screenshots/
5. Verify all interactive elements work correctly

This task uses the browser worker for visual verification.""",
                worker_role="tester",  # Can also be browser-headless role
                priority=2,
                dependencies=[t.id for t in tasks if "E2E" in t.title],
                estimated_duration="short"
            ))

            logger.info(f"Added Playwright E2E testing tasks for web project: {project_type}")

        return tasks

    # =========================================================================
    # TEMPLATE & SKILL INTEGRATION
    # =========================================================================

    async def _find_matching_templates(
        self,
        project_type: str,
        technologies: List[str],
        description: str
    ) -> List[Dict]:
        """Find templates matching the project requirements."""
        if not self.template_extractor:
            return []

        try:
            # Get all templates
            templates = await self.template_extractor.list_templates()

            matches = []
            for template in templates:
                score = 0

                # Match project type
                if project_type in template.get("name", "").lower():
                    score += 3

                # Match technologies
                template_techs = template.get("technologies", [])
                for tech in technologies:
                    if tech.lower() in [t.lower() for t in template_techs]:
                        score += 2

                # Match description keywords
                desc_lower = description.lower()
                if any(kw in desc_lower for kw in template.get("keywords", [])):
                    score += 1

                if score > 0:
                    matches.append((template, score))

            # Sort by score
            matches.sort(key=lambda x: x[1], reverse=True)
            return [m[0] for m in matches[:3]]

        except Exception as e:
            logger.warning(f"Error finding templates: {e}")
            return []

    async def _tasks_from_template(
        self,
        template: Dict,
        parsed_objective: Dict
    ) -> List[PlannedTask]:
        """Generate tasks from a template structure."""
        tasks = []

        # Use template's task structure if available
        template_tasks = template.get("tasks", [])

        for i, t_task in enumerate(template_tasks):
            task_id = str(uuid.uuid4())
            tasks.append(PlannedTask(
                id=task_id,
                title=t_task.get("title", f"Task {i+1}"),
                description=t_task.get("description", ""),
                worker_role=t_task.get("worker_role", "coder"),
                priority=t_task.get("priority", 10 - i),
                dependencies=[],  # Will be resolved later
                estimated_duration=t_task.get("duration", "medium"),
                validation_required=True
            ))

        return tasks

    def set_skills_engine(self, skills_engine) -> None:
        """Set the skills engine for task planning."""
        self.skills_engine = skills_engine
        logger.info("Skills engine connected to task planner")

    def set_template_extractor(self, template_extractor) -> None:
        """Set the template extractor for task planning."""
        self.template_extractor = template_extractor
        logger.info("Template extractor connected to task planner")

    def set_design_system(self, design_system) -> None:
        """Set the design system for task planning."""
        self.design_system = design_system
        logger.info("Design system connected to task planner")
