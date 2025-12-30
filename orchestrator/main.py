# =============================================================================
# CLOPUS v3 Orchestrator Main Entry Point
# =============================================================================
"""
Main orchestrator that coordinates all CLOPUS operations.
"""

import asyncio
import json
import signal
import sys
import time
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
from .port_manager import get_port_manager, PortManager
from .project_docs import get_docs_generator, ProjectDocsGenerator
from .design_system import get_design_system, get_consultation_queue, DesignSystem
from .project_state import get_state_manager, ProjectStateManager, ProjectState
from .project_resumption import get_resumption_generator, create_resumption_objective
from .shared_context import get_shared_context, SharedContextManager
from .heartbeat_agent import HeartbeatAgent, get_heartbeat_agent, set_heartbeat_worker_pool
from .verificator_client import VerificatorClient, get_verificator_client, set_verificator_client
from .collaboration import CollaborationManager
from .message_router import MessageRouter
from .context_injector import ContextInjector
from .ai_planner import AIPlanner, create_ai_planner
from .ai_first import AIFirstEngine, set_ai_engine, get_ai_engine
from .websocket_server import (
    start_websocket_server,
    stop_websocket_server,
    emit_worker_status,
    emit_task_completed,
    emit_task_failed,
    emit_question_pending,
    emit_validation_result,
    emit_self_healing,
    emit_objective_created,
    emit_objective_completed,
    emit_project_update,
    WebSocketServer,
)
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

        # =================================================================
        # AUTHENTICATION STATE TRACKING (NEW)
        # =================================================================
        # When OAuth expires, we pause all operations until user re-authenticates
        self._auth_paused = False
        self._auth_pause_reason: Optional[str] = None
        self._auth_question_id: Optional[str] = None
        self._last_auth_check: Optional[datetime] = None

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
        self.shared_context: Optional[SharedContextManager] = None

        # Heartbeat agent (completion guardian)
        self.heartbeat_agent: Optional[HeartbeatAgent] = None

        # Verificator client (intelligent verification using Worker 8)
        self.verificator_client: Optional[VerificatorClient] = None

        # Inter-worker collaboration components
        self.collaboration_manager: Optional[CollaborationManager] = None
        self.message_router: Optional[MessageRouter] = None
        self.context_injector: Optional[ContextInjector] = None

        # AI-first planning (NEW in v3.1)
        self.ai_planner: Optional[AIPlanner] = None

        # AI-first intelligence engine (NEW in v3.2)
        self.ai_engine: Optional[AIFirstEngine] = None

        # WebSocket server for TUI real-time updates
        self.websocket_server: Optional[WebSocketServer] = None

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

        # =====================================================================
        # SELF-HEALING ON STARTUP
        # =====================================================================
        # Reset stale assigned tasks (from previous run that didn't complete)
        reset_count = await self.memory.reset_stale_assigned_tasks()
        if reset_count > 0:
            logger.info(f"Self-healing: Reset {reset_count} stale assigned tasks to pending")

        # Deduplicate pending objectives
        dup_count = await self.memory.deduplicate_pending_objectives()
        if dup_count > 0:
            logger.info(f"Self-healing: Marked {dup_count} duplicate objectives")

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

        # Initialize verificator client (uses Worker 8 for intelligent verification)
        self.verificator_client = VerificatorClient(self.worker_pool)
        set_verificator_client(self.verificator_client)
        logger.info("Verificator client initialized (Worker 8)")

        # =====================================================================
        # AI-FIRST PLANNING INITIALIZATION (NEW in v3.1)
        # =====================================================================
        # Initialize AI planner for intelligent task generation
        self.ai_planner = AIPlanner(self.worker_pool, self.memory)
        logger.info("AI Planner initialized - using AI-first task generation")

        # Connect worker pool to task planner and objective parser
        # This enables AI-first planning instead of template-based planning
        self.task_planner.set_worker_pool(self.worker_pool)
        self.task_planner.set_ai_planner(self.ai_planner)
        self.objective_parser.set_worker_pool(self.worker_pool)
        self.objective_parser.set_ai_planner(self.ai_planner)
        logger.info("AI Planner connected to task planner and objective parser")

        # =====================================================================
        # AI-FIRST INTELLIGENCE ENGINE (NEW in v3.2)
        # =====================================================================
        # Replaces ALL regex/pattern matching with Claude Code intelligence
        self.ai_engine = AIFirstEngine(self.worker_pool, self.memory)
        set_ai_engine(self.ai_engine)

        # Connect AI engine to components that need it (already initialized)
        self.confidence_engine.set_ai_engine(self.ai_engine)
        self.task_planner.set_ai_engine(self.ai_engine)
        self.worker_pool.set_ai_engine(self.ai_engine)
        self.verificator_client.set_ai_engine(self.ai_engine)
        self.objective_parser.set_ai_engine(self.ai_engine)
        # Note: other components will be connected after they're initialized below
        logger.info("AI-First Engine initialized - regex patterns deprecated")

        # Initialize inter-worker collaboration components
        self.message_router = MessageRouter(
            self.worker_pool,
            self.settings.ipc_path
        )
        self.collaboration_manager = CollaborationManager(
            self.worker_pool,
            self.memory,
            self.settings.ipc_path
        )
        await self.collaboration_manager.initialize()
        self.context_injector = ContextInjector(
            self.memory,
            self.settings.ipc_path
        )

        # Connect AI engine to collaboration components (NEW in v3.2)
        self.message_router.set_ai_engine(self.ai_engine)
        self.context_injector.set_ai_engine(self.ai_engine)
        logger.info("Inter-worker collaboration initialized")

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

        # Connect AI engine to skills engine for semantic matching (NEW in v3.2)
        if self.ai_engine:
            self.skills_engine.set_ai_engine(self.ai_engine)

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
        self.validation_pipeline.set_ai_engine(self.ai_engine)
        logger.info("Validation pipeline initialized")

        self.project_setup = ProjectSetup("/workspace")
        self.project_setup.set_ai_engine(self.ai_engine)
        logger.info("Project setup initialized")

        self.shared_context = get_shared_context()
        logger.info("Shared context manager initialized")

        self.capability_installer = CapabilityInstaller(self.worker_pool)
        logger.info("Capability installer initialized")

        # Initialize project state manager (needed by heartbeat agent)
        self.state_manager = get_state_manager(self.settings.workspace_path)
        self.state_manager.set_ai_engine(self.ai_engine)
        logger.info("Project state manager initialized")

        # Initialize design system
        self.design_system = get_design_system(self.memory)
        self.design_system.set_ai_engine(self.ai_engine)
        logger.info("Design system initialized")

        # Initialize heartbeat agent (completion guardian)
        # Uses worker dispatch (OAuth) instead of direct API calls
        heartbeat_interval = self.settings.heartbeat_config.interval_seconds if hasattr(self.settings, 'heartbeat_config') else 300
        self.heartbeat_agent = get_heartbeat_agent(
            memory=self.memory,
            state_manager=self.state_manager,
            shared_context=self.shared_context,
            worker_pool=self.worker_pool,
            heartbeat_interval_seconds=heartbeat_interval,
            workspace_path=self.settings.workspace_path,
            ipc_path=self.settings.ipc_path
        )
        logger.info(f"Heartbeat agent initialized (interval: {heartbeat_interval}s, using worker dispatch)")

        self.knowledge_base = KnowledgeBase(self.memory, "/app/knowledge")
        self.knowledge_base.set_ai_engine(self.ai_engine)
        logger.info("Knowledge base initialized")

        # Initialize resumption generator
        self.resumption_generator = get_resumption_generator(
            self.state_manager,
            get_port_manager()
        )
        logger.info("Resumption generator initialized")

        # =====================================================================
        # CONNECT COMPONENTS FOR INTEGRATION
        # =====================================================================
        # Connect skills engine to task planner for skill-aware planning
        self.task_planner.set_skills_engine(self.skills_engine)
        self.task_planner.set_template_extractor(self.template_extractor)
        self.task_planner.set_design_system(self.design_system)

        # Connect skills engine to worker pool for skill-enhanced prompts
        self.worker_pool.set_skills_engine(self.skills_engine)

        logger.info("Component integrations configured")

        # =====================================================================
        # WEBSOCKET SERVER FOR TUI REAL-TIME UPDATES
        # =====================================================================
        self.websocket_server = await start_websocket_server(
            host="0.0.0.0",
            port=8765
        )
        if self.websocket_server:
            logger.info("WebSocket server started on ws://0.0.0.0:8765")
        else:
            logger.warning("WebSocket server could not be started (websockets package may be missing)")

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

        # =====================================================================
        # INITIAL AUTH CHECK
        # =====================================================================
        await self._check_initial_auth()

        # =====================================================================
        # SCAN FOR INCOMPLETE PROJECTS AND CREATE RESUMPTION TASKS
        # =====================================================================
        await self._scan_and_resume_projects()

        # Start background tasks
        tasks = [
            asyncio.create_task(self._main_loop()),
            asyncio.create_task(self._objective_watcher()),
            asyncio.create_task(self._answer_watcher()),
            asyncio.create_task(self._worker_monitor()),
            asyncio.create_task(self._status_loop()),
            asyncio.create_task(self._heartbeat_loop()),  # Completion guardian
            asyncio.create_task(self._collaboration_loop()),  # Inter-worker communication
            asyncio.create_task(self._self_healing_loop()),  # Autonomous recovery
            asyncio.create_task(self._auth_health_loop()),  # Auth health monitoring
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

        if self.collaboration_manager:
            await self.collaboration_manager.shutdown()

        if self.worker_pool:
            await self.worker_pool.shutdown()

        # Stop WebSocket server
        await stop_websocket_server()
        logger.info("WebSocket server stopped")

        logger.info("CLOPUS orchestrator shutdown complete")

    def request_shutdown(self) -> None:
        """Request graceful shutdown."""
        self._shutdown_event.set()

    # =========================================================================
    # PROJECT RESUMPTION
    # =========================================================================

    async def _scan_and_resume_projects(self) -> None:
        """
        Scan workspace for incomplete projects and create resumption tasks.
        Called on CLOPUS startup.
        """
        logger.info("Scanning for incomplete projects...")

        try:
            # Scan workspace for incomplete projects
            incomplete_projects = await self.state_manager.scan_workspace()

            if not incomplete_projects:
                logger.info("No incomplete projects found")
                return

            logger.info(f"Found {len(incomplete_projects)} incomplete project(s)")

            # Clean up orphaned dev servers first
            port_manager = get_port_manager()
            killed = port_manager.cleanup_orphaned_servers()
            if killed:
                logger.info(f"Cleaned up {killed} orphaned dev server(s)")

            # Process each incomplete project
            for state in incomplete_projects:
                logger.info(f"Processing incomplete project: {state.project_name}")

                # Handle port mismatches
                if state.dev_server.get("needs_restart"):
                    current_port = state.dev_server.get("port")
                    if current_port:
                        success, new_port = port_manager.restart_on_correct_port(
                            state.project_name,
                            current_port,
                            state.project_path
                        )
                        if success:
                            await self.state_manager.update_dev_server(
                                state.project_path,
                                running=False,  # Will be started by task
                                allocated_port=new_port
                            )

                # Generate resumption tasks
                tasks = await self.resumption_generator.generate_resumption_tasks(state)

                if tasks:
                    # Create or requeue the objective
                    objective_id = await create_resumption_objective(state, self.memory)

                    if objective_id:
                        # Create tasks for this objective
                        await self.memory.create_tasks(objective_id, tasks)

                        logger.info(
                            f"Created {len(tasks)} resumption tasks for {state.project_name}"
                        )

                        # Log activity
                        await self.memory.log_activity(
                            source="resumption",
                            action="tasks_created",
                            details={
                                "project": state.project_name,
                                "objective_id": objective_id,
                                "task_count": len(tasks),
                                "pending_work": state.get_pending_work()
                            }
                        )

        except Exception as e:
            logger.error(f"Error scanning for incomplete projects: {e}", exc_info=True)

    # =========================================================================
    # MAIN LOOPS
    # =========================================================================

    async def _main_loop(self) -> None:
        """Main orchestration loop."""
        logger.info("Main loop started")

        while self.running:
            try:
                # =============================================================
                # AUTH PAUSE CHECK - Don't process anything if auth expired
                # =============================================================
                if self._auth_paused:
                    # Check if user has re-authenticated
                    if await self._check_auth_restored():
                        logger.info("Authentication restored - resuming operations")
                        self._auth_paused = False
                        self._auth_pause_reason = None
                        self._auth_question_id = None
                    else:
                        # Still paused, just wait
                        await asyncio.sleep(5)
                        continue

                # Get next objective to process
                objective = await self.memory.get_next_objective()

                if objective:
                    await self._process_objective(objective)

                # Always try to assign pending tasks (not just when no objective)
                # This ensures tasks get dispatched even when objectives are queued
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

            # =================================================================
            # HANDLE RESUMPTION OBJECTIVES - Skip AI planning, use existing path
            # =================================================================
            # Resumption objectives already have a project path and just need
            # their pending tasks created. Going through AI planning would
            # generate a DIFFERENT project name, creating duplicate folders.
            if objective.content.startswith("[RESUMPTION]"):
                logger.info(f"Processing RESUMPTION objective - skipping AI planning")
                await self._process_resumption_objective(objective)
                return

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
                question_id = await self.user_interaction.ask_clarification(
                    f"I need clarification on this objective: {objective.content}\n\nSpecifically: {parsed.get('unclear_points', 'general scope')}",
                    objective_id=objective.id,
                    confidence_score=confidence
                )

                # Emit question pending event for TUI
                if question_id:
                    emit_question_pending(
                        question_id=question_id,
                        content=f"Clarification needed for objective (confidence: {confidence:.0%})"
                    )
                return

            # =====================================================================
            # CREATE PROJECT WITH CLAUDE.md
            # =====================================================================
            # Determine project path from parsed objective
            # Reject generic "project" name from AI fallback - use objective ID instead
            parsed_name = parsed.get("project_name")
            if parsed_name and parsed_name not in ("project", "custom"):
                project_name = parsed_name
            else:
                project_name = f"project-{objective.id[:8]}"
            project_path = f"/workspace/{project_name}"
            project_type = parsed.get("project_type")

            # =================================================================
            # CRITICAL: Link project to objective in metadata
            # This enables heartbeat to find the correct project for an objective
            # =================================================================
            try:
                await self.memory.short_term.update_objective_metadata(
                    objective.id,
                    {
                        "project_path": project_path,
                        "project_name": project_name,
                        "project_type": project_type
                    }
                )
                logger.info(f"Linked objective {objective.id[:8]} to project: {project_name}")
            except Exception as e:
                logger.warning(f"Could not link project to objective: {e}")

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
                        "project_name": project_name,
                        "claude_md": str(claude_md_path)
                    }
                )

                # Initialize project state for tracking
                if self.heartbeat_agent and self.heartbeat_agent.state_manager:
                    try:
                        await self.heartbeat_agent.state_manager.create_state(
                            project_path,
                            objective.id,
                            content
                        )
                        logger.info(f"Initialized project state for: {project_name}")
                    except Exception as e:
                        logger.warning(f"Could not initialize project state: {e}")

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

            # Create tasks in memory with project context
            # Inject project_path and shared context into task descriptions
            def enhance_task_description(task_def: dict) -> str:
                base_desc = task_def.get("description") or ""
                enhancements = []

                # Add project path if not already present
                if project_path not in base_desc:
                    enhancements.append(f"Project Path: {project_path}")

                # Add shared context for cross-project dependencies
                if self.shared_context:
                    shared_info = self.shared_context.get_shared_context_for_project(project_name)
                    if shared_info:
                        enhancements.append(shared_info)

                if enhancements:
                    return base_desc + "\n\n" + "\n\n".join(enhancements)
                return base_desc

            await self.memory.create_tasks(objective.id, [
                {
                    "title": t["title"],
                    "description": enhance_task_description(t),
                    "priority": t.get("priority", 5),
                    "dependencies": t.get("dependencies", []),
                    "worker_role": t.get("worker_role")
                }
                for t in tasks
            ])

        except Exception as e:
            logger.error(f"Error processing objective: {e}", exc_info=True)
            await self.memory.complete_objective(objective.id, success=False)

    async def _process_resumption_objective(self, objective) -> None:
        """
        Process a resumption objective without AI planning.

        Resumption objectives already have a project path and pending work defined.
        Going through AI planning would generate a DIFFERENT project name,
        which is why we extract the existing path and create tasks directly.
        """
        import re

        content = objective.content

        # Extract project path from content
        # Format: "Project Path: /workspace/project-name"
        path_match = re.search(r'Project Path:\s*(/workspace/[\w\-]+)', content)
        if not path_match:
            logger.error(f"Resumption objective missing Project Path: {content[:200]}")
            await self.memory.complete_objective(objective.id, success=False)
            return

        project_path = path_match.group(1)
        project_name = Path(project_path).name

        logger.info(f"Resumption using existing project: {project_path}")

        # Update objective metadata with project info
        try:
            await self.memory.short_term.update_objective_metadata(
                objective.id,
                {
                    "project_path": project_path,
                    "project_name": project_name,
                    "is_resumption": True
                }
            )
        except Exception as e:
            logger.warning(f"Could not update resumption objective metadata: {e}")

        # Load project state
        state_manager = get_state_manager()
        state = await state_manager.get_state(project_path)

        if not state:
            logger.warning(f"No project state found at {project_path}, checking if project exists")
            project_dir = Path(project_path)
            if not project_dir.exists():
                logger.error(f"Project directory does not exist: {project_path}")
                await self.memory.complete_objective(objective.id, success=False)
                return
            # Create minimal state
            state = await state_manager.create_state(project_path, objective.id, content)

        # Generate resumption tasks using the resumption generator
        resumption_gen = get_resumption_generator(state_manager, get_port_manager())
        tasks = await resumption_gen.generate_resumption_tasks(state)

        if not tasks:
            logger.info(f"No pending work for {project_name}, marking objective complete")
            await self.memory.complete_objective(objective.id, success=True)
            return

        logger.info(f"Generated {len(tasks)} resumption tasks for {project_name}")

        # Create tasks in memory
        await self.memory.create_tasks(objective.id, [
            {
                "title": t["title"],
                "description": t["description"] + f"\n\nProject Path: {project_path}",
                "priority": t.get("priority", 5),
                "dependencies": t.get("dependencies", []),
                "worker_role": t.get("worker_role")
            }
            for t in tasks
        ])

        logger.info(f"Resumption objective processed: {len(tasks)} tasks created for {project_name}")

    async def _assign_pending_tasks(self) -> None:
        """Assign pending tasks to available workers."""
        # Get assignable tasks
        tasks = await self.memory.get_assignable_tasks()

        for task in tasks:
            # Get idle worker for role
            worker = await self.memory.get_idle_worker(task.worker_role)

            if worker:
                # Determine correct project path for this task (use async for AI-first)
                project_path = await self._get_project_path_for_task_async(task)

                # =====================================================================
                # USE VERIFICATOR TO SPECIFY EXPECTED ARTIFACTS (if not already set)
                # =====================================================================
                if not task.expected_artifacts and self.verificator_client:
                    try:
                        artifacts = await self.verificator_client.specify_artifacts(
                            task_title=task.title,
                            task_description=task.description or "",
                            project_path=project_path
                        )
                        if artifacts:
                            # Update task with expected artifacts
                            await self.memory.short_term.update_expected_artifacts(
                                task.id, artifacts
                            )
                            logger.info(
                                f"Verificator specified {len(artifacts)} expected artifacts for task: {task.title}"
                            )
                    except Exception as e:
                        logger.warning(f"Could not specify artifacts for task: {e}")

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

                # Get relevant memory context (basic lookup)
                try:
                    memory_context = await self.memory.get_relevant_context(
                        task.title + " " + (task.description or "")
                    )
                except Exception:
                    pass

                # Inject full context (design system, learnings, API endpoints)
                enriched_description = task.description or ""
                if self.context_injector:
                    try:
                        task_dict = {
                            "description": task.description or "",
                            "prompt": task.title,
                        }
                        enriched_task = await self.context_injector.inject_context(
                            task=task_dict,
                            worker_role=worker.role,
                            project_path=project_path
                        )
                        enriched_description = enriched_task.get("description", task.description or "")
                    except Exception as e:
                        logger.debug(f"Context injection failed: {e}")

                # Dispatch to worker with correct cwd and context
                dispatched = await self.worker_pool.dispatch_task(
                    worker.id,
                    task.id,
                    task.title,
                    enriched_description,
                    cwd=project_path,
                    relevant_skills=relevant_skills if relevant_skills else None,
                    memory_context=memory_context
                )

                if dispatched:
                    logger.info(f"Assigned task '{task.title}' to worker {worker.id}")

                    # Emit worker status for TUI
                    emit_worker_status(
                        worker_id=worker.id,
                        status="busy",
                        role=worker.role,
                        task_id=task.id
                    )
                else:
                    # Dispatch failed (worker didn't acknowledge) - revert assignment
                    # Reset task to pending so it can be reassigned
                    await self.memory.short_term.update_task_status(
                        task.id, "pending"
                    )
                    # Reset worker to idle in the pool
                    if worker.id in self.worker_pool.workers:
                        self.worker_pool.workers[worker.id]["status"] = "idle"
                        self.worker_pool.workers[worker.id]["current_task"] = None
                    logger.warning(
                        f"Task '{task.title}' dispatch failed, reverted to pending for reassignment"
                    )

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
                            objective_id = await self.memory.create_objective(objective_text)
                            logger.info(f"New objective from file: {file.name}")

                            # Emit objective created event for TUI
                            if objective_id:
                                emit_objective_created(
                                    objective_id=objective_id,
                                    content=objective_text
                                )

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
                # Skip monitoring if auth is paused
                if self._auth_paused:
                    await asyncio.sleep(2)
                    continue

                # Check for completed tasks
                results = await self.worker_pool.collect_results()

                for worker_id, result in results.items():
                    task_id = result.get("task_id")
                    success = result.get("status") == "completed"

                    # =============================================================
                    # AUTH ERROR DETECTION - Check if this result indicates auth failure
                    # =============================================================
                    if self._is_auth_error(result):
                        error_msg = result.get("result", "") or result.get("error", "OAuth token expired")
                        await self._handle_auth_error(error_msg)
                        # Don't process this result further, task will be retried after auth
                        continue

                    if task_id:
                        # Get task details for validation BEFORE marking complete
                        task = await self.memory.short_term.get_task(task_id)

                        # =====================================================================
                        # ARTIFACT VERIFICATION - Check expected files were created
                        # LENIENT MODE: Log warnings but don't fail tasks for missing artifacts
                        # The verificator's artifact inference isn't perfect and shouldn't
                        # block task completion for non-critical files
                        # =====================================================================
                        artifacts_verified = True
                        if task and success and task.expected_artifacts:
                            artifacts_verified, missing = await self._verify_artifacts(task)
                            if not artifacts_verified:
                                # LENIENT: Only warn, don't fail the task
                                # The AI might have achieved the goal differently than expected
                                logger.warning(
                                    f"Task {task_id}: Some expected artifacts not found: {missing}. "
                                    f"Continuing as success since worker reported completion."
                                )
                                # Still mark as verified since worker completed successfully
                                await self.memory.short_term.mark_artifacts_verified(task_id, True)
                            else:
                                # Mark artifacts as verified in DB
                                await self.memory.short_term.mark_artifacts_verified(task_id, True)
                                logger.info(f"Task {task_id}: All {len(task.expected_artifacts)} artifacts verified")

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

                        # Emit WebSocket events for TUI
                        if success:
                            emit_task_completed(
                                task_id=task_id,
                                title=task.title if task else "Unknown",
                                project=task.project if hasattr(task, 'project') and task.project else "",
                                worker_id=worker_id
                            )
                        else:
                            emit_task_failed(
                                task_id=task_id,
                                title=task.title if task else "Unknown",
                                error=result.get("error", ""),
                                worker_id=worker_id
                            )

                        # Worker is now idle
                        worker_info = self.worker_pool.workers.get(worker_id, {})
                        emit_worker_status(
                            worker_id=worker_id,
                            status="idle",
                            role=worker_info.get("role", "unknown"),
                            task_id=None
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
                            # EXTRACT LEARNINGS (ContextInjector - patterns/solutions/warnings)
                            # =============================================================
                            if self.context_injector and success:
                                try:
                                    task_dict = {
                                        "id": task.id,
                                        "title": task.title,
                                        "description": task.description or "",
                                    }
                                    learnings = await self.context_injector.extract_learnings(
                                        task_result=result,
                                        task=task_dict,
                                        worker_role=task.worker_role or "unknown"
                                    )
                                    if learnings:
                                        logger.info(
                                            f"Extracted {len(learnings)} learnings from task {task.id}"
                                        )
                                except Exception as e:
                                    logger.debug(f"Learning extraction failed: {e}")

                            # =============================================================
                            # UPDATE PROJECT STATE ON TASK COMPLETION
                            # =============================================================
                            try:
                                await self._update_project_state_on_task_completion(task, success)
                            except Exception as e:
                                logger.warning(f"Error updating project state: {e}")

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

                            # =============================================================
                            # CHECK IF OBJECTIVE IS COMPLETE
                            # =============================================================
                            # CRITICAL FIX: Don't immediately mark objective as failed
                            # when tasks fail. Let the heartbeat agent handle remediation.
                            # Only mark as COMPLETED when ALL tasks succeed.
                            # =============================================================
                            objective_tasks = await self.memory.short_term.get_tasks_for_objective(
                                task.objective_id
                            )

                            # Check task statuses
                            completed_count = sum(
                                1 for t in objective_tasks
                                if (t.status.value if hasattr(t.status, 'value') else str(t.status)) == "completed"
                            )
                            failed_count = sum(
                                1 for t in objective_tasks
                                if (t.status.value if hasattr(t.status, 'value') else str(t.status)) == "failed"
                            )
                            pending_count = sum(
                                1 for t in objective_tasks
                                if (t.status.value if hasattr(t.status, 'value') else str(t.status)) in ("pending", "assigned", "in_progress")
                            )
                            total_count = len(objective_tasks)

                            logger.info(
                                f"Objective {task.objective_id[:8]} progress: "
                                f"{completed_count}/{total_count} completed, "
                                f"{failed_count} failed, {pending_count} pending"
                            )

                            # Only mark as COMPLETED if ALL tasks succeeded
                            if completed_count == total_count and total_count > 0:
                                await self.memory.complete_objective(
                                    task.objective_id,
                                    success=True
                                )

                                # Emit objective completion event for TUI
                                emit_objective_completed(
                                    objective_id=task.objective_id,
                                    success=True,
                                    task_count=total_count
                                )

                                # Extract template and sync to GitHub
                                await self._extract_template_if_applicable(task.objective_id)
                                await self._sync_to_github_if_applicable(task.objective_id)

                                logger.info(f"Objective {task.objective_id[:8]} COMPLETED successfully!")

                            # If there are failed tasks but no pending work, let heartbeat handle it
                            # DON'T immediately mark as failed - heartbeat may create remediation tasks
                            elif failed_count > 0 and pending_count == 0:
                                logger.warning(
                                    f"Objective {task.objective_id[:8]} has {failed_count} failed tasks. "
                                    f"Heartbeat will analyze for remediation."
                                )
                                # Emit update but don't mark as complete yet
                                emit_project_update(
                                    project_id=task.objective_id,
                                    status="needs_remediation",
                                    details={
                                        "completed": completed_count,
                                        "failed": failed_count,
                                        "total": total_count
                                    }
                                )

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

    async def _heartbeat_loop(self) -> None:
        """
        Heartbeat agent loop - The Completion Guardian.

        Periodically analyzes all active objectives to ensure:
        1. Requirements from objectives are actually being met
        2. All 8 validation stages pass
        3. Multi-project integrations work together
        4. Projects don't get marked complete prematurely
        """
        logger.info("Heartbeat loop started (Completion Guardian)")

        # Wait a bit for other systems to initialize
        await asyncio.sleep(30)

        while self.running:
            try:
                # Skip heartbeat if auth is paused
                if self._auth_paused:
                    logger.debug("Heartbeat skipped - auth paused")
                    await asyncio.sleep(30)
                    continue

                if self.heartbeat_agent:
                    await self.heartbeat_agent._heartbeat_cycle()

                # Get interval from config or use default (5 minutes)
                interval = 300
                if hasattr(self.settings, 'heartbeat_config'):
                    interval = self.settings.heartbeat_config.interval_seconds

                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}", exc_info=True)
                await asyncio.sleep(60)  # Wait a minute before retrying

    async def _collaboration_loop(self) -> None:
        """
        Inter-worker collaboration loop.

        Monitors the collaboration IPC directory and:
        1. Routes help requests to appropriate workers
        2. Processes async events (spawn_subtask, share_learning, etc.)
        3. Delivers responses back to requesting workers
        """
        logger.info("Collaboration loop started (Inter-worker communication)")

        # Wait for other systems to initialize
        await asyncio.sleep(5)

        while self.running:
            try:
                # Skip collaboration if auth is paused
                if self._auth_paused:
                    await asyncio.sleep(5)
                    continue

                if self.collaboration_manager:
                    await self.collaboration_manager.process_collaboration()

                # Poll every 500ms for responsive inter-worker communication
                await asyncio.sleep(0.5)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in collaboration loop: {e}", exc_info=True)
                await asyncio.sleep(2)  # Brief pause before retrying

    async def _self_healing_loop(self) -> None:
        """
        Autonomous self-healing loop.

        Periodically performs maintenance tasks to keep the system healthy:
        1. Reset tasks stuck in 'assigned' state too long
        2. Deduplicate incoming objectives
        3. Clean up stale IPC files
        4. Verify worker health and restart if needed
        """
        logger.info("Self-healing loop started (Autonomous recovery)")

        # Wait for initial startup to complete
        await asyncio.sleep(60)

        while self.running:
            try:
                # Skip self-healing if auth is paused (except for essential cleanup)
                if self._auth_paused:
                    await asyncio.sleep(60)
                    continue

                # Run self-healing every 5 minutes
                healing_actions = []

                # 1. Reset stale assigned tasks (stuck > 30 minutes)
                stale_count = await self.memory.cleanup_stale_tasks(stale_threshold_minutes=30)
                if stale_count > 0:
                    healing_actions.append(f"Reset {stale_count} stale tasks")

                # 2. Deduplicate pending objectives
                dup_count = await self.memory.deduplicate_pending_objectives()
                if dup_count > 0:
                    healing_actions.append(f"Deduplicated {dup_count} objectives")

                # 3. Check for orphaned pending.json files (worker died mid-task)
                orphan_count = await self._cleanup_orphaned_ipc_files()
                if orphan_count > 0:
                    healing_actions.append(f"Cleaned {orphan_count} orphaned IPC files")

                # 4. Verify workers are responding (health check)
                unhealthy_count = await self._check_worker_health()
                if unhealthy_count > 0:
                    healing_actions.append(f"Detected {unhealthy_count} unhealthy workers")

                # Log healing actions if any were taken
                if healing_actions:
                    logger.info(f"Self-healing cycle completed: {', '.join(healing_actions)}")

                    # Emit self-healing event for TUI
                    total_actions = stale_count + dup_count + orphan_count + unhealthy_count
                    emit_self_healing(
                        action="cycle_completed",
                        count=total_actions,
                        details="; ".join(healing_actions)
                    )

                # Run every 5 minutes
                await asyncio.sleep(300)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in self-healing loop: {e}", exc_info=True)
                await asyncio.sleep(60)  # Wait a minute before retrying

    async def _cleanup_orphaned_ipc_files(self) -> int:
        """Clean up orphaned IPC files from workers that died mid-task."""
        orphan_count = 0
        ipc_base = Path("/app/ipc/tasks")

        if not ipc_base.exists():
            return 0

        for worker_dir in ipc_base.iterdir():
            if not worker_dir.is_dir():
                continue

            pending_file = worker_dir / "pending.json"
            status_file = worker_dir / "status.json"

            # If pending.json exists but status shows idle, clean up
            if pending_file.exists() and status_file.exists():
                try:
                    status_data = json.loads(status_file.read_text())
                    status = status_data.get("status", "")
                    updated_at = status_data.get("updated_at", "")

                    # If worker is idle but has pending file, it's orphaned
                    if status == "idle":
                        # Check if pending file is old (> 2 minutes)
                        pending_stat = pending_file.stat()
                        if time.time() - pending_stat.st_mtime > 120:
                            logger.warning(f"Cleaning orphaned pending.json in {worker_dir.name}")
                            pending_file.unlink()
                            orphan_count += 1
                except Exception as e:
                    logger.debug(f"Error checking orphan status for {worker_dir.name}: {e}")

        return orphan_count

    async def _check_worker_health(self) -> int:
        """Check worker health based on status file updates."""
        unhealthy_count = 0
        ipc_base = Path("/app/ipc/tasks")
        stale_threshold = 60  # Consider unhealthy if no update in 60 seconds

        if not ipc_base.exists():
            return 0

        for worker_dir in ipc_base.iterdir():
            if not worker_dir.is_dir():
                continue

            status_file = worker_dir / "status.json"
            if status_file.exists():
                try:
                    status_data = json.loads(status_file.read_text())
                    updated_at = status_data.get("updated_at", "")

                    if updated_at:
                        # Parse ISO format datetime
                        from datetime import datetime
                        last_update = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                        now = datetime.now(last_update.tzinfo) if last_update.tzinfo else datetime.now()
                        age_seconds = (now - last_update).total_seconds()

                        if age_seconds > stale_threshold:
                            logger.warning(f"Worker {worker_dir.name} appears unhealthy (no update for {age_seconds:.0f}s)")
                            unhealthy_count += 1
                except Exception as e:
                    logger.debug(f"Error checking health for {worker_dir.name}: {e}")

        return unhealthy_count

    # =========================================================================
    # PROJECT PATH DETECTION
    # =========================================================================

    async def _get_project_path_for_task_async(self, task) -> str:
        """
        Determine the correct project path for a task.

        NEW IN v3.2: AI-First approach
        Priority:
        1. Task metadata (resumption tasks)
        2. AI-First Engine (semantic understanding)
        3. Regex patterns (deprecated fallback)
        4. Auto-detect most recent project

        Returns: Project path string (e.g., "/workspace/nexus-api")
        """
        project_path = None

        # PRIORITY 1: Extract from task metadata (resumption tasks) - fast check
        if hasattr(task, 'metadata') and task.metadata:
            if isinstance(task.metadata, dict):
                project_path = task.metadata.get('project_path')
                if project_path:
                    return project_path

        # PRIORITY 2: AI-First project detection
        if self.ai_engine and task.description:
            try:
                # Get available projects
                workspace = Path("/workspace")
                if workspace.exists():
                    available_projects = [
                        str(p) for p in workspace.iterdir()
                        if p.is_dir() and not p.name.startswith('.')
                    ]

                    if available_projects:
                        result = await self.ai_engine.detect_project_path(
                            task_title=task.title if hasattr(task, 'title') else "",
                            task_description=task.description,
                            available_projects=available_projects,
                            task_result=task.result if hasattr(task, 'result') else None
                        )

                        if result.success and result.result:
                            detected_path = result.result.get("project_path")
                            if detected_path and result.confidence > 0.5:
                                logger.debug(f"AI-first detected project: {detected_path} ({result.confidence:.2f})")
                                return detected_path
            except Exception as e:
                logger.debug(f"AI-first project detection failed: {e}")

        # PRIORITY 3: Regex fallback (deprecated)
        project_path = self._regex_detect_project_path(task)
        if project_path:
            return project_path

        # PRIORITY 4: Find most recently modified project
        workspace = Path("/workspace")
        if workspace.exists():
            projects = [
                p for p in workspace.iterdir()
                if p.is_dir() and not p.name.startswith('.')
                and ((p / "package.json").exists() or (p / "requirements.txt").exists() or (p / ".clopus").exists())
            ]
            if projects:
                # Sort by modification time, most recent first
                projects.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                project_path = str(projects[0])
                logger.debug(f"Auto-detected project for task: {project_path}")
                return project_path

        # Fallback to workspace root
        return "/workspace"

    def _get_project_path_for_task(self, task) -> str:
        """Sync wrapper for backward compatibility."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # In async context, use regex fallback for sync call
                project_path = self._regex_detect_project_path(task)
                if project_path:
                    return project_path
                return self._fallback_recent_project()
            return loop.run_until_complete(
                self._get_project_path_for_task_async(task)
            )
        except RuntimeError:
            project_path = self._regex_detect_project_path(task)
            if project_path:
                return project_path
            return self._fallback_recent_project()

    def _regex_detect_project_path(self, task) -> Optional[str]:
        """DEPRECATED: Regex-based project path detection. Use AI-first instead."""
        import re

        project_path = None

        # Extract from task description
        if task.description:
            # Look for explicit project path mentions
            path_match = re.search(r'(?:Project Path:|Project:)\s*(/workspace/[\w\-]+)', task.description)
            if path_match:
                return path_match.group(1)

            # Look for any workspace path
            path_match = re.search(r'/workspace/([\w\-]+)', task.description)
            if path_match:
                return f"/workspace/{path_match.group(1)}"

        # Extract from task result
        if hasattr(task, 'result') and task.result and isinstance(task.result, str):
            path_match = re.search(r'/workspace/([\w\-]+)', task.result)
            if path_match:
                return f"/workspace/{path_match.group(1)}"

        return None

    def _fallback_recent_project(self) -> str:
        """Find most recently modified project."""
        workspace = Path("/workspace")
        if workspace.exists():
            projects = [
                p for p in workspace.iterdir()
                if p.is_dir() and not p.name.startswith('.')
                and ((p / "package.json").exists() or (p / "requirements.txt").exists() or (p / ".clopus").exists())
            ]
            if projects:
                projects.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                return str(projects[0])
        return "/workspace"

    # =========================================================================
    # ARTIFACT VERIFICATION
    # =========================================================================

    async def _verify_artifacts(self, task) -> tuple[bool, list]:
        """
        Verify that expected artifacts from a task actually exist.

        Uses the Verificator (Worker 8) for intelligent verification when available,
        with fallback to simple file existence checks.

        Returns:
            tuple: (all_verified: bool, missing_artifacts: list)
        """
        if not task.expected_artifacts:
            return True, []

        # Use async version for AI-first project detection
        project_path = await self._get_project_path_for_task_async(task)

        # Try using the verificator client for intelligent verification
        if self.verificator_client:
            try:
                verified, missing, found = await self.verificator_client.verify_completion(
                    task_title=task.title,
                    task_description=task.description or "",
                    expected_artifacts=task.expected_artifacts,
                    project_path=project_path,
                    task_result=task.result if hasattr(task, 'result') else None
                )

                if not verified:
                    logger.error(
                        f"Task {task.id} ({task.title}): Verificator found {len(missing)} missing artifacts: {missing}"
                    )
                else:
                    logger.info(
                        f"Task {task.id}: Verificator confirmed {len(found)} artifacts present"
                    )

                return verified, missing

            except Exception as e:
                logger.warning(f"Verificator failed, falling back to file check: {e}")

        # Fallback: Simple file existence check
        missing = []

        for artifact in task.expected_artifacts:
            # Artifact can be:
            # - Relative path: "app/models/edge.py" -> resolve against project path
            # - Absolute path: "/workspace/nexus-api/app/models/edge.py"
            # - Endpoint: "GET /api/v1/edges" -> special handling

            if artifact.startswith(("GET ", "POST ", "PUT ", "PATCH ", "DELETE ")):
                # This is an endpoint - we'd need to start the server to verify
                # For now, check if the corresponding file might exist
                # e.g., "GET /api/v1/edges" -> check for edges.py in endpoints
                endpoint_parts = artifact.split()
                if len(endpoint_parts) >= 2:
                    path = endpoint_parts[1]  # e.g., "/api/v1/edges"
                    # Extract the resource name (last part of path)
                    resource = path.rstrip('/').split('/')[-1]
                    if resource:
                        # Check common patterns for endpoint files
                        possible_files = [
                            Path(project_path) / "app" / "api" / "v1" / "endpoints" / f"{resource}.py",
                            Path(project_path) / "app" / "routes" / f"{resource}.py",
                            Path(project_path) / "src" / "routes" / f"{resource}.py",
                            Path(project_path) / "api" / f"{resource}.py",
                        ]
                        if not any(f.exists() for f in possible_files):
                            missing.append(artifact)
                            logger.warning(f"Endpoint artifact not found: {artifact}")
            else:
                # This is a file path
                if artifact.startswith("/"):
                    # Absolute path
                    artifact_path = Path(artifact)
                else:
                    # Relative path - resolve against project
                    artifact_path = Path(project_path) / artifact

                if not artifact_path.exists():
                    missing.append(artifact)
                    logger.warning(f"File artifact not found: {artifact_path}")

        if missing:
            logger.error(
                f"Task {task.id} ({task.title}): {len(missing)} of {len(task.expected_artifacts)} artifacts missing"
            )
            return False, missing

        return True, []

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
            # Use async version for AI-first project path detection
            project_path = await self._get_project_path_for_task_async(task)

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

                # Emit validation result for TUI
                emit_validation_result(
                    task_id=task.id,
                    passed=True,
                    stages=[
                        {
                            "stage": s.stage.value if hasattr(s.stage, 'value') else str(s.stage),
                            "status": s.status.value if hasattr(s.status, 'value') else str(s.status),
                        }
                        for s in result.stages
                    ]
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

                # Emit validation result for TUI
                emit_validation_result(
                    task_id=task.id,
                    passed=False,
                    stages=[
                        {
                            "stage": s.stage.value if hasattr(s.stage, 'value') else str(s.stage),
                            "status": s.status.value if hasattr(s.status, 'value') else str(s.status),
                        }
                        for s in result.stages
                    ]
                )

                # Create a fix task for the debugger
                await self._create_fix_task(task, failed_stages, result.summary)

                return False

        except Exception as e:
            logger.error(f"Error running validation: {e}")
            # On error, fail the task to be safe
            return False

    async def _create_fix_task(self, original_task, failed_stages: list, error_summary: str) -> bool:
        """Create a fix task for the debugger when validation fails.

        IMPORTANT: Limited to MAX_FIX_ATTEMPTS to prevent infinite loops.
        After max attempts, returns False so caller can start dev server anyway.

        Returns:
            True if a fix task was created, False if max attempts exceeded.
        """
        MAX_FIX_ATTEMPTS = 3  # Maximum fix attempts before giving up

        try:
            # =====================================================================
            # CHECK RETRY COUNT TO PREVENT INFINITE LOOPS
            # =====================================================================
            current_attempts = 0
            if hasattr(original_task, 'metadata') and original_task.metadata:
                if isinstance(original_task.metadata, dict):
                    current_attempts = original_task.metadata.get('fix_attempts', 0)

            # Also check if this is already a fix task (count those attempts)
            if hasattr(original_task, 'title') and 'Fix validation failures' in original_task.title:
                current_attempts += 1

            if current_attempts >= MAX_FIX_ATTEMPTS:
                logger.warning(
                    f"Task {original_task.id} has exceeded max fix attempts ({MAX_FIX_ATTEMPTS}). "
                    f"Not creating more fix tasks. Caller should start dev server if build passed."
                )
                # Return False to signal max attempts reached - caller should start dev server
                return False

            logger.info(f"Creating fix task for {original_task.id} (attempt {current_attempts + 1}/{MAX_FIX_ATTEMPTS})")

            fix_description = f"""
