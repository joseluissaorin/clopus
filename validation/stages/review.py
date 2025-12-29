# =============================================================================
# CLOPUS v3 Code Review Validator
# =============================================================================
"""
Code review stage using the reviewer worker.
"""

from pathlib import Path
from typing import Optional
import json

from .base import BaseValidator
from ..pipeline import StageResult, ValidationStage, ValidationStatus


class ReviewValidator(BaseValidator):
    """Run code review using reviewer worker."""

    stage = ValidationStage.REVIEW

    def __init__(self, worker_pool=None):
        self.worker_pool = worker_pool

    async def validate(self, path: Path, project_type: str) -> StageResult:
        """Run code review."""
        if not self.worker_pool:
            return await self._static_review(path, project_type)

        # Get reviewer worker
        reviewer_id = self.worker_pool.get_worker_by_role("reviewer")

        if not reviewer_id:
            return await self._static_review(path, project_type)

        # Dispatch review task
        review_prompt = self._build_review_prompt(path, project_type)

        success = await self.worker_pool.dispatch_task(
            worker_id=reviewer_id,
            task_id=f"review_{path.name}",
            title="Code Review",
            description=review_prompt,
            cwd=str(path)
        )

        if not success:
            return await self._static_review(path, project_type)

        # Wait for result (with timeout)
        import asyncio
        for _ in range(60):  # 5 minute timeout
            results = await self.worker_pool.collect_results()
            if reviewer_id in results:
                result = results[reviewer_id]
                return self._parse_review_result(result)
            await asyncio.sleep(5)

        return StageResult(
            stage=self.stage,
            status=ValidationStatus.FAILED,
            errors=["Code review timed out"]
        )

    async def _static_review(self, path: Path, project_type: str) -> StageResult:
        """Run static code review checks."""
        warnings = []
        errors = []

        # Check for common issues
        checks = await self._run_static_checks(path, project_type)
        warnings.extend(checks)

        # Check code complexity
        complexity = await self._check_complexity(path, project_type)
        warnings.extend(complexity)

        # Check documentation
        docs = await self._check_documentation(path, project_type)
        warnings.extend(docs)

        return StageResult(
            stage=self.stage,
            status=ValidationStatus.PASSED if not errors else ValidationStatus.FAILED,
            output=f"Static review: {len(warnings)} suggestions",
            errors=errors,
            warnings=warnings
        )

    def _build_review_prompt(self, path: Path, project_type: str) -> str:
        """Build prompt for code review."""
        return f"""Review the code in this {project_type} project.

Check for:
1. Code quality and readability
2. Potential bugs or edge cases
3. Security issues
4. Performance concerns
5. Best practices violations
6. Missing error handling
7. Test coverage gaps

Provide a structured review with:
- CRITICAL: Issues that must be fixed
- WARNINGS: Issues that should be addressed
- SUGGESTIONS: Optional improvements

Be thorough but concise. Focus on actionable feedback."""

    def _parse_review_result(self, result: dict) -> StageResult:
        """Parse the review result from worker."""
        output = result.get("result", "")
        errors = []
        warnings = []

        # Parse output for actual issues, not just keyword matches
        lines = output.split("\n")
        in_critical_section = False
        in_warning_section = False

        for line in lines:
            line_stripped = line.strip()
            line_lower = line_stripped.lower()

            # Skip empty lines and code blocks
            if not line_stripped or line_stripped.startswith("```"):
                continue

            # Skip section headers - they contain keywords but aren't issues themselves
            if line_stripped.startswith("#") or line_stripped.startswith("##"):
                in_critical_section = "critical" in line_lower
                in_warning_section = "warning" in line_lower
                continue

            # Skip positive statements like "No critical issues" or "No errors found"
            if any(phrase in line_lower for phrase in [
                "no critical", "no error", "no issue", "no problem",
                "looks good", "well structured", "properly", "correctly",
                "passes", "compiles without error", "builds successfully"
            ]):
                continue

            # Skip code snippets (indented lines that look like code)
            if line_stripped.startswith(("throw ", "return ", "const ", "let ", "var ", "if ", "for ")):
                continue

            # Collect actual issues based on context
            if in_critical_section and line_stripped.startswith(("-", "*", "•")):
                # This is a bullet point in the CRITICAL section
                issue = line_stripped.lstrip("-*• ").strip()
                if issue and len(issue) > 5:  # Ignore very short items
                    errors.append(issue[:200])
            elif in_warning_section and line_stripped.startswith(("-", "*", "•")):
                # This is a bullet point in the WARNING section
                issue = line_stripped.lstrip("-*• ").strip()
                if issue and len(issue) > 5:
                    warnings.append(issue[:200])

        # Review passes if no actionable critical issues found
        status = ValidationStatus.FAILED if errors else ValidationStatus.PASSED

        return StageResult(
            stage=self.stage,
            status=status,
            output=output[:1000],
            errors=errors[:10],
            warnings=warnings[:20]
        )

    async def _run_static_checks(self, path: Path, project_type: str) -> list:
        """Run static review checks."""
        warnings = []

        # Check file sizes
        for file in path.rglob("*"):
            if file.is_file():
                if any(skip in str(file) for skip in ["node_modules", ".git", "dist"]):
                    continue
                try:
                    size = file.stat().st_size
                    if size > 500000:  # 500KB
                        warnings.append(f"{file.name}: Large file ({size // 1000}KB)")

                    # Check line count for source files
                    if file.suffix in [".py", ".js", ".ts", ".tsx"]:
                        lines = len(file.read_text().split("\n"))
                        if lines > 500:
                            warnings.append(f"{file.name}: Large file ({lines} lines)")
                except:
                    pass

        return warnings[:10]

    async def _check_complexity(self, path: Path, project_type: str) -> list:
        """Check code complexity."""
        warnings = []

        if project_type in ("python", "django"):
            # Could use radon for Python
            returncode, stdout, stderr = await self.run_command(
                ["python", "-m", "radon", "cc", str(path), "-a", "-s"],
                cwd=path
            )
            if "C" in stdout or "D" in stdout or "F" in stdout:
                warnings.append("High cyclomatic complexity detected")

        return warnings

    async def _check_documentation(self, path: Path, project_type: str) -> list:
        """Check for documentation."""
        warnings = []

        # Check for README
        readme_files = ["README.md", "README.rst", "README.txt", "README"]
        has_readme = any((path / f).exists() for f in readme_files)
        if not has_readme:
            warnings.append("No README file found")

        # Check for function documentation
        if project_type in ("python", "django"):
            for py_file in path.rglob("*.py"):
                if any(skip in str(py_file) for skip in ["test", "__pycache__", ".git"]):
                    continue
                try:
                    content = py_file.read_text()
                    # Count functions without docstrings
                    import re
                    functions = re.findall(r"def \w+\(", content)
                    docstrings = re.findall(r'"""', content)
                    if len(functions) > len(docstrings) // 2:
                        warnings.append(f"{py_file.name}: Missing docstrings")
                        break  # Only warn once
                except:
                    pass

        return warnings[:5]

    def is_applicable(self, path: Path, project_type: str) -> bool:
        """Code review is always applicable."""
        return True
