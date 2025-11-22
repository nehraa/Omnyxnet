#!/bin/bash
# Easy test script for Pangea Net - Run on each device
# This script handles everything automatically:
# 1. Auto-detects if it's the first node or joining node
# 2. Builds binaries if needed
# 3. Starts node with proper configuration
# 4. Provides simple file upload/download commands

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

clear
echo "╔════════════════════════════════════════╗"
echo "║   🌍 Pangea Net - Easy Device Test    ║"
echo "╚════════════════════════════════════════╝"
echo ""

# Find project root
if [ -f "go/bin/go-node" ] || [ -f "go/main.go" ]; then
    PROJECT_ROOT="$(pwd)"
elif [ -f "../go/main.go" ]; then
    PROJECT_ROOT="$(cd .. && pwd)"
else
    echo -e "${RED}❌ Error: Cannot find Pangea Net installation${NC}"
    echo "Please run this script from the project root or scripts directory"
    exit 1
fi

cd "$PROJECT_ROOT"

# Parse command line arguments
NODE_ID=${1:-}
BOOTSTRAP=${2:-}

# Interactive mode if no arguments
if [ -z "$NODE_ID" ]; then
    echo -e "${CYAN}Select mode:${NC}"
    echo "  1. First device (bootstrap node)"
    echo "  2. Additional device (connect to network)"
    echo ""
    read -p "Enter choice (1 or 2): " choice
    
    if [ "$choice" == "1" ]; then
        NODE_ID=1
        echo ""
        echo -e "${GREEN}✓${NC} You selected: First device (bootstrap)"
    elif [ "$choice" == "2" ]; then
        read -p "Enter node ID (e.g., 2, 3, 4...): " NODE_ID
        echo ""
        echo -e "${YELLOW}ℹ${NC}  From Device 1 logs, copy just the peer ID (12D3Koo...)"
        read -p "Bootstrap IP: " BOOTSTRAP_IP
        read -p "Bootstrap Peer ID: " PEER_ID
        BOOTSTRAP="/ip4/${BOOTSTRAP_IP}/tcp/9180/p2p/${PEER_ID}"
        echo ""
        echo -e "${GREEN}✓${NC} Device #${NODE_ID} → /ip4/${BOOTSTRAP_IP}/tcp/9180/p2p/${PEER_ID}"
    else
        echo -e "${RED}Invalid choice${NC}"
        exit 1
    fi
    echo ""
fi

# Configuration
CAPNP_PORT=$((8080 + NODE_ID - 1))
P2P_PORT=$((9080 + NODE_ID - 1))
DHT_PORT=$((9180 + NODE_ID - 1))
DATA_DIR="$HOME/.pangea/node-$NODE_ID"

mkdir -p "$DATA_DIR/cache"
mkdir -p "$DATA_DIR/logs"
mkdir -p "$DATA_DIR/uploads"
mkdir -p "$DATA_DIR/downloads"

echo -e "${BLUE}Configuration:${NC}"
echo "  Node ID: $NODE_ID"
echo "  Cap'n Proto Port: $CAPNP_PORT"
echo "  P2P Port: $P2P_PORT" 
echo "  DHT Port: $DHT_PORT"
echo "  Data Directory: $DATA_DIR"
if [ -n "$BOOTSTRAP" ]; then
    echo "  Bootstrap Peer: $BOOTSTRAP"
else
    echo "  Mode: Bootstrap (first node)"
fi
echo ""

