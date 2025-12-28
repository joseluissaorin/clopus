"""Desktop notification service"""

import asyncio
from typing import Optional, Callable, List
from dataclasses import dataclass
from enum import Enum
import time


class NotificationType(Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class Notification:
    title: str
    message: str
    type: NotificationType = NotificationType.INFO
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()


class NotificationService:
    """Desktop and in-app notification service"""

    def __init__(self, enable_desktop: bool = True):
        self.enable_desktop = enable_desktop
        self._plyer_available = False
        self._callbacks: List[Callable] = []
        self._history: List[Notification] = []
        self._max_history = 100

        # Try to import plyer for desktop notifications
        if enable_desktop:
            try:
                from plyer import notification
                self._plyer = notification
                self._plyer_available = True
            except ImportError:
                self._plyer_available = False

    def on_notification(self, callback: Callable) -> None:
        """Register callback for notifications"""
        self._callbacks.append(callback)

    async def notify(
        self,
        title: str,
        message: str,
        notification_type: NotificationType = NotificationType.INFO,
        desktop: bool = True
    ) -> None:
        """Send a notification"""
        notif = Notification(
            title=title,
            message=message,
            type=notification_type,
        )

        # Add to history
        self._history.append(notif)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        # Call in-app callbacks
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(notif)
                else:
                    callback(notif)
            except Exception:
                pass

        # Send desktop notification
        if desktop and self.enable_desktop and self._plyer_available:
            try:
                # Run in thread to avoid blocking
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._plyer.notify(
                        title=f"CLOPUS: {title}",
                        message=message,
                        app_name="CLOPUS",
                        timeout=5,
                    )
                )
            except Exception:
                pass

    async def notify_task_completed(self, task_title: str, project: str = "") -> None:
        """Notify when a task completes"""
        msg = task_title
        if project:
            msg = f"{task_title}\nProject: {project}"
        await self.notify(
            title="Task Completed",
            message=msg,
            notification_type=NotificationType.SUCCESS,
        )

    async def notify_task_failed(self, task_title: str, error: str = "") -> None:
        """Notify when a task fails"""
        msg = task_title
        if error:
            msg = f"{task_title}\nError: {error[:100]}"
        await self.notify(
            title="Task Failed",
            message=msg,
            notification_type=NotificationType.ERROR,
        )

    async def notify_question_pending(self, question: str) -> None:
        """Notify when a question needs answering"""
        await self.notify(
            title="Question Pending",
            message=question[:100],
            notification_type=NotificationType.WARNING,
        )

    async def notify_project_completed(self, project_name: str) -> None:
        """Notify when a project completes"""
        await self.notify(
            title="Project Completed",
            message=f"All tasks completed for {project_name}",
            notification_type=NotificationType.SUCCESS,
        )

    async def notify_validation_failed(self, project: str, stage: str) -> None:
        """Notify when validation fails"""
        await self.notify(
            title="Validation Failed",
            message=f"Stage '{stage}' failed for {project}",
            notification_type=NotificationType.ERROR,
        )

    async def notify_worker_offline(self, worker_id: int, role: str) -> None:
        """Notify when a worker goes offline"""
        await self.notify(
            title="Worker Offline",
            message=f"Worker {worker_id} ({role}) is offline",
            notification_type=NotificationType.WARNING,
        )

    async def notify_self_healing(self, action: str, count: int) -> None:
        """Notify about self-healing actions"""
        await self.notify(
            title="Self-Healing",
            message=f"{action}: {count} items",
            notification_type=NotificationType.INFO,
            desktop=False,  # Don't spam desktop with these
        )

    def get_history(self, limit: int = 50) -> List[Notification]:
        """Get notification history"""
        return self._history[-limit:]

    def clear_history(self) -> None:
        """Clear notification history"""
        self._history.clear()
