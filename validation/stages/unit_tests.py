# =============================================================================
# CLOPUS v3 Unit Test Validator
# =============================================================================
"""
Unit test execution for various project types.
"""

from pathlib import Path
import json

from .base import BaseValidator
from ..pipeline import StageResult, ValidationStage, ValidationStatus


class UnitTestValidator(BaseValidator):
    """Run unit tests."""

    stage = ValidationStage.UNIT_TESTS

    async def validate(self, path: Path, project_type: str) -> StageResult:
        """Run unit tests based on project type."""
        if project_type in ("nodejs", "react", "nextjs", "vue", "expo"):
            return await self._run_jest(path)
        elif project_type in ("python", "django"):
            return await self._run_pytest(path)
        elif project_type == "rust":
            return await self._run_cargo_test(path)
        elif project_type == "go":
            return await self._run_go_test(path)
        else:
            return StageResult(
                stage=self.stage,
                status=ValidationStatus.SKIPPED,
                output=f"No test runner for project type: {project_type}"
            )

    async def _run_jest(self, path: Path) -> StageResult:
        """Run Jest tests."""
        # Check if Jest is configured
        pkg_path = path / "package.json"
        if pkg_path.exists():
            pkg = json.loads(pkg_path.read_text())
            scripts = pkg.get("scripts", {})
            if "test" not in scripts:
                return StageResult(
                    stage=self.stage,
                    status=ValidationStatus.SKIPPED,
                    output="No test script found in package.json"
                )

        returncode, stdout, stderr = await self.run_command(
            ["npm", "test", "--", "--passWithNoTests", "--ci"],
            cwd=path,
            timeout=300
        )

        output = stdout + stderr

        # Parse Jest output
        if "PASS" in output and "FAIL" not in output:
            # Extract test counts
            tests_passed = output.count("PASS")
            return StageResult(
                stage=self.stage,
                status=ValidationStatus.PASSED,
                output=f"All tests passed ({tests_passed} suites)",
                metadata={"suites_passed": tests_passed}
            )

        if "FAIL" in output or returncode != 0:
            errors = []
            for line in output.split("\n"):
                if "FAIL" in line or "Error" in line:
                    errors.append(line[:200])
            return StageResult(
                stage=self.stage,
                status=ValidationStatus.FAILED,
                output=output,
                errors=errors[:10]
            )

        return StageResult(
            stage=self.stage,
            status=ValidationStatus.PASSED,
            output="Tests completed"
        )

    async def _run_pytest(self, path: Path) -> StageResult:
        """Run pytest."""
        # Check if there are test files
        test_files = list(path.rglob("test_*.py")) + list(path.rglob("*_test.py"))
        if not test_files:
            return StageResult(
                stage=self.stage,
                status=ValidationStatus.SKIPPED,
                output="No test files found"
            )

        returncode, stdout, stderr = await self.run_command(
            ["python", "-m", "pytest", "-v", "--tb=short"],
            cwd=path,
            timeout=300
        )

        output = stdout + stderr

        # Parse pytest output
        if "passed" in output and "failed" not in output.lower():
            # Extract counts
            import re
            match = re.search(r"(\d+) passed", output)
            passed = int(match.group(1)) if match else 0

            return StageResult(
                stage=self.stage,
                status=ValidationStatus.PASSED,
                output=f"{passed} tests passed",
                metadata={"tests_passed": passed}
            )

        if "failed" in output.lower() or returncode != 0:
            errors = []
            for line in output.split("\n"):
                if "FAILED" in line or "ERROR" in line:
                    errors.append(line[:200])
            return StageResult(
                stage=self.stage,
                status=ValidationStatus.FAILED,
                output=output,
                errors=errors[:10]
            )

        return StageResult(
            stage=self.stage,
            status=ValidationStatus.PASSED,
            output="Tests completed"
        )

    async def _run_cargo_test(self, path: Path) -> StageResult:
        """Run Rust tests."""
        returncode, stdout, stderr = await self.run_command(
            ["cargo", "test"],
            cwd=path,
            timeout=300
        )

        output = stdout + stderr

        if returncode == 0:
            return StageResult(
                stage=self.stage,
                status=ValidationStatus.PASSED,
                output="All tests passed"
            )

        errors = self.parse_errors(output)
        return StageResult(
            stage=self.stage,
            status=ValidationStatus.FAILED,
            output=output,
            errors=errors
        )

    async def _run_go_test(self, path: Path) -> StageResult:
        """Run Go tests."""
        returncode, stdout, stderr = await self.run_command(
            ["go", "test", "./...", "-v"],
            cwd=path,
            timeout=300
        )

        output = stdout + stderr

        if returncode == 0:
            return StageResult(
                stage=self.stage,
                status=ValidationStatus.PASSED,
                output="All tests passed"
            )

        errors = self.parse_errors(output)
        return StageResult(
            stage=self.stage,
            status=ValidationStatus.FAILED,
            output=output,
            errors=errors
        )

    def is_applicable(self, path: Path, project_type: str) -> bool:
        """Check if unit tests are applicable."""
        # Check for test directories or files
        test_patterns = [
            "test_*.py", "*_test.py", "*.test.js", "*.spec.js",
            "*.test.ts", "*.spec.ts", "*_test.go"
        ]

        for pattern in test_patterns:
            if list(path.rglob(pattern)):
                return True

        # Check for test directory
        if (path / "tests").exists() or (path / "test").exists():
            return True

        # Check for test script in package.json
        if (path / "package.json").exists():
            try:
                pkg = json.loads((path / "package.json").read_text())
                return "test" in pkg.get("scripts", {})
            except:
                pass

        return False
