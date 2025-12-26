# =============================================================================
# CLOPUS v3 Task Planner
# =============================================================================
"""
Breaks down objectives into executable tasks with dependencies.
Assigns appropriate worker roles and priorities.
"""

import asyncio
import uuid
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import logging

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


class TaskPlanner:
    """Plan and decompose objectives into tasks."""

    def __init__(self, memory_client, confidence_engine, objective_parser):
        self.memory = memory_client
        self.confidence = confidence_engine
        self.parser = objective_parser

        # Skills engine and template extractor (set by orchestrator)
        self.skills_engine = None
        self.template_extractor = None

        # Standard task patterns for common project types
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
        }

    async def plan(self, objective_id: str, parsed_objective: Dict) -> List[Dict]:
        """Create a task plan for an objective."""
        logger.info(f"Planning tasks for objective: {objective_id}")

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

        # Add testing tasks
        test_tasks = self._plan_testing_tasks(base_tasks, complexity)
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

        # Set proper dependencies
        tasks_with_deps = self._resolve_dependencies(base_tasks)

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
            "validation_required": task.validation_required
        }

    def _resolve_dependencies(self, tasks: List[PlannedTask]) -> List[PlannedTask]:
        """Ensure dependencies are properly ordered."""
        # Build dependency graph
        task_map = {t.id: t for t in tasks}

        # Assign priorities based on dependencies
        for task in tasks:
            if not task.dependencies:
                task.priority = max(task.priority, 8)  # High priority for no deps
            else:
                # Priority based on dependency chain depth
                depth = self._get_dependency_depth(task, task_map)
                task.priority = max(1, 10 - depth)

        return sorted(tasks, key=lambda t: (-t.priority, len(t.dependencies)))

    def _get_dependency_depth(self, task: PlannedTask, task_map: Dict) -> int:
        """Get the depth of dependencies."""
        if not task.dependencies:
            return 0

        max_depth = 0
        for dep_id in task.dependencies:
            if dep_id in task_map:
                depth = self._get_dependency_depth(task_map[dep_id], task_map)
                max_depth = max(max_depth, depth + 1)

        return max_depth

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

        setup_id = str(uuid.uuid4())
        tasks.append(PlannedTask(
            id=setup_id,
            title="API project setup",
            description="Initialize FastAPI project with dependencies and configuration",
            worker_role="coder",
            priority=10,
            estimated_duration="short"
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
            title="Create data models",
            description="Define Pydantic models and database schemas",
            worker_role="coder",
            priority=9,
            dependencies=[setup_id, research_id],
            estimated_duration="medium"
        ))

        db_id = str(uuid.uuid4())
        tasks.append(PlannedTask(
            id=db_id,
            title="Implement database layer",
            description="Set up database connection and CRUD operations",
            worker_role="coder",
            priority=8,
            dependencies=[models_id],
            estimated_duration="medium"
        ))

        endpoints_id = str(uuid.uuid4())
        tasks.append(PlannedTask(
            id=endpoints_id,
            title="Implement API endpoints",
            description="Create all required REST endpoints with validation",
            worker_role="coder",
            priority=7,
            dependencies=[db_id],
            estimated_duration="long"
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

    def _plan_testing_tasks(
        self,
        implementation_tasks: List[PlannedTask],
        complexity: str
    ) -> List[PlannedTask]:
        """Create testing tasks."""
        tasks = []

        coder_task_ids = [t.id for t in implementation_tasks if t.worker_role == "coder"]

        # Unit tests
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

        # E2E tests for high+ complexity
        if complexity in ("high", "very_high"):
            tasks.append(PlannedTask(
                id=str(uuid.uuid4()),
                title="Write E2E tests",
                description="Create end-to-end tests with Playwright",
                worker_role="tester",
                priority=3,
                dependencies=coder_task_ids,
                estimated_duration="long"
            ))

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
