# =============================================================================
# CLOPUS v3 Lint Validator
# =============================================================================
"""
Linting for various languages using appropriate tools.
"""

from pathlib import Path
from typing import List, Tuple

from .base import BaseValidator
from ..pipeline import StageResult, ValidationStage, ValidationStatus


class LintValidator(BaseValidator):
    """Validate code style and quality using linters."""

    stage = ValidationStage.LINT

    async def validate(self, path: Path, project_type: str) -> StageResult:
        """Run appropriate linters based on project type."""
        errors = []
        warnings = []
        output_parts = []

        if project_type in ("nodejs", "react", "nextjs", "vue", "expo"):
            result = await self._run_eslint(path)
            errors.extend(result[0])
            warnings.extend(result[1])
            output_parts.append(result[2])

        if project_type in ("python", "django"):
            result = await self._run_pylint(path)
            errors.extend(result[0])
            warnings.extend(result[1])
            output_parts.append(result[2])

            result = await self._run_ruff(path)
            errors.extend(result[0])
            warnings.extend(result[1])
            output_parts.append(result[2])

        if project_type == "go":
            result = await self._run_golint(path)
            errors.extend(result[0])
            warnings.extend(result[1])
            output_parts.append(result[2])

        if project_type == "rust":
            result = await self._run_clippy(path)
            errors.extend(result[0])
            warnings.extend(result[1])
            output_parts.append(result[2])

        status = ValidationStatus.PASSED if not errors else ValidationStatus.FAILED

        return StageResult(
            stage=self.stage,
            status=status,
            output="\n".join(output_parts),
            errors=errors,
            warnings=warnings
        )

    async def _run_eslint(self, path: Path) -> Tuple[List[str], List[str], str]:
        """Run ESLint."""
        # Check if ESLint is available
        if not (path / "node_modules" / ".bin" / "eslint").exists():
            # Try npx
            cmd = ["npx", "eslint", ".", "--ext", ".js,.jsx,.ts,.tsx", "--format", "compact"]
        else:
            cmd = ["./node_modules/.bin/eslint", ".", "--ext", ".js,.jsx,.ts,.tsx", "--format", "compact"]

        returncode, stdout, stderr = await self.run_command(cmd, cwd=path)

        errors = []
        warnings = []

        for line in (stdout + stderr).split("\n"):
            if "error" in line.lower():
                errors.append(line[:200])
            elif "warning" in line.lower():
                warnings.append(line[:200])

        return errors, warnings, f"ESLint: {len(errors)} errors, {len(warnings)} warnings"

    async def _run_pylint(self, path: Path) -> Tuple[List[str], List[str], str]:
        """Run Pylint."""
        cmd = ["python", "-m", "pylint", str(path), "--output-format=text", "--score=no"]

        returncode, stdout, stderr = await self.run_command(cmd, cwd=path)

        errors = []
        warnings = []

        for line in stdout.split("\n"):
            if ": E" in line or ": F" in line:  # Error or Fatal
                errors.append(line[:200])
            elif ": W" in line or ": C" in line:  # Warning or Convention
                warnings.append(line[:200])

        return errors[:20], warnings[:20], f"Pylint: {len(errors)} errors, {len(warnings)} warnings"

    async def _run_ruff(self, path: Path) -> Tuple[List[str], List[str], str]:
        """Run Ruff (fast Python linter)."""
        cmd = ["ruff", "check", str(path)]

        returncode, stdout, stderr = await self.run_command(cmd, cwd=path)

        errors = self.parse_errors(stdout)
        warnings = self.parse_warnings(stdout)

        return errors[:20], warnings[:20], f"Ruff: {len(errors)} issues"

    async def _run_golint(self, path: Path) -> Tuple[List[str], List[str], str]:
        """Run Go linters."""
        cmd = ["golangci-lint", "run"]

        returncode, stdout, stderr = await self.run_command(cmd, cwd=path)

        errors = self.parse_errors(stdout + stderr)
        warnings = self.parse_warnings(stdout + stderr)

        return errors[:20], warnings[:20], f"Go lint: {len(errors)} issues"

    async def _run_clippy(self, path: Path) -> Tuple[List[str], List[str], str]:
        """Run Rust Clippy."""
        cmd = ["cargo", "clippy", "--", "-D", "warnings"]

        returncode, stdout, stderr = await self.run_command(cmd, cwd=path)

        errors = self.parse_errors(stderr)
        warnings = self.parse_warnings(stderr)

        return errors[:20], warnings[:20], f"Clippy: {len(errors)} errors, {len(warnings)} warnings"

    def is_applicable(self, path: Path, project_type: str) -> bool:
        """Check if linting is applicable."""
        return project_type != "unknown"
