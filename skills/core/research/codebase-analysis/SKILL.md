---
name: codebase-analysis
description: Analyze and understand codebases
version: 1.0.0
category: research
technologies: [python, ast, tree-sitter, git]
triggers:
  - codebase analysis
  - code understanding
  - architecture analysis
  - dependency analysis
---

# Codebase Analysis

Tools and techniques for understanding codebases.

## Project Structure Analysis

```python
from pathlib import Path
from collections import defaultdict
import json

class ProjectAnalyzer:
    def __init__(self, root_path: str):
        self.root = Path(root_path)
        self.ignore_dirs = {'.git', 'node_modules', '__pycache__', 'venv', '.venv', 'dist', 'build'}

    def analyze_structure(self) -> dict:
        structure = {
            "root": str(self.root),
            "files_by_type": defaultdict(list),
            "directories": [],
            "total_files": 0,
            "total_lines": 0
        }

        for path in self.root.rglob('*'):
            if any(ignored in path.parts for ignored in self.ignore_dirs):
                continue

            if path.is_file():
                ext = path.suffix.lower()
                structure["files_by_type"][ext].append(str(path.relative_to(self.root)))
                structure["total_files"] += 1

                try:
                    structure["total_lines"] += len(path.read_text().splitlines())
                except:
                    pass
            elif path.is_dir():
                structure["directories"].append(str(path.relative_to(self.root)))

        return structure

    def detect_project_type(self) -> str:
        indicators = {
            "package.json": "node",
            "requirements.txt": "python",
            "pyproject.toml": "python",
            "Cargo.toml": "rust",
            "go.mod": "go",
            "pom.xml": "java-maven",
            "build.gradle": "java-gradle",
            "Gemfile": "ruby",
            "composer.json": "php"
        }

        for file, project_type in indicators.items():
            if (self.root / file).exists():
                return project_type

        return "unknown"
```

## Dependency Analysis

```python
import ast
import re
from typing import Set, Dict

class DependencyAnalyzer:
    def analyze_python_imports(self, file_path: str) -> Set[str]:
        """Extract imports from Python file."""
        imports = set()

        with open(file_path, 'r') as f:
            tree = ast.parse(f.read())

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split('.')[0])

        return imports

    def analyze_js_imports(self, file_path: str) -> Set[str]:
        """Extract imports from JavaScript/TypeScript file."""
        imports = set()

        with open(file_path, 'r') as f:
            content = f.read()

        # Match import statements
        patterns = [
            r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]',
            r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)',
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, content):
                module = match.group(1)
                if not module.startswith('.'):
                    imports.add(module.split('/')[0])

        return imports

    def build_dependency_graph(self, root: str) -> Dict:
        """Build internal dependency graph."""
        graph = defaultdict(set)
        root_path = Path(root)

        for py_file in root_path.rglob('*.py'):
            module_name = str(py_file.relative_to(root_path)).replace('/', '.').replace('.py', '')
            imports = self.analyze_python_imports(str(py_file))
            graph[module_name] = imports

        return dict(graph)
```

## Code Complexity Analysis

```python
import ast
from dataclasses import dataclass
from typing import List

@dataclass
class FunctionMetrics:
    name: str
    lines: int
    complexity: int  # Cyclomatic complexity
    parameters: int
    nested_depth: int

class ComplexityAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.functions: List[FunctionMetrics] = []
        self.current_depth = 0
        self.max_depth = 0

    def analyze_file(self, file_path: str) -> List[FunctionMetrics]:
        with open(file_path, 'r') as f:
            tree = ast.parse(f.read())

        self.visit(tree)
        return self.functions

    def visit_FunctionDef(self, node):
        complexity = self._calculate_complexity(node)

        metrics = FunctionMetrics(
            name=node.name,
            lines=node.end_lineno - node.lineno + 1,
            complexity=complexity,
            parameters=len(node.args.args),
            nested_depth=self._get_max_depth(node)
        )
        self.functions.append(metrics)
        self.generic_visit(node)

    def _calculate_complexity(self, node) -> int:
        """Calculate cyclomatic complexity."""
        complexity = 1

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1

        return complexity

    def _get_max_depth(self, node, depth=0) -> int:
        max_depth = depth
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.With, ast.Try)):
                max_depth = max(max_depth, self._get_max_depth(child, depth + 1))
            else:
                max_depth = max(max_depth, self._get_max_depth(child, depth))
        return max_depth
```

## Git History Analysis

```python
import subprocess
from datetime import datetime
from collections import defaultdict

class GitAnalyzer:
    def __init__(self, repo_path: str):
        self.repo_path = repo_path

    def _run_git(self, *args) -> str:
        result = subprocess.run(
            ['git', '-C', self.repo_path] + list(args),
            capture_output=True,
            text=True
        )
        return result.stdout

    def get_file_history(self, file_path: str) -> List[Dict]:
        """Get commit history for a file."""
        log = self._run_git(
            'log', '--follow', '--format=%H|%an|%ae|%at|%s',
            '--', file_path
        )

        commits = []
        for line in log.strip().split('\n'):
            if line:
                hash_, author, email, timestamp, message = line.split('|', 4)
                commits.append({
                    'hash': hash_,
                    'author': author,
                    'email': email,
                    'date': datetime.fromtimestamp(int(timestamp)),
                    'message': message
                })

        return commits

    def get_contributors(self) -> Dict[str, int]:
        """Get contributor statistics."""
        log = self._run_git('shortlog', '-sn', '--all')

        contributors = {}
        for line in log.strip().split('\n'):
            if line:
                count, name = line.strip().split('\t', 1)
                contributors[name] = int(count)

        return contributors

    def get_hotspots(self, limit: int = 20) -> List[Dict]:
        """Find frequently changed files."""
        log = self._run_git('log', '--name-only', '--format=')

        file_counts = defaultdict(int)
        for line in log.split('\n'):
            if line.strip():
                file_counts[line.strip()] += 1

        sorted_files = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)
        return [{'file': f, 'changes': c} for f, c in sorted_files[:limit]]
```

## Report Generation

```python
def generate_analysis_report(project_path: str) -> str:
    analyzer = ProjectAnalyzer(project_path)

    structure = analyzer.analyze_structure()
    project_type = analyzer.detect_project_type()

    report = f"""
# Codebase Analysis Report

## Overview
- **Project Type**: {project_type}
- **Total Files**: {structure['total_files']}
- **Total Lines**: {structure['total_lines']:,}

## File Distribution
"""

    for ext, files in sorted(structure['files_by_type'].items()):
        report += f"- `{ext}`: {len(files)} files\n"

    return report
```

## Best Practices

1. Start with high-level structure
2. Identify entry points
3. Map dependencies
4. Find complexity hotspots
5. Review git history for context
6. Document findings
7. Create architecture diagrams
8. Identify patterns and anti-patterns
