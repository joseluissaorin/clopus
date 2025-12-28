# =============================================================================
# CLOPUS v3 Worker Pool
# =============================================================================
"""
Manages the pool of Claude Code worker instances.
Handles task dispatch, result collection, and worker health monitoring.
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import logging

from .config import WorkerConfig

logger = logging.getLogger("clopus.worker_pool")


class WorkerPool:
    """Manage Claude Code worker instances."""

    def __init__(
        self,
        memory_client,
        config: WorkerConfig,
        ipc_path: str = "/app/ipc"
    ):
        self.memory = memory_client
        self.config = config
        self.ipc_path = Path(ipc_path)
        self.workers: Dict[int, Dict] = {}
        self._running = False

        # Skills engine for enhanced prompts (set by orchestrator)
        self.skills_engine = None

    async def initialize(self) -> None:
        """Initialize worker pool."""
        logger.info(f"Initializing worker pool with {self.config.count} workers")

        # Create IPC directories
        self.ipc_path.mkdir(parents=True, exist_ok=True)

        for i in range(1, self.config.count + 1):
            role = self.config.roles[(i - 1) % len(self.config.roles)]

            # Create worker IPC directory
            worker_dir = self.ipc_path / "tasks" / str(i)
            worker_dir.mkdir(parents=True, exist_ok=True)

            # =================================================================
            # CLEAR STALE IPC FILES ON RESTART
            # =================================================================
            # This ensures workers pick up fresh tasks after orchestrator restart
            pending_file = worker_dir / "pending.json"
            result_file = worker_dir / "result.json"
            cancel_file = worker_dir / "cancel"
            ack_file = worker_dir / "ack.json"
            collected_file = worker_dir / "result.collected"

            if pending_file.exists():
                pending_file.unlink()
                logger.info(f"Cleared stale pending task for worker {i}")
            if result_file.exists():
                result_file.unlink()
                logger.info(f"Cleared stale result for worker {i}")
            if cancel_file.exists():
                cancel_file.unlink()
            if ack_file.exists():
                ack_file.unlink()
            if collected_file.exists():
                collected_file.unlink()

            # Register worker
            worker = await self.memory.register_worker(i, role)
            self.workers[i] = {
                "id": i,
                "role": role,
                "status": "idle",
                "current_task": None,
                "ipc_dir": worker_dir,
                "last_heartbeat": datetime.now()
            }

            logger.info(f"Registered worker {i} with role: {role}")

        self._running = True

    async def shutdown(self) -> None:
        """Shutdown worker pool."""
        logger.info("Shutting down worker pool")
        self._running = False

        # Clear pending tasks
        for worker_id, worker in self.workers.items():
            pending_file = worker["ipc_dir"] / "pending.json"
            if pending_file.exists():
                pending_file.unlink()

    async def dispatch_task(
        self,
        worker_id: int,
        task_id: str,
        title: str,
        description: Optional[str] = None,
        cwd: str = "/workspace",
        relevant_skills: Optional[List[Dict]] = None,
        memory_context: Optional[str] = None,
        ack_timeout: int = 10
    ) -> bool:
        """Dispatch a task to a worker with acknowledgment handshake.

        Args:
            worker_id: The worker to dispatch to
            task_id: The task ID
            title: Task title
            description: Task description
            cwd: Working directory for the task
            relevant_skills: Optional list of relevant skills
            memory_context: Optional memory context
            ack_timeout: Seconds to wait for worker acknowledgment (default 10)

        Returns:
            True if task was acknowledged by worker, False otherwise
        """
        if worker_id not in self.workers:
            logger.error(f"Worker {worker_id} not found")
            return False

        worker = self.workers[worker_id]

        if worker["status"] != "idle":
            logger.warning(f"Worker {worker_id} is not idle (status: {worker['status']})")
            return False

        # Build prompt for Claude Code with skill and memory context
        prompt = await self._build_task_prompt(
            title,
            description,
            worker["role"],
            relevant_skills,
            memory_context
        )

        # Create task file
        task_data = {
            "task_id": task_id,
            "prompt": prompt,
            "cwd": cwd,
            "dispatched_at": datetime.now().isoformat()
        }

        pending_file = worker["ipc_dir"] / "pending.json"
        ack_file = worker["ipc_dir"] / "ack.json"

        # Remove stale ack file if exists
        if ack_file.exists():
            ack_file.unlink()

        # Write task
        pending_file.write_text(json.dumps(task_data, indent=2))
        logger.debug(f"Wrote pending task {task_id} for worker {worker_id}")

        # Wait for acknowledgment with timeout
        start_time = datetime.now()
        while (datetime.now() - start_time).total_seconds() < ack_timeout:
            if ack_file.exists():
                try:
                    ack_data = json.loads(ack_file.read_text())
                    if ack_data.get("task_id") == task_id:
                        # Worker acknowledged the task
                        worker["status"] = "busy"
                        worker["current_task"] = task_id
                        logger.info(f"Task {task_id} acknowledged by worker {worker_id}")
                        return True
                except json.JSONDecodeError:
                    pass
            await asyncio.sleep(0.1)

        # Timeout - worker didn't acknowledge
        logger.warning(f"Worker {worker_id} did not acknowledge task {task_id} within {ack_timeout}s")

        # Clean up pending file
        if pending_file.exists():
            pending_file.unlink()

        return False

    def is_reserved_role(self, role: str) -> bool:
        """Check if a role is reserved (not for regular task assignment)."""
        reserved = getattr(
            self.config, 'reserved_roles',
            ['heartbeat', 'verificator', 'browser-headless', 'browser-chrome', 'services']
        )
        return role in reserved

    def get_heartbeat_worker_id(self) -> Optional[int]:
        """Get the dedicated heartbeat worker ID."""
        for worker_id, worker in self.workers.items():
            if worker["role"] == "heartbeat":
                return worker_id
        return None

    async def get_idle_workers(self, role: Optional[str] = None, include_reserved: bool = False) -> List[Dict]:
        """
        Get list of idle workers.

        Args:
            role: Filter by specific role
            include_reserved: If True, include reserved roles like heartbeat
        """
        idle = []

        for worker_id, worker in self.workers.items():
            if worker["status"] == "idle":
                # Skip reserved roles unless explicitly included
                if not include_reserved and self.is_reserved_role(worker["role"]):
                    continue
                if role is None or worker["role"] == role:
                    idle.append(worker)

        return idle

    async def _build_task_prompt(
        self,
        title: str,
        description: Optional[str],
        role: str,
        relevant_skills: Optional[List[Dict]] = None,
        memory_context: Optional[str] = None
    ) -> str:
        """Build a prompt for Claude Code with skill and memory context."""
        role_instructions = {
            "coder": "You are implementing code. Focus on clean, working code that follows best practices. Always follow the design documentation in .clopus/design/ when styling components.",
            "tester": "You are writing tests. Ensure comprehensive coverage and edge case handling.",
            "reviewer": "You are reviewing code. Check for bugs, security issues, and best practices. Verify that code follows the design system documented in .clopus/design/.",
            "researcher": "You are researching. Find relevant information, docs, and solutions.",
            "debugger": "You are debugging. Identify root causes and implement fixes.",
            "heartbeat": """You are the Completion Guardian. Your task is to analyze a project and identify gaps between the stated objective and current implementation.