# Check and build binaries
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${BLUE}📦 Build Check${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"

BUILD_NEEDED=false

if [ ! -f "go/bin/go-node" ]; then
    echo "Go binary not found, building..."
    BUILD_NEEDED=true
    cd go && go build -o bin/go-node . || exit 1
    cd ..
    echo -e "${GREEN}✅ Go node built${NC}"
else
    echo -e "${GREEN}✅ Go binary ready${NC}"
fi

if [ ! -f "rust/target/release/libpangea_ces.so" ] && [ ! -f "rust/target/release/libpangea_ces.dylib" ]; then
    echo "Rust library not found, building..."
    BUILD_NEEDED=true
    cd rust && cargo build --release || exit 1
    cd ..
    echo -e "${GREEN}✅ Rust library built${NC}"
else
    echo -e "${GREEN}✅ Rust library ready${NC}"
fi

echo ""

# Start the node
LOG_FILE="$DATA_DIR/logs/node.log"

echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${BLUE}🚀 Starting Node${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"

# Set library path for Rust FFI
export LD_LIBRARY_PATH="$PROJECT_ROOT/rust/target/release:$LD_LIBRARY_PATH"
export DYLD_LIBRARY_PATH="$PROJECT_ROOT/rust/target/release:$DYLD_LIBRARY_PATH"

# Build command
CMD="./go/bin/go-node -node-id=$NODE_ID -capnp-addr=:$CAPNP_PORT -libp2p=true"

if [ -n "$BOOTSTRAP" ]; then
    CMD="$CMD -peers=$BOOTSTRAP"
else
    CMD="$CMD -local=true"
fi

# Start in background with nohup for persistence
nohup $CMD > "$LOG_FILE" 2>&1 &
NODE_PID=$!
disown
echo $NODE_PID > "$DATA_DIR/node.pid"

echo -e "${GREEN}✅ Node started (PID: $NODE_PID)${NC}"
echo ""

# Wait and verify
sleep 3

if ! ps -p $NODE_PID > /dev/null 2>&1; then
    echo -e "${RED}❌ Node failed to start!${NC}"
    echo "Check log: $LOG_FILE"
    tail -20 "$LOG_FILE"
    exit 1
fi

echo -e "${GREEN}✅ Node is running!${NC}"
echo ""

# Get IP address for other devices (try multiple methods for portability)
if command -v hostname &> /dev/null; then
    # Select the first private IP address (192.168.x.x, 10.x.x.x, 172.16-31.x.x)
    IP_ADDR=$(hostname -I 2>/dev/null | tr ' ' '\n' | grep -E '^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[0-1])\.)' | head -n 1)
    # If no private IP found, fall back to the first IP
    if [ -z "$IP_ADDR" ]; then
        IP_ADDR=$(hostname -I 2>/dev/null | awk '{print $1}')
    fi
fi
if [ -z "$IP_ADDR" ] && command -v ip &> /dev/null; then
    # Try getting IP from active interface
    IP_ADDR=$(ip addr show 2>/dev/null | grep -oP 'inet \K[\d.]+' | grep -v '^127\.' | head -1)
fi
if [ -z "$IP_ADDR" ] && command -v ip &> /dev/null; then
    # Fallback to ip route (requires connectivity)
    IP_ADDR=$(ip route get 1.1.1.1 2>/dev/null | grep -oP 'src \K\S+' || true)
fi
if [ -z "$IP_ADDR" ] && command -v ifconfig &> /dev/null; then
    # Additional fallback for systems with ifconfig
    IP_ADDR=$(ifconfig 2>/dev/null | grep -oE 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -oE '([0-9]*\.){3}[0-9]*' | grep -v '^127\.' | head -1)
fi
if [ -z "$IP_ADDR" ]; then
    IP_ADDR="<your-ip-address>"
fi

echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${BLUE}📋 Connection Info${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo ""
echo -e "${CYAN}For other devices to join this network:${NC}"
echo -e "${YELLOW}  ./scripts/easy_test.sh <NODE_ID> /ip4/${IP_ADDR}/tcp/${DHT_PORT}${NC}"
echo ""
echo -e "Example:"
echo -e "  ${YELLOW}./scripts/easy_test.sh 2 /ip4/${IP_ADDR}/tcp/${DHT_PORT}${NC}"
echo ""

# Create helper script for file operations
cat > "$DATA_DIR/commands.sh" << 'EOF'
#!/bin/bash
# Pangea Net Node Commands

NODE_ID=$1
PROJECT_ROOT=$2
DATA_DIR=$3

upload() {
    FILE=$1
    if [ -z "$FILE" ]; then
        echo "Usage: upload <file>"
        return 1
    fi
    
    if [ ! -f "$FILE" ]; then
        echo "Error: File not found: $FILE"
        return 1
    fi
    
    echo "Uploading: $FILE"
    # Copy to uploads directory
    cp "$FILE" "$DATA_DIR/uploads/"
    FILENAME=$(basename "$FILE")
    
    # Note: Upload CLI integration pending. File staged but not yet distributed.
    # The Rust upload protocol is implemented but CLI wiring is in progress.
    echo "File staged for upload: $DATA_DIR/uploads/$FILENAME"
    echo ""
    echo "When CLI integration is complete, upload will:"
    echo "  1. Compress (zstd)"
    echo "  2. Encrypt (ChaCha20-Poly1305)"
    echo "  3. Shard (Reed-Solomon)"
    echo "  4. Distribute to peers via Go node"
    echo ""
    echo "Status: CLI integration in progress"
}

download() {
    HASH=$1
    if [ -z "$HASH" ]; then
        echo "Usage: download <file_hash>"
        return 1
    fi
    
    echo "Downloading file with hash: $HASH"
    # TODO: Call Rust download CLI when available
    echo "Download will:"
    echo "  1. Query DHT for file location"
    echo "  2. Check local cache first"
    echo "  3. Fetch shards from peers"
    echo "  4. Reconstruct via Reed-Solomon"
    echo "  5. Decrypt and decompress"
    echo "  6. Save to: $DATA_DIR/downloads/"
}

list_files() {
    echo "Cached files:"
    # TODO: Query cache for manifests
    ls -lh "$DATA_DIR/cache/" 2>/dev/null || echo "  (cache empty)"
}

status() {
    if [ -f "$DATA_DIR/node.pid" ]; then
        PID=$(cat "$DATA_DIR/node.pid")
    else
        PID=""
    fi
    if [ -n "$PID" ] && ps -p $PID > /dev/null 2>&1; then
        echo "Node Status: RUNNING (PID: $PID)"
    else
        echo "Node Status: STOPPED"
    fi
    
    echo ""
    echo "Directories:"
    echo "  Cache:     $([ -d "$DATA_DIR/cache" ] && du -sh "$DATA_DIR/cache" 2>/dev/null | cut -f1 || echo "N/A")"
    echo "  Uploads:   $([ -d "$DATA_DIR/uploads" ] && ls "$DATA_DIR/uploads" 2>/dev/null | wc -l || echo "N/A") files"
    echo "  Downloads: $([ -d "$DATA_DIR/downloads" ] && ls "$DATA_DIR/downloads" 2>/dev/null | wc -l || echo "N/A") files"
}

logs() {
    tail -f "$DATA_DIR/logs/node.log"
}

stop() {
    PID=$(cat "$DATA_DIR/node.pid" 2>/dev/null)
    if [ -n "$PID" ]; then
        kill $PID 2>/dev/null && echo "Node stopped" || echo "Node not running"
    else
        echo "No PID file found"
    fi
}

help() {
    echo "Pangea Net Node Commands:"
    echo ""
    echo "  upload <file>         Upload a file to the network"
    echo "  download <hash>       Download a file by hash"
    echo "  list                  List cached files"
    echo "  status                Show node status"
    echo "  logs                  View node logs (Ctrl+C to exit)"
    echo "  stop                  Stop the node"
    echo "  help                  Show this help"
}

# Parse command
case "$4" in
    upload)
        upload "$5"
        ;;
    download)
        download "$5"
        ;;
    list|list_files)
        list_files
        ;;
    status)
        status
        ;;
    logs)
        logs
        ;;
    stop)
        stop
        ;;
    help|*)
        help
        ;;
