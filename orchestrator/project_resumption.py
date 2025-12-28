# =============================================================================
# CLOPUS v3 Project Resumption
# =============================================================================
"""
Generates resumption tasks for incomplete projects.
Enables CLOPUS to continue work across restarts.
"""

import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging

from .project_state import ProjectState, ProjectStateManager, get_state_manager

logger = logging.getLogger("clopus.project_resumption")


@dataclass
class ResumptionTask:
    """A task to resume work on a project."""
    id: str
    title: str
    description: str
    worker_role: str
    priority: int
    project_path: str
    resumption_type: str  # validation, e2e, dev_server, documentation, design


class ProjectResumptionGenerator:
    """
    Generates tasks to resume incomplete projects.
    Called on CLOPUS startup to continue previous work.
    """

    def __init__(
        self,
        state_manager: ProjectStateManager,
        port_manager=None
    ):
        self.state_manager = state_manager
        self.port_manager = port_manager

    async def generate_resumption_tasks(
        self,
        state: ProjectState
    ) -> List[Dict]:
        """
        Generate all tasks needed to complete a project.
        Returns tasks in priority order.
        """
        tasks = []
        pending_work = state.get_pending_work()

        logger.info(
            f"Generating resumption tasks for {state.project_name}: {pending_work}"
        )

        # Priority order of resumption tasks
        for work_item in pending_work:
            if work_item == "restart_dev_server":
                tasks.append(self._create_restart_server_task(state))
            elif work_item == "start_dev_server":
                tasks.append(self._create_start_server_task(state))
            elif work_item == "design":
                tasks.append(self._create_design_task(state))
            elif work_item == "validation":
                tasks.append(self._create_validation_task(state))
            elif work_item == "e2e_testing":
                tasks.append(self._create_e2e_task(state))
            elif work_item == "documentation":
                tasks.append(self._create_documentation_task(state))

        return [t for t in tasks if t is not None]

    def _create_restart_server_task(self, state: ProjectState) -> Dict:
        """Create task to restart dev server on correct port."""
        current_port = state.dev_server.get("port")
        allocated_port = state.dev_server.get("allocated_port")

        return {
            "id": str(uuid.uuid4()),
            "title": f"Restart dev server on correct port",
            "description": f"""Restart the dev server for {state.project_name}.

## Current State
- Currently running on port: {current_port}
- Should be running on port: {allocated_port}

## Actions Required
1. Stop the current dev server (kill process on port {current_port})
2. Start dev server on allocated port {allocated_port}
3. Verify server is accessible at http://0.0.0.0:{allocated_port}

## Project Path
{state.project_path}

This is a resumption task - the project was previously in progress.
""",
            "worker_role": "debugger",
            "priority": 10,  # Highest priority
            "project_path": state.project_path,
            "metadata": {
                "resumption_type": "dev_server_restart",
                "current_port": current_port,
                "allocated_port": allocated_port
            }
        }

    def _create_start_server_task(self, state: ProjectState) -> Dict:
        """Create task to start dev server."""
        allocated_port = state.dev_server.get("allocated_port")

        if not allocated_port and self.port_manager:
            allocated_port = self.port_manager.get_project_port(state.project_name)

        return {
            "id": str(uuid.uuid4()),
            "title": f"Start dev server",
            "description": f"""Start the dev server for {state.project_name}.

## Actions Required
1. Navigate to project: {state.project_path}
2. Start dev server on port {allocated_port}
3. Verify server is accessible

## Commands
```bash
cd {state.project_path}
npm run dev -- --host 0.0.0.0 --port {allocated_port}
```

## Expected Result
Server running at http://0.0.0.0:{allocated_port}

This is a resumption task - the project was previously in progress.
""",
            "worker_role": "debugger",
            "priority": 9,
            "project_path": state.project_path,
            "metadata": {
                "resumption_type": "dev_server_start",
                "allocated_port": allocated_port
            }
        }

    def _create_design_task(self, state: ProjectState) -> Optional[Dict]:
        """Create task to complete design system."""
        # Check if design system file exists but is incomplete
        design_file = Path(state.project_path) / ".clopus" / "design" / "DESIGN_SYSTEM.md"

        if design_file.exists():
            # Design exists, might just need review
            return None

        return {
            "id": str(uuid.uuid4()),
            "title": f"Create design system for {state.project_name}",
            "description": f"""Create comprehensive design system for this project.

## Project Context
- Path: {state.project_path}
- Objective: {state.objective_content or 'See project files'}

## Required Outputs
Save to .clopus/design/:
1. DESIGN_SYSTEM.md - Complete design documentation
2. tailwind-theme.js - Tailwind config (if applicable)
3. variables.css - CSS variables (if applicable)

## Design Documentation Must Include
- Brand identity (name, tagline)
- Color palette (with dark mode)
- Typography scale
- Spacing system
- Component styles

This is a resumption task - the project needs design before implementation can continue.
""",
            "worker_role": "designer",
            "priority": 8,
            "project_path": state.project_path,
            "metadata": {
                "resumption_type": "design"
            }
        }

    def _create_validation_task(self, state: ProjectState) -> Dict:
        """Create task to complete validation."""
        passed = state.validation.get("stages_passed", [])
        failed = state.validation.get("stages_failed", [])
        pending = state.validation.get("stages_pending", [])

        return {
            "id": str(uuid.uuid4()),
            "title": f"Complete validation for {state.project_name}",
            "description": f"""Run validation pipeline and fix any failures.

## Current Validation State
- Passed: {', '.join(passed) if passed else 'None'}
- Failed: {', '.join(failed) if failed else 'None'}
- Pending: {', '.join(pending) if pending else 'None'}

## Project Path
{state.project_path}

## Actions Required
1. Run the full validation pipeline
2. Fix any failing stages
3. Re-run until all stages pass

## Validation Stages
1. Syntax - Code parses correctly
2. Lint - ESLint/linting passes
3. Build - Project builds successfully
4. Unit Tests - All tests pass
5. Integration Tests - API/component tests
6. E2E Tests - Playwright browser tests
7. Security - No vulnerabilities
8. Review - Code quality check

This is a resumption task - validation was partially complete.
""",
            "worker_role": "debugger",
            "priority": 7,
            "project_path": state.project_path,
            "metadata": {
                "resumption_type": "validation",
                "stages_passed": passed,
                "stages_pending": pending
            }
        }

    def _create_e2e_task(self, state: ProjectState) -> Dict:
        """Create task to run E2E tests."""
        screenshots = state.stages.get("e2e_testing", {}).get("screenshots", [])
        dev_server_url = state.dev_server.get("url", "http://localhost:3000")

        return {
            "id": str(uuid.uuid4()),
            "title": f"Run E2E tests for {state.project_name}",
            "description": f"""Run end-to-end browser tests using Playwright.

## Project Path
{state.project_path}

## Dev Server
{dev_server_url}

## Existing Screenshots
{len(screenshots)} screenshots already captured.

## Actions Required
1. Ensure dev server is running
2. Run Playwright E2E tests
3. Capture screenshots of all major features
4. Save screenshots to .clopus/screenshots/

## E2E Test Requirements
- Test all user flows
- Capture before/after states
- Test dark mode if applicable
- Test responsive layouts
- Verify all features work

## Screenshots to Capture
- Homepage/main view
- Each major feature in action
- Form submissions
- Error states
- Mobile viewport

This is a resumption task - E2E testing was not completed.
""",
            "worker_role": "tester",
            "priority": 6,
            "project_path": state.project_path,
            "metadata": {
                "resumption_type": "e2e_testing",
                "existing_screenshots": len(screenshots)
            }
        }

    def _create_documentation_task(self, state: ProjectState) -> Dict:
        """Create task to generate PROJECT.md."""
        return {
            "id": str(uuid.uuid4()),
            "title": f"Generate PROJECT.md for {state.project_name}",
            "description": f"""Generate comprehensive project documentation.

## Project Path
{state.project_path}

## PROJECT.md Must Include

### 1. Project Overview
- Name and description
- Current status
- Objective

### 2. Current State
| Stage | Status |
|-------|--------|
| Setup | {state.stages.get('setup', {}).get('status', 'unknown')} |
| Design | {state.stages.get('design', {}).get('status', 'unknown')} |
| Implementation | {state.stages.get('implementation', {}).get('status', 'unknown')} |
| Validation | {state.validation.get('status', 'unknown')} |
| E2E Testing | {state.stages.get('e2e_testing', {}).get('status', 'unknown')} |

### 3. Dev Server
- Port: {state.dev_server.get('allocated_port') or state.dev_server.get('port')}
- URL: {state.dev_server.get('url', 'Not running')}

### 4. Validation Results
{chr(10).join(f'- {s}: Passed' for s in state.validation.get('stages_passed', []))}
{chr(10).join(f'- {s}: Failed' for s in state.validation.get('stages_failed', []))}
{chr(10).join(f'- {s}: Pending' for s in state.validation.get('stages_pending', []))}

### 5. Technology Stack
Detect and document from package.json/requirements.txt

### 6. Features
List all implemented features

This is a resumption task - documentation needs to be generated.
""",
            "worker_role": "reviewer",
            "priority": 5,
            "project_path": state.project_path,
            "metadata": {
                "resumption_type": "documentation"
            }
        }


