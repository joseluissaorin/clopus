#!/bin/bash
set -e

# Ensure HOME is set correctly for non-root user
export HOME=/home/ubuntu

WORKER_ID=${WORKER_ID:-1}
WORKER_ROLE=${WORKER_ROLE:-coder}
IPC_PATH=${IPC_PATH:-/app/ipc}
AUTH_MODE=${AUTH_MODE:-oauth}

echo "[Worker $WORKER_ID] Starting as $WORKER_ROLE..."

# =============================================================================
# Authentication Setup
# =============================================================================

# Check if .claude directory is mounted (preferred for OAuth)
CLAUDE_HOME="$HOME/.claude"
if [ -d "/home/ubuntu/.claude-host" ] && [ -f "/home/ubuntu/.claude-host/.credentials.json" ]; then
    echo "[Worker $WORKER_ID] Using mounted OAuth credentials..."
    # Copy only essential auth files (not plugins which may have permission issues)
    mkdir -p "$CLAUDE_HOME"
    cp /home/ubuntu/.claude-host/.credentials.json "$CLAUDE_HOME/" 2>/dev/null || true
    [ -f /home/ubuntu/.claude-host/settings.json ] && cp /home/ubuntu/.claude-host/settings.json "$CLAUDE_HOME/" 2>/dev/null || true
    chmod 600 "$CLAUDE_HOME/.credentials.json" 2>/dev/null || true
elif [ -n "$CLAUDE_OAUTH_TOKEN" ]; then
    echo "[Worker $WORKER_ID] Using OAuth token from environment..."
    # Create credentials file from token
    mkdir -p "$CLAUDE_HOME"
    cat > "$CLAUDE_HOME/.credentials.json" << CREDS
{
  "claudeAiOauth": {
    "accessToken": "$CLAUDE_OAUTH_TOKEN",
    "expiresAt": 9999999999999
  }
}
CREDS
    chmod 600 "$CLAUDE_HOME/.credentials.json"
elif [ -n "$ANTHROPIC_API_KEY" ]; then
    echo "[Worker $WORKER_ID] Using API key..."
    export ANTHROPIC_API_KEY
else
    echo "[Worker $WORKER_ID] WARNING: No authentication configured!"
    echo "[Worker $WORKER_ID] Set CLAUDE_OAUTH_TOKEN, mount ~/.claude, or set ANTHROPIC_API_KEY"
fi

# Create IPC directories for this worker
mkdir -p "$IPC_PATH/tasks/$WORKER_ID"

# Initialize status
STARTED_AT=$(date -Iseconds)
echo '{"status": "idle", "role": "'$WORKER_ROLE'", "started_at": "'$STARTED_AT'", "updated_at": "'$STARTED_AT'"}' > "$IPC_PATH/tasks/$WORKER_ID/status.json"

# Main loop - poll for tasks
HEARTBEAT_INTERVAL=5
LAST_HEARTBEAT=0

while true; do
    PENDING_FILE="$IPC_PATH/tasks/$WORKER_ID/pending.json"
    CURRENT_TIME=$(date +%s)

    # Update heartbeat periodically when idle
    if [ $((CURRENT_TIME - LAST_HEARTBEAT)) -ge $HEARTBEAT_INTERVAL ]; then
        echo '{"status": "idle", "role": "'$WORKER_ROLE'", "updated_at": "'$(date -Iseconds)'", "started_at": "'$STARTED_AT'"}' > "$IPC_PATH/tasks/$WORKER_ID/status.json"
        LAST_HEARTBEAT=$CURRENT_TIME
    fi

    if [ -f "$PENDING_FILE" ]; then
        echo "[Worker $WORKER_ID] Found pending task..."

        # Update status to busy
        echo '{"status": "busy", "role": "'$WORKER_ROLE'", "task_started": "'$(date -Iseconds)'", "updated_at": "'$(date -Iseconds)'"}' > "$IPC_PATH/tasks/$WORKER_ID/status.json"

        # Read task
        TASK=$(cat "$PENDING_FILE")
        TASK_ID=$(echo "$TASK" | jq -r '.task_id')
        TASK_PROMPT=$(echo "$TASK" | jq -r '.prompt')
        TASK_CWD=$(echo "$TASK" | jq -r '.cwd // "/workspace"')

        echo "[Worker $WORKER_ID] Executing task $TASK_ID..."

        # Load role-specific system prompt if exists
        SYSTEM_PROMPT_FILE="/app/system-prompts/$WORKER_ROLE.md"
        BASE_PROMPT_FILE="/app/system-prompts/base.md"

        SYSTEM_PROMPT=""
        if [ -f "$BASE_PROMPT_FILE" ]; then
            SYSTEM_PROMPT=$(cat "$BASE_PROMPT_FILE")
        fi
        if [ -f "$SYSTEM_PROMPT_FILE" ]; then
            SYSTEM_PROMPT="$SYSTEM_PROMPT\n\n$(cat $SYSTEM_PROMPT_FILE)"
        fi

        # Run Claude Code
        cd "$TASK_CWD"

        # Start background heartbeat while executing task
        (
            while true; do
                sleep 5
                echo '{"status": "busy", "role": "'$WORKER_ROLE'", "task_id": "'$TASK_ID'", "task_started": "'$(date -Iseconds)'", "updated_at": "'$(date -Iseconds)'"}' > "$IPC_PATH/tasks/$WORKER_ID/status.json"
            done
        ) &
        HEARTBEAT_PID=$!

        # Execute Claude Code with the task (skip permissions for autonomous operation)
        RESULT=$(claude --print --dangerously-skip-permissions "$TASK_PROMPT" 2>&1) || RESULT="Error: $?"

        # Stop background heartbeat
        kill $HEARTBEAT_PID 2>/dev/null || true

        # Write result
        echo "{\"task_id\": \"$TASK_ID\", \"status\": \"completed\", \"result\": $(echo "$RESULT" | jq -Rs .), \"completed_at\": \"$(date -Iseconds)\"}" > "$IPC_PATH/tasks/$WORKER_ID/result.json"

        # Remove pending task
        rm "$PENDING_FILE"

        # Update status to idle
        echo '{"status": "idle", "role": "'$WORKER_ROLE'", "last_task": "'$TASK_ID'", "updated_at": "'$(date -Iseconds)'", "started_at": "'$STARTED_AT'"}' > "$IPC_PATH/tasks/$WORKER_ID/status.json"
        LAST_HEARTBEAT=$CURRENT_TIME

        echo "[Worker $WORKER_ID] Task $TASK_ID completed."
    fi

    # Poll interval
    sleep 0.5
done
