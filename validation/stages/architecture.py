# =============================================================================
# CLOPUS v3 Architecture Validation Stage
# =============================================================================
"""
Validates that implementation actually matches architectural requirements.
Uses Claude Code intelligence, not regex patterns.

This stage catches gaps like:
- Database models exist but endpoints use in-memory storage
- Auth is specified but not implemented
- Redis caching specified but not used
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseValidator
from ..pipeline import StageResult, ValidationStatus

logger = logging.getLogger("clopus.validation.architecture")


class ArchitectureValidator(BaseValidator):
    """
    Validates architectural compliance using Claude Code intelligence.

    This is a BLOCKING stage - if critical architectural gaps are found,
    validation fails even if all other stages pass.
    """

    stage_name = "architecture"

    def __init__(self, worker_pool=None):
        super().__init__()
        self.worker_pool = worker_pool
        self._architectural_verifier = None

    @property
    def architectural_verifier(self):
        """Lazy load the architectural verifier."""
        if self._architectural_verifier is None and self.worker_pool:
            try:
                from orchestrator.architectural_verifier import get_architectural_verifier
                self._architectural_verifier = get_architectural_verifier(self.worker_pool)
            except Exception as e:
                logger.warning(f"Could not load architectural verifier: {e}")
        return self._architectural_verifier

    async def validate(
        self,
        path: Path,
        project_type: str
    ) -> StageResult:
        """
        Validate architectural compliance.

        Checks:
        1. Database integration (if PostgreSQL/database in requirements)
        2. Authentication implementation (if auth required)
        3. Cache usage (if Redis in requirements)
        4. Overall architecture compliance

        Returns:
            StageResult with PASSED, FAILED, or SKIPPED status
        """
        import time
        start_time = time.time()

        project = path
        project_path = str(path)
        errors = []
        warnings = []
        metadata = {}

        # Check if architectural verifier is available
        if not self.architectural_verifier:
            logger.warning("Architectural verifier not available, using fallback checks")
            return await self._fallback_validation(project_path, start_time)

        try:
            # Read project requirements from CLAUDE.md
            requirements = await self._extract_requirements(project)
            metadata["requirements_detected"] = requirements

            gaps = []

            # Check database integration if required
            if requirements.get("database"):
                logger.info("Checking database integration...")
                db_gaps = await self.architectural_verifier.verify_database_integration(project_path)
                gaps.extend(db_gaps)
                metadata["database_check"] = {
                    "required": True,
                    "gaps_found": len(db_gaps)
                }

            # Check auth implementation if required
            if requirements.get("auth"):
                logger.info("Checking auth implementation...")
                auth_gaps = await self.architectural_verifier.verify_auth_implementation(project_path)
                gaps.extend(auth_gaps)
                metadata["auth_check"] = {
                    "required": True,
                    "gaps_found": len(auth_gaps)
                }

            # Check cache implementation if required
            if requirements.get("cache"):
                logger.info("Checking cache implementation...")
                cache_gaps = await self.architectural_verifier.verify_cache_implementation(project_path)
                gaps.extend(cache_gaps)
                metadata["cache_check"] = {
                    "required": True,
                    "gaps_found": len(cache_gaps)
                }

            # Process gaps
            critical_gaps = [g for g in gaps if g.severity == "critical"]
            high_gaps = [g for g in gaps if g.severity == "high"]
            other_gaps = [g for g in gaps if g.severity not in ("critical", "high")]

            # Critical gaps are errors (fail validation)
            for gap in critical_gaps:
                errors.append(
                    f"CRITICAL: {gap.requirement} - Actual: {gap.actual_state} "
                    f"(Files: {', '.join(gap.files_affected[:3])})"
                )

            # High severity gaps are also errors
            for gap in high_gaps:
                errors.append(
                    f"HIGH: {gap.requirement} - Actual: {gap.actual_state}"
                )

            # Lower severity gaps are warnings
            for gap in other_gaps:
                warnings.append(
                    f"{gap.severity.upper()}: {gap.requirement} - {gap.actual_state}"
                )

            metadata["total_gaps"] = len(gaps)
            metadata["critical_count"] = len(critical_gaps)
            metadata["high_count"] = len(high_gaps)

            duration_ms = int((time.time() - start_time) * 1000)

            # Determine status
            if critical_gaps or high_gaps:
                return StageResult(
                    stage="architecture",
                    status=ValidationStatus.FAILED,
                    duration_ms=duration_ms,
                    output=f"Found {len(critical_gaps)} critical and {len(high_gaps)} high severity architectural gaps",
                    errors=errors,
                    warnings=warnings,
                    metadata=metadata
                )

            if warnings:
                return StageResult(
                    stage="architecture",
                    status=ValidationStatus.PASSED,
                    duration_ms=duration_ms,
                    output=f"Architecture OK with {len(warnings)} minor issues",
                    errors=[],
                    warnings=warnings,
                    metadata=metadata
                )

            return StageResult(
                stage="architecture",
                status=ValidationStatus.PASSED,
                duration_ms=duration_ms,
                output="Architecture validation passed",
                errors=[],
                warnings=[],
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"Architecture validation error: {e}", exc_info=True)
            duration_ms = int((time.time() - start_time) * 1000)
            return StageResult(
                stage="architecture",
                status=ValidationStatus.FAILED,
                duration_ms=duration_ms,
                output=f"Architecture validation error: {str(e)}",
                errors=[str(e)],
                warnings=[],
                metadata=metadata
            )

    async def _extract_requirements(self, project: Path) -> Dict[str, bool]:
        """Extract architectural requirements from CLAUDE.md."""
        requirements = {
            "database": False,
            "auth": False,
            "cache": False
        }

        claude_md = project / "CLAUDE.md"
        if not claude_md.exists():
            return requirements

        try:
            content = claude_md.read_text().lower()

            # Check for database requirements
            if any(term in content for term in [
                "postgresql", "postgres", "database", "sqlalchemy",
                "sql", "persist", "storage"
            ]):
                requirements["database"] = True

            # Check for auth requirements
            if any(term in content for term in [
                "authentication", "jwt", "login", "auth",
                "authorization", "oauth", "session"
            ]):
                requirements["auth"] = True

            # Check for cache requirements
            if any(term in content for term in [
                "redis", "cache", "caching", "memcached"
            ]):
                requirements["cache"] = True

        except Exception as e:
            logger.warning(f"Error reading CLAUDE.md: {e}")

        return requirements

    async def _fallback_validation(
        self,
        project_path: str,
        start_time: float
    ) -> StageResult:
        """
        Fallback validation when architectural verifier is not available.
        Uses simple pattern matching to detect obvious anti-patterns.
        """
        import time
        project = Path(project_path)
        errors = []
        warnings = []

        # Check for in-memory storage anti-patterns
        api_dir = project / "app" / "api"
        if api_dir.exists():
            for py_file in api_dir.rglob("*.py"):
                try:
                    content = py_file.read_text()

                    # Check for in-memory dict storage
                    if "_db: dict" in content or "_db = {}" in content:
                        errors.append(
                            f"In-memory storage detected in {py_file.relative_to(project)}: "
                            "Replace with database session"
                        )

                    if "_storage: dict" in content or "_storage = {}" in content:
                        errors.append(
                            f"In-memory storage detected in {py_file.relative_to(project)}"
                        )

                    # Check for TODO comments indicating incomplete work
                    if "# TODO: database" in content.lower():
                        warnings.append(
                            f"Incomplete database integration in {py_file.relative_to(project)}"
                        )

                    if "# in-memory" in content.lower():
                        warnings.append(
                            f"In-memory placeholder in {py_file.relative_to(project)}"
                        )

                except Exception as e:
                    logger.debug(f"Error reading {py_file}: {e}")

        duration_ms = int((time.time() - start_time) * 1000)

        if errors:
            return StageResult(
                stage="architecture",
                status=ValidationStatus.FAILED,
                duration_ms=duration_ms,
                output=f"Found {len(errors)} architectural issues (fallback check)",
                errors=errors,
                warnings=warnings,
                metadata={"fallback_mode": True}
            )

        return StageResult(
            stage="architecture",
            status=ValidationStatus.PASSED,
            duration_ms=duration_ms,
            output="Architecture validation passed (fallback mode)",
            errors=[],
            warnings=warnings,
            metadata={"fallback_mode": True}
        )


async def validate(
    path: Path,
    project_type: str,
    worker_pool=None
) -> StageResult:
    """Module-level validation function."""
    validator = ArchitectureValidator(worker_pool=worker_pool)
    return await validator.validate(path, project_type)
