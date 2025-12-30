# =============================================================================
# CLOPUS v3 Worker Pool
# =============================================================================
"""
Manages the pool of Claude Code worker instances.
Handles task dispatch, result collection, and worker health monitoring.

NEW IN v3.2: AI-First Intelligence Integration
- Supports AI-first inference task types
- Error recovery intelligence
- Task dependency analysis
- Commit strategy, test selection, doc updates
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import logging

from .config import WorkerConfig

if TYPE_CHECKING:
    from .ai_first import AIFirstEngine

logger = logging.getLogger("clopus.worker_pool")


class WorkerPool:
    """
    Manage Claude Code worker instances.

    NEW IN v3.2: AI-First Intelligence Integration
    - Supports AI-first inference task types for error recovery,
      dependency analysis, commit strategy, test selection, etc.
    """

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

        # AI-First Engine (set by orchestrator, NEW in v3.2)
        self.ai_engine: Optional["AIFirstEngine"] = None

        # Verification results cache - stores results by task_id to prevent race conditions
        # between collect_results() background loop and dispatch_verification_task()
        self._verification_results: Dict[str, Dict] = {}

    def set_ai_engine(self, ai_engine: "AIFirstEngine") -> None:
        """Set the AI-first engine for intelligent task processing."""
        self.ai_engine = ai_engine
        logger.info("AI-First Engine connected to worker pool")

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
        ack_timeout: int = 10,
        session_mode: str = "auto",
        resume_session: Optional[str] = None
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
            session_mode: Claude Code session mode ('auto', 'continue', 'new')
            resume_session: Optional session ID to resume

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

        # Create task file with session handling
        task_data = {
            "task_id": task_id,
            "prompt": prompt,
            "cwd": cwd,
            "dispatched_at": datetime.now().isoformat(),
            "session_mode": session_mode
        }

        # Add session resume if provided
        if resume_session:
            task_data["resume_session"] = resume_session

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
        # browser-headless and browser-chrome are now assignable for browser automation tasks
        reserved = getattr(
            self.config, 'reserved_roles',
            ['heartbeat', 'verificator', 'services']
        )
        return role in reserved

    def get_heartbeat_worker_id(self) -> Optional[int]:
        """Get the dedicated heartbeat worker ID."""
        for worker_id, worker in self.workers.items():
            if worker["role"] == "heartbeat":
                return worker_id
        return None

    def get_worker_session(self, worker_id: int) -> Optional[str]:
        """Get the last session ID for a worker.

        Useful for continuing sessions when dispatching follow-up tasks.
        """
        if worker_id in self.workers:
            return self.workers[worker_id].get("last_session_id")
        return None

    def get_session_for_project(self, project_path: str, role: str) -> Optional[str]:
        """Find a session ID for a specific project/role combination.

        Searches all workers with the given role for a session in the specified project.
        """
        for worker_id, worker in self.workers.items():
            if worker["role"] == role:
                session_file = worker["ipc_dir"] / "session.json"
                if session_file.exists():
                    try:
                        session_data = json.loads(session_file.read_text())
                        if session_data.get("project") == project_path:
                            return session_data.get("session_id")
                    except (json.JSONDecodeError, OSError):
                        continue
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
        Always check for result files regardless of internal status tracking,
        since workers update their status independently.
        """
        results = {}

        for worker_id, worker in self.workers.items():
            # IMPORTANT: Always check for result files, not just "busy" workers
            # Workers update their own status.json to "idle" after completing tasks,
            # but our internal tracking may be out of sync. A result.json file
            # indicates a task was completed and needs processing.
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

                    # Track session ID for future task continuations
                    session_id = result_data.get("session_id")
                    if session_id:
                        worker["last_session_id"] = session_id
                        logger.debug(f"Worker {worker_id} session: {session_id}")

                    # Cache verification results for dispatch_verification_task to retrieve
                    task_id = result_data.get("task_id")
                    if task_id and task_id.startswith("verify-"):
                        self._verification_results[task_id] = result_data
                        logger.debug(f"Cached verification result: {task_id}")

                    logger.info(f"Collected result from worker {worker_id}: {task_id}")

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
        creds_status_file = worker["ipc_dir"] / "credentials_status.json"

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

        # Include credential status if available
        if creds_status_file.exists():
            try:
                creds_status = json.loads(creds_status_file.read_text())
                status["credentials"] = creds_status
            except json.JSONDecodeError:
                pass

        return status

    async def get_credentials_health(self) -> Dict[str, Any]:
        """
        Get credential health status for all workers.

        Returns a summary including:
        - Workers with expired tokens
        - Workers with tokens expiring soon (< 2 hours)
        - Overall health status
        """
        health = {
            "healthy": True,
            "expired_workers": [],
            "expiring_soon_workers": [],
            "worker_details": {},
            "min_hours_remaining": float("inf"),
            "host_token_hours": None
        }

        # Check host token (via IPC mount point reference)
        host_creds_path = Path("/app/ipc/../.claude/.credentials.json")
        if not host_creds_path.exists():
            # Try alternative path
            host_creds_path = Path.home() / ".claude" / ".credentials.json"

        if host_creds_path.exists():
            try:
                import time
                creds = json.loads(host_creds_path.read_text())
                expires_at = creds.get("claudeAiOauth", {}).get("expiresAt", 0)
                if expires_at > 0:
                    hours_left = (expires_at / 1000 - time.time()) / 3600
                    health["host_token_hours"] = round(hours_left, 2)
            except:
                pass

        for worker_id, worker in self.workers.items():
            creds_file = worker["ipc_dir"] / "credentials_status.json"
            if creds_file.exists():
                try:
                    creds_status = json.loads(creds_file.read_text())
                    hours = creds_status.get("token_expires_hours", -999)

                    health["worker_details"][worker_id] = {
                        "role": worker["role"],
                        "hours_remaining": hours,
                        "last_sync": creds_status.get("last_sync")
                    }

                    if hours < health["min_hours_remaining"]:
                        health["min_hours_remaining"] = hours

                    if hours < 0:
                        health["expired_workers"].append(worker_id)
                        health["healthy"] = False
                    elif hours < 2:
                        health["expiring_soon_workers"].append(worker_id)
                except:
                    pass

        if health["min_hours_remaining"] == float("inf"):
            health["min_hours_remaining"] = None

        return health

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
        timeout_seconds: int = 60,
        session_mode: str = "auto",
        resume_session: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Dispatch a verification task to the verificator worker and wait for result.

        Args:
            task_type: One of SPECIFY_ARTIFACTS, VERIFY_COMPLETION, CHECK_DUPLICATE,
                      MATCH_PROJECT, AUDIT_COMPLETED, SEMANTIC_CHECK,
                      OBJECTIVE_ANALYSIS, TASK_GENERATION
            task_data: Context data for the verification
            timeout_seconds: Maximum time to wait for result
            session_mode: Claude Code session mode ('auto', 'continue', 'new')
            resume_session: Optional session ID to resume

        Returns:
            Parsed JSON result from verificator, or None if failed/timeout
        """
        import uuid

        worker_id = self.get_verificator_worker_id()
        if worker_id is None:
            logger.error("No verificator worker found")
            return None

        worker = self.workers[worker_id]

        # Helper to check actual worker status from IPC file
        def is_worker_actually_idle() -> bool:
            """Check file-based status, not just in-memory status."""
            status_file = worker["ipc_dir"] / "status.json"
            pending_file = worker["ipc_dir"] / "pending.json"

            # If there's a pending task, worker is not idle
            if pending_file.exists():
                return False

            # Check the worker's self-reported status
            if status_file.exists():
                try:
                    file_status = json.loads(status_file.read_text())
                    return file_status.get("status") == "idle"
                except:
                    pass

            # Fallback to in-memory status
            return worker["status"] == "idle"

        # Wait for worker to become available (with timeout)
        # Check BOTH in-memory and file-based status to avoid race conditions
        # For AI planning tasks (long timeout), wait up to half the timeout for availability
        wait_start = datetime.now()
        wait_timeout = min(timeout_seconds // 2, 180)  # Up to 3 minutes wait for availability

        logger.debug(f"Waiting up to {wait_timeout}s for verificator to become idle...")

        while not is_worker_actually_idle():
            await asyncio.sleep(0.5)
            elapsed = (datetime.now() - wait_start).total_seconds()
            if elapsed > wait_timeout:
                logger.warning(f"Verificator worker not available within {wait_timeout}s timeout")
                return {
                    "error": "worker_busy",
                    "task_type": task_type,
                    "timeout_seconds": timeout_seconds,
                    "retryable": True,
                    "message": f"Verificator worker was busy for {wait_timeout} seconds"
                }
            # Log progress every 30s
            if int(elapsed) % 30 == 0 and int(elapsed) > 0:
                logger.info(f"Still waiting for verificator... ({int(elapsed)}s elapsed)")

        # Sync in-memory status with file status
        worker["status"] = "idle"

        # Build verification prompt
        prompt = self._build_verification_prompt(task_type, task_data)

        # Create unique task ID
        verification_task_id = f"verify-{task_type.lower()}-{uuid.uuid4().hex[:8]}"

        # Dispatch task with session handling
        task_json = {
            "task_id": verification_task_id,
            "prompt": prompt,
            "cwd": task_data.get("project_path", "/workspace"),
            "dispatched_at": datetime.now().isoformat(),
            "session_mode": session_mode
        }

        # Add session resume if provided
        if resume_session:
            task_json["resume_session"] = resume_session

        pending_file = worker["ipc_dir"] / "pending.json"
        pending_file.write_text(json.dumps(task_json, indent=2))

        worker["status"] = "busy"
        worker["current_task"] = verification_task_id

        logger.info(f"Dispatched verification task {verification_task_id} ({task_type})")

        # Wait for result - check both file and cache to handle race conditions
        result_file = worker["ipc_dir"] / "result.json"
        start_time = datetime.now()

        while (datetime.now() - start_time).total_seconds() < timeout_seconds:
            # First check the cache (in case background collector already got it)
            if verification_task_id in self._verification_results:
                result_data = self._verification_results.pop(verification_task_id)
                logger.debug(f"Retrieved verification result from cache: {verification_task_id}")

                worker["status"] = "idle"
                worker["current_task"] = None

                # Capture session ID for future continuations
                session_id = result_data.get("session_id")
                if session_id:
                    worker["last_session_id"] = session_id
                    logger.debug(f"Verification worker session: {session_id}")

                # Parse the actual output from Claude's response
                output = result_data.get("result", result_data.get("output", ""))
                parsed_result = self._parse_verification_result(output, task_type)

                # Include session ID in result for AI planner session continuity
                if parsed_result and isinstance(parsed_result, dict):
                    parsed_result["_session_id"] = session_id
                elif parsed_result:
                    parsed_result = {"result": parsed_result, "_session_id": session_id}

                return parsed_result

            # Then check the file directly
            if result_file.exists():
                try:
                    result_data = json.loads(result_file.read_text())

                    # Verify this result is for our task
                    result_task_id = result_data.get("task_id")
                    if result_task_id != verification_task_id:
                        # This is a result for a different task - cache it and keep waiting
                        logger.debug(f"Found result for different task: {result_task_id}, waiting for {verification_task_id}")
                        self._verification_results[result_task_id] = result_data
                        result_file.unlink()
                        await asyncio.sleep(0.5)
                        continue

                    result_file.unlink()

                    worker["status"] = "idle"
                    worker["current_task"] = None

                    # Capture session ID for future continuations
                    session_id = result_data.get("session_id")
                    if session_id:
                        worker["last_session_id"] = session_id
                        logger.debug(f"Verification worker session: {session_id}")

                    # Parse the actual output from Claude's response
                    output = result_data.get("result", result_data.get("output", ""))
                    parsed_result = self._parse_verification_result(output, task_type)

                    # Include session ID in result for AI planner session continuity
                    if parsed_result and isinstance(parsed_result, dict):
                        parsed_result["_session_id"] = session_id
                    elif parsed_result:
                        parsed_result = {"result": parsed_result, "_session_id": session_id}

                    return parsed_result

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

            "ARCHITECTURAL_ANALYSIS": f"""TASK TYPE: ARCHITECTURAL_ANALYSIS

