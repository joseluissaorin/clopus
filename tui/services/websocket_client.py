"""WebSocket client for real-time updates"""

import asyncio
import json
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class EventType(Enum):
    WORKER_STATUS = "worker_status"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_ASSIGNED = "task_assigned"
    OBJECTIVE_COMPLETED = "objective_completed"
    QUESTION_PENDING = "question_pending"
    VALIDATION_RESULT = "validation_result"
    SELF_HEALING = "self_healing"
    LOG_MESSAGE = "log_message"


@dataclass
class Event:
    type: EventType
    data: Dict[str, Any]
    timestamp: float


class WebSocketClient:
    """WebSocket client for real-time orchestrator updates"""

    def __init__(self, url: str = "ws://localhost:8765"):
        self.url = url
        self._connected = False
        self._websocket = None
        self._callbacks: Dict[EventType, List[Callable]] = {}
        self._reconnect_delay = 1.0
        self._max_reconnect_delay = 30.0
        self._running = False

    def on(self, event_type: EventType, callback: Callable) -> None:
        """Register callback for event type"""
        if event_type not in self._callbacks:
            self._callbacks[event_type] = []
        self._callbacks[event_type].append(callback)

    def on_any(self, callback: Callable) -> None:
        """Register callback for all events"""
        for event_type in EventType:
            self.on(event_type, callback)

    async def _emit(self, event: Event) -> None:
        """Emit event to callbacks"""
        callbacks = self._callbacks.get(event.type, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception:
                pass

    async def connect(self) -> bool:
        """Connect to WebSocket server"""
        try:
            import websockets
            self._websocket = await websockets.connect(self.url)
            self._connected = True
            self._reconnect_delay = 1.0  # Reset delay on success
            return True
        except Exception:
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from WebSocket server"""
        self._running = False
        if self._websocket:
            await self._websocket.close()
            self._websocket = None
        self._connected = False

    async def send(self, message: Dict[str, Any]) -> bool:
        """Send message to server"""
        if not self._connected or not self._websocket:
            return False
        try:
            await self._websocket.send(json.dumps(message))
            return True
        except Exception:
            return False

    async def start(self) -> None:
        """Start listening for messages with auto-reconnect"""
        self._running = True

        while self._running:
            try:
                if not self._connected:
                    connected = await self.connect()
                    if not connected:
                        await asyncio.sleep(self._reconnect_delay)
                        self._reconnect_delay = min(
                            self._reconnect_delay * 2,
                            self._max_reconnect_delay
                        )
                        continue

                async for message in self._websocket:
                    try:
                        data = json.loads(message)
                        event_type_str = data.get("type", "")

                        # Map string to EventType
                        try:
                            event_type = EventType(event_type_str)
                        except ValueError:
                            continue

                        event = Event(
                            type=event_type,
                            data=data.get("data", {}),
                            timestamp=data.get("timestamp", 0),
                        )
                        await self._emit(event)
                    except json.JSONDecodeError:
                        pass

            except Exception:
                self._connected = False
                if self._running:
                    await asyncio.sleep(self._reconnect_delay)
                    self._reconnect_delay = min(
                        self._reconnect_delay * 2,
                        self._max_reconnect_delay
                    )

    @property
    def connected(self) -> bool:
        return self._connected


class MockWebSocketClient(WebSocketClient):
    """Mock WebSocket client that polls IPC files instead"""

    def __init__(self):
        super().__init__()
        self._last_task_stats = {}
        self._last_worker_status = {}

    async def start(self) -> None:
        """Start polling for updates"""
        from .ipc import IPCMonitor
        from .database import DatabaseClient

        ipc = IPCMonitor()
        db = DatabaseClient()
        await db.connect()

        self._running = True
        self._connected = True  # Always "connected" in mock mode

        while self._running:
            try:
                # Poll worker status
                workers = await ipc.get_all_worker_status()
                for worker in workers:
                    old_status = self._last_worker_status.get(worker.id)
                    if old_status != worker.status:
                        await self._emit(Event(
                            type=EventType.WORKER_STATUS,
                            data={
                                "worker_id": worker.id,
                                "role": worker.role,
                                "status": worker.status,
                            },
                            timestamp=0,
                        ))
                    self._last_worker_status[worker.id] = worker.status

                # Poll task stats
                stats = await db.get_task_stats()
                if stats != self._last_task_stats:
                    # Check for completed tasks
                    old_completed = self._last_task_stats.get("completed", 0)
                    new_completed = stats.get("completed", 0)
                    if new_completed > old_completed:
                        await self._emit(Event(
                            type=EventType.TASK_COMPLETED,
                            data={"count": new_completed - old_completed},
                            timestamp=0,
                        ))

                    # Check for failed tasks
                    old_failed = self._last_task_stats.get("failed", 0)
                    new_failed = stats.get("failed", 0)
                    if new_failed > old_failed:
                        await self._emit(Event(
                            type=EventType.TASK_FAILED,
                            data={"count": new_failed - old_failed},
                            timestamp=0,
                        ))

                    self._last_task_stats = stats

                await asyncio.sleep(1.0)
            except Exception:
                await asyncio.sleep(2.0)

        await db.close()
