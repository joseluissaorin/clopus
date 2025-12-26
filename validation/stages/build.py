# =============================================================================
# CLOPUS v3 Build Validator
# =============================================================================
"""
Build/compile validation for various project types.
"""

from pathlib import Path

from .base import BaseValidator
from ..pipeline import StageResult, ValidationStage, ValidationStatus


class BuildValidator(BaseValidator):
    """Validate that project builds successfully."""

    stage = ValidationStage.BUILD

    async def validate(self, path: Path, project_type: str) -> StageResult:
        """Run build command based on project type."""
        if project_type in ("nodejs", "react", "nextjs", "vue"):
            return await self._build_npm(path)
        elif project_type == "expo":
            return await self._build_expo(path)
        elif project_type in ("python", "django"):
            return await self._build_python(path)
        elif project_type == "rust":
            return await self._build_rust(path)
        elif project_type == "go":
            return await self._build_go(path)
        else:
            return StageResult(
                stage=self.stage,
                status=ValidationStatus.SKIPPED,
                output=f"No build command for project type: {project_type}"
            )

    async def _build_npm(self, path: Path) -> StageResult:
        """Build Node.js project."""
        # First install dependencies if needed
        if not (path / "node_modules").exists():
            returncode, stdout, stderr = await self.run_command(
                ["npm", "install"],
                cwd=path,
                timeout=300
            )
            if returncode != 0:
                return StageResult(
                    stage=self.stage,
                    status=ValidationStatus.FAILED,
                    output=stdout,
                    errors=[f"npm install failed: {stderr}"]
                )

        # Run build
        returncode, stdout, stderr = await self.run_command(
            ["npm", "run", "build"],
            cwd=path,
            timeout=300
        )

        if returncode != 0:
            return StageResult(
                stage=self.stage,
                status=ValidationStatus.FAILED,
                output=stdout + stderr,
                errors=self.parse_errors(stdout + stderr)
            )

        return StageResult(
            stage=self.stage,
            status=ValidationStatus.PASSED,
            output="Build successful",
            warnings=self.parse_warnings(stdout + stderr)
        )

    async def _build_expo(self, path: Path) -> StageResult:
        """Build Expo project."""
        # Install dependencies
        if not (path / "node_modules").exists():
            returncode, stdout, stderr = await self.run_command(
                ["npm", "install"],
                cwd=path,
                timeout=300
            )
            if returncode != 0:
                return StageResult(
                    stage=self.stage,
                    status=ValidationStatus.FAILED,
                    errors=[f"npm install failed: {stderr}"]
                )

        # Run expo doctor to check configuration
        returncode, stdout, stderr = await self.run_command(
            ["npx", "expo-doctor"],
            cwd=path
        )

        errors = self.parse_errors(stdout + stderr)
        warnings = self.parse_warnings(stdout + stderr)

        if returncode != 0 and errors:
            return StageResult(
                stage=self.stage,
                status=ValidationStatus.FAILED,
                output=stdout,
                errors=errors,
                warnings=warnings
            )

        return StageResult(
            stage=self.stage,
            status=ValidationStatus.PASSED,
            output="Expo project validated",
            warnings=warnings
        )

    async def _build_python(self, path: Path) -> StageResult:
        """Validate Python project."""
        # Check if there's a setup.py or pyproject.toml
        if (path / "pyproject.toml").exists():
            # Try building with pip
            returncode, stdout, stderr = await self.run_command(
                ["pip", "install", "-e", ".", "--dry-run"],
                cwd=path
            )
        elif (path / "setup.py").exists():
            returncode, stdout, stderr = await self.run_command(
                ["python", "setup.py", "check"],
                cwd=path
            )
        else:
            # Just check imports
            returncode, stdout, stderr = await self.run_command(
                ["python", "-m", "compileall", str(path)],
                cwd=path
            )

        if returncode != 0:
            return StageResult(
                stage=self.stage,
                status=ValidationStatus.FAILED,
                output=stdout + stderr,
                errors=self.parse_errors(stdout + stderr)
            )

        return StageResult(
            stage=self.stage,
            status=ValidationStatus.PASSED,
            output="Python project validated"
        )

    async def _build_rust(self, path: Path) -> StageResult:
        """Build Rust project."""
        returncode, stdout, stderr = await self.run_command(
            ["cargo", "build", "--release"],
            cwd=path,
            timeout=600
        )

        if returncode != 0:
            return StageResult(
                stage=self.stage,
                status=ValidationStatus.FAILED,
                output=stderr,
                errors=self.parse_errors(stderr)
            )

        return StageResult(
            stage=self.stage,
            status=ValidationStatus.PASSED,
            output="Cargo build successful"
        )

    async def _build_go(self, path: Path) -> StageResult:
        """Build Go project."""
        returncode, stdout, stderr = await self.run_command(
            ["go", "build", "./..."],
            cwd=path
        )

        if returncode != 0:
            return StageResult(
                stage=self.stage,
                status=ValidationStatus.FAILED,
                output=stderr,
                errors=self.parse_errors(stderr)
            )

        return StageResult(
            stage=self.stage,
            status=ValidationStatus.PASSED,
            output="Go build successful"
        )

    def is_applicable(self, path: Path, project_type: str) -> bool:
        """Check if build is applicable."""
        # Check for build scripts/files
        if (path / "package.json").exists():
            import json
            try:
                pkg = json.loads((path / "package.json").read_text())
                return "build" in pkg.get("scripts", {})
            except:
                pass

        return project_type in ("rust", "go", "python", "django")
