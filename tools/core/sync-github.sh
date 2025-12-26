#!/usr/bin/env bash
# =============================================================================
# GitHub Sync Tool
# =============================================================================
# Syncs skills, templates, MCPs, and knowledge to GitHub

set -euo pipefail

CLOPUS_DIR="${CLOPUS_DIR:-/app}"
COMMIT_MSG="${1:-chore: sync CLOPUS assets}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

cd "$CLOPUS_DIR"

echo ""
echo "🔄 Syncing CLOPUS Assets to GitHub"
echo ""

# Check if there are changes
if git diff --quiet && git diff --cached --quiet; then
    log_info "No changes to sync"
    exit 0
fi

# Sync generated skills
if [ -d "skills/generated" ] && [ "$(ls -A skills/generated 2>/dev/null)" ]; then
    log_info "Syncing generated skills..."
    git add skills/generated/
fi

# Sync extracted templates
if [ -d "templates/extracted" ] && [ "$(ls -A templates/extracted 2>/dev/null)" ]; then
    log_info "Syncing extracted templates..."
    git add templates/extracted/
fi

# Sync generated MCPs
if [ -d "mcp-servers/generated" ] && [ "$(ls -A mcp-servers/generated 2>/dev/null)" ]; then
    log_info "Syncing generated MCPs..."
    git add mcp-servers/generated/
fi

# Sync generated tools
if [ -d "tools/generated" ] && [ "$(ls -A tools/generated 2>/dev/null)" ]; then
    log_info "Syncing generated tools..."
    git add tools/generated/
fi

# Sync knowledge base
if [ -d "knowledge" ]; then
    log_info "Syncing knowledge base..."
    git add knowledge/
fi

# Check if anything was staged
if git diff --cached --quiet; then
    log_info "No new assets to sync"
    exit 0
fi

# Commit
log_info "Committing changes..."
git commit -m "$COMMIT_MSG

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: CLOPUS <noreply@anthropic.com>"

# Push
log_info "Pushing to remote..."
if git push; then
    log_success "Sync complete!"
else
    log_error "Push failed. Please push manually."
    exit 1
fi

# Show what was synced
echo ""
echo "Synced assets:"
git diff --name-only HEAD~1
