#!/bin/bash
# Test script to spawn 10 libp2p nodes and connect them

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
GO_NODE="$PROJECT_ROOT/go/bin/go-node"
LOG_DIR="/tmp/wgt_nodes"

# Clean up function
cleanup() {
    echo -e "\n${BLUE}Cleaning up nodes...${NC}"
    pkill -9 -f "go-node.*--node-id" 2>/dev/null || true
    rm -rf "$LOG_DIR"
    sleep 1
}

trap cleanup EXIT

# Clean up any existing processes
cleanup

# Create log directory
mkdir -p "$LOG_DIR"

echo -e "${BLUE}🧪 10-Node libp2p Mesh Test${NC}"
echo "================================"
echo ""

# Start node 1 (bootstrap node)
echo -e "${BLUE}Starting Node 1 (bootstrap)...${NC}"
CAPNP_PORT=8080
$GO_NODE --libp2p --local --test --node-id=1 --capnp-addr=:$CAPNP_PORT > "$LOG_DIR/node1.log" 2>&1 &
NODE1_PID=$!
sleep 2

# Get node 1 multiaddr
NODE1_ADDR=$(grep "tcp.*p2p" "$LOG_DIR/node1.log" | awk -F'   ' '{print $2}' | tr -d ' ')
if [ -z "$NODE1_ADDR" ]; then
    echo -e "${RED}❌ Failed to get Node 1 address${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Node 1 started${NC}"
echo "   Address: $NODE1_ADDR"
echo ""

# Start nodes 2-10
echo -e "${BLUE}Starting Nodes 2-10...${NC}"
for i in {2..10}; do
    CAPNP_PORT=$((8079 + i))
    $GO_NODE --libp2p --local --test --node-id=$i --capnp-addr=:$CAPNP_PORT --peers="$NODE1_ADDR" > "$LOG_DIR/node$i.log" 2>&1 &
    sleep 0.5
    echo -e "${GREEN}✅ Node $i started (Cap'n Proto: $CAPNP_PORT)${NC}"
done

echo ""
echo -e "${BLUE}Waiting for connections to establish...${NC}"
sleep 5

# Check connection status
echo ""
echo -e "${BLUE}📊 Connection Status:${NC}"
echo "================================"

total_peers=0
for i in {1..10}; do
    peer_count=$(grep "Connected peers:" "$LOG_DIR/node$i.log" | tail -1 | grep -oE '[0-9]+$' || echo "0")
    total_peers=$((total_peers + peer_count))
    
    if [ "$peer_count" -gt 0 ]; then
        echo -e "${GREEN}Node $i: $peer_count peer(s) connected${NC}"
    else
        echo -e "${YELLOW}Node $i: No peers connected${NC}"
    fi
done

echo ""
echo "================================"
avg_peers=$((total_peers / 10))
echo -e "${BLUE}Average peers per node: $avg_peers${NC}"

# Show network topology
echo ""
echo -e "${BLUE}🌐 Network Topology:${NC}"
echo "================================"
for i in {1..10}; do
    if grep -q "Network Status" "$LOG_DIR/node$i.log"; then
        echo -e "\n${BLUE}Node $i:${NC}"
        grep "Network Status" -A 4 "$LOG_DIR/node$i.log" | tail -4 | sed 's/^/  /'
    fi
done

# Show some ping results
echo ""
echo -e "${BLUE}📡 Ping Results (sample):${NC}"
echo "================================"
for i in {2..5}; do
    ping_result=$(grep "Ping to" "$LOG_DIR/node$i.log" | head -1 || echo "")
    if [ -n "$ping_result" ]; then
        echo "Node $i: $(echo $ping_result | awk '{print $NF}')"
    fi
done

echo ""
echo -e "${GREEN}✅ Test complete!${NC}"
echo ""
echo "Logs available in: $LOG_DIR"
echo "Nodes will be terminated on exit (Ctrl+C)"
echo ""
echo "Press Ctrl+C to stop all nodes..."

# Keep script running
while true; do
    sleep 5
    # Show live peer count every 5 seconds
    active_count=$(ps aux | grep -c "[g]o-node.*--node-id" || echo "0")
    echo -e "\r${BLUE}Active nodes: $active_count${NC}" | tr -d '\n'
done
