# =============================================================================
# CLOPUS v3 Orchestrator Main Entry Point
# =============================================================================
"""
Main orchestrator that coordinates all CLOPUS operations.
"""

import asyncio
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import logging

from .config import get_settings, Settings
from .memory_client import MemoryClient
from .worker_pool import WorkerPool
from .task_planner import TaskPlanner
from .objective_parser import ObjectiveParser
from .confidence_engine import ConfidenceEngine
from .status_reporter import StatusReporter
from .user_interaction import UserInteractionHandler
from .github_sync import GitHubSync
from .service_manager import ServiceManager
from .skills_engine import SkillsEngine
from .mcp_generator import MCPGenerator
from .template_extractor import TemplateExtractor
from validation.pipeline import ValidationPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("clopus.orchestrator")


class Orchestrator:
    """Main CLOPUS orchestrator."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.running = False
        self._shutdown_event = asyncio.Event()

        # Components (initialized in start())
        self.memory: Optional[MemoryClient] = None
        self.worker_pool: Optional[WorkerPool] = None
        self.task_planner: Optional[TaskPlanner] = None
        self.objective_parser: Optional[ObjectiveParser] = None
        self.confidence_engine: Optional[ConfidenceEngine] = None
        self.status_reporter: Optional[StatusReporter] = None
        self.user_interaction: Optional[UserInteractionHandler] = None
        self.github_sync: Optional[GitHubSync] = None
        self.service_manager: Optional[ServiceManager] = None

        # Self-generating ecosystem components
        self.skills_engine: Optional[SkillsEngine] = None
        self.mcp_generator: Optional[MCPGenerator] = None
        self.template_extractor: Optional[TemplateExtractor] = None
        self.validation_pipeline: Optional[ValidationPipeline] = None

    async def initialize(self) -> None:
        """Initialize all components."""
        logger.info("Initializing CLOPUS orchestrator...")

        # Initialize memory
        self.memory = MemoryClient(
            sqlite_path=self.settings.memory_config.sqlite_path,
            chromadb_host=self.settings.memory_config.chromadb_host,
            chromadb_port=self.settings.memory_config.chromadb_port
        )
        await self.memory.initialize()
        logger.info("Memory system initialized")

        # Initialize confidence engine
        self.confidence_engine = ConfidenceEngine(
            self.memory,
            self.settings.confidence_config
        )
        logger.info("Confidence engine initialized")

        # Initialize objective parser
        self.objective_parser = ObjectiveParser(self.memory, self.confidence_engine)
        logger.info("Objective parser initialized")

        # Initialize task planner
        self.task_planner = TaskPlanner(
            self.memory,
            self.confidence_engine,
            self.objective_parser
        )
        logger.info("Task planner initialized")

        # Initialize worker pool
        self.worker_pool = WorkerPool(
            self.memory,
            self.settings.worker_config,
            self.settings.ipc_path
        )
        await self.worker_pool.initialize()
        logger.info("Worker pool initialized")

        # Initialize status reporter
        self.status_reporter = StatusReporter(
            self.memory,
            self.worker_pool
        )
        logger.info("Status reporter initialized")

        # Initialize user interaction handler
        self.user_interaction = UserInteractionHandler(
            self.memory,
            self.confidence_engine,
            Path(self.settings.interface_config.questions_dir),
            Path(self.settings.interface_config.answers_dir)
        )
        logger.info("User interaction handler initialized")

        # Initialize GitHub sync
        self.github_sync = GitHubSync(
            self.settings.github_config,
            Path(self.settings.skills_path),
            Path(self.settings.templates_path),
            Path(self.settings.mcp_servers_path)
        )
        logger.info("GitHub sync initialized")

        # Initialize service manager
        self.service_manager = ServiceManager(self.settings.services_config)
        logger.info("Service manager initialized")

        # Initialize self-generating ecosystem components
        self.skills_engine = SkillsEngine(
            self.memory,
            self.github_sync,
            self.settings.skills_path
        )
        await self.skills_engine.discover_skills()
        logger.info("Skills engine initialized")

        self.mcp_generator = MCPGenerator(
            self.memory,
            self.github_sync,
            self.worker_pool,
            self.settings.mcp_servers_path
        )
        logger.info("MCP generator initialized")

        self.template_extractor = TemplateExtractor(
            self.memory,
            self.github_sync,
            self.settings.templates_path
        )
        logger.info("Template extractor initialized")

        self.validation_pipeline = ValidationPipeline(
            self.memory,
            self.settings.validation_config,
            self.worker_pool
        )
        logger.info("Validation pipeline initialized")

        logger.info("CLOPUS orchestrator fully initialized")

    async def start(self) -> None:
        """Start the orchestrator."""
        await self.initialize()
        self.running = True

        logger.info("Starting CLOPUS orchestrator...")
        await self.memory.log_activity(
            source="orchestrator",
            action="started",
            details={"version": "3.0.0"}
        )

        # Start background tasks
        tasks = [
            asyncio.create_task(self._main_loop()),
            asyncio.create_task(self._objective_watcher()),
            asyncio.create_task(self._answer_watcher()),
            asyncio.create_task(self._worker_monitor()),
            asyncio.create_task(self._status_loop()),
        ]

        # Wait for shutdown
        await self._shutdown_event.wait()

        # Cancel all tasks
        for task in tasks:
            task.cancel()

        await self.shutdown()

    async def shutdown(self) -> None:
        """Shutdown the orchestrator."""
        logger.info("Shutting down CLOPUS orchestrator...")
        self.running = False

        if self.memory:
            await self.memory.log_activity(
                source="orchestrator",
                action="shutdown"
            )
            await self.memory.close()

        if self.worker_pool:
            await self.worker_pool.shutdown()

        logger.info("CLOPUS orchestrator shutdown complete")

    def request_shutdown(self) -> None:
        """Request graceful shutdown."""
        self._shutdown_event.set()

    # =========================================================================
    # MAIN LOOPS
    # =========================================================================

    async def _main_loop(self) -> None:
        """Main orchestration loop."""
        logger.info("Main loop started")

        while self.running:
            try:
                # Get next objective to process
                objective = await self.memory.get_next_objective()

                if objective:
                    await self._process_objective(objective)
                else:
                    # Check for assignable tasks
                    await self._assign_pending_tasks()

                # Small delay to prevent tight loop
                await asyncio.sleep(0.5)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                await asyncio.sleep(5)

    async def _process_objective(self, objective) -> None:
        """Process a single objective."""
        logger.info(f"Processing objective: {objective.content[:100]}...")

        try:
            # Mark as in progress
            await self.memory.start_objective(objective.id)

            # Check for clarifications from previous questions
            clarifications = []
            if objective.metadata and "clarifications" in objective.metadata:
                clarifications = objective.metadata["clarifications"]
                logger.info(f"Found {len(clarifications)} clarification(s) for objective")

            # Build enhanced content with clarifications
            content = objective.content
            if clarifications:
                clarification_text = "\n\n---\nUser Clarifications:\n"
                for c in clarifications:
                    clarification_text += f"- {c['answer']}\n"
                content += clarification_text

            # Parse objective (with clarifications if any)
            parsed = await self.objective_parser.parse(content)

            # Check confidence - higher if we have clarifications
            confidence = await self.confidence_engine.calculate(
                "objective_clarity",
                {
                    "objective": content,
                    "parsed": parsed,
                    "has_clarifications": len(clarifications) > 0
                }
            )

            # Boost confidence if we have clarifications
            if clarifications:
                confidence = min(1.0, confidence + 0.3)
                logger.info(f"Boosted confidence to {confidence} due to clarifications")

            if confidence < self.settings.confidence_config.threshold:
                # Ask for clarification
                await self.user_interaction.ask_clarification(
                    f"I need clarification on this objective: {objective.content}\n\nSpecifically: {parsed.get('unclear_points', 'general scope')}",
                    objective_id=objective.id,
                    confidence_score=confidence
                )
                return

            # Plan tasks
            tasks = await self.task_planner.plan(objective.id, parsed)
            logger.info(f"Created {len(tasks)} tasks for objective")

            # Create tasks in memory
            await self.memory.create_tasks(objective.id, [
                {
                    "title": t["title"],
                    "description": t.get("description"),
                    "priority": t.get("priority", 5),
                    "dependencies": t.get("dependencies", []),
                    "worker_role": t.get("worker_role")
                }
                for t in tasks
            ])

        except Exception as e:
            logger.error(f"Error processing objective: {e}", exc_info=True)
            await self.memory.complete_objective(objective.id, success=False)

    async def _assign_pending_tasks(self) -> None:
        """Assign pending tasks to available workers."""
        # Get assignable tasks
        tasks = await self.memory.get_assignable_tasks()

        for task in tasks:
            # Get idle worker for role
            worker = await self.memory.get_idle_worker(task.worker_role)

            if worker:
                # Assign task
                await self.memory.assign_task_to_worker(
                    task.id,
                    worker.id,
                    worker.role
                )

                # Dispatch to worker
                await self.worker_pool.dispatch_task(
                    worker.id,
                    task.id,
                    task.title,
                    task.description
                )

                logger.info(f"Assigned task '{task.title}' to worker {worker.id}")

    async def _objective_watcher(self) -> None:
        """Watch for new objectives from file system."""
        objectives_dir = Path(self.settings.interface_config.objectives_dir)
        objectives_dir.mkdir(parents=True, exist_ok=True)

        processed = set()

        while self.running:
            try:
                for file in objectives_dir.glob("*.md"):
                    if file.name not in processed:
                        content = file.read_text()
                        processed.add(file.name)

                        # Extract objective from markdown
                        lines = content.strip().split("\n")
                        objective_text = "\n".join(
                            line for line in lines
                            if not line.startswith("#") and not line.startswith("---")
                        ).strip()

                        if objective_text:
                            await self.memory.create_objective(objective_text)
                            logger.info(f"New objective from file: {file.name}")

                            # Archive file
                            archive_dir = objectives_dir / "processed"
                            archive_dir.mkdir(exist_ok=True)
                            file.rename(archive_dir / file.name)

                await asyncio.sleep(1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in objective watcher: {e}")
                await asyncio.sleep(5)

    async def _answer_watcher(self) -> None:
        """Watch for answers from file system."""
        answers_dir = Path(self.settings.interface_config.answers_dir)
        answers_dir.mkdir(parents=True, exist_ok=True)

        processed = set()

        while self.running:
            try:
                for file in answers_dir.glob("*.md"):
                    if file.name not in processed:
                        content = file.read_text()
                        processed.add(file.name)

                        # Extract answer
                        lines = content.strip().split("\n")
                        answer_text = "\n".join(
                            line for line in lines
                            if not line.startswith("#") and not line.startswith("---")
                        ).strip()

                        if answer_text:
                            question_id = file.stem
                            objective_id = await self.memory.answer(question_id, answer_text)
                            logger.info(f"Answer received for question: {question_id}")

                            if objective_id:
                                logger.info(f"Objective {objective_id} re-queued for processing with clarification")

                            # Remove answer file
                            file.unlink()

                await asyncio.sleep(1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in answer watcher: {e}")
                await asyncio.sleep(5)

    async def _worker_monitor(self) -> None:
        """Monitor worker health and task completion."""
        while self.running:
            try:
                # Check for completed tasks
                results = await self.worker_pool.collect_results()

                for worker_id, result in results.items():
                    task_id = result.get("task_id")
                    success = result.get("status") == "completed"

                    if task_id:
                        await self.memory.complete_task(
                            task_id,
                            worker_id,
                            success,
                            result.get("result"),
                            result.get("error")
                        )

                        # Get task details for validation
                        task = await self.memory.short_term.get_task(task_id)
                        if task:
                            # Run validation on completed coding tasks
                            if success and task.worker_role in ("coder", "tester"):
                                await self._run_validation(task)

                            # Check if objective is complete
                            objective_tasks = await self.memory.short_term.get_tasks_for_objective(
                                task.objective_id
                            )
                            all_complete = all(
                                t.status.value in ("completed", "failed")
                                for t in objective_tasks
                            )
                            if all_complete:
                                all_success = all(
                                    t.status.value == "completed"
                                    for t in objective_tasks
                                )
                                await self.memory.complete_objective(
                                    task.objective_id,
                                    success=all_success
                                )

                                # Extract template from successful projects
                                if all_success:
                                    await self._extract_template_if_applicable(task.objective_id)

                # Update worker heartbeats
                await self.worker_pool.check_heartbeats()

                await asyncio.sleep(0.5)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in worker monitor: {e}")
                await asyncio.sleep(5)

    async def _status_loop(self) -> None:
        """Continuous status reporting."""
        while self.running:
            try:
                status = await self.status_reporter.get_status()
                # Status is available via API or status file
                await self.status_reporter.write_status_file(status)
                await asyncio.sleep(2)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in status loop: {e}")
                await asyncio.sleep(5)

    # =========================================================================
    # VALIDATION & SELF-GENERATING ECOSYSTEM
    # =========================================================================

    async def _run_validation(self, task) -> None:
        """Run validation pipeline on completed task."""
        try:
            # Determine project path from task context
            project_path = "/workspace"  # Default

            # Try to extract path from task result or metadata
            if task.result and isinstance(task.result, str):
                # Look for path patterns in result
                import re
                path_match = re.search(r'/workspace/[\w\-/]+', task.result)
                if path_match:
                    project_path = path_match.group(0).rsplit('/', 1)[0]

            logger.info(f"Running validation on {project_path} for task {task.id}")

            # Run validation pipeline
            result = await self.validation_pipeline.validate(
                project_path=project_path,
                task_id=task.id
            )

            # Log validation result
            if result.passed:
                logger.info(f"Validation passed for task {task.id}: {result.summary}")
                await self.memory.log_activity(
                    source="validation",
                    action="passed",
                    details={"task_id": task.id, "summary": result.summary}
                )
            else:
                logger.warning(f"Validation failed for task {task.id}: {result.summary}")
                await self.memory.log_activity(
                    source="validation",
                    action="failed",
                    details={
                        "task_id": task.id,
                        "summary": result.summary,
                        "stages": [
                            {
                                "stage": s.stage.value if hasattr(s.stage, 'value') else str(s.stage),
                                "status": s.status.value if hasattr(s.status, 'value') else str(s.status)
                            }
                            for s in result.stages
                        ]
                    }
                )

                # Store learning about failure pattern
                await self.memory.long_term.store(
                    memory_type="learning",
                    content=f"Validation failure: {result.summary}",
                    metadata={
                        "type": "validation_failure",
                        "task_id": task.id,
                        "stages_failed": [
                            s.stage.value if hasattr(s.stage, 'value') else str(s.stage)
                            for s in result.stages
                            if (s.status.value if hasattr(s.status, 'value') else str(s.status)) == "failed"
                        ]
                    }
                )

        except Exception as e:
            logger.error(f"Error running validation: {e}")

    async def _extract_template_if_applicable(self, objective_id: str) -> None:
        """Extract a template from completed objective if applicable."""
        try:
            objective = await self.memory.short_term.get_objective(objective_id)
            if not objective:
                return

            # Check if this looks like a project creation task
            content_lower = objective.content.lower()
            is_project = any(
                keyword in content_lower
                for keyword in ["create", "build", "develop", "implement", "make"]
            )

            if not is_project:
                return

            # Determine project path (try to infer from objective)
            import re
            path_match = re.search(r'/workspace/([\w\-]+)', objective.content)
            if path_match:
                project_name = path_match.group(1)
                project_path = f"/workspace/{project_name}"
            else:
                # Try common project directories
                from pathlib import Path
                workspace = Path("/workspace")
                recent_dirs = sorted(
                    [d for d in workspace.iterdir() if d.is_dir()],
                    key=lambda x: x.stat().st_mtime,
                    reverse=True
                )
                if recent_dirs:
                    project_path = str(recent_dirs[0])
                    project_name = recent_dirs[0].name
                else:
                    return

            # Generate template name
            template_name = f"template-{project_name}"

            logger.info(f"Extracting template '{template_name}' from {project_path}")

            # Extract template
            result = await self.template_extractor.extract_template(
                project_path=project_path,
                template_name=template_name,
                description=f"Template extracted from: {objective.content[:100]}"
            )

            if result:
                logger.info(f"Template extracted successfully: {template_name}")
                await self.memory.log_activity(
                    source="template_extractor",
                    action="extracted",
                    details={"template_name": template_name, "source": project_path}
                )

                # Store as learning
                await self.memory.long_term.store(
                    memory_type="skill",
                    content=f"Template: {template_name} - Extracted from {project_path}",
                    metadata={
                        "type": "template",
                        "name": template_name,
                        "source": project_path
                    }
                )

        except Exception as e:
            logger.error(f"Error extracting template: {e}")

    async def _find_skill_for_task(self, task_description: str) -> Optional[dict]:
        """Find a matching skill for a task."""
        if not self.skills_engine:
            return None

        try:
            skill = await self.skills_engine.find_skill_for_task(task_description)
            if skill:
                logger.info(f"Found skill '{skill.get('name')}' for task")
            return skill
        except Exception as e:
            logger.error(f"Error finding skill: {e}")
            return None


async def main():
    """Main entry point."""
    orchestrator = Orchestrator()

    # Handle signals
    loop = asyncio.get_event_loop()

    def signal_handler():
        orchestrator.request_shutdown()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    await orchestrator.start()


if __name__ == "__main__":
    asyncio.run(main())
