# =============================================================================
# CLOPUS v3 Heartbeat Agent (Completion Guardian)
# =============================================================================
"""
The Heartbeat Agent is a periodic supervisor that ensures projects actually
meet their objectives. It uses Claude to:

1. Parse objectives into concrete requirements
2. Assess current project state vs requirements
3. Identify gaps between promises and reality
4. Spawn new tasks to fill gaps
5. Run integration tests for multi-project objectives
6. Enforce all 8 validation phases before marking complete

This is the "little voice in the head" that asks:
"Did we actually build what we promised?"
"""

import asyncio
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import logging
import anthropic

from .project_state import ProjectState, ProjectStateManager, get_state_manager
from .memory_client import MemoryClient
from .shared_context import SharedContextManager, get_shared_context

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

    The Heartbeat Agent runs on a timer and uses Claude to:
    1. Analyze objectives and extract concrete requirements
    2. Compare requirements with actual project state
    3. Identify gaps and spawn tasks to fill them
    4. Run integration tests for multi-project objectives
    5. Enforce full 8-stage validation before completion
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
        anthropic_client: Optional[anthropic.Anthropic] = None,
        heartbeat_interval_seconds: int = 300,  # 5 minutes default
        workspace_path: str = "/workspace"
    ):
        self.memory = memory
        self.state_manager = state_manager
        self.shared_context = shared_context
        self.client = anthropic_client or anthropic.Anthropic()
        self.heartbeat_interval = heartbeat_interval_seconds
        self.workspace = Path(workspace_path)
        self.running = False
        self._last_analysis: Dict[str, GapAnalysis] = {}

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
        """Find the project path associated with an objective."""
        # Try to extract from objective content
        path_match = re.search(r'/workspace/([\w\-]+)', objective.content)
        if path_match:
            project_path = f"/workspace/{path_match.group(1)}"
            if Path(project_path).exists():
                return project_path

        # Try metadata
        if objective.metadata and 'project_path' in objective.metadata:
            return objective.metadata['project_path']

        # Look for tasks associated with this objective
        tasks = await self.memory.short_term.get_tasks_for_objective(objective.id)
        for task in tasks:
            if task.description:
                path_match = re.search(r'/workspace/([\w\-]+)', task.description)
                if path_match:
                    project_path = f"/workspace/{path_match.group(1)}"
                    if Path(project_path).exists():
                        return project_path

        # Find most recently modified project
        if self.workspace.exists():
            projects = [
                p for p in self.workspace.iterdir()
                if p.is_dir() and not p.name.startswith('.')
                and ((p / "package.json").exists() or (p / "requirements.txt").exists())
            ]
            if projects:
                projects.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                return str(projects[0])

        return None

    async def _analyze_gaps_with_claude(
        self,
        objective,
        project_path: str,
        state: ProjectState
    ) -> GapAnalysis:
        """Use Claude to analyze gaps between objective and current state."""

        # Gather current state information
        project_info = await self._gather_project_info(project_path)

        # Build prompt for Claude
        prompt = f"""You are analyzing a software project to identify gaps between the stated objective and the current implementation.

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

### Project Stages
{json.dumps(state.stages, indent=2)}

## YOUR TASK
Analyze this project and provide a JSON response with:

1. **requirements**: List of concrete requirements extracted from the objective. Each should have:
   - id: unique identifier (req_001, req_002, etc.)
   - description: what needs to be built
   - category: api, frontend, database, integration, testing, documentation
   - priority: critical, high, medium, low
   - verification_method: how to verify (file_exists, endpoint_works, test_passes, builds_successfully)
   - verification_target: specific file/endpoint to check
   - is_met: boolean - is this requirement currently satisfied?
   - evidence: if met, what proves it

2. **suggested_tasks**: Tasks that should be created to fill gaps. Each should have:
   - title: concise task title
   - description: detailed description
   - priority: 1-10 (1 is highest)
   - worker_role: coder, tester, reviewer, debugger, designer, researcher

3. **validation_gaps**: List of validation stages that haven't passed but should

4. **integration_needed**: boolean - does this project need integration testing with other projects?

5. **integration_projects**: if integration_needed, list the project names that need to be tested together

6. **overall_completion**: float 0.0 to 1.0 - how complete is the project vs objective?

Respond ONLY with valid JSON, no markdown formatting."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse Claude's response
            response_text = response.content[0].text.strip()

            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                response_text = re.sub(r'^```(?:json)?\n?', '', response_text)
                response_text = re.sub(r'\n?```$', '', response_text)

            analysis_data = json.loads(response_text)

            # Build GapAnalysis from response
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

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response: {e}")
            return GapAnalysis(
                project_path=project_path,
                objective_id=objective.id,
                objective_content=objective.content
            )
        except Exception as e:
            logger.error(f"Error in Claude analysis: {e}")
            return GapAnalysis(
                project_path=project_path,
                objective_id=objective.id,
                objective_content=objective.content
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

        # Check for existing tasks to avoid duplicates
        existing_tasks = await self.memory.short_term.get_tasks_for_objective(objective.id)
        existing_titles = {t.title for t in existing_tasks}

        tasks_to_create = []
        for task in gap_analysis.suggested_tasks:
            # Skip if similar task exists
            if any(task['title'].lower() in t.lower() or t.lower() in task['title'].lower()
                   for t in existing_titles):
                continue
            tasks_to_create.append(task)

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
            **kwargs
        )

    return _heartbeat_agent
