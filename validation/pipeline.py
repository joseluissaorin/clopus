# =============================================================================
# CLOPUS v3 Validation Pipeline
# =============================================================================
"""
Orchestrates the 8-stage validation pipeline.

NEW IN v3.2: AI-First Validation Evaluation
- Uses Claude intelligence for semantic project type detection
- Uses AI for intelligent validation result evaluation
- Falls back to keyword matching when AI unavailable
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum
import logging

if TYPE_CHECKING:
    from orchestrator.ai_first import AIFirstEngine

logger = logging.getLogger("clopus.validation")


class ValidationStage(str, Enum):
    SYNTAX = "syntax"
    LINT = "lint"
    BUILD = "build"
    UNIT_TESTS = "unit_tests"
    INTEGRATION_TESTS = "integration_tests"
    E2E_TESTS = "e2e_tests"
    SECURITY = "security"
    ARCHITECTURE = "architecture"  # NEW: Claude-powered architecture compliance
    REVIEW = "review"


class ValidationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


# Default per-stage timeouts (in seconds)
DEFAULT_STAGE_TIMEOUTS = {
    "syntax": 60,
    "lint": 120,
    "build": 300,
    "unit_tests": 300,
    "integration_tests": 600,
    "e2e_tests": 600,
    "security": 180,
    "architecture": 300,  # Claude-powered analysis takes time
    "review": 300
}


@dataclass
class StageResult:
    """Result of a single validation stage."""
    stage: ValidationStage
    status: ValidationStatus
    duration_ms: int = 0
    output: str = ""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Complete validation result."""
    passed: bool
    stages: List[StageResult]
    total_duration_ms: int
    started_at: datetime
    completed_at: datetime
    summary: str


