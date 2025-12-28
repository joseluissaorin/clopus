# =============================================================================
# CLOPUS v3 Message Router
# =============================================================================
"""
Intelligent routing of messages between workers.
Handles role-based routing, load balancing, and fallback strategies.
"""

import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("clopus.message_router")


class RoutingStrategy(str, Enum):
    """Message routing strategies."""
    PREFER_IDLE = "prefer_idle"  # Prefer idle workers
    ROUND_ROBIN = "round_robin"  # Distribute evenly
    PRIORITY = "priority"        # Use priority workers first
    FALLBACK = "fallback"        # Use fallback role if primary unavailable


@dataclass
class WorkerCapability:
    """Describes a worker's capabilities."""
    role: str
    can_handle: List[str]  # Request types this worker can handle
    priority: int = 0      # Higher = preferred for this role
    is_specialized: bool = False  # True for reserved workers


# Worker role capabilities
ROLE_CAPABILITIES = {
    "coder": {
        "can_handle": ["code", "fix", "implement", "refactor"],
        "priority": 1,
        "is_specialized": False,
    },
    "tester": {
        "can_handle": ["test", "verify", "validate", "check"],
        "priority": 1,
        "is_specialized": False,
    },
    "reviewer": {
        "can_handle": ["review", "audit", "assess", "evaluate"],
        "priority": 1,
        "is_specialized": False,
    },
    "researcher": {
        "can_handle": ["research", "find", "search", "lookup", "api", "documentation"],
        "priority": 1,
        "is_specialized": False,
    },
    "debugger": {
        "can_handle": ["debug", "fix", "diagnose", "investigate", "error"],
        "priority": 2,
        "is_specialized": False,
    },
    "designer": {
        "can_handle": ["design", "ui", "ux", "color", "style", "layout", "visual"],
        "priority": 1,
        "is_specialized": False,
    },
    "heartbeat": {
        "can_handle": [],  # Reserved - never routes regular tasks
        "priority": 0,
        "is_specialized": True,
    },
    "verificator": {
        "can_handle": [],  # Reserved - never routes regular tasks
        "priority": 0,
        "is_specialized": True,
    },
    "browser-headless": {
        "can_handle": ["browser", "screenshot", "e2e", "test", "navigate", "scrape"],
        "priority": 2,  # Preferred for browser tasks
        "is_specialized": True,
    },
    "browser-chrome": {
        "can_handle": ["browser", "screenshot", "e2e", "test", "navigate", "scrape", "visual"],
        "priority": 1,  # Fallback for browser tasks
        "is_specialized": True,
    },
    "services": {
        "can_handle": ["email", "gmail", "api", "external", "integration"],
        "priority": 1,
        "is_specialized": True,
    },
}


