# =============================================================================
# CLOPUS v3 Verificator Client
# =============================================================================
"""
High-level interface for intelligent verification using Worker 8 (Verificator).
Provides semantic analysis, deduplication, and artifact verification using Claude.

NEW IN v3.2: AI-First Integration
- All fallback methods now use AI-first engine when available
- Regex patterns are DEPRECATED and only used as last resort
- AI understands context, intent, and semantics - regex doesn't
"""

import hashlib
import logging
import time
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING
from pathlib import Path
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from .ai_first import AIFirstEngine

logger = logging.getLogger("clopus.verificator_client")

# Auth error patterns to detect OAuth token expiration
AUTH_ERROR_PATTERNS = [
    "authentication_error",
    "oauth token has expired",
    "token has expired",
    "please obtain a new token",
    "refresh your existing token",
    "not authenticated",
    "authentication required",
]


def is_auth_error(result: Optional[Dict]) -> bool:
    """Check if a result indicates an authentication error."""
    if not result:
        return False

    # Check for explicit error type
    error_type = result.get("type", "")
    if error_type == "authentication_error":
        return True

    # Check result text for auth error patterns
    result_text = str(result.get("result", ""))
    error_text = str(result.get("error", ""))
    message_text = str(result.get("message", ""))
    combined = (result_text + error_text + message_text).lower()

    for pattern in AUTH_ERROR_PATTERNS:
        if pattern in combined:
            return True

    return False


@dataclass
class CacheEntry:
    """A cached verification result with TTL."""
    value: Any
    created_at: float = field(default_factory=time.time)
    ttl_seconds: float = 300  # 5 minutes default

    def is_valid(self) -> bool:
        """Check if cache entry is still valid."""
        return (time.time() - self.created_at) < self.ttl_seconds


class VerificatorCache:
    """
    LRU-style cache for verificator results with TTL.

    Reduces repeated calls to the verificator worker for:
    - Artifact specification (same task title → same artifacts)
    - Duplicate detection (same task pair → same result)
    - Completion verification (artifacts don't change often)
    """

    def __init__(self, max_size: int = 500, default_ttl: float = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: List[str] = []  # For LRU eviction
        self._hits = 0
        self._misses = 0

    def _make_key(self, prefix: str, *args) -> str:
        """Create a cache key from prefix and arguments."""
        content = "|".join(str(a) for a in args)
        hash_val = hashlib.md5(content.encode()).hexdigest()[:16]
        return f"{prefix}:{hash_val}"

    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache if valid."""
        entry = self._cache.get(key)
        if entry is None:
            self._misses += 1
            return None

        if not entry.is_valid():
            # Expired, remove it
            self._remove(key)
            self._misses += 1
            return None

        # Update access order for LRU
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)

        self._hits += 1
        return entry.value

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Store a value in cache with optional TTL."""
        # Evict if at capacity
        while len(self._cache) >= self.max_size and self._access_order:
            oldest_key = self._access_order.pop(0)
            self._cache.pop(oldest_key, None)

        self._cache[key] = CacheEntry(
            value=value,
            ttl_seconds=ttl or self.default_ttl
        )
        self._access_order.append(key)

    def _remove(self, key: str) -> None:
        """Remove an entry from cache."""
        self._cache.pop(key, None)
        if key in self._access_order:
            self._access_order.remove(key)

    def invalidate_prefix(self, prefix: str) -> int:
        """Invalidate all entries with a given prefix."""
        keys_to_remove = [k for k in self._cache if k.startswith(prefix)]
        for key in keys_to_remove:
            self._remove(key)
        return len(keys_to_remove)

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._access_order.clear()

    @property
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.1%}"
        }


