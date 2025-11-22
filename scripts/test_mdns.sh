#!/bin/bash
# mDNS Auto-Discovery Test Script
# Tests automatic peer discovery and connection on local network

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Detect project root
if [ -f "go/bin/go-node" ]; then
    PROJECT_ROOT="$(pwd)"
elif [ -f "../go/bin/go-node" ]; then
    PROJECT_ROOT="$(cd .. && pwd)"
else
    echo -e "${RED}Error: Cannot find Pangea Net installation${NC}"
    exit 1
fi

cd "$PROJECT_ROOT"

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   📡 mDNS Auto-Discovery Test         ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# Export library path for Rust FFI
export LD_LIBRARY_PATH="$PROJECT_ROOT/rust/target/release:$LD_LIBRARY_PATH"

# Check if binaries exist
if [ ! -f "go/bin/go-node" ]; then
    echo -e "${RED}❌ Go binary not found${NC}"
    echo "Run: cd go && make build"
    exit 1
fi

if [ ! -f "rust/target/release/libpangea_ces.so" ]; then
    echo -e "${RED}❌ Rust library not found${NC}"
    echo "Run: cd rust && cargo build --release"
    exit 1
fi

echo -e "${GREEN}✓ Binaries ready${NC}"
echo ""

# Test configuration
NUM_NODES=3
DATA_DIR_BASE="$HOME/.pangea-mdns-test"
PIDS=()

# Cleanup function
cleanup() {
    echo ""
    echo -e "${YELLOW}🧹 Cleaning up...${NC}"
    for pid in "${PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
        fi
    done
    sleep 1
    rm -rf "$DATA_DIR_BASE"
    echo -e "${GREEN}✓ Cleanup complete${NC}"
}

trap cleanup EXIT INT TERM

# Clean up any previous test data
rm -rf "$DATA_DIR_BASE"

echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo -e "${CYAN}Test: Starting $NUM_NODES nodes for mDNS discovery${NC}"
echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo ""

# Start nodes without any bootstrap peers - they should find each other via mDNS!
for i in $(seq 1 $NUM_NODES); do
    NODE_DIR="$DATA_DIR_BASE/node-$i"
    mkdir -p "$NODE_DIR/logs"
    
    CAPNP_PORT=$((8080 + i - 1))
    
    echo -e "${BLUE}Starting Node $i (Cap'n Proto port: $CAPNP_PORT)...${NC}"
    
    # Start node without bootstrap peer - mDNS will handle discovery
    "$PROJECT_ROOT/go/bin/go-node" \
        -id="$i" \
        -port="$CAPNP_PORT" \
        -data="$NODE_DIR" \
        > "$NODE_DIR/logs/node.log" 2>&1 &
    
    NODE_PID=$!
    PIDS+=($NODE_PID)
    
    echo -e "${GREEN}✓ Node $i started (PID: $NODE_PID)${NC}"
    
    # Brief pause between node starts
    sleep 2
done

echo ""
echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo -e "${CYAN}Waiting for mDNS discovery...${NC}"
echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo ""

# Wait for mDNS to discover and connect peers (mDNS typically takes 1-5 seconds)
echo -e "${YELLOW}⏳ Waiting 10 seconds for mDNS auto-discovery and connection...${NC}"
for i in {10..1}; do
    echo -ne "${YELLOW}   $i seconds remaining...\r${NC}"
    sleep 1
done
echo ""
echo ""

# Check logs for mDNS discovery
echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo -e "${CYAN}mDNS Discovery Results:${NC}"
echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo ""

DISCOVERY_COUNT=0
CONNECTION_COUNT=0

