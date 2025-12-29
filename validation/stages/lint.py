# =============================================================================
# CLOPUS v3 Lint Validator
# =============================================================================
"""
Linting for various languages using appropriate tools.

AI-FIRST APPROACH (v3.3):
- Uses JSON output formats where available for structured parsing
- Exit codes are primary success/failure indicator
- No naive keyword matching - uses semantic patterns from base class
"""

import json
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
        all_passed = True

        if project_type in ("nodejs", "react", "react-typescript", "nextjs", "vue", "expo"):
            result = await self._run_eslint(path)
            errors.extend(result[0])
            warnings.extend(result[1])
            output_parts.append(result[2])
            if result[0]:  # Has errors
                all_passed = False

        if project_type in ("python", "django"):
            result = await self._run_ruff(path)
            errors.extend(result[0])
            warnings.extend(result[1])
            output_parts.append(result[2])
            if result[0]:
                all_passed = False

        if project_type == "go":
            result = await self._run_golint(path)
            errors.extend(result[0])
            warnings.extend(result[1])
            output_parts.append(result[2])
            if result[0]:
                all_passed = False

        if project_type == "rust":
            result = await self._run_clippy(path)
            errors.extend(result[0])
            warnings.extend(result[1])
            output_parts.append(result[2])
            if result[0]:
                all_passed = False

        # For HTML5 projects, skip linting (no linter typically configured)
        if project_type == "html5":
            return StageResult(
                stage=self.stage,
                status=ValidationStatus.PASSED,
                output="HTML5 project - no linting configured",
                errors=[],
                warnings=[]
            )

        status = ValidationStatus.PASSED if all_passed else ValidationStatus.FAILED

        return StageResult(
            stage=self.stage,
            status=status,
            output="\n".join(output_parts),
            errors=errors[:20],
            warnings=warnings[:30]
        )

    async def _run_eslint(self, path: Path) -> Tuple[List[str], List[str], str]:
        """
        Run ESLint with JSON output for structured parsing.

        AI-First: Uses JSON format to avoid keyword matching issues.
        """
        # Use JSON output format for structured parsing
        if (path / "node_modules" / ".bin" / "eslint").exists():
            cmd = ["./node_modules/.bin/eslint", ".", "--ext", ".js,.jsx,.ts,.tsx", "--format", "json"]
        else:
            cmd = ["npx", "eslint", ".", "--ext", ".js,.jsx,.ts,.tsx", "--format", "json"]

        returncode, stdout, stderr = await self.run_command(cmd, cwd=path)

        errors = []
        warnings = []

        # Try to parse JSON output
        try:
            results = json.loads(stdout) if stdout.strip() else []
            for file_result in results:
                for msg in file_result.get("messages", []):
                    severity = msg.get("severity", 0)
                    file_path = file_result.get("filePath", "")
                    line = msg.get("line", 0)
                    message = msg.get("message", "")
                    rule_id = msg.get("ruleId", "")

                    formatted = f"{file_path}:{line}: {message} ({rule_id})"

                    if severity == 2:  # Error
                        errors.append(formatted[:200])
                    elif severity == 1:  # Warning
                        warnings.append(formatted[:200])

        except json.JSONDecodeError:
            # Fallback: if not JSON, use exit code as primary indicator
            if returncode != 0:
                # Use improved pattern-based parsing from base class
                errors = self.parse_errors(stdout + stderr, returncode)
                warnings = self.parse_warnings(stdout + stderr)

        return errors[:20], warnings[:30], f"ESLint: {len(errors)} errors, {len(warnings)} warnings"

    async def _run_ruff(self, path: Path) -> Tuple[List[str], List[str], str]:
        """
        Run Ruff with JSON output for structured parsing.

        AI-First: Uses JSON format for precise error extraction.
        """
        cmd = ["ruff", "check", str(path), "--output-format", "json"]

        returncode, stdout, stderr = await self.run_command(cmd, cwd=path)

        errors = []
        warnings = []

        try:
            results = json.loads(stdout) if stdout.strip() else []
            for issue in results:
                file_path = issue.get("filename", "")
                line = issue.get("location", {}).get("row", 0)
                code = issue.get("code", "")
                message = issue.get("message", "")

                formatted = f"{file_path}:{line}: [{code}] {message}"

                # Ruff codes: E=error, W=warning, F=pyflakes, etc.
                if code.startswith(("E9", "F")):  # Syntax errors, undefined names
                    errors.append(formatted[:200])
                else:
                    warnings.append(formatted[:200])

        except json.JSONDecodeError:
            # Fallback to exit code based detection
            if returncode != 0:
                errors = self.parse_errors(stdout + stderr, returncode)
                warnings = self.parse_warnings(stdout + stderr)

        return errors[:20], warnings[:30], f"Ruff: {len(errors)} errors, {len(warnings)} warnings"

    async def _run_golint(self, path: Path) -> Tuple[List[str], List[str], str]:
        """
        Run Go linters with JSON output.

        AI-First: Uses structured output from golangci-lint.
        """
        cmd = ["golangci-lint", "run", "--out-format", "json"]

        returncode, stdout, stderr = await self.run_command(cmd, cwd=path)

        errors = []
        warnings = []

        try:
            result = json.loads(stdout) if stdout.strip() else {}
            issues = result.get("Issues", [])

            for issue in issues:
                file_path = issue.get("Pos", {}).get("Filename", "")
                line = issue.get("Pos", {}).get("Line", 0)
                message = issue.get("Text", "")
                severity = issue.get("Severity", "").lower()

                formatted = f"{file_path}:{line}: {message}"

                if severity == "error":
                    errors.append(formatted[:200])
                else:
                    warnings.append(formatted[:200])

        except json.JSONDecodeError:
            if returncode != 0:
                errors = self.parse_errors(stdout + stderr, returncode)
                warnings = self.parse_warnings(stdout + stderr)

        return errors[:20], warnings[:30], f"Go lint: {len(errors)} errors, {len(warnings)} warnings"

    async def _run_clippy(self, path: Path) -> Tuple[List[str], List[str], str]:
        """
        Run Rust Clippy with JSON output.

        AI-First: Uses cargo's JSON message format.
        """
        cmd = ["cargo", "clippy", "--message-format", "json", "--", "-D", "warnings"]

        returncode, stdout, stderr = await self.run_command(cmd, cwd=path)

        errors = []
        warnings = []

        # Parse JSON lines (cargo outputs one JSON object per line)
        for line in stdout.split("\n"):
            if not line.strip():
                continue
            try:
                msg = json.loads(line)
                if msg.get("reason") == "compiler-message":
                    compiler_msg = msg.get("message", {})
                    level = compiler_msg.get("level", "")
                    message = compiler_msg.get("message", "")
                    spans = compiler_msg.get("spans", [])

                    location = ""
                    if spans:
                        span = spans[0]
                        location = f"{span.get('file_name', '')}:{span.get('line_start', '')}"

                    formatted = f"{location}: {message}" if location else message

                    if level == "error":
                        errors.append(formatted[:200])
                    elif level == "warning":
                        warnings.append(formatted[:200])

            except json.JSONDecodeError:
                continue

        # If no JSON parsed but exit code indicates failure
        if not errors and returncode != 0:
            errors = self.parse_errors(stderr, returncode)
            warnings = self.parse_warnings(stderr)

        return errors[:20], warnings[:30], f"Clippy: {len(errors)} errors, {len(warnings)} warnings"

    def is_applicable(self, path: Path, project_type: str) -> bool:
        """Check if linting is applicable."""
        return project_type not in ("unknown", "html5")
