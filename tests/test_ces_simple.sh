#!/bin/bash
# Simple CES wiring test - starts Go node and runs Python test

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "======================================"
echo "CES Wiring Simple Test"
echo "======================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Cleanup function
cleanup() {
    echo ""
    echo "Cleaning up..."
    if [ -n "$GO_NODE_PID" ]; then
        echo "Stopping Go node (PID: $GO_NODE_PID)"
        kill $GO_NODE_PID 2>/dev/null || true
        wait $GO_NODE_PID 2>/dev/null || true
    fi
}

trap cleanup EXIT

# Check if Go binary exists
if [ ! -f "$PROJECT_ROOT/go/go-node" ] && [ ! -f "$PROJECT_ROOT/go/bin/go-node" ]; then
    echo -e "${YELLOW}Go node binary not found. Building...${NC}"
    cd "$PROJECT_ROOT/go"
    go build -o go-node .
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to build Go node${NC}"
        exit 1
    fi
    echo -e "${GREEN}Go node built successfully${NC}"
elif [ ! -f "$PROJECT_ROOT/go/go-node" ] && [ -f "$PROJECT_ROOT/go/bin/go-node" ]; then
    echo -e "${GREEN}Using existing Go binary from bin/go-node${NC}"
    cp "$PROJECT_ROOT/go/bin/go-node" "$PROJECT_ROOT/go/go-node"
fi

# Check if Rust library exists
if [ ! -f "$PROJECT_ROOT/rust/target/release/libpangea_ces.so" ] && \
   [ ! -f "$PROJECT_ROOT/rust/target/release/libpangea_ces.dylib" ] && \
   [ ! -f "$PROJECT_ROOT/rust/target/release/libpangea_ces.a" ]; then
    echo -e "${YELLOW}Rust library not found. Building...${NC}"
    cd "$PROJECT_ROOT/rust"
    cargo build --release --lib
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to build Rust library${NC}"
        exit 1
    fi
    echo -e "${GREEN}Rust library built successfully${NC}"
fi

# Set library path for Rust FFI
export LD_LIBRARY_PATH="$PROJECT_ROOT/rust/target/release:${LD_LIBRARY_PATH:-}"
export DYLD_LIBRARY_PATH="$PROJECT_ROOT/rust/target/release:${DYLD_LIBRARY_PATH:-}"

# Start Go node in background
echo "Starting Go node..."
cd "$PROJECT_ROOT/go"
./go-node --node-id 1 --capnp-addr :8080 --test &
GO_NODE_PID=$!

# Wait for Go node to start
echo "Waiting for Go node to initialize..."
sleep 3

# Check if Go node is running
if ! ps -p $GO_NODE_PID > /dev/null 2>&1; then
    echo -e "${RED}Go node failed to start${NC}"
    exit 1
fi

echo -e "${GREEN}Go node started (PID: $GO_NODE_PID)${NC}"
echo ""

# Run Python test with venv
echo "Running CES wiring test..."
cd "$PROJECT_ROOT"

# Use venv Python if available
if [ -f "$PROJECT_ROOT/python/.venv/bin/python" ]; then
    PYTHON_BIN="$PROJECT_ROOT/python/.venv/bin/python"
    echo "Using venv Python: $PYTHON_BIN"
else
    PYTHON_BIN="python3"
    echo "Using system Python: $PYTHON_BIN"
fi

$PYTHON_BIN tests/test_ces_wiring.py

TEST_RESULT=$?

echo ""
if [ $TEST_RESULT -eq 0 ]; then
    echo -e "${GREEN}✅ CES wiring test passed!${NC}"
else
    echo -e "${RED}❌ CES wiring test failed${NC}"
fi

exit $TEST_RESULT