Write your analysis to the file specified in the task. Be thorough - check every requirement, every endpoint, every test. This is critical for ensuring project quality.""",
            "designer": """You are the Design Lead for this project. Your responsibilities:

1. CREATE COMPREHENSIVE DESIGN DOCUMENTATION:
   - Brand identity (name, logo concept, tagline)
   - Color palette (primary, secondary, accent, backgrounds, text colors)
   - Typography (font families, sizes, weights for headings, body, UI)
   - Component styles (buttons, inputs, cards, modals, navigation)
   - Spacing system (consistent margins/padding scale)
   - Visual hierarchy and layout patterns

2. FOR NEW PROJECTS:
   - Create a unique brand identity that matches the project purpose
   - Choose colors that evoke the right emotions for the use case
   - Define a complete design system before implementation begins
   - Save all documentation to .clopus/design/ for other workers to follow

3. FOR EXISTING PROJECTS:
   - Analyze existing styles (CSS, component code, screenshots)
   - Extract and document the current design system
   - Ensure any new features match the existing visual language

4. ONGOING SUPPORT:
   - Other workers may request design feedback
   - Review screenshots and suggest improvements
   - Ensure visual consistency across the entire application

Always output your design decisions to .clopus/design/DESIGN_SYSTEM.md""",

            "verificator": """You are the Intelligent Verificator. Your job is to use Claude's intelligence to verify, analyze, and validate work.