class VerificatorClient:
    """Client for intelligent verification operations using the Verificator worker."""

    def __init__(self, worker_pool, cache_enabled: bool = True):
        """
        Initialize the verificator client.

        Args:
            worker_pool: The WorkerPool instance to dispatch verification tasks
            cache_enabled: Whether to enable result caching (default: True)
        """
        self.worker_pool = worker_pool
        self._fallback_to_regex = True  # Use regex if verificator unavailable

        # AI-First Engine (NEW in v3.2)
        self.ai_engine: Optional["AIFirstEngine"] = None

        # =================================================================
        # AUTH ERROR TRACKING (NEW)
        # =================================================================
        # Track auth errors so orchestrator can pause operations
        self._last_auth_error: Optional[str] = None
        self._auth_error_count: int = 0

        # Caching layer (NEW in v3.2)
        self.cache_enabled = cache_enabled
        self._cache = VerificatorCache(
            max_size=500,
            default_ttl=300  # 5 minutes
        ) if cache_enabled else None

    def set_ai_engine(self, ai_engine: "AIFirstEngine") -> None:
        """
        Set the AI-first engine for intelligent fallback operations.

        When the verificator worker is unavailable, AI-first engine
        provides semantic understanding instead of regex patterns.
        """
        self.ai_engine = ai_engine
        logger.info("AI-First Engine connected to verificator client")

    # =========================================================================
    # AUTH ERROR HANDLING
    # =========================================================================

    def _handle_auth_error(self, result: Dict) -> None:
        """Record an authentication error from a result."""
        error_msg = result.get("message", "") or result.get("error", "OAuth token expired")
        self._last_auth_error = str(error_msg)
        self._auth_error_count += 1
        logger.error(f"AUTHENTICATION ERROR in verificator: {error_msg}")

    def has_auth_error(self) -> bool:
        """Check if there's a pending auth error."""
        return self._last_auth_error is not None

    def get_auth_error(self) -> Optional[str]:
        """Get the last auth error message."""
        return self._last_auth_error

    def clear_auth_error(self) -> None:
        """Clear the auth error state (after user re-authenticates)."""
        self._last_auth_error = None
        logger.info("Auth error state cleared")

    async def specify_artifacts(
        self,
        task_title: str,
        task_description: str,
        project_path: str
    ) -> List[str]:
        """
        Use Claude to intelligently determine expected artifacts for a task.

        Args:
            task_title: The task title
            task_description: The task description
            project_path: Path to the project

        Returns:
            List of expected artifact paths
        """
        # Check cache first
        if self._cache:
            cache_key = self._cache._make_key("artifacts", task_title, project_path)
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit for artifact specification: {task_title}")
                return cached

        if not self.worker_pool.is_verificator_available():
            logger.debug("Verificator not available, using AI-first fallback")
            # Use async AI-first fallback directly (not the sync wrapper)
            artifacts = await self._fallback_infer_artifacts_async(task_title, task_description)
            if self._cache:
                self._cache.set(cache_key, artifacts, ttl=600)  # 10 min for fallback
            return artifacts

        result = await self.worker_pool.dispatch_verification_task(
            "SPECIFY_ARTIFACTS",
            {
                "title": task_title,
                "description": task_description,
                "project_path": project_path
            }
        )

        # Check for error responses (timeout, worker_busy, auth errors, etc.)
        if result and is_auth_error(result):
            # AUTH ERROR: Record it and use fallback
            self._handle_auth_error(result)
            logger.error("Auth error in specify_artifacts - using fallback")
        elif result and "error" in result:
            logger.warning(f"Verificator error: {result.get('message', result['error'])}")
            if result.get("retryable"):
                logger.debug(f"Error is retryable, using fallback for now")
        elif result and "artifacts" in result:
            artifacts = result["artifacts"]
            logger.info(f"Verificator specified {len(artifacts)} artifacts for task: {task_title}")
            # Cache the result
            if self._cache:
                self._cache.set(cache_key, artifacts)
            return artifacts

        logger.warning("Verificator failed to specify artifacts, using AI-first fallback")
        # Use async AI-first fallback directly (not the sync wrapper)
        artifacts = await self._fallback_infer_artifacts_async(task_title, task_description)
        if self._cache:
            self._cache.set(cache_key, artifacts, ttl=600)  # 10 min for fallback
        return artifacts

    async def verify_completion(
        self,
        task_title: str,
        task_description: str,
        expected_artifacts: List[str],
        project_path: str,
        task_result: Optional[Dict] = None
    ) -> Tuple[bool, List[str], List[str]]:
        """
        Verify if a completed task actually created its expected artifacts.

        Args:
            task_title: The task title
            task_description: The task description
            expected_artifacts: List of expected artifacts
            project_path: Path to the project
            task_result: Optional result data from the task

        Returns:
            Tuple of (verified: bool, missing: List[str], found: List[str])
        """
        if not expected_artifacts:
            return True, [], []

        if not self.worker_pool.is_verificator_available():
            logger.debug("Verificator not available, using file check fallback")
            return self._fallback_verify_artifacts(expected_artifacts, project_path)

        result = await self.worker_pool.dispatch_verification_task(
            "VERIFY_COMPLETION",
            {
                "title": task_title,
                "description": task_description,
                "expected_artifacts": expected_artifacts,
                "project_path": project_path,
                "result": str(task_result) if task_result else "No result"
            }
        )

        # Check for error responses (timeout, worker_busy, auth errors, etc.)
        if result and is_auth_error(result):
            # AUTH ERROR: Record it and use fallback
            self._handle_auth_error(result)
            logger.error("Auth error in verify_completion - using file check fallback")
        elif result and "error" in result:
            logger.warning(f"Verificator error: {result.get('message', result['error'])}")
        elif result and "verified" in result:
            verified = result.get("verified", False)
            missing = result.get("missing", [])
            found = result.get("found", [])
            return verified, missing, found

        logger.warning("Verificator failed, using file check fallback")
        return self._fallback_verify_artifacts(expected_artifacts, project_path)

    async def check_duplicate(
        self,
        task1_title: str,
        task1_description: str,
        task2_title: str,
        task2_description: str
    ) -> Tuple[bool, float]:
        """
        Check if two tasks are semantically duplicates.

        Args:
            task1_title: First task title
            task1_description: First task description
            task2_title: Second task title
            task2_description: Second task description

        Returns:
            Tuple of (is_duplicate: bool, confidence: float)
        """
        # Check cache first (order tasks consistently for cache key)
        if self._cache:
            # Sort titles to ensure same pair always hits same cache key
            sorted_titles = sorted([task1_title, task2_title])
            cache_key = self._cache._make_key("duplicate", sorted_titles[0], sorted_titles[1])
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit for duplicate check")
                return cached

        if not self.worker_pool.is_verificator_available():
            logger.debug("Verificator not available, using word overlap fallback")
            result = self._fallback_check_duplicate(
                task1_title, task1_description,
                task2_title, task2_description
            )
            if self._cache:
                self._cache.set(cache_key, result, ttl=600)  # 10 min for fallback
            return result

        result = await self.worker_pool.dispatch_verification_task(
            "CHECK_DUPLICATE",
            {
                "task1_title": task1_title,
                "task1_description": task1_description or "",
                "task2_title": task2_title,
                "task2_description": task2_description or ""
            }
        )

        # Check for error responses (timeout, worker_busy, auth errors, etc.)
        if result and is_auth_error(result):
            # AUTH ERROR: Record it and use fallback
            self._handle_auth_error(result)
            logger.error("Auth error in check_duplicate - using word overlap fallback")
        elif result and "error" in result:
            logger.warning(f"Verificator error: {result.get('message', result['error'])}")
        elif result and "is_duplicate" in result:
            is_duplicate = result.get("is_duplicate", False)
            confidence = result.get("confidence", 0.0)
            dup_result = (is_duplicate, confidence)
            # Cache the result
            if self._cache:
                self._cache.set(cache_key, dup_result)
            return dup_result

        logger.warning("Verificator failed, using word overlap fallback")
        fallback_result = self._fallback_check_duplicate(
            task1_title, task1_description,
            task2_title, task2_description
        )
        if self._cache:
            self._cache.set(cache_key, fallback_result, ttl=600)
        return fallback_result

    def get_cache_stats(self) -> Optional[Dict[str, Any]]:
        """Get cache statistics for monitoring."""
        if self._cache:
            return self._cache.stats
        return None

    def invalidate_cache(self, prefix: Optional[str] = None) -> int:
        """Invalidate cache entries. If prefix given, only those; otherwise all."""
        if not self._cache:
            return 0
        if prefix:
            return self._cache.invalidate_prefix(prefix)
        self._cache.clear()
        return -1  # Indicates full clear

    async def match_project(
        self,
        objective_content: str,
        available_projects: List[Dict]
    ) -> Tuple[Optional[str], float]:
        """
        Match an objective to the correct project.

        Args:
            objective_content: The objective text
            available_projects: List of project dicts with path, name, etc.

        Returns:
            Tuple of (project_path: Optional[str], confidence: float)
        """
        if not available_projects:
            return None, 0.0

        if not self.worker_pool.is_verificator_available():
            logger.debug("Verificator not available, using keyword matching fallback")
            return self._fallback_match_project(objective_content, available_projects)

        result = await self.worker_pool.dispatch_verification_task(
            "MATCH_PROJECT",
            {
                "objective_content": objective_content,
                "projects": available_projects
            }
        )

        # Check for error responses (timeout, worker_busy, auth errors, etc.)
        if result and is_auth_error(result):
            # AUTH ERROR: Record it and use fallback
            self._handle_auth_error(result)
            logger.error("Auth error in match_project - using keyword matching fallback")
        elif result and "error" in result:
            logger.warning(f"Verificator error: {result.get('message', result['error'])}")
        elif result and "project_path" in result:
            project_path = result.get("project_path")
            confidence = result.get("confidence", 0.0)
            if project_path and confidence > 0.5:
                return project_path, confidence

        logger.warning("Verificator failed, using keyword matching fallback")
        return self._fallback_match_project(objective_content, available_projects)

    async def audit_completed_task(
        self,
        task_id: str,
        task_title: str,
        expected_artifacts: List[str],
        project_path: str
    ) -> Tuple[bool, List[str], str]:
        """
        Audit a completed task to verify its artifacts exist.

        Args:
            task_id: The task ID
            task_title: The task title
            expected_artifacts: List of expected artifacts
            project_path: Path to the project

        Returns:
            Tuple of (passed: bool, missing_artifacts: List[str], recommendation: str)
        """
        if not expected_artifacts:
            return True, [], "accept"

        if not self.worker_pool.is_verificator_available():
            logger.debug("Verificator not available, using file check fallback")
            verified, missing, _ = self._fallback_verify_artifacts(expected_artifacts, project_path)
            recommendation = "accept" if verified else "re-run"
            return verified, missing, recommendation

        result = await self.worker_pool.dispatch_verification_task(
            "AUDIT_COMPLETED",
            {
                "task_id": task_id,
                "title": task_title,
                "expected_artifacts": expected_artifacts,
                "project_path": project_path
            }
        )

        # Check for error responses (timeout, worker_busy, auth errors, etc.)
        if result and is_auth_error(result):
            # AUTH ERROR: Record it and use fallback
            self._handle_auth_error(result)
            logger.error("Auth error in audit_completed_task - using file check fallback")
        elif result and "error" in result:
            logger.warning(f"Verificator error: {result.get('message', result['error'])}")
        elif result and "passed" in result:
            passed = result.get("passed", False)
            missing = result.get("missing_artifacts", [])
            recommendation = result.get("recommendation", "manual-review")
            return passed, missing, recommendation

        logger.warning("Verificator failed, using file check fallback")
        verified, missing, _ = self._fallback_verify_artifacts(expected_artifacts, project_path)
        recommendation = "accept" if verified else "re-run"
        return verified, missing, recommendation

    async def semantic_check(
        self,
        task_title: str,
        task_description: str,
        task_result: Optional[Dict],
        files_created: List[str]
    ) -> Tuple[bool, float, List[str]]:
        """
        Check if task output semantically matches requirements.

        Args:
            task_title: The task title
            task_description: The task description
            task_result: The task result dict
            files_created: List of files created by the task

        Returns:
            Tuple of (matches: bool, coverage: float, gaps: List[str])
            NOTE: When verification fails due to auth error, returns:
            (False, 0.0, ["VERIFICATION_UNAVAILABLE: Auth error"])
        """
        if not self.worker_pool.is_verificator_available():
            # Check if we have a pending auth error
            if self._last_auth_error:
                logger.warning(f"Semantic check skipped due to auth error: {self._last_auth_error}")
                return False, 0.0, ["VERIFICATION_UNAVAILABLE: Authentication expired"]
            # No good fallback for semantic checking, but no auth error
            logger.debug("Verificator not available, assuming success for semantic check")
            return True, 1.0, []

        result = await self.worker_pool.dispatch_verification_task(
            "SEMANTIC_CHECK",
            {
                "title": task_title,
                "description": task_description,
                "result": str(task_result) if task_result else "No result",
                "files_created": files_created
            }
        )

        # Check for error responses (timeout, worker_busy, auth errors, etc.)
        if result and is_auth_error(result):
            # AUTH ERROR: Record it and return failure indicator
            self._handle_auth_error(result)
            logger.error("Auth error in semantic_check - CANNOT verify task completion")
            return False, 0.0, ["VERIFICATION_UNAVAILABLE: Authentication expired - please re-login"]
        elif result and "error" in result:
            logger.warning(f"Verificator error: {result.get('message', result['error'])}")
        elif result and "matches" in result:
            matches = result.get("matches", True)
            coverage = result.get("coverage", 1.0)
            gaps = result.get("gaps", [])
            return matches, coverage, gaps

        # No good fallback - but distinguish from auth errors
        if self._last_auth_error:
            return False, 0.0, ["VERIFICATION_UNAVAILABLE: Authentication expired"]
        return True, 1.0, []

    # =========================================================================
    # FALLBACK METHODS (When verificator is unavailable)
    # =========================================================================
    # NEW IN v3.2: AI-First fallbacks
    # These methods now use AI-first engine when available, regex as last resort

    async def _fallback_infer_artifacts_async(self, title: str, description: str) -> List[str]:
        """
        AI-first artifact inference fallback.

        Priority:
        1. AI-First Engine (semantic understanding)
        2. Regex patterns (deprecated, last resort)
        """
        # Try AI-First Engine
        if self.ai_engine:
            try:
                result = await self.ai_engine.infer_artifacts(title, description)
                if result.success and result.result:
                    artifacts = result.result.get("artifacts", [])
                    artifact_paths = [
                        a.get("path", a.get("name", ""))
                        for a in artifacts if a
                    ]
                    if artifact_paths:
                        logger.debug(f"AI-first inferred {len(artifact_paths)} artifacts")
                        return artifact_paths
            except Exception as e:
                logger.warning(f"AI-first artifact inference failed: {e}")

        # Fall back to regex (deprecated)
        logger.debug("Using deprecated regex artifact inference")
        return self._regex_infer_artifacts(title, description)

    def _fallback_infer_artifacts(self, title: str, description: str) -> List[str]:
        """Sync wrapper for backward compatibility."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If in async context, use the sync fallback directly
                return self._regex_infer_artifacts(title, description)
            return loop.run_until_complete(
                self._fallback_infer_artifacts_async(title, description)
            )
        except RuntimeError:
            return self._regex_infer_artifacts(title, description)

    def _regex_infer_artifacts(self, title: str, description: str) -> List[str]:
        """DEPRECATED: Regex-based artifact inference. Use AI-first instead."""
        import re

        artifacts = []
        text = f"{title} {description}".lower()

        # File creation patterns
        file_patterns = [
            r'create\s+(?:file\s+)?["\']?([a-z0-9_/.-]+\.(py|js|ts|tsx|css|html|json|yaml|yml|md))["\']?',
            r'add\s+(?:file\s+)?["\']?([a-z0-9_/.-]+\.(py|js|ts|tsx|css|html|json|yaml|yml|md))["\']?',
            r'implement\s+["\']?([a-z0-9_/.-]+\.(py|js|ts|tsx))["\']?',
        ]

        for pattern in file_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    artifacts.append(match[0])
                else:
                    artifacts.append(match)

        # Endpoint patterns (FastAPI/Express style)
        endpoint_patterns = [
            r'(?:create|add|implement)\s+(?:endpoint|route)\s+(?:for\s+)?["\']?(/[a-z0-9_/-]+)["\']?',
            r'(?:POST|GET|PUT|DELETE|PATCH)\s+["\']?(/[a-z0-9_/-]+)["\']?',
        ]

        for pattern in endpoint_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Convert endpoint to likely file
                endpoint_name = match.strip('/').split('/')[-1]
                if 'api' in title.lower() or 'backend' in title.lower():
                    artifacts.append(f"app/routers/{endpoint_name}.py")
                else:
                    artifacts.append(f"src/routes/{endpoint_name}.ts")

        # Common patterns
        if 'model' in title.lower():
            if 'sqlalchemy' in text or 'python' in text or '.py' in text:
                model_name = self._extract_entity_name(title)
                if model_name:
                    artifacts.append(f"app/models/{model_name.lower()}.py")

        if 'component' in title.lower() and ('react' in text or '.tsx' in text):
            component_name = self._extract_entity_name(title)
            if component_name:
                artifacts.append(f"src/components/{component_name}.tsx")

        return list(set(artifacts))

    def _extract_entity_name(self, title: str) -> Optional[str]:
        """Extract entity name from task title."""
        import re

        # Try to find a capitalized word that's likely the entity name
        patterns = [
            r'(?:create|add|implement)\s+(\w+)\s+(?:model|component|service)',
            r'(\w+)\s+(?:model|component|service)',
        ]

        for pattern in patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                name = match.group(1)
                if name.lower() not in ['the', 'a', 'an', 'new', 'create', 'add']:
                    return name

        return None

    def _fallback_verify_artifacts(
        self,
        expected_artifacts: List[str],
        project_path: str
    ) -> Tuple[bool, List[str], List[str]]:
        """Simple file existence check fallback."""
        missing = []
        found = []
        project = Path(project_path)

        for artifact in expected_artifacts:
            # Handle both absolute and relative paths
            if artifact.startswith('/'):
                full_path = Path(artifact)
            else:
                full_path = project / artifact

            if full_path.exists():
                found.append(artifact)
            else:
                # Try common variations
                variations = [
                    project / artifact,
                    project / "src" / artifact,
                    project / "app" / artifact,
                ]

                artifact_found = False
                for var_path in variations:
                    if var_path.exists():
                        found.append(artifact)
                        artifact_found = True
                        break

                if not artifact_found:
                    missing.append(artifact)

        verified = len(missing) == 0
        return verified, missing, found

    async def _fallback_check_duplicate_async(
        self,
        task1_title: str,
        task1_description: str,
        task2_title: str,
        task2_description: str
    ) -> Tuple[bool, float]:
        """
        AI-first duplicate detection fallback.

        Priority:
        1. AI-First Engine (semantic understanding)
        2. Word overlap (deprecated, last resort)
        """
        # Try AI-First Engine
        if self.ai_engine:
            try:
                result = await self.ai_engine.check_duplicate(
                    task1_title, task1_description,
                    task2_title, task2_description
                )
                if result.success and result.result:
                    is_dup = result.result.get("is_duplicate", False)
                    similarity = result.result.get("similarity", 0.0)
                    logger.debug(f"AI-first duplicate check: {is_dup} ({similarity:.2f})")
                    return is_dup, similarity
            except Exception as e:
                logger.warning(f"AI-first duplicate check failed: {e}")

        # Fall back to word overlap (deprecated)
        logger.debug("Using deprecated word overlap duplicate detection")
        return self._regex_check_duplicate(
            task1_title, task1_description,
            task2_title, task2_description
        )

    def _fallback_check_duplicate(
        self,
        task1_title: str,
        task1_description: str,
        task2_title: str,
        task2_description: str
    ) -> Tuple[bool, float]:
        """Sync wrapper for backward compatibility."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return self._regex_check_duplicate(
                    task1_title, task1_description,
                    task2_title, task2_description
                )
            return loop.run_until_complete(
                self._fallback_check_duplicate_async(
                    task1_title, task1_description,
                    task2_title, task2_description
                )
            )
        except RuntimeError:
            return self._regex_check_duplicate(
                task1_title, task1_description,
                task2_title, task2_description
            )

    def _regex_check_duplicate(
        self,
        task1_title: str,
        task1_description: str,
        task2_title: str,
        task2_description: str
    ) -> Tuple[bool, float]:
        """DEPRECATED: Word overlap based duplicate detection. Use AI-first instead."""
        import re

        def normalize(text: str) -> set:
            if not text:
                return set()
            words = re.findall(r'\b[a-z]+\b', text.lower())
            # Filter stopwords
            stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those'}
            return set(w for w in words if w not in stopwords and len(w) > 2)

        text1 = f"{task1_title} {task1_description}"
        text2 = f"{task2_title} {task2_description}"

        words1 = normalize(text1)
        words2 = normalize(text2)

        if not words1 or not words2:
            return False, 0.0

        # Jaccard similarity
        intersection = len(words1 & words2)
        union = len(words1 | words2)

        similarity = intersection / union if union > 0 else 0.0

        # Consider duplicate if >70% overlap
        is_duplicate = similarity > 0.7

        return is_duplicate, similarity

    async def _fallback_match_project_async(
        self,
        objective_content: str,
        available_projects: List[Dict]
    ) -> Tuple[Optional[str], float]:
        """
        AI-first project matching fallback.

        Priority:
        1. AI-First Engine (semantic understanding)
        2. Keyword matching (deprecated, last resort)
        """
        # Try AI-First Engine
        if self.ai_engine:
            try:
                project_names = [
                    p.get("path", p.get("name", ""))
                    for p in available_projects
                ]
                result = await self.ai_engine.detect_project_path(
                    task_title="",
                    task_description=objective_content,
                    available_projects=project_names
                )
                if result.success and result.result:
                    project_path = result.result.get("project_path")
                    confidence = result.confidence
                    if project_path:
                        logger.debug(f"AI-first matched project: {project_path} ({confidence:.2f})")
                        return project_path, confidence
            except Exception as e:
                logger.warning(f"AI-first project matching failed: {e}")

        # Fall back to keyword matching (deprecated)
        logger.debug("Using deprecated keyword project matching")
        return self._regex_match_project(objective_content, available_projects)

    def _fallback_match_project(
        self,
        objective_content: str,
        available_projects: List[Dict]
    ) -> Tuple[Optional[str], float]:
        """Sync wrapper for backward compatibility."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return self._regex_match_project(objective_content, available_projects)
            return loop.run_until_complete(
                self._fallback_match_project_async(objective_content, available_projects)
            )
        except RuntimeError:
            return self._regex_match_project(objective_content, available_projects)

    def _regex_match_project(
        self,
        objective_content: str,
        available_projects: List[Dict]
    ) -> Tuple[Optional[str], float]:
        """DEPRECATED: Keyword matching based project matching. Use AI-first instead."""
        objective_lower = objective_content.lower()
        best_match = None
        best_score = 0.0

        for project in available_projects:
            project_path = project.get("path", "")
            project_name = project.get("name", Path(project_path).name if project_path else "")

            score = 0.0

            # Check if project name appears in objective
            if project_name.lower() in objective_lower:
                score += 0.5

            # Check for common keywords
            keywords = project.get("keywords", [])
            for keyword in keywords:
                if keyword.lower() in objective_lower:
                    score += 0.1

            # Check technology stack matches
            tech_stack = project.get("tech_stack", [])
            for tech in tech_stack:
                if tech.lower() in objective_lower:
                    score += 0.05

            if score > best_score:
                best_score = min(score, 1.0)
                best_match = project_path

        return best_match, best_score


# Helper function for easy access
_verificator_client: Optional[VerificatorClient] = None


def get_verificator_client(worker_pool=None) -> Optional[VerificatorClient]:
    """Get or create the global verificator client."""
    global _verificator_client

    if _verificator_client is None and worker_pool is not None:
        _verificator_client = VerificatorClient(worker_pool)

    return _verificator_client


def set_verificator_client(client: VerificatorClient) -> None:
    """Set the global verificator client."""
    global _verificator_client
    _verificator_client = client
