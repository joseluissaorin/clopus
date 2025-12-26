#!/bin/bash
# =============================================================================
# CLOPUS Worker Post-Task Hook
# =============================================================================
# Runs after each task execution

set -e

WORKER_ID=${WORKER_ID:-1}
WORKER_ROLE=${WORKER_ROLE:-coder}
TASK_ID=${1:-unknown}
TASK_STATUS=${2:-completed}
IPC_PATH=${IPC_PATH:-/app/ipc}

echo "[Hook] Post-task: Worker $WORKER_ID completed task $TASK_ID with status $TASK_STATUS"

# Update worker status
STATUS_FILE="$IPC_PATH/tasks/$WORKER_ID/status.json"
echo "{\"status\": \"idle\", \"role\": \"$WORKER_ROLE\", \"last_task\": \"$TASK_ID\", \"last_status\": \"$TASK_STATUS\", \"updated_at\": \"$(date -Iseconds)\"}" > "$STATUS_FILE"

# Log task completion
echo "[$(date -Iseconds)] Task $TASK_ID $TASK_STATUS by Worker $WORKER_ID" >> "$IPC_PATH/activity.log"

# Sync memory if significant work was done
if [ "$TASK_STATUS" = "completed" ]; then
    # Store learning from successful task
    if command -v python3 &>/dev/null; then
        python3 -c "
import json
from datetime import datetime

learning = {
    'worker_id': $WORKER_ID,
    'role': '$WORKER_ROLE',
    'task_id': '$TASK_ID',
    'completed_at': datetime.now().isoformat()
}

# Write to learnings file
with open('$IPC_PATH/learnings.jsonl', 'a') as f:
    f.write(json.dumps(learning) + '\n')
" 2>/dev/null || true
    fi
fi

exit 0