{task_data.get('instructions', 'Perform a full architectural analysis.')}

PROJECT PATH: {task_data.get('project_path', '/workspace')}
ANALYSIS TYPE: {task_data.get('analysis_type', 'full')}

Your job is to READ THE ACTUAL CODE and verify implementation matches requirements:

1. READ the CLAUDE.md file to understand project requirements
2. READ the actual source files in app/api/, app/models/, etc.
3. VERIFY code semantically does what it claims:
   - Do endpoints actually USE the database models? Or do they use in-memory dicts?
   - Is authentication actually implemented? Or just scaffolded?
   - Is caching actually used? Or just imported but unused?
4. Look for anti-patterns that indicate incomplete integration:
   - `_db: dict = {{}}` or `_storage = {{}}` (in-memory storage)
   - Missing `Depends(get_db)` in endpoint signatures
   - Models imported but never instantiated
   - Comments like "# TODO: implement" or "# In-memory for now"

For each gap found, provide:
- What the CLAUDE.md/requirements say
- What the code ACTUALLY does
- Specific files that need fixing
- Exact steps to remediate

Respond with JSON:
{{
  "gaps": [
    {{
      "requirement": "what was required",
      "actual_state": "what the code actually does",
      "severity": "critical|high|medium|low",
      "category": "database|auth|cache|api|frontend",
      "files_affected": ["app/api/v1/endpoints/nodes.py"],
      "remediation_steps": ["Replace _nodes_db dict with SQLAlchemy session", "Add Depends(get_db) to endpoints"]
    }}
  ],
  "overall_compliance": 0.0-1.0,
  "reasoning": "explanation of analysis"
}}""",

            "PERSISTENCE_TEST": f"""TASK TYPE: PERSISTENCE_TEST

