# =============================================================================
# CLOPUS v3 Syntax Validator
# =============================================================================
"""
Basic syntax checking for various languages.
"""

from pathlib import Path
from typing import Dict, List

from .base import BaseValidator
from ..pipeline import StageResult, ValidationStage, ValidationStatus


class SyntaxValidator(BaseValidator):
    """Validate syntax for various languages."""

    stage = ValidationStage.SYNTAX

    # File extension to syntax checker mapping
    CHECKERS: Dict[str, List[str]] = {
        ".py": ["python", "-m", "py_compile"],
        ".js": ["node", "--check"],
        ".ts": ["npx", "tsc", "--noEmit", "--skipLibCheck"],
        ".tsx": ["npx", "tsc", "--noEmit", "--skipLibCheck", "--jsx", "react"],
        ".json": ["python", "-m", "json.tool"],
        ".yaml": ["python", "-c", "import yaml; yaml.safe_load(open('{}'))"],
        ".yml": ["python", "-c", "import yaml; yaml.safe_load(open('{}'))"],
    }

    async def validate(self, path: Path, project_type: str) -> StageResult:
        """Check syntax of all applicable files."""
        errors = []
        warnings = []
        files_checked = 0

        # Get all source files
        for ext, checker in self.CHECKERS.items():
            for file in path.rglob(f"*{ext}"):
                # Skip node_modules, __pycache__, etc.
                if any(
                    skip in str(file)
                    for skip in ["node_modules", "__pycache__", ".git", "dist", "build"]
                ):
                    continue

                files_checked += 1

                # Build command
                if "{}" in str(checker):
                    cmd = [c.replace("{}", str(file)) for c in checker]
                else:
                    cmd = checker + [str(file)]

                returncode, stdout, stderr = await self.run_command(cmd, cwd=path)

                if returncode != 0:
                    error_msg = f"{file.name}: {stderr or stdout}"
                    errors.append(error_msg[:200])

        status = ValidationStatus.PASSED if not errors else ValidationStatus.FAILED

        return StageResult(
            stage=self.stage,
            status=status,
            output=f"Checked {files_checked} files",
            errors=errors,
            warnings=warnings,
            metadata={"files_checked": files_checked}
        )

    def is_applicable(self, path: Path, project_type: str) -> bool:
        """Syntax check is always applicable."""
        return True
