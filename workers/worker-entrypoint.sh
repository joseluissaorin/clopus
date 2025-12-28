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
# Authentication Setup
# =============================================================================

# Check if .claude directory is mounted (preferred for OAuth)
if [ -d "/home/ubuntu/.claude-host" ] && [ -f "/home/ubuntu/.claude-host/.credentials.json" ]; then
    echo "[Worker $WORKER_ID] Using mounted OAuth credentials..."
    cp /home/ubuntu/.claude-host/.credentials.json "$CLAUDE_HOME/" 2>/dev/null || true
    [ -f /home/ubuntu/.claude-host/settings.json ] && cp /home/ubuntu/.claude-host/settings.json "$CLAUDE_HOME/settings.json.base" 2>/dev/null || true
    chmod 600 "$CLAUDE_HOME/.credentials.json" 2>/dev/null || true
elif [ -n "$CLAUDE_OAUTH_TOKEN" ]; then
    echo "[Worker $WORKER_ID] Using OAuth token from environment..."
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
LAST_HEARTBEAT=0

while true; do
    PENDING_FILE="$IPC_PATH/tasks/$WORKER_ID/pending.json"
    CURRENT_TIME=$(date +%s)

    # Update heartbeat periodically when idle
    if [ $((CURRENT_TIME - LAST_HEARTBEAT)) -ge $HEARTBEAT_INTERVAL ]; then
        echo "{\"status\": \"idle\", \"role\": \"$WORKER_ROLE\", \"model\": \"$CLAUDE_MODEL\", \"updated_at\": \"$(date -Iseconds)\", \"started_at\": \"$STARTED_AT\", \"session_enabled\": true}" > "$IPC_PATH/tasks/$WORKER_ID/status.json"
        LAST_HEARTBEAT=$CURRENT_TIME
    fi

    if [ -f "$PENDING_FILE" ]; then
        echo "[Worker $WORKER_ID] Found pending task..."

        # Update status to busy
        echo "{\"status\": \"busy\", \"role\": \"$WORKER_ROLE\", \"model\": \"$CLAUDE_MODEL\", \"task_started\": \"$(date -Iseconds)\", \"updated_at\": \"$(date -Iseconds)\"}" > "$IPC_PATH/tasks/$WORKER_ID/status.json"

        # Read task
        TASK=$(cat "$PENDING_FILE")
        TASK_ID=$(echo "$TASK" | jq -r '.task_id')
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

        # Change to task directory
        cd "$TASK_CWD"

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

        # Execute Claude Code
        RAW_OUTPUT=$(claude "${CLAUDE_ARGS[@]}" "$FULL_PROMPT" 2>&1) || RAW_OUTPUT="{\"error\": \"$?\"}"

        # Parse output
        SESSION_ID=$(extract_session_id "$RAW_OUTPUT")
        RESULT=$(extract_result "$RAW_OUTPUT")

        # Save session ID for future continuations
        if [ -n "$SESSION_ID" ]; then
            save_session_id "$TASK_CWD" "$SESSION_ID"
            # Also save to task-specific IPC
            echo "{\"session_id\": \"$SESSION_ID\", \"worker_id\": \"$WORKER_ID\", \"project\": \"$TASK_CWD\"}" > "$WORKER_SESSION_FILE"
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

        # Remove pending task
        rm "$PENDING_FILE"

        # Update status to idle
        echo "{\"status\": \"idle\", \"role\": \"$WORKER_ROLE\", \"model\": \"$CLAUDE_MODEL\", \"last_task\": \"$TASK_ID\", \"last_session\": \"$SESSION_ID\", \"updated_at\": \"$(date -Iseconds)\", \"started_at\": \"$STARTED_AT\"}" > "$IPC_PATH/tasks/$WORKER_ID/status.json"
        LAST_HEARTBEAT=$CURRENT_TIME

        echo "[Worker $WORKER_ID] Task $TASK_ID completed (session: ${SESSION_ID:-none})."
    fi

    # Poll interval
    sleep 0.5
done
