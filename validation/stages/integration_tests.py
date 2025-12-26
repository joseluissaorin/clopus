# =============================================================================
# CLOPUS v3 Integration Test Validator
# =============================================================================
"""
Integration test execution.
"""

from pathlib import Path
import json

from .base import BaseValidator
from ..pipeline import StageResult, ValidationStage, ValidationStatus


class IntegrationTestValidator(BaseValidator):
    """Run integration tests."""

    stage = ValidationStage.INTEGRATION_TESTS

    async def validate(self, path: Path, project_type: str) -> StageResult:
        """Run integration tests."""
        # Look for integration test scripts
        if (path / "package.json").exists():
            pkg = json.loads((path / "package.json").read_text())
            scripts = pkg.get("scripts", {})

            if "test:integration" in scripts:
                return await self._run_npm_script(path, "test:integration")
            elif "test:int" in scripts:
                return await self._run_npm_script(path, "test:int")

        # Check for Python integration tests
        if project_type in ("python", "django"):
            int_tests = list(path.rglob("**/integration/**/test_*.py"))
            if int_tests:
                return await self._run_pytest_integration(path)

        # Check for integration test directory
        int_dir = path / "tests" / "integration"
        if int_dir.exists():
            if project_type in ("nodejs", "react", "nextjs"):
                return await self._run_jest_dir(path, int_dir)
            elif project_type in ("python", "django"):
                return await self._run_pytest_dir(path, int_dir)

        return StageResult(
            stage=self.stage,
            status=ValidationStatus.SKIPPED,
            output="No integration tests found"
        )

    async def _run_npm_script(self, path: Path, script: str) -> StageResult:
        """Run npm script for integration tests."""
        returncode, stdout, stderr = await self.run_command(
            ["npm", "run", script],
            cwd=path,
            timeout=600
        )

        output = stdout + stderr

        if returncode == 0:
            return StageResult(
                stage=self.stage,
                status=ValidationStatus.PASSED,
                output="Integration tests passed"
            )

        return StageResult(
            stage=self.stage,
            status=ValidationStatus.FAILED,
            output=output,
            errors=self.parse_errors(output)
        )

    async def _run_jest_dir(self, path: Path, test_dir: Path) -> StageResult:
        """Run Jest on specific directory."""
        returncode, stdout, stderr = await self.run_command(
            ["npx", "jest", str(test_dir), "--ci"],
            cwd=path,
            timeout=600
        )

        output = stdout + stderr

        if returncode == 0:
            return StageResult(
                stage=self.stage,
                status=ValidationStatus.PASSED,
                output="Integration tests passed"
            )

        return StageResult(
            stage=self.stage,
            status=ValidationStatus.FAILED,
            output=output,
            errors=self.parse_errors(output)
        )

    async def _run_pytest_integration(self, path: Path) -> StageResult:
        """Run pytest with integration marker."""
        returncode, stdout, stderr = await self.run_command(
            ["python", "-m", "pytest", "-v", "-m", "integration"],
            cwd=path,
            timeout=600
        )

        output = stdout + stderr

        if returncode == 0:
            return StageResult(
                stage=self.stage,
                status=ValidationStatus.PASSED,
                output="Integration tests passed"
            )

        return StageResult(
            stage=self.stage,
            status=ValidationStatus.FAILED,
            output=output,
            errors=self.parse_errors(output)
        )

    async def _run_pytest_dir(self, path: Path, test_dir: Path) -> StageResult:
        """Run pytest on specific directory."""
        returncode, stdout, stderr = await self.run_command(
            ["python", "-m", "pytest", str(test_dir), "-v"],
            cwd=path,
            timeout=600
        )

        output = stdout + stderr

        if returncode == 0:
            return StageResult(
                stage=self.stage,
                status=ValidationStatus.PASSED,
                output="Integration tests passed"
            )

        return StageResult(
            stage=self.stage,
            status=ValidationStatus.FAILED,
            output=output,
            errors=self.parse_errors(output)
        )

    def is_applicable(self, path: Path, project_type: str) -> bool:
        """Check if integration tests are applicable."""
        # Check for integration test directory
        if (path / "tests" / "integration").exists():
            return True

        # Check for integration test script
        if (path / "package.json").exists():
            try:
                pkg = json.loads((path / "package.json").read_text())
                scripts = pkg.get("scripts", {})
                return any(
                    "integration" in k.lower()
                    for k in scripts.keys()
                )
            except:
                pass

        return False
