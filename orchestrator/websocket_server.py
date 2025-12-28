"""
WebSocket Server for CLOPUS TUI Real-time Updates

Broadcasts events to connected TUI clients:
- Worker status changes
- Task completion/failure
- Objective updates
- Question pending notifications
- Validation results
- Self-healing actions
- Log messages
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from weakref import WeakSet

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    WebSocketServerProtocol = Any

logger = logging.getLogger("clopus.websocket")


class EventType(str, Enum):
    """Event types for WebSocket messages"""
    WORKER_STATUS = "worker_status"
    TASK_ASSIGNED = "task_assigned"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    OBJECTIVE_CREATED = "objective_created"
    OBJECTIVE_COMPLETED = "objective_completed"
    QUESTION_PENDING = "question_pending"
    QUESTION_ANSWERED = "question_answered"
    VALIDATION_RESULT = "validation_result"
    SELF_HEALING = "self_healing"
    LOG_MESSAGE = "log_message"
    SYSTEM_STATUS = "system_status"
    PROJECT_UPDATE = "project_update"


@dataclass
class Event:
    """WebSocket event structure"""
    type: EventType
    data: Dict[str, Any]
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()

    def to_json(self) -> str:
        return json.dumps({
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp,
        })


class WebSocketServer:
    """
    WebSocket server for broadcasting real-time updates to TUI clients.

    Usage:
        server = WebSocketServer()
        await server.start()

        # Emit events
        server.emit(EventType.TASK_COMPLETED, {"task_id": "123", "title": "..."})

        # Later...
        await server.stop()
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8765,
        max_clients: int = 100
    ):
        self.host = host
        self.port = port
        self.max_clients = max_clients

        self._clients: Set[WebSocketServerProtocol] = set()
        self._server = None
        self._running = False
        self._event_handlers: Dict[EventType, List[Callable]] = {}
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._broadcast_task: Optional[asyncio.Task] = None

    async def start(self) -> bool:
        """Start the WebSocket server"""
        if not WEBSOCKETS_AVAILABLE:
            logger.warning("websockets package not available, WebSocket server disabled")
            return False

        try:
            self._server = await websockets.serve(
                self._handle_connection,
                self.host,
                self.port,
                ping_interval=30,
                ping_timeout=10,
            )
            self._running = True

            # Start broadcast worker
            self._broadcast_task = asyncio.create_task(self._broadcast_worker())

            logger.info(f"WebSocket server started on ws://{self.host}:{self.port}")
            return True

        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
            return False

    async def stop(self) -> None:
        """Stop the WebSocket server"""
        self._running = False

        if self._broadcast_task:
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass

        # Close all client connections
        for client in list(self._clients):
            try:
                await client.close()
            except Exception:
                pass

        self._clients.clear()

        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

        logger.info("WebSocket server stopped")

    async def _handle_connection(
        self,
        websocket: WebSocketServerProtocol,
        path: str = "/"
    ) -> None:
        """Handle a new client connection"""
        if len(self._clients) >= self.max_clients:
            logger.warning(f"Max clients ({self.max_clients}) reached, rejecting connection")
            await websocket.close(1013, "Max clients reached")
            return

        client_id = id(websocket)
        self._clients.add(websocket)
        logger.info(f"Client connected: {client_id} (total: {len(self._clients)})")

        try:
            # Send welcome message with current status
            await self._send_welcome(websocket)

            # Handle incoming messages
            async for message in websocket:
                await self._handle_message(websocket, message)

        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
        finally:
            self._clients.discard(websocket)
            logger.info(f"Client disconnected: {client_id} (total: {len(self._clients)})")

    async def _send_welcome(self, websocket: WebSocketServerProtocol) -> None:
        """Send welcome message to new client"""
        welcome = Event(
            type=EventType.SYSTEM_STATUS,
            data={
                "message": "Connected to CLOPUS WebSocket server",
                "version": "1.0.0",
                "clients": len(self._clients),
            }
        )
        await websocket.send(welcome.to_json())

    async def _handle_message(
        self,
        websocket: WebSocketServerProtocol,
        message: str
    ) -> None:
        """Handle incoming message from client"""
        try:
            data = json.loads(message)
            msg_type = data.get("type", "")

            # Handle subscription requests
            if msg_type == "subscribe":
                # Client wants to subscribe to specific event types
                event_types = data.get("events", [])
                logger.debug(f"Client subscribed to: {event_types}")

            # Handle ping
            elif msg_type == "ping":
                await websocket.send(json.dumps({"type": "pong"}))

            # Handle custom commands
            elif msg_type == "command":
                # Could handle commands like "get_status", "refresh", etc.
                command = data.get("command", "")
                logger.debug(f"Received command: {command}")

        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON message received")
        except Exception as e:
            logger.error(f"Error handling message: {e}")

    async def _broadcast_worker(self) -> None:
        """Worker task that broadcasts queued events to all clients"""
        while self._running:
            try:
                # Wait for event with timeout
                try:
                    event = await asyncio.wait_for(
                        self._message_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                if not self._clients:
                    continue

                # Broadcast to all clients
                message = event.to_json()
                dead_clients = set()

                for client in self._clients:
                    try:
                        await asyncio.wait_for(
                            client.send(message),
                            timeout=5.0
                        )
                    except (asyncio.TimeoutError, Exception):
                        dead_clients.add(client)

                # Remove dead clients
                for client in dead_clients:
                    self._clients.discard(client)
                    try:
                        await client.close()
                    except Exception:
                        pass

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in broadcast worker: {e}")
                await asyncio.sleep(1)

    def emit(self, event_type: EventType, data: Dict[str, Any]) -> None:
        """
        Emit an event to all connected clients.

        This is non-blocking - events are queued and sent asynchronously.
        """
        if not self._running:
            return

        event = Event(type=event_type, data=data)

        try:
            self._message_queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning("Event queue full, dropping event")

    async def emit_async(self, event_type: EventType, data: Dict[str, Any]) -> None:
        """Async version of emit"""
        if not self._running:
            return

        event = Event(type=event_type, data=data)
        await self._message_queue.put(event)

    @property
    def client_count(self) -> int:
        """Get number of connected clients"""
        return len(self._clients)

    @property
    def is_running(self) -> bool:
        """Check if server is running"""
        return self._running


# Global instance
_websocket_server: Optional[WebSocketServer] = None


def get_websocket_server() -> Optional[WebSocketServer]:
    """Get the global WebSocket server instance"""
    return _websocket_server


def set_websocket_server(server: WebSocketServer) -> None:
    """Set the global WebSocket server instance"""
    global _websocket_server
    _websocket_server = server


async def start_websocket_server(
    host: str = "0.0.0.0",
    port: int = 8765
) -> Optional[WebSocketServer]:
    """Start the global WebSocket server"""
    global _websocket_server

    if _websocket_server and _websocket_server.is_running:
        return _websocket_server

    _websocket_server = WebSocketServer(host=host, port=port)
    success = await _websocket_server.start()

    if success:
        return _websocket_server
    return None


async def stop_websocket_server() -> None:
    """Stop the global WebSocket server"""
    global _websocket_server

    if _websocket_server:
        await _websocket_server.stop()
        _websocket_server = None


def emit_event(event_type: EventType, data: Dict[str, Any]) -> None:
    """Emit an event through the global WebSocket server"""
    if _websocket_server:
        _websocket_server.emit(event_type, data)


# Convenience functions for common events
def emit_worker_status(
    worker_id: int,
    status: str,
    role: str,
    task_id: Optional[str] = None
) -> None:
    """Emit worker status change event"""
    emit_event(EventType.WORKER_STATUS, {
        "worker_id": worker_id,
        "status": status,
        "role": role,
        "task_id": task_id,
    })


def emit_task_completed(
    task_id: str,
    title: str,
    project: str = "",
    worker_id: Optional[int] = None
) -> None:
    """Emit task completed event"""
    emit_event(EventType.TASK_COMPLETED, {
        "task_id": task_id,
        "title": title,
        "project": project,
        "worker_id": worker_id,
    })


def emit_task_failed(
    task_id: str,
    title: str,
    error: str = "",
    worker_id: Optional[int] = None
) -> None:
    """Emit task failed event"""
    emit_event(EventType.TASK_FAILED, {
        "task_id": task_id,
        "title": title,
        "error": error,
        "worker_id": worker_id,
    })


def emit_question_pending(question_id: str, content: str) -> None:
    """Emit question pending event"""
    emit_event(EventType.QUESTION_PENDING, {
        "question_id": question_id,
        "content": content[:200],  # Truncate for display
    })


def emit_validation_result(
    task_id: str,
    passed: bool,
    stages: List[Dict[str, Any]]
) -> None:
    """Emit validation result event"""
    emit_event(EventType.VALIDATION_RESULT, {
        "task_id": task_id,
        "passed": passed,
        "stages": stages,
    })


def emit_self_healing(action: str, count: int, details: str = "") -> None:
    """Emit self-healing event"""
    emit_event(EventType.SELF_HEALING, {
        "action": action,
        "count": count,
        "details": details,
    })


def emit_objective_created(objective_id: str, content: str) -> None:
    """Emit objective created event"""
    emit_event(EventType.OBJECTIVE_CREATED, {
        "objective_id": objective_id,
        "content": content[:200],
    })


def emit_objective_completed(
    objective_id: str,
    success: bool,
    task_count: int = 0
) -> None:
    """Emit objective completed event"""
    emit_event(EventType.OBJECTIVE_COMPLETED, {
        "objective_id": objective_id,
        "success": success,
        "task_count": task_count,
    })


def emit_project_update(
    project_name: str,
    status: str,
    port: Optional[int] = None
) -> None:
    """Emit project update event"""
    emit_event(EventType.PROJECT_UPDATE, {
        "project_name": project_name,
        "status": status,
        "port": port,
    })
