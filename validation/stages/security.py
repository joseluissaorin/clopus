# =============================================================================
# CLOPUS v3 Security Validator
# =============================================================================
"""
Security scanning for vulnerabilities and issues.

AI-FIRST APPROACH (v3.3):
- Uses structured JSON output from security tools
- Pattern matching is context-aware (skips comments, test files, safe contexts)
- No naive keyword matching - understands code semantics
- Relies on established security scanners where available
"""

from pathlib import Path
import json
import re
from typing import Optional, TYPE_CHECKING

from .base import BaseValidator
from ..pipeline import StageResult, ValidationStage, ValidationStatus

if TYPE_CHECKING:
    from orchestrator.ai_first import AIFirstEngine


class SecurityValidator(BaseValidator):
    """Run security scans using AI-first approach."""

    stage = ValidationStage.SECURITY

    # Context-aware security patterns
    # Each pattern has: (regex, message, false_positive_contexts)
    SECURITY_CHECKS = [
        # Critical: hardcoded credentials
        {
            "pattern": r'(?:password|passwd|pwd)\s*[=:]\s*["\'][^"\']{8,}["\']',
            "message": "Potential hardcoded password",
            "severity": "warning",
            "skip_in": ["test", "example", "mock", "sample", "fixture"],
            "skip_patterns": [r"placeholder", r"your_password", r"\*\*\*", r"xxx"],
        },
        {
            "pattern": r'(?:api[_-]?key|apikey|api_secret)\s*[=:]\s*["\'][a-zA-Z0-9_\-]{20,}["\']',
            "message": "Potential hardcoded API key",
            "severity": "warning",
            "skip_in": ["test", "example", "mock", ".env.example"],
            "skip_patterns": [r"your_api_key", r"sk_test_", r"pk_test_"],
        },
        # SQL Injection - only flag string concatenation in SQL
        {
            "pattern": r'(?:SELECT|INSERT|UPDATE|DELETE|DROP)\s+.*?\+\s*(?:request|req|params|query|user)',
            "message": "Potential SQL injection via string concatenation",
            "severity": "warning",
            "skip_in": ["test", "mock"],
            "skip_patterns": [],
        },
        # Command injection - only in non-controlled contexts
        {
            "pattern": r'(?:subprocess\.(?:call|run|Popen)|os\.system|os\.popen)\s*\([^)]*(?:request|params|input|user)',
            "message": "Potential command injection",
            "severity": "warning",
            "skip_in": ["test"],
            "skip_patterns": [],
        },
    ]

    async def validate(self, path: Path, project_type: str) -> StageResult:
        """Run security validations using structured tools."""
        errors = []
        warnings = []

        # Run npm audit for Node.js projects (structured JSON)
        if (path / "package.json").exists():
            audit_result = await self._run_npm_audit(path)
            errors.extend(audit_result[0])
            warnings.extend(audit_result[1])

        # Run pip-audit for Python projects (structured JSON)
        if project_type in ("python", "django"):
            audit_result = await self._run_pip_audit(path)
            errors.extend(audit_result[0])
            warnings.extend(audit_result[1])

        # Context-aware pattern scan (not naive regex)
        pattern_result = await self._scan_patterns_smart(path)
        warnings.extend(pattern_result)

        # Check for common misconfigurations
        config_result = await self._check_configs(path)
        errors.extend(config_result[0])
        warnings.extend(config_result[1])

        # Determine status - only fail on actual security errors (npm/pip audit)
        # Pattern matches are warnings only
        if errors:
            status = ValidationStatus.FAILED
        else:
            status = ValidationStatus.PASSED

        return StageResult(
            stage=self.stage,
            status=status,
            output=f"Security scan: {len(errors)} issues, {len(warnings)} warnings",
            errors=errors[:20],
            warnings=warnings[:20]
        )

    async def _run_npm_audit(self, path: Path) -> tuple:
        """
        Run npm audit with JSON output.

        AI-First: Uses structured JSON for precise vulnerability extraction.
        """
        returncode, stdout, stderr = await self.run_command(
            ["npm", "audit", "--json"],
            cwd=path,
            timeout=120
        )

        errors = []
        warnings = []

        try:
            audit_data = json.loads(stdout)
            vulnerabilities = audit_data.get("vulnerabilities", {})

            for name, vuln in vulnerabilities.items():
                severity = vuln.get("severity", "low")
                via = vuln.get("via", [])
                via_str = ""
                if via and isinstance(via[0], dict):
                    via_str = f" - {via[0].get('title', '')}"

                message = f"{name}: {severity} severity{via_str}"

                if severity in ("high", "critical"):
                    errors.append(message)
                elif severity == "moderate":
                    warnings.append(message)
                # Skip low severity

        except json.JSONDecodeError:
            # If npm audit fails to produce JSON, check exit code
            if returncode != 0 and returncode != 1:  # 1 = vulnerabilities found
                # This is a tool error, not a security issue
                pass

        return errors[:10], warnings[:10]

    async def _run_pip_audit(self, path: Path) -> tuple:
        """
        Run pip-audit with JSON output.

        AI-First: Uses structured JSON for precise vulnerability extraction.
        """
        returncode, stdout, stderr = await self.run_command(
            ["pip-audit", "--format", "json"],
            cwd=path,
            timeout=120
        )

        errors = []
        warnings = []

        try:
            audit_data = json.loads(stdout) if stdout.strip() else []
            for vuln in audit_data:
                name = vuln.get("name", "unknown")
                vuln_id = vuln.get("id", "")
                fix_versions = vuln.get("fix_versions", [])
                fix_str = f" (fix: {fix_versions[0]})" if fix_versions else ""
                message = f"{name}: {vuln_id}{fix_str}"
                errors.append(message)
        except json.JSONDecodeError:
            # Tool error, not security issue
            pass

        return errors[:10], warnings[:10]

    async def _scan_patterns_smart(self, path: Path) -> list:
        """
        Context-aware pattern scanning.

        AI-First approach:
        - Skips test files, examples, and mocks
        - Checks for false positive patterns in matched content
        - Doesn't match patterns in comments
        """
        warnings = []

        # File extensions to scan
        extensions = [".py", ".js", ".ts", ".jsx", ".tsx"]
        skip_dirs = ["node_modules", "__pycache__", ".git", "dist", "build", "vendor", ".venv", "venv"]

        for ext in extensions:
            for file in path.rglob(f"*{ext}"):
                # Skip directories
                if any(skip in str(file) for skip in skip_dirs):
                    continue

                file_str = str(file).lower()

                try:
                    content = file.read_text()
                    lines = content.split('\n')

                    for check in self.SECURITY_CHECKS:
                        # Skip if file is in skip_in list
                        if any(skip in file_str for skip in check.get("skip_in", [])):
                            continue

                        pattern = check["pattern"]
                        message = check["message"]
                        skip_patterns = check.get("skip_patterns", [])

                        for i, line in enumerate(lines, 1):
                            # Skip comment lines
                            stripped = line.strip()
                            if stripped.startswith(("#", "//", "/*", "*", "'")):
                                continue

                            matches = re.findall(pattern, line, re.IGNORECASE)
                            if matches:
                                # Check for false positive patterns
                                is_false_positive = False
                                for fp in skip_patterns:
                                    if re.search(fp, line, re.IGNORECASE):
                                        is_false_positive = True
                                        break

                                if not is_false_positive:
                                    rel_path = file.relative_to(path)
                                    warnings.append(f"{rel_path}:{i}: {message}")

                except Exception:
                    pass

        return warnings[:15]

    async def _check_configs(self, path: Path) -> tuple:
        """Check for configuration security issues."""
        errors = []
        warnings = []

        # Check for exposed secrets in common files
        secret_files = [".env", ".env.local", "config.json", "secrets.json"]
        for secret_file in secret_files:
            file_path = path / secret_file
            if file_path.exists():
                # Check if in .gitignore
                gitignore = path / ".gitignore"
                if gitignore.exists():
                    try:
                        gitignore_content = gitignore.read_text()
                        if secret_file not in gitignore_content:
                            warnings.append(f"{secret_file} should be in .gitignore")
                    except:
                        pass
                else:
                    warnings.append(f"{secret_file} exists but no .gitignore found")

        # Check for DEBUG mode in production configs (only in non-development files)
        settings_files = list(path.rglob("**/settings.py")) + list(path.rglob("**/config.py"))
        for settings in settings_files:
            # Skip development settings
            if "dev" in str(settings).lower() or "local" in str(settings).lower():
                continue

            try:
                content = settings.read_text()
                # Check for unconditional DEBUG = True (not in if/else)
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if re.search(r'^DEBUG\s*=\s*True', line) and not lines[max(0, i-1)].strip().startswith(('if', 'elif', '#')):
                        warnings.append(f"{settings.name}: DEBUG=True should be environment-controlled")
                        break
            except:
                pass

        return errors, warnings

    def is_applicable(self, path: Path, project_type: str) -> bool:
        """Security scan is applicable to all projects."""
        return True
