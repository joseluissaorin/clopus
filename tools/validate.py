#!/usr/bin/env python3
"""
CLOPUS Manual Validation Tool

Usage:
    python tools/validate.py /path/to/project
    python tools/validate.py /workspace/todo-app
    python tools/validate.py --all  # Validate all projects in /workspace
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from validation.pipeline import ValidationPipeline, ValidationStage


class SimpleConfig:
    """Simple config for standalone validation."""
    enabled_stages = [
        ValidationStage.SYNTAX,
        ValidationStage.LINT,
        ValidationStage.BUILD,
        ValidationStage.UNIT_TESTS,
        ValidationStage.INTEGRATION_TESTS,
        ValidationStage.E2E_TESTS,
        ValidationStage.SECURITY,
    ]
    strict_mode = False
    allow_warnings = True
    timeout_per_stage_s = 300


async def validate_project(project_path: str) -> dict:
    """Run validation on a project and return results."""
    path = Path(project_path)

    if not path.exists():
        return {"error": f"Project path does not exist: {project_path}"}

    print(f"\n{'='*60}")
    print(f"VALIDATING: {project_path}")
    print(f"{'='*60}\n")

    # Create validation pipeline
    pipeline = ValidationPipeline(
        memory_client=None,
        config=SimpleConfig(),
        worker_pool=None
    )

    # Run validation
    result = await pipeline.validate(project_path=project_path)

    # Display results
    print(f"\n{'='*60}")
    print(f"VALIDATION RESULTS")
    print(f"{'='*60}")
    print(f"Overall: {'✓ PASSED' if result.passed else '✗ FAILED'}")
    print(f"Duration: {result.total_duration_ms}ms")
    print()

    for stage in result.stages:
        stage_name = stage.stage.value if hasattr(stage.stage, 'value') else str(stage.stage)
        status = stage.status.value if hasattr(stage.status, 'value') else str(stage.status)

        icon = "✓" if status == "passed" else "✗" if status == "failed" else "○"
        print(f"  {icon} {stage_name}: {status.upper()}")

        if stage.errors:
            for error in stage.errors[:3]:
                print(f"      └─ {error[:100]}")

    print()

    # Save results to project
    results_file = path / ".clopus" / "validation_results.json"
    results_file.parent.mkdir(exist_ok=True)

    results_data = {
        "project_path": project_path,
        "overall_passed": result.passed,
        "stages": [
            {
                "stage": s.stage.value if hasattr(s.stage, 'value') else str(s.stage),
                "passed": (s.status.value if hasattr(s.status, 'value') else str(s.status)) == "passed",
                "errors": s.errors,
                "warnings": s.warnings,
                "duration_ms": s.duration_ms
            }
            for s in result.stages
        ],
        "total_duration_ms": result.total_duration_ms,
        "timestamp": datetime.now().isoformat()
    }

    results_file.write_text(json.dumps(results_data, indent=2))
    print(f"Results saved to: {results_file}")

    return results_data


async def start_dev_server(project_path: str) -> None:
    """Start dev server for a project."""
    import subprocess
    import os

    path = Path(project_path)

    if not (path / "package.json").exists():
        print(f"No package.json found in {project_path}")
        return

    pkg = json.loads((path / "package.json").read_text())
    scripts = pkg.get("scripts", {})

    if "dev" not in scripts:
        print(f"No 'dev' script found in package.json")
        return

    # Calculate port
    project_name = path.name
    port = 3000 + (hash(project_name) % 100)

    print(f"\nStarting dev server on port {port}...")

    # Create startup script
    startup_script = path / ".clopus" / "start_server.sh"
    startup_script.parent.mkdir(exist_ok=True)

    startup_script.write_text(f'''#!/bin/bash
cd {project_path}
export PORT={port}
export HOST=0.0.0.0
npm run dev -- --host 0.0.0.0 --port {port} &
echo $! > {path / ".clopus" / "dev_server.pid"}
echo "Server started on http://0.0.0.0:{port}"
''')
    os.chmod(startup_script, 0o755)

    # Run it
    subprocess.Popen(
        ["bash", str(startup_script)],
        cwd=project_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Save server info
    server_info = path / ".clopus" / "server_info.json"
    server_info.write_text(json.dumps({
        "port": port,
        "host": "0.0.0.0",
        "url": f"http://0.0.0.0:{port}",
        "started_at": datetime.now().isoformat()
    }, indent=2))

    print(f"✓ Dev server started: http://0.0.0.0:{port}")
    print(f"  Access from network: http://<your-ip>:{port}")


async def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    arg = sys.argv[1]

    if arg == "--all":
        # Validate all projects in /workspace
        workspace = Path("/workspace")
        if not workspace.exists():
            workspace = Path.home() / "Dev" / "clopus-projects"

        projects = [p for p in workspace.iterdir() if p.is_dir() and not p.name.startswith('.')]

        for project in projects:
            if (project / "package.json").exists() or (project / "requirements.txt").exists():
                await validate_project(str(project))
    elif arg == "--start-servers":
        # Start dev servers for all projects
        workspace = Path("/workspace")
        if not workspace.exists():
            workspace = Path.home() / "Dev" / "clopus-projects"

        projects = [p for p in workspace.iterdir() if p.is_dir() and not p.name.startswith('.')]

        for project in projects:
            if (project / "package.json").exists():
                await start_dev_server(str(project))
    else:
        # Validate specific project
        result = await validate_project(arg)

        if "--start" in sys.argv:
            await start_dev_server(arg)

        sys.exit(0 if result.get("overall_passed", False) else 1)


if __name__ == "__main__":
    asyncio.run(main())