You will receive structured verification requests. Your responses MUST be valid JSON that matches the expected output format for each task type.

TASK TYPES:

1. SPECIFY_ARTIFACTS: Analyze a task description and determine what files/endpoints it should create.
   Output: {"artifacts": ["path/to/file.py", "path/to/other.js"], "reasoning": "..."}

2. VERIFY_COMPLETION: Check if a completed task actually created what it claimed.
   Output: {"verified": true/false, "missing": ["file1.py"], "found": ["file2.py"], "reasoning": "..."}

3. CHECK_DUPLICATE: Determine if two tasks are semantically the same (regardless of wording).
   Output: {"is_duplicate": true/false, "confidence": 0.0-1.0, "reasoning": "..."}

4. MATCH_PROJECT: Match an objective to the correct project based on content analysis.
   Output: {"project_path": "/workspace/project-name", "confidence": 0.0-1.0, "reasoning": "..."}

5. AUDIT_COMPLETED: Audit a completed task to check if its artifacts actually exist.
   Output: {"passed": true/false, "missing_artifacts": [], "recommendation": "re-run"/"accept"/"manual-review"}

6. SEMANTIC_CHECK: Check if task output semantically matches what was requested.
   Output: {"matches": true/false, "coverage": 0.0-1.0, "gaps": ["missing feature X"], "reasoning": "..."}

ALWAYS respond with valid JSON only. No markdown, no explanation outside JSON.""",

            "browser-headless": """You are the Headless Browser Automation specialist using Playwright MCP.

Your role is to automate browser interactions for:
- Web scraping and data extraction
- Form filling and submission
- Website testing and validation
- Screenshot capture
- PDF generation

## Tools Available (via Playwright MCP)
- Navigate to URLs
- Click elements using selectors
- Fill input fields
- Extract text content
- Take screenshots
- Evaluate JavaScript
- Handle authentication

## Best Practices
1. Always wait for elements before interacting
2. Use robust selectors (prefer data-testid, id, then CSS)
3. Handle popups, modals, and cookie banners gracefully
4. Respect rate limits and robots.txt
5. Return extracted data in structured JSON format
6. Take screenshots as evidence of completed actions

## Output Format
Always return results as JSON:
{
    "success": true/false,
    "data": {...extracted data...},
    "screenshots": ["path/to/screenshot.png"],
    "error": null or "error message"
}""",

            "browser-chrome": """You are the Chrome Browser Automation specialist with the Claude in Chrome extension.

Your role is to perform complex browser interactions that benefit from visual control:
- OAuth authentication flows
- Multi-step form wizards
- Interactive web applications
- Visual verification tasks
- Tasks requiring human-like interaction patterns

## Unique Capabilities
- Google Chrome with all extensions
- Claude in Chrome extension for collaborative browsing
- Full VNC access for visual debugging
- Persistent browser profiles for session management
- Can handle CAPTCHAs and complex auth flows

## Tools Available
- All Playwright MCP tools
- Direct Chrome DevTools access
- Extension-based interactions
- Cookie and session management

## Best Practices
1. Use visual verification when text extraction is unreliable
2. Leverage the Claude extension for complex decision-making
3. Save session cookies for repeated authentication
4. Take screenshots at each step for audit trail
5. Handle OAuth flows by preserving browser state

## VNC Access
Users can view your browser at:
- noVNC: http://localhost:6280
- VNC: localhost:5920""",

            "services": """You are the Services Integration specialist responsible for external service automation.

Your role is to integrate with external services via MCP servers for:
- Email automation (Gmail MCP)
- Web scraping (Firecrawl MCP)
- Calendar management
- Messaging platforms (Slack, Discord)
- Payment processing
- Cloud services

## Available MCPs

### Gmail MCP
- Read, send, and manage emails
- Search emails by query
- Create drafts
- Manage labels
- Send with attachments

### Firecrawl MCP
- Advanced web scraping
- JavaScript rendering
- Structured data extraction
- Batch URL processing