class ValidationPipeline:
    """
    8-stage validation pipeline with configurable per-stage timeouts.

    NEW IN v3.2: AI-First Validation
    - Uses AI intelligence for semantic project type detection
    - Uses AI for intelligent result evaluation
    - Falls back to keyword matching when AI unavailable
    """

    def __init__(
        self,
        memory_client,
        config,
        worker_pool=None,
        stage_timeouts: Optional[Dict[str, int]] = None
    ):
        self.memory = memory_client
        self.config = config
        self.worker_pool = worker_pool
        self.enabled_stages = config.enabled_stages
        self.strict_mode = config.strict_mode
        self.allow_warnings = config.allow_warnings
        self.default_timeout = config.timeout_per_stage_s

        # AI-First Engine (set by orchestrator, NEW in v3.2)
        self.ai_engine: Optional["AIFirstEngine"] = None

        # Per-stage configurable timeouts
        self.stage_timeouts = {**DEFAULT_STAGE_TIMEOUTS}
        if stage_timeouts:
            self.stage_timeouts.update(stage_timeouts)

    def set_ai_engine(self, ai_engine: "AIFirstEngine") -> None:
        """Set the AI-first engine for intelligent validation."""
        self.ai_engine = ai_engine
        logger.info("AI-First Engine connected to validation pipeline")

        # Import stage handlers
        from .stages import (
            syntax, lint, build, unit_tests,
            integration_tests, e2e_tests, security, architecture, review
        )

        self.stage_handlers = {
            ValidationStage.SYNTAX: syntax.SyntaxValidator(),
            ValidationStage.LINT: lint.LintValidator(),
            ValidationStage.BUILD: build.BuildValidator(),
            ValidationStage.UNIT_TESTS: unit_tests.UnitTestValidator(),
            ValidationStage.INTEGRATION_TESTS: integration_tests.IntegrationTestValidator(),
            ValidationStage.E2E_TESTS: e2e_tests.E2ETestValidator(),
            ValidationStage.SECURITY: security.SecurityValidator(),
            ValidationStage.ARCHITECTURE: architecture.ArchitectureValidator(self.worker_pool),
            ValidationStage.REVIEW: review.ReviewValidator(self.worker_pool),
        }

    async def validate(
        self,
        project_path: str,
        task_id: Optional[str] = None,
        stages: Optional[List[ValidationStage]] = None
    ) -> ValidationResult:
        """Run validation pipeline on a project."""
        start_time = datetime.now()
        path = Path(project_path)

        if not path.exists():
            return ValidationResult(
                passed=False,
                stages=[],
                total_duration_ms=0,
                started_at=start_time,
                completed_at=datetime.now(),
                summary=f"Project path does not exist: {project_path}"
            )

        # Determine which stages to run
        stages_to_run = stages or [
            ValidationStage(s) for s in self.enabled_stages
        ]

        # Detect project type for stage configuration
        project_type = self._detect_project_type(path)
        logger.info(f"Validating {project_path} (type: {project_type})")

        results = []
        all_passed = True

        for stage in stages_to_run:
            if stage.value not in self.enabled_stages:
                results.append(StageResult(
                    stage=stage,
                    status=ValidationStatus.SKIPPED
                ))
                continue

            handler = self.stage_handlers.get(stage)
            if not handler:
                logger.warning(f"No handler for stage: {stage}")
                continue

            # Check if stage is applicable
            if not handler.is_applicable(path, project_type):
                results.append(StageResult(
                    stage=stage,
                    status=ValidationStatus.SKIPPED,
                    output=f"Stage not applicable for {project_type}"
                ))
                continue

            # Get per-stage timeout
            stage_timeout = self.stage_timeouts.get(stage.value, self.default_timeout)

            # Run stage with timeout
            try:
                logger.info(f"Running stage: {stage.value} (timeout: {stage_timeout}s)")
                stage_start = datetime.now()

                result = await asyncio.wait_for(
                    handler.validate(path, project_type),
                    timeout=stage_timeout
                )

                result.duration_ms = int(
                    (datetime.now() - stage_start).total_seconds() * 1000
                )
                results.append(result)

                # Check if stage passed
                if result.status == ValidationStatus.FAILED:
                    all_passed = False

                    # In strict mode, stop on first failure
                    if self.strict_mode:
                        logger.warning(f"Stage {stage.value} failed, stopping pipeline")
                        break

                # Check warnings in strict mode
                if not self.allow_warnings and result.warnings:
                    all_passed = False

                # Store result in memory
                if task_id:
                    # Handle both Enum and string values safely
                    stage_name = stage.value if hasattr(stage, 'value') else str(stage)
                    status_name = result.status.value if hasattr(result.status, 'value') else str(result.status)
                    await self.memory.short_term.log_activity(
                        source="validation",
                        action=f"stage_{stage_name}",
                        details={
                            "status": status_name,
                            "errors": len(result.errors),
                            "warnings": len(result.warnings)
                        },
                        task_id=task_id
                    )

            except asyncio.TimeoutError:
                logger.warning(f"Stage {stage.value} timed out after {stage_timeout}s")
                results.append(StageResult(
                    stage=stage,
                    status=ValidationStatus.TIMEOUT,
                    errors=[f"Stage timed out after {stage_timeout} seconds"],
                    output=f"Timeout after {stage_timeout}s. Consider increasing timeout or optimizing stage."
                ))

                # In non-strict mode, continue with remaining stages
                if self.strict_mode:
                    all_passed = False
                    break
                else:
                    # Log timeout but continue
                    logger.info(f"Continuing pipeline after {stage.value} timeout (non-strict mode)")
                    all_passed = False
                    continue

            except Exception as e:
                logger.error(f"Error in stage {stage.value}: {e}")
                results.append(StageResult(
                    stage=stage,
                    status=ValidationStatus.FAILED,
                    errors=[str(e)]
                ))
                all_passed = False

                if self.strict_mode:
                    break

        end_time = datetime.now()
        total_ms = int((end_time - start_time).total_seconds() * 1000)

        # Generate summary
        summary = self._generate_summary(results, all_passed)

        return ValidationResult(
            passed=all_passed,
            stages=results,
            total_duration_ms=total_ms,
            started_at=start_time,
            completed_at=end_time,
            summary=summary
        )

    async def _detect_project_type_async(self, path: Path) -> str:
        """
        Detect the type of project.

        NEW IN v3.2: AI-First approach
        Priority:
        1. AI-First Engine (semantic detection)
        2. File-based detection (deprecated fallback)
        """
        # Try AI-First Engine for semantic detection
        if self.ai_engine:
            try:
                # Gather file info
                existing_files = []
                for pattern in ["*.json", "*.toml", "*.py", "*.ts", "*.tsx", "*.js"]:
                    existing_files.extend([f.name for f in path.glob(pattern)][:20])

                result = await self.ai_engine.analyze_project_requirements(
                    objective="Detect project type for validation",
                    existing_files=existing_files,
                    context={"path": str(path)}
                )

                if result.success and result.result:
                    detected_type = result.result.get("project_type")
                    if detected_type:
                        logger.debug(f"AI-first detected project type: {detected_type}")
                        return detected_type

            except Exception as e:
                logger.debug(f"AI-first project type detection failed: {e}")

        # Fallback to file-based detection (deprecated)
        return self._file_detect_project_type(path)

    def _detect_project_type(self, path: Path) -> str:
        """Sync wrapper for project type detection."""
        # Try to run async version if event loop is available
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're in an async context, can't await directly
                # Fall back to sync version
                return self._file_detect_project_type(path)
            else:
                return loop.run_until_complete(self._detect_project_type_async(path))
        except RuntimeError:
            return self._file_detect_project_type(path)

    def _file_detect_project_type(self, path: Path) -> str:
        """DEPRECATED: File-based project type detection. Use AI-first instead."""
        # Check for common project files
        if (path / "package.json").exists():
            package = (path / "package.json").read_text()
            if "next" in package:
                return "nextjs"
            elif "expo" in package:
                return "expo"
            elif "react" in package:
                return "react"
            elif "vue" in package:
                return "vue"
            return "nodejs"

        if (path / "pyproject.toml").exists() or (path / "setup.py").exists():
            if (path / "manage.py").exists():
                return "django"
            return "python"

        if (path / "Cargo.toml").exists():
            return "rust"

        if (path / "go.mod").exists():
            return "go"

        if (path / "composer.json").exists():
            return "php"

        if (path / "Gemfile").exists():
            return "ruby"

        return "unknown"

    def _generate_summary(self, results: List[StageResult], passed: bool) -> str:
        """Generate human-readable summary."""
        lines = []
        status_emoji = "✓" if passed else "✗"
        lines.append(f"{status_emoji} Validation {'PASSED' if passed else 'FAILED'}")
        lines.append("")

        for result in results:
            # Handle both Enum and string values safely
            stage_name = result.stage.value if hasattr(result.stage, 'value') else str(result.stage)
            status_str = result.status.value if hasattr(result.status, 'value') else str(result.status)

            if status_str == "passed":
                lines.append(f"  ✓ {stage_name}: passed ({result.duration_ms}ms)")
            elif status_str == "failed":
                lines.append(f"  ✗ {stage_name}: FAILED")
                for error in result.errors[:3]:
                    lines.append(f"      - {error[:80]}")
            elif status_str == "timeout":
                lines.append(f"  ⏱ {stage_name}: TIMEOUT")
                for error in result.errors[:3]:
                    lines.append(f"      - {error[:80]}")
            elif status_str == "skipped":
                lines.append(f"  ○ {stage_name}: skipped")

            if result.warnings:
                lines.append(f"      ⚠ {len(result.warnings)} warning(s)")

        return "\n".join(lines)

    async def validate_file(
        self,
        file_path: str,
        stages: Optional[List[ValidationStage]] = None
    ) -> ValidationResult:
        """Validate a single file."""
        path = Path(file_path)
        project_path = path.parent

        # Run subset of stages for single file
        file_stages = stages or [
            ValidationStage.SYNTAX,
            ValidationStage.LINT
        ]

        return await self.validate(
            str(project_path),
            stages=file_stages
        )

    async def quick_check(self, project_path: str) -> Tuple[bool, str]:
        """Quick validation check (syntax + lint only)."""
        result = await self.validate(
            project_path,
            stages=[ValidationStage.SYNTAX, ValidationStage.LINT]
        )
        return result.passed, result.summary

    async def full_check(self, project_path: str) -> ValidationResult:
        """Full validation with all stages."""
        return await self.validate(project_path)
