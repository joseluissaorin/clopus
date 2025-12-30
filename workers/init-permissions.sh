#!/bin/bash
# init-permissions.sh - Run as root to fix volume permissions, then exec as ubuntu
# This script should be the container entrypoint when user: root is set

set -e

# Fix ownership of directories that might be created by root during volume mount
echo "[Init] Fixing volume permissions..."

# Claude projects directory (mounted volume)
if [ -d "/home/ubuntu/.claude" ]; then
    chown -R ubuntu:ubuntu /home/ubuntu/.claude
fi

# Ensure the projects directory exists with correct ownership
mkdir -p /home/ubuntu/.claude/projects
chown -R ubuntu:ubuntu /home/ubuntu/.claude

# IPC directory
if [ -d "/app/ipc" ]; then
    chown -R ubuntu:ubuntu /app/ipc
fi

# Workspace shared directories
if [ -d "/workspace/.shared" ]; then
    chown -R ubuntu:ubuntu /workspace/.shared
fi
if [ -d "/workspace/.clopus" ]; then
    chown -R ubuntu:ubuntu /workspace/.clopus
fi

echo "[Init] Permissions fixed, starting worker as ubuntu..."

# Execute the main entrypoint as ubuntu user
exec su ubuntu -c "/app/worker-entrypoint.sh"
