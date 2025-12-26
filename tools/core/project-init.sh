#!/usr/bin/env bash
# =============================================================================
# Project Initialization Tool
# =============================================================================
# Initializes a new project with CLOPUS conventions

set -euo pipefail

PROJECT_NAME="${1:-}"
TEMPLATE="${2:-}"
WORKSPACE="${WORKSPACE_PATH:-/workspace}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

show_usage() {
    cat << EOF
Usage: project-init.sh <project-name> [template]

Arguments:
  project-name   Name of the project (will be used for directory and repo)
  template       Optional template to use (default: none)

Available templates:
  saas-starter      SaaS application scaffold
  react-dashboard   React admin dashboard
  python-api        FastAPI backend
  expo-app          React Native Expo app
  cli-tool          CLI tool scaffold

Examples:
  project-init.sh my-saas saas-starter
  project-init.sh my-api python-api
  project-init.sh my-app
EOF
}

if [ -z "$PROJECT_NAME" ]; then
    log_error "Project name is required"
    show_usage
    exit 1
fi

PROJECT_PATH="$WORKSPACE/$PROJECT_NAME"

# Check if project already exists
if [ -d "$PROJECT_PATH" ]; then
    log_error "Project directory already exists: $PROJECT_PATH"
    exit 1
fi

log_info "Creating project: $PROJECT_NAME"

# Create project directory
mkdir -p "$PROJECT_PATH"
cd "$PROJECT_PATH"

# Initialize git
log_info "Initializing git repository..."
git init

# Create basic structure
mkdir -p src tests docs .github/workflows

# Create README
cat > README.md << EOF
# $PROJECT_NAME

> Created with CLOPUS v3

## Description

TODO: Add project description

## Getting Started

TODO: Add setup instructions

## Development

TODO: Add development instructions

## License

MIT
EOF

# Create .gitignore
cat > .gitignore << 'EOF'
# Dependencies
node_modules/
__pycache__/
*.pyc
.venv/
venv/

# Build
dist/
build/
*.egg-info/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Environment
.env
.env.local
.env.*.local

# Logs
*.log
logs/

# OS
.DS_Store
Thumbs.db

# Testing
coverage/
.coverage
htmlcov/
.pytest_cache/

# Misc
*.bak
*.tmp
EOF

# Create .editorconfig
cat > .editorconfig << 'EOF'
root = true

[*]
indent_style = space
indent_size = 2
end_of_line = lf
charset = utf-8
trim_trailing_whitespace = true
insert_final_newline = true

[*.md]
trim_trailing_whitespace = false

[*.py]
indent_size = 4

[Makefile]
indent_style = tab
EOF

# Apply template if specified
if [ -n "$TEMPLATE" ]; then
    TEMPLATE_PATH="/app/templates/core/$TEMPLATE"

    if [ -d "$TEMPLATE_PATH" ]; then
        log_info "Applying template: $TEMPLATE"

        # Copy template files (excluding TEMPLATE.md)
        if [ -d "$TEMPLATE_PATH/scaffold" ]; then
            cp -r "$TEMPLATE_PATH/scaffold/"* ./ 2>/dev/null || true
        fi

        # Replace placeholders
        find . -type f -name "*.md" -o -name "*.json" -o -name "*.yaml" -o -name "*.yml" | while read -r file; do
            sed -i "s/{{PROJECT_NAME}}/$PROJECT_NAME/g" "$file" 2>/dev/null || true
        done

        log_success "Template applied: $TEMPLATE"
    else
        log_error "Template not found: $TEMPLATE"
        log_info "Available templates:"
        ls -1 /app/templates/core/ 2>/dev/null || echo "  (none)"
    fi
fi

# Initial commit
git add .
git commit -m "Initial commit

Created with CLOPUS v3
Template: ${TEMPLATE:-none}

🤖 Generated with [Claude Code](https://claude.com/claude-code)"

log_success "Project created: $PROJECT_PATH"
log_info "Next steps:"
echo "  cd $PROJECT_PATH"
echo "  # Start developing!"
