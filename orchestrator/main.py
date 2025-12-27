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
from .skills_engine import SkillsEngine
from .mcp_generator import MCPGenerator
from .template_extractor import TemplateExtractor
from .project_setup import ProjectSetup
from .service_manager import ServiceManager
from .capability_installer import CapabilityInstaller
from .knowledge_base import KnowledgeBase
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
        self.project_setup: Optional[ProjectSetup] = None

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
        self.service_manager = ServiceManager("/app/docker-compose.yml")
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

        self.project_setup = ProjectSetup("/workspace")
        logger.info("Project setup initialized")

        self.capability_installer = CapabilityInstaller(self.worker_pool)
        logger.info("Capability installer initialized")

        self.knowledge_base = KnowledgeBase(self.memory, "/app/knowledge")
        logger.info("Knowledge base initialized")

        # =====================================================================
        # CONNECT COMPONENTS FOR INTEGRATION
        # =====================================================================
        # Connect skills engine to task planner for skill-aware planning
        self.task_planner.set_skills_engine(self.skills_engine)
        self.task_planner.set_template_extractor(self.template_extractor)

        # Connect skills engine to worker pool for skill-enhanced prompts
        self.worker_pool.set_skills_engine(self.skills_engine)

        logger.info("Component integrations configured")
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

            # =====================================================================
            # CREATE PROJECT WITH CLAUDE.md
            # =====================================================================
            # Determine project path from parsed objective
            project_name = parsed.get("project_name") or f"project-{objective.id[:8]}"
            project_path = f"/workspace/{project_name}"
            project_type = parsed.get("project_type")

            # Create CLAUDE.md for the project
            try:
                claude_md_path = await self.project_setup.setup_project(
                    project_path=project_path,
                    objective_content=content,
                    project_type=project_type
                )
                logger.info(f"Created CLAUDE.md at {claude_md_path}")

                # Store project info in memory for workers to use
                await self.memory.log_activity(
                    source="project_setup",
                    action="created",
                    details={
                        "objective_id": objective.id,
                        "project_path": project_path,
                        "claude_md": str(claude_md_path)
                    }
                )
            except Exception as e:
                logger.warning(f"Could not create CLAUDE.md: {e}")

            # =====================================================================
            # AUTO-PROVISION REQUIRED SERVICES (Tier 2)
            # =====================================================================
            try:
                service_needs = await self.service_manager.analyze_project_needs(
                    project_path=project_path,
                    parsed_objective=parsed
                )

                if service_needs.get("databases") or service_needs.get("queues"):
                    logger.info(f"Project needs services: {service_needs}")
                    provision_results = await self.service_manager.provision_services(service_needs)

                    for service, success in provision_results.items():
                        if success:
                            logger.info(f"Provisioned service: {service}")
                        else:
                            logger.warning(f"Failed to provision service: {service}")

                if service_needs.get("missing_credentials"):
                    # Ask user for missing credentials
                    await self.user_interaction.ask_clarification(
                        f"Missing credentials for external services: {', '.join(service_needs['missing_credentials'])}",
                        objective_id=objective.id,
                        confidence_score=0.3
                    )
            except Exception as e:
                logger.warning(f"Error analyzing service needs: {e}")

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

                # =====================================================================
                # GET RELEVANT SKILLS AND MEMORY CONTEXT
                # =====================================================================
                relevant_skills = []
                memory_context = None

                # Find relevant skills for the task
                if self.skills_engine:
                    skill = await self._find_skill_for_task(task.title + " " + (task.description or ""))
                    if skill:
                        relevant_skills.append(skill)

                # Get relevant memory context
                try:
                    memory_context = await self.memory.get_relevant_context(
                        task.title + " " + (task.description or "")
                    )
                except Exception:
                    pass

                # Dispatch to worker with context
                await self.worker_pool.dispatch_task(
                    worker.id,
                    task.id,
                    task.title,
                    task.description,
                    relevant_skills=relevant_skills if relevant_skills else None,
                    memory_context=memory_context
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
                        # Get task details for validation BEFORE marking complete
                        task = await self.memory.short_term.get_task(task_id)

                        # =====================================================================
                        # MANDATORY VALIDATION - Tasks FAIL if validation fails
                        # =====================================================================
                        validation_passed = True
                        if task and success and task.worker_role in ("coder", "tester", "debugger"):
                            validation_passed = await self._run_validation(task)

                            if not validation_passed:
                                # OVERRIDE success - validation failure means task failure
                                success = False
                                logger.error(
                                    f"Task {task_id} marked as FAILED due to validation failure"
                                )

                        await self.memory.complete_task(
                            task_id,
                            worker_id,
                            success,
                            result.get("result"),
                            result.get("error") or ("Validation failed" if not validation_passed else None)
                        )

                        if task:
                            # =============================================================
                            # RECORD OUTCOME FOR LEARNING (Confidence Engine)
                            # =============================================================
                            try:
                                await self.confidence_engine.record_task_outcome(
                                    task_id=task.id,
                                    task_type=task.worker_role,
                                    success=success,
                                    validation_passed=validation_passed,
                                    error=result.get("error")
                                )
                            except Exception as e:
                                logger.warning(f"Error recording task outcome: {e}")

                            # =============================================================
                            # LEARN FROM OUTCOME (Knowledge Base)
                            # =============================================================
                            try:
                                if success and validation_passed:
                                    # Learn from success
                                    await self.knowledge_base.learn_from_task_success(
                                        task_title=task.title,
                                        task_description=task.description or "",
                                        approach=result.get("result", "")[:1000]
                                    )
                                else:
                                    # Learn from failure
                                    await self.knowledge_base.learn_from_task_failure(
                                        task_title=task.title,
                                        task_description=task.description or "",
                                        error=result.get("error", "Unknown error"),
                                        validation_failures=None  # Could extract from validation result
                                    )
                            except Exception as e:
                                logger.warning(f"Error learning from outcome: {e}")

                            # =============================================================
                            # EXTRACT SKILL FROM SUCCESSFUL TASK (Self-Generating)
                            # =============================================================
                            if success and validation_passed:
                                await self._extract_skill_from_task(task, result)

                            # =============================================================
                            # RE-VALIDATE AFTER FIX TASK COMPLETES
                            # =============================================================
                            if success and task.title.startswith("Fix validation failures:"):
                                await self._handle_fix_task_completion(task)

                            # Check if objective is complete
                            objective_tasks = await self.memory.short_term.get_tasks_for_objective(
                                task.objective_id
                            )
                            all_complete = all(
                                (t.status.value if hasattr(t.status, 'value') else str(t.status)) in ("completed", "failed")
                                for t in objective_tasks
                            )
                            if all_complete:
                                all_success = all(
                                    (t.status.value if hasattr(t.status, 'value') else str(t.status)) == "completed"
                                    for t in objective_tasks
                                )
                                await self.memory.complete_objective(
                                    task.objective_id,
                                    success=all_success
                                )

                                # Extract template and sync to GitHub
                                if all_success:
                                    await self._extract_template_if_applicable(task.objective_id)
                                    await self._sync_to_github_if_applicable(task.objective_id)

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

    async def _run_validation(self, task) -> bool:
        """
        Run validation pipeline on completed task.

        MANDATORY: Tasks FAIL if validation fails.
        Returns True if validation passed, False if failed.
        """
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

            logger.info(f"[MANDATORY VALIDATION] Running on {project_path} for task {task.id}")

            # Run validation pipeline
            result = await self.validation_pipeline.validate(
                project_path=project_path,
                task_id=task.id
            )

            # Log validation result
            if result.passed:
                logger.info(f"✓ Validation PASSED for task {task.id}: {result.summary}")
                await self.memory.log_activity(
                    source="validation",
                    action="passed",
                    details={"task_id": task.id, "summary": result.summary}
                )
                return True
            else:
                # =====================================================================
                # VALIDATION FAILED - TASK MUST FAIL
                # =====================================================================
                logger.error(f"✗ VALIDATION FAILED for task {task.id}: {result.summary}")

                # Get failed stages for detailed error
                failed_stages = [
                    s.stage.value if hasattr(s.stage, 'value') else str(s.stage)
                    for s in result.stages
                    if (s.status.value if hasattr(s.status, 'value') else str(s.status)) == "failed"
                ]

                await self.memory.log_activity(
                    source="validation",
                    action="failed",
                    details={
                        "task_id": task.id,
                        "summary": result.summary,
                        "failed_stages": failed_stages,
                        "stages": [
                            {
                                "stage": s.stage.value if hasattr(s.stage, 'value') else str(s.stage),
                                "status": s.status.value if hasattr(s.status, 'value') else str(s.status),
                                "message": getattr(s, 'message', None) or getattr(s, 'error', None)
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
                        "stages_failed": failed_stages
                    }
                )

                # Create a fix task for the debugger
                await self._create_fix_task(task, failed_stages, result.summary)

                return False

        except Exception as e:
            logger.error(f"Error running validation: {e}")
            # On error, fail the task to be safe
            return False

    async def _create_fix_task(self, original_task, failed_stages: list, error_summary: str) -> None:
        """Create a fix task for the debugger when validation fails."""
        try:
            fix_description = f"""
VALIDATION FAILURE - Fix Required

Original Task: {original_task.title}
Original Task ID: {original_task.id}
Failed Validation Stages: {', '.join(failed_stages)}
Error Summary: {error_summary}

Please:
1. Analyze the validation errors
2. Fix the code to pass all validation stages
3. Validation will automatically re-run after this fix task completes

Failed stages need to pass:
{chr(10).join(f'- {stage}' for stage in failed_stages)}

IMPORTANT: After fixing, validation will automatically re-run on the project.
"""

            await self.memory.create_tasks(original_task.objective_id, [
                {
                    "title": f"Fix validation failures: {original_task.title}",
                    "description": fix_description,
                    "priority": 1,  # High priority
                    "dependencies": [],
                    "worker_role": "debugger",
                    "metadata": {
                        "is_fix_task": True,
                        "original_task_id": original_task.id,
                        "failed_stages": failed_stages,
                        "revalidate_after": True
                    }
                }
            ])

            logger.info(f"Created fix task for validation failures in task {original_task.id}")

        except Exception as e:
            logger.error(f"Error creating fix task: {e}")

    async def _handle_fix_task_completion(self, fix_task) -> None:
        """
        Handle completion of a fix task by re-running validation.
        If validation passes, start the dev server for the project.
        """
        try:
            logger.info(f"Fix task completed: {fix_task.title}")

            # Determine project path
            project_path = "/workspace"
            if fix_task.description:
                import re
                path_match = re.search(r'/workspace/([\w\-]+)', fix_task.description)
                if path_match:
                    project_path = path_match.group(0)

            # Find the actual project directory
            from pathlib import Path
            workspace = Path("/workspace")
            projects = [p for p in workspace.iterdir() if p.is_dir() and not p.name.startswith('.')]

            for project in projects:
                if (project / "package.json").exists() or (project / "requirements.txt").exists():
                    project_path = str(project)
                    break

            logger.info(f"[RE-VALIDATION] Running full validation on {project_path}")

            # Run full validation
            result = await self.validation_pipeline.validate(
                project_path=project_path,
                task_id=fix_task.id
            )

            if result.passed:
                logger.info(f"✓ RE-VALIDATION PASSED for {project_path}")

                # Start dev server for the project
                await self._start_project_dev_server(project_path)

                # Log success
                await self.memory.log_activity(
                    source="validation",
                    action="revalidation_passed",
                    details={"project_path": project_path, "fix_task_id": fix_task.id}
                )
            else:
                logger.warning(f"✗ RE-VALIDATION FAILED for {project_path}: {result.summary}")

                # Create another fix task
                failed_stages = [
                    str(s.stage.value if hasattr(s.stage, 'value') else s.stage)
                    for s in result.stages
                    if str(s.status.value if hasattr(s.status, 'value') else s.status) == "failed"
                ]

                # Create a new mock task for the fix task creation
                class MockTask:
                    def __init__(self, task):
                        self.id = task.id
                        self.title = task.title.replace("Fix validation failures: ", "")
                        self.objective_id = task.objective_id

                await self._create_fix_task(
                    MockTask(fix_task),
                    failed_stages,
                    result.summary
                )

        except Exception as e:
            logger.error(f"Error handling fix task completion: {e}")

    async def _start_project_dev_server(self, project_path: str) -> None:
        """Start a dev server for the project so it's accessible via browser."""
        try:
            from pathlib import Path
            import subprocess
            import os

            project = Path(project_path)
            project_name = project.name

            # Determine the port (use project hash for consistent ports)
            base_port = 3000
            port = base_port + (hash(project_name) % 100)

            # Check if package.json exists
            if (project / "package.json").exists():
                import json
                pkg = json.loads((project / "package.json").read_text())
                scripts = pkg.get("scripts", {})

                if "dev" in scripts:
                    # Start the dev server in background
                    logger.info(f"Starting dev server for {project_name} on port {port}")

                    # Create a startup script
                    startup_script = project / ".clopus" / "start_server.sh"
                    startup_script.parent.mkdir(exist_ok=True)

                    startup_script.write_text(f'''#!/bin/bash
cd {project_path}
export PORT={port}
export HOST=0.0.0.0
npm run dev -- --host 0.0.0.0 --port {port} &
echo $! > {project / ".clopus" / "dev_server.pid"}
''')
                    os.chmod(startup_script, 0o755)

                    # Execute the startup script
                    subprocess.Popen(
                        ["bash", str(startup_script)],
                        cwd=project_path,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )

                    logger.info(f"✓ Dev server started: http://0.0.0.0:{port}")

                    # Store the server info
                    server_info = project / ".clopus" / "server_info.json"
                    server_info.write_text(json.dumps({
                        "port": port,
                        "host": "0.0.0.0",
                        "url": f"http://0.0.0.0:{port}",
                        "started_at": str(datetime.now())
                    }))

        except Exception as e:
            logger.error(f"Error starting dev server: {e}")

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

    async def _extract_skill_from_task(self, task, result: dict) -> None:
        """
        Extract a reusable skill from a successful task.
        Part of the self-generating ecosystem.
        """
        if not self.skills_engine:
            return

        try:
            task_description = f"{task.title}: {task.description or ''}"
            task_result = result.get("result", "")

            # Only extract from non-trivial tasks
            if len(task_description) < 50:
                return

            # Try to extract skill
            skill = await self.skills_engine.extract_skill_from_task(
                task_description=task_description,
                task_result={"result": task_result},
                success=True
            )

            if skill:
                logger.info(f"Extracted skill from task: {skill.get('name')}")
                await self.memory.log_activity(
                    source="skills_engine",
                    action="extracted",
                    details={"skill_name": skill.get("name"), "task_id": task.id}
                )

        except Exception as e:
            logger.warning(f"Error extracting skill from task: {e}")

    async def _sync_to_github_if_applicable(self, objective_id: str) -> None:
        """
        Sync completed project to GitHub.
        Creates repo if needed and pushes all changes.
        """
        if not self.github_sync:
            return

        try:
            objective = await self.memory.short_term.get_objective(objective_id)
            if not objective:
                return

            # Check if this is a project that should be synced
            content_lower = objective.content.lower()
            is_project = any(
                keyword in content_lower
                for keyword in ["create", "build", "develop", "implement", "make"]
            )

            if not is_project:
                return

            # Find project path
            from pathlib import Path
            import re

            path_match = re.search(r'/workspace/([\w\-]+)', objective.content)
            if path_match:
                project_name = path_match.group(1)
                project_path = Path(f"/workspace/{project_name}")
            else:
                workspace = Path("/workspace")
                recent_dirs = sorted(
                    [d for d in workspace.iterdir() if d.is_dir()],
                    key=lambda x: x.stat().st_mtime,
                    reverse=True
                )
                if recent_dirs:
                    project_path = recent_dirs[0]
                    project_name = project_path.name
                else:
                    return

            if not project_path.exists():
                return

            # Check if already a git repo
            is_git_repo = (project_path / ".git").exists()

            if not is_git_repo:
                # Create GitHub repo
                logger.info(f"Creating GitHub repository for {project_name}")
                repo_url = await self.github_sync.create_project_repo(
                    project_name=project_name,
                    description=objective.content[:100],
                    private=True,  # Default to private
                    local_path=project_path
                )

                if repo_url:
                    logger.info(f"Created GitHub repository: {repo_url}")
                    await self.memory.log_activity(
                        source="github_sync",
                        action="repo_created",
                        details={"repo_url": repo_url, "project": project_name}
                    )

            # Push changes
            pushed = await self.github_sync.push_project(
                local_path=project_path,
                commit_message=f"[CLOPUS] Project completed: {objective.content[:50]}"
            )

            if pushed:
                logger.info(f"Pushed project {project_name} to GitHub")
                await self.memory.log_activity(
                    source="github_sync",
                    action="pushed",
                    details={"project": project_name}
                )

            # Also sync any generated skills/templates/MCPs
            await self.github_sync.sync_all()

        except Exception as e:
            logger.error(f"Error syncing to GitHub: {e}")


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
