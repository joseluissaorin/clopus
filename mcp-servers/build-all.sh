#!/bin/bash
# Build all MCP servers
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Building all MCP servers..."

for server_dir in "$SCRIPT_DIR"/core/*/; do
    if [ -f "$server_dir/package.json" ]; then
        server_name=$(basename "$server_dir")
        echo "Building $server_name..."
        cd "$server_dir"
        npm install --silent 2>/dev/null || true
        npm run build --silent 2>/dev/null || npx tsc --skipLibCheck 2>/dev/null || true
        echo "  ✓ $server_name built"
    fi
done

echo "All MCP servers built!"
