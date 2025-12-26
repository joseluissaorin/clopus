---
name: security-audit
description: Security auditing and vulnerability assessment
version: 1.0.0
category: security
technologies: [python, owasp, bandit, semgrep, trivy]
triggers:
  - security audit
  - vulnerability scan
  - security assessment
  - penetration testing
---

# Security Audit

Security auditing, vulnerability scanning, and assessment.

## Static Analysis

```python
import subprocess
import json
from pathlib import Path
from typing import List, Dict

class SecurityScanner:
    def run_bandit(self, path: str) -> List[Dict]:
        """Run Bandit for Python security analysis."""
        result = subprocess.run(
            ['bandit', '-r', path, '-f', 'json', '-ll'],
            capture_output=True,
            text=True
        )

        if result.stdout:
            data = json.loads(result.stdout)
            return data.get('results', [])
        return []

    def run_semgrep(self, path: str, config: str = 'auto') -> List[Dict]:
        """Run Semgrep for multi-language security scanning."""
        result = subprocess.run(
            ['semgrep', '--config', config, path, '--json'],
            capture_output=True,
            text=True
        )

        if result.stdout:
            data = json.loads(result.stdout)
            return data.get('results', [])
        return []

    def run_trivy(self, image: str) -> Dict:
        """Scan Docker image for vulnerabilities."""
        result = subprocess.run(
            ['trivy', 'image', '--format', 'json', image],
            capture_output=True,
            text=True
        )

        if result.stdout:
            return json.loads(result.stdout)
        return {}

    def run_npm_audit(self, path: str) -> Dict:
        """Run npm audit for JavaScript dependencies."""
        result = subprocess.run(
            ['npm', 'audit', '--json'],
            cwd=path,
            capture_output=True,
            text=True
        )

        if result.stdout:
            return json.loads(result.stdout)
        return {}
```

## OWASP Top 10 Checks

```python
class OWASPChecker:
    def check_injection(self, code: str) -> List[Dict]:
        """Check for injection vulnerabilities."""
        issues = []

        # SQL Injection patterns
        sql_patterns = [
            r'execute\s*\(\s*["\'].*%s',
            r'cursor\.execute\s*\(\s*f["\']',
            r'query\s*=.*\+.*input',
        ]

        # Command Injection patterns
        cmd_patterns = [
            r'os\.system\s*\(',
            r'subprocess\.call\s*\([^,]+shell\s*=\s*True',
            r'eval\s*\(',
            r'exec\s*\(',
        ]

        for pattern in sql_patterns + cmd_patterns:
            matches = re.finditer(pattern, code)
            for match in matches:
                issues.append({
                    'type': 'injection',
                    'severity': 'high',
                    'line': code[:match.start()].count('\n') + 1,
                    'match': match.group()
                })

        return issues

    def check_broken_auth(self, code: str) -> List[Dict]:
        """Check for authentication issues."""
        issues = []

        patterns = [
            (r'password\s*=\s*["\'][^"\']+["\']', 'Hardcoded password'),
            (r'jwt\.decode\s*\([^)]*verify\s*=\s*False', 'JWT verification disabled'),
            (r'session\s*\[\s*["\'].*["\']\s*\]\s*=.*request', 'Potential session fixation'),
        ]

        for pattern, message in patterns:
            if re.search(pattern, code):
                issues.append({
                    'type': 'broken_auth',
                    'severity': 'high',
                    'message': message
                })

        return issues

    def check_sensitive_data(self, code: str) -> List[Dict]:
        """Check for sensitive data exposure."""
        issues = []

        # API keys, tokens, secrets
        secret_patterns = [
            r'api_key\s*=\s*["\'][A-Za-z0-9]{20,}["\']',
            r'secret\s*=\s*["\'][^"\']{10,}["\']',
            r'password\s*=\s*["\'][^"\']+["\']',
            r'AWS_SECRET_ACCESS_KEY',
            r'PRIVATE_KEY',
        ]

        for pattern in secret_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                issues.append({
                    'type': 'sensitive_data',
                    'severity': 'critical',
                    'message': f'Potential secret exposure: {pattern}'
                })

        return issues

    def check_xss(self, code: str) -> List[Dict]:
        """Check for XSS vulnerabilities."""
        issues = []

        patterns = [
            (r'innerHTML\s*=', 'Direct innerHTML assignment'),
            (r'document\.write\s*\(', 'document.write usage'),
            (r'dangerouslySetInnerHTML', 'React dangerouslySetInnerHTML'),
            (r'\|\s*safe', 'Django/Jinja safe filter'),
        ]

        for pattern, message in patterns:
            if re.search(pattern, code):
                issues.append({
                    'type': 'xss',
                    'severity': 'high',
                    'message': message
                })

        return issues
```

