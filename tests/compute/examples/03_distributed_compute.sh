#!/bin/bash
# Distributed Compute - Matrix Multiplication across devices
# 
# This test:
# 1. Starts Node 1 (Coordinator) on THIS device
# 2. Waits for you to connect another device running a Go node
# 3. Runs distributed matrix multiplication across the connected nodes
#
# To run on the OTHER device:
#   cd go && ./bin/go-node -node-id=2 -capnp-addr=:8080 -local -test -peers="<multiaddr>"

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"
cd "$PROJECT_ROOT"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Cleanup function
cleanup() {
    echo ""
    echo -e "${YELLOW}🧹 Cleaning up...${NC}"
    pkill -f "go-node.*node-id=1" 2>/dev/null || true
    sleep 1
}
trap cleanup EXIT

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     DISTRIBUTED COMPUTE - Cross-Device Matrix Multiply       ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ============================================================
# 0. Kill any existing nodes
# ============================================================
echo -e "${YELLOW}🛑 Stopping any existing Go nodes...${NC}"
pkill -f "go-node" 2>/dev/null || true
sleep 2

# Wait for port 8080 to be available
retries=5
while lsof -i :8080 >/dev/null 2>&1 && [ $retries -gt 0 ]; do
    echo "   Waiting for port 8080 to free..."
    sleep 1
    retries=$((retries-1))
done
echo -e "   ${GREEN}✅ Ready${NC}"
echo ""

# ============================================================
# 1. Build Go node if needed
# ============================================================
echo -e "${YELLOW}🔨 Step 1: Ensuring Go node is built...${NC}"
if [ ! -f "$PROJECT_ROOT/go/bin/go-node" ]; then
    echo "   Building go-node..."
    cd "$PROJECT_ROOT/go" && go build -o bin/go-node . && cd "$PROJECT_ROOT"
fi
echo -e "   ${GREEN}✅ Go node binary ready${NC}"
echo ""

# ============================================================
# 2. Set up Python virtual environment
# ============================================================
echo -e "${YELLOW}🐍 Step 2: Setting up Python environment...${NC}"
cd "$PROJECT_ROOT/python"

if [ ! -d ".venv" ]; then
    echo "   Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate
pip install -q -r requirements.txt 2>/dev/null || pip install -q pycapnp numpy

echo -e "   ${GREEN}✅ Python environment ready${NC}"
cd "$PROJECT_ROOT"
echo ""

# ============================================================
# 3. Start Go Node 1 (Coordinator)
# ============================================================
echo -e "${YELLOW}🚀 Step 3: Starting Go Node 1 (Coordinator) on :8080...${NC}"

# Set library paths for Rust
export LD_LIBRARY_PATH="$PROJECT_ROOT/rust/target/release:$LD_LIBRARY_PATH"
export DYLD_LIBRARY_PATH="$PROJECT_ROOT/rust/target/release:$DYLD_LIBRARY_PATH"

"$PROJECT_ROOT/go/bin/go-node" \
    -node-id=1 \
    -capnp-addr=:8080 \
    -libp2p=true \
    -local \
    -test \
    > /tmp/go_node_1.log 2>&1 &
NODE1_PID=$!

echo "   Started Node 1 (PID: $NODE1_PID)"

# Wait for Node 1 to be ready
retries=10
while ! nc -z localhost 8080 2>/dev/null && [ $retries -gt 0 ]; do
    sleep 0.5
    retries=$((retries-1))
done

if ! nc -z localhost 8080 2>/dev/null; then
    echo -e "   ${RED}❌ Node 1 failed to start${NC}"
    cat /tmp/go_node_1.log
    exit 1
fi

echo -e "   ${GREEN}✅ Node 1 running on :8080${NC}"
echo ""

# ============================================================
# 4. Get Node 1's libp2p multiaddr for other devices
# ============================================================
echo -e "${YELLOW}🔗 Step 4: Getting connection info for other devices...${NC}"
sleep 1

# Get local IP
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")

# Extract multiaddr from log
NODE1_MULTIADDR=""
for i in {1..5}; do
    NODE1_MULTIADDR=$(grep -o '/ip4/127\.0\.0\.1/tcp/[0-9]*/p2p/[^ ]*' /tmp/go_node_1.log 2>/dev/null | head -1)
    if [ -n "$NODE1_MULTIADDR" ]; then
        break
    fi
    sleep 0.5