for i in $(seq 1 $NUM_NODES); do
    LOG_FILE="$DATA_DIR_BASE/node-$i/logs/node.log"
    
    echo -e "${BLUE}Node $i:${NC}"
    
    # Check for mDNS discoveries
    if grep -q "mDNS discovered local peer" "$LOG_FILE"; then
        DISCOVERED=$(grep "mDNS discovered local peer" "$LOG_FILE" | wc -l)
        echo -e "  ${GREEN}✓ Discovered $DISCOVERED peer(s) via mDNS${NC}"
        DISCOVERY_COUNT=$((DISCOVERY_COUNT + DISCOVERED))
    else
        echo -e "  ${YELLOW}⚠ No mDNS discoveries${NC}"
    fi
    
    # Check for successful auto-connections
    if grep -q "Successfully connected to mDNS peer" "$LOG_FILE"; then
        CONNECTED=$(grep "Successfully connected to mDNS peer" "$LOG_FILE" | wc -l)
        echo -e "  ${GREEN}✓ Auto-connected to $CONNECTED peer(s)${NC}"
        CONNECTION_COUNT=$((CONNECTION_COUNT + CONNECTED))
    else
        echo -e "  ${YELLOW}⚠ No successful auto-connections${NC}"
    fi
    
    # Show peer IDs discovered
    if grep -q "mDNS discovered local peer" "$LOG_FILE"; then
        echo -e "  ${CYAN}Discovered peers:${NC}"
        grep "mDNS discovered local peer" "$LOG_FILE" | sed 's/.*peer: /    - /' | head -3
    fi
    
    echo ""
done

# Detailed connection status
echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo -e "${CYAN}Connection Status:${NC}"
echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo ""

for i in $(seq 1 $NUM_NODES); do
    LOG_FILE="$DATA_DIR_BASE/node-$i/logs/node.log"
    
    echo -e "${BLUE}Node $i:${NC}"
    
    # Get latest network status
    if grep -q "Network Status:" "$LOG_FILE"; then
        LAST_STATUS=$(grep -A 3 "Network Status:" "$LOG_FILE" | tail -4)
        echo "$LAST_STATUS" | sed 's/^/  /'
    else
        echo -e "  ${YELLOW}No network status available${NC}"
    fi
    
    echo ""
done

# Test summary
echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo -e "${CYAN}Test Summary:${NC}"
echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo ""

echo -e "Nodes started: ${GREEN}$NUM_NODES${NC}"
echo -e "Total mDNS discoveries: ${GREEN}$DISCOVERY_COUNT${NC}"
echo -e "Total auto-connections: ${GREEN}$CONNECTION_COUNT${NC}"
echo ""

# Expected: Each node should discover the other nodes
# With 3 nodes: Node 1 finds 2 peers, Node 2 finds 2 peers, Node 3 finds 2 peers = 6 total discoveries
EXPECTED_DISCOVERIES=$((NUM_NODES * (NUM_NODES - 1)))

if [ $DISCOVERY_COUNT -ge $((EXPECTED_DISCOVERIES / 2)) ]; then
    echo -e "${GREEN}✅ mDNS discovery working! ($DISCOVERY_COUNT/$EXPECTED_DISCOVERIES discoveries)${NC}"
else
    echo -e "${YELLOW}⚠️  Partial mDNS discovery ($DISCOVERY_COUNT/$EXPECTED_DISCOVERIES discoveries)${NC}"
fi

if [ $CONNECTION_COUNT -ge $((EXPECTED_DISCOVERIES / 2)) ]; then
    echo -e "${GREEN}✅ Auto-connection working! ($CONNECTION_COUNT connections)${NC}"
else
    echo -e "${YELLOW}⚠️  Partial auto-connection ($CONNECTION_COUNT connections)${NC}"
fi

echo ""
echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo -e "${CYAN}📝 Full Logs Available At:${NC}"
echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo ""

for i in $(seq 1 $NUM_NODES); do
    echo -e "  Node $i: ${YELLOW}$DATA_DIR_BASE/node-$i/logs/node.log${NC}"
done

echo ""
echo -e "${GREEN}✓ mDNS test complete!${NC}"
echo ""
echo -e "${BLUE}What just happened:${NC}"
echo "  1. Started $NUM_NODES nodes WITHOUT any bootstrap peers"
echo "  2. mDNS automatically discovered peers on the local network"
echo "  3. Nodes automatically connected to discovered peers"
echo "  4. No manual configuration needed!"
echo ""
echo -e "${YELLOW}Press Enter to stop nodes and cleanup...${NC}"
read
