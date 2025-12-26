#!/bin/bash
# =============================================================================
# CLOPUS Worker Pre-Task Hook
# =============================================================================
# Runs before each task execution

set -e

WORKER_ID=${WORKER_ID:-1}
WORKER_ROLE=${WORKER_ROLE:-coder}
TASK_ID=${1:-unknown}
IPC_PATH=${IPC_PATH:-/app/ipc}

echo "[Hook] Pre-task: Worker $WORKER_ID ($WORKER_ROLE) starting task $TASK_ID"

# Update worker status
STATUS_FILE="$IPC_PATH/tasks/$WORKER_ID/status.json"
echo "{\"status\": \"busy\", \"role\": \"$WORKER_ROLE\", \"current_task\": \"$TASK_ID\", \"started_at\": \"$(date -Iseconds)\"}" > "$STATUS_FILE"

# Log task start
echo "[$(date -Iseconds)] Task $TASK_ID started by Worker $WORKER_ID" >> "$IPC_PATH/activity.log"

# Check workspace health
if [ -d "/workspace" ]; then
    cd /workspace

    # Ensure git is configured
    if [ ! -f ~/.gitconfig ]; then
        git config --global user.email "clopus@localhost"
        git config --global user.name "CLOPUS Worker $WORKER_ID"
    fi
fi

exit 0