{task_data.get('instructions', 'Test that data persists across service restarts.')}

PROJECT PATH: {task_data.get('project_path', '/workspace')}
API PORT: {task_data.get('api_port', 8000)}

This is a RUNTIME TEST to verify data actually persists:

1. Check if the API is running (or start it)
2. Create a test record via the API (POST request)
3. Note the record ID
4. Stop/restart the API service
5. Try to retrieve the record (GET request)
6. If the record is NOT found:
   - This PROVES in-memory storage is being used
   - Data does NOT persist
   - Database integration is REQUIRED

Return your findings:
{{
  "persistence_passed": true/false,
  "persistence_failed": true/false,
  "test_details": {{
    "record_created": true/false,
    "record_id": "uuid...",
    "record_found_after_restart": true/false
  }},
  "files_affected": ["app/api/v1/endpoints/nodes.py"],
  "remediation_steps": ["Replace in-memory dict with SQLAlchemy session", "..."]
}}""",

            # =====================================================================
            # AI PLANNING TASK TYPES (NEW in v3.1)
            # These enable AI-first task generation instead of template-based
            # =====================================================================

            "OBJECTIVE_ANALYSIS": f"""TASK TYPE: OBJECTIVE_ANALYSIS

{task_data.get('prompt', 'Analyze this objective.')}

