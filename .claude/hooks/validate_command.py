#!/usr/bin/env python3
"""
CLOPUS PreToolUse Hook - Command Validation
============================================
Validates Bash commands before execution to prevent dangerous operations.

This hook runs INSIDE Docker workers and blocks dangerous commands.
"""

import json
import sys
import re
import os

# Read hook input from stdin
try:
    data = json.load(sys.stdin)
except json.JSONDecodeError:
    sys.exit(0)

tool_name = data.get('tool_name', '')
tool_input = data.get('tool_input', {})

# Only validate Bash commands
if tool_name != 'Bash':
    sys.exit(0)

command = tool_input.get('command', '')

# Get worker ID for context
worker_id = os.environ.get('WORKER_ID', os.environ.get('CLOPUS_WORKER_ID', '0'))

# Dangerous patterns that should be blocked
DANGEROUS_PATTERNS = [
    # File system destruction
    (r'rm\s+-rf\s+/$', 'Recursive delete from root'),
    (r'rm\s+-rf\s+/\s', 'Recursive delete from root'),
    (r'rm\s+-rf\s+~', 'Recursive delete from home'),
    (r'rm\s+-rf\s+/workspace$', 'Delete entire workspace'),
    (r'rm\s+-rf\s+\*$', 'Delete with wildcard'),
    (r'rm\s+-rf\s+\.\*', 'Delete hidden files'),

    # System commands
    (r'\bsudo\s', 'Sudo command'),
    (r'\bshutdown\b', 'Shutdown command'),
    (r'\breboot\b', 'Reboot command'),
    (r'\bmkfs\b', 'Filesystem format'),
    (r'\bdd\s+if=', 'Direct disk write'),
    (r'\bchown\s+-R\s+.*/', 'Recursive chown from root'),
    (r'\bchmod\s+-R\s+777\s+/', 'Recursive chmod 777 from root'),

    # Database destruction
    (r'DROP\s+DATABASE', 'Drop database'),
    (r'DROP\s+TABLE\s+\*', 'Drop all tables'),
    (r'TRUNCATE\s+TABLE', 'Truncate table'),
    (r'DELETE\s+FROM\s+\w+\s*;?\s*$', 'Delete all from table'),

    # Git destructive
    (r'git\s+push\s+.*--force\s+.*main', 'Force push to main'),
    (r'git\s+push\s+.*--force\s+.*master', 'Force push to master'),
    (r'git\s+reset\s+--hard\s+HEAD~', 'Hard reset'),
    (r'git\s+clean\s+-fdx', 'Git clean all untracked'),

    # Secrets exposure
    (r'cat\s+.*\.env\.production', 'Read production env'),
    (r'cat\s+.*/\.ssh/id_', 'Read SSH keys'),

    # Container escape attempts
    (r'docker\s+exec\s+.*rm\s+-rf', 'Docker exec with rm -rf'),
    (r'nsenter\b', 'Namespace enter'),
]

# Check command against patterns
for pattern, reason in DANGEROUS_PATTERNS:
    if re.search(pattern, command, re.IGNORECASE):
        # Block the command
        result = {
            'permissionDecision': 'deny',
            'permissionDecisionReason': f'CLOPUS Safety [Worker {worker_id}]: {reason} - Command blocked'
        }
        print(json.dumps(result))
        sys.exit(0)

# Command is safe - allow it
sys.exit(0)
