#!/bin/bash
set -e

# Ensure HOME is set correctly for non-root user
export HOME=/home/ubuntu

WORKER_ID=${WORKER_ID:-1}
WORKER_ROLE=${WORKER_ROLE:-coder}
IPC_PATH=${IPC_PATH:-/app/ipc}
AUTH_MODE=${AUTH_MODE:-oauth}

# MCP configuration
export MCP_TIMEOUT=${MCP_TIMEOUT:-15000}
export MAX_MCP_OUTPUT_TOKENS=${MAX_MCP_OUTPUT_TOKENS:-50000}

echo "[Worker $WORKER_ID] Starting as $WORKER_ROLE..."

# Check for MCP configuration
if [ -f "/workspace/.mcp.json" ]; then
    echo "[Worker $WORKER_ID] MCP servers configured from .mcp.json"
fi

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

# =============================================================================
# Native Claude Code Skills Setup
# =============================================================================
# Claude Code auto-discovers skills from ~/.claude/skills/
# This enables progressive disclosure (metadata loaded first, content on-demand)

SKILLS_DIR="$HOME/.claude/skills"
SKILLS_SOURCE="/app/skills"

mkdir -p "$SKILLS_DIR"

# Set up skills based on worker role
setup_skills_for_role() {
    local role=$1
    local categories=""

    case $role in
        coder)
            categories="development testing"
            ;;
        tester)
            categories="testing development"
            ;;
        reviewer)
            categories="security testing"
            ;;
        researcher)
            categories="research data"
            ;;
        debugger)
            categories="development testing security"
            ;;
        deployer)
            categories="devops security"
            ;;
        *)
            categories="development testing"
            ;;
    esac

    # Symlink skills by category
    for category in $categories; do
        if [ -d "$SKILLS_SOURCE/core/$category" ]; then
            for skill_dir in "$SKILLS_SOURCE/core/$category"/*; do
                if [ -d "$skill_dir" ] && [ -f "$skill_dir/SKILL.md" ]; then
                    skill_name=$(basename "$skill_dir")
                    # Symlink if not exists
                    if [ ! -e "$SKILLS_DIR/$skill_name" ]; then
                        ln -sf "$skill_dir" "$SKILLS_DIR/$skill_name"
                    fi
                fi
            done
        fi
    done
}

# Set up skills for this worker's role
setup_skills_for_role "$WORKER_ROLE"

# Count skills
SKILL_COUNT=$(find "$SKILLS_DIR" -maxdepth 1 -type l 2>/dev/null | wc -l)
echo "[Worker $WORKER_ID] Claude Code skills configured: $SKILL_COUNT skills for role $WORKER_ROLE"

# Create IPC directories for this worker
mkdir -p "$IPC_PATH/tasks/$WORKER_ID"

# =============================================================================
# Create Collaboration IPC Directories
# =============================================================================
# These directories enable inter-worker communication
mkdir -p "$IPC_PATH/collaboration/requests"
mkdir -p "$IPC_PATH/collaboration/responses"
mkdir -p "$IPC_PATH/collaboration/events"
mkdir -p "$IPC_PATH/collaboration/screenshots"
mkdir -p "$IPC_PATH/memory/shared"

echo "[Worker $WORKER_ID] Collaboration IPC directories ready"

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
            if [ -n "$SYSTEM_PROMPT" ]; then
                SYSTEM_PROMPT="$SYSTEM_PROMPT

---

$(cat $SYSTEM_PROMPT_FILE)"
            else
                SYSTEM_PROMPT=$(cat "$SYSTEM_PROMPT_FILE")
            fi
        fi

        echo "[Worker $WORKER_ID] Role: $WORKER_ROLE, System prompt loaded: $([[ -n "$SYSTEM_PROMPT" ]] && echo "yes" || echo "no")"

        # Run Claude Code
        cd "$TASK_CWD"

        # Write system prompt to file for Claude Code to use
        SYSTEM_PROMPT_TMP="$TASK_CWD/.claude_system_prompt_$WORKER_ID"
        if [ -n "$SYSTEM_PROMPT" ]; then
            echo "$SYSTEM_PROMPT" > "$SYSTEM_PROMPT_TMP"
        fi

        # Start background heartbeat while executing task
        (
            while true; do
                sleep 5
                echo '{"status": "busy", "role": "'$WORKER_ROLE'", "task_id": "'$TASK_ID'", "task_started": "'$(date -Iseconds)'", "updated_at": "'$(date -Iseconds)'"}' > "$IPC_PATH/tasks/$WORKER_ID/status.json"
            done
        ) &
        HEARTBEAT_PID=$!

        # Build prompt with system context prepended
        FULL_PROMPT="$TASK_PROMPT"
        if [ -n "$SYSTEM_PROMPT" ]; then
            # Prepend role-specific context to the task
            FULL_PROMPT="[ROLE: $WORKER_ROLE Worker]

$SYSTEM_PROMPT

---
TASK:
$TASK_PROMPT"
        fi

        # Execute Claude Code with the task (skip permissions for autonomous operation)
        RESULT=$(claude --print --dangerously-skip-permissions "$FULL_PROMPT" 2>&1) || RESULT="Error: $?"

        # Cleanup temp file
        rm -f "$SYSTEM_PROMPT_TMP" 2>/dev/null || true

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
