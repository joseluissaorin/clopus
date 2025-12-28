# =============================================================================
# CLOPUS v3 Verificator Client
# =============================================================================
"""
High-level interface for intelligent verification using Worker 8 (Verificator).
Provides semantic analysis, deduplication, and artifact verification using Claude.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger("clopus.verificator_client")


class VerificatorClient:
    """Client for intelligent verification operations using the Verificator worker."""

    def __init__(self, worker_pool):
        """
        Initialize the verificator client.

        Args:
            worker_pool: The WorkerPool instance to dispatch verification tasks
        """
        self.worker_pool = worker_pool
        self._fallback_to_regex = True  # Use regex if verificator unavailable

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
        if not self.worker_pool.is_verificator_available():
            logger.debug("Verificator not available, using regex fallback")
            return self._fallback_infer_artifacts(task_title, task_description)

        result = await self.worker_pool.dispatch_verification_task(
            "SPECIFY_ARTIFACTS",
            {
                "title": task_title,
                "description": task_description,
                "project_path": project_path
            }
        )

        if result and "artifacts" in result:
            artifacts = result["artifacts"]
            logger.info(f"Verificator specified {len(artifacts)} artifacts for task: {task_title}")
            return artifacts

        logger.warning("Verificator failed to specify artifacts, using regex fallback")
        return self._fallback_infer_artifacts(task_title, task_description)

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

        if result:
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
        if not self.worker_pool.is_verificator_available():
            logger.debug("Verificator not available, using word overlap fallback")
            return self._fallback_check_duplicate(
                task1_title, task1_description,
                task2_title, task2_description
            )

        result = await self.worker_pool.dispatch_verification_task(
            "CHECK_DUPLICATE",
            {
                "task1_title": task1_title,
                "task1_description": task1_description or "",
                "task2_title": task2_title,
                "task2_description": task2_description or ""
            }
        )

        if result:
            is_duplicate = result.get("is_duplicate", False)
            confidence = result.get("confidence", 0.0)
            return is_duplicate, confidence

        logger.warning("Verificator failed, using word overlap fallback")
        return self._fallback_check_duplicate(
            task1_title, task1_description,
            task2_title, task2_description
        )

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

        if result:
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

        if result:
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
        """
        if not self.worker_pool.is_verificator_available():
            # No good fallback for semantic checking
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

        if result:
            matches = result.get("matches", True)
            coverage = result.get("coverage", 1.0)
            gaps = result.get("gaps", [])
            return matches, coverage, gaps

        # No good fallback, assume success
        return True, 1.0, []

    # =========================================================================
    # FALLBACK METHODS (When verificator is unavailable)
    # =========================================================================

    def _fallback_infer_artifacts(self, title: str, description: str) -> List[str]:
        """Regex-based artifact inference fallback."""
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

    def _fallback_check_duplicate(
        self,
        task1_title: str,
        task1_description: str,
        task2_title: str,
        task2_description: str
    ) -> Tuple[bool, float]:
        """Word overlap based duplicate detection fallback."""
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

    def _fallback_match_project(
        self,
        objective_content: str,
        available_projects: List[Dict]
    ) -> Tuple[Optional[str], float]:
        """Keyword matching based project matching fallback."""
        import re

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
