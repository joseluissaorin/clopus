# =============================================================================
# CLOPUS v3 Collaboration Manager
# =============================================================================
"""
Manages inter-worker collaboration via the IPC system.
Monitors collaboration requests, routes them to appropriate workers,
and delivers responses back to requesting workers.
"""

import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("clopus.collaboration")


class RequestType(str, Enum):
    """Types of collaboration requests."""
    HELP_REQUEST = "help_request"
    BROWSER_ACTION = "browser_action"
    E2E_TEST = "e2e_test"
    SCREENSHOT = "screenshot"


class EventType(str, Enum):
    """Types of collaboration events (async)."""
    SPAWN_SUBTASK = "spawn_subtask"
    SHARE_LEARNING = "share_learning"
    REPORT_ISSUE = "report_issue"
    UPDATE_CONTEXT = "update_context"


@dataclass
class CollaborationRequest:
    """Represents a collaboration request from a worker."""
    id: str
    type: RequestType
    from_worker_id: str
    from_role: str
    to_role: str
    question: Optional[str] = None
    action: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 60
    created_at: str = ""

    # Internal tracking
    task_id: Optional[str] = None
    dispatched_at: Optional[datetime] = None


@dataclass
class CollaborationEvent:
    """Represents an async event from a worker."""
    id: str
    type: EventType
    from_worker_id: str
    from_role: str
    payload: Dict[str, Any]
    created_at: str


