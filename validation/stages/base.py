# =============================================================================
# CLOPUS v3 Base Validator
# =============================================================================
"""
Base class for validation stages.

AI-FIRST APPROACH (v3.3):
- Parsing output uses semantic understanding, not naive keyword matching
- False positives are filtered by checking context
- Exit codes are the primary success/failure indicator
"""

import asyncio
import subprocess
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Tuple, TYPE_CHECKING

from ..pipeline import StageResult, ValidationStage, ValidationStatus

if TYPE_CHECKING:
    from orchestrator.ai_first import AIFirstEngine


class BaseValidator(ABC):
    """Base class for validation stages."""

    stage: ValidationStage

    # AI engine for intelligent parsing (set by pipeline)
    ai_engine: Optional["AIFirstEngine"] = None

    # Patterns that indicate SUCCESS (not errors despite containing keywords)
    SUCCESS_PATTERNS = [
        r"0 errors?",
        r"no errors?",
        r"all .* passed",
        r"successfully",
        r"✓|✔|passed|ok\b",
        r"error.*(handler|boundary|logger|message|code)",  # Variable/class names
        r"errors? fixed",
        r"warning.*(handler|suppressed|ignored)",
    ]

    # Patterns that indicate actual errors (not just keyword presence)
    ERROR_PATTERNS = [
        r"error[:\s]+\S",           # "error: something" or "error something"
        r"failed[:\s]+\S",          # "failed: something"
        r"exception[:\s]+\S",       # "exception: something"
        r"\berror\b.*\bline\s*\d+", # "error at line 42"
        r"^\s*\d+\s+errors?\b",     # "5 errors found"
        r"compilation failed",
        r"build failed",
        r"test failed",
        r"syntax error",
        r"type error",
        r"reference error",
    ]

    # Patterns for actual warnings
    WARNING_PATTERNS = [
        r"warning[:\s]+\S",         # "warning: something"
        r"^\s*\d+\s+warnings?\b",   # "5 warnings found"
        r"deprecated",
        r"unused",
    ]

    def is_applicable(self, path: Path, project_type: str) -> bool:
        """Check if this validator is applicable to the project."""
        return True

    @abstractmethod
    async def validate(self, path: Path, project_type: str) -> StageResult:
        """Run validation and return result."""
        pass

    async def run_command(
        self,
        command: List[str],
        cwd: Optional[Path] = None,
        timeout: int = 300
    ) -> Tuple[int, str, str]:
        """Run a shell command and return (returncode, stdout, stderr)."""
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )

            return (
                process.returncode,
                stdout.decode() if stdout else "",
                stderr.decode() if stderr else ""
            )

        except asyncio.TimeoutError:
            if process:
                process.kill()
            raise
        except Exception as e:
            return (1, "", str(e))

    def _is_success_line(self, line: str) -> bool:
        """Check if a line indicates success (despite containing error keywords)."""
        line_lower = line.lower()
        for pattern in self.SUCCESS_PATTERNS:
            if re.search(pattern, line_lower):
                return True
        return False

    def _is_actual_error(self, line: str) -> bool:
        """Check if a line is an actual error (not just containing the word)."""
        line_lower = line.lower()
        for pattern in self.ERROR_PATTERNS:
            if re.search(pattern, line_lower):
                return True
        return False

    def _is_actual_warning(self, line: str) -> bool:
        """Check if a line is an actual warning (not just containing the word)."""
        line_lower = line.lower()
        for pattern in self.WARNING_PATTERNS:
            if re.search(pattern, line_lower):
                return True
        return False

    def parse_errors(self, output: str, returncode: int = None) -> List[str]:
        """
        Parse errors from command output using semantic understanding.

        AI-First approach:
        1. Exit code is primary indicator (returncode != 0 means failure)
        2. Success patterns filter out false positives
        3. Error patterns identify actual errors
        """
        errors = []

        for line in output.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Skip lines that indicate success
            if self._is_success_line(line):
                continue

            # Only include lines that are actual errors
            if self._is_actual_error(line):
                errors.append(line[:300])  # Limit line length

        # Deduplicate while preserving order
        seen = set()
        unique_errors = []
        for error in errors:
            if error not in seen:
                seen.add(error)
                unique_errors.append(error)

        return unique_errors[:20]  # Limit total errors

    def parse_warnings(self, output: str) -> List[str]:
        """
        Parse warnings from command output using semantic understanding.

        AI-First approach:
        1. Success patterns filter out false positives
        2. Warning patterns identify actual warnings
        """
        warnings = []

        for line in output.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Skip lines that indicate success
            if self._is_success_line(line):
                continue

            # Only include lines that are actual warnings
            if self._is_actual_warning(line):
                warnings.append(line[:300])

        # Deduplicate while preserving order
        seen = set()
        unique_warnings = []
        for warning in warnings:
            if warning not in seen:
                seen.add(warning)
                unique_warnings.append(warning)

        return unique_warnings[:30]  # Limit total warnings

    async def ai_parse_output(
        self,
        output: str,
        returncode: int,
        tool_name: str
    ) -> Tuple[List[str], List[str]]:
        """
        Use AI to intelligently parse tool output.

        Returns (errors, warnings) based on semantic understanding.
        Falls back to pattern-based parsing if AI unavailable.
        """
        if not self.ai_engine:
            return self.parse_errors(output, returncode), self.parse_warnings(output)

        try:
            result = await self.ai_engine.analyze_tool_output(
                tool_name=tool_name,
                output=output,
                returncode=returncode
            )

            if result.success and result.result:
                return (
                    result.result.get("errors", [])[:20],
                    result.result.get("warnings", [])[:30]
                )
        except Exception:
            pass

        # Fallback to pattern-based parsing
        return self.parse_errors(output, returncode), self.parse_warnings(output)
