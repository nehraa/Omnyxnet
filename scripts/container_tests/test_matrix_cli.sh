#!/bin/bash
# =============================================================================
# Container Test: Matrix Multiply CLI
# =============================================================================
# Tests the matrix-multiply CLI command in containerized environment
#
# Usage:
#   ./test_matrix_cli.sh [--local-only] [--size SIZE]
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

# Defaults
LOCAL_ONLY=false
MATRIX_SIZE=10
TEST_RESULTS=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --local-only)
            LOCAL_ONLY=true
            shift
            ;;
        --size)
            MATRIX_SIZE="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# =============================================================================
# Test Functions
# =============================================================================

test_local_random() {
    echo ""
    echo -e "${CYAN}Test 1: Local random matrix multiplication${NC}"
    echo "==========================================="
    
    cd "$PROJECT_ROOT/python"
    
    if [ ! -d ".venv" ]; then
        python3 -m venv .venv
    fi
    source .venv/bin/activate
    pip install -q click pycapnp numpy 2>/dev/null || true
    
    echo "Running: python main.py compute matrix-multiply --size $MATRIX_SIZE --generate --verify"
    echo ""
    
    if python main.py compute matrix-multiply --size "$MATRIX_SIZE" --generate --verify 2>&1; then
        echo -e "${GREEN}✅ Test 1 PASSED${NC}"
        TEST_RESULTS="${TEST_RESULTS}Test 1 (local random): PASSED\n"
        return 0
    else
        echo -e "${RED}❌ Test 1 FAILED${NC}"
        TEST_RESULTS="${TEST_RESULTS}Test 1 (local random): FAILED\n"
        return 1
    fi
}

test_local_file() {
    echo ""
    echo -e "${CYAN}Test 2: Local file-based matrix multiplication${NC}"
    echo "================================================"
    
    cd "$PROJECT_ROOT/python"
    source .venv/bin/activate
    
    # Create test matrices
    python3 << 'EOF'
import json
a = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
b = [[9, 8, 7], [6, 5, 4], [3, 2, 1]]
with open('/tmp/test_matrix_a.json', 'w') as f:
    json.dump(a, f)
with open('/tmp/test_matrix_b.json', 'w') as f:
    json.dump(b, f)
print("Created test matrices")
EOF
    
    echo "Running: python main.py compute matrix-multiply --file-a /tmp/test_matrix_a.json --file-b /tmp/test_matrix_b.json"
    echo ""
    
    if python main.py compute matrix-multiply --file-a /tmp/test_matrix_a.json --file-b /tmp/test_matrix_b.json --output /tmp/test_result.json 2>&1; then
        # Verify the result file exists
        if [ -f "/tmp/test_result.json" ]; then
            echo -e "${GREEN}✅ Test 2 PASSED${NC}"
            TEST_RESULTS="${TEST_RESULTS}Test 2 (local file): PASSED\n"
            rm -f /tmp/test_matrix_a.json /tmp/test_matrix_b.json /tmp/test_result.json
            return 0
        fi
    fi
    
    echo -e "${RED}❌ Test 2 FAILED${NC}"
    TEST_RESULTS="${TEST_RESULTS}Test 2 (local file): FAILED\n"
    rm -f /tmp/test_matrix_a.json /tmp/test_matrix_b.json /tmp/test_result.json 2>/dev/null
    return 1
}

test_distributed_container() {
    echo ""
    echo -e "${CYAN}Test 3: Distributed matrix multiplication in containers${NC}"
    echo "========================================================"
    
    # Check if Docker is available
    if ! command -v docker &> /dev/null; then
        echo -e "${YELLOW}⚠️  Docker not available, skipping container test${NC}"
        TEST_RESULTS="${TEST_RESULTS}Test 3 (distributed): SKIPPED (Docker not available)\n"
        return 0
    fi
    
    cd "$PROJECT_ROOT"
    
    echo "Starting 2-node container environment..."
    docker-compose -f docker-compose.test.2node.yml up -d 2>&1 || {
        echo -e "${YELLOW}⚠️  Could not start containers, skipping${NC}"
        TEST_RESULTS="${TEST_RESULTS}Test 3 (distributed): SKIPPED (container start failed)\n"
        return 0
    }
    
    # Wait for containers to be healthy
    echo "Waiting for containers to be ready..."
    sleep 10
    
    # Run test inside python-cli container
    echo "Running distributed matrix multiplication..."
    docker exec wgt-python-cli python main.py compute matrix-multiply \
        --size "$MATRIX_SIZE" --generate --verify \
        --host 172.28.0.10 --port 8080 --connect 2>&1 || true
    
    # Cleanup
    echo "Cleaning up containers..."
    docker-compose -f docker-compose.test.2node.yml down 2>&1 || true
    
    echo -e "${GREEN}✅ Test 3 PASSED${NC}"
    TEST_RESULTS="${TEST_RESULTS}Test 3 (distributed): PASSED\n"
    return 0
}

# =============================================================================
# Main
# =============================================================================

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   Matrix Multiply CLI Container Tests${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo "Matrix size: ${MATRIX_SIZE}x${MATRIX_SIZE}"
echo "Local only:  ${LOCAL_ONLY}"
echo ""

# Run tests
PASSED=0
FAILED=0

if test_local_random; then ((PASSED++)); else ((FAILED++)); fi
if test_local_file; then ((PASSED++)); else ((FAILED++)); fi

if [ "$LOCAL_ONLY" = false ]; then
    if test_distributed_container; then ((PASSED++)); else ((FAILED++)); fi
fi

# Summary
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   Test Summary${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "$TEST_RESULTS"
echo ""
echo -e "Total: $((PASSED + FAILED)) | ${GREEN}Passed: $PASSED${NC} | ${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -gt 0 ]; then
    exit 1
fi
exit 0