## Dependency Audit

```python
class DependencyAuditor:
    def audit_requirements(self, requirements_path: str) -> List[Dict]:
        """Audit Python requirements for known vulnerabilities."""
        result = subprocess.run(
            ['pip-audit', '-r', requirements_path, '--format', 'json'],
            capture_output=True,
            text=True
        )

        if result.stdout:
            return json.loads(result.stdout)
        return []

    def check_outdated(self, path: str) -> List[Dict]:
        """Check for outdated dependencies."""
        result = subprocess.run(
            ['pip', 'list', '--outdated', '--format', 'json'],
            capture_output=True,
            text=True
        )

        if result.stdout:
            return json.loads(result.stdout)
        return []
```

## Security Headers Check

```python
import httpx

class HeadersChecker:
    SECURITY_HEADERS = {
        'Strict-Transport-Security': 'HSTS not set',
        'Content-Security-Policy': 'CSP not set',
        'X-Frame-Options': 'Clickjacking protection not set',
        'X-Content-Type-Options': 'MIME sniffing protection not set',
        'X-XSS-Protection': 'XSS protection not set',
        'Referrer-Policy': 'Referrer policy not set',
    }

    async def check_headers(self, url: str) -> Dict:
        """Check security headers of a URL."""
        async with httpx.AsyncClient() as client:
            response = await client.get(url)

        results = {
            'url': url,
            'missing': [],
            'present': [],
            'score': 0
        }

        for header, message in self.SECURITY_HEADERS.items():
            if header.lower() in [h.lower() for h in response.headers]:
                results['present'].append(header)
                results['score'] += 1
            else:
                results['missing'].append({'header': header, 'message': message})

        results['score'] = (results['score'] / len(self.SECURITY_HEADERS)) * 100

        return results
```

## Report Generation

```python
def generate_security_report(findings: Dict) -> str:
    report = """
# Security Audit Report

## Executive Summary
"""

    critical = len([f for f in findings.get('issues', []) if f.get('severity') == 'critical'])
    high = len([f for f in findings.get('issues', []) if f.get('severity') == 'high'])
    medium = len([f for f in findings.get('issues', []) if f.get('severity') == 'medium'])

    report += f"""
- **Critical Issues:** {critical}
- **High Issues:** {high}
- **Medium Issues:** {medium}

## Findings

"""

    for issue in sorted(findings.get('issues', []),
                        key=lambda x: {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}.get(x.get('severity', 'low'), 4)):
        report += f"""
### [{issue.get('severity', 'unknown').upper()}] {issue.get('type', 'Unknown')}
- **Location:** {issue.get('file', 'N/A')}:{issue.get('line', 'N/A')}
- **Description:** {issue.get('message', 'No description')}
- **Recommendation:** {issue.get('recommendation', 'Review and fix')}

"""

    return report
```

## Best Practices

1. Run scans in CI/CD pipeline
2. Keep dependencies updated
3. Use multiple scanning tools
4. Prioritize critical findings
5. Document remediation steps
6. Regular security training
7. Implement security headers
8. Use secrets management
