---
allowed-tools: Bash, Read
description: Report current worker status to the orchestrator
---

# Report Worker Status

## Current Task

!`cat /app/ipc/tasks/${WORKER_ID:-0}/pending.json 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Task: {d.get(\"task_id\", \"none\")}'); print(f'Title: {d.get(\"title\", \"unknown\")}')" 2>/dev/null || echo "No active task"`

## Recent Operations

!`tail -5 /tmp/clopus_worker_${WORKER_ID:-0}_operations.jsonl 2>/dev/null || echo "No operations logged yet"`

## Session Info

- Worker ID: ${WORKER_ID:-0}
- Session Start: ${CLOPUS_SESSION_START:-unknown}
- Current Task: ${CLOPUS_CURRENT_TASK:-none}

Status report complete.