You are analyzing an objective for CLOPUS, a universal autonomous agent system.
This agent can build ANYTHING - not just predefined project types.

CRITICAL: Do NOT use pattern matching or templates. Use YOUR INTELLIGENCE to understand
what the user wants and design a custom solution tailored to their specific needs.

The output MUST be valid JSON that can be parsed. No additional text before or after the JSON.""",

            "TASK_GENERATION": f"""TASK TYPE: TASK_GENERATION

{task_data.get('prompt', 'Generate tasks for this project.')}

You are generating tasks for CLOPUS, a universal autonomous agent system.
Generate SPECIFIC, ACTIONABLE tasks tailored to this exact project.

CRITICAL:
- Do NOT use generic task templates
- Tasks must be specific to the requirements
- Include expected file paths and validation criteria
- Each task should produce concrete, verifiable artifacts

The output MUST be valid JSON that can be parsed. No additional text before or after the JSON.""",

            # =====================================================================
            # AI-FIRST INFERENCE TASK TYPES (NEW in v3.2)
            # Replace all regex/pattern matching with Claude intelligence
            # =====================================================================

            "ARTIFACT_INFERENCE": f"""TASK TYPE: ARTIFACT_INFERENCE

{task_data.get('prompt', 'Infer expected artifacts from this task.')}

