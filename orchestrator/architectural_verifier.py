# =============================================================================
# CLOPUS v3 Architectural Verifier
# =============================================================================
"""
Verifies that implementation actually matches architectural requirements.
Uses Claude Code intelligence to analyze code semantically, not regex patterns.

This catches gaps like:
- Database models exist but endpoints use in-memory storage
- Auth is specified but not implemented
- Redis caching specified but not used
"""

import logging
from typing import Any, Dict, List, Optional
from pathlib import Path
from dataclasses import dataclass, field

# Import auth error detection from verificator_client
from .verificator_client import is_auth_error

logger = logging.getLogger("clopus.architectural_verifier")


@dataclass
class ArchitecturalGap:
    """Represents a gap between requirements and implementation."""
    requirement: str
    actual_state: str
    severity: str  # critical, high, medium, low
    category: str  # database, auth, cache, api, etc.
    files_affected: List[str] = field(default_factory=list)
    remediation_steps: List[str] = field(default_factory=list)


class ArchitecturalVerifier:
    """
    Uses Claude Code to verify implementation matches requirements.

    Unlike regex-based verification, this uses actual AI intelligence to:
    1. Read and understand CLAUDE.md requirements
    2. Analyze source code semantically
    3. Detect when code "exists but doesn't work" (e.g., models not connected)
    4. Generate specific remediation tasks
    """

    def __init__(self, worker_pool):
        """
        Initialize the architectural verifier.

        Args:
            worker_pool: The WorkerPool instance to dispatch analysis tasks
        """
        self.worker_pool = worker_pool
        self._last_auth_error: Optional[str] = None

    def has_auth_error(self) -> bool:
        """Check if there's a pending auth error."""
        return self._last_auth_error is not None

    def get_auth_error(self) -> Optional[str]:
        """Get the last auth error message."""
        return self._last_auth_error

    def clear_auth_error(self) -> None:
        """Clear auth error state."""
        self._last_auth_error = None

    async def verify_project(self, project_path: str) -> List[ArchitecturalGap]:
        """
        Perform comprehensive architectural verification of a project.

        Uses Claude to:
        1. Parse CLAUDE.md for requirements
        2. Analyze actual code implementation
        3. Identify gaps between requirements and reality

        Args:
            project_path: Path to the project to verify

        Returns:
            List of architectural gaps found.
            NOTE: Returns a special gap with category="AUTH_ERROR" if auth failed.
        """
        logger.info(f"Starting architectural verification for: {project_path}")

        # Dispatch to verificator worker (worker 8) for intelligent analysis
        result = await self.worker_pool.dispatch_verification_task(
            "ARCHITECTURAL_ANALYSIS",
            {
                "project_path": project_path,
                "analysis_type": "full"
            }
        )

        # Check for auth errors FIRST
        if result and is_auth_error(result):
            error_msg = result.get("message", "") or result.get("error", "OAuth token expired")
            self._last_auth_error = str(error_msg)
            logger.error(f"AUTHENTICATION ERROR in architectural verification: {error_msg}")
            # Return a special gap to indicate verification couldn't be performed
            return [ArchitecturalGap(
                requirement="Architectural verification",
                actual_state="VERIFICATION FAILED: Authentication expired - please re-login to Claude Code",
                severity="critical",
                category="AUTH_ERROR",
                files_affected=[],
                remediation_steps=["Re-authenticate Claude Code workers: docker exec -it clopus-worker-1 claude login"]
            )]

        if result and "error" in result:
            logger.warning(f"Architectural analysis error: {result.get('message', result['error'])}")
            # Return empty but log the real error
            return []

        if result and "gaps" in result:
            gaps = []
            for gap_data in result["gaps"]:
                gaps.append(ArchitecturalGap(
                    requirement=gap_data.get("requirement", "Unknown"),
                    actual_state=gap_data.get("actual_state", "Unknown"),
                    severity=gap_data.get("severity", "medium"),
                    category=gap_data.get("category", "unknown"),
                    files_affected=gap_data.get("files_affected", []),
                    remediation_steps=gap_data.get("remediation_steps", [])
                ))

            logger.info(f"Found {len(gaps)} architectural gaps in {project_path}")
            return gaps

        logger.warning("Architectural analysis returned no results")
        return []

    async def verify_database_integration(self, project_path: str) -> List[ArchitecturalGap]:
        """
        Specifically verify database integration is complete.

        Checks:
        - Database is specified in CLAUDE.md
        - Models exist
        - Endpoints actually USE the models (not in-memory dicts)
        - Database session is properly injected

        Args:
            project_path: Path to the project

        Returns:
            List of database-related gaps
        """
        result = await self.worker_pool.dispatch_verification_task(
            "ARCHITECTURAL_ANALYSIS",
            {
                "project_path": project_path,
                "analysis_type": "database_integration",
                "instructions": """
                Analyze if the database is properly integrated:

                1. Read CLAUDE.md to check if PostgreSQL/database is required
                2. Check if SQLAlchemy models exist in app/models/
                3. Check if endpoints in app/api/ actually USE those models
                4. Look for anti-patterns like:
                   - _db: dict or = {} for storage
                   - Missing Depends(get_db) in endpoint signatures
                   - Models imported but never used
                   - Comments like "# In-memory" or "# TODO: database"

                For each gap found, provide:
                - What the requirement says
                - What the code actually does
                - Specific files that need fixing
                - Exact steps to fix it
                """
            }
        )

        return self._parse_gap_result(result, "database")

    async def verify_auth_implementation(self, project_path: str) -> List[ArchitecturalGap]:
        """
        Verify authentication is properly implemented.

        Checks:
        - Auth is specified in CLAUDE.md
        - Auth endpoints exist (/auth/login, /auth/register, etc.)
        - JWT token handling is implemented
        - Protected routes use auth dependencies

        Args:
            project_path: Path to the project

        Returns:
            List of auth-related gaps
        """
        result = await self.worker_pool.dispatch_verification_task(
            "ARCHITECTURAL_ANALYSIS",
            {
                "project_path": project_path,
                "analysis_type": "auth_implementation",
                "instructions": """
                Analyze if authentication is properly implemented:

                1. Read CLAUDE.md to check if JWT/auth is required
                2. Check for auth endpoints (/auth/login, /auth/register, etc.)
                3. Check for JWT token creation and validation
                4. Check if protected routes have auth dependencies
                5. Look for frontend auth handling

                For each gap found, provide specific remediation steps.
                """
            }
        )

        return self._parse_gap_result(result, "auth")

    async def verify_cache_implementation(self, project_path: str) -> List[ArchitecturalGap]:
        """
        Verify caching is properly implemented.

        Args:
            project_path: Path to the project

        Returns:
            List of cache-related gaps
        """
        result = await self.worker_pool.dispatch_verification_task(
            "ARCHITECTURAL_ANALYSIS",
            {
                "project_path": project_path,
                "analysis_type": "cache_implementation",
                "instructions": """
                Analyze if caching is properly implemented:

                1. Read CLAUDE.md to check if Redis/caching is required
                2. Check for Redis client configuration
                3. Check if cache is actually used in endpoints
                4. Look for cache decorators or explicit cache calls

                For each gap found, provide specific remediation steps.
                """
            }
        )

        return self._parse_gap_result(result, "cache")

    async def verify_persistence(self, project_path: str, api_port: int = 8000) -> ArchitecturalGap:
        """
        Verify that data actually persists by testing restart behavior.

        This is a runtime test that:
        1. Starts the API
        2. Creates test data
        3. Restarts the API
        4. Checks if data survived

        Args:
            project_path: Path to the project
            api_port: Port to run the API on

        Returns:
            Gap if persistence fails, None if it works
        """
        result = await self.worker_pool.dispatch_verification_task(
            "PERSISTENCE_TEST",
            {
                "project_path": project_path,
                "api_port": api_port,
                "instructions": """
                Test that data actually persists:

                1. Start the API server
                2. Create a test node via POST /api/v1/nodes
                3. Note the node ID
                4. Stop the server
                5. Start the server again
                6. Try to GET /api/v1/nodes/{id}

                If the node is NOT found after restart:
                - This proves in-memory storage is being used
                - Data does not persist
                - Database integration is REQUIRED

                Return whether persistence passed or failed, with details.
                """
            }
        )

        if result and result.get("persistence_failed"):
            return ArchitecturalGap(
                requirement="Data must persist across restarts (PostgreSQL)",
                actual_state="Data is lost on restart (in-memory storage)",
                severity="critical",
                category="database",
                files_affected=result.get("files_affected", []),
                remediation_steps=result.get("remediation_steps", [
                    "Replace in-memory dict storage with SQLAlchemy session",
                    "Add Depends(get_db) to endpoint signatures",
                    "Use session.add(), session.execute() for data operations",
                    "Import and use models from app/models/"
                ])
            )

        return None

    async def generate_remediation_tasks(
        self,
        gaps: List[ArchitecturalGap],
        project_path: str
    ) -> List[Dict[str, Any]]:
        """
        Generate specific remediation tasks for detected gaps.

        Uses Claude to create detailed, actionable tasks that workers can execute.

        Args:
            gaps: List of architectural gaps to fix
            project_path: Path to the project

        Returns:
            List of task dictionaries ready for task planner
        """
        if not gaps:
            return []

        # Group gaps by category for efficient task creation
        critical_gaps = [g for g in gaps if g.severity == "critical"]
        high_gaps = [g for g in gaps if g.severity == "high"]
        other_gaps = [g for g in gaps if g.severity not in ("critical", "high")]

        tasks = []

        # Critical gaps get individual tasks
        for gap in critical_gaps:
            result = await self.worker_pool.dispatch_verification_task(
                "GENERATE_REMEDIATION_TASK",
                {
                    "project_path": project_path,
                    "gap": {
                        "requirement": gap.requirement,
                        "actual_state": gap.actual_state,
                        "category": gap.category,
                        "files_affected": gap.files_affected,
                        "remediation_steps": gap.remediation_steps
                    },
                    "instructions": """
                    Generate a detailed task to fix this architectural gap.

                    The task should:
                    1. Have a clear, actionable title
                    2. Include specific files to modify
                    3. Include code changes needed
                    4. Reference the original requirement

                    Return a task object with:
                    - title: string
                    - description: detailed string
                    - priority: "urgent" for critical
                    - worker_role: "coder" or appropriate role
                    """
                }
            )

            if result and "task" in result:
                task = result["task"]
                task["priority"] = "urgent"
                task["metadata"] = {
                    "gap_category": gap.category,
                    "gap_severity": gap.severity,
                    "architectural_remediation": True
                }
                tasks.append(task)

        # High priority gaps
        for gap in high_gaps:
            tasks.append({
                "title": f"Fix {gap.category}: {gap.requirement[:50]}...",
                "description": f"""
## Architectural Gap

**Requirement:** {gap.requirement}
**Current State:** {gap.actual_state}
**Severity:** {gap.severity}

## Files Affected
{chr(10).join(f'- {f}' for f in gap.files_affected)}

## Remediation Steps
{chr(10).join(f'{i+1}. {step}' for i, step in enumerate(gap.remediation_steps))}
                """,
                "priority": "high",
                "worker_role": "coder",
                "metadata": {
                    "gap_category": gap.category,
                    "gap_severity": gap.severity,
                    "architectural_remediation": True
                }
            })

        return tasks

    def _parse_gap_result(
        self,
        result: Optional[Dict],
        category: str
    ) -> List[ArchitecturalGap]:
        """Parse verification result into gap objects."""
        if not result:
            return []

        if "error" in result:
            logger.warning(f"{category} analysis error: {result.get('message', result['error'])}")
            return []

        gaps = []
        for gap_data in result.get("gaps", []):
            gaps.append(ArchitecturalGap(
                requirement=gap_data.get("requirement", "Unknown"),
                actual_state=gap_data.get("actual_state", "Unknown"),
                severity=gap_data.get("severity", "medium"),
                category=category,
                files_affected=gap_data.get("files_affected", []),
                remediation_steps=gap_data.get("remediation_steps", [])
            ))

        return gaps


# Singleton instance
_architectural_verifier: Optional[ArchitecturalVerifier] = None


def get_architectural_verifier(worker_pool=None) -> Optional[ArchitecturalVerifier]:
    """Get or create the global architectural verifier."""
    global _architectural_verifier

    if _architectural_verifier is None and worker_pool is not None:
        _architectural_verifier = ArchitecturalVerifier(worker_pool)

    return _architectural_verifier
