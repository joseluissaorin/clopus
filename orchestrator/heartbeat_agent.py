# =============================================================================
# CLOPUS v3 Heartbeat Agent (Completion Guardian)
# =============================================================================
"""
The Heartbeat Agent is a periodic supervisor that ensures projects actually
meet their objectives. It uses Claude Code workers (via OAuth) to:

1. Parse objectives into concrete requirements
2. Assess current project state vs requirements
3. Identify gaps between promises and reality
4. Spawn new tasks to fill gaps
5. Run integration tests for multi-project objectives
6. Enforce all 8 validation phases before marking complete

This is the "little voice in the head" that asks:
"Did we actually build what we promised?"

NOTE: This agent does NOT use the Anthropic API directly. Instead, it
dispatches analysis tasks to Claude Code workers that use OAuth authentication.
"""

import asyncio
import json
import re
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass, field
import logging

from .project_state import ProjectState, ProjectStateManager, get_state_manager
from .memory_client import MemoryClient
from .shared_context import SharedContextManager, get_shared_context
from .verificator_client import VerificatorClient, get_verificator_client
from .architectural_verifier import ArchitecturalVerifier, get_architectural_verifier
from .ai_first import AIFirstEngine, get_ai_engine

if TYPE_CHECKING:
    from .worker_pool import WorkerPool

logger = logging.getLogger("clopus.heartbeat")


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Requirement:
    """A concrete requirement extracted from an objective."""
    id: str
    description: str
    category: str  # api, frontend, database, integration, testing, etc.
    priority: str  # critical, high, medium, low
    verification_method: str  # file_exists, endpoint_works, test_passes, etc.
    verification_target: Optional[str] = None  # specific file, endpoint, etc.
    is_met: bool = False
    evidence: Optional[str] = None


@dataclass
class GapAnalysis:
    """Analysis of gaps between requirements and current state."""
    project_path: str
    objective_id: str
    objective_content: str
    requirements: List[Requirement] = field(default_factory=list)
    met_requirements: List[Requirement] = field(default_factory=list)
    unmet_requirements: List[Requirement] = field(default_factory=list)
    suggested_tasks: List[Dict] = field(default_factory=list)
    validation_gaps: List[str] = field(default_factory=list)
    integration_needed: bool = False
    integration_projects: List[str] = field(default_factory=list)
    overall_completion: float = 0.0
    analysis_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class IntegrationTestResult:
    """Result of integration testing between projects."""
    projects: List[str]
    tests_run: int
    tests_passed: int
    tests_failed: int
    failures: List[Dict] = field(default_factory=list)
    screenshots: List[str] = field(default_factory=list)
    passed: bool = False


# =============================================================================
# HEARTBEAT AGENT
# =============================================================================

