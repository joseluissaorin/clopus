#!/bin/bash
# =============================================================================
# CLOPUS Worker Memory Sync Hook
# =============================================================================
# Syncs worker learnings to the memory system

set -e

WORKER_ID=${WORKER_ID:-1}
IPC_PATH=${IPC_PATH:-/app/ipc}
CHROMADB_HOST=${CHROMADB_HOST:-chromadb}
CHROMADB_PORT=${CHROMADB_PORT:-8000}

echo "[Hook] Memory sync for Worker $WORKER_ID"

# Check if there are learnings to sync
LEARNINGS_FILE="$IPC_PATH/learnings.jsonl"

if [ ! -f "$LEARNINGS_FILE" ]; then
    echo "[Hook] No learnings to sync"
    exit 0
fi

# Count learnings
LEARNING_COUNT=$(wc -l < "$LEARNINGS_FILE" 2>/dev/null || echo "0")

if [ "$LEARNING_COUNT" -eq 0 ]; then
    echo "[Hook] No learnings to sync"
    exit 0
fi

echo "[Hook] Syncing $LEARNING_COUNT learnings..."

# Process learnings via Python script
python3 << 'EOF'
import json
import os
import sys

learnings_file = os.environ.get('LEARNINGS_FILE', '/app/ipc/learnings.jsonl')
chromadb_host = os.environ.get('CHROMADB_HOST', 'chromadb')
chromadb_port = int(os.environ.get('CHROMADB_PORT', 8000))

try:
    import chromadb

    client = chromadb.HttpClient(host=chromadb_host, port=chromadb_port)
    collection = client.get_or_create_collection("clopus_learnings")

    with open(learnings_file, 'r') as f:
        for line in f:
            try:
                learning = json.loads(line.strip())

                # Store in ChromaDB
                collection.add(
                    ids=[learning.get('task_id', 'unknown')],
                    documents=[json.dumps(learning)],
                    metadatas=[{
                        'worker_id': str(learning.get('worker_id')),
                        'role': learning.get('role', 'unknown')
                    }]
                )
            except json.JSONDecodeError:
                continue

    # Clear learnings file after sync
    open(learnings_file, 'w').close()
    print("[Hook] Learnings synced successfully")

except ImportError:
    print("[Hook] ChromaDB not available, skipping sync")
except Exception as e:
    print(f"[Hook] Sync error: {e}")
    sys.exit(1)
EOF

echo "[Hook] Memory sync complete"
exit 0
