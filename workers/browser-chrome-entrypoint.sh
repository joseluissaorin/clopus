#!/bin/bash
# =============================================================================
# CLOPUS Chrome Browser Worker Entrypoint
# =============================================================================
# Starts VNC, Chrome, and Claude Code worker loop

set -e

echo "[Chrome Worker $WORKER_ID] Starting..."

# =============================================================================
# Configuration
# =============================================================================
IPC_DIR="${IPC_PATH:-/app/ipc}/tasks/$WORKER_ID"
PENDING_FILE="$IPC_DIR/pending.json"
RESULT_FILE="$IPC_DIR/result.json"
ACK_FILE="$IPC_DIR/ack.json"
CANCEL_FILE="$IPC_DIR/cancel"
SYSTEM_PROMPT_FILE="/app/system-prompts/browser.md"

mkdir -p "$IPC_DIR"

# =============================================================================
# Start Virtual Display (Xvfb)
# =============================================================================
echo "[Chrome Worker $WORKER_ID] Starting Xvfb on display :99..."

# Clean up stale X server lock files from previous runs
rm -f /tmp/.X99-lock /tmp/.X11-unix/X99 2>/dev/null || true

Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99
sleep 2

# =============================================================================
# Start Window Manager (Fluxbox)
# =============================================================================
echo "[Chrome Worker $WORKER_ID] Starting Fluxbox window manager..."
fluxbox &
sleep 1

# =============================================================================
# Start VNC Server
# =============================================================================
echo "[Chrome Worker $WORKER_ID] Starting x11vnc server..."
x11vnc -display :99 -forever -shared -rfbport 5900 -bg -o /tmp/x11vnc.log
sleep 1

# =============================================================================
# Start noVNC (Web-based VNC)
# =============================================================================
echo "[Chrome Worker $WORKER_ID] Starting noVNC on port 6080..."
/usr/share/novnc/utils/novnc_proxy --vnc localhost:5900 --listen 6080 &
sleep 1

echo "[Chrome Worker $WORKER_ID] VNC ready at :5900, noVNC ready at :6080"

# =============================================================================
# Claude Code Authentication
# =============================================================================
echo "[Chrome Worker $WORKER_ID] Setting up Claude Code authentication..."

# Check for OAuth token file (from host mount)
if [ -f "/home/ubuntu/.claude-host/.credentials" ]; then
    mkdir -p ~/.claude
    cp -r /home/ubuntu/.claude-host/* ~/.claude/ 2>/dev/null || true
    echo "[Chrome Worker $WORKER_ID] Claude credentials copied from host"
elif [ -n "$CLAUDE_OAUTH_TOKEN" ]; then
    echo "[Chrome Worker $WORKER_ID] Using OAuth token from environment"
fi

# =============================================================================
# Task Polling Loop
# =============================================================================
echo "[Chrome Worker $WORKER_ID] Starting task polling loop..."

while true; do
    # Check for pending task
    if [ -f "$PENDING_FILE" ]; then
        echo "[Chrome Worker $WORKER_ID] Found pending task..."

        # Read task data
        TASK_ID=$(jq -r '.task_id' "$PENDING_FILE")
        PROMPT=$(jq -r '.prompt' "$PENDING_FILE")
        CWD=$(jq -r '.cwd // "/workspace"' "$PENDING_FILE")

        echo "[Chrome Worker $WORKER_ID] Processing task: $TASK_ID"

        # Acknowledge the task
        echo "{\"task_id\": \"$TASK_ID\", \"acknowledged_at\": \"$(date -Iseconds)\"}" > "$ACK_FILE"
        echo "[Chrome Worker $WORKER_ID] Task acknowledged"

        # Remove pending file
        rm -f "$PENDING_FILE"

        # Build Claude Code command with system prompt
        SYSTEM_PROMPT=""
        if [ -f "$SYSTEM_PROMPT_FILE" ]; then
            SYSTEM_PROMPT="--system-prompt $SYSTEM_PROMPT_FILE"
        fi

        # Execute Claude Code
        cd "$CWD"
        echo "[Chrome Worker $WORKER_ID] Executing Claude Code in $CWD..."

        # Run Claude Code and capture output
        OUTPUT=$(claude --print "$PROMPT" $SYSTEM_PROMPT 2>&1) || true
        EXIT_CODE=$?

        # Check if cancelled during execution
        if [ -f "$CANCEL_FILE" ]; then
            echo "[Chrome Worker $WORKER_ID] Task was cancelled"
            rm -f "$CANCEL_FILE"
            echo "{\"task_id\": \"$TASK_ID\", \"success\": false, \"error\": \"Task cancelled\", \"output\": \"\"}" > "$RESULT_FILE"
        elif [ $EXIT_CODE -eq 0 ]; then
            echo "[Chrome Worker $WORKER_ID] Task completed successfully"
            # Escape output for JSON
            ESCAPED_OUTPUT=$(echo "$OUTPUT" | jq -Rs .)
            echo "{\"task_id\": \"$TASK_ID\", \"success\": true, \"output\": $ESCAPED_OUTPUT}" > "$RESULT_FILE"
        else
            echo "[Chrome Worker $WORKER_ID] Task failed with exit code $EXIT_CODE"
            ESCAPED_OUTPUT=$(echo "$OUTPUT" | jq -Rs .)
            echo "{\"task_id\": \"$TASK_ID\", \"success\": false, \"error\": \"Exit code $EXIT_CODE\", \"output\": $ESCAPED_OUTPUT}" > "$RESULT_FILE"
        fi

        # Clean up ack file
        rm -f "$ACK_FILE"
    fi

    # Poll interval (500ms)
    sleep 0.5
done