## Best Practices
1. Handle API rate limits gracefully with exponential backoff
2. Log all external interactions for audit trail
3. Return structured data for downstream tasks
4. Respect user privacy and data handling policies
5. Validate responses before returning
6. Store credentials securely in environment variables

## Output Format
Always return results as JSON:
{
    "success": true/false,
    "service": "gmail"/"firecrawl"/etc,
    "action": "send_email"/"scrape_url"/etc,
    "result": {...},
    "error": null or "error message"
}""",
        }

        instruction = role_instructions.get(role, role_instructions["coder"])

        prompt_parts = [
            f"# Task: {title}",
            "",
            instruction,
            "",
        ]

        if description:
            prompt_parts.extend([
                "## Details",
                description,
                "",
            ])

        # =====================================================================
        # HINT AT RELEVANT SKILLS (Native Claude Code Discovery)
        # =====================================================================
        # Claude Code auto-discovers skills from ~/.claude/skills/
        # We just hint at which skills may be useful - Claude loads them on-demand
        # This is more efficient than injecting full skill content
        if relevant_skills:
            skill_names = [s.get("name", "") for s in relevant_skills[:5] if s.get("name")]
            if skill_names:
                prompt_parts.extend([
                    "## Relevant Skills Available",
                    "The following skills are available and may help with this task:",
                    ", ".join(skill_names),
                    "",
                    "Claude Code will automatically load these skills when needed.",
                    ""
                ])

        # =====================================================================
        # ADD MEMORY CONTEXT (PAST LEARNINGS)
        # =====================================================================
        if memory_context:
            prompt_parts.extend([
                "## Relevant Context from Past Projects",
                memory_context[:1000],  # Truncate to 1000 chars
                ""
            ])

        prompt_parts.extend([
            "## Requirements",
            "- Complete the task fully",
            "- Ensure code passes linting and validation",
            "- Write clean, readable code",
            "- Handle errors appropriately",
            "- Code will be validated by an 8-stage pipeline",
            "",
            "Begin working on this task now."
        ])

        return "\n".join(prompt_parts)

    def set_skills_engine(self, skills_engine) -> None:
        """Set the skills engine for enhanced prompts."""
        self.skills_engine = skills_engine
        logger.info("Skills engine connected to worker pool")

    async def collect_results(self) -> Dict[int, Dict]:
        """Collect completed task results from workers using atomic file operations.

        Uses atomic rename to prevent race conditions when reading result files.
        """
        results = {}

        for worker_id, worker in self.workers.items():
            if worker["status"] != "busy":
                continue

            result_file = worker["ipc_dir"] / "result.json"
            collected_file = worker["ipc_dir"] / "result.collected"

            if result_file.exists():
                try:
                    # Atomic rename to prevent race condition
                    # If rename succeeds, we own the file exclusively
                    result_file.rename(collected_file)

                    # Now safely read the collected file
                    result_data = json.loads(collected_file.read_text())

                    # Remove the collected file after reading
                    collected_file.unlink()

                    results[worker_id] = result_data

                    # Update worker state
                    worker["status"] = "idle"
                    worker["current_task"] = None
                    worker["last_heartbeat"] = datetime.now()

                    logger.info(f"Collected result from worker {worker_id}: {result_data.get('task_id')}")

                except FileNotFoundError:
                    # Another process already collected this result (race condition)
                    logger.debug(f"Result file for worker {worker_id} was already collected")

                except json.JSONDecodeError as e:
                    logger.error(f"Invalid result JSON from worker {worker_id}: {e}")
                    # Clean up the corrupt file
                    if collected_file.exists():
                        collected_file.unlink()

                except OSError as e:
                    logger.error(f"OS error collecting result from worker {worker_id}: {e}")

        return results

    async def check_heartbeats(self) -> List[int]:
        """Check worker heartbeats and return stale workers."""
        stale_workers = []
        timeout = timedelta(seconds=self.config.heartbeat_interval_s * 3)

        for worker_id, worker in self.workers.items():
            # Check status file for heartbeat
            status_file = worker["ipc_dir"] / "status.json"

            if status_file.exists():
                try:
                    status_data = json.loads(status_file.read_text())
                    updated_at = status_data.get("updated_at") or status_data.get("started_at")

                    if updated_at:
                        last_update = datetime.fromisoformat(updated_at)
                        # Ensure both datetimes are timezone-aware
                        now = datetime.now(timezone.utc)
                        if last_update.tzinfo is None:
                            last_update = last_update.replace(tzinfo=timezone.utc)
                        if now - last_update > timeout:
                            stale_workers.append(worker_id)
                            worker["status"] = "offline"
                        else:
                            worker["last_heartbeat"] = last_update
                            # Reset to idle if worker was offline but is now responding
                            if worker["status"] == "offline":
                                worker["status"] = "idle"
                                logger.info(f"Worker {worker_id} back online")

                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Error reading status for worker {worker_id}: {e}")

        if stale_workers:
            logger.warning(f"Stale workers detected: {stale_workers}")

        return stale_workers


    async def get_worker_status(self, worker_id: int) -> Optional[Dict]:
        """Get status of a specific worker."""
        if worker_id not in self.workers:
            return None

        worker = self.workers[worker_id]
        status_file = worker["ipc_dir"] / "status.json"

        status = {
            "id": worker_id,
            "role": worker["role"],
            "status": worker["status"],
            "current_task": worker["current_task"],
            "last_heartbeat": worker["last_heartbeat"].isoformat()
        }

        if status_file.exists():
            try:
                file_status = json.loads(status_file.read_text())
                status.update(file_status)
            except json.JSONDecodeError:
                pass

        return status

    async def get_all_status(self) -> List[Dict]:
        """Get status of all workers."""
        statuses = []
        for worker_id in self.workers:
            status = await self.get_worker_status(worker_id)
            if status:
                statuses.append(status)
        return statuses

    async def cancel_task(self, worker_id: int) -> bool:
        """Cancel the current task for a worker."""
        if worker_id not in self.workers:
            return False

        worker = self.workers[worker_id]

        # Remove pending file if exists
        pending_file = worker["ipc_dir"] / "pending.json"
        if pending_file.exists():
            pending_file.unlink()

        # Write cancel signal
        cancel_file = worker["ipc_dir"] / "cancel"
        cancel_file.touch()

        # Update status
        worker["status"] = "idle"
        worker["current_task"] = None

        logger.info(f"Cancelled task for worker {worker_id}")
        return True

    async def reassign_task(self, from_worker: int, to_worker: int) -> bool:
        """Reassign a task from one worker to another."""
        if from_worker not in self.workers or to_worker not in self.workers:
            return False

        from_worker_data = self.workers[from_worker]
        to_worker_data = self.workers[to_worker]

        if to_worker_data["status"] != "idle":
            return False

        # Read pending task
        pending_file = from_worker_data["ipc_dir"] / "pending.json"
        if not pending_file.exists():
            return False

        task_data = json.loads(pending_file.read_text())

        # Move to new worker
        new_pending_file = to_worker_data["ipc_dir"] / "pending.json"
        new_pending_file.write_text(json.dumps(task_data, indent=2))

        # Clean up old worker
        pending_file.unlink()
        from_worker_data["status"] = "idle"
        from_worker_data["current_task"] = None

        # Update new worker
        to_worker_data["status"] = "busy"
        to_worker_data["current_task"] = task_data.get("task_id")

        logger.info(f"Reassigned task from worker {from_worker} to {to_worker}")
        return True

    def get_worker_by_role(self, role: str) -> Optional[int]:
        """Get a worker ID by role preference."""
        # First try exact role match
        for worker_id, worker in self.workers.items():
            if worker["role"] == role and worker["status"] == "idle":
                return worker_id

        # Fall back to any idle worker
        for worker_id, worker in self.workers.items():
            if worker["status"] == "idle":
                return worker_id

        return None

    def get_verificator_worker_id(self) -> Optional[int]:
        """Get the dedicated verificator worker ID."""
        for worker_id, worker in self.workers.items():
            if worker["role"] == "verificator":
                return worker_id
        return None

    def is_verificator_available(self) -> bool:
        """Check if the verificator worker is available (idle)."""
        worker_id = self.get_verificator_worker_id()
        if worker_id is None:
            return False
        return self.workers[worker_id]["status"] == "idle"

    async def dispatch_verification_task(
        self,
        task_type: str,
        task_data: Dict[str, Any],
        timeout_seconds: int = 60
    ) -> Optional[Dict[str, Any]]:
        """
        Dispatch a verification task to the verificator worker and wait for result.

        Args:
            task_type: One of SPECIFY_ARTIFACTS, VERIFY_COMPLETION, CHECK_DUPLICATE,
                      MATCH_PROJECT, AUDIT_COMPLETED, SEMANTIC_CHECK
            task_data: Context data for the verification
            timeout_seconds: Maximum time to wait for result

        Returns:
            Parsed JSON result from verificator, or None if failed/timeout
        """
        import uuid

        worker_id = self.get_verificator_worker_id()
        if worker_id is None:
            logger.error("No verificator worker found")
            return None

        worker = self.workers[worker_id]

        # Wait for worker to become available (with timeout)
        wait_start = datetime.now()
        while worker["status"] != "idle":
            await asyncio.sleep(0.5)
            if (datetime.now() - wait_start).total_seconds() > timeout_seconds:
                logger.warning(f"Verificator worker not available within {timeout_seconds}s timeout")
                return {
                    "error": "worker_busy",
                    "task_type": task_type,
                    "timeout_seconds": timeout_seconds,
                    "retryable": True,
                    "message": f"Verificator worker was busy for {timeout_seconds} seconds"
                }

        # Build verification prompt
        prompt = self._build_verification_prompt(task_type, task_data)

        # Create unique task ID
        verification_task_id = f"verify-{task_type.lower()}-{uuid.uuid4().hex[:8]}"

        # Dispatch task
        task_json = {
            "task_id": verification_task_id,
            "prompt": prompt,
            "cwd": task_data.get("project_path", "/workspace"),
            "dispatched_at": datetime.now().isoformat()
        }

        pending_file = worker["ipc_dir"] / "pending.json"
        pending_file.write_text(json.dumps(task_json, indent=2))

        worker["status"] = "busy"
        worker["current_task"] = verification_task_id

        logger.info(f"Dispatched verification task {verification_task_id} ({task_type})")

        # Wait for result
        result_file = worker["ipc_dir"] / "result.json"
        start_time = datetime.now()

        while (datetime.now() - start_time).total_seconds() < timeout_seconds:
            if result_file.exists():
                try:
                    result_data = json.loads(result_file.read_text())
                    result_file.unlink()

                    worker["status"] = "idle"
                    worker["current_task"] = None

                    # Parse the actual output from Claude's response
                    output = result_data.get("output", "")
                    return self._parse_verification_result(output, task_type)

                except json.JSONDecodeError as e:
                    logger.error(f"Invalid result JSON: {e}")
                    worker["status"] = "idle"
                    worker["current_task"] = None
                    return None

            await asyncio.sleep(0.5)

        # Timeout - return error dict instead of None for retry handling
        logger.warning(f"Verification task {verification_task_id} timed out after {timeout_seconds}s")
        worker["status"] = "idle"
        worker["current_task"] = None
        return {
            "error": "timeout",
            "task_type": task_type,
            "task_id": verification_task_id,
            "timeout_seconds": timeout_seconds,
            "retryable": True,
            "message": f"Verification task {task_type} timed out after {timeout_seconds} seconds"
        }

    def _build_verification_prompt(self, task_type: str, task_data: Dict[str, Any]) -> str:
        """Build a structured verification prompt."""
        prompts = {
            "SPECIFY_ARTIFACTS": f"""TASK TYPE: SPECIFY_ARTIFACTS

