#!/usr/bin/env bash
# =============================================================================
# Workspace Cleanup Tool
# =============================================================================
# Removes temporary files and build artifacts

set -euo pipefail

WORKSPACE="${1:-/workspace}"
DRY_RUN="${DRY_RUN:-false}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $*"; }

echo ""
echo "🧹 Cleaning Workspace"
echo "   Path: $WORKSPACE"
echo "   Mode: $([ "$DRY_RUN" = "true" ] && echo "Dry Run" || echo "Live")"
echo ""

FREED=0

cleanup() {
    local pattern="$1"
    local description="$2"

    local found=$(find "$WORKSPACE" -name "$pattern" -type d 2>/dev/null | wc -l)

    if [ "$found" -gt 0 ]; then
        local size=$(find "$WORKSPACE" -name "$pattern" -type d -exec du -sh {} + 2>/dev/null | awk '{sum += $1} END {print sum}')

        log_info "$description ($found found)"

        if [ "$DRY_RUN" = "true" ]; then
            find "$WORKSPACE" -name "$pattern" -type d 2>/dev/null | head -5
            [ "$found" -gt 5 ] && echo "  ... and $((found - 5)) more"
        else
            find "$WORKSPACE" -name "$pattern" -type d -exec rm -rf {} + 2>/dev/null || true
        fi
    fi
}

cleanup_files() {
    local pattern="$1"
    local description="$2"

    local found=$(find "$WORKSPACE" -name "$pattern" -type f 2>/dev/null | wc -l)

    if [ "$found" -gt 0 ]; then
        log_info "$description ($found files found)"

        if [ "$DRY_RUN" = "true" ]; then
            find "$WORKSPACE" -name "$pattern" -type f 2>/dev/null | head -5
        else
            find "$WORKSPACE" -name "$pattern" -type f -delete 2>/dev/null || true
        fi
    fi
}

# Calculate initial size
INITIAL_SIZE=$(du -sh "$WORKSPACE" 2>/dev/null | cut -f1)

# Node.js artifacts
cleanup "node_modules" "Node modules"
cleanup ".next" "Next.js build cache"
cleanup ".nuxt" "Nuxt.js build cache"
cleanup "dist" "Distribution folders"
cleanup ".turbo" "Turbo cache"

# Python artifacts
cleanup "__pycache__" "Python bytecode cache"
cleanup ".pytest_cache" "Pytest cache"
cleanup "*.egg-info" "Python egg info"
cleanup ".mypy_cache" "Mypy cache"
cleanup ".ruff_cache" "Ruff cache"
cleanup ".venv" "Python virtual environments"
cleanup "venv" "Python virtual environments"

# Build artifacts
cleanup "build" "Build directories"
cleanup "target" "Rust/Maven targets"
cleanup ".gradle" "Gradle cache"

# Test artifacts
cleanup "coverage" "Coverage reports"
cleanup "htmlcov" "HTML coverage reports"
cleanup ".coverage" "Coverage data"

# IDE/Editor
cleanup ".idea" "IntelliJ IDEA"

# Logs
cleanup_files "*.log" "Log files"
cleanup_files "*.log.*" "Rotated log files"

# Temporary files
cleanup_files "*.tmp" "Temporary files"
cleanup_files "*.bak" "Backup files"
cleanup_files "*.swp" "Vim swap files"
cleanup_files ".DS_Store" "macOS files"

# Docker
cleanup_files "*.tar" "Docker image tarballs"

# Calculate final size
FINAL_SIZE=$(du -sh "$WORKSPACE" 2>/dev/null | cut -f1)

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Cleanup Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Before: $INITIAL_SIZE"
echo "  After:  $FINAL_SIZE"
echo ""

if [ "$DRY_RUN" = "true" ]; then
    log_warning "This was a dry run. No files were deleted."
    log_info "Run with DRY_RUN=false to actually clean."
else
    log_success "Cleanup complete!"
fi