You are analyzing a task to determine what files, endpoints, or artifacts it should create.

Use YOUR INTELLIGENCE to understand the task intent, not pattern matching.
For example:
- "Implement user authentication" → auth.py, middleware/auth.py, tests/test_auth.py
- "Add dark mode toggle" → ThemeToggle.tsx, theme.css, useTheme.ts

RESPOND WITH JSON ONLY:
{{
    "artifacts": [
        {{"type": "file", "path": "path/to/file.py", "purpose": "why this file"}},
        {{"type": "endpoint", "path": "/api/users", "method": "POST", "purpose": "why"}},
        {{"type": "component", "name": "UserProfile", "path": "src/components/UserProfile.tsx"}}
    ],
    "confidence": 0.85,
    "reasoning": "Based on the task description..."
}}""",

            "PROJECT_DETECTION": f"""TASK TYPE: PROJECT_DETECTION

{task_data.get('prompt', 'Detect which project this task belongs to.')}

You are determining which project a task should run in.

Use YOUR INTELLIGENCE to understand the task context, not keyword matching.
For example:
- "Fix the API endpoint" + projects=[nexus-api, nexus-web] → nexus-api
- "Update the React component" → likely a web/frontend project

Available Projects: {task_data.get('available_projects', [])}

RESPOND WITH JSON ONLY:
{{
    "project_path": "/workspace/project-name",
    "confidence": 0.9,
    "reasoning": "This task mentions X which is in project Y"
}}""",

            "DUPLICATE_CHECK": f"""TASK TYPE: DUPLICATE_CHECK

{task_data.get('prompt', 'Check if these tasks are duplicates.')}

You are determining if two tasks are semantically the same (doing the same work).

Use YOUR INTELLIGENCE to understand intent, not word overlap.
For example:
- "Create user model" vs "Implement User SQLAlchemy model" → DUPLICATE
- "Add login endpoint" vs "Create user registration" → NOT DUPLICATE

RESPOND WITH JSON ONLY:
{{
    "is_duplicate": true/false,
    "similarity": 0.95,
    "reasoning": "Both tasks are creating the same...",
    "differences": ["Task 1 also includes X", "Task 2 focuses on Y"]
}}""",

            "TECH_DETECTION": f"""TASK TYPE: TECH_DETECTION

{task_data.get('prompt', 'Detect technologies for this project.')}

You are determining what technologies a project should use.

Use YOUR INTELLIGENCE to understand requirements, not keyword matching.
For example:
- "Modern web app" → React, TypeScript, Tailwind (inferred)
- "Real-time features" → WebSocket, Redis (inferred)

RESPOND WITH JSON ONLY:
{{
    "technologies": [
        {{"name": "React", "category": "frontend", "confidence": 0.95, "reason": "explicitly mentioned"}},
        {{"name": "TypeScript", "category": "language", "confidence": 0.8, "reason": "implied by React + modern"}}
    ],
    "stack_summary": "React + TypeScript frontend with FastAPI backend",
    "recommendations": ["Consider adding Tailwind for styling"]
}}""",

            "FEATURE_EXTRACTION": f"""TASK TYPE: FEATURE_EXTRACTION

{task_data.get('prompt', 'Extract features from this objective.')}

You are extracting features from an objective description.