Analyze this task and determine what files/endpoints it should create:

TASK TITLE: {task_data.get('title', 'Unknown')}
TASK DESCRIPTION: {task_data.get('description', 'No description')}
PROJECT PATH: {task_data.get('project_path', '/workspace')}

Based on the task description:
1. What specific files should be created? (include full paths relative to project root)
2. What API endpoints should be created? (if applicable)
3. What other artifacts are expected?

Respond with JSON:
{{"artifacts": ["path/to/file1.py", "path/to/file2.ts"], "reasoning": "explanation"}}""",

            "VERIFY_COMPLETION": f"""TASK TYPE: VERIFY_COMPLETION

Verify if this completed task actually created what it claimed:

TASK TITLE: {task_data.get('title', 'Unknown')}
TASK DESCRIPTION: {task_data.get('description', 'No description')}
EXPECTED ARTIFACTS: {json.dumps(task_data.get('expected_artifacts', []))}
PROJECT PATH: {task_data.get('project_path', '/workspace')}
TASK RESULT: {task_data.get('result', 'No result provided')}

Check if the expected artifacts actually exist in the project.
Use ls and cat commands to verify file existence and content.

Respond with JSON:
{{"verified": true/false, "missing": [], "found": [], "reasoning": "explanation"}}""",

            "CHECK_DUPLICATE": f"""TASK TYPE: CHECK_DUPLICATE

