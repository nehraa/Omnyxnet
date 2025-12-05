#!/bin/bash
# Distributed Compute - Start Node (Responder)
# Just starts the node and connects to initiator
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
NODE_PID_FILE="$SESSION_DIR/responder.pid"
LOG_FILE="$SESSION_DIR/responder.log"

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
    echo -e "${GREEN}✅ Node stopped${NC}"
}
trap cleanup EXIT

echo -e "${CYAN}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║   DISTRIBUTED COMPUTE - START NODE (Responder)            ║"
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
pkill -f "go-node.*node-id=2" 2>/dev/null || true
sleep 1

# Get peer address from user
echo -e "${YELLOW}Enter the peer address from the initiator device:${NC}"
echo -e "(looks like: /ip4/192.168.x.x/tcp/7777/p2p/Qm...)"
echo ""
read -p "> " PEER_ADDR

if [ -z "$PEER_ADDR" ]; then
    echo -e "${RED}❌ No peer address provided${NC}"
    exit 1
fi

# Extract initiator IP from peer address for later test connections
INITIATOR_IP=$(echo "$PEER_ADDR" | grep -o '/ip4/[^/]*' | sed 's|/ip4/||')

# Start node
echo ""
echo -e "${YELLOW}Starting Node 2 (responder)...${NC}"
export LD_LIBRARY_PATH="$PROJECT_ROOT/rust/target/release:$LD_LIBRARY_PATH"
export DYLD_LIBRARY_PATH="$PROJECT_ROOT/rust/target/release:$DYLD_LIBRARY_PATH"

"$PROJECT_ROOT/go/bin/go-node" \
    -node-id=2 \
    -capnp-addr=0.0.0.0:8081 \
    -libp2p=true \
    -libp2p-port=7778 \
    -test \
    -peers="$PEER_ADDR" \
    > "$LOG_FILE" 2>&1 &
echo $! > "$NODE_PID_FILE"

# Wait for connection
echo -e "${YELLOW}Connecting to initiator...${NC}"
sleep 5

# Check connection
PEER_COUNT=$(grep "Connected peers: [1-9]" "$LOG_FILE" 2>/dev/null | tail -1 | grep -o '[0-9]*$' || echo "0")

if [ "$PEER_COUNT" -gt 0 ]; then
    # Extract connected peer info from logs
    CONNECTED_PEER=$(grep "PEER CONNECTED" "$LOG_FILE" 2>/dev/null | tail -1)
    PEER_IP=$(echo "$CONNECTED_PEER" | grep -o 'IP=[^ ]*' | sed 's/IP=//')
    PEER_ID=$(echo "$CONNECTED_PEER" | grep -o 'PeerID=[^ ]*' | sed 's/PeerID=//' | cut -c1-12)
    
    echo -e "${GREEN}✅ Connected to initiator!${NC}"
    echo ""
    echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}🎉 CONNECTION ESTABLISHED!${NC}"
    echo ""
    echo -e "  ${CYAN}This Node (Responder/Worker):${NC}"
    echo -e "    Role: WORKER - will execute tasks sent by initiator"
    echo -e "    Libp2p Port: 7778"
    echo ""
    echo -e "  ${CYAN}Connected To (Initiator/Manager):${NC}"
    echo -e "    IP Address: ${GREEN}${INITIATOR_IP}${NC}"
    echo -e "    Peer ID: ${GREEN}${PEER_ID}...${NC}"
    echo ""
    echo -e "  ${YELLOW}When initiator sends a task, you will see execution logs below.${NC}"
    echo ""
    echo -e "You can now run tests from setup.sh on the INITIATOR device:"
    echo -e "  ${YELLOW}→ Option 18 → Run Distributed Test${NC}"
    echo ""
    echo -e "Or directly (from initiator device):"
    echo -e "  ${YELLOW}python3 python/examples/distributed_matrix_multiply.py --connect --host ${INITIATOR_IP} --port 8080 --size 100 --generate --verify${NC}"
    echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
else
    echo -e "${YELLOW}⚠️  Connection in progress...${NC}"
    echo "Check log: $LOG_FILE"
fi

echo ""
echo -e "${YELLOW}Node running. Keep this terminal open. (Ctrl+C to stop)${NC}"
echo -e "${CYAN}📋 Watching for incoming compute tasks...${NC}"
echo ""

# Track what we've already shown
LAST_TASK_LINE=0

# Keep running and show task execution logs
while true; do
    sleep 1
    if [ ! -f "$NODE_PID_FILE" ]; then
        break
    fi
    pid=$(cat "$NODE_PID_FILE")
    if ! ps -p "$pid" > /dev/null 2>&1; then
        echo -e "${RED}Node stopped unexpectedly. Log output:${NC}"
        echo "------------------------------------------------"
        cat "$LOG_FILE"
        echo "------------------------------------------------"
        break
    fi
    
    # Show connection status periodically
    NEW_PEER_COUNT=$(grep "Connected peers: [0-9]" "$LOG_FILE" 2>/dev/null | tail -1 | grep -o '[0-9]*$' || echo "0")
    if [ "$NEW_PEER_COUNT" != "$PEER_COUNT" ]; then
        PEER_COUNT=$NEW_PEER_COUNT
        echo -e "${GREEN}Connected peers: ${PEER_COUNT}${NC}"
    fi
    
    # Show compute task logs (incoming tasks and execution)
    CURRENT_LINES=$(wc -l < "$LOG_FILE" 2>/dev/null | tr -d ' ')
    if [ "$CURRENT_LINES" -gt "$LAST_TASK_LINE" ]; then
        # Extract compute-related lines we haven't shown yet
        tail -n +$((LAST_TASK_LINE + 1)) "$LOG_FILE" 2>/dev/null | while read -r line; do
            # Show task received
            if echo "$line" | grep -q "\[COMPUTE\] Received task"; then
                task_id=$(echo "$line" | grep -o 'task [^ ]*' | head -1)
                chunk=$(echo "$line" | grep -o 'chunk [0-9]*' | head -1)
                bytes=$(echo "$line" | grep -o '[0-9]* bytes' | head -1)
                echo ""
                echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
                echo -e "${CYAN}📥 INCOMING TASK FROM INITIATOR${NC}"
                echo -e "   Task: ${task_id}"
                echo -e "   Chunk: ${chunk}"
                echo -e "   Input: ${bytes}"
                echo -e "${YELLOW}   ⚙️  Executing computation...${NC}"
            fi
            # Show task completed
            if echo "$line" | grep -q "\[COMPUTE\] Task .* completed"; then
                task_id=$(echo "$line" | grep -o 'Task [^ ]*' | head -1)
                exec_time=$(echo "$line" | grep -o 'in [0-9]*ms' | head -1)
                result_size=$(echo "$line" | grep -o 'result: [0-9]* bytes' | head -1)
                echo -e "${GREEN}   ✅ COMPLETED!${NC}"
                echo -e "   Execution time: ${exec_time}"
                echo -e "   Result: ${result_size}"
                echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            fi
        done
        LAST_TASK_LINE=$CURRENT_LINES
    fi
done
