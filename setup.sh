#!/usr/bin/env bash
# =============================================================================
# CLOPUS v3 Setup Script
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

echo -e "${CYAN}${BOLD}"
cat << 'EOF'
   ____ _     ___  ____  _   _ ____
  / ___| |   / _ \|  _ \| | | / ___|
 | |   | |  | | | | |_) | | | \___ \
 | |___| |__| |_| |  __/| |_| |___) |
  \____|_____\___/|_|    \___/|____/

  Setup Script v3.0.0
EOF
echo -e "${NC}\n"

# =============================================================================
# Check Prerequisites
# =============================================================================
log_info "Checking prerequisites..."

check_command() {
    if command -v "$1" &>/dev/null; then
        echo -e "  ${GREEN}✓${NC} $1 found"
        return 0
    else
        echo -e "  ${RED}✗${NC} $1 not found"
        return 1
    fi
}

missing=0
check_command docker || missing=1
check_command git || missing=1
check_command gh || missing=1
check_command jq || missing=1

if [ $missing -eq 1 ]; then
    echo ""
    log_error "Missing dependencies. Please install them first:"
    echo "  - Docker: https://docs.docker.com/get-docker/"
    echo "  - Git: https://git-scm.com/"
    echo "  - GitHub CLI: https://cli.github.com/"
    echo "  - jq: apt install jq / brew install jq"
    exit 1
fi

# Check Docker is running
if ! docker info &>/dev/null; then
    log_error "Docker is not running. Please start Docker first."
    exit 1
fi

echo ""
log_success "All prerequisites met!"

# =============================================================================
# Create .env file
# =============================================================================
echo ""
log_info "Configuring environment..."

if [ -f "$SCRIPT_DIR/.env" ]; then
    log_warning ".env already exists. Skipping..."
else
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    log_success "Created .env from template"

    echo ""
    echo -e "${YELLOW}Please enter your configuration:${NC}"
    echo ""

    # Anthropic API Key
    read -p "Anthropic API Key (sk-ant-...): " api_key
    if [ -n "$api_key" ]; then
        sed -i "s|ANTHROPIC_API_KEY=.*|ANTHROPIC_API_KEY=$api_key|" "$SCRIPT_DIR/.env"
    fi

    # Auth mode
    echo ""
    echo "Authentication mode:"
    echo "  1) api     - Use API key only"
    echo "  2) login   - Use Claude subscription (requires login)"
    echo "  3) hybrid  - Use subscription first, fallback to API (recommended)"
    read -p "Choose [3]: " auth_choice
    auth_choice=${auth_choice:-3}

    case $auth_choice in
        1) sed -i "s|AUTH_MODE=.*|AUTH_MODE=api|" "$SCRIPT_DIR/.env" ;;
        2) sed -i "s|AUTH_MODE=.*|AUTH_MODE=login|" "$SCRIPT_DIR/.env" ;;
        *) sed -i "s|AUTH_MODE=.*|AUTH_MODE=hybrid|" "$SCRIPT_DIR/.env" ;;
    esac

    log_success "Environment configured!"
fi

# =============================================================================
# Create Directories
# =============================================================================
echo ""
log_info "Creating directories..."

mkdir -p "$SCRIPT_DIR"/{data/{sqlite,chromadb,postgres,redis,minio},logs,ipc/tasks,objectives,questions,answers,output}

# Create .gitkeep files
touch "$SCRIPT_DIR/skills/generated/.gitkeep"
touch "$SCRIPT_DIR/mcp-servers/generated/.gitkeep"
touch "$SCRIPT_DIR/templates/extracted/.gitkeep"
touch "$SCRIPT_DIR/tools/generated/.gitkeep"
touch "$SCRIPT_DIR/browser/profiles/.gitkeep"

# Ensure anthropic session directory exists
mkdir -p "$HOME/.anthropic"

log_success "Directories created!"

# =============================================================================
# Build Docker Images
# =============================================================================
echo ""
log_info "Building Docker images (this may take a while)..."

cd "$SCRIPT_DIR"

# Build base image
log_info "Building base image..."
docker build -t clopus-base:latest -f Dockerfile.base . || {
    log_error "Failed to build base image"
    exit 1
}

log_success "Docker images built!"

# =============================================================================
# Initialize Git (if not already)
# =============================================================================
echo ""
if [ ! -d "$SCRIPT_DIR/.git" ]; then
    log_info "Initializing git repository..."
    git init
    git add .
    git commit -m "Initial CLOPUS v3 setup"
    log_success "Git repository initialized!"
else
    log_info "Git repository already exists."
fi

# =============================================================================
# GitHub Authentication
# =============================================================================
echo ""
log_info "Checking GitHub authentication..."

if gh auth status &>/dev/null; then
    log_success "GitHub CLI is authenticated!"
else
    log_warning "GitHub CLI is not authenticated."
    echo "Run 'gh auth login' to authenticate."
fi

# =============================================================================
# Claude Authentication (optional)
# =============================================================================
echo ""
read -p "Do you want to authenticate with Claude now? (y/N): " do_auth
if [[ "$do_auth" =~ ^[Yy]$ ]]; then
    if command -v claude &>/dev/null; then
        claude login
    else
        log_warning "Claude Code CLI not found."
        log_info "Install with: npm install -g @anthropic-ai/claude-code"
    fi
fi

# =============================================================================
# Done!
# =============================================================================
echo ""
echo -e "${GREEN}${BOLD}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║                    CLOPUS Setup Complete!                     ║${NC}"
echo -e "${GREEN}${BOLD}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Next steps:"
echo ""
echo "  1. Review and edit .env if needed:"
echo -e "     ${CYAN}nano .env${NC}"
echo ""
echo "  2. Start CLOPUS:"
echo -e "     ${CYAN}./clopus start${NC}"
echo ""
echo "  3. Give it an objective:"
echo -e "     ${CYAN}./clopus objective \"Build a todo app with React\"${NC}"
echo ""
echo "  4. Monitor status:"
echo -e "     ${CYAN}./clopus status --watch${NC}"
echo ""
echo "  5. View logs:"
echo -e "     ${CYAN}./clopus logs -f${NC}"
echo ""
echo "For help, run: ./clopus help"
echo ""
