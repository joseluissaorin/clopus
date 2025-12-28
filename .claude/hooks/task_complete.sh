#!/bin/bash
# =============================================================================
# CLOPUS Task Complete Hook
# =============================================================================
# Called when Claude Code finishes responding. Finalizes task state.

WORKER_ID="${CLOPUS_WORKER_ID:-${WORKER_ID:-0}}"
TASK_ID="${CLOPUS_CURRENT_TASK:-none}"

# Log task completion
echo "[CLOPUS] Response complete for worker $WORKER_ID, task $TASK_ID at $(date -Iseconds)" >> /tmp/clopus_worker_$WORKER_ID.log

# Calculate session duration if start time is set
if [ -n "$CLOPUS_SESSION_START" ]; then
    DURATION=$(($(date +%s) - CLOPUS_SESSION_START))
    echo "[CLOPUS] Session duration: ${DURATION}s" >> /tmp/clopus_worker_$WORKER_ID.log
fi

# Write completion marker to IPC if task is active
if [ "$TASK_ID" != "none" ] && [ -d "/app/ipc/tasks/$WORKER_ID" ]; then
    echo "{\"event\": \"response_complete\", \"task_id\": \"$TASK_ID\", \"timestamp\": \"$(date -Iseconds)\"}" > "/app/ipc/tasks/$WORKER_ID/response_complete.json"
fi

exit 0
