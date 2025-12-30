# =============================================================================
# CLOPUS v3 E2E Test Validator
# =============================================================================
"""
End-to-end test execution using Playwright.
"""

from pathlib import Path
import json

from .base import BaseValidator
from ..pipeline import StageResult, ValidationStage, ValidationStatus


class E2ETestValidator(BaseValidator):
    """Run end-to-end tests with Playwright."""

    stage = ValidationStage.E2E_TESTS

    async def validate(self, path: Path, project_type: str) -> StageResult:
        """Run E2E tests."""
        # Check for Playwright config
        playwright_configs = [
            "playwright.config.ts",
            "playwright.config.js",
            "e2e/playwright.config.ts"
        ]

        has_playwright = any(
            (path / config).exists()
            for config in playwright_configs
        )

        if has_playwright:
            return await self._run_playwright(path)

        # Check for Cypress
        if (path / "cypress.config.js").exists() or (path / "cypress.config.ts").exists():
            return await self._run_cypress(path)

        # Check for e2e script in package.json
        if (path / "package.json").exists():
            pkg = json.loads((path / "package.json").read_text())
            scripts = pkg.get("scripts", {})

            if "test:e2e" in scripts:
                return await self._run_npm_e2e(path)
            elif "e2e" in scripts:
                return await self._run_npm_e2e(path, "e2e")

        return StageResult(
            stage=self.stage,
            status=ValidationStatus.SKIPPED,
            output="No E2E test configuration found"
        )

    async def _run_playwright(self, path: Path) -> StageResult:
        """Run Playwright tests."""
        # Install browsers if needed
        await self.run_command(
            ["npx", "playwright", "install", "--with-deps"],
            cwd=path,
            timeout=300
        )

        returncode, stdout, stderr = await self.run_command(
            ["npx", "playwright", "test", "--reporter=line"],
            cwd=path,
            timeout=600
        )

        output = stdout + stderr

        if returncode == 0:
            return StageResult(
                stage=self.stage,
                status=ValidationStatus.PASSED,
                output="All E2E tests passed"
            )

        # Parse Playwright output
        errors = []
        for line in output.split("\n"):
            if "FAILED" in line or "Error" in line:
                errors.append(line[:200])

        return StageResult(
            stage=self.stage,
            status=ValidationStatus.FAILED,
            output=output,
            errors=errors[:10]
        )

    async def _run_cypress(self, path: Path) -> StageResult:
        """Run Cypress tests."""
        returncode, stdout, stderr = await self.run_command(
            ["npx", "cypress", "run", "--headless"],
            cwd=path,
            timeout=600
        )

        output = stdout + stderr

        if returncode == 0:
            return StageResult(
                stage=self.stage,
                status=ValidationStatus.PASSED,
                output="All Cypress tests passed"
            )

        errors = self.parse_errors(output)
        return StageResult(
            stage=self.stage,
            status=ValidationStatus.FAILED,
            output=output,
            errors=errors[:10]
        )

    async def _run_npm_e2e(self, path: Path, script: str = "test:e2e") -> StageResult:
        """Run E2E via npm script."""
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
                output="E2E tests passed"
            )

        return StageResult(
            stage=self.stage,
            status=ValidationStatus.FAILED,
            output=output,
            errors=self.parse_errors(output)
        )

    # Web project types that should have E2E tests
    WEB_PROJECT_TYPES = {
        "react", "nextjs", "vue", "angular", "svelte", "solid",
        "web", "frontend", "dashboard", "spa", "pwa", "nodejs",
        "todo", "app", "webapp", "website", "landing",
        "admin", "portal", "ui", "interface", "vite"
    }

    def is_applicable(self, path: Path, project_type: str) -> bool:
        """Check if E2E tests are applicable - ANY web project with config."""
        # Check for E2E config files first (if config exists, run tests)
        e2e_indicators = [
            "playwright.config.ts",
            "playwright.config.js",
            "playwright.config.mjs",
            "cypress.config.js",
            "cypress.config.ts",
            "e2e",
            "tests"
        ]

        for indicator in e2e_indicators:
            if (path / indicator).exists():
                return True

        # Check for e2e script in package.json
        if (path / "package.json").exists():
            try:
                pkg = json.loads((path / "package.json").read_text())
                scripts = pkg.get("scripts", {})
                if any("e2e" in k.lower() or "playwright" in k.lower() for k in scripts.keys()):
                    return True
            except:
                pass

        # Check project type - be inclusive for web projects
        project_type_lower = (project_type or "").lower()
        for web_type in self.WEB_PROJECT_TYPES:
            if web_type in project_type_lower:
                # For web projects, check if there's any test infrastructure
                if (path / "package.json").exists():
                    try:
                        pkg = json.loads((path / "package.json").read_text())
                        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                        if "@playwright/test" in deps or "cypress" in deps:
                            return True
                    except:
                        pass

        return False