class CollaborationManager:
    """
    Manages inter-worker collaboration.

    Flow:
    1. Workers write requests to /app/ipc/collaboration/requests/{id}.json
    2. CollaborationManager monitors this directory
    3. Routes request to appropriate worker via task dispatch
    4. Collects result and writes to /app/ipc/collaboration/responses/{id}.json
    5. Requesting worker polls for response and consumes it
    """

    def __init__(
        self,
        worker_pool,
        memory_client,
        ipc_path: str = "/app/ipc"
    ):
        self.worker_pool = worker_pool
        self.memory = memory_client
        self.ipc_path = Path(ipc_path)
        self.collab_path = self.ipc_path / "collaboration"

        # Active request tracking
        self.pending_requests: Dict[str, CollaborationRequest] = {}

        # Rate limiting
        self.last_scan = datetime.now()
        self.scan_interval = 0.5  # seconds

        self._running = False

    async def initialize(self) -> None:
        """Initialize collaboration directories."""
        logger.info("Initializing collaboration manager")

        # Create directories
        dirs = [
            self.collab_path / "requests",
            self.collab_path / "responses",
            self.collab_path / "events",
            self.collab_path / "screenshots",
            self.ipc_path / "memory" / "shared",
        ]

        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Clean up stale files from previous runs
        await self._cleanup_stale_files()

        self._running = True
        logger.info("Collaboration manager initialized")

    async def _cleanup_stale_files(self) -> None:
        """Clean up stale request/response files from previous runs."""
        # Clean requests older than 5 minutes
        cutoff = datetime.now() - timedelta(minutes=5)

        for requests_dir in [self.collab_path / "requests", self.collab_path / "responses"]:
            if requests_dir.exists():
                for file in requests_dir.glob("*.json"):
                    try:
                        stat = file.stat()
                        if datetime.fromtimestamp(stat.st_mtime) < cutoff:
                            file.unlink()
                            logger.info(f"Cleaned up stale file: {file.name}")
                    except Exception as e:
                        logger.warning(f"Could not clean up {file}: {e}")

    async def process_collaboration(self) -> None:
        """
        Main collaboration processing loop.
        Call this regularly from the orchestrator's main loop.
        """
        if not self._running:
            return

        # Process pending requests
        await self._scan_requests()

        # Process events (spawn_subtask, share_learning, etc.)
        await self._scan_events()

        # Check for completed tasks and deliver responses
        await self._check_pending_responses()

    async def _scan_requests(self) -> None:
        """Scan for new collaboration requests."""
        requests_dir = self.collab_path / "requests"

        for request_file in requests_dir.glob("*.json"):
            request_id = request_file.stem

            # Skip if already being processed
            if request_id in self.pending_requests:
                continue

            try:
                data = json.loads(request_file.read_text())
                request = CollaborationRequest(
                    id=data["id"],
                    type=RequestType(data["type"]),
                    from_worker_id=data["from_worker_id"],
                    from_role=data.get("from_role", "unknown"),
                    to_role=data.get("to_role", ""),
                    question=data.get("question"),
                    action=data.get("action"),
                    context=data.get("context", {}),
                    timeout_seconds=data.get("timeout_seconds", 60),
                    created_at=data.get("created_at", ""),
                )

                # Route the request
                await self._route_request(request)

            except Exception as e:
                logger.error(f"Error processing request {request_id}: {e}")
                # Write error response
                await self._write_error_response(request_id, str(e))

    async def _route_request(self, request: CollaborationRequest) -> None:
        """Route a request to the appropriate worker."""
        logger.info(f"Routing {request.type.value} request {request.id} from {request.from_role} to {request.to_role}")

        # Map request to target role
        target_role = request.to_role

        # Special handling for browser requests
        if request.type in [RequestType.BROWSER_ACTION, RequestType.E2E_TEST, RequestType.SCREENSHOT]:
            target_role = "browser-headless"

        # Find available worker with target role
        worker = await self._find_worker_for_role(target_role)

        if not worker:
            logger.warning(f"No available worker for role {target_role}")
            await self._write_error_response(
                request.id,
                f"No available worker for role: {target_role}. Request will retry."
            )
            return

        # Create a task for the worker
        task_description = self._create_task_description(request)

        # Store in pending tracking
        request.dispatched_at = datetime.now()
        self.pending_requests[request.id] = request

        # Dispatch to worker via IPC
        await self._dispatch_help_task(worker["id"], request, task_description)

    async def _find_worker_for_role(self, role: str) -> Optional[Dict]:
        """Find an idle worker with the specified role."""
        for worker_id, worker in self.worker_pool.workers.items():
            if worker["role"] == role and worker["status"] == "idle":
                return worker

        # If no idle worker, return any worker with the role
        for worker_id, worker in self.worker_pool.workers.items():
            if worker["role"] == role:
                return worker

        return None

    def _create_task_description(self, request: CollaborationRequest) -> str:
        """Create a task description for the target worker."""
        if request.type == RequestType.HELP_REQUEST:
            context_str = ""
            if request.context:
                context_str = f"\n\nContext:\n```json\n{json.dumps(request.context, indent=2)}\n```"

            return f"""## Help Request from {request.from_role.upper()} Worker

**Question:** {request.question}
{context_str}

**Instructions:**
- Answer the question based on your expertise
- Be concise but complete
- If you need more context, say so clearly

**Response Format:**
Provide your answer directly. This will be sent back to the requesting worker."""

        elif request.type == RequestType.BROWSER_ACTION:
            return f"""## Browser Automation Request

**Action:** {request.action}
**URL:** {request.context.get('url', 'Not specified')}

**Test Data:**
```json
{json.dumps(request.context.get('test_data', {}), indent=2)}
```

**Instructions:**
1. Use Playwright MCP to execute the requested action
2. Capture screenshots if requested: {request.context.get('capture_screenshots', True)}
3. Return results including any screenshots, console logs, and success status

**Response Format:**
Return a JSON object with:
- success: boolean
- steps_executed: array of step results
- screenshots: array of screenshot paths
- console_logs: any relevant logs
- error: error message if failed"""

        elif request.type == RequestType.E2E_TEST:
            return f"""## E2E Test Request

**Scenario:** {request.context.get('scenario')}
**Base URL:** {request.context.get('base_url', 'http://localhost:3000')}

**Steps:**
{json.dumps(request.context.get('steps', []), indent=2)}

**Assertions to verify:**
{json.dumps(request.context.get('assertions', []), indent=2)}

**Instructions:**
1. Navigate to the base URL
2. Execute each step using Playwright MCP
3. Verify each assertion
4. Capture screenshots at key points

**Response Format:**
Return JSON with:
- success: boolean
- assertions_passed: array of passed assertions
- assertions_failed: array of failed assertions
- screenshots: array of screenshot paths
- steps_executed: array of step results"""

        elif request.type == RequestType.SCREENSHOT:
            return f"""## Screenshot Request

**URL:** {request.context.get('url')}
**Selector:** {request.context.get('selector', 'Full page')}
**Full Page:** {request.context.get('full_page', False)}
**Wait For:** {request.context.get('wait_for', 'Page load')}

**Instructions:**
1. Navigate to the URL
2. Wait for the specified selector if provided
3. Capture screenshot
4. Save to /app/ipc/collaboration/screenshots/

**Response Format:**
Return JSON with:
- success: boolean
- screenshot_path: path to the saved screenshot
- page_title: title of the page"""

        return f"Unknown request type: {request.type}"

    async def _dispatch_help_task(
        self,
        worker_id: int,
        request: CollaborationRequest,
        description: str
    ) -> None:
        """Dispatch a help task to a worker via IPC."""
        worker_dir = self.ipc_path / "tasks" / str(worker_id)
        pending_file = worker_dir / "pending.json"

        # Create high-priority task
        task = {
            "id": f"collab_{request.id}",
            "title": f"[{request.type.value}] Help Request from {request.from_role}",
            "description": description,
            "priority": "urgent",
            "type": "help_request",
            "collaboration_id": request.id,
            "from_worker": request.from_worker_id,
            "from_role": request.from_role,
            "timeout_seconds": request.timeout_seconds,
            "dispatched_at": datetime.now().isoformat(),
        }

        # Write to pending file
        pending_file.write_text(json.dumps(task, indent=2))

        # Update request tracking
        request.task_id = task["id"]

        logger.info(f"Dispatched help task {task['id']} to worker {worker_id}")

    async def _check_pending_responses(self) -> None:
        """Check for completed help tasks and deliver responses."""
        now = datetime.now()
        completed = []

        for request_id, request in self.pending_requests.items():
            # Check for timeout
            if request.dispatched_at:
                elapsed = (now - request.dispatched_at).total_seconds()
                if elapsed > request.timeout_seconds:
                    logger.warning(f"Request {request_id} timed out after {elapsed}s")
                    await self._write_error_response(
                        request_id,
                        f"Request timed out after {request.timeout_seconds} seconds"
                    )
                    completed.append(request_id)
                    continue

            # Check for task result
            # Find which worker has this task
            for worker_id, worker in self.worker_pool.workers.items():
                result_file = self.ipc_path / "tasks" / str(worker_id) / "result.json"
                collected_file = self.ipc_path / "tasks" / str(worker_id) / "result.collected"

                if result_file.exists() or collected_file.exists():
                    try:
                        # Read result (prefer collected if exists)
                        target_file = collected_file if collected_file.exists() else result_file
                        result = json.loads(target_file.read_text())

                        # Check if this is our task
                        if result.get("task_id") == request.task_id or result.get("collaboration_id") == request_id:
                            # Write response
                            await self._write_success_response(request, result)
                            completed.append(request_id)

                            # Clean up
                            try:
                                target_file.unlink()
                            except:
                                pass
                            break
                    except Exception as e:
                        logger.error(f"Error reading result: {e}")

        # Remove completed requests
        for request_id in completed:
            del self.pending_requests[request_id]

    async def _write_success_response(
        self,
        request: CollaborationRequest,
        result: Dict
    ) -> None:
        """Write a successful response to the response directory."""
        response_file = self.collab_path / "responses" / f"{request.id}.json"

        response = {
            "request_id": request.id,
            "success": result.get("success", True),
            "response": result.get("output", result.get("result", "")),
            "from_role": request.to_role,
            "from_worker_id": result.get("worker_id", "unknown"),
            "completed_at": datetime.now().isoformat(),
        }

        # Include any additional data
        if "screenshots" in result:
            response["screenshots"] = result["screenshots"]
        if "steps_executed" in result:
            response["steps_executed"] = result["steps_executed"]
        if "assertions_passed" in result:
            response["assertions_passed"] = result["assertions_passed"]
        if "assertions_failed" in result:
            response["assertions_failed"] = result["assertions_failed"]

        response_file.write_text(json.dumps(response, indent=2))
        logger.info(f"Wrote response for request {request.id}")

    async def _write_error_response(self, request_id: str, error: str) -> None:
        """Write an error response."""
        response_file = self.collab_path / "responses" / f"{request_id}.json"

        response = {
            "request_id": request_id,
            "success": False,
            "error": error,
            "completed_at": datetime.now().isoformat(),
        }

        response_file.write_text(json.dumps(response, indent=2))
        logger.info(f"Wrote error response for request {request_id}: {error}")

    async def _scan_events(self) -> None:
        """Scan for collaboration events (async operations)."""
        events_dir = self.collab_path / "events"

        for event_file in events_dir.glob("*.json"):
            try:
                data = json.loads(event_file.read_text())
                event = CollaborationEvent(
                    id=data["id"],
                    type=EventType(data["type"]),
                    from_worker_id=data["from_worker_id"],
                    from_role=data.get("from_role", "unknown"),
                    payload=data.get("payload", {}),
                    created_at=data.get("created_at", ""),
                )

                # Process event
                await self._process_event(event)

                # Delete processed event file
                event_file.unlink()

            except Exception as e:
                logger.error(f"Error processing event {event_file.name}: {e}")
                # Move to a failed directory or delete
                try:
                    event_file.unlink()
                except:
                    pass

    async def _process_event(self, event: CollaborationEvent) -> None:
        """Process a collaboration event."""
        logger.info(f"Processing event {event.id} of type {event.type.value}")

        if event.type == EventType.SPAWN_SUBTASK:
            await self._handle_spawn_subtask(event)
        elif event.type == EventType.SHARE_LEARNING:
            await self._handle_share_learning(event)
        elif event.type == EventType.REPORT_ISSUE:
            await self._handle_report_issue(event)
        elif event.type == EventType.UPDATE_CONTEXT:
            await self._handle_update_context(event)

    async def _handle_spawn_subtask(self, event: CollaborationEvent) -> None:
        """Handle a spawn_subtask event."""
        payload = event.payload
        target_role = payload.get("target_role")
        title = payload.get("title")
        description = payload.get("description")
        priority = payload.get("priority", "normal")

        # Find worker for role
        worker = await self._find_worker_for_role(target_role)

        if not worker:
            logger.warning(f"No worker available for role {target_role}")
            return

        # Create task
        worker_dir = self.ipc_path / "tasks" / str(worker["id"])
        pending_file = worker_dir / "pending.json"

        task = {
            "id": f"subtask_{event.id}",
            "title": title,
            "description": description,
            "priority": priority,
            "type": "subtask",
            "spawned_by": event.from_worker_id,
            "spawned_by_role": event.from_role,
            "dispatched_at": datetime.now().isoformat(),
        }

        pending_file.write_text(json.dumps(task, indent=2))
        logger.info(f"Spawned subtask for {target_role}: {title}")

    async def _handle_share_learning(self, event: CollaborationEvent) -> None:
        """Handle a share_learning event - store in memory."""
        payload = event.payload
        learning_type = payload.get("learning_type", "pattern")
        content = payload.get("content", "")
        metadata = payload.get("metadata", {})

        # Store in long-term memory
        try:
            await self.memory.long_term.store(
                content=content,
                memory_type=learning_type,
                metadata={
                    **metadata,
                    "from_role": event.from_role,
                    "from_worker_id": event.from_worker_id,
                    "shared_at": event.created_at,
                }
            )
            logger.info(f"Stored shared learning from {event.from_role}: {content[:100]}...")
        except Exception as e:
            logger.error(f"Failed to store learning: {e}")

    async def _handle_report_issue(self, event: CollaborationEvent) -> None:
        """Handle a report_issue event - create high-priority debugger task."""
        payload = event.payload
        title = payload.get("title")
        description = payload.get("description")

        # Find debugger worker
        worker = await self._find_worker_for_role("debugger")

        if not worker:
            logger.warning("No debugger worker available for issue")
            return

        # Create high-priority task
        worker_dir = self.ipc_path / "tasks" / str(worker["id"])
        pending_file = worker_dir / "pending.json"

        task_desc = f"""## Issue Report from {event.from_role}

**Title:** {title}
**Description:** {description}
**File:** {payload.get('file_path', 'Not specified')}
**Error:** {payload.get('error_message', 'Not specified')}
**Severity:** {payload.get('severity', 'medium')}

**Stack Trace:**
```
{payload.get('stack_trace', 'Not provided')}
```

**Instructions:**
1. Investigate the reported issue
2. Identify root cause
3. Either fix the issue or spawn a task to the appropriate worker"""

        task = {
            "id": f"issue_{event.id}",
            "title": f"[BUG] {title}",
            "description": task_desc,
            "priority": "urgent" if payload.get("severity") == "critical" else "high",
            "type": "issue",
            "reported_by": event.from_worker_id,
            "reported_by_role": event.from_role,
            "dispatched_at": datetime.now().isoformat(),
        }

        pending_file.write_text(json.dumps(task, indent=2))
        logger.info(f"Created issue task for debugger: {title}")

    async def _handle_update_context(self, event: CollaborationEvent) -> None:
        """Handle an update_context event - update shared memory cache."""
        payload = event.payload
        context_type = payload.get("context_type")
        data = payload.get("data", {})

        # Write to shared memory cache
        shared_path = self.ipc_path / "memory" / "shared"

        if context_type == "design_system":
            file_path = shared_path / "design_system.json"
        elif context_type == "api_endpoints":
            file_path = shared_path / "api_endpoints.json"
        else:
            file_path = shared_path / f"{context_type}.json"

        try:
            file_path.write_text(json.dumps(data, indent=2))
            logger.info(f"Updated shared context: {context_type}")
        except Exception as e:
            logger.error(f"Failed to update shared context: {e}")

    async def shutdown(self) -> None:
        """Shutdown collaboration manager."""
        self._running = False
        self.pending_requests.clear()
        logger.info("Collaboration manager shut down")
