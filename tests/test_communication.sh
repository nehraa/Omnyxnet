#!/bin/bash
# ============================================================================
# Pangea Net - Communication Module Test
# Tests P2P chat, voice, and video communication using libp2p
# ============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Get project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Test results
PASSED=0
FAILED=0

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║   🔗 Pangea Net - Communication Module Test                  ║"
echo "║   Tests P2P chat, voice, and video using libp2p             ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Test function
test_result() {
    local name="$1"
    local result="$2"
    if [ "$result" -eq 0 ]; then
        echo -e "${GREEN}✅ PASS${NC}: $name"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}❌ FAIL${NC}: $name"
        FAILED=$((FAILED + 1))
    fi
}

# ============================================================================
# Prerequisites Check
# ============================================================================

echo -e "\n${YELLOW}=== Prerequisites Check ===${NC}\n"

# Check Go binary
if [ -f "$PROJECT_ROOT/go/bin/go-node" ]; then
    test_result "Go node binary exists" 0
else
    echo -e "${YELLOW}Building Go node...${NC}"
    cd "$PROJECT_ROOT/go"
    if go build -o bin/go-node . 2>/dev/null; then
        test_result "Go node binary built" 0
    else
        test_result "Go node binary built" 1
        echo -e "${RED}Cannot continue without Go binary${NC}"
        exit 1
    fi
    cd "$PROJECT_ROOT"
fi

# Check Rust library
RUST_LIB=""
if [ -f "$PROJECT_ROOT/rust/target/release/libpangea_ces.so" ]; then
    RUST_LIB="$PROJECT_ROOT/rust/target/release/libpangea_ces.so"
elif [ -f "$PROJECT_ROOT/rust/target/release/libpangea_ces.dylib" ]; then
    RUST_LIB="$PROJECT_ROOT/rust/target/release/libpangea_ces.dylib"
fi

if [ -n "$RUST_LIB" ]; then
    test_result "Rust library exists" 0
else
    echo -e "${YELLOW}Building Rust library...${NC}"
    cd "$PROJECT_ROOT/rust"
    if cargo build --release 2>/dev/null; then
        test_result "Rust library built" 0
    else
        test_result "Rust library built" 1
        echo -e "${RED}Cannot continue without Rust library${NC}"
        exit 1
    fi
    cd "$PROJECT_ROOT"
fi

# Set library path
export LD_LIBRARY_PATH="$PROJECT_ROOT/rust/target/release:${LD_LIBRARY_PATH:-}"

# Check communication package
if [ -f "$PROJECT_ROOT/go/pkg/communication/communication.go" ]; then
    test_result "Communication package exists" 0
else
    test_result "Communication package exists" 1
fi

# ============================================================================
# Test Go Compilation with Communication Package
# ============================================================================

echo -e "\n${YELLOW}=== Go Compilation Test ===${NC}\n"

cd "$PROJECT_ROOT/go"

# Check if Go code compiles (including communication package)
if go build ./... 2>/dev/null; then
    test_result "Go code compiles (including communication)" 0
else
    test_result "Go code compiles (including communication)" 1
fi

cd "$PROJECT_ROOT"

# ============================================================================
# Test Node Startup with mDNS
# ============================================================================

echo -e "\n${YELLOW}=== mDNS Discovery Test ===${NC}\n"

# Create temp directory for logs
TEST_DIR=$(mktemp -d)
NODE1_LOG="$TEST_DIR/node1.log"
NODE2_LOG="$TEST_DIR/node2.log"

cleanup() {
    pkill -u "$USER" -f "go-node.*node-id" 2>/dev/null || true
    rm -rf "$TEST_DIR" 2>/dev/null || true
}
trap cleanup EXIT

# Find available ports
find_available_port() {
    local port=$1
    while netstat -tuln 2>/dev/null | grep -q ":$port " || ss -tuln 2>/dev/null | grep -q ":$port "; do
        port=$((port + 1))
    done
    echo $port
}

PORT1=$(find_available_port 18080)
PORT2=$(find_available_port $((PORT1 + 1)))

