#!/bin/bash
# Distributed Compute Test - Initiator
# Run this FIRST on your device
# Then follow the instructions to start the responder on another device

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"
cd "$PROJECT_ROOT"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Session files
SESSION_DIR="$HOME/.pangea/compute_test"
mkdir -p "$SESSION_DIR"
NODE_PID_FILE="$SESSION_DIR/node.pid"
LOG_FILE="$SESSION_DIR/node.log"
PEER_FILE="$SESSION_DIR/peer_address.txt"

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

get_local_ip() {
    hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1"
}

echo -e "${CYAN}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║   DISTRIBUTED COMPUTE - INITIATOR (Device 1)              ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Build if needed
if [ ! -f "$PROJECT_ROOT/go/bin/go-node" ]; then
    echo -e "${YELLOW}Building Go node...${NC}"
    cd "$PROJECT_ROOT/go" && go build -o bin/go-node . && cd "$PROJECT_ROOT"
fi

# Setup Python
cd "$PROJECT_ROOT/python"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt 2>/dev/null || pip install -q pycapnp numpy
cd "$PROJECT_ROOT"

# Kill any existing nodes
pkill -f "go-node.*node-id=1" 2>/dev/null || true
sleep 1

# Start node
echo -e "${YELLOW}Starting Node 1...${NC}"
export LD_LIBRARY_PATH="$PROJECT_ROOT/rust/target/release:$LD_LIBRARY_PATH"
export DYLD_LIBRARY_PATH="$PROJECT_ROOT/rust/target/release:$DYLD_LIBRARY_PATH"

"$PROJECT_ROOT/go/bin/go-node" \
    -node-id=1 \
    -capnp-addr=:8080 \
    -libp2p=true \
    -local \
    -test \
    > "$LOG_FILE" 2>&1 &
echo $! > "$NODE_PID_FILE"

# Wait for startup
sleep 3

# Extract peer address
PEER_ADDR=$(grep -o '/ip4/127\.0\.0\.1/tcp/[0-9]*/p2p/[^ ]*' "$LOG_FILE" 2>/dev/null | head -1)
LOCAL_IP=$(get_local_ip)
PEER_ADDR_EXTERNAL=$(echo "$PEER_ADDR" | sed "s/127.0.0.1/$LOCAL_IP/")

if [ -z "$PEER_ADDR" ]; then
    echo -e "${RED}❌ Failed to start node${NC}"
    tail -10 "$LOG_FILE"
    exit 1
fi

echo "$PEER_ADDR_EXTERNAL" > "$PEER_FILE"

echo -e "${GREEN}✅ Node 1 started!${NC}"
echo ""
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}🔗 ON THE RESPONDER DEVICE, RUN:${NC}"
echo ""
echo -e "${YELLOW}bash tests/compute/examples/03_distributed_compute_responder.sh${NC}"
echo ""
echo -e "${CYAN}Then when prompted, paste this address:${NC}"
echo -e "${GREEN}${PEER_ADDR_EXTERNAL}${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Waiting for responder to connect...${NC}"
echo "(Press Ctrl+C to cancel)"

# Wait for responder with timeout
timeout=60
elapsed=0
while [ $elapsed -lt $timeout ]; do
    PEER_COUNT=$(grep "Connected peers: [1-9]" "$LOG_FILE" 2>/dev/null | tail -1 | grep -o '[0-9]*$' || echo "0")
    
    if [ "$PEER_COUNT" -gt 0 ]; then
        echo -e "${GREEN}✅ Responder connected!${NC}"
        break
    fi
    
    sleep 1
    elapsed=$((elapsed+1))
done

echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║         Running Distributed Matrix Multiplication         ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if responder connected
ACTUAL_PEER_COUNT=$(grep "Connected peers: [1-9]" "$LOG_FILE" 2>/dev/null | tail -1 | grep -o '[0-9]*$' || echo "0")
if [ "$ACTUAL_PEER_COUNT" -eq 0 ]; then
    echo -e "${YELLOW}⚠️  No responder connected yet${NC}"
    echo -e "${YELLOW}The test will run LOCALLY on this machine${NC}"
    echo ""
else
    echo -e "${GREEN}✅ Responder is connected${NC}"
    echo -e "${GREEN}The test will run REMOTELY on the responder node${NC}"
    echo ""
fi

# Run the compute test
cd "$PROJECT_ROOT/python"
source .venv/bin/activate

python3 examples/distributed_matrix_multiply.py \
    --size 5 \
    --generate \
    --verify \
    --connect \
    --host localhost \
    --port 8080

echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Distributed compute test completed!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
