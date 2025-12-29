# =============================================================================
# CLOPUS v3 Unit Test Validator
# =============================================================================
"""
Unit test execution for various project types.

AI-FIRST APPROACH (v3.3):
- Uses JSON output formats for structured test result parsing
- Exit codes are the primary success/failure indicator
- No naive keyword matching like "PASS" in output
"""

from pathlib import Path
import json
import re

from .base import BaseValidator
from ..pipeline import StageResult, ValidationStage, ValidationStatus


class UnitTestValidator(BaseValidator):
    """Run unit tests."""

    stage = ValidationStage.UNIT_TESTS

    async def validate(self, path: Path, project_type: str) -> StageResult:
        """Run unit tests based on project type."""
        if project_type in ("nodejs", "react", "react-typescript", "nextjs", "vue", "expo"):
            return await self._run_jest(path)
        elif project_type in ("python", "django"):
            return await self._run_pytest(path)
        elif project_type == "rust":
            return await self._run_cargo_test(path)
        elif project_type == "go":
            return await self._run_go_test(path)
        elif project_type == "html5":
            # HTML5 projects may not have unit tests configured
            return StageResult(
                stage=self.stage,
                status=ValidationStatus.SKIPPED,
                output="HTML5 project - unit tests skipped (E2E tests will verify)"
            )
        else:
            return StageResult(
                stage=self.stage,
                status=ValidationStatus.SKIPPED,
                output=f"No test runner for project type: {project_type}"
            )

    async def _run_jest(self, path: Path) -> StageResult:
        """
        Run Jest or Vitest tests with JSON output.

        AI-First: Uses JSON reporters for structured parsing.
        Exit code is the primary success indicator.
        """
        # Check if test is configured
        pkg_path = path / "package.json"
        if pkg_path.exists():
            pkg = json.loads(pkg_path.read_text())
            scripts = pkg.get("scripts", {})
            if "test" not in scripts and "test:run" not in scripts:
                return StageResult(
                    stage=self.stage,
                    status=ValidationStatus.SKIPPED,
                    output="No test script found in package.json"
                )

        # Detect if using Vitest
        is_vitest = self._detect_vitest(path, pkg_path)

        if is_vitest:
            # Use vitest with JSON reporter
            cmd = ["npx", "vitest", "run", "--reporter=json"]
        else:
            # Use Jest with JSON output
            cmd = ["npm", "test", "--", "--passWithNoTests", "--ci", "--json"]

        returncode, stdout, stderr = await self.run_command(
            cmd,
            cwd=path,
            timeout=300
        )

        # Try to parse JSON output
        try:
            # Find JSON in output (may have other text before/after)
            json_match = re.search(r'\{[\s\S]*"numTotalTests"[\s\S]*\}', stdout)
            if json_match:
                results = json.loads(json_match.group())

                num_passed = results.get("numPassedTests", 0)
                num_failed = results.get("numFailedTests", 0)
                num_total = results.get("numTotalTests", 0)

                if num_failed == 0 and returncode == 0:
                    return StageResult(
                        stage=self.stage,
                        status=ValidationStatus.PASSED,
                        output=f"All {num_passed} tests passed",
                        metadata={"tests_passed": num_passed, "tests_total": num_total}
                    )

                # Extract failure details
                errors = []
                for test_result in results.get("testResults", []):
                    for assertion in test_result.get("assertionResults", []):
                        if assertion.get("status") == "failed":
                            title = assertion.get("fullName", assertion.get("title", "Unknown test"))
                            failure_msgs = assertion.get("failureMessages", [])
                            msg = failure_msgs[0][:150] if failure_msgs else "Test failed"
                            errors.append(f"{title}: {msg}")

                return StageResult(
                    stage=self.stage,
                    status=ValidationStatus.FAILED,
                    output=f"{num_failed} of {num_total} tests failed",
                    errors=errors[:10]
                )

        except (json.JSONDecodeError, TypeError):
            pass

        # Fallback: use exit code as primary indicator
        output = stdout + stderr

        if returncode == 0:
            return StageResult(
                stage=self.stage,
                status=ValidationStatus.PASSED,
                output="Tests completed successfully"
            )

        # Parse errors using improved base class method
        errors = self.parse_errors(output, returncode)
        return StageResult(
            stage=self.stage,
            status=ValidationStatus.FAILED,
            output=output[:2000],
            errors=errors[:10]
        )

    def _detect_vitest(self, path: Path, pkg_path: Path) -> bool:
        """Detect if project uses Vitest."""
        if pkg_path.exists():
            try:
                pkg = json.loads(pkg_path.read_text())
                dev_deps = pkg.get("devDependencies", {})
                if "vitest" in dev_deps:
                    return True
            except json.JSONDecodeError:
                pass

        # Check for vitest config
        if (path / "vitest.config.ts").exists() or (path / "vitest.config.js").exists():
            return True

        # Check vite.config for vitest
        vite_config = path / "vite.config.ts"
        if vite_config.exists():
            try:
                content = vite_config.read_text()
                if "vitest" in content or "test:" in content:
                    return True
            except:
                pass

        return False

    async def _run_pytest(self, path: Path) -> StageResult:
        """
        Run pytest with JSON output.

        AI-First: Uses pytest-json-report for structured output.
        Exit code is the primary success indicator.
        """
        # Check if there are test files
        test_files = list(path.rglob("test_*.py")) + list(path.rglob("*_test.py"))
        if not test_files:
            return StageResult(
                stage=self.stage,
                status=ValidationStatus.SKIPPED,
                output="No test files found"
            )

        # Try with JSON report first
        json_report_path = path / ".pytest_report.json"
        returncode, stdout, stderr = await self.run_command(
            [
                "python", "-m", "pytest", "-v", "--tb=short",
                f"--json-report", f"--json-report-file={json_report_path}"
            ],
            cwd=path,
            timeout=300
        )

        # Try to parse JSON report
        if json_report_path.exists():
            try:
                report = json.loads(json_report_path.read_text())
                summary = report.get("summary", {})

                passed = summary.get("passed", 0)
                failed = summary.get("failed", 0)
                total = summary.get("total", 0)

                if failed == 0 and returncode == 0:
                    return StageResult(
                        stage=self.stage,
                        status=ValidationStatus.PASSED,
                        output=f"{passed} tests passed",
                        metadata={"tests_passed": passed, "tests_total": total}
                    )

                # Extract failure details
                errors = []
                for test in report.get("tests", []):
                    if test.get("outcome") == "failed":
                        nodeid = test.get("nodeid", "Unknown test")
                        longrepr = test.get("call", {}).get("longrepr", "")
                        if longrepr:
                            errors.append(f"{nodeid}: {longrepr[:150]}")
                        else:
                            errors.append(f"{nodeid}: Test failed")

                return StageResult(
                    stage=self.stage,
                    status=ValidationStatus.FAILED,
                    output=f"{failed} of {total} tests failed",
                    errors=errors[:10]
                )

            except (json.JSONDecodeError, TypeError):
                pass
            finally:
                # Clean up report file
                try:
                    json_report_path.unlink()
                except:
                    pass

        # Fallback: parse exit code and summary line
        output = stdout + stderr

        if returncode == 0:
            # Try to extract count from summary line
            match = re.search(r"(\d+) passed", output)
            passed = int(match.group(1)) if match else 0

            return StageResult(
                stage=self.stage,
                status=ValidationStatus.PASSED,
                output=f"{passed} tests passed",
                metadata={"tests_passed": passed}
            )

        # Parse errors using improved base class method
        errors = self.parse_errors(output, returncode)
        return StageResult(
            stage=self.stage,
            status=ValidationStatus.FAILED,
            output=output[:2000],
            errors=errors[:10]
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