done

# Replace 127.0.0.1 with actual IP for cross-device connection
if [ -n "$NODE1_MULTIADDR" ]; then
    NODE1_MULTIADDR_EXTERNAL=$(echo "$NODE1_MULTIADDR" | sed "s/127.0.0.1/$LOCAL_IP/")
fi

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║           CONNECT ANOTHER DEVICE TO THIS NODE                ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "On the OTHER device, run:"
echo ""
echo -e "${GREEN}cd go && ./bin/go-node -node-id=2 -capnp-addr=:8080 -local -test \\${NC}"
echo -e "${GREEN}    -peers=\"$NODE1_MULTIADDR_EXTERNAL\"${NC}"
echo ""
echo -e "Or for same machine (testing): ${YELLOW}$NODE1_MULTIADDR${NC}"
echo ""

# ============================================================
# 5. Wait for peer connection
# ============================================================
echo -e "${YELLOW}🔍 Step 5: Waiting for another device to connect...${NC}"
echo "   (Press Enter when the other device is connected, or wait for auto-detect)"
echo ""

# Monitor for peer connection in background
connected=false
timeout=60
elapsed=0

while [ $elapsed -lt $timeout ]; do
    # Check if peers connected
    PEER_COUNT=$(grep "Connected peers: [1-9]" /tmp/go_node_1.log 2>/dev/null | tail -1 | grep -o '[0-9]*$' || echo "0")
    
    if [ "$PEER_COUNT" -gt 0 ]; then
        echo -e "   ${GREEN}✅ Connected! Found $PEER_COUNT peer(s)${NC}"
        connected=true
        break
    fi
    
    # Check for user input (non-blocking)
    if read -t 1 -n 1; then
        echo ""
        echo -e "   ${YELLOW}Proceeding without waiting...${NC}"
        break
    fi
    
    elapsed=$((elapsed+1))
    
    # Show progress every 5 seconds
    if [ $((elapsed % 5)) -eq 0 ]; then
        echo "   Waiting... ($elapsed seconds, press Enter to proceed)"
    fi
done

if [ "$connected" = false ]; then
    PEER_COUNT=$(grep "Connected peers" /tmp/go_node_1.log 2>/dev/null | tail -1 | grep -o '[0-9]*$' || echo "0")
    if [ "$PEER_COUNT" -gt 0 ]; then
        echo -e "   ${GREEN}✅ Connected! Found $PEER_COUNT peer(s)${NC}"
    else
        echo -e "   ${YELLOW}⚠️  No peers connected yet (will run locally on this node)${NC}"
    fi
fi
echo ""

# ============================================================
# 6. Run Distributed Matrix Multiplication
# ============================================================
echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          Running Distributed Matrix Multiplication           ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "The computation uses the MapReduce pattern:"
echo "  📊 SPLIT  → Coordinator breaks matrices into blocks"
echo "  🔧 EXECUTE → Worker nodes compute block multiplications"  
echo "  🔗 MERGE  → Coordinator combines results"
echo ""

cd "$PROJECT_ROOT/python"
source .venv/bin/activate

# Run with connection to Node 1 (coordinator)
python3 examples/distributed_matrix_multiply.py \
    --size 5 \
    --generate \
    --verify \
    --connect \
    --host localhost \
    --port 8080

echo ""

# ============================================================
# 7. Show execution summary
# ============================================================
echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    EXECUTION SUMMARY                         ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if distributed execution happened
if grep -q "Delegating chunk" /tmp/go_node_1.log 2>/dev/null; then
    echo -e "${GREEN}✅ DISTRIBUTED EXECUTION: Chunks were delegated to worker nodes!${NC}"
    grep "Delegating chunk" /tmp/go_node_1.log 2>/dev/null | head -5
elif grep -q "completed locally" /tmp/go_node_1.log 2>/dev/null; then
    echo -e "${YELLOW}⚠️  LOCAL EXECUTION: Job ran on this node only${NC}"
    echo "   Connect another device to enable distributed execution"
fi

echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}✅ Compute test completed!${NC}"
echo -e "${GREEN}============================================================${NC}"

