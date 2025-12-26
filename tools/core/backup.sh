#!/usr/bin/env bash
# =============================================================================
# Backup Tool
# =============================================================================
# Creates backups of CLOPUS data and configurations

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/app/backups}"
CLOPUS_DIR="${CLOPUS_DIR:-/app}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="clopus_backup_$TIMESTAMP"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

echo ""
echo "💾 Creating CLOPUS Backup"
echo "   Timestamp: $TIMESTAMP"
echo ""

# Create backup directory
mkdir -p "$BACKUP_DIR/$BACKUP_NAME"

# Backup SQLite database
if [ -d "$CLOPUS_DIR/data/sqlite" ]; then
    log_info "Backing up SQLite database..."
    cp -r "$CLOPUS_DIR/data/sqlite" "$BACKUP_DIR/$BACKUP_NAME/sqlite"
fi

# Backup configurations
log_info "Backing up configurations..."
mkdir -p "$BACKUP_DIR/$BACKUP_NAME/config"

[ -f "$CLOPUS_DIR/.env" ] && cp "$CLOPUS_DIR/.env" "$BACKUP_DIR/$BACKUP_NAME/config/"
[ -f "$CLOPUS_DIR/config.yaml" ] && cp "$CLOPUS_DIR/config.yaml" "$BACKUP_DIR/$BACKUP_NAME/config/"

# Backup knowledge base
if [ -d "$CLOPUS_DIR/knowledge" ]; then
    log_info "Backing up knowledge base..."
    cp -r "$CLOPUS_DIR/knowledge" "$BACKUP_DIR/$BACKUP_NAME/knowledge"
fi

# Backup generated assets
log_info "Backing up generated assets..."
mkdir -p "$BACKUP_DIR/$BACKUP_NAME/generated"

[ -d "$CLOPUS_DIR/skills/generated" ] && cp -r "$CLOPUS_DIR/skills/generated" "$BACKUP_DIR/$BACKUP_NAME/generated/skills"
[ -d "$CLOPUS_DIR/templates/extracted" ] && cp -r "$CLOPUS_DIR/templates/extracted" "$BACKUP_DIR/$BACKUP_NAME/generated/templates"
[ -d "$CLOPUS_DIR/mcp-servers/generated" ] && cp -r "$CLOPUS_DIR/mcp-servers/generated" "$BACKUP_DIR/$BACKUP_NAME/generated/mcps"
[ -d "$CLOPUS_DIR/tools/generated" ] && cp -r "$CLOPUS_DIR/tools/generated" "$BACKUP_DIR/$BACKUP_NAME/generated/tools"

# Create archive
log_info "Creating archive..."
cd "$BACKUP_DIR"
tar -czf "$BACKUP_NAME.tar.gz" "$BACKUP_NAME"
rm -rf "$BACKUP_NAME"

# Upload to MinIO if available
if command -v mc &>/dev/null && mc alias list clopus &>/dev/null; then
    log_info "Uploading to MinIO..."
    mc cp "$BACKUP_NAME.tar.gz" clopus/backups/
fi

# Cleanup old backups (keep last 10)
log_info "Cleaning up old backups..."
ls -t "$BACKUP_DIR"/*.tar.gz 2>/dev/null | tail -n +11 | xargs -r rm

BACKUP_SIZE=$(du -h "$BACKUP_DIR/$BACKUP_NAME.tar.gz" | cut -f1)

log_success "Backup complete!"
echo ""
echo "  Location: $BACKUP_DIR/$BACKUP_NAME.tar.gz"
echo "  Size: $BACKUP_SIZE"