esac
EOF

chmod +x "$DATA_DIR/commands.sh"

echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${BLUE}🎮 Quick Commands${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo ""
echo -e "${CYAN}Use these commands to interact with your node:${NC}"
echo ""
echo -e "  ${YELLOW}Status:${NC}"
echo -e "    $DATA_DIR/commands.sh $NODE_ID '$PROJECT_ROOT' '$DATA_DIR' status"
echo ""
echo -e "  ${YELLOW}Upload a file:${NC}"
echo -e "    $DATA_DIR/commands.sh $NODE_ID '$PROJECT_ROOT' '$DATA_DIR' upload /path/to/file"
echo ""
echo -e "  ${YELLOW}Download a file:${NC}"
echo -e "    $DATA_DIR/commands.sh $NODE_ID '$PROJECT_ROOT' '$DATA_DIR' download <file_hash>"
echo ""
echo -e "  ${YELLOW}View logs:${NC}"
echo -e "    $DATA_DIR/commands.sh $NODE_ID '$PROJECT_ROOT' '$DATA_DIR' logs"
echo ""
echo -e "  ${YELLOW}Stop node:${NC}"
echo -e "    $DATA_DIR/commands.sh $NODE_ID '$PROJECT_ROOT' '$DATA_DIR' stop"
echo ""

# Create easy alias with properly quoted variables
cat > "$DATA_DIR/alias.sh" << EOF
alias pangea="$DATA_DIR/commands.sh $NODE_ID '$PROJECT_ROOT' '$DATA_DIR'"
EOF
echo ""
echo -e "${GREEN}💡 Pro tip:${NC} Add this alias to your shell:"
echo -e "    ${YELLOW}source $DATA_DIR/alias.sh${NC}"
echo -e "    Then you can just type: ${YELLOW}pangea status${NC}"
echo ""

echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${BLUE}📊 Node Information${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo ""
echo "  Node ID:       $NODE_ID"
echo "  PID:           $NODE_PID"
echo "  Log File:      $LOG_FILE"
echo "  Data Dir:      $DATA_DIR"
echo "  Cache Dir:     $DATA_DIR/cache"
echo "  Your IP:       $IP_ADDR"
echo ""
echo -e "${GREEN}✅ Node setup complete!${NC}"
echo ""
echo -e "${YELLOW}Keep this terminal open or press Ctrl+C to detach.${NC}"
echo -e "${YELLOW}The node will continue running in the background.${NC}"
echo ""

# Show live log tail (user can Ctrl+C)
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${BLUE}📝 Live Logs (Ctrl+C to detach)${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo ""

tail -f "$LOG_FILE" 2>/dev/null || true