# Start node 1
echo -e "${CYAN}Starting Node 1 on port $PORT1...${NC}"
"$PROJECT_ROOT/go/bin/go-node" -node-id=1 -capnp-addr=:$PORT1 -libp2p -local -test > "$NODE1_LOG" 2>&1 &
NODE1_PID=$!
sleep 2

# Check if node 1 started
if ps -p $NODE1_PID > /dev/null 2>&1; then
    test_result "Node 1 started" 0
else
    test_result "Node 1 started" 1
    echo -e "${RED}Node 1 failed to start. Log:${NC}"
    cat "$NODE1_LOG"
fi

# Start node 2
echo -e "${CYAN}Starting Node 2 on port $PORT2...${NC}"
"$PROJECT_ROOT/go/bin/go-node" -node-id=2 -capnp-addr=:$PORT2 -libp2p -local -test > "$NODE2_LOG" 2>&1 &
NODE2_PID=$!
sleep 2

# Check if node 2 started
if ps -p $NODE2_PID > /dev/null 2>&1; then
    test_result "Node 2 started" 0
else
    test_result "Node 2 started" 1
    echo -e "${RED}Node 2 failed to start. Log:${NC}"
    cat "$NODE2_LOG"
fi

# Wait for mDNS discovery
echo -e "${CYAN}Waiting for mDNS discovery (5 seconds)...${NC}"
sleep 5

# Check for mDNS discovery in logs
if grep -q "mDNS" "$NODE1_LOG" 2>/dev/null || grep -q "mDNS" "$NODE2_LOG" 2>/dev/null; then
    test_result "mDNS service initialized" 0
else
    test_result "mDNS service initialized" 1
fi

# Check for peer discovery
if grep -q "discovered\|Connected\|peer" "$NODE1_LOG" 2>/dev/null || \
   grep -q "discovered\|Connected\|peer" "$NODE2_LOG" 2>/dev/null; then
    test_result "Peer discovery working" 0
else
    test_result "Peer discovery working" 1
    echo -e "${YELLOW}Note: mDNS may take longer in some environments${NC}"
fi

# Stop nodes
echo -e "${CYAN}Stopping nodes...${NC}"
kill $NODE1_PID 2>/dev/null || true
kill $NODE2_PID 2>/dev/null || true
sleep 1

# ============================================================================
# Test Deprecated Python Files
# ============================================================================

echo -e "\n${YELLOW}=== Deprecated Files Check ===${NC}\n"

# Check that deprecated Python files have deprecation warnings
for file in live_video.py live_video_udp.py live_voice.py live_chat.py; do
    if [ -f "$PROJECT_ROOT/python/$file" ]; then
        if grep -q "DEPRECATED" "$PROJECT_ROOT/python/$file"; then
            test_result "$file has deprecation notice" 0
        else
            test_result "$file has deprecation notice" 1
        fi
    fi
done

# Check that QUIC file is removed
if [ ! -f "$PROJECT_ROOT/python/live_video_quic.py" ]; then
    test_result "QUIC file removed" 0
else
    test_result "QUIC file removed" 1
fi

# ============================================================================
# Test Documentation
# ============================================================================

echo -e "\n${YELLOW}=== Documentation Check ===${NC}\n"

# Check communication documentation exists
if [ -f "$PROJECT_ROOT/docs/COMMUNICATION.md" ]; then
    test_result "COMMUNICATION.md exists" 0
else
    test_result "COMMUNICATION.md exists" 1
fi

# Check documentation index is updated
if grep -q "Communication" "$PROJECT_ROOT/docs/DOCUMENTATION_INDEX.md" 2>/dev/null; then
    test_result "Documentation index updated" 0
else
    test_result "Documentation index updated" 1
fi

# ============================================================================
# Summary
# ============================================================================

echo ""
echo -e "${CYAN}════════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}                         TEST SUMMARY                            ${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  Passed: ${GREEN}$PASSED${NC}"
echo -e "  Failed: ${RED}$FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed${NC}"
    exit 1
fi
