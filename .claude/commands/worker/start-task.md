---
allowed-tools: Bash, Read
description: Start working on a CLOPUS task from the orchestrator queue
argument-hint: [task-id]
---

# Start CLOPUS Task

Starting task: **$ARGUMENTS**

## Load Task Details

!`cat /app/ipc/tasks/${WORKER_ID:-0}/pending.json 2>/dev/null || echo '{"error": "No pending task found"}'`

## Check Project Context

!`cat /workspace/CLAUDE.md 2>/dev/null | head -50 || echo "No CLAUDE.md found - check project path"`

## Task Loaded

You are now working on this task. Please:

1. **Read the task description carefully**
2. **Check CLAUDE.md for project requirements**
3. **Plan your approach before implementing**
4. **Follow CLOPUS architectural patterns**
5. **Signal completion when done**

Begin implementation.