Use YOUR INTELLIGENCE to understand both explicit and implicit features.
For example:
- "with dark mode and user auth" → [dark mode, user authentication]
- Implicit features: login implies signup, logout, password reset

RESPOND WITH JSON ONLY:
{{
    "features": [
        {{"name": "User Authentication", "explicit": true, "priority": "high", "subfeatures": ["login", "logout", "signup"]}},
        {{"name": "Dark Mode", "explicit": true, "priority": "medium", "subfeatures": ["theme toggle", "system preference detection"]}}
    ],
    "total_scope": "medium",
    "missing_clarifications": ["Which OAuth providers to support?"]
}}""",

            "SKILL_MATCHING": f"""TASK TYPE: SKILL_MATCHING

{task_data.get('prompt', 'Match skills for this task.')}

You are determining which skills are most relevant for a task.

Use YOUR INTELLIGENCE to understand semantic relevance, not keyword overlap.
For example:
- "Implement REST API" → [fastapi, api-design, testing]
- The skill descriptions tell you what each skill does

RESPOND WITH JSON ONLY:
{{
    "matched_skills": [
        {{"name": "fastapi", "relevance": 0.95, "reason": "Task involves API development"}},
        {{"name": "testing", "relevance": 0.7, "reason": "APIs should have tests"}}
    ],
    "skill_load_order": ["fastapi", "api-design", "testing"]
}}""",

            "ENTITY_EXTRACTION": f"""TASK TYPE: ENTITY_EXTRACTION

{task_data.get('prompt', 'Extract entities from this text.')}

You are extracting entities (models, components, endpoints, etc.) from text.

Use YOUR INTELLIGENCE to understand context-dependent entity types.
For example:
- "User profile with avatar" → User (model), Avatar (component)
- Relationships between entities

RESPOND WITH JSON ONLY:
{{
    "entities": [
        {{"name": "User", "type": "model", "context": "user profile", "attributes": ["name", "email", "avatar"]}},
        {{"name": "UserProfile", "type": "component", "context": "display user info"}},
        {{"name": "/users", "type": "endpoint", "methods": ["GET", "POST", "PUT"]}}
    ],
    "relationships": [
        {{"from": "UserProfile", "to": "User", "type": "displays"}}
    ]
}}""",

            # =====================================================================
            # AI-FIRST INFERENCE TASK TYPES - Part 2 (NEW in v3.2)
            # Additional intelligence for autonomous operation
            # =====================================================================

            "ERROR_RECOVERY": f"""TASK TYPE: ERROR_RECOVERY

{task_data.get('prompt', 'Diagnose this error and recommend recovery.')}

You are diagnosing an error and recommending a recovery strategy.

Error: {task_data.get('error', 'Unknown error')}
Context: {task_data.get('context', 'No context provided')}
Failed Task: {task_data.get('failed_task', 'Unknown task')}
Retry Count: {task_data.get('retry_count', 0)}

Use YOUR INTELLIGENCE to understand the root cause and suggest fixes.

RESPOND WITH JSON ONLY:
{{
    "diagnosis": "Root cause analysis...",
    "severity": "critical|high|medium|low",
    "recovery_strategy": "retry|modify_task|skip|escalate|manual",
    "recommended_actions": [
        {{"action": "Specific action to take", "priority": 1}},
        {{"action": "Second action", "priority": 2}}
    ],
    "modified_task": null or {{"title": "...", "description": "..."}},
    "confidence": 0.85,
    "requires_user_input": true/false
}}""",

            "DEPENDENCY_ANALYSIS": f"""TASK TYPE: DEPENDENCY_ANALYSIS

{task_data.get('prompt', 'Analyze task dependencies.')}

You are analyzing task dependencies to determine execution order.

Tasks: {json.dumps(task_data.get('tasks', []), indent=2)}

Use YOUR INTELLIGENCE to understand semantic dependencies, not just explicit ones.
For example:
- "Add user model" must come before "Add user endpoints"
- "Setup project" is implicitly a dependency for everything