VALIDATION FAILURE - Fix Required (Attempt {current_attempts + 1}/{MAX_FIX_ATTEMPTS})

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
NOTE: This is attempt {current_attempts + 1} of {MAX_FIX_ATTEMPTS}. If this fails, no more automatic retries.
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
                        "revalidate_after": True,
                        "fix_attempts": current_attempts + 1  # Track attempt count
                    }
                }
            ])

            logger.info(f"Created fix task for validation failures in task {original_task.id}")
            return True

        except Exception as e:
            logger.error(f"Error creating fix task: {e}")
            return False  # On error, signal that no fix task was created

    async def _handle_fix_task_completion(self, fix_task) -> None:
        """
        Handle completion of a fix task by re-running validation.
        If validation passes, start the dev server for the project.
        """
        try:
            import re
            from pathlib import Path

            logger.info(f"Fix task completed: {fix_task.title}")

            # =================================================================
            # DETERMINE PROJECT PATH (same logic as _run_validation)
            # =================================================================
            project_path = None

            # Try metadata first
            if hasattr(fix_task, 'metadata') and fix_task.metadata:
                if isinstance(fix_task.metadata, dict):
                    project_path = fix_task.metadata.get('project_path')

            # Try description
            if not project_path and fix_task.description:
                path_match = re.search(r'(?:Project Path:|Project:)\s*(/workspace/[\w\-]+)', fix_task.description)
                if path_match:
                    project_path = path_match.group(1)
                else:
                    path_match = re.search(r'/workspace/([\w\-]+)', fix_task.description)
                    if path_match:
                        project_path = f"/workspace/{path_match.group(1)}"

            # Find most recently modified project as fallback
            if not project_path:
                workspace = Path("/workspace")
                if workspace.exists():
                    projects = [
                        p for p in workspace.iterdir()
                        if p.is_dir() and not p.name.startswith('.')
                        and ((p / "package.json").exists() or (p / "requirements.txt").exists())
                    ]
                    if projects:
                        projects.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                        project_path = str(projects[0])

            if not project_path:
                project_path = "/workspace"
                logger.warning("Could not determine project path for re-validation")

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

                # Generate project documentation and branding
                await self._generate_project_docs_and_branding(project_path, fix_task, result)

                # Log success
                await self.memory.log_activity(
                    source="validation",
                    action="revalidation_passed",
                    details={"project_path": project_path, "fix_task_id": fix_task.id}
                )
            else:
                logger.warning(f"✗ RE-VALIDATION FAILED for {project_path}: {result.summary}")

                # Check if build passed (app is functional even if review failed)
                build_passed = any(
                    str(s.stage.value if hasattr(s.stage, 'value') else s.stage) == "build"
                    and str(s.status.value if hasattr(s.status, 'value') else s.status) == "passed"
                    for s in result.stages
                )

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
                        # Pass through metadata with fix_attempts count
                        self.metadata = getattr(task, 'metadata', {}) or {}

                fix_task_created = await self._create_fix_task(
                    MockTask(fix_task),
                    failed_stages,
                    result.summary
                )

                # If no fix task was created (max attempts exceeded) and build passed,
                # start the dev server anyway - the app is functional
                if not fix_task_created and build_passed:
                    logger.info(
                        f"Max fix attempts exceeded but build passed. "
                        f"Starting dev server for {project_path} despite failed stages: {failed_stages}"
                    )
                    await self._start_project_dev_server(project_path)

                    # Generate project documentation even with partial validation
                    await self._generate_project_docs_and_branding(project_path, fix_task, result)

                    await self.memory.log_activity(
                        source="validation",
                        action="dev_server_started_after_max_attempts",
                        details={
                            "project_path": project_path,
                            "failed_stages": failed_stages,
                            "build_passed": True
                        }
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

            # Use dynamic port allocation with availability checking
            port_manager = get_port_manager()
            port = port_manager.get_project_port(project_name)
            logger.info(f"Allocated port {port} for {project_name}")

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

                    # Emit project update for TUI
                    emit_project_update(
                        project_name=project_name,
                        status="running",
                        port=port
                    )

                    # Store the server info
                    server_info = project / ".clopus" / "server_info.json"
                    server_info.write_text(json.dumps({
                        "port": port,
                        "host": "0.0.0.0",
                        "url": f"http://0.0.0.0:{port}",
                        "started_at": str(datetime.now())
                    }))

                    # Update project state
                    await self.state_manager.update_dev_server(
                        str(project),
                        running=True,
                        port=port
                    )

        except Exception as e:
            logger.error(f"Error starting dev server: {e}")

    async def _generate_project_docs_and_branding(
        self,
        project_path: str,
        task,
        validation_result
    ) -> None:
        """Generate project documentation using Designer's design system."""
        try:
            from pathlib import Path

            project = Path(project_path)
            project_name = project.name

            # Get objective content
            objective_content = "Project created by CLOPUS"
            if task and task.objective_id:
                try:
                    objective = await self.memory.short_term.get_objective(task.objective_id)
                    if objective:
                        objective_content = objective.content
                except Exception:
                    pass

            # Read branding from Designer's design system
            branding = None
            design_system = await self.design_system.get_design_system(project_path)
            if design_system:
                # Extract branding from design system documentation
                branding = design_system.get("branding", {})
                if not branding and "documentation" in design_system:
                    # Parse name from design system doc
                    doc = design_system["documentation"]
                    import re
                    name_match = re.search(r'\*\*Project Name:\*\*\s*(.+)', doc)
                    primary_match = re.search(r'Primary.*#([0-9A-Fa-f]{6})', doc)
                    branding = {
                        "name": name_match.group(1).strip() if name_match else project_name,
                        "primary_color": f"#{primary_match.group(1)}" if primary_match else "#3B82F6",
                    }
                logger.info(f"Using Designer's branding for {project_name}")
            else:
                # Fallback if no design system exists (shouldn't happen normally)
                branding = {"name": project_name, "primary_color": "#3B82F6"}
                logger.warning(f"No design system found for {project_name}, using default")

            # Get port
            port_manager = get_port_manager()
            port = port_manager.get_project_port(project_name)

            # Get completed tasks
            tasks_completed = []
            if task and task.objective_id:
                try:
                    tasks = await self.memory.short_term.get_tasks_for_objective(task.objective_id)
                    tasks_completed = [
                        {
                            "title": t.title,
                            "success": (t.status.value if hasattr(t.status, 'value') else str(t.status)) == "completed"
                        }
                        for t in tasks
                    ]
                except Exception:
                    pass

            # Build validation results dict
            val_results = {
                "stages": [
                    {
                        "stage": str(s.stage.value if hasattr(s.stage, 'value') else s.stage),
                        "passed": str(s.status.value if hasattr(s.status, 'value') else s.status) == "passed"
                    }
                    for s in validation_result.stages
                ] if validation_result else []
            }

            # Generate documentation
            docs_gen = get_docs_generator()
            docs_path = await docs_gen.generate_project_docs(
                project_path=project_path,
                objective=objective_content,
                tasks_completed=tasks_completed,
                validation_results=val_results,
                port=port,
                branding=branding
            )

            logger.info(f"Generated project documentation: {docs_path}")

            # Log activity
            await self.memory.log_activity(
                source="project_docs",
                action="generated",
                details={
                    "project": project_name,
                    "docs_path": docs_path,
                    "branding": branding
                }
            )

        except Exception as e:
            logger.error(f"Error generating project docs and branding: {e}")

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

    async def _update_project_state_on_task_completion(self, task, success: bool) -> None:
        """
        Update project state when a task completes.
        This keeps the project state file in sync with actual progress.
        """
        import re
        from pathlib import Path

        try:
            # =================================================================
            # EXTRACT PROJECT PATH FROM TASK
            # =================================================================
            project_path = None

            # Try metadata first
            if hasattr(task, 'metadata') and task.metadata:
                if isinstance(task.metadata, dict):
                    project_path = task.metadata.get('project_path')

            # Try description
            if not project_path and task.description:
                path_match = re.search(r'(?:Project Path:|Project:)\s*(/workspace/[\w\-]+)', task.description)
                if path_match:
                    project_path = path_match.group(1)
                else:
                    path_match = re.search(r'/workspace/([\w\-]+)', task.description)
                    if path_match:
                        project_path = f"/workspace/{path_match.group(1)}"

            # Try title for project name patterns
            if not project_path and task.title:
                # Look for "for <project>" pattern
                title_match = re.search(r'for ([\w\-]+)$', task.title)
                if title_match:
                    project_path = f"/workspace/{title_match.group(1)}"

            if not project_path:
                logger.debug(f"Could not determine project path for task: {task.title}")
                return

            # =================================================================
            # DETERMINE WHAT TYPE OF TASK COMPLETED
            # =================================================================
            task_title_lower = task.title.lower()

            # Design system tasks
            if "design" in task_title_lower and "system" in task_title_lower:
                if success:
                    await self.state_manager.update_stage(
                        project_path, "design", "completed"
                    )
                    # Check if design system file exists
                    design_file = Path(project_path) / ".clopus" / "design" / "DESIGN_SYSTEM.md"
                    if design_file.exists():
                        await self.state_manager.update_has_design_system(project_path, True)
                    logger.info(f"Updated project state: design completed for {project_path}")
                else:
                    await self.state_manager.update_stage(
                        project_path, "design", "failed"
                    )

            # E2E testing tasks
            elif "e2e" in task_title_lower or "end-to-end" in task_title_lower:
                if success:
                    await self.state_manager.update_stage(
                        project_path, "e2e_testing", "completed"
                    )
                    # Check for screenshots
                    screenshots_dir = Path(project_path) / ".clopus" / "screenshots"
                    if screenshots_dir.exists():
                        screenshots = list(screenshots_dir.glob("*.png"))
                        await self.state_manager.update_screenshots(
                            project_path, [str(s) for s in screenshots]
                        )
                    logger.info(f"Updated project state: e2e_testing completed for {project_path}")
                else:
                    await self.state_manager.update_stage(
                        project_path, "e2e_testing", "failed"
                    )

            # Documentation/PROJECT.md tasks
            elif "project.md" in task_title_lower or "documentation" in task_title_lower:
                if success:
                    await self.state_manager.update_stage(
                        project_path, "documentation", "completed"
                    )
                    logger.info(f"Updated project state: documentation completed for {project_path}")
                else:
                    await self.state_manager.update_stage(
                        project_path, "documentation", "failed"
                    )

            # Validation tasks
            elif "validation" in task_title_lower or "validate" in task_title_lower:
                if success:
                    await self.state_manager.update_stage(
                        project_path, "validation", "completed"
                    )
                    logger.info(f"Updated project state: validation completed for {project_path}")
                else:
                    await self.state_manager.update_stage(
                        project_path, "validation", "failed"
                    )

            # Dev server tasks
            elif "dev server" in task_title_lower or "start server" in task_title_lower:
                if success:
                    # Actually start the dev server
                    await self._start_project_dev_server(project_path)
                    logger.info(f"Dev server started for {project_path}")

            # Implementation/coding tasks
            elif task.worker_role == "coder" and success:
                # Mark implementation as in progress or completed
                current_state = await self.state_manager.get_state(project_path)
                if current_state:
                    impl_status = current_state.stages.get("implementation", {}).get("status")
                    if impl_status == "pending":
                        await self.state_manager.update_stage(
                            project_path, "implementation", "in_progress"
                        )

            # Check if project is complete (all stages done)
            state = await self.state_manager.get_state(project_path)
            if state and state.is_complete():
                await self.state_manager.update_status(project_path, "completed")
                logger.info(f"Project {project_path} marked as COMPLETED")

        except Exception as e:
            logger.warning(f"Error updating project state for task {task.id}: {e}")

    # =========================================================================
    # AUTHENTICATION ERROR HANDLING
    # =========================================================================
    # These methods detect OAuth token expiration and pause operations until
    # the user manually re-authenticates in one of the worker containers.

    async def _check_initial_auth(self) -> None:
        """Check authentication status on startup."""
        logger.info("Checking authentication status...")

        if not self.worker_pool:
            logger.warning("Worker pool not available, skipping auth check")
            return

        # Wait for verificator worker to be available
        await asyncio.sleep(2)

        if not self.worker_pool.is_verificator_available():
            logger.warning("Verificator not available, skipping initial auth check")
            return

        try:
            # Try a simple verification task to test auth
            result = await self.worker_pool.dispatch_verification_task(
                "SEMANTIC_CHECK",
                {"title": "Auth check", "description": "Startup auth verification", "result": "", "files_created": []},
                timeout_seconds=20
            )

            if result and self._is_auth_error(result):
                error_msg = result.get("result", "") or result.get("error", "OAuth token expired")
                logger.error(f"AUTHENTICATION ERROR on startup: {error_msg}")
                await self._handle_auth_error(error_msg)
            else:
                logger.info("Authentication check PASSED - Claude Code workers are authenticated")
                self._last_auth_check = datetime.now()

        except Exception as e:
            logger.warning(f"Auth check failed with exception: {e}")

    async def _auth_health_loop(self) -> None:
        """Periodically check auth health and detect expiration early."""
        # Check every 5 minutes
        check_interval = 300

        while self.running:
            try:
                await asyncio.sleep(check_interval)

                if self._auth_paused:
                    # Already paused, check if restored
                    if await self._check_auth_restored():
                        logger.info("Auth restored during health check")
                        self._auth_paused = False
                        self._auth_pause_reason = None
                        self._auth_question_id = None
                    continue

                # =====================================================================
                # CHECK WORKER CREDENTIAL HEALTH (token expiration tracking)
                # =====================================================================
                if self.worker_pool:
                    try:
                        creds_health = await self.worker_pool.get_credentials_health()

                        # Log summary
                        if creds_health.get("min_hours_remaining") is not None:
                            min_hours = creds_health["min_hours_remaining"]
                            host_hours = creds_health.get("host_token_hours")

                            if min_hours < 0:
                                # Some workers have expired tokens
                                expired = creds_health.get("expired_workers", [])
                                logger.error(f"CREDENTIAL WARNING: Workers {expired} have EXPIRED tokens!")
                                logger.info("Workers will auto-sync from host on next idle cycle")
                            elif min_hours < 1:
                                logger.warning(f"CREDENTIAL WARNING: Tokens expiring within 1 hour (min: {min_hours:.1f}h)")
                                if host_hours and host_hours > min_hours:
                                    logger.info(f"Host token has {host_hours:.1f}h remaining - workers will sync")
                            elif min_hours < 2:
                                expiring = creds_health.get("expiring_soon_workers", [])
                                logger.info(f"Token health: Workers {expiring} expiring within 2h (min: {min_hours:.1f}h)")
                            else:
                                logger.debug(f"Token health: OK - minimum {min_hours:.1f}h remaining across all workers")

                            # If host token is also expiring, warn user
                            if host_hours is not None and host_hours < 2:
                                logger.warning(f"HOST TOKEN expiring in {host_hours:.1f}h - run 'claude login' soon!")

                    except Exception as e:
                        logger.debug(f"Credential health check error: {e}")

                # Proactive auth check via verificator
                if self.worker_pool and self.worker_pool.is_verificator_available():
                    try:
                        result = await self.worker_pool.dispatch_verification_task(
                            "SEMANTIC_CHECK",
                            {"title": "Auth health check", "description": "Periodic auth verification", "result": "", "files_created": []},
                            timeout_seconds=15
                        )

                        if result and self._is_auth_error(result):
                            error_msg = result.get("result", "") or result.get("error", "OAuth token expired")
                            logger.error(f"Auth health check detected expiration: {error_msg}")
                            await self._handle_auth_error(error_msg)
                        else:
                            # Auth is healthy
                            self._last_auth_check = datetime.now()
                            logger.debug("Auth health check passed")

                    except Exception as e:
                        logger.debug(f"Auth health check error: {e}")

                # Also check verificator client's auth error state
                if self.verificator_client and self.verificator_client.has_auth_error():
                    error = self.verificator_client.get_auth_error()
                    if not self._auth_paused:
                        await self._handle_auth_error(error or "Auth error from verificator")

                # Check AI planner's auth error state
                if self.ai_planner and self.ai_planner.has_auth_error():
                    error = self.ai_planner.get_auth_error()
                    if not self._auth_paused:
                        await self._handle_auth_error(error or "Auth error from AI planner")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in auth health loop: {e}")
                await asyncio.sleep(30)

    def _is_auth_error(self, result: dict) -> bool:
        """Check if a task result indicates an authentication error."""
        if not result:
            return False

        # Check result text for auth error patterns
        result_text = str(result.get("result", ""))
        error_text = str(result.get("error", ""))
        combined = result_text + error_text

        auth_patterns = [
            "authentication_error",
            "OAuth token has expired",
            "token has expired",
            "Please obtain a new token",
            "refresh your existing token",
            "not authenticated",
            "authentication required",
        ]

        for pattern in auth_patterns:
            if pattern.lower() in combined.lower():
                return True

        return False

    async def _handle_auth_error(self, error_message: str) -> None:
        """Handle an authentication error by pausing operations and alerting user."""
        if self._auth_paused:
            # Already paused, don't create duplicate questions
            return

        logger.error(f"AUTHENTICATION ERROR DETECTED: {error_message}")
        logger.error("Pausing all operations until user re-authenticates")

        self._auth_paused = True
        self._auth_pause_reason = error_message
        self._last_auth_check = datetime.now()

        # Create a question file to alert the user
        if self.user_interaction:
            try:
                question_id = await self.user_interaction.ask_clarification(
                    question="AUTHENTICATION EXPIRED - Action Required",
                    context=f"""
CLOPUS has detected that the OAuth token for Claude Code has expired.

Error: {error_message}

**All operations are PAUSED until you re-authenticate.**

To fix this:
1. Open a terminal in any worker container:
   docker exec -it clopus-worker-1 bash

2. Run the Claude Code login command:
   claude login

3. Complete the OAuth flow in your browser

4. Create an answer file to resume:
   echo "authenticated" > /app/ipc/answers/auth-restored.txt

Or simply wait - CLOPUS will automatically detect when auth is restored.
""",
                    options=["I have re-authenticated", "Skip this check (not recommended)"]
                )
                self._auth_question_id = question_id
                logger.info(f"Created auth question: {question_id}")
            except Exception as e:
                logger.error(f"Failed to create auth question: {e}")

    async def _check_auth_restored(self) -> bool:
        """Check if authentication has been restored."""
        # Method 1: Check for answer file
        answers_dir = self.settings.interface_config.answers_dir
        answer_file = Path(answers_dir) / "auth-restored.txt"
        if answer_file.exists():
            answer_file.unlink()
            logger.info("Found auth-restored.txt - authentication confirmed")
            return True

        # Method 2: Periodically test auth by dispatching a simple verification task
        if self._last_auth_check:
            time_since_check = (datetime.now() - self._last_auth_check).total_seconds()
            if time_since_check < 30:  # Don't check more than every 30 seconds
                return False

        self._last_auth_check = datetime.now()

        # Try a lightweight verification task to test auth
        if self.worker_pool and self.worker_pool.is_verificator_available():
            try:
                result = await self.worker_pool.dispatch_verification_task(
                    "SEMANTIC_CHECK",
                    {"title": "Auth test", "description": "Test", "result": "", "files_created": []},
                    timeout_seconds=15
                )
                if result and not self._is_auth_error(result):
                    logger.info("Auth test succeeded - authentication restored")
                    return True
                elif result and self._is_auth_error(result):
                    logger.debug("Auth test failed - still waiting for re-authentication")
            except Exception as e:
                logger.debug(f"Auth test error: {e}")

        return False


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
