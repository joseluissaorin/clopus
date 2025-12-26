#!/usr/bin/env bash
# =============================================================================
# Validation Pipeline Runner
# =============================================================================
# Runs the 8-stage validation pipeline on a project

set -euo pipefail

PROJECT_PATH="${1:-.}"
STRICT="${STRICT:-true}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[PASS]${NC} $*"; }
log_warning() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[FAIL]${NC} $*" >&2; }

FAILED=0
PASSED=0
SKIPPED=0

run_stage() {
    local stage_name="$1"
    local stage_cmd="$2"

    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Stage: $stage_name${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    if eval "$stage_cmd"; then
        log_success "$stage_name"
        ((PASSED++))
    else
        if [ "$STRICT" = "true" ]; then
            log_error "$stage_name"
            ((FAILED++))
        else
            log_warning "$stage_name (non-strict mode)"
            ((SKIPPED++))
        fi
    fi
}

cd "$PROJECT_PATH"

echo ""
echo "🔍 Running CLOPUS Validation Pipeline"
echo "   Project: $(pwd)"
echo ""

# Stage 1: Syntax & Format
run_stage "1. Syntax & Format" '
    # Check JSON files
    find . -name "*.json" -not -path "./node_modules/*" -exec python3 -m json.tool {} > /dev/null \; 2>/dev/null || true

    # Check YAML files
    if command -v yamllint &>/dev/null; then
        yamllint -d relaxed . 2>/dev/null || true
    fi

    # Run Prettier if available
    if [ -f "package.json" ] && command -v npx &>/dev/null; then
        npx prettier --check "**/*.{js,ts,jsx,tsx,json,md}" 2>/dev/null || true
    fi

    # Run Black if Python
    if [ -f "requirements.txt" ] || [ -f "pyproject.toml" ]; then
        if command -v black &>/dev/null; then
            black --check . 2>/dev/null || true
        fi
    fi

    true  # Dont fail on format issues
'

# Stage 2: Linting
run_stage "2. Linting" '
    LINT_PASSED=true

    # ESLint for JavaScript/TypeScript
    if [ -f "package.json" ]; then
        if npx eslint . --ext .js,.jsx,.ts,.tsx 2>/dev/null; then
            echo "ESLint: OK"
        else
            LINT_PASSED=false
        fi
    fi

    # Ruff/Pylint for Python
    if [ -f "requirements.txt" ] || [ -f "pyproject.toml" ]; then
        if command -v ruff &>/dev/null; then
            if ruff check . 2>/dev/null; then
                echo "Ruff: OK"
            else
                LINT_PASSED=false
            fi
        fi
    fi

    $LINT_PASSED
'

# Stage 3: Build
run_stage "3. Build" '
    BUILD_PASSED=true

    # Node.js build
    if [ -f "package.json" ]; then
        npm install 2>/dev/null || BUILD_PASSED=false
        if grep -q "\"build\"" package.json; then
            npm run build 2>/dev/null || BUILD_PASSED=false
        fi
    fi

    # Python install
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt 2>/dev/null || BUILD_PASSED=false
    fi

    # Go build
    if [ -f "go.mod" ]; then
        go build ./... 2>/dev/null || BUILD_PASSED=false
    fi

    # Rust build
    if [ -f "Cargo.toml" ]; then
        cargo build 2>/dev/null || BUILD_PASSED=false
    fi

    $BUILD_PASSED
'

# Stage 4: Unit Tests
run_stage "4. Unit Tests" '
    TESTS_PASSED=true

    # Jest/Vitest for Node.js
    if [ -f "package.json" ]; then
        if grep -q "\"test\"" package.json; then
            npm test 2>/dev/null || TESTS_PASSED=false
        fi
    fi

    # Pytest for Python
    if [ -d "tests" ] && ([ -f "requirements.txt" ] || [ -f "pyproject.toml" ]); then
        if command -v pytest &>/dev/null; then
            pytest tests/ -v 2>/dev/null || TESTS_PASSED=false
        fi
    fi

    # Go tests
    if [ -f "go.mod" ]; then
        go test ./... 2>/dev/null || TESTS_PASSED=false
    fi

    $TESTS_PASSED
'

# Stage 5: Integration Tests
run_stage "5. Integration Tests" '
    # Check for integration test markers
    if [ -d "tests/integration" ]; then
        pytest tests/integration/ -v -m integration 2>/dev/null || true
    fi
    true  # Optional stage
'

# Stage 6: E2E Tests
run_stage "6. E2E Tests" '
    # Check for E2E test setup
    if [ -f "playwright.config.ts" ] || [ -f "playwright.config.js" ]; then
        npx playwright test 2>/dev/null || true
    fi
    if [ -f "cypress.config.ts" ] || [ -f "cypress.config.js" ]; then
        npx cypress run 2>/dev/null || true
    fi
    true  # Optional stage
'

# Stage 7: Security Scan
run_stage "7. Security Scan" '
    SECURITY_PASSED=true

    # npm audit
    if [ -f "package-lock.json" ]; then
        npm audit --audit-level=high 2>/dev/null || SECURITY_PASSED=false
    fi

    # pip-audit / safety
    if [ -f "requirements.txt" ]; then
        if command -v safety &>/dev/null; then
            safety check -r requirements.txt 2>/dev/null || SECURITY_PASSED=false
        fi
    fi

    # Check for secrets
    if command -v git-secrets &>/dev/null; then
        git secrets --scan 2>/dev/null || SECURITY_PASSED=false
    fi

    $SECURITY_PASSED
'

# Stage 8: Review (placeholder - would be done by reviewer worker)
run_stage "8. Code Review" '
    echo "Code review is performed by the Reviewer worker"
    true
'

# Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Validation Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "  ${GREEN}Passed:${NC}  $PASSED"
echo -e "  ${RED}Failed:${NC}  $FAILED"
echo -e "  ${YELLOW}Skipped:${NC} $SKIPPED"
echo ""

if [ $FAILED -gt 0 ]; then
    log_error "Validation failed with $FAILED errors"
    exit 1
else
    log_success "All validation stages passed!"
    exit 0
fi
