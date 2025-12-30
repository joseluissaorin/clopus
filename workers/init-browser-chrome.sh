#!/bin/bash
# init-browser-chrome.sh - Run as root to fix volume permissions, then exec as ubuntu
# This script should be the container entrypoint for browser-chrome worker

set -e

# Fix ownership of directories that might be created by root during volume mount
echo "[Init Browser-Chrome] Fixing volume permissions..."

# Claude projects directory (mounted volume)
if [ -d "/home/ubuntu/.claude" ]; then
    chown -R ubuntu:ubuntu /home/ubuntu/.claude
fi

# Ensure the projects directory exists with correct ownership
mkdir -p /home/ubuntu/.claude/projects
chown -R ubuntu:ubuntu /home/ubuntu/.claude

# Chrome profile directory
if [ -d "/home/ubuntu/.config/google-chrome" ]; then
    chown -R ubuntu:ubuntu /home/ubuntu/.config/google-chrome
fi

# IPC directory
if [ -d "/app/ipc" ]; then
    chown -R ubuntu:ubuntu /app/ipc
fi

# Workspace directories
if [ -d "/workspace/.shared" ]; then
    chown -R ubuntu:ubuntu /workspace/.shared 2>/dev/null || true
fi

echo "[Init Browser-Chrome] Permissions fixed, starting browser worker as ubuntu..."

# Execute the main entrypoint as ubuntu user
exec su ubuntu -c "/app/browser-chrome-entrypoint.sh"
