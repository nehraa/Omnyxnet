#!/bin/bash
# Distributed Compute - Start Node (Initiator)
# Just starts the node and waits for connections
# Does NOT run any tests - that's separate

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Session files
SESSION_DIR="$HOME/.pangea/distributed"
mkdir -p "$SESSION_DIR"
NODE_PID_FILE="$SESSION_DIR/initiator.pid"
LOG_FILE="$SESSION_DIR/initiator.log"
CONNECTION_FILE="$SESSION_DIR/connection.txt"

# Cleanup
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down node...${NC}"
    if [ -f "$NODE_PID_FILE" ]; then
        local pid=$(cat "$NODE_PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            kill "$pid" 2>/dev/null || true
        fi
        rm -f "$NODE_PID_FILE"
    fi
    rm -f "$CONNECTION_FILE"
    echo -e "${GREEN}✅ Node stopped${NC}"
}
trap cleanup EXIT

get_local_ip() {
    # Try to get external IP
    local ip=$(ifconfig 2>/dev/null | grep "inet " | grep -v "127.0.0.1" | head -1 | awk '{print $2}')
    if [ -z "$ip" ]; then
        ip=$(hostname -I 2>/dev/null | awk '{print $1}')
    fi
    if [ -z "$ip" ]; then
        ip="127.0.0.1"
    fi
    echo "$ip"
}

echo -e "${CYAN}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║   DISTRIBUTED COMPUTE - START NODE (Initiator)            ║"
echo "║   This just starts the node - run tests separately        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Build if needed (or if source files changed)
NEED_BUILD=false
if [ ! -f "$PROJECT_ROOT/go/bin/go-node" ]; then
    NEED_BUILD=true
else
    # Check if any Go source files are newer than the binary
    NEWEST_GO=$(find "$PROJECT_ROOT/go" -name "*.go" -newer "$PROJECT_ROOT/go/bin/go-node" 2>/dev/null | head -1)
    if [ -n "$NEWEST_GO" ]; then
        echo -e "${YELLOW}Source files changed, rebuilding...${NC}"
        NEED_BUILD=true
    fi
fi

if [ "$NEED_BUILD" = true ]; then
    echo -e "${YELLOW}Building Go node...${NC}"
    cd "$PROJECT_ROOT/go" && go build -o bin/go-node . && cd "$PROJECT_ROOT"
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Build failed${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Build complete${NC}"
fi

# Kill any existing nodes
pkill -f "go-node.*node-id=1" 2>/dev/null || true
sleep 1

# Start node
echo -e "${YELLOW}Starting Node 1 (initiator)...${NC}"
export LD_LIBRARY_PATH="$PROJECT_ROOT/rust/target/release:$LD_LIBRARY_PATH"
export DYLD_LIBRARY_PATH="$PROJECT_ROOT/rust/target/release:$DYLD_LIBRARY_PATH"

"$PROJECT_ROOT/go/bin/go-node" \
    -node-id=1 \
    -capnp-addr=0.0.0.0:8080 \
    -libp2p=true \
    -libp2p-port=7777 \
    -test \
    > "$LOG_FILE" 2>&1 &
echo $! > "$NODE_PID_FILE"

# Wait for startup
sleep 3

# Extract peer address
PEER_ADDR=$(grep -o '/ip4/[^/]*/tcp/[0-9]*/p2p/[^ ]*' "$LOG_FILE" 2>/dev/null | grep -v "127.0.0.1" | head -1)
if [ -z "$PEER_ADDR" ]; then
    PEER_ADDR=$(grep -o '/ip4/127\.0\.0\.1/tcp/[0-9]*/p2p/[^ ]*' "$LOG_FILE" 2>/dev/null | head -1)
fi

LOCAL_IP=$(get_local_ip)
PEER_ADDR_EXTERNAL=$(echo "$PEER_ADDR" | sed "s/127.0.0.1/$LOCAL_IP/")

if [ -z "$PEER_ADDR" ]; then
    echo -e "${RED}❌ Failed to start node${NC}"
    tail -10 "$LOG_FILE"
    exit 1
fi

# Save connection info for other scripts
echo "INITIATOR_IP=$LOCAL_IP" > "$CONNECTION_FILE"
echo "INITIATOR_PORT=8080" >> "$CONNECTION_FILE"
echo "PEER_ADDR=$PEER_ADDR_EXTERNAL" >> "$CONNECTION_FILE"

echo -e "${GREEN}✅ Node 1 started!${NC}"
echo ""
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}📋 CONNECTION INFO${NC}"
echo ""
echo -e "   Initiator IP: ${GREEN}${LOCAL_IP}${NC}"
echo -e "   Cap'n Proto:  ${GREEN}${LOCAL_IP}:8080${NC}"
echo ""
echo -e "${CYAN}🔗 FOR RESPONDER (other device), paste this address:${NC}"
echo -e "${GREEN}${PEER_ADDR_EXTERNAL}${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo ""

# Monitor connections
echo -e "${YELLOW}Waiting for connections... (Ctrl+C to stop)${NC}"
echo ""

LAST_PEER_COUNT=0
LAST_WORKER_LINE=0
while true; do
    PEER_COUNT=$(grep "Connected peers: [0-9]" "$LOG_FILE" 2>/dev/null | tail -1 | grep -o '[0-9]*$' || echo "0")
    
    if [ "$PEER_COUNT" != "$LAST_PEER_COUNT" ]; then
        if [ "$PEER_COUNT" -gt 0 ]; then
            # Get worker info
            WORKER_INFO=$(grep "PEER CONNECTED" "$LOG_FILE" 2>/dev/null | tail -1)
            WORKER_IP=$(echo "$WORKER_INFO" | grep -o 'IP=[^ ]*' | sed 's/IP=//')
            WORKER_PEER_ID=$(echo "$WORKER_INFO" | grep -o 'PeerID=[^ ]*' | sed 's/PeerID=//' | cut -c1-12)
            
            echo -e "${GREEN}✅ Connected peers: ${PEER_COUNT}${NC}"
            echo ""
            echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
            echo -e "${GREEN}🎉 WORKER CONNECTED!${NC}"
            echo ""
            echo -e "  ${CYAN}This Node (Initiator/Manager):${NC}"
            echo -e "    Role: MANAGER - will send tasks to workers"
            echo -e "    IP: ${LOCAL_IP}"
            echo ""
            echo -e "  ${CYAN}Connected Worker:${NC}"
            echo -e "    IP Address: ${GREEN}${WORKER_IP}${NC}"
            echo -e "    Peer ID: ${GREEN}${WORKER_PEER_ID}...${NC}"
            echo ""
            echo -e "You can now run tests from setup.sh:"
            echo -e "  ${YELLOW}→ Option 18 → Run Distributed Test${NC}"
            echo ""
            echo -e "Or directly:"
            echo -e "  ${YELLOW}python3 python/examples/distributed_matrix_multiply.py --connect --host localhost --port 8080 --size 100 --generate --verify${NC}"
            echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
        else
            echo -e "${YELLOW}⏳ Connected peers: ${PEER_COUNT}${NC}"
        fi
        LAST_PEER_COUNT=$PEER_COUNT
    fi
    
    sleep 2
done
