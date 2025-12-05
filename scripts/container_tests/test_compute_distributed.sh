#!/bin/bash
# =============================================================================
# Container Test: Distributed Compute
# =============================================================================
# Tests distributed matrix multiplication across multiple containers
#
# Usage:
#   ./test_compute_distributed.sh [--nodes 2|3|4]
#
# =============================================================================

# set -e  # Handled manually

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
NUM_NODES=2
COMPOSE_FILE=""
TEST_RESULTS=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --nodes)
            NUM_NODES="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Select compose file based on node count
case $NUM_NODES in
    2)
        COMPOSE_FILE="docker-compose.test.2node.yml"
        ;;
    3)
        COMPOSE_FILE="docker-compose.test.3node.yml"
        ;;
    4)
        COMPOSE_FILE="docker-compose.test.compute.yml"
        ;;
    *)
        echo "Invalid node count. Use 2, 3, or 4"
        exit 1
        ;;
esac

# =============================================================================
# Test Functions
# =============================================================================

check_docker() {
    echo ""
    echo -e "${CYAN}Checking Docker availability...${NC}"
    
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker not installed${NC}"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        echo -e "${RED}❌ Docker daemon not running${NC}"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        # Try docker compose (V2)
        if ! docker compose version &> /dev/null; then
            echo -e "${RED}❌ Docker Compose not installed${NC}"
            exit 1
        fi
    fi
    
    echo -e "${GREEN}✅ Docker is available${NC}"
}

start_containers() {
    echo ""
    echo -e "${CYAN}Starting ${NUM_NODES}-node container environment...${NC}"
    echo "Using compose file: $COMPOSE_FILE"
    
    cd "$PROJECT_ROOT"
    
    # Build and start containers
    if command -v docker-compose &> /dev/null; then
        docker-compose -f "$COMPOSE_FILE" up -d --build 2>&1
    else
        docker compose -f "$COMPOSE_FILE" up -d --build 2>&1
    fi
    
    echo "Waiting for containers to be healthy..."
    sleep 15
    
    # Check container status
    if command -v docker-compose &> /dev/null; then
        docker-compose -f "$COMPOSE_FILE" ps
    else
        docker compose -f "$COMPOSE_FILE" ps
    fi
}

stop_containers() {
    echo ""
    echo -e "${CYAN}Stopping containers...${NC}"
    
    cd "$PROJECT_ROOT"
    
    if command -v docker-compose &> /dev/null; then
        docker-compose -f "$COMPOSE_FILE" down -v 2>&1 || true
    else
        docker compose -f "$COMPOSE_FILE" down -v 2>&1 || true
    fi
}

test_small_matrix() {
    echo ""
    echo -e "${CYAN}Test: Small matrix (5x5) multiplication${NC}"
    echo "=========================================="
    
    local result
    if [ "$NUM_NODES" = "2" ] || [ "$NUM_NODES" = "4" ]; then
        result=$(docker exec wgt-python-cli python main.py compute matrix-multiply \
            --size 5 --generate --verify \
            --host 172.28.0.10 --port 8080 --connect 2>&1) || true
    else
        # 3-node mesh doesn't have python-cli container
        echo -e "${YELLOW}⚠️  Running locally for 3-node mesh${NC}"
        cd "$PROJECT_ROOT/python"
        source .venv/bin/activate 2>/dev/null || true
        result=$(python main.py compute matrix-multiply --size 5 --generate --verify 2>&1) || true
    fi
    
    echo "$result"
    
    if echo "$result" | grep -q "COMPUTATION COMPLETE"; then
        echo -e "${GREEN}✅ Small matrix test PASSED${NC}"
        TEST_RESULTS="${TEST_RESULTS}Small matrix (5x5): PASSED\n"
        return 0
    else
        echo -e "${RED}❌ Small matrix test FAILED${NC}"
        TEST_RESULTS="${TEST_RESULTS}Small matrix (5x5): FAILED\n"
        return 1
    fi
}

test_medium_matrix() {
    echo ""
    echo -e "${CYAN}Test: Medium matrix (20x20) multiplication${NC}"
    echo "============================================="
    
    local result
    if [ "$NUM_NODES" = "2" ] || [ "$NUM_NODES" = "4" ]; then
        result=$(docker exec wgt-python-cli python main.py compute matrix-multiply \
            --size 20 --generate --verify \
            --host 172.28.0.10 --port 8080 --connect 2>&1) || true
    else
        cd "$PROJECT_ROOT/python"
        source .venv/bin/activate 2>/dev/null || true
        result=$(python main.py compute matrix-multiply --size 20 --generate --verify 2>&1) || true
    fi
    
    echo "$result" | tail -20
    
    if echo "$result" | grep -q "Result matches NumPy"; then
        echo -e "${GREEN}✅ Medium matrix test PASSED${NC}"
        TEST_RESULTS="${TEST_RESULTS}Medium matrix (20x20): PASSED\n"
        return 0
    else
        echo -e "${RED}❌ Medium matrix test FAILED${NC}"
        TEST_RESULTS="${TEST_RESULTS}Medium matrix (20x20): FAILED\n"
        return 1
    fi
}

test_large_matrix() {
    echo ""
    echo -e "${CYAN}Test: Large matrix (50x50) multiplication${NC}"
    echo "============================================"
    
    local result
    if [ "$NUM_NODES" = "2" ] || [ "$NUM_NODES" = "4" ]; then
        result=$(docker exec wgt-python-cli python main.py compute matrix-multiply \
            --size 50 --generate --verify \
            --host 172.28.0.10 --port 8080 --connect 2>&1) || true
    else
        cd "$PROJECT_ROOT/python"
        source .venv/bin/activate 2>/dev/null || true
        result=$(python main.py compute matrix-multiply --size 50 --generate --verify 2>&1) || true
    fi
    
    echo "$result" | tail -20
    
    if echo "$result" | grep -q "COMPUTATION COMPLETE"; then
        echo -e "${GREEN}✅ Large matrix test PASSED${NC}"
        TEST_RESULTS="${TEST_RESULTS}Large matrix (50x50): PASSED\n"
        return 0
    else
        echo -e "${RED}❌ Large matrix test FAILED${NC}"
        TEST_RESULTS="${TEST_RESULTS}Large matrix (50x50): FAILED\n"
        return 1
    fi
}

# =============================================================================
# Main
# =============================================================================

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   Distributed Compute Container Tests${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo "Node count: ${NUM_NODES}"
echo "Compose file: ${COMPOSE_FILE}"
echo ""

check_docker

# Setup
trap stop_containers EXIT
start_containers

# Run tests
PASSED=0
FAILED=0

if test_small_matrix; then ((PASSED++)); else ((FAILED++)); fi
if test_medium_matrix; then ((PASSED++)); else ((FAILED++)); fi
if test_large_matrix; then ((PASSED++)); else ((FAILED++)); fi

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
