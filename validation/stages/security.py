# =============================================================================
# CLOPUS v3 Security Validator
# =============================================================================
"""
Security scanning for vulnerabilities and issues.
"""

from pathlib import Path
import json
import re

from .base import BaseValidator
from ..pipeline import StageResult, ValidationStage, ValidationStatus


class SecurityValidator(BaseValidator):
    """Run security scans."""

    stage = ValidationStage.SECURITY

    # Patterns that indicate potential security issues
    DANGEROUS_PATTERNS = [
        (r"eval\s*\(", "Dangerous eval() usage"),
        (r"exec\s*\(", "Dangerous exec() usage"),
        (r"innerHTML\s*=", "Potential XSS via innerHTML"),
        (r"document\.write", "Potential XSS via document.write"),
        (r"password\s*=\s*['\"][^'\"]+['\"]", "Hardcoded password"),
        (r"api[_-]?key\s*=\s*['\"][^'\"]+['\"]", "Hardcoded API key"),
        (r"secret\s*=\s*['\"][^'\"]+['\"]", "Hardcoded secret"),
        (r"SELECT\s+.*\s+FROM.*\+", "Potential SQL injection"),
        (r"subprocess\.call\(.*(shell=True)", "Shell injection risk"),
        (r"os\.system\s*\(", "Shell command execution"),
    ]

    async def validate(self, path: Path, project_type: str) -> StageResult:
        """Run security validations."""
        errors = []
        warnings = []

        # Run npm audit for Node.js projects
        if (path / "package.json").exists():
            audit_result = await self._run_npm_audit(path)
            errors.extend(audit_result[0])
            warnings.extend(audit_result[1])

        # Run pip-audit for Python projects
        if project_type in ("python", "django"):
            audit_result = await self._run_pip_audit(path)
            errors.extend(audit_result[0])
            warnings.extend(audit_result[1])

        # Run pattern-based security scan
        pattern_result = await self._scan_patterns(path)
        errors.extend(pattern_result[0])
        warnings.extend(pattern_result[1])

        # Check for common misconfigurations
        config_result = await self._check_configs(path)
        errors.extend(config_result[0])
        warnings.extend(config_result[1])

        # Determine status
        if errors:
            status = ValidationStatus.FAILED
        elif warnings:
            status = ValidationStatus.PASSED
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
        """Run npm audit."""
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
                message = f"{name}: {severity} severity vulnerability"

                if severity in ("high", "critical"):
                    errors.append(message)
                else:
                    warnings.append(message)

        except json.JSONDecodeError:
            # Non-JSON output, parse as text
            if "high" in stdout.lower() or "critical" in stdout.lower():
                errors.append("npm audit found high/critical vulnerabilities")
            elif "moderate" in stdout.lower():
                warnings.append("npm audit found moderate vulnerabilities")

        return errors, warnings

    async def _run_pip_audit(self, path: Path) -> tuple:
        """Run pip-audit."""
        returncode, stdout, stderr = await self.run_command(
            ["pip-audit", "--format", "json"],
            cwd=path,
            timeout=120
        )

        errors = []
        warnings = []

        try:
            audit_data = json.loads(stdout)
            for vuln in audit_data:
                name = vuln.get("name", "unknown")
                vuln_id = vuln.get("id", "")
                message = f"{name}: {vuln_id}"
                errors.append(message)
        except json.JSONDecodeError:
            if returncode != 0 and stdout:
                errors.append("pip-audit found vulnerabilities")

        return errors, warnings

    async def _scan_patterns(self, path: Path) -> tuple:
        """Scan for dangerous patterns."""
        errors = []
        warnings = []

        # File extensions to scan
        extensions = [".py", ".js", ".ts", ".jsx", ".tsx", ".php", ".rb"]

        for ext in extensions:
            for file in path.rglob(f"*{ext}"):
                # Skip common non-source directories
                if any(
                    skip in str(file)
                    for skip in ["node_modules", "__pycache__", ".git", "dist", "build", "vendor"]
                ):
                    continue

                try:
                    content = file.read_text()

                    for pattern, message in self.DANGEROUS_PATTERNS:
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        if matches:
                            rel_path = file.relative_to(path)
                            warnings.append(f"{rel_path}: {message}")

                except Exception:
                    pass

        return errors, warnings[:20]

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
                    gitignore_content = gitignore.read_text()
                    if secret_file not in gitignore_content:
                        warnings.append(f"{secret_file} should be in .gitignore")
                else:
                    warnings.append(f"{secret_file} exists but no .gitignore found")

        # Check for DEBUG mode in production configs
        settings_files = list(path.rglob("**/settings.py")) + list(path.rglob("**/config.py"))
        for settings in settings_files:
            try:
                content = settings.read_text()
                if re.search(r"DEBUG\s*=\s*True", content):
                    warnings.append(f"{settings.name}: DEBUG=True should not be in production")
            except:
                pass

        return errors, warnings

    def is_applicable(self, path: Path, project_type: str) -> bool:
        """Security scan is applicable to all projects."""
        return True