class MessageRouter:
    """
    Routes messages between workers intelligently.

    Responsibilities:
    - Find best worker for a given role/request type
    - Load balance across available workers
    - Handle fallback when primary worker unavailable
    - Track worker load and availability
    """

    def __init__(
        self,
        worker_pool,
        ipc_path: str = "/app/ipc"
    ):
        self.worker_pool = worker_pool
        self.ipc_path = Path(ipc_path)

        # Track recent task assignments for load balancing
        self.recent_assignments: Dict[int, List[datetime]] = {}

        # Configuration
        self.max_concurrent_per_worker = 1  # Workers handle one task at a time
        self.load_window_seconds = 60       # Time window for load calculation

    def get_worker_for_role(
        self,
        role: str,
        strategy: RoutingStrategy = RoutingStrategy.PREFER_IDLE,
        exclude_workers: Optional[List[int]] = None
    ) -> Optional[Dict]:
        """
        Find the best worker for a given role.

        Args:
            role: Target worker role
            strategy: Routing strategy to use
            exclude_workers: Worker IDs to exclude from consideration

        Returns:
            Worker dict or None if no suitable worker found
        """
        exclude = set(exclude_workers or [])
        candidates = []

        # Find all workers with the target role
        for worker_id, worker in self.worker_pool.workers.items():
            if worker_id in exclude:
                continue

            if worker["role"] == role:
                candidates.append(worker)

        if not candidates:
            logger.warning(f"No workers found with role: {role}")
            return None

        # Apply routing strategy
        if strategy == RoutingStrategy.PREFER_IDLE:
            return self._route_prefer_idle(candidates)
        elif strategy == RoutingStrategy.ROUND_ROBIN:
            return self._route_round_robin(candidates)
        elif strategy == RoutingStrategy.PRIORITY:
            return self._route_priority(candidates)
        else:
            return candidates[0] if candidates else None

    def _route_prefer_idle(self, candidates: List[Dict]) -> Optional[Dict]:
        """Prefer idle workers."""
        # First, try to find an idle worker
        idle_workers = [w for w in candidates if w["status"] == "idle"]
        if idle_workers:
            return idle_workers[0]

        # If no idle workers, return the one with lowest load
        return min(candidates, key=lambda w: self._get_worker_load(w["id"]))

    def _route_round_robin(self, candidates: List[Dict]) -> Optional[Dict]:
        """Distribute tasks evenly using round-robin."""
        if not candidates:
            return None

        # Find worker with fewest recent assignments
        return min(candidates, key=lambda w: self._get_recent_assignments(w["id"]))

    def _route_priority(self, candidates: List[Dict]) -> Optional[Dict]:
        """Route to highest priority worker."""
        role = candidates[0]["role"] if candidates else None
        if not role:
            return None

        capabilities = ROLE_CAPABILITIES.get(role, {})
        priority = capabilities.get("priority", 0)

        # Sort by priority, then by idle status
        sorted_candidates = sorted(
            candidates,
            key=lambda w: (
                -priority,
                0 if w["status"] == "idle" else 1,
                self._get_worker_load(w["id"])
            )
        )

        return sorted_candidates[0] if sorted_candidates else None

    def _get_worker_load(self, worker_id: int) -> int:
        """Get current load for a worker (number of pending tasks)."""
        worker_dir = self.ipc_path / "tasks" / str(worker_id)
        pending_file = worker_dir / "pending.json"

        if pending_file.exists():
            return 1
        return 0

    def _get_recent_assignments(self, worker_id: int) -> int:
        """Get number of recent task assignments."""
        cutoff = datetime.now() - timedelta(seconds=self.load_window_seconds)

        if worker_id not in self.recent_assignments:
            return 0

        # Filter to recent assignments only
        recent = [t for t in self.recent_assignments[worker_id] if t > cutoff]
        self.recent_assignments[worker_id] = recent

        return len(recent)

    def record_assignment(self, worker_id: int) -> None:
        """Record that a task was assigned to a worker."""
        if worker_id not in self.recent_assignments:
            self.recent_assignments[worker_id] = []

        self.recent_assignments[worker_id].append(datetime.now())

    def get_browser_worker(
        self,
        prefer_headless: bool = True
    ) -> Optional[Dict]:
        """
        Get a browser worker for automation tasks.

        Args:
            prefer_headless: If True, prefer headless Playwright worker (faster)
                           If False, prefer Chrome VNC worker (visual debugging)

        Returns:
            Browser worker dict or None
        """
        primary_role = "browser-headless" if prefer_headless else "browser-chrome"
        fallback_role = "browser-chrome" if prefer_headless else "browser-headless"

        # Try primary first
        worker = self.get_worker_for_role(primary_role)
        if worker:
            return worker

        # Fallback
        logger.info(f"Primary browser worker ({primary_role}) unavailable, trying {fallback_role}")
        return self.get_worker_for_role(fallback_role)

    def get_fallback_worker(
        self,
        primary_role: str,
        request_type: str
    ) -> Optional[Dict]:
        """
        Find a fallback worker when primary role is unavailable.

        Args:
            primary_role: The preferred role that was unavailable
            request_type: Type of request (used to find capable workers)

        Returns:
            Fallback worker or None
        """
        # Find roles that can handle this request type
        capable_roles = []
        for role, caps in ROLE_CAPABILITIES.items():
            if role == primary_role:
                continue
            if caps.get("is_specialized"):
                continue  # Don't use specialized workers as fallback
            if request_type.lower() in [c.lower() for c in caps.get("can_handle", [])]:
                capable_roles.append((role, caps.get("priority", 0)))

        # Sort by priority (higher = better)
        capable_roles.sort(key=lambda x: -x[1])

        # Try each capable role
        for role, _ in capable_roles:
            worker = self.get_worker_for_role(role)
            if worker:
                logger.info(f"Using {role} as fallback for {primary_role}")
                return worker

        return None

    def get_worker_by_id(self, worker_id: int) -> Optional[Dict]:
        """Get a specific worker by ID."""
        return self.worker_pool.workers.get(worker_id)

    def get_idle_workers(self) -> List[Dict]:
        """Get all idle workers."""
        return [w for w in self.worker_pool.workers.values() if w["status"] == "idle"]

    def get_workers_by_role(self, role: str) -> List[Dict]:
        """Get all workers with a specific role."""
        return [w for w in self.worker_pool.workers.values() if w["role"] == role]

    def is_worker_available(self, worker_id: int) -> bool:
        """Check if a worker is available (idle and not overloaded)."""
        worker = self.get_worker_by_id(worker_id)
        if not worker:
            return False

        if worker["status"] != "idle":
            return False

        if self._get_worker_load(worker_id) >= self.max_concurrent_per_worker:
            return False

        return True

    def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing statistics for monitoring."""
        stats = {
            "total_workers": len(self.worker_pool.workers),
            "idle_workers": len(self.get_idle_workers()),
            "by_role": {},
            "recent_assignments": {},
        }

        # Count by role
        for worker in self.worker_pool.workers.values():
            role = worker["role"]
            if role not in stats["by_role"]:
                stats["by_role"][role] = {"total": 0, "idle": 0}
            stats["by_role"][role]["total"] += 1
            if worker["status"] == "idle":
                stats["by_role"][role]["idle"] += 1

        # Recent assignments
        for worker_id, assignments in self.recent_assignments.items():
            stats["recent_assignments"][worker_id] = len(assignments)

        return stats

    def suggest_role_for_task(self, task_description: str) -> str:
        """
        Suggest the best role for a task based on its description.

        Args:
            task_description: Description of the task

        Returns:
            Suggested role
        """
        description_lower = task_description.lower()

        # Keywords that map to roles
        role_keywords = {
            "coder": ["implement", "create", "build", "code", "add", "write"],
            "tester": ["test", "verify", "check", "e2e", "unit test"],
            "reviewer": ["review", "audit", "evaluate", "assess"],
            "researcher": ["research", "find", "look up", "api docs", "documentation"],
            "debugger": ["debug", "fix", "error", "bug", "crash", "investigate"],
            "designer": ["design", "ui", "ux", "color", "style", "layout", "visual"],
            "browser-headless": ["screenshot", "browser", "navigate", "scrape", "e2e"],
            "services": ["email", "gmail", "send", "notification", "external api"],
        }

        # Score each role based on keyword matches
        scores: Dict[str, int] = {}
        for role, keywords in role_keywords.items():
            scores[role] = sum(1 for kw in keywords if kw in description_lower)

        # Return role with highest score (default to coder)
        if max(scores.values()) == 0:
            return "coder"

        return max(scores.items(), key=lambda x: x[1])[0]
