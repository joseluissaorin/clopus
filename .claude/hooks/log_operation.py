#!/usr/bin/env python3
"""
CLOPUS PostToolUse Hook - Operation Logging
============================================
Logs all tool operations for orchestrator tracking and debugging.

This hook runs INSIDE Docker workers and logs to IPC for orchestrator visibility.
"""

import json
import sys
import os
from datetime import datetime


def summarize_input(tool_name: str, tool_input: dict) -> str:
    """Create a brief summary of tool input."""
    if tool_name == 'Bash':
        cmd = tool_input.get('command', '')
        return cmd[:100] + '...' if len(cmd) > 100 else cmd
    elif tool_name == 'Read':
        return tool_input.get('file_path', 'unknown')
    elif tool_name == 'Edit':
        return f"Edit {tool_input.get('file_path', 'unknown')}"
    elif tool_name == 'Write':
        return f"Write {tool_input.get('file_path', 'unknown')}"
    elif tool_name == 'Grep':
        return f"Grep '{tool_input.get('pattern', '')}'"
    elif tool_name == 'Glob':
        return f"Glob '{tool_input.get('pattern', '')}'"
    else:
        return str(tool_input)[:100]


def main():
    # Read hook input from stdin
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    # Extract operation details
    tool_name = data.get('tool_name', 'unknown')
    tool_input = data.get('tool_input', {})
    tool_output = data.get('tool_output', {})

    # Get worker ID from environment
    worker_id = os.environ.get('WORKER_ID', os.environ.get('CLOPUS_WORKER_ID', '0'))
    worker_role = os.environ.get('WORKER_ROLE', 'unknown')
    task_id = os.environ.get('CLOPUS_CURRENT_TASK', 'none')

    # Build log entry
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'worker_id': worker_id,
        'worker_role': worker_role,
        'task_id': task_id,
        'tool': tool_name,
        'input_summary': summarize_input(tool_name, tool_input),
        'success': tool_output.get('success', True) if isinstance(tool_output, dict) else True
    }

    # Write to worker log file
    log_file = f'/tmp/clopus_worker_{worker_id}_operations.jsonl'
    try:
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    except Exception:
        pass

    # Write to shared IPC log if available
    ipc_path = os.environ.get('IPC_PATH', os.environ.get('CLOPUS_IPC_PATH', '/app/ipc'))
    ipc_log = f'{ipc_path}/tasks/{worker_id}/operations.jsonl'
    try:
        os.makedirs(os.path.dirname(ipc_log), exist_ok=True)
        with open(ipc_log, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    except Exception:
        pass

    # For important operations, also write to a shared operations log
    if tool_name in ('Write', 'Edit', 'Bash'):
        shared_log = f'{ipc_path}/collaboration/events/operations.jsonl'
        try:
            os.makedirs(os.path.dirname(shared_log), exist_ok=True)
            with open(shared_log, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception:
            pass

    sys.exit(0)


if __name__ == '__main__':
    main()
