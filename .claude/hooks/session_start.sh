#!/bin/bash
# =============================================================================
# CLOPUS Session Start Hook
# =============================================================================
# Called when a Claude Code session starts. Initializes worker context.

# Get worker ID from environment or hostname
WORKER_ID="${WORKER_ID:-$(hostname | grep -oP '\d+$' || echo '0')}"

# Log session start
echo "[CLOPUS] Session started for worker $WORKER_ID at $(date -Iseconds)" >> /tmp/clopus_worker_$WORKER_ID.log

# Set environment variables for the session
if [ -n "$CLAUDE_ENV_FILE" ]; then
    echo "export CLOPUS_WORKER_ID=$WORKER_ID" >> "$CLAUDE_ENV_FILE"
    echo "export CLOPUS_SESSION_START=$(date +%s)" >> "$CLAUDE_ENV_FILE"

    # Load any pending task context
    if [ -f "/app/ipc/tasks/$WORKER_ID/pending.json" ]; then
        TASK_ID=$(python3 -c "import json; print(json.load(open('/app/ipc/tasks/$WORKER_ID/pending.json')).get('task_id', ''))" 2>/dev/null)
        if [ -n "$TASK_ID" ]; then
            echo "export CLOPUS_CURRENT_TASK=$TASK_ID" >> "$CLAUDE_ENV_FILE"
        fi
    fi
fi

# Check if CLAUDE.md exists and load key context
if [ -f "/workspace/CLAUDE.md" ]; then
    # Extract project name from CLAUDE.md
    PROJECT_NAME=$(head -1 /workspace/CLAUDE.md | sed 's/^#\s*//')
    if [ -n "$CLAUDE_ENV_FILE" ] && [ -n "$PROJECT_NAME" ]; then
        echo "export CLOPUS_PROJECT_NAME='$PROJECT_NAME'" >> "$CLAUDE_ENV_FILE"
    fi
fi

exit 0
