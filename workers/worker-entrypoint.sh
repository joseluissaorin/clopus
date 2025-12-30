#!/bin/bash
set -e

# =============================================================================
# CLOPUS Worker Entrypoint v3.2
# =============================================================================
# Features:
# - Full Claude Code session handling (--continue, --resume, --output-format json)
# - Worker-specific model selection
# - Session persistence across restarts
# - Proper hook and skill integration
# =============================================================================

# Ensure HOME is set correctly for non-root user
export HOME=/home/ubuntu

WORKER_ID=${WORKER_ID:-1}
WORKER_ROLE=${WORKER_ROLE:-coder}
IPC_PATH=${IPC_PATH:-/app/ipc}
AUTH_MODE=${AUTH_MODE:-oauth}
CLAUDE_CONFIG_PATH=${CLAUDE_CONFIG_PATH:-/app/claude-config}

# MCP configuration
export MCP_TIMEOUT=${MCP_TIMEOUT:-15000}
export MAX_MCP_OUTPUT_TOKENS=${MAX_MCP_OUTPUT_TOKENS:-50000}

# Session handling configuration
SESSION_DIR="$HOME/.claude/projects"
WORKER_SESSION_FILE="$IPC_PATH/tasks/$WORKER_ID/session.json"

echo "[Worker $WORKER_ID] Starting as $WORKER_ROLE (Claude Code v3.2)..."

# =============================================================================
# Claude Code Configuration Setup
# =============================================================================

CLAUDE_HOME="$HOME/.claude"
mkdir -p "$CLAUDE_HOME"
mkdir -p "$SESSION_DIR"

# Ensure projects directory has correct permissions (may be created by root during volume mount)
if [ -d "$CLAUDE_HOME/projects" ]; then
    # Check if we own the directory, if not it might be from a volume mount
    if [ ! -w "$CLAUDE_HOME/projects" ]; then
        echo "[Worker $WORKER_ID] Fixing projects directory permissions..."
        # If we can't write, try to create a new directory (will be owned by current user)
        rm -rf "$CLAUDE_HOME/projects" 2>/dev/null || true
        mkdir -p "$CLAUDE_HOME/projects"
    fi
else
    mkdir -p "$CLAUDE_HOME/projects"
fi

# Ensure workspace directory and subdirectories have correct permissions
# This fixes the recurring permission issues with root-owned files in /workspace
if [ -d "/workspace" ]; then
    # Try to fix permissions on .clopus and .shared directories
    for dir in "/workspace/.clopus" "/workspace/.shared"; do
        if [ -d "$dir" ] && [ ! -w "$dir" ]; then
            echo "[Worker $WORKER_ID] Fixing workspace subdirectory permissions: $dir"
            # Try to take ownership if we have sudo (we won't, but try anyway)
            sudo chown -R ubuntu:ubuntu "$dir" 2>/dev/null || true
        fi
    done

    # Ensure we can write to workspace
    if [ ! -w "/workspace" ]; then
        echo "[Worker $WORKER_ID] Warning: /workspace is not writable"
    fi
fi

