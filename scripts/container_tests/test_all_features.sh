#!/bin/bash
# =============================================================================
# Container Test: All Features
# =============================================================================
# Comprehensive integration test that runs all feature tests in containers
#
# Usage:
#   ./test_all_features.sh [--quick]
#
# =============================================================================

# Error handling: We don't use 'set -e' since we track test failures manually
# Using 'set -u' to catch undefined variables
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Options
QUICK_MODE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --quick)
            QUICK_MODE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# =============================================================================
# Test Runner
# =============================================================================

run_test() {
    local test_name="$1"
    local test_script="$2"
    local test_args="${3:-}"
    
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}   Running: ${test_name}${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    
    if bash "$test_script" $test_args; then
        return 0
    else
        return 1
    fi
}

# =============================================================================
# Main
# =============================================================================

echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   WGT COMPREHENSIVE FEATURE TEST SUITE                     ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Quick mode: $QUICK_MODE"
echo "Start time: $(date)"
echo ""

PASSED=0
FAILED=0
SKIPPED=0
RESULTS=""

# Test 1: Network Connection
echo ""
echo -e "${YELLOW}[1/4] Network Connection Tests${NC}"
if run_test "Network Connection" "$SCRIPT_DIR/test_network_connection.sh"; then
    RESULTS="${RESULTS}✅ Network Connection: PASSED\n"
    ((PASSED++))
else
    RESULTS="${RESULTS}❌ Network Connection: FAILED\n"
    ((FAILED++))
fi

# Test 2: Matrix CLI (local only for quick mode)
echo ""
echo -e "${YELLOW}[2/4] Matrix CLI Tests${NC}"
if [ "$QUICK_MODE" = true ]; then
    if run_test "Matrix CLI (local)" "$SCRIPT_DIR/test_matrix_cli.sh" "--local-only --size 5"; then
        RESULTS="${RESULTS}✅ Matrix CLI (local): PASSED\n"
        ((PASSED++))
    else
        RESULTS="${RESULTS}❌ Matrix CLI (local): FAILED\n"
        ((FAILED++))
    fi
else
    if run_test "Matrix CLI" "$SCRIPT_DIR/test_matrix_cli.sh" "--size 10"; then
        RESULTS="${RESULTS}✅ Matrix CLI: PASSED\n"
        ((PASSED++))
    else
        RESULTS="${RESULTS}❌ Matrix CLI: FAILED\n"
        ((FAILED++))
    fi
fi

# Test 3: Distributed Compute (skip in quick mode)
echo ""
echo -e "${YELLOW}[3/4] Distributed Compute Tests${NC}"
if [ "$QUICK_MODE" = true ]; then
    echo -e "${YELLOW}⚠️  Skipped in quick mode${NC}"
    RESULTS="${RESULTS}⏭️  Distributed Compute: SKIPPED (quick mode)\n"
    ((SKIPPED++))
else
    # Check if Docker is available
    if command -v docker &> /dev/null && docker info &> /dev/null 2>&1; then
        if run_test "Distributed Compute" "$SCRIPT_DIR/test_compute_distributed.sh" "--nodes 2"; then
            RESULTS="${RESULTS}✅ Distributed Compute: PASSED\n"
            ((PASSED++))
        else
            RESULTS="${RESULTS}❌ Distributed Compute: FAILED\n"
            ((FAILED++))
        fi
    else
        echo -e "${YELLOW}⚠️  Docker not available, skipping${NC}"
        RESULTS="${RESULTS}⏭️  Distributed Compute: SKIPPED (Docker unavailable)\n"
        ((SKIPPED++))
    fi
fi

# Test 4: Python CLI basic tests
echo ""
echo -e "${YELLOW}[4/4] Python CLI Basic Tests${NC}"
cd "$PROJECT_ROOT/python"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate 2>/dev/null || true
pip install -q click pycapnp 2>/dev/null || true

# Test CLI help commands
if python main.py --help > /dev/null 2>&1 && \
   python main.py compute --help > /dev/null 2>&1 && \
   python main.py compute matrix-multiply --help > /dev/null 2>&1; then
    RESULTS="${RESULTS}✅ Python CLI: PASSED\n"
    ((PASSED++))
else
    RESULTS="${RESULTS}❌ Python CLI: FAILED\n"
    ((FAILED++))
fi

# =============================================================================
# Summary
# =============================================================================

echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   TEST SUMMARY                                             ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "$RESULTS"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TOTAL=$((PASSED + FAILED + SKIPPED))
echo -e "Total Tests: $TOTAL"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo -e "${YELLOW}Skipped: $SKIPPED${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "End time: $(date)"
echo ""

if [ $FAILED -gt 0 ]; then
    echo -e "${RED}❌ Some tests failed!${NC}"
    exit 1
else
    echo -e "${GREEN}✅ All tests passed!${NC}"
    exit 0
fi
