# =============================================================================
# CLOPUS v3 Base Validator
# =============================================================================
"""
Base class for validation stages.
"""

import asyncio
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Tuple

from ..pipeline import StageResult, ValidationStage, ValidationStatus


class BaseValidator(ABC):
    """Base class for validation stages."""

    stage: ValidationStage

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

    def parse_errors(self, output: str) -> List[str]:
        """Parse errors from command output."""
        errors = []
        for line in output.split("\n"):
            line = line.strip()
            if line and any(
                indicator in line.lower()
                for indicator in ["error", "failed", "exception"]
            ):
                errors.append(line)
        return errors

    def parse_warnings(self, output: str) -> List[str]:
        """Parse warnings from command output."""
        warnings = []
        for line in output.split("\n"):
            line = line.strip()
            if line and "warning" in line.lower():
                warnings.append(line)
        return warnings
