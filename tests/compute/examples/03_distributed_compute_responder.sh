#!/bin/bash
# Distributed Compute Test - Responder
# Run this SECOND on your device (after running initiator on the first device)
# Paste the peer address when prompted

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"
cd "$PROJECT_ROOT"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
CAPNP_PORT="${1:-8080}"  # Can override with argument for same-machine testing

# Session files
SESSION_DIR="$HOME/.pangea/compute_test"
mkdir -p "$SESSION_DIR"
NODE_PID_FILE="$SESSION_DIR/responder_node.pid"
LOG_FILE="$SESSION_DIR/responder_node.log"

# Cleanup
cleanup() {
    if [ -f "$NODE_PID_FILE" ]; then
        local pid=$(cat "$NODE_PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            kill "$pid" 2>/dev/null || true
        fi
        rm -f "$NODE_PID_FILE"
    fi
}
trap cleanup EXIT

echo -e "${CYAN}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║   DISTRIBUTED COMPUTE - RESPONDER (Device 2)              ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

if [ "$CAPNP_PORT" != "8080" ]; then
    echo -e "${YELLOW}📝 Custom Cap'n Proto port: :${CAPNP_PORT}${NC}"
fi

# Build if needed
if [ ! -f "$PROJECT_ROOT/go/bin/go-node" ]; then
    echo -e "${YELLOW}Building Go node...${NC}"
    cd "$PROJECT_ROOT/go" && go build -o bin/go-node . && cd "$PROJECT_ROOT"
fi

# Kill any existing nodes
pkill -f "go-node.*node-id=2" 2>/dev/null || true
sleep 1

# Get peer address from user
echo -e "${YELLOW}Enter the peer address from the initiator device:${NC}"
read -p "> " PEER_ADDR

if [ -z "$PEER_ADDR" ]; then
    echo -e "${RED}❌ No peer address provided${NC}"
    exit 1
fi

# Start node
echo -e "${YELLOW}Starting Node 2 (responder)...${NC}"
export LD_LIBRARY_PATH="$PROJECT_ROOT/rust/target/release:$LD_LIBRARY_PATH"
export DYLD_LIBRARY_PATH="$PROJECT_ROOT/rust/target/release:$DYLD_LIBRARY_PATH"

"$PROJECT_ROOT/go/bin/go-node" \
    -node-id=2 \
    -capnp-addr=:${CAPNP_PORT} \
    -libp2p=true \
    -local \
    -test \
    -peers="$PEER_ADDR" \
    > "$LOG_FILE" 2>&1 &
echo $! > "$NODE_PID_FILE"

# Wait for startup and connection
echo -e "${YELLOW}Connecting to initiator...${NC}"
sleep 4

# Check if connected
if grep -q "Connected peers: [1-9]" "$LOG_FILE" 2>/dev/null; then
    echo -e "${GREEN}✅ Connected to initiator!${NC}"
else
    echo -e "${YELLOW}⚠️  Connection in progress...${NC}"
fi

echo ""
echo -e "${GREEN}Responder ready. Keep this terminal open.${NC}"
echo -e "${YELLOW}The initiator will now run the distributed compute test.${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop this responder when done.${NC}"
echo ""

# Keep node running
while true; do
    sleep 1
    if [ ! -f "$NODE_PID_FILE" ]; then
        break
    fi
    pid=$(cat "$NODE_PID_FILE")
    if ! ps -p "$pid" > /dev/null 2>&1; then
        break
    fi
done
