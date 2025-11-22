#!/bin/bash
# Test script for automated file upload/download functionality

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
    echo -e "${RED}❌ Error: Cannot find Pangea Net installation${NC}"
    exit 1
fi

cd "$PROJECT_ROOT"

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   🌍 Pangea Net - Automated Test      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# Export library path for Rust FFI
export LD_LIBRARY_PATH="$PROJECT_ROOT/rust/target/release:$LD_LIBRARY_PATH"

# Check binaries
echo -e "${CYAN}Checking binaries...${NC}"
if [ ! -f "go/bin/go-node" ]; then
    echo -e "${YELLOW}Building Go binary...${NC}"
    cd go && make build
    cd ..
fi

if [ ! -f "rust/target/release/libpangea_ces.so" ]; then
    echo -e "${YELLOW}Building Rust library...${NC}"
    cd rust && cargo build --release
    cd ..
fi

echo -e "${GREEN}✓ Binaries ready${NC}"
echo ""

# Configuration
NUM_NODES=3
DATA_DIR_BASE="/tmp/pangea-automated-test"
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
    sleep 2
    rm -rf "$DATA_DIR_BASE"
    echo -e "${GREEN}✓ Cleanup complete${NC}"
}

trap cleanup EXIT INT TERM

# Clean up any previous test data
rm -rf "$DATA_DIR_BASE"

echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo -e "${CYAN}Starting $NUM_NODES nodes...${NC}"
echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo ""

# Start Go nodes
for i in $(seq 1 $NUM_NODES); do
    NODE_DIR="$DATA_DIR_BASE/node-$i"
    mkdir -p "$NODE_DIR/logs"
    
    CAPNP_PORT=$((8080 + i - 1))
    P2P_PORT=$((9080 + i - 1))
    
    echo -e "${BLUE}Starting Go Node $i (ports: $CAPNP_PORT, $P2P_PORT)...${NC}"
    
    "$PROJECT_ROOT/go/bin/go-node" \
        -id="$i" \
        -port="$CAPNP_PORT" \
        -p2p-port="$P2P_PORT" \
        > "$NODE_DIR/logs/go-node.log" 2>&1 &
    
    GO_PID=$!
    PIDS+=($GO_PID)
    echo -e "${GREEN}✓ Go Node $i started (PID: $GO_PID)${NC}"
    
    sleep 1
done

echo ""
echo -e "${CYAN}Waiting for nodes to initialize...${NC}"
sleep 5
echo ""

# Create test file
TEST_FILE="$DATA_DIR_BASE/test_file.txt"
echo "Hello from Pangea Net automated test!" > "$TEST_FILE"
echo "This file tests the automated upload/download functionality." >> "$TEST_FILE"
echo "File size: $(wc -c < "$TEST_FILE") bytes" >> "$TEST_FILE"

echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo -e "${CYAN}📤 Testing Automated Upload${NC}"
echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo ""

# Set cache directory
export PANGEA_CACHE_DIR="$DATA_DIR_BASE/cache"
mkdir -p "$PANGEA_CACHE_DIR"

# Upload file using automated uploader
echo -e "${BLUE}Uploading: $TEST_FILE${NC}"
echo ""

UPLOAD_OUTPUT=$("$PROJECT_ROOT/rust/target/release/pangea-rust-node" \
    put "$TEST_FILE" \
    --go-addr "127.0.0.1:8080" 2>&1)

echo "$UPLOAD_OUTPUT"
echo ""

# Extract file hash from output
FILE_HASH=$(echo "$UPLOAD_OUTPUT" | grep -oP 'File hash:\s*\K\S+')

if [ -z "$FILE_HASH" ]; then
    echo -e "${RED}❌ Failed to extract file hash from upload output${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Upload successful!${NC}"
echo -e "${CYAN}File hash: ${FILE_HASH}${NC}"
echo ""

echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo -e "${CYAN}📋 Testing List Files${NC}"
echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo ""

"$PROJECT_ROOT/rust/target/release/pangea-rust-node" \
    list \
    --go-addr "127.0.0.1:8080" 2>&1

echo ""

echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo -e "${CYAN}ℹ️  Testing File Info${NC}"
echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo ""

"$PROJECT_ROOT/rust/target/release/pangea-rust-node" \
    info "$FILE_HASH" \
    --go-addr "127.0.0.1:8080" 2>&1

echo ""

echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo -e "${CYAN}📥 Testing Automated Download${NC}"
echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo ""

DOWNLOAD_FILE="$DATA_DIR_BASE/downloaded_file.txt"

echo -e "${BLUE}Downloading file hash: $FILE_HASH${NC}"
echo ""

"$PROJECT_ROOT/rust/target/release/pangea-rust-node" \
    get "$FILE_HASH" \
    -o "$DOWNLOAD_FILE" \
    --go-addr "127.0.0.1:8080" 2>&1

echo ""

# Verify downloaded file
if [ -f "$DOWNLOAD_FILE" ]; then
    echo -e "${GREEN}✅ Download successful!${NC}"
    echo ""
    echo -e "${CYAN}Downloaded file contents:${NC}"
    cat "$DOWNLOAD_FILE"
    echo ""
    
    # Compare files
    if cmp -s "$TEST_FILE" "$DOWNLOAD_FILE"; then
        echo -e "${GREEN}✅ File integrity verified! Files match perfectly.${NC}"
    else
        echo -e "${RED}❌ File mismatch! Downloaded file differs from original.${NC}"
        exit 1
    fi
else
    echo -e "${RED}❌ Download failed! File not found.${NC}"
    exit 1
fi

echo ""
echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo -e "${CYAN}🔍 Testing Search${NC}"
echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo ""

"$PROJECT_ROOT/rust/target/release/pangea-rust-node" \
    search "test" \
    --go-addr "127.0.0.1:8080" 2>&1

echo ""

echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   ✅ All Tests Passed!                 ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""

echo -e "${CYAN}Summary:${NC}"
echo -e "  ✅ Automated upload: ${GREEN}PASSED${NC}"
echo -e "  ✅ File list: ${GREEN}PASSED${NC}"
echo -e "  ✅ File info: ${GREEN}PASSED${NC}"
echo -e "  ✅ Automated download: ${GREEN}PASSED${NC}"
echo -e "  ✅ File integrity: ${GREEN}PASSED${NC}"
echo -e "  ✅ File search: ${GREEN}PASSED${NC}"
echo ""

echo -e "${YELLOW}Press Enter to stop nodes and cleanup...${NC}"
read
