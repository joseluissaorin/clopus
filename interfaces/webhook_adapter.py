# =============================================================================
# CLOPUS v3 Webhook Interface Adapter
# =============================================================================
"""
REST API and WebSocket interface for external integrations.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, asdict

from aiohttp import web, WSMsgType
import aiohttp_cors

from .base import InterfaceAdapter

logger = logging.getLogger("clopus.webhook_adapter")


@dataclass
class WebhookEvent:
    """Represents a webhook event."""
    type: str
    data: Dict
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return asdict(self)


class WebhookAdapter(InterfaceAdapter):
    """
    REST API and WebSocket interface for CLOPUS.

    Endpoints:
        GET  /                     - API info
        GET  /health               - Health check
        GET  /status               - System status

        POST /objectives           - Create new objective
        GET  /objectives           - List objectives
        GET  /objectives/:id       - Get objective details

        GET  /questions            - List pending questions
        POST /questions/:id/answer - Answer a question

        GET  /workers              - Worker status
        GET  /tasks                - Active tasks

        GET  /skills               - List skills
        GET  /templates            - List templates

        WS   /ws                   - WebSocket for real-time updates
    """

    def __init__(
        self,
        orchestrator,
        host: str = "0.0.0.0",
        port: int = 8888,
        api_key: Optional[str] = None
    ):
        super().__init__(orchestrator)
        self.host = host
        self.port = port
        self.api_key = api_key
        self.app: Optional[web.Application] = None
        self.runner: Optional[web.AppRunner] = None
        self.websockets: Set[web.WebSocketResponse] = set()
        self._event_queue: asyncio.Queue = asyncio.Queue()

    async def start(self) -> None:
        """Start the webhook server."""
        logger.info(f"Starting webhook server on {self.host}:{self.port}")

        self.app = web.Application(middlewares=[self._auth_middleware])
        self._setup_routes()
        self._setup_cors()

        self.runner = web.AppRunner(self.app)
        await self.runner.setup()

        site = web.TCPSite(self.runner, self.host, self.port)
        await site.start()

        self._running = True

        # Start event broadcaster
        asyncio.create_task(self._broadcast_events())

        logger.info(f"Webhook server running on http://{self.host}:{self.port}")

    async def stop(self) -> None:
        """Stop the webhook server."""
        logger.info("Stopping webhook server...")
        self._running = False

        # Close all WebSocket connections
        for ws in self.websockets:
            await ws.close(code=1001, message=b"Server shutting down")
        self.websockets.clear()

        if self.runner:
            await self.runner.cleanup()

        logger.info("Webhook server stopped")

    def _setup_routes(self) -> None:
        """Setup API routes."""
        router = self.app.router

        # General
        router.add_get("/", self._handle_root)
        router.add_get("/health", self._handle_health)
        router.add_get("/status", self._handle_status)

        # Objectives
        router.add_post("/objectives", self._handle_create_objective)
        router.add_get("/objectives", self._handle_list_objectives)
        router.add_get("/objectives/{id}", self._handle_get_objective)

        # Questions
        router.add_get("/questions", self._handle_list_questions)
        router.add_post("/questions/{id}/answer", self._handle_answer_question)

        # Workers
        router.add_get("/workers", self._handle_list_workers)

        # Tasks
        router.add_get("/tasks", self._handle_list_tasks)

        # Skills & Templates
        router.add_get("/skills", self._handle_list_skills)
        router.add_get("/templates", self._handle_list_templates)

        # WebSocket
        router.add_get("/ws", self._handle_websocket)

    def _setup_cors(self) -> None:
        """Setup CORS for the API."""
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
            )
        })

        for route in list(self.app.router.routes()):
            cors.add(route)

    @web.middleware
    async def _auth_middleware(self, request: web.Request, handler):
        """API key authentication middleware."""
        # Skip auth for health check and root
        if request.path in ["/", "/health"]:
            return await handler(request)

        # Skip auth if no API key configured
        if not self.api_key:
            return await handler(request)

        # Check Authorization header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            if token == self.api_key:
                return await handler(request)

        # Check X-API-Key header
        api_key = request.headers.get("X-API-Key", "")
        if api_key == self.api_key:
            return await handler(request)

        raise web.HTTPUnauthorized(text="Invalid or missing API key")

    # =========================================================================
    # Route Handlers
    # =========================================================================

    async def _handle_root(self, request: web.Request) -> web.Response:
        """Root endpoint - API info."""
        return web.json_response({
            "name": "CLOPUS API",
            "version": "3.0.0",
            "description": "Claude Orchestrated Parallel Universal System",
            "endpoints": {
                "status": "/status",
                "objectives": "/objectives",
                "questions": "/questions",
                "workers": "/workers",
                "tasks": "/tasks",
                "skills": "/skills",
                "templates": "/templates",
                "websocket": "/ws"
            }
        })

    async def _handle_health(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        return web.json_response({
            "status": "healthy",
            "timestamp": datetime.now().isoformat()
        })

    async def _handle_status(self, request: web.Request) -> web.Response:
        """Get system status."""
        workers = await self.orchestrator.worker_pool.get_all_status()
        objectives = await self.orchestrator.memory.get_objectives()

        return web.json_response({
            "status": "running" if self._running else "stopped",
            "workers": {
                "total": len(workers),
                "idle": len([w for w in workers if w.get("status") == "idle"]),
                "busy": len([w for w in workers if w.get("status") == "busy"])
            },
            "objectives": {
                "active": len([o for o in objectives if o.get("status") == "active"]),
                "completed": len([o for o in objectives if o.get("status") == "completed"])
            },
            "timestamp": datetime.now().isoformat()
        })

    async def _handle_create_objective(self, request: web.Request) -> web.Response:
        """Create a new objective."""
        try:
            data = await request.json()
            content = data.get("content") or data.get("objective")

            if not content:
                raise web.HTTPBadRequest(text="Missing 'content' field")

            objective_id = await self.receive_objective(content)

            await self._queue_event(WebhookEvent(
                type="objective_created",
                data={"id": objective_id, "content": content}
            ))

            return web.json_response({
                "id": objective_id,
                "status": "created",
                "message": "Objective created successfully"
            }, status=201)

        except json.JSONDecodeError:
            raise web.HTTPBadRequest(text="Invalid JSON")

    async def _handle_list_objectives(self, request: web.Request) -> web.Response:
        """List all objectives."""
        status_filter = request.query.get("status")
        limit = int(request.query.get("limit", 50))

        objectives = await self.orchestrator.memory.get_objectives()

        if status_filter:
            objectives = [o for o in objectives if o.get("status") == status_filter]

        return web.json_response({
            "objectives": objectives[:limit],
            "total": len(objectives)
        })

    async def _handle_get_objective(self, request: web.Request) -> web.Response:
        """Get objective details."""
        objective_id = request.match_info["id"]
        objective = await self.orchestrator.memory.get_objective(objective_id)

        if not objective:
            raise web.HTTPNotFound(text=f"Objective not found: {objective_id}")

        return web.json_response(objective)

    async def _handle_list_questions(self, request: web.Request) -> web.Response:
        """List pending questions."""
        questions = await self.orchestrator.memory.get_pending_questions()
        return web.json_response({
            "questions": questions,
            "count": len(questions)
        })

    async def _handle_answer_question(self, request: web.Request) -> web.Response:
        """Answer a question."""
        question_id = request.match_info["id"]

        try:
            data = await request.json()
            answer = data.get("answer")

            if not answer:
                raise web.HTTPBadRequest(text="Missing 'answer' field")

            await self.receive_answer(question_id, answer)

            await self._queue_event(WebhookEvent(
                type="question_answered",
                data={"question_id": question_id}
            ))

            return web.json_response({
                "status": "answered",
                "question_id": question_id
            })

        except json.JSONDecodeError:
            raise web.HTTPBadRequest(text="Invalid JSON")

    async def _handle_list_workers(self, request: web.Request) -> web.Response:
        """List worker status."""
        workers = await self.orchestrator.worker_pool.get_all_status()
        return web.json_response({
            "workers": workers,
            "count": len(workers)
        })

    async def _handle_list_tasks(self, request: web.Request) -> web.Response:
        """List active tasks."""
        tasks = await self.orchestrator.memory.get_active_tasks()
        return web.json_response({
            "tasks": tasks,
            "count": len(tasks)
        })

    async def _handle_list_skills(self, request: web.Request) -> web.Response:
        """List available skills."""
        skills = await self.orchestrator.skills_engine.list_skills()
        return web.json_response({
            "skills": skills,
            "count": len(skills)
        })

    async def _handle_list_templates(self, request: web.Request) -> web.Response:
        """List available templates."""
        templates = await self.orchestrator.template_extractor.list_templates()
        return web.json_response({
            "templates": templates,
            "count": len(templates)
        })

    # =========================================================================
    # WebSocket Handler
    # =========================================================================

    async def _handle_websocket(self, request: web.Request) -> web.WebSocketResponse:
        """Handle WebSocket connections for real-time updates."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        self.websockets.add(ws)
        logger.info(f"WebSocket client connected. Total: {len(self.websockets)}")

        # Send welcome message
        await ws.send_json({
            "type": "connected",
            "message": "Connected to CLOPUS WebSocket",
            "timestamp": datetime.now().isoformat()
        })

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self._handle_ws_message(ws, data)
                    except json.JSONDecodeError:
                        await ws.send_json({"error": "Invalid JSON"})
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
        finally:
            self.websockets.discard(ws)
            logger.info(f"WebSocket client disconnected. Total: {len(self.websockets)}")

        return ws

    async def _handle_ws_message(
        self,
        ws: web.WebSocketResponse,
        data: Dict
    ) -> None:
        """Handle incoming WebSocket messages."""
        msg_type = data.get("type")

        if msg_type == "ping":
            await ws.send_json({"type": "pong", "timestamp": datetime.now().isoformat()})

        elif msg_type == "subscribe":
            # Could implement topic subscriptions here
            await ws.send_json({"type": "subscribed", "topics": data.get("topics", ["*"])})

        elif msg_type == "objective":
            content = data.get("content")
            if content:
                objective_id = await self.receive_objective(content)
                await ws.send_json({
                    "type": "objective_created",
                    "id": objective_id
                })

        elif msg_type == "answer":
            question_id = data.get("question_id")
            answer = data.get("answer")
            if question_id and answer:
                await self.receive_answer(question_id, answer)
                await ws.send_json({
                    "type": "question_answered",
                    "question_id": question_id
                })

    # =========================================================================
    # Event Broadcasting
    # =========================================================================

    async def _queue_event(self, event: WebhookEvent) -> None:
        """Queue an event for broadcasting."""
        await self._event_queue.put(event)

    async def _broadcast_events(self) -> None:
        """Broadcast events to all connected WebSocket clients."""
        while self._running:
            try:
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=1.0
                )

                # Broadcast to all WebSocket clients
                if self.websockets:
                    event_data = event.to_dict()
                    await asyncio.gather(
                        *[ws.send_json(event_data) for ws in self.websockets],
                        return_exceptions=True
                    )

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error broadcasting event: {e}")

    # =========================================================================
    # InterfaceAdapter Implementation
    # =========================================================================

    async def send_status(self, status: Dict) -> None:
        """Send status update via WebSocket."""
        await self._queue_event(WebhookEvent(
            type="status_update",
            data=status
        ))

    async def send_question(self, question_id: str, question: str) -> None:
        """Send question via WebSocket."""
        await self._queue_event(WebhookEvent(
            type="question",
            data={
                "id": question_id,
                "question": question
            }
        ))

    async def send_notification(self, message: str, level: str = "info") -> None:
        """Send notification via WebSocket."""
        await self._queue_event(WebhookEvent(
            type="notification",
            data={
                "message": message,
                "level": level
            }
        ))
