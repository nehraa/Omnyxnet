#!/bin/bash
# =============================================================================
# Container Test: Network Connection
# =============================================================================
# Tests the network registry and peer discovery in containerized environment
#
# Usage:
#   ./test_network_connection.sh
#
# =============================================================================

# Don't use set -e since we handle errors manually
# set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

TEST_RESULTS=""

# =============================================================================
# Test Functions
# =============================================================================

test_registry_init() {
    echo ""
    echo -e "${CYAN}Test 1: Network registry initialization${NC}"
    echo "=========================================="
    
    cd "$PROJECT_ROOT/scripts"
    source network_registry.sh
    
    # Clear any existing registry
    rm -rf ~/.wgt 2>/dev/null || true
    
    # Initialize registry
    init_registry
    
    if [ -f "$HOME/.wgt/network.json" ]; then
        echo "Registry file created at ~/.wgt/network.json"
        echo -e "${GREEN}✅ Test 1 PASSED${NC}"
        TEST_RESULTS="${TEST_RESULTS}Test 1 (registry init): PASSED\n"
        return 0
    else
        echo -e "${RED}❌ Test 1 FAILED${NC}"
        TEST_RESULTS="${TEST_RESULTS}Test 1 (registry init): FAILED\n"
        return 1
    fi
}

test_save_peer() {
    echo ""
    echo -e "${CYAN}Test 2: Save peer to registry${NC}"
    echo "==============================="
    
    cd "$PROJECT_ROOT/scripts"
    source network_registry.sh
    
    save_peer "test-peer-1" "/ip4/192.168.1.100/tcp/9081/p2p/QmTest123" 8080 "connected"
    
    local peers=$(get_peers)
    if echo "$peers" | grep -q "test-peer-1"; then
        echo "Peer saved successfully"
        echo -e "${GREEN}✅ Test 2 PASSED${NC}"
        TEST_RESULTS="${TEST_RESULTS}Test 2 (save peer): PASSED\n"
        return 0
    else
        echo -e "${RED}❌ Test 2 FAILED${NC}"
        TEST_RESULTS="${TEST_RESULTS}Test 2 (save peer): FAILED\n"
        return 1
    fi
}

test_get_peer() {
    echo ""
    echo -e "${CYAN}Test 3: Get peer from registry${NC}"
    echo "================================"
    
    cd "$PROJECT_ROOT/scripts"
    source network_registry.sh
    
    local peer=$(get_peer_by_id "test-peer-1")
    
    if echo "$peer" | grep -q "192.168.1.100"; then
        echo "Peer retrieved: $peer"
        echo -e "${GREEN}✅ Test 3 PASSED${NC}"
        TEST_RESULTS="${TEST_RESULTS}Test 3 (get peer): PASSED\n"
        return 0
    else
        echo -e "${RED}❌ Test 3 FAILED${NC}"
        TEST_RESULTS="${TEST_RESULTS}Test 3 (get peer): FAILED\n"
        return 1
    fi
}

test_list_peers() {
    echo ""
    echo -e "${CYAN}Test 4: List peers${NC}"
    echo "==================="
    
    cd "$PROJECT_ROOT/scripts"
    source network_registry.sh
    
    # Add another peer
    save_peer "test-peer-2" "/ip4/192.168.1.101/tcp/9082/p2p/QmTest456" 8081 "connected"
    
    list_peers
    
    local peer_count=$(get_peers | python3 -c "import json,sys; print(len(json.load(sys.stdin)))")
    
    if [ "$peer_count" -ge 2 ]; then
        echo "Found $peer_count peers"
        echo -e "${GREEN}✅ Test 4 PASSED${NC}"
        TEST_RESULTS="${TEST_RESULTS}Test 4 (list peers): PASSED\n"
        return 0
    else
        echo -e "${RED}❌ Test 4 FAILED${NC}"
        TEST_RESULTS="${TEST_RESULTS}Test 4 (list peers): FAILED\n"
        return 1
    fi
}

test_is_connected() {
    echo ""
    echo -e "${CYAN}Test 5: Check connection status${NC}"
    echo "================================="
    
    cd "$PROJECT_ROOT/scripts"
    source network_registry.sh
    
    if is_connected; then
        echo "is_connected() returned true"
        echo -e "${GREEN}✅ Test 5 PASSED${NC}"
        TEST_RESULTS="${TEST_RESULTS}Test 5 (is_connected): PASSED\n"
        return 0
    else
        echo -e "${RED}❌ Test 5 FAILED${NC}"
        TEST_RESULTS="${TEST_RESULTS}Test 5 (is_connected): FAILED\n"
        return 1
    fi
}

test_clear_registry() {
    echo ""
    echo -e "${CYAN}Test 6: Clear registry${NC}"
    echo "========================"
    
    cd "$PROJECT_ROOT/scripts"
    source network_registry.sh
    
    clear_registry
    
    local peer_count=$(get_peers | python3 -c "import json,sys; print(len(json.load(sys.stdin)))")
    
    if [ "$peer_count" -eq 0 ]; then
        echo "Registry cleared successfully"
        echo -e "${GREEN}✅ Test 6 PASSED${NC}"
        TEST_RESULTS="${TEST_RESULTS}Test 6 (clear registry): PASSED\n"
        return 0
    else
        echo -e "${RED}❌ Test 6 FAILED${NC}"
        TEST_RESULTS="${TEST_RESULTS}Test 6 (clear registry): FAILED\n"
        return 1
    fi
}

test_check_network_script() {
    echo ""
    echo -e "${CYAN}Test 7: check_network.sh script${NC}"
    echo "=================================="
    
    cd "$PROJECT_ROOT/scripts"
    
    # Test status command
    if ./check_network.sh --status 2>&1 | grep -q "Network Status"; then
        echo "check_network.sh --status works"
        echo -e "${GREEN}✅ Test 7 PASSED${NC}"
        TEST_RESULTS="${TEST_RESULTS}Test 7 (check_network.sh): PASSED\n"
        return 0
    else
        echo -e "${RED}❌ Test 7 FAILED${NC}"
        TEST_RESULTS="${TEST_RESULTS}Test 7 (check_network.sh): FAILED\n"
        return 1
    fi
}

# =============================================================================
# Main
# =============================================================================

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   Network Connection Container Tests${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Run tests
PASSED=0
FAILED=0

if test_registry_init; then ((PASSED++)); else ((FAILED++)); fi
if test_save_peer; then ((PASSED++)); else ((FAILED++)); fi
if test_get_peer; then ((PASSED++)); else ((FAILED++)); fi
if test_list_peers; then ((PASSED++)); else ((FAILED++)); fi
if test_is_connected; then ((PASSED++)); else ((FAILED++)); fi
if test_clear_registry; then ((PASSED++)); else ((FAILED++)); fi
if test_check_network_script; then ((PASSED++)); else ((FAILED++)); fi

# Cleanup
rm -rf ~/.wgt 2>/dev/null || true

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