Determine if these two tasks are semantically the same (even if worded differently):

TASK 1 TITLE: {task_data.get('task1_title', 'Unknown')}
TASK 1 DESCRIPTION: {task_data.get('task1_description', '')}

TASK 2 TITLE: {task_data.get('task2_title', 'Unknown')}
TASK 2 DESCRIPTION: {task_data.get('task2_description', '')}

Consider:
- Do they create the same files/artifacts?
- Do they implement the same functionality?
- Would completing one make the other redundant?

Respond with JSON:
{{"is_duplicate": true/false, "confidence": 0.0-1.0, "reasoning": "explanation"}}""",

            "MATCH_PROJECT": f"""TASK TYPE: MATCH_PROJECT

Match this objective to the correct project:

OBJECTIVE: {task_data.get('objective_content', 'Unknown')}

AVAILABLE PROJECTS:
{json.dumps(task_data.get('projects', []), indent=2)}

Analyze the objective content and determine which project it refers to.
Consider: project names, technology stacks, described functionality.

Respond with JSON:
{{"project_path": "/workspace/project-name", "confidence": 0.0-1.0, "reasoning": "explanation"}}""",

            "AUDIT_COMPLETED": f"""TASK TYPE: AUDIT_COMPLETED

Audit this completed task to verify its artifacts actually exist:

TASK ID: {task_data.get('task_id', 'Unknown')}
TASK TITLE: {task_data.get('title', 'Unknown')}
EXPECTED ARTIFACTS: {json.dumps(task_data.get('expected_artifacts', []))}
PROJECT PATH: {task_data.get('project_path', '/workspace')}

Use file system commands to check if each artifact exists.
For each missing artifact, note if it's critical or optional.

Respond with JSON:
{{"passed": true/false, "missing_artifacts": [], "recommendation": "re-run"/"accept"/"manual-review"}}""",

            "SEMANTIC_CHECK": f"""TASK TYPE: SEMANTIC_CHECK

Check if the task output semantically matches what was requested:

TASK TITLE: {task_data.get('title', 'Unknown')}
TASK DESCRIPTION: {task_data.get('description', 'No description')}
TASK OUTPUT/RESULT: {task_data.get('result', 'No result')}
FILES CREATED: {json.dumps(task_data.get('files_created', []))}

Analyze:
1. Does the output match the task requirements?
2. What percentage of the requirements are covered?
3. What gaps exist?

Respond with JSON:
{{"matches": true/false, "coverage": 0.0-1.0, "gaps": [], "reasoning": "explanation"}}""",
        }

        return prompts.get(task_type, prompts["SEMANTIC_CHECK"])

    def _parse_verification_result(self, output: str, task_type: str) -> Optional[Dict[str, Any]]:
        """Parse the JSON result from verificator output."""
        import re

        # Try to extract JSON from the output
        # Claude might include some text before/after the JSON

        # First try direct parse
        try:
            return json.loads(output.strip())
        except json.JSONDecodeError:
            pass

        # Try to find JSON block
        json_patterns = [
            r'\{[\s\S]*\}',  # Any JSON object
            r'```json\s*(\{[\s\S]*?\})\s*```',  # Code block
            r'```\s*(\{[\s\S]*?\})\s*```',  # Code block without json
        ]

        for pattern in json_patterns:
            match = re.search(pattern, output)
            if match:
                try:
                    json_str = match.group(1) if '```' in pattern else match.group(0)
                    return json.loads(json_str)
                except (json.JSONDecodeError, IndexError):
                    continue

        logger.warning(f"Could not parse verification result for {task_type}: {output[:200]}")
        return None