# Set up worker-specific configuration from mounted config
setup_claude_config() {
    local role=$1

    # Copy base settings if exists
    if [ -f "$CLAUDE_CONFIG_PATH/settings.json" ]; then
        cp "$CLAUDE_CONFIG_PATH/settings.json" "$CLAUDE_HOME/settings.json"
    fi

    # Override with role-specific settings if exists
    if [ -f "$CLAUDE_CONFIG_PATH/settings.$role.json" ]; then
        cp "$CLAUDE_CONFIG_PATH/settings.$role.json" "$CLAUDE_HOME/settings.json"
    fi

    # Set up model - all workers use Opus for maximum capability
    export CLAUDE_MODEL="${CLAUDE_MODEL:-opus}"

    # Link hooks directory
    if [ -d "$CLAUDE_CONFIG_PATH/hooks" ]; then
        mkdir -p "$CLAUDE_HOME/hooks"
        for hook in "$CLAUDE_CONFIG_PATH/hooks"/*; do
            if [ -f "$hook" ]; then
                hook_name=$(basename "$hook")
                cp "$hook" "$CLAUDE_HOME/hooks/$hook_name"
                chmod +x "$CLAUDE_HOME/hooks/$hook_name" 2>/dev/null || true
            fi
        done
    fi

    # Link commands directory for slash commands
    if [ -d "$CLAUDE_CONFIG_PATH/commands" ]; then
        mkdir -p "$CLAUDE_HOME/commands"
        cp -r "$CLAUDE_CONFIG_PATH/commands/"* "$CLAUDE_HOME/commands/" 2>/dev/null || true
    fi

    echo "[Worker $WORKER_ID] Claude Code config loaded for role: $role (model: $CLAUDE_MODEL)"
}

# =============================================================================
# Authentication Setup with Auto-Sync
# =============================================================================

HOST_CREDS="/home/ubuntu/.claude-host/.credentials.json"
LOCAL_CREDS="$CLAUDE_HOME/.credentials.json"
CREDS_STATUS_FILE="$IPC_PATH/tasks/$WORKER_ID/credentials_status.json"

# Function to get token expiration time in hours
get_token_expiry_hours() {
    local creds_file=$1
    if [ -f "$creds_file" ]; then
        python3 -c "
import json, sys, time
try:
    with open('$creds_file') as f:
        d = json.load(f)
    expires_at = d.get('claudeAiOauth', {}).get('expiresAt', 0)
    if expires_at > 0:
        hours_left = (expires_at/1000 - time.time()) / 3600
        print(f'{hours_left:.2f}')
    else:
        print('-999')
except:
    print('-999')
" 2>/dev/null || echo "-999"
    else
        echo "-999"
    fi
}

# Function to sync credentials from host if needed
sync_credentials_from_host() {
    local force=${1:-false}

    if [ ! -f "$HOST_CREDS" ]; then
        echo "[Worker $WORKER_ID] No host credentials available at $HOST_CREDS"
        return 1
    fi

    local host_expiry=$(get_token_expiry_hours "$HOST_CREDS")
    local local_expiry=$(get_token_expiry_hours "$LOCAL_CREDS")

    # Sync if:
    # 1. Force flag is set
    # 2. Local credentials don't exist
    # 3. Local token is expired or expiring soon (< 1 hour)
    # 4. Host token is newer (more hours remaining)

    local should_sync=false
    local reason=""

    if [ "$force" = "true" ]; then
        should_sync=true
        reason="forced sync"
    elif [ ! -f "$LOCAL_CREDS" ]; then
        should_sync=true
        reason="no local credentials"
    elif [ "$(echo "$local_expiry < 1" | bc -l 2>/dev/null || echo 0)" = "1" ]; then
        should_sync=true
        reason="local token expired or expiring soon (${local_expiry}h remaining)"
    elif [ "$(echo "$host_expiry > $local_expiry + 0.5" | bc -l 2>/dev/null || echo 0)" = "1" ]; then
        should_sync=true
        reason="host token is fresher (host: ${host_expiry}h, local: ${local_expiry}h)"
    fi

    if [ "$should_sync" = "true" ]; then
        echo "[Worker $WORKER_ID] Syncing credentials from host: $reason"
        cp "$HOST_CREDS" "$LOCAL_CREDS" 2>/dev/null || true
        chmod 600 "$LOCAL_CREDS" 2>/dev/null || true
        local_expiry=$(get_token_expiry_hours "$LOCAL_CREDS")
        echo "[Worker $WORKER_ID] Token synced, expires in ${local_expiry} hours"
    fi

    # Write credentials status for orchestrator monitoring
    mkdir -p "$(dirname "$CREDS_STATUS_FILE")"
    python3 -c "
import json, time
status = {
    'worker_id': $WORKER_ID,
    'token_expires_hours': $local_expiry,
    'last_sync': time.strftime('%Y-%m-%dT%H:%M:%S'),
    'synced_from_host': '$should_sync' == 'true'
}
with open('$CREDS_STATUS_FILE', 'w') as f:
    json.dump(status, f)
" 2>/dev/null || true

    return 0
}

# Initial credential sync
if [ -d "/home/ubuntu/.claude-host" ] && [ -f "$HOST_CREDS" ]; then
    echo "[Worker $WORKER_ID] Host credentials mounted, syncing..."
    sync_credentials_from_host true
elif [ -n "$CLAUDE_OAUTH_TOKEN" ]; then
    echo "[Worker $WORKER_ID] Using OAuth token from environment..."
    mkdir -p "$CLAUDE_HOME"
    cat > "$LOCAL_CREDS" << CREDS
{
  "claudeAiOauth": {
    "accessToken": "$CLAUDE_OAUTH_TOKEN",
    "expiresAt": 9999999999999
  }
}
CREDS
    chmod 600 "$LOCAL_CREDS"
elif [ -n "$ANTHROPIC_API_KEY" ]; then
    echo "[Worker $WORKER_ID] Using API key..."
    export ANTHROPIC_API_KEY
else
    echo "[Worker $WORKER_ID] WARNING: No authentication configured!"
    echo "[Worker $WORKER_ID] Set CLAUDE_OAUTH_TOKEN, mount ~/.claude, or set ANTHROPIC_API_KEY"
fi

# Apply role-specific Claude Code configuration
setup_claude_config "$WORKER_ROLE"

# =============================================================================
# Native Claude Code Skills Setup
# =============================================================================

SKILLS_DIR="$HOME/.claude/skills"
SKILLS_SOURCE="/app/skills"

mkdir -p "$SKILLS_DIR"

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
        designer)
            categories="design development"
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
                    if [ ! -e "$SKILLS_DIR/$skill_name" ]; then
                        ln -sf "$skill_dir" "$SKILLS_DIR/$skill_name"
                    fi
                fi
            done
        fi
    done

    # Also link skills from mounted config
    if [ -d "$CLAUDE_CONFIG_PATH/skills" ]; then
        for skill_dir in "$CLAUDE_CONFIG_PATH/skills"/*; do
            if [ -d "$skill_dir" ] && [ -f "$skill_dir/SKILL.md" ]; then
                skill_name=$(basename "$skill_dir")
                if [ ! -e "$SKILLS_DIR/$skill_name" ]; then
                    ln -sf "$skill_dir" "$SKILLS_DIR/$skill_name"
                fi
            fi
        done
    fi
}

setup_skills_for_role "$WORKER_ROLE"

SKILL_COUNT=$(find "$SKILLS_DIR" -maxdepth 1 -type l 2>/dev/null | wc -l)
echo "[Worker $WORKER_ID] Skills configured: $SKILL_COUNT skills for role $WORKER_ROLE"

# =============================================================================
# IPC Directory Setup
# =============================================================================

mkdir -p "$IPC_PATH/tasks/$WORKER_ID"

# Collaboration IPC directories (inter-worker communication)
mkdir -p "$IPC_PATH/collaboration/requests"
mkdir -p "$IPC_PATH/collaboration/responses"
mkdir -p "$IPC_PATH/collaboration/events"
mkdir -p "$IPC_PATH/collaboration/screenshots"
mkdir -p "$IPC_PATH/memory/shared"

echo "[Worker $WORKER_ID] IPC directories ready"

# =============================================================================
# Session Management Functions
# =============================================================================

# Get or create session ID for a project
get_session_id() {
    local project_path=$1
    local session_file="$SESSION_DIR/$WORKER_ID-$(echo "$project_path" | md5sum | cut -d' ' -f1).session"

    if [ -f "$session_file" ]; then
        cat "$session_file"
    else
        echo ""
    fi
}

# Save session ID for a project
save_session_id() {
    local project_path=$1
    local session_id=$2
    local session_file="$SESSION_DIR/$WORKER_ID-$(echo "$project_path" | md5sum | cut -d' ' -f1).session"

    echo "$session_id" > "$session_file"
    echo "[Worker $WORKER_ID] Session saved: $session_id for $project_path"
}

# Extract session ID from Claude Code JSON output
extract_session_id() {
    local output=$1
    echo "$output" | jq -r '.session_id // empty' 2>/dev/null || echo ""
}

# Extract result content from Claude Code JSON output
extract_result() {
    local output=$1
    # Try to get the result field, fall back to full output
    local result=$(echo "$output" | jq -r '.result // empty' 2>/dev/null)
    if [ -z "$result" ]; then
        # If no result field, return the raw output
        echo "$output"
    else
        echo "$result"
    fi
}

# =============================================================================
# Initialize Status
# =============================================================================

STARTED_AT=$(date -Iseconds)
echo "{\"status\": \"idle\", \"role\": \"$WORKER_ROLE\", \"model\": \"$CLAUDE_MODEL\", \"started_at\": \"$STARTED_AT\", \"updated_at\": \"$STARTED_AT\", \"session_enabled\": true}" > "$IPC_PATH/tasks/$WORKER_ID/status.json"

# =============================================================================
# Main Task Loop
# =============================================================================

HEARTBEAT_INTERVAL=5
CREDS_CHECK_INTERVAL=300  # Check credentials every 5 minutes
LAST_HEARTBEAT=0
LAST_CREDS_CHECK=0

while true; do
    PENDING_FILE="$IPC_PATH/tasks/$WORKER_ID/pending.json"
    CURRENT_TIME=$(date +%s)

    # Update heartbeat periodically when idle
    if [ $((CURRENT_TIME - LAST_HEARTBEAT)) -ge $HEARTBEAT_INTERVAL ]; then
        echo "{\"status\": \"idle\", \"role\": \"$WORKER_ROLE\", \"model\": \"$CLAUDE_MODEL\", \"updated_at\": \"$(date -Iseconds)\", \"started_at\": \"$STARTED_AT\", \"session_enabled\": true}" > "$IPC_PATH/tasks/$WORKER_ID/status.json"
        LAST_HEARTBEAT=$CURRENT_TIME
    fi

    # Periodic credential sync check (every 5 minutes)
    if [ $((CURRENT_TIME - LAST_CREDS_CHECK)) -ge $CREDS_CHECK_INTERVAL ]; then
        sync_credentials_from_host false
        LAST_CREDS_CHECK=$CURRENT_TIME
    fi

    if [ -f "$PENDING_FILE" ]; then
        echo "[Worker $WORKER_ID] Found pending task..."

        # Update status to busy
        echo "{\"status\": \"busy\", \"role\": \"$WORKER_ROLE\", \"model\": \"$CLAUDE_MODEL\", \"task_started\": \"$(date -Iseconds)\", \"updated_at\": \"$(date -Iseconds)\"}" > "$IPC_PATH/tasks/$WORKER_ID/status.json"

        # Read task
        TASK=$(cat "$PENDING_FILE")
        TASK_ID=$(echo "$TASK" | jq -r '.task_id')

        # Write acknowledgment IMMEDIATELY so orchestrator knows we have the task
        echo "{\"task_id\": \"$TASK_ID\", \"acknowledged_at\": \"$(date -Iseconds)\"}" > "$IPC_PATH/tasks/$WORKER_ID/ack.json"
        echo "[Worker $WORKER_ID] Acknowledged task $TASK_ID"

        TASK_PROMPT=$(echo "$TASK" | jq -r '.prompt')
        TASK_CWD=$(echo "$TASK" | jq -r '.cwd // "/workspace"')
        TASK_SESSION_MODE=$(echo "$TASK" | jq -r '.session_mode // "auto"')
        TASK_RESUME_SESSION=$(echo "$TASK" | jq -r '.resume_session // empty')

        echo "[Worker $WORKER_ID] Executing task $TASK_ID in $TASK_CWD..."

        # Load role-specific system prompt
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

        # Change to task directory (with fallback if directory doesn't exist)
        if [ -d "$TASK_CWD" ]; then
            cd "$TASK_CWD"
        elif [ "$TASK_CWD" = "/workspace" ]; then
            cd /workspace
        else
            echo "[Worker $WORKER_ID] Warning: Directory $TASK_CWD does not exist, using /workspace"
            # Try to create the directory if it looks like a project path
            if [[ "$TASK_CWD" == /workspace/* ]]; then
                mkdir -p "$TASK_CWD" 2>/dev/null || true
                if [ -d "$TASK_CWD" ]; then
                    cd "$TASK_CWD"
                else
                    cd /workspace
                fi
            else
                cd /workspace
            fi
        fi

        # Start background heartbeat
        (
            while true; do
                sleep 5
                echo "{\"status\": \"busy\", \"role\": \"$WORKER_ROLE\", \"model\": \"$CLAUDE_MODEL\", \"task_id\": \"$TASK_ID\", \"task_started\": \"$(date -Iseconds)\", \"updated_at\": \"$(date -Iseconds)\"}" > "$IPC_PATH/tasks/$WORKER_ID/status.json"
            done
        ) &
        HEARTBEAT_PID=$!

        # Build full prompt with system context
        FULL_PROMPT="[ROLE: $WORKER_ROLE Worker]

$SYSTEM_PROMPT

---
TASK:
$TASK_PROMPT"

        # =============================================================================
        # Claude Code Execution with Session Handling
        # =============================================================================

        CLAUDE_ARGS=("--output-format" "json" "--dangerously-skip-permissions")

        # Determine session mode
        if [ -n "$TASK_RESUME_SESSION" ]; then
            # Resume specific session
            CLAUDE_ARGS+=("--resume" "$TASK_RESUME_SESSION")
            echo "[Worker $WORKER_ID] Resuming session: $TASK_RESUME_SESSION"
        elif [ "$TASK_SESSION_MODE" = "continue" ]; then
            # Continue in current project session
            EXISTING_SESSION=$(get_session_id "$TASK_CWD")
            if [ -n "$EXISTING_SESSION" ]; then
                CLAUDE_ARGS+=("--continue")
                echo "[Worker $WORKER_ID] Continuing session for $TASK_CWD"
            fi
        fi

        # Execute Claude Code - capture both output and exit code
        # Use timeout to prevent tasks from running indefinitely (default: 30 minutes)
        TASK_TIMEOUT=${TASK_TIMEOUT:-1800}
        RAW_OUTPUT=$(timeout $TASK_TIMEOUT claude "${CLAUDE_ARGS[@]}" "$FULL_PROMPT" 2>&1) || true
        CLAUDE_EXIT_CODE=$?

        # Check if timeout occurred (exit code 124)
        if [ $CLAUDE_EXIT_CODE -eq 124 ]; then
            echo "[Worker $WORKER_ID] WARNING: Task timed out after ${TASK_TIMEOUT}s"
            RAW_OUTPUT='{"error": "timeout", "message": "Task execution timed out after '"$TASK_TIMEOUT"' seconds"}'
        fi

        # Only replace with error if output is empty AND looks like an error occurred
        if [ -z "$RAW_OUTPUT" ]; then
            RAW_OUTPUT="{\"error\": \"no_output\", \"message\": \"Claude Code produced no output\"}"
        elif echo "$RAW_OUTPUT" | grep -q '"error"'; then
            # Output already contains error, pass through
            echo "[Worker $WORKER_ID] Claude returned error in output"
        fi

        # Parse output
        SESSION_ID=$(extract_session_id "$RAW_OUTPUT")
        RESULT=$(extract_result "$RAW_OUTPUT")

        # Save session ID for future continuations
        if [ -n "$SESSION_ID" ]; then
            save_session_id "$TASK_CWD" "$SESSION_ID"
            # Also save to task-specific IPC
            echo "{\"session_id\": \"$SESSION_ID\", \"worker_id\": \"$WORKER_ID\", \"project\": \"$TASK_CWD\"}" > "$WORKER_SESSION_FILE"
        else
            # Log warning when no session ID - helps debug stuck/failed tasks
            echo "[Worker $WORKER_ID] WARNING: No session ID returned for task $TASK_ID"
            # Log first 500 chars of output for debugging
            echo "[Worker $WORKER_ID] Raw output (first 500 chars): $(echo "$RAW_OUTPUT" | head -c 500)"
        fi

        # Stop background heartbeat
        kill $HEARTBEAT_PID 2>/dev/null || true

        # Write result with session info
        RESULT_JSON=$(jq -n \
            --arg task_id "$TASK_ID" \
            --arg status "completed" \
            --arg result "$RESULT" \
            --arg session_id "$SESSION_ID" \
            --arg completed_at "$(date -Iseconds)" \
            '{task_id: $task_id, status: $status, result: $result, session_id: $session_id, completed_at: $completed_at}')

        echo "$RESULT_JSON" > "$IPC_PATH/tasks/$WORKER_ID/result.json"

        # Remove pending task (use -f to avoid failure if already removed)
        rm -f "$PENDING_FILE"

        # Update status to idle
        echo "{\"status\": \"idle\", \"role\": \"$WORKER_ROLE\", \"model\": \"$CLAUDE_MODEL\", \"last_task\": \"$TASK_ID\", \"last_session\": \"$SESSION_ID\", \"updated_at\": \"$(date -Iseconds)\", \"started_at\": \"$STARTED_AT\"}" > "$IPC_PATH/tasks/$WORKER_ID/status.json"
        LAST_HEARTBEAT=$CURRENT_TIME

        echo "[Worker $WORKER_ID] Task $TASK_ID completed (session: ${SESSION_ID:-none})."
    fi

    # Poll interval
    sleep 0.5
done
