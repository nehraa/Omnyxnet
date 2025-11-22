#!/bin/bash
# Simple cross-device setup for Pangea Net
# Run this script on each device to start a node

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "========================================"
echo "🌍 Pangea Net - Cross-Device Setup"
echo "========================================"
echo ""

# Detect project root
if [ -f "go/bin/go-node" ]; then
    PROJECT_ROOT="$(pwd)"
elif [ -f "../go/bin/go-node" ]; then
    PROJECT_ROOT="$(cd .. && pwd)"
else
    echo "Error: Cannot find Pangea Net installation"
    echo "Please run this script from the project root or scripts directory"
    exit 1
fi

cd "$PROJECT_ROOT"

# Configuration
NODE_ID=${1:-1}
CAPNP_PORT=${2:-8080}
P2P_PORT=${3:-9080}
DHT_PORT=${4:-9180}
BOOTSTRAP_PEER=${5:-}

echo "Configuration:"
echo "  Node ID: $NODE_ID"
echo "  Cap'n Proto Port: $CAPNP_PORT"
echo "  P2P Port: $P2P_PORT"
echo "  DHT Port: $DHT_PORT"
if [ -n "$BOOTSTRAP_PEER" ]; then
    echo "  Bootstrap Peer: $BOOTSTRAP_PEER"
else
    echo "  Bootstrap Peer: None (will use mDNS for local discovery)"
fi
echo ""

# Check if binaries exist
if [ ! -f "go/bin/go-node" ]; then
    echo "Building Go node..."
    cd go && go build -o bin/go-node . || exit 1
    cd ..
    echo -e "${GREEN}✅ Go node built${NC}"
fi

if [ ! -f "rust/target/release/libpangea_ces.so" ] && [ ! -f "rust/target/release/libpangea_ces.dylib" ]; then
    echo "Building Rust library..."
    cd rust && cargo build --release || exit 1
    cd ..
    echo -e "${GREEN}✅ Rust library built${NC}"
fi

# Create data directory for this node
DATA_DIR="$HOME/.pangea/node-$NODE_ID"
mkdir -p "$DATA_DIR/cache"
mkdir -p "$DATA_DIR/logs"

echo "Data directory: $DATA_DIR"
echo ""

# Start the node
LOG_FILE="$DATA_DIR/logs/node.log"

echo -e "${BLUE}Starting Pangea Net Node $NODE_ID...${NC}"
echo "Log file: $LOG_FILE"
echo ""

# Build the command
CMD="./go/bin/go-node -node-id=$NODE_ID -capnp-addr=:$CAPNP_PORT -libp2p=true"

# Add bootstrap peer if provided
if [ -n "$BOOTSTRAP_PEER" ]; then
    CMD="$CMD -peers=$BOOTSTRAP_PEER"
else
    CMD="$CMD -local=true"
fi

# Start the node in the background
$CMD > "$LOG_FILE" 2>&1 &
NODE_PID=$!

echo -e "${GREEN}✅ Node started with PID: $NODE_PID${NC}"
echo ""

# Save PID to file
echo $NODE_PID > "$DATA_DIR/node.pid"

# Wait a moment and check if it's still running
sleep 2

if ps -p $NODE_PID > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Node is running successfully!${NC}"
    echo ""
    echo "📋 Connection Information:"
    echo "  - Node ID: $NODE_ID"
    echo "  - Cap'n Proto: localhost:$CAPNP_PORT"
    echo "  - P2P: localhost:$P2P_PORT"
    echo "  - DHT: localhost:$DHT_PORT"
    echo ""
    echo "📂 Directories:"
    echo "  - Data: $DATA_DIR"
    echo "  - Cache: $DATA_DIR/cache"
    echo "  - Logs: $LOG_FILE"
    echo ""
    echo "🔧 Management Commands:"
    echo "  - View logs: tail -f $LOG_FILE"
    echo "  - Stop node: kill $NODE_PID"
    echo "  - Check status: ps -p $NODE_PID"
    echo ""
    echo -e "${YELLOW}Keep this terminal open or run in background.${NC}"
    echo -e "${YELLOW}To stop the node, run: kill $NODE_PID${NC}"
else
    echo -e "${RED}❌ Node failed to start!${NC}"
    echo "Check the log file for errors: $LOG_FILE"
    exit 1
fi