RESPOND WITH JSON ONLY:
{{
    "dependency_graph": {{
        "task_id_1": ["depends_on_task_id_2", "depends_on_task_id_3"],
        "task_id_2": []
    }},
    "execution_order": ["task_id_2", "task_id_1"],
    "parallel_groups": [
        ["task_a", "task_b"],
        ["task_c"]
    ],
    "critical_path": ["task_x", "task_y", "task_z"],
    "reasoning": "Task X must complete before Y because..."
}}""",

            "COMMIT_STRATEGY": f"""TASK TYPE: COMMIT_STRATEGY

{task_data.get('prompt', 'Plan commit strategy.')}

You are planning how to commit changes logically.

Changes: {json.dumps(task_data.get('changes', []), indent=2)}
Files Modified: {task_data.get('files_modified', [])}

Use YOUR INTELLIGENCE to group related changes and write good commit messages.

RESPOND WITH JSON ONLY:
{{
    "commits": [
        {{
            "files": ["file1.py", "file2.py"],
            "message": "feat: Add user authentication",
            "type": "feat|fix|refactor|docs|test|chore",
            "scope": "auth",
            "breaking": false
        }}
    ],
    "commit_order": [0, 1, 2],
    "reasoning": "Grouping auth-related changes together..."
}}""",

            "TEST_SELECTION": f"""TASK TYPE: TEST_SELECTION

{task_data.get('prompt', 'Select tests to run.')}

You are selecting which tests to run based on changes made.

Changes: {json.dumps(task_data.get('changes', []), indent=2)}
Available Tests: {task_data.get('available_tests', [])}
Test Types: unit, integration, e2e

Use YOUR INTELLIGENCE to select relevant tests, not just matching filenames.

RESPOND WITH JSON ONLY:
{{
    "tests_to_run": [
        {{"test": "test_auth.py", "reason": "Auth module was modified", "priority": 1}},
        {{"test": "test_api.py", "reason": "API depends on auth", "priority": 2}}
    ],
    "test_order": ["unit", "integration", "e2e"],
    "estimated_duration": "5 minutes",
    "skip_reasons": {{
        "test_unrelated.py": "No changes affect this test"
    }}
}}""",

            "DOC_UPDATE_SUGGESTION": f"""TASK TYPE: DOC_UPDATE_SUGGESTION

{task_data.get('prompt', 'Suggest documentation updates.')}

You are suggesting which documentation needs updating based on code changes.

Changes: {json.dumps(task_data.get('changes', []), indent=2)}
Existing Docs: {task_data.get('existing_docs', [])}

Use YOUR INTELLIGENCE to identify documentation that needs updating.

RESPOND WITH JSON ONLY:
{{
    "updates_needed": [
        {{
            "doc_path": "README.md",
            "section": "API Endpoints",
            "change_type": "add|update|remove",
            "reason": "New endpoint added",
            "suggested_content": "## New Endpoint\\n..."
        }}
    ],
    "new_docs_suggested": [
        {{"path": "docs/auth.md", "purpose": "Document authentication flow"}}
    ],
    "priority": "high|medium|low"
}}""",

            "QUALITY_PREDICTION": f"""TASK TYPE: QUALITY_PREDICTION

{task_data.get('prompt', 'Predict quality issues.')}

You are predicting potential quality issues before they occur.

Task: {task_data.get('task_description', 'Unknown task')}
Code Changes: {task_data.get('code_changes', 'No changes')}
Project Context: {task_data.get('context', 'No context')}

Use YOUR INTELLIGENCE to identify potential issues proactively.

RESPOND WITH JSON ONLY:
{{
    "predicted_issues": [
        {{
            "type": "security|performance|reliability|maintainability",
            "description": "Potential SQL injection in user input",
            "severity": "critical|high|medium|low",
            "likelihood": 0.8,
            "prevention": "Use parameterized queries",
            "affected_files": ["app/api/users.py"]
        }}
    ],
    "overall_risk_score": 0.3,
    "recommendations": ["Add input validation", "Add rate limiting"],
    "confidence": 0.85
}}""",
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