async def create_resumption_objective(
    state: ProjectState,
    memory_client
) -> Optional[str]:
    """
    Create an objective for resuming an incomplete project.
    Returns the objective ID.

    IMPORTANT: Checks for existing in_progress objectives for this project
    to prevent duplicate objectives from being created.
    """
    # First, check if the stored objective_id still exists
    if state.objective_id:
        try:
            existing = await memory_client.short_term.get_objective(state.objective_id)
            if existing and existing.status.value in ('pending', 'planning', 'in_progress'):
                # Re-queue existing objective
                await memory_client.requeue_objective(state.objective_id)
                return state.objective_id
        except Exception:
            pass

    # =================================================================
    # CHECK FOR ANY EXISTING IN_PROGRESS OBJECTIVE FOR THIS PROJECT
    # =================================================================
    # This prevents duplicate resumption objectives when the orchestrator
    # restarts multiple times or when heartbeat creates objectives.
    try:
        from memory.short_term import ObjectiveStatus
        in_progress = await memory_client.short_term.get_objectives_by_status(
            ObjectiveStatus.IN_PROGRESS
        )
        for obj in in_progress:
            # Check if this objective is for the same project
            if state.project_path in obj.content or state.project_name in obj.content:
                logger.info(f"Found existing in_progress objective {obj.id} for {state.project_name}, skipping creation")
                return obj.id
    except Exception as e:
        logger.warning(f"Error checking existing objectives: {e}")

    # Create new resumption objective only if none exists
    content = f"""[RESUMPTION] Continue work on: {state.project_name}

Project Path: {state.project_path}

## Previous Progress
- Status: {state.status}
- Design: {state.stages.get('design', {}).get('status', 'pending')}
- Implementation: {state.stages.get('implementation', {}).get('status', 'pending')}
- Validation: {state.validation.get('status', 'pending')} ({len(state.validation.get('stages_passed', []))}/8 passed)
- E2E Testing: {state.stages.get('e2e_testing', {}).get('status', 'pending')}

## Pending Work
{chr(10).join(f'- {w}' for w in state.get_pending_work())}

## Original Objective
{state.objective_content or 'Not recorded'}

Continue from where we left off. Complete all pending work.
"""

    objective = await memory_client.create_objective(content)
    objective_id = objective.id
    logger.info(f"Created resumption objective {objective_id} for {state.project_name}")

    return objective_id


# Singleton instance
_resumption_generator: Optional[ProjectResumptionGenerator] = None


def get_resumption_generator(
    state_manager: Optional[ProjectStateManager] = None,
    port_manager=None
) -> ProjectResumptionGenerator:
    """Get the resumption generator instance."""
    global _resumption_generator
    if _resumption_generator is None:
        sm = state_manager or get_state_manager()
        _resumption_generator = ProjectResumptionGenerator(sm, port_manager)
    return _resumption_generator