class HeartbeatAgent:
    """
    Periodic supervisor that ensures projects meet their objectives.

    The Heartbeat Agent runs on a timer and uses Claude Code workers to:
    1. Analyze objectives and extract concrete requirements
    2. Compare requirements with actual project state
    3. Identify gaps and spawn tasks to fill them
    4. Run integration tests for multi-project objectives
    5. Enforce full 8-stage validation before completion

    NOTE: Uses OAuth-authenticated Claude Code workers, NOT the Anthropic API.
    """

    # Validation stages that must all pass
    REQUIRED_VALIDATION_STAGES = [
        "syntax", "lint", "build", "unit_tests",
        "integration_tests", "e2e_tests", "security", "review"
    ]

    def __init__(
        self,
        memory: MemoryClient,
        state_manager: ProjectStateManager,
        shared_context: SharedContextManager,
        worker_pool: Optional["WorkerPool"] = None,
        heartbeat_interval_seconds: int = 300,  # 5 minutes default
        workspace_path: str = "/workspace",
        ipc_path: str = "/app/ipc"
    ):
        self.memory = memory
        self.state_manager = state_manager
        self.shared_context = shared_context
        self.worker_pool = worker_pool
        self.heartbeat_interval = heartbeat_interval_seconds
        self.workspace = Path(workspace_path)
        self.ipc_path = Path(ipc_path)
        self.running = False
        self._last_analysis: Dict[str, GapAnalysis] = {}
        self._pending_analyses: Dict[str, asyncio.Event] = {}
        self._verificator_client: Optional[VerificatorClient] = None
        self._architectural_verifier: Optional[ArchitecturalVerifier] = None

    @property
    def verificator_client(self) -> Optional[VerificatorClient]:
        """Get the verificator client (lazily initialized from global)."""
        if self._verificator_client is None:
            self._verificator_client = get_verificator_client(self.worker_pool)
        return self._verificator_client

    @property
    def architectural_verifier(self) -> Optional[ArchitecturalVerifier]:
        """Get the architectural verifier (lazily initialized from global)."""
        if self._architectural_verifier is None:
            self._architectural_verifier = get_architectural_verifier(self.worker_pool)
        return self._architectural_verifier

    # =========================================================================
    # MAIN HEARTBEAT LOOP
    # =========================================================================

    async def start(self) -> None:
        """Start the heartbeat loop."""
        self.running = True
        logger.info(f"Heartbeat Agent started (interval: {self.heartbeat_interval}s)")

        while self.running:
            try:
                await self._heartbeat_cycle()
            except Exception as e:
                logger.error(f"Error in heartbeat cycle: {e}", exc_info=True)

            await asyncio.sleep(self.heartbeat_interval)

    async def stop(self) -> None:
        """Stop the heartbeat loop."""
        self.running = False
        logger.info("Heartbeat Agent stopped")

    async def _heartbeat_cycle(self) -> None:
        """
        One cycle of the heartbeat:
        1. Get all active objectives
        2. For each objective, analyze gaps
        3. Spawn tasks to fill gaps
        4. Check if integration testing needed
        5. Enforce validation completion
        """
        logger.info("=== HEARTBEAT CYCLE START ===")

        # Get active objectives (in_progress)
        objectives = await self._get_active_objectives()

        if not objectives:
            logger.info("No active objectives to monitor")
            return

        for objective in objectives:
            try:
                await self._analyze_and_remediate(objective)
            except Exception as e:
                logger.error(f"Error analyzing objective {objective.id}: {e}")

        logger.info("=== HEARTBEAT CYCLE END ===")

    async def _get_active_objectives(self) -> List[Any]:
        """Get all objectives that are in progress."""
        # Get from memory
        try:
            from memory.short_term import ObjectiveStatus
            objectives = await self.memory.short_term.get_objectives_by_status(
                ObjectiveStatus.IN_PROGRESS
            )
            return objectives
        except Exception as e:
            logger.error(f"Error getting active objectives: {e}")
            return []

    async def _retroactive_artifact_check(self, objective_id: str, project_path: str) -> None:
        """
        Check completed tasks that haven't been artifact-verified.

        This catches tasks that were marked complete before artifact verification
        was implemented, or that somehow bypassed verification.

        Uses the Verificator (Worker 8) for intelligent verification when available.
        """
        try:
            unverified = await self.memory.short_term.get_unverified_completed_tasks(objective_id)

            for task in unverified:
                if not task.expected_artifacts:
                    # No artifacts to verify, mark as verified
                    await self.memory.short_term.mark_artifacts_verified(task.id, True)
                    continue

                # Try using verificator for intelligent audit
                if self.verificator_client:
                    try:
                        passed, missing, recommendation = await self.verificator_client.audit_completed_task(
                            task_id=task.id,
                            task_title=task.title,
                            expected_artifacts=task.expected_artifacts,
                            project_path=project_path
                        )

                        if passed:
                            await self.memory.short_term.mark_artifacts_verified(task.id, True)
                            logger.info(f"Retroactive check (Verificator): Task {task.id} artifacts verified")
                        else:
                            logger.warning(
                                f"Retroactive check (Verificator): Task {task.id} missing artifacts: {missing}"
                            )
                            if recommendation == "re-run":
                                from memory.short_term import TaskStatus
                                await self.memory.short_term.update_task_status(
                                    task.id,
                                    TaskStatus.FAILED,
                                    error=f"Retroactive artifact check failed: missing {missing}"
                                )
                            else:
                                # Manual review or accept - log but don't fail
                                await self.memory.log_activity(
                                    source="heartbeat",
                                    action="artifact_check_needs_review",
                                    details={
                                        "task_id": task.id,
                                        "missing": missing,
                                        "recommendation": recommendation
                                    }
                                )
                        continue
                    except Exception as e:
                        logger.warning(f"Verificator audit failed, using fallback: {e}")

                # Fallback: Simple file existence check
                missing = []
                for artifact in task.expected_artifacts:
                    if artifact.startswith(("GET ", "POST ", "PUT ", "PATCH ", "DELETE ")):
                        # Endpoint - check for corresponding file
                        endpoint_parts = artifact.split()
                        if len(endpoint_parts) >= 2:
                            resource = endpoint_parts[1].rstrip('/').split('/')[-1]
                            if resource:
                                possible_files = [
                                    Path(project_path) / "app" / "api" / "v1" / "endpoints" / f"{resource}.py",
                                    Path(project_path) / "app" / "routes" / f"{resource}.py",
                                ]
                                if not any(f.exists() for f in possible_files):
                                    missing.append(artifact)
                    else:
                        # File path
                        if artifact.startswith("/"):
                            artifact_path = Path(artifact)
                        else:
                            artifact_path = Path(project_path) / artifact

                        if not artifact_path.exists():
                            missing.append(artifact)

                if missing:
                    # Artifacts missing - mark task as failed so it can be re-done
                    logger.warning(
                        f"Retroactive check: Task {task.id} ({task.title}) missing artifacts: {missing}"
                    )
                    from memory.short_term import TaskStatus
                    await self.memory.short_term.update_task_status(
                        task.id,
                        TaskStatus.FAILED,
                        error=f"Retroactive artifact check failed: missing {missing}"
                    )
                else:
                    # All artifacts present - mark as verified
                    await self.memory.short_term.mark_artifacts_verified(task.id, True)
                    logger.info(f"Retroactive check: Task {task.id} artifacts verified")

        except Exception as e:
            logger.error(f"Error in retroactive artifact check: {e}")

    async def _run_architectural_verification(self, objective, project_path: str) -> None:
        """
        Run architectural verification to detect semantic gaps.

        This uses Claude Code intelligence to detect issues like:
        - Database models exist but endpoints use in-memory storage
        - Auth is specified but not implemented
        - Redis caching is configured but not used

        Unlike regex-based checks, this actually READS the code and
        understands what it does.
        """
        if not self.architectural_verifier:
            logger.debug("Architectural verifier not available")
            return

        try:
            logger.info(f"Running architectural verification for: {project_path}")

            # Run full architectural verification
            gaps = await self.architectural_verifier.verify_project(project_path)

            if not gaps:
                logger.info("No architectural gaps detected")
                return

            logger.warning(f"Found {len(gaps)} architectural gaps")

            # Log the gaps
            for gap in gaps:
                logger.warning(
                    f"ARCHITECTURAL GAP [{gap.severity}]: {gap.requirement} "
                    f"(actual: {gap.actual_state})"
                )

            # Log activity
            await self.memory.log_activity(
                source="heartbeat",
                action="architectural_gaps_detected",
                details={
                    "objective_id": objective.id,
                    "project_path": project_path,
                    "gap_count": len(gaps),
                    "critical_count": len([g for g in gaps if g.severity == "critical"]),
                    "gaps": [
                        {
                            "requirement": g.requirement,
                            "actual_state": g.actual_state,
                            "severity": g.severity,
                            "category": g.category
                        }
                        for g in gaps
                    ]
                }
            )

            # Generate remediation tasks for critical/high gaps
            critical_high_gaps = [g for g in gaps if g.severity in ("critical", "high")]
            if critical_high_gaps:
                remediation_tasks = await self.architectural_verifier.generate_remediation_tasks(
                    critical_high_gaps, project_path
                )

                if remediation_tasks:
                    logger.info(f"Creating {len(remediation_tasks)} architectural remediation tasks")
                    await self.memory.create_tasks(objective.id, remediation_tasks)

                    await self.memory.log_activity(
                        source="heartbeat",
                        action="architectural_remediation_tasks_created",
                        details={
                            "objective_id": objective.id,
                            "task_count": len(remediation_tasks),
                            "task_titles": [t.get("title", "Unknown") for t in remediation_tasks]
                        }
                    )

        except Exception as e:
            logger.error(f"Error in architectural verification: {e}", exc_info=True)

    # =========================================================================
    # OBJECTIVE ANALYSIS (Claude-Powered)
    # =========================================================================

    async def _analyze_and_remediate(self, objective) -> None:
        """Analyze an objective and create tasks to fill gaps."""
        logger.info(f"Analyzing objective: {objective.content[:100]}...")

        # Find project path for this objective
        project_path = await self._find_project_for_objective(objective)
        if not project_path:
            logger.warning(f"No project found for objective {objective.id}")
            return

        # =================================================================
        # RETROACTIVE ARTIFACT CHECK
        # =================================================================
        # Check completed tasks that claim to have created artifacts but
        # haven't been verified. Mark them as failed if artifacts are missing.
        # This catches tasks from before artifact verification was implemented.
        await self._retroactive_artifact_check(objective.id, project_path)

        # =================================================================
        # ARCHITECTURAL VERIFICATION (Claude-Powered)
        # =================================================================
        # Uses Claude Code intelligence to detect semantic gaps like:
        # - Models exist but endpoints use in-memory storage
        # - Auth is specified but not actually implemented
        # - Caching is configured but never used
        await self._run_architectural_verification(objective, project_path)

        # Load project state
        state = await self.state_manager.get_state(project_path)
        if not state:
            state = await self.state_manager.create_state(
                project_path,
                objective.id,
                objective.content
            )

        # Use Claude to analyze gaps
        gap_analysis = await self._analyze_gaps_with_claude(
            objective,
            project_path,
            state
        )

        self._last_analysis[objective.id] = gap_analysis

        # Log analysis
        await self.memory.log_activity(
            source="heartbeat",
            action="gap_analysis",
            details={
                "objective_id": objective.id,
                "project_path": project_path,
                "completion": gap_analysis.overall_completion,
                "unmet_count": len(gap_analysis.unmet_requirements),
                "validation_gaps": gap_analysis.validation_gaps
            }
        )

        # Spawn tasks for unmet requirements
        if gap_analysis.unmet_requirements:
            await self._spawn_remediation_tasks(objective, gap_analysis)

        # Check if integration testing needed
        if gap_analysis.integration_needed:
            await self._run_integration_tests(gap_analysis)

        # Enforce validation completion
        if gap_analysis.validation_gaps:
            await self._enforce_validation(objective, project_path, gap_analysis)

        # Check for completion
        if gap_analysis.overall_completion >= 0.95 and not gap_analysis.validation_gaps:
            await self._check_completion_gate(objective, project_path, state)

    async def _find_project_for_objective(self, objective) -> Optional[str]:
        """
        Find the project path associated with an objective.

        Uses multiple strategies with priority:
        1. Explicit path in objective content (/workspace/xxx)
        2. Explicit path in objective metadata
        3. Project name matching from objective keywords
        4. Verificator-based intelligent matching (Claude-powered)
        5. Path from associated tasks
        6. Most recently modified project (fallback)
        """
        objective_lower = objective.content.lower()

        # Priority 1: Explicit path in objective content
        path_match = re.search(r'/workspace/([\w\-]+)', objective.content)
        if path_match:
            project_path = f"/workspace/{path_match.group(1)}"
            if Path(project_path).exists():
                return project_path

        # Priority 2: Metadata
        if objective.metadata and 'project_path' in objective.metadata:
            return objective.metadata['project_path']

        # Priority 3: Project name matching from objective keywords
        # Look for project names that match common patterns
        available_projects = []
        if self.workspace.exists():
            available_projects = [
                p for p in self.workspace.iterdir()
                if p.is_dir() and not p.name.startswith('.')
                and ((p / "package.json").exists() or (p / "requirements.txt").exists() or (p / ".clopus").exists())
            ]

        for project in available_projects:
            project_name = project.name.lower()

            # Check for direct name mention
            if project_name in objective_lower:
                logger.info(f"Matched project '{project.name}' from objective content")
                return str(project)

            # Check for common patterns based on project type indicators
            # Frontend patterns
            if any(x in objective_lower for x in ['react', 'frontend', 'web app', 'dashboard', 'ui']):
                if any(x in project_name for x in ['web', 'frontend', 'app', 'ui', 'client']):
                    if 'api' not in project_name and 'backend' not in project_name:
                        logger.info(f"Matched frontend project '{project.name}' from objective keywords")
                        return str(project)

            # Backend patterns
            if any(x in objective_lower for x in ['fastapi', 'backend', 'api server', 'rest api']):
                if any(x in project_name for x in ['api', 'backend', 'server', 'service']):
                    logger.info(f"Matched backend project '{project.name}' from objective keywords")
                    return str(project)

        # Priority 4: Verificator-based intelligent matching
        if self.verificator_client and available_projects:
            try:
                project_info = [
                    {
                        "path": str(p),
                        "name": p.name,
                        "has_package_json": (p / "package.json").exists(),
                        "has_requirements": (p / "requirements.txt").exists(),
                        "keywords": self._extract_project_keywords(p)
                    }
                    for p in available_projects
                ]
                matched_path, confidence = await self.verificator_client.match_project(
                    objective_content=objective.content,
                    available_projects=project_info
                )
                if matched_path and confidence > 0.6:
                    logger.info(f"Verificator matched project: {matched_path} (confidence: {confidence})")
                    return matched_path
            except Exception as e:
                logger.debug(f"Verificator project matching failed: {e}")

        # Priority 5: Look in task descriptions
        tasks = await self.memory.short_term.get_tasks_for_objective(objective.id)
        for task in tasks:
            if task.description:
                path_match = re.search(r'/workspace/([\w\-]+)', task.description)
                if path_match:
                    project_path = f"/workspace/{path_match.group(1)}"
                    if Path(project_path).exists():
                        return project_path

        # Priority 6: Fallback - Most recently modified project
        if available_projects:
            available_projects.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            logger.warning(
                f"Using fallback project detection (most recent): {available_projects[0].name}"
            )
            return str(available_projects[0])

        return None

    def _extract_project_keywords(self, project_path: Path) -> List[str]:
        """Extract keywords from a project for matching purposes."""
        keywords = []

        # From package.json
        package_json = project_path / "package.json"
        if package_json.exists():
            try:
                import json
                data = json.loads(package_json.read_text())
                if "name" in data:
                    keywords.append(data["name"])
                if "keywords" in data:
                    keywords.extend(data["keywords"])
                if "dependencies" in data:
                    deps = list(data["dependencies"].keys())[:5]
                    keywords.extend(deps)
            except Exception:
                pass

        # From requirements.txt
        requirements = project_path / "requirements.txt"
        if requirements.exists():
            try:
                lines = requirements.read_text().split('\n')[:5]
                for line in lines:
                    pkg = line.split('==')[0].split('>=')[0].strip()
                    if pkg:
                        keywords.append(pkg)
            except Exception:
                pass

        return keywords[:10]  # Limit to avoid too much data

    async def _analyze_gaps_with_claude(
        self,
        objective,
        project_path: str,
        state: ProjectState
    ) -> GapAnalysis:
        """
        Analyze gaps between objective and current state using a Claude Code worker.

        This dispatches an analysis task to an available worker (preferably researcher)
        and waits for the result. Uses OAuth authentication, NOT the Anthropic API.
        """

        # Gather current state information
        project_info = await self._gather_project_info(project_path)

        # Build the analysis prompt that will be sent to the worker
        analysis_prompt = f"""[HEARTBEAT GAP ANALYSIS]

Analyze this project and identify gaps between the objective and current implementation.

## OBJECTIVE
{objective.content}

## CURRENT PROJECT STATE
Project Path: {project_path}
Project Name: {state.project_name}
Status: {state.status}

### Files in Project
{project_info.get('files_summary', 'No files found')}

### API Endpoints (if backend)
{project_info.get('endpoints', 'No endpoints found')}

### Frontend Components (if frontend)
{project_info.get('components', 'No components found')}

### Test Coverage
{project_info.get('test_info', 'No test information')}

### Validation Status
Stages Passed: {state.validation.get('stages_passed', [])}
Stages Failed: {state.validation.get('stages_failed', [])}
Stages Pending: {state.validation.get('stages_pending', [])}

## REQUIRED OUTPUT
Write a JSON file to {project_path}/.clopus/heartbeat_analysis.json with:

```json
{{
  "requirements": [
    {{
      "id": "req_001",
      "description": "what needs to be built",
      "category": "api|frontend|database|integration|testing|documentation",
      "priority": "critical|high|medium|low",
      "verification_method": "file_exists|endpoint_works|test_passes",
      "verification_target": "specific file/endpoint",
      "is_met": true/false,
      "evidence": "proof if met"
    }}
  ],
  "suggested_tasks": [
    {{
      "title": "task title",
      "description": "detailed description",
      "priority": 1-10,
      "worker_role": "coder|tester|reviewer|debugger|designer|researcher"
    }}
  ],
  "validation_gaps": ["list", "of", "missing", "validation", "stages"],
  "integration_needed": true/false,
  "integration_projects": ["project1", "project2"],
  "overall_completion": 0.0-1.0
}}
```

Analyze carefully and be thorough. Check:
- Are all features from the objective implemented?
- Are there API endpoints for all required functionality?
- Are there tests for the critical paths?
- Is the frontend connected to the backend (if applicable)?
- Are all 8 validation stages passing?
"""

        # Try to dispatch to a worker or fall back to local analysis
        if self.worker_pool:
            try:
                return await self._dispatch_analysis_to_worker(
                    objective, project_path, state, analysis_prompt
                )
            except Exception as e:
                logger.warning(f"Worker dispatch failed, using local analysis: {e}")

        # Fallback: Do local analysis without Claude
        return await self._local_gap_analysis(objective, project_path, state, project_info)

    async def _dispatch_analysis_to_worker(
        self,
        objective,
        project_path: str,
        state: ProjectState,
        prompt: str
    ) -> GapAnalysis:
        """
        Dispatch gap analysis to the dedicated heartbeat worker.

        The heartbeat worker (worker-7) is reserved exclusively for heartbeat
        analysis tasks. It is never assigned regular tasks by the task planner.
        This ensures the heartbeat agent can always run its analysis without
        depending on other workers' availability.
        """

        # Always use the dedicated heartbeat worker
        worker_id = self.worker_pool.get_heartbeat_worker_id()

        if worker_id is None:
            logger.error("No dedicated heartbeat worker configured!")
            raise RuntimeError("No heartbeat worker available")

        # Check if heartbeat worker is available
        worker = self.worker_pool.workers.get(worker_id)
        if not worker:
            logger.error(f"Heartbeat worker {worker_id} not found in pool")
            raise RuntimeError("Heartbeat worker not in pool")

        # If the heartbeat worker is busy, wait for it to finish
        # Comprehensive analysis can take 5+ minutes for large projects
        max_wait = 300  # 5 minutes max wait
        wait_interval = 5
        waited = 0

        while worker.get("status") == "busy" and waited < max_wait:
            logger.info(f"Heartbeat worker busy, waiting... ({waited}/{max_wait}s)")
            await asyncio.sleep(wait_interval)
            waited += wait_interval
            # Collect any completed results to free up the worker
            await self.worker_pool.collect_results()

        if worker.get("status") != "idle":
            logger.warning(f"Heartbeat worker still busy after {max_wait}s wait")
            raise RuntimeError("Heartbeat worker timeout")

        # Create a unique task ID for this analysis
        task_id = f"heartbeat-{uuid.uuid4().hex[:8]}"

        # Dispatch the task
        await self.worker_pool.dispatch_task(
            worker_id=worker_id,
            task_id=task_id,
            title=f"Heartbeat analysis for {state.project_name}",
            description=prompt,
            cwd=project_path
        )

        logger.info(f"Dispatched gap analysis to worker {worker_id}")

        # Wait for result (with timeout)
        result_file = self.ipc_path / "tasks" / str(worker_id) / "result.json"
        analysis_file = Path(project_path) / ".clopus" / "heartbeat_analysis.json"

        # Comprehensive analysis takes time - allow 5 minutes for large projects
        timeout = 300  # 5 minutes
        start_time = datetime.now()

        while (datetime.now() - start_time).total_seconds() < timeout:
            # Check if worker completed the task
            if result_file.exists():
                try:
                    result_data = json.loads(result_file.read_text())
                    if result_data.get("task_id") == task_id:
                        # Task completed, check for analysis file
                        if analysis_file.exists():
                            return self._parse_analysis_file(
                                analysis_file, objective, project_path
                            )
                        break
                except json.JSONDecodeError:
                    pass

            await asyncio.sleep(2)

        # If we get here, check if analysis file was created anyway
        if analysis_file.exists():
            return self._parse_analysis_file(analysis_file, objective, project_path)

        logger.warning("Gap analysis task timed out or failed")
        raise RuntimeError("Analysis task timed out")

    def _parse_analysis_file(
        self,
        analysis_file: Path,
        objective,
        project_path: str
    ) -> GapAnalysis:
        """Parse the analysis file created by the worker."""
        try:
            analysis_data = json.loads(analysis_file.read_text())

            requirements = [
                Requirement(
                    id=r.get('id', f'req_{i}'),
                    description=r.get('description', ''),
                    category=r.get('category', 'other'),
                    priority=r.get('priority', 'medium'),
                    verification_method=r.get('verification_method', 'manual'),
                    verification_target=r.get('verification_target'),
                    is_met=r.get('is_met', False),
                    evidence=r.get('evidence')
                )
                for i, r in enumerate(analysis_data.get('requirements', []))
            ]

            met = [r for r in requirements if r.is_met]
            unmet = [r for r in requirements if not r.is_met]

            return GapAnalysis(
                project_path=project_path,
                objective_id=objective.id,
                objective_content=objective.content,
                requirements=requirements,
                met_requirements=met,
                unmet_requirements=unmet,
                suggested_tasks=analysis_data.get('suggested_tasks', []),
                validation_gaps=analysis_data.get('validation_gaps', []),
                integration_needed=analysis_data.get('integration_needed', False),
                integration_projects=analysis_data.get('integration_projects', []),
                overall_completion=analysis_data.get('overall_completion', 0.0)
            )

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse analysis file: {e}")
            return GapAnalysis(
                project_path=project_path,
                objective_id=objective.id,
                objective_content=objective.content
            )

    async def _local_gap_analysis(
        self,
        objective,
        project_path: str,
        state: ProjectState,
        project_info: Dict[str, Any]
    ) -> GapAnalysis:
        """
        Perform local gap analysis without Claude.
        Uses heuristics to identify obvious gaps.
        """
        logger.info("Performing local gap analysis (no worker available)")

        requirements = []
        suggested_tasks = []
        validation_gaps = []

        # Check validation stages
        stages_passed = state.validation.get('stages_passed', [])
        for stage in self.REQUIRED_VALIDATION_STAGES:
            if stage not in stages_passed:
                validation_gaps.append(stage)

        # Check for obvious missing pieces
        objective_lower = objective.content.lower()

        # Check for API endpoints mentioned in objective
        if 'api' in objective_lower or 'endpoint' in objective_lower or 'backend' in objective_lower:
            endpoints = project_info.get('endpoints', '')
            if 'No endpoints found' in endpoints or not endpoints:
                requirements.append(Requirement(
                    id='req_api',
                    description='API endpoints implementation',
                    category='api',
                    priority='critical',
                    verification_method='endpoint_works',
                    is_met=False
                ))
                suggested_tasks.append({
                    'title': 'Implement API endpoints',
                    'description': 'The objective mentions API/backend but no endpoints were found',
                    'priority': 2,
                    'worker_role': 'coder'
                })

        # Check for frontend components
        if 'frontend' in objective_lower or 'react' in objective_lower or 'ui' in objective_lower:
            components = project_info.get('components', '')
            if 'No components found' in components or not components:
                requirements.append(Requirement(
                    id='req_frontend',
                    description='Frontend components implementation',
                    category='frontend',
                    priority='critical',
                    verification_method='file_exists',
                    is_met=False
                ))
                suggested_tasks.append({
                    'title': 'Implement frontend components',
                    'description': 'The objective mentions frontend/UI but no components were found',
                    'priority': 2,
                    'worker_role': 'coder'
                })

        # Check for tests
        test_info = project_info.get('test_info', '')
        if '0 test files' in test_info or 'No test' in test_info:
            requirements.append(Requirement(
                id='req_tests',
                description='Test coverage',
                category='testing',
                priority='high',
                verification_method='test_passes',
                is_met=False
            ))
            suggested_tasks.append({
                'title': 'Add test coverage',
                'description': 'No test files found in the project',
                'priority': 3,
                'worker_role': 'tester'
            })

        # Check for integration (multi-project)
        integration_needed = False
        integration_projects = []
        linked = self.shared_context.get_linked_projects(state.project_name)
        if linked:
            integration_needed = True
            integration_projects = linked

        # Calculate completion
        total_stages = len(self.REQUIRED_VALIDATION_STAGES)
        passed_stages = len(stages_passed)
        overall_completion = passed_stages / total_stages if total_stages > 0 else 0.0

        met = [r for r in requirements if r.is_met]
        unmet = [r for r in requirements if not r.is_met]

        return GapAnalysis(
            project_path=project_path,
            objective_id=objective.id,
            objective_content=objective.content,
            requirements=requirements,
            met_requirements=met,
            unmet_requirements=unmet,
            suggested_tasks=suggested_tasks,
            validation_gaps=validation_gaps,
            integration_needed=integration_needed,
            integration_projects=integration_projects,
            overall_completion=overall_completion
        )

    async def _gather_project_info(self, project_path: str) -> Dict[str, Any]:
        """Gather information about the current project state."""
        project = Path(project_path)
        info = {}

        # Get file summary
        files = []
        for pattern in ["**/*.py", "**/*.ts", "**/*.tsx", "**/*.js", "**/*.jsx"]:
            files.extend([
                str(f.relative_to(project))
                for f in project.glob(pattern)
                if 'node_modules' not in str(f) and 'venv' not in str(f)
                and '__pycache__' not in str(f) and '.git' not in str(f)
            ])

        # Limit to first 50 files
        if len(files) > 50:
            info['files_summary'] = "\n".join(files[:50]) + f"\n... and {len(files) - 50} more files"
        else:
            info['files_summary'] = "\n".join(files) if files else "No source files found"

        # Check for API endpoints (Python/FastAPI)
        endpoints = []
        for py_file in project.rglob("*.py"):
            if 'venv' in str(py_file) or '__pycache__' in str(py_file):
                continue
            try:
                content = py_file.read_text()
                # Look for FastAPI route decorators
                route_matches = re.findall(
                    r'@(?:app|router)\.(get|post|put|patch|delete)\(["\']([^"\']+)["\']',
                    content
                )
                for method, path in route_matches:
                    endpoints.append(f"{method.upper()} {path}")
            except Exception:
                pass

        info['endpoints'] = "\n".join(endpoints) if endpoints else "No API endpoints found"

        # Check for React components
        components = []
        for tsx_file in project.rglob("*.tsx"):
            if 'node_modules' in str(tsx_file):
                continue
            try:
                content = tsx_file.read_text()
                # Look for function component exports
                comp_matches = re.findall(
                    r'(?:export\s+(?:default\s+)?function|const)\s+(\w+)',
                    content
                )
                for comp in comp_matches:
                    if comp[0].isupper():  # React components are capitalized
                        components.append(f"{tsx_file.stem}: {comp}")
            except Exception:
                pass

        info['components'] = "\n".join(components[:30]) if components else "No React components found"

        # Check test coverage
        test_files = list(project.rglob("*.test.*")) + list(project.rglob("*.spec.*"))
        test_files = [f for f in test_files if 'node_modules' not in str(f)]
        info['test_info'] = f"{len(test_files)} test files found"

        return info

    # =========================================================================
    # TASK SPAWNING
    # =========================================================================

    async def _spawn_remediation_tasks(
        self,
        objective,
        gap_analysis: GapAnalysis
    ) -> None:
        """Create tasks to address unmet requirements."""

        if not gap_analysis.suggested_tasks:
            # Generate tasks from unmet requirements
            for req in gap_analysis.unmet_requirements:
                gap_analysis.suggested_tasks.append({
                    'title': f"Implement: {req.description[:50]}",
                    'description': f"""
[HEARTBEAT REMEDIATION TASK]

Requirement: {req.description}
Category: {req.category}
Priority: {req.priority}

Verification Method: {req.verification_method}
Verification Target: {req.verification_target or 'N/A'}

Project Path: {gap_analysis.project_path}

Please implement this requirement and ensure it passes verification.
""",
                    'priority': {'critical': 1, 'high': 3, 'medium': 5, 'low': 7}.get(req.priority, 5),
                    'worker_role': self._get_worker_role_for_category(req.category)
                })

        # =================================================================
        # SMART TASK DEDUPLICATION
        # =================================================================
        # Key principle: Don't block re-creation of tasks for UNMET requirements
        # just because a previous attempt was marked "completed" but didn't
        # actually create the expected artifact.

        # Get all pending/assigned tasks globally (these are actively being worked on)
        all_pending = await self.memory.short_term.get_pending_tasks()

        # Get objective tasks, but only consider completed tasks if they have
        # verified artifacts - this prevents blocking re-creation of failed work
        objective_tasks = await self.memory.short_term.get_tasks_for_objective(objective.id)

        # Build set of titles we should NOT duplicate
        existing_titles = set()

        # All pending/assigned tasks block duplication (work in progress)
        for t in all_pending:
            existing_titles.add(t.title.lower())

        # For objective tasks, only block on VERIFIED completed tasks
        # Unverified completed tasks should NOT block - they claimed completion
        # but didn't actually deliver the artifact
        for t in objective_tasks:
            status_val = t.status.value if hasattr(t.status, 'value') else str(t.status)
            if status_val in ('pending', 'assigned', 'in_progress'):
                existing_titles.add(t.title.lower())
            elif status_val == 'completed':
                # Only block if artifacts were verified (or no artifacts expected)
                if t.artifacts_verified or not t.expected_artifacts:
                    existing_titles.add(t.title.lower())
                else:
                    # Completed but unverified - don't block, log warning
                    logger.warning(
                        f"Ignoring unverified completed task for dedup: {t.title}"
                    )

        # Helper function for fuzzy title matching (with semantic fallback via verificator)
        async def is_duplicate(new_title: str, new_description: str = "") -> bool:
            new_lower = new_title.lower()
            # Extract key terms (remove common prefixes)
            new_key = new_lower.replace('implement:', '').replace('implement ', '').strip()
            new_key = new_key.replace('write ', '').replace('create ', '').replace('add ', '').strip()

            for existing in existing_titles:
                # Direct match
                if new_lower == existing:
                    return True
                # Substring match (either direction)
                if new_key in existing or existing in new_lower:
                    return True
                # Key term overlap (at least 60% of words match)
                new_words = set(new_key.split())
                existing_words = set(existing.split())
                if new_words and existing_words:
                    overlap = len(new_words & existing_words)
                    if overlap >= 0.6 * min(len(new_words), len(existing_words)):
                        return True

            # If no word-based match, try semantic check via verificator (for edge cases)
            if self.verificator_client and new_description:
                try:
                    # Check against the most similar-looking existing tasks
                    for existing in list(existing_titles)[:5]:  # Limit to avoid too many checks
                        is_dup, confidence = await self.verificator_client.check_duplicate(
                            task1_title=new_title,
                            task1_description=new_description,
                            task2_title=existing,
                            task2_description=""  # We don't have description for existing
                        )
                        if is_dup and confidence > 0.7:
                            logger.debug(f"Semantic duplicate found: '{new_title}' ~ '{existing}' (conf: {confidence})")
                            return True
                except Exception as e:
                    logger.debug(f"Semantic duplicate check failed: {e}")

            return False

        tasks_to_create = []
        for task in gap_analysis.suggested_tasks:
            # Use async duplicate check with semantic verification
            is_dup = await is_duplicate(task['title'], task.get('description', ''))
            if not is_dup:
                # Use verificator to specify artifacts, falling back to regex inference
                expected_artifacts = await self._infer_expected_artifacts(
                    task.get('title', ''),
                    task.get('description', ''),
                    gap_analysis.project_path
                )
                task['expected_artifacts'] = expected_artifacts
                tasks_to_create.append(task)
            else:
                logger.debug(f"Skipping duplicate task: {task['title']}")

        if tasks_to_create:
            logger.info(f"Spawning {len(tasks_to_create)} remediation tasks for objective {objective.id}")
            await self.memory.create_tasks(objective.id, tasks_to_create)

            await self.memory.log_activity(
                source="heartbeat",
                action="tasks_spawned",
                details={
                    "objective_id": objective.id,
                    "task_count": len(tasks_to_create),
                    "task_titles": [t['title'] for t in tasks_to_create]
                }
            )

    def _get_worker_role_for_category(self, category: str) -> str:
        """Map requirement category to worker role."""
        mapping = {
            'api': 'coder',
            'frontend': 'coder',
            'database': 'coder',
            'integration': 'tester',
            'testing': 'tester',
            'documentation': 'coder',
            'design': 'designer',
            'research': 'researcher',
            'debugging': 'debugger',
            'review': 'reviewer'
        }
        return mapping.get(category.lower(), 'coder')

    async def _infer_expected_artifacts(
        self,
        title: str,
        description: str,
        project_path: str
    ) -> list:
        """
        Infer expected artifacts from task title and description.

        NEW IN v3.2: AI-First approach
        Priority:
        1. AI-First Engine (semantic understanding)
        2. Verificator (Worker 8) for intelligent artifact specification
        3. Regex-based inference (deprecated, last resort)

        This enables artifact verification - tasks that claim to create files
        must actually create them.
        """
        # Priority 1: Try AI-First Engine
        ai_engine = get_ai_engine()
        if ai_engine:
            try:
                result = await ai_engine.infer_artifacts(
                    task_title=title,
                    task_description=description,
                    project_context={"path": project_path}
                )
                if result.success and result.result:
                    artifacts = result.result.get("artifacts", [])
                    artifact_paths = [
                        a.get("path", a.get("name", ""))
                        for a in artifacts if a
                    ]
                    if artifact_paths:
                        logger.info(f"AI-first inferred {len(artifact_paths)} artifacts for '{title[:50]}'")
                        return artifact_paths
            except Exception as e:
                logger.debug(f"AI-first artifact inference failed: {e}")

        # Priority 2: Try using verificator for intelligent artifact specification
        if self.verificator_client:
            try:
                artifacts = await self.verificator_client.specify_artifacts(
                    task_title=title,
                    task_description=description,
                    project_path=project_path
                )
                if artifacts:
                    logger.info(f"Verificator specified {len(artifacts)} artifacts for '{title[:50]}'")
                    return artifacts
            except Exception as e:
                logger.debug(f"Verificator artifact specification failed: {e}")

        # Priority 3: Fallback to Regex-based inference (DEPRECATED)
        logger.debug("Using deprecated regex artifact inference")
        return self._regex_infer_artifacts(title, description)

    def _regex_infer_artifacts(self, title: str, description: str) -> list:
        """DEPRECATED: Regex-based artifact inference. Use AI-first instead."""
        import re
        artifacts = []

        combined = f"{title} {description}".lower()

        # Pattern: "Create/Implement X model" -> app/models/x.py
        model_match = re.search(r'(?:create|implement|add)\s+(\w+)\s+(?:sqlalchemy\s+)?model', combined)
        if model_match:
            model_name = model_match.group(1).lower()
            artifacts.append(f"app/models/{model_name}.py")

        # Pattern: "Create/Implement X endpoint(s)" -> app/api/v1/endpoints/x.py
        endpoint_match = re.search(r'(?:create|implement|add)\s+(\w+)\s+(?:crud\s+)?endpoint', combined)
        if endpoint_match:
            endpoint_name = endpoint_match.group(1).lower()
            # Also accept plural
            if endpoint_name.endswith('s'):
                endpoint_name = endpoint_name[:-1]
            artifacts.append(f"app/api/v1/endpoints/{endpoint_name}s.py")

        # Pattern: "app/path/to/file.py" in description -> exact file
        file_refs = re.findall(r'(?:create|implement|add|in|at)\s+[`\'"]*([a-zA-Z0-9_/]+\.(?:py|ts|tsx|js|jsx))[`\'"]*', combined)
        for file_ref in file_refs:
            if file_ref not in artifacts and not file_ref.startswith('/'):
                artifacts.append(file_ref)

        # Pattern: "tests/unit/test_x.py" or "tests/e2e/test_x.py"
        test_match = re.search(r'(?:write|create|add)\s+(?:\w+\s+)?tests?\s+for\s+(\w+)', combined)
        if test_match:
            test_subject = test_match.group(1).lower()
            if 'unit' in combined:
                artifacts.append(f"tests/unit/test_{test_subject}.py")
            elif 'e2e' in combined or 'end-to-end' in combined:
                artifacts.append(f"tests/e2e/test_{test_subject}.py")
            elif 'integration' in combined:
                artifacts.append(f"tests/integration/test_{test_subject}.py")

        # Pattern: explicit file paths mentioned
        explicit_files = re.findall(r'[`\'"](/?\w+(?:/\w+)*\.\w+)[`\'"]', description)
        for f in explicit_files:
            if f not in artifacts:
                artifacts.append(f.lstrip('/'))

        # Log what we inferred
        if artifacts:
            logger.debug(f"Inferred artifacts (regex) for '{title[:50]}': {artifacts}")

        return artifacts

    # =========================================================================
    # INTEGRATION TESTING
    # =========================================================================

    async def _run_integration_tests(self, gap_analysis: GapAnalysis) -> IntegrationTestResult:
        """Run integration tests between multiple projects."""
        logger.info(f"Running integration tests for: {gap_analysis.integration_projects}")

        result = IntegrationTestResult(
            projects=gap_analysis.integration_projects,
            tests_run=0,
            tests_passed=0,
            tests_failed=0
        )

        # Get project paths
        project_paths = []
        for proj_name in gap_analysis.integration_projects:
            proj_path = self.workspace / proj_name
            if proj_path.exists():
                project_paths.append(proj_path)

        if len(project_paths) < 2:
            logger.warning("Not enough projects for integration testing")
            return result

        try:
            # Start services for each project
            started_services = await self._start_project_services(project_paths)

            # Wait for services to be ready
            await asyncio.sleep(5)

            # Run integration tests
            for proj_path in project_paths:
                # Look for integration test files
                integration_tests = list(proj_path.rglob("*integration*.test.*"))
                integration_tests.extend(list(proj_path.rglob("*e2e*.test.*")))

                for test_file in integration_tests:
                    result.tests_run += 1
                    try:
                        # Run the test
                        test_result = await self._run_single_test(proj_path, test_file)
                        if test_result:
                            result.tests_passed += 1
                        else:
                            result.tests_failed += 1
                            result.failures.append({
                                'project': proj_path.name,
                                'test_file': str(test_file),
                                'error': 'Test failed'
                            })
                    except Exception as e:
                        result.tests_failed += 1
                        result.failures.append({
                            'project': proj_path.name,
                            'test_file': str(test_file),
                            'error': str(e)
                        })

            # Take screenshots if browser testing
            # TODO: Implement screenshot capture

            result.passed = result.tests_failed == 0 and result.tests_run > 0

            # Stop services
            await self._stop_project_services(started_services)

        except Exception as e:
            logger.error(f"Error in integration testing: {e}")
            result.failures.append({
                'error': str(e),
                'type': 'infrastructure'
            })

        # Log result
        await self.memory.log_activity(
            source="heartbeat",
            action="integration_test_completed",
            details={
                "projects": gap_analysis.integration_projects,
                "tests_run": result.tests_run,
                "tests_passed": result.tests_passed,
                "tests_failed": result.tests_failed,
                "passed": result.passed
            }
        )

        return result

    async def _start_project_services(self, project_paths: List[Path]) -> List[Dict]:
        """Start dev servers for projects."""
        started = []

        for proj_path in project_paths:
            try:
                # Check if package.json exists (Node project)
                if (proj_path / "package.json").exists():
                    # Start npm dev server
                    proc = subprocess.Popen(
                        ["npm", "run", "dev"],
                        cwd=proj_path,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    started.append({
                        'path': str(proj_path),
                        'type': 'node',
                        'process': proc
                    })
                    logger.info(f"Started Node dev server for {proj_path.name}")

                # Check if requirements.txt exists (Python project)
                elif (proj_path / "requirements.txt").exists():
                    # Look for main.py or app.py
                    main_file = None
                    for candidate in ["app/main.py", "main.py", "app.py"]:
                        if (proj_path / candidate).exists():
                            main_file = candidate
                            break

                    if main_file:
                        proc = subprocess.Popen(
                            ["python", "-m", "uvicorn", main_file.replace('/', '.').replace('.py', ':app'), "--reload"],
                            cwd=proj_path,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE
                        )
                        started.append({
                            'path': str(proj_path),
                            'type': 'python',
                            'process': proc
                        })
                        logger.info(f"Started Python server for {proj_path.name}")

            except Exception as e:
                logger.error(f"Error starting service for {proj_path}: {e}")

        return started

    async def _stop_project_services(self, services: List[Dict]) -> None:
        """Stop project services."""
        for service in services:
            try:
                proc = service.get('process')
                if proc:
                    proc.terminate()
                    proc.wait(timeout=5)
                    logger.info(f"Stopped service for {service['path']}")
            except Exception as e:
                logger.warning(f"Error stopping service: {e}")

    async def _run_single_test(self, project_path: Path, test_file: Path) -> bool:
        """Run a single test file and return success status."""
        try:
            # Determine test runner
            if test_file.suffix in ['.ts', '.tsx', '.js', '.jsx']:
                # Use npm test or vitest
                result = subprocess.run(
                    ["npx", "vitest", "run", str(test_file)],
                    cwd=project_path,
                    capture_output=True,
                    timeout=60
                )
            elif test_file.suffix == '.py':
                # Use pytest
                result = subprocess.run(
                    ["python", "-m", "pytest", str(test_file), "-v"],
                    cwd=project_path,
                    capture_output=True,
                    timeout=60
                )
            else:
                return False

            return result.returncode == 0

        except subprocess.TimeoutExpired:
            logger.warning(f"Test timed out: {test_file}")
            return False
        except Exception as e:
            logger.error(f"Error running test {test_file}: {e}")
            return False

    # =========================================================================
    # VALIDATION ENFORCEMENT
    # =========================================================================

    async def _enforce_validation(
        self,
        objective,
        project_path: str,
        gap_analysis: GapAnalysis
    ) -> None:
        """Ensure all validation stages are completed."""

        for stage in gap_analysis.validation_gaps:
            # Create a task to run this validation stage
            task_def = {
                'title': f"Run validation: {stage}",
                'description': f"""
[HEARTBEAT VALIDATION ENFORCEMENT]

The validation stage '{stage}' has not passed for this project.

Project Path: {project_path}

Please ensure this validation stage passes:
- {stage}

This is a mandatory requirement before the project can be marked complete.
""",
                'priority': 2,
                'worker_role': 'tester' if 'test' in stage else 'reviewer' if stage == 'review' else 'coder'
            }

            # Check if similar task exists
            existing_tasks = await self.memory.short_term.get_tasks_for_objective(objective.id)
            if not any(stage in t.title.lower() for t in existing_tasks):
                await self.memory.create_tasks(objective.id, [task_def])
                logger.info(f"Created validation enforcement task for stage: {stage}")

    # =========================================================================
    # COMPLETION GATE
    # =========================================================================

    async def _check_completion_gate(
        self,
        objective,
        project_path: str,
        state: ProjectState
    ) -> bool:
        """
        Final check before marking project complete.
        Returns True if project can be marked complete.
        """
        logger.info(f"Checking completion gate for {state.project_name}")

        # Check 1: All validation stages passed
        all_stages_passed = all(
            stage in state.validation.get('stages_passed', [])
            for stage in self.REQUIRED_VALIDATION_STAGES
        )

        if not all_stages_passed:
            missing = [
                s for s in self.REQUIRED_VALIDATION_STAGES
                if s not in state.validation.get('stages_passed', [])
            ]
            logger.warning(f"Completion blocked: Missing validation stages: {missing}")
            return False

        # Check 2: No failed tasks
        tasks = await self.memory.short_term.get_tasks_for_objective(objective.id)
        failed_tasks = [t for t in tasks if str(t.status) == 'failed']
        if failed_tasks:
            logger.warning(f"Completion blocked: {len(failed_tasks)} failed tasks")
            return False

        # Check 3: Run final integration test if multi-project
        linked_projects = self.shared_context.get_linked_projects(state.project_name)
        if linked_projects:
            logger.info(f"Running final integration test with: {linked_projects}")
            # Would run integration tests here

        # Check 4: All requirements met (from last analysis)
        last_analysis = self._last_analysis.get(objective.id)
        if last_analysis and last_analysis.unmet_requirements:
            logger.warning(
                f"Completion blocked: {len(last_analysis.unmet_requirements)} unmet requirements"
            )
            return False

        # All checks passed - mark complete
        logger.info(f"Completion gate PASSED for {state.project_name}")

        await self.state_manager.mark_complete(project_path)
        await self.memory.complete_objective(objective.id, success=True)

        await self.memory.log_activity(
            source="heartbeat",
            action="project_completed",
            details={
                "project_name": state.project_name,
                "project_path": project_path,
                "objective_id": objective.id,
                "validation_stages_passed": state.validation.get('stages_passed', [])
            }
        )

        return True

    # =========================================================================
    # PUBLIC API
    # =========================================================================

    async def force_analysis(self, objective_id: str) -> Optional[GapAnalysis]:
        """Force an immediate analysis of an objective."""
        try:
            objective = await self.memory.short_term.get_objective(objective_id)
            if not objective:
                return None

            project_path = await self._find_project_for_objective(objective)
            if not project_path:
                return None

            state = await self.state_manager.get_state(project_path)
            if not state:
                return None

            return await self._analyze_gaps_with_claude(objective, project_path, state)

        except Exception as e:
            logger.error(f"Error in force analysis: {e}")
            return None

    def get_last_analysis(self, objective_id: str) -> Optional[GapAnalysis]:
        """Get the last analysis for an objective."""
        return self._last_analysis.get(objective_id)

    async def get_project_health(self, project_path: str) -> Dict[str, Any]:
        """Get health status of a project."""
        state = await self.state_manager.get_state(project_path)
        if not state:
            return {"status": "unknown", "error": "No state found"}

        return {
            "status": state.status,
            "completion": sum(
                1 for s in state.stages.values()
                if s.get("status") == "completed"
            ) / len(state.stages),
            "validation": {
                "passed": state.validation.get("stages_passed", []),
                "failed": state.validation.get("stages_failed", []),
                "pending": state.validation.get("stages_pending", [])
            },
            "dev_server": state.dev_server,
            "pending_work": state.get_pending_work()
        }


# =============================================================================
# SINGLETON
# =============================================================================

_heartbeat_agent: Optional[HeartbeatAgent] = None


def get_heartbeat_agent(
    memory: Optional[MemoryClient] = None,
    state_manager: Optional[ProjectStateManager] = None,
    shared_context: Optional[SharedContextManager] = None,
    worker_pool: Optional["WorkerPool"] = None,
    **kwargs
) -> HeartbeatAgent:
    """Get or create the heartbeat agent instance."""
    global _heartbeat_agent

    if _heartbeat_agent is None:
        if memory is None or state_manager is None or shared_context is None:
            raise ValueError("Must provide memory, state_manager, and shared_context on first call")

        _heartbeat_agent = HeartbeatAgent(
            memory=memory,
            state_manager=state_manager,
            shared_context=shared_context,
            worker_pool=worker_pool,
            **kwargs
        )

    return _heartbeat_agent


def set_heartbeat_worker_pool(worker_pool: "WorkerPool") -> None:
    """Set the worker pool for the heartbeat agent after initialization."""
    global _heartbeat_agent
    if _heartbeat_agent is not None:
        _heartbeat_agent.worker_pool = worker_pool
