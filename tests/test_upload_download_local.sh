#!/bin/bash
# Test upload/download on localhost with multiple nodes

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}🧪 Upload/Download Test (Localhost)${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Clean up previous test data
rm -rf /tmp/pangea-test-upload-download
mkdir -p /tmp/pangea-test-upload-download
TEST_DIR="/tmp/pangea-test-upload-download"

# Create test file
TEST_FILE="$TEST_DIR/test_file.txt"
echo "This is a test file for upload/download testing!" > "$TEST_FILE"
echo "Line 2: Lorem ipsum dolor sit amet" >> "$TEST_FILE"
echo "Line 3: The quick brown fox jumps over the lazy dog" >> "$TEST_FILE"
ORIGINAL_HASH=$(sha256sum "$TEST_FILE" | awk '{print $1}')
echo -e "${GREEN}✓ Created test file: $TEST_FILE${NC}"
echo -e "  Original hash: $ORIGINAL_HASH"
echo ""

# Start nodes
echo -e "${BLUE}Starting test nodes...${NC}"

# Node 1 (Bootstrap)
NODE1_PID=""
NODE2_PID=""
NODE3_PID=""

cleanup() {
    echo -e "\n${YELLOW}Cleaning up...${NC}"
    [ -n "$NODE1_PID" ] && kill $NODE1_PID 2>/dev/null || true
    [ -n "$NODE2_PID" ] && kill $NODE2_PID 2>/dev/null || true
    [ -n "$NODE3_PID" ] && kill $NODE3_PID 2>/dev/null || true
    sleep 1
}

trap cleanup EXIT

# Start Node 1
# Note: Using -local flag for localhost testing - mDNS discovery within local network
# No need for -peers flag when testing on localhost, nodes will discover each other via mDNS
LOG1="$TEST_DIR/node1.log"
export LD_LIBRARY_PATH="$PROJECT_ROOT/rust/target/release:$LD_LIBRARY_PATH"
./go/bin/go-node -node-id=1 -capnp-addr=:18080 -libp2p=true -local > "$LOG1" 2>&1 &
NODE1_PID=$!
sleep 3

if ! ps -p $NODE1_PID > /dev/null; then
    echo -e "${RED}❌ Node 1 failed to start${NC}"
    cat "$LOG1"
    exit 1
fi
echo -e "${GREEN}✓ Node 1 started (PID: $NODE1_PID)${NC}"

# Extract Node 1 peer info for reference
sleep 2
PEER1_MULTIADDR=$(grep "Listening addresses:" -A 2 "$LOG1" | grep "/ip4/127.0.0.1/" | head -1 | awk '{print $NF}')
echo -e "  Multiaddr: $PEER1_MULTIADDR"

# Start Node 2
# Note: Using -local flag - nodes discover each other automatically on localhost
LOG2="$TEST_DIR/node2.log"
./go/bin/go-node -node-id=2 -capnp-addr=:18081 -libp2p=true -local > "$LOG2" 2>&1 &
NODE2_PID=$!
sleep 3

if ! ps -p $NODE2_PID > /dev/null; then
    echo -e "${RED}❌ Node 2 failed to start${NC}"
    cat "$LOG2"
    exit 1
fi
echo -e "${GREEN}✓ Node 2 started (PID: $NODE2_PID)${NC}"

# Start Node 3
LOG3="$TEST_DIR/node3.log"
./go/bin/go-node -node-id=3 -capnp-addr=:18082 -libp2p=true -local > "$LOG3" 2>&1 &
NODE3_PID=$!
sleep 3

if ! ps -p $NODE3_PID > /dev/null; then
    echo -e "${RED}❌ Node 3 failed to start${NC}"
    cat "$LOG3"
    exit 1
fi
echo -e "${GREEN}✓ Node 3 started (PID: $NODE3_PID)${NC}"
echo ""

# Wait for nodes to discover each other
echo -e "${BLUE}Waiting for peer discovery...${NC}"
sleep 5

# Check connectivity
echo -e "${BLUE}Checking node connectivity...${NC}"
PEER_COUNT1=$(grep "Connected peers:" "$LOG1" | tail -1 | awk '{print $NF}')
PEER_COUNT2=$(grep "Connected peers:" "$LOG2" | tail -1 | awk '{print $NF}')
PEER_COUNT3=$(grep "Connected peers:" "$LOG3" | tail -1 | awk '{print $NF}')

echo -e "  Node 1 peers: ${PEER_COUNT1:-0}"
echo -e "  Node 2 peers: ${PEER_COUNT2:-0}"
echo -e "  Node 3 peers: ${PEER_COUNT3:-0}"

if [ "${PEER_COUNT1:-0}" -lt "1" ]; then
    echo -e "${YELLOW}⚠ Warning: Nodes may not be fully connected${NC}"
fi
echo ""

# Test 1: Upload file
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Test 1: Upload File${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# TODO: Implement Python CLI for upload
# For now, test the RPC interface directly
echo -e "${YELLOW}ℹ  Upload test pending Python CLI implementation${NC}"
echo -e "  File ready at: $TEST_FILE"
echo ""

# Test 2: Download file (when upload is implemented)
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Test 2: Download File${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}ℹ  Download test pending upload completion${NC}"
echo ""

# Show node logs for debugging
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Recent Node Logs${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "\n${GREEN}Node 1:${NC}"
tail -5 "$LOG1"
echo -e "\n${GREEN}Node 2:${NC}"
tail -5 "$LOG2"
echo -e "\n${GREEN}Node 3:${NC}"
tail -5 "$LOG3"
echo ""

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✓ 3 nodes started successfully${NC}"
echo -e "${GREEN}✓ Network adapter with FetchShard implemented${NC}"
echo -e "${YELLOW}⏳ Waiting for Python CLI integration for end-to-end test${NC}"
echo ""
echo -e "Test environment ready at: $TEST_DIR"
echo -e "Test file: $TEST_FILE"
echo -e "Logs: $LOG1, $LOG2, $LOG3"
echo ""
