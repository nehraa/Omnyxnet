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
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
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

# Create temp directory for logs and PID files
TEST_DIR=$(mktemp -d)
NODE1_LOG="$TEST_DIR/node1.log"
NODE2_LOG="$TEST_DIR/node2.log"
NODE1_PID_FILE="$TEST_DIR/node1.pid"
NODE2_PID_FILE="$TEST_DIR/node2.pid"

# Cleanup function using PID files (fixes review comment about generic process patterns)
cleanup() {
    echo -e "${CYAN}Cleaning up...${NC}"
    
    # Kill processes using PID files
    if [ -f "$NODE1_PID_FILE" ]; then
        local pid=$(cat "$NODE1_PID_FILE" 2>/dev/null)
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
            wait "$pid" 2>/dev/null || true
        fi
    fi
    
    if [ -f "$NODE2_PID_FILE" ]; then
        local pid=$(cat "$NODE2_PID_FILE" 2>/dev/null)
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
            wait "$pid" 2>/dev/null || true
        fi
    fi
    
    rm -rf "$TEST_DIR" 2>/dev/null || true
}
trap cleanup EXIT

# Find available ports - check command availability first (fixes review comment)
find_available_port() {
    local port=$1
    local port_check_cmd=""
    
    # Check which command is available for port checking
    if command -v netstat >/dev/null 2>&1; then
        port_check_cmd="netstat -tuln"
    elif command -v ss >/dev/null 2>&1; then
        port_check_cmd="ss -tuln"
    else
        echo -e "${YELLOW}Warning: Neither 'netstat' nor 'ss' available. Using port $port without checking.${NC}" >&2
        echo $port
        return
    fi
    
    while eval "$port_check_cmd 2>/dev/null" | grep -q ":$port "; do
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
echo "$NODE1_PID" > "$NODE1_PID_FILE"
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
echo "$NODE2_PID" > "$NODE2_PID_FILE"
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

# Check for mDNS service initialization (more specific pattern per review comment)
if grep -q "mDNS" "$NODE1_LOG" 2>/dev/null || grep -q "mDNS" "$NODE2_LOG" 2>/dev/null; then
    test_result "mDNS service initialized" 0
else
    test_result "mDNS service initialized" 1
fi

# Check for peer discovery (more specific patterns per review comment)
if grep -qE "discovered|Connected|peer" "$NODE1_LOG" 2>/dev/null || \
   grep -qE "discovered|Connected|peer" "$NODE2_LOG" 2>/dev/null; then
    test_result "Peer discovery working" 0
else
    # This might fail on some CI environments without multicast support
    echo -e "${YELLOW}Note: Peer discovery may require multicast support${NC}"
    test_result "Peer discovery working" 1
fi

# Check for communication service initialization (per review comment)
if grep -q "Communication service started" "$NODE1_LOG" 2>/dev/null || \
   grep -q "💬 Communication service started" "$NODE1_LOG" 2>/dev/null; then
    test_result "Communication service initialized (Node 1)" 0
else
    # Communication service may not be integrated yet
    echo -e "${YELLOW}Note: Communication service integration pending${NC}"
    test_result "Communication service initialized (Node 1)" 1
fi

# ============================================================================
# Test Python CLI
# ============================================================================

echo -e "\n${YELLOW}=== Python CLI Test ===${NC}\n"

# Check if Python CLI has the new commands
cd "$PROJECT_ROOT/python"

if python3 -c "from src.cli import chat, voice, video" 2>/dev/null; then
    test_result "Python CLI has chat/voice/video commands" 0
else
    test_result "Python CLI has chat/voice/video commands" 1
fi

# Test chat history file reading
echo -e "${CYAN}Testing chat history file reading...${NC}"
mkdir -p ~/.pangea/communication

# Create a test chat history file
cat > ~/.pangea/communication/chat_history.json << 'EOF'
{
    "test-peer-id": [
        {
            "id": "1234567890",
            "from": "test-peer-id",
            "to": "local-id",
            "content": "Hello, test message!",
            "timestamp": "2025-12-03T00:00:00Z"
        }
    ]
}
EOF

# Test that go_client can read the file
if python3 -c "
from src.client.go_client import GoNodeClient
client = GoNodeClient()
history = client.get_chat_history('test-peer-id')
assert len(history) == 1
assert history[0]['content'] == 'Hello, test message!'
print('Chat history read successfully')
" 2>/dev/null; then
    test_result "Go client reads chat history file" 0
else
    test_result "Go client reads chat history file" 1
fi

# Clean up test file
rm -f ~/.pangea/communication/chat_history.json

cd "$PROJECT_ROOT"

# ============================================================================
# Test Documentation
# ============================================================================

echo -e "\n${YELLOW}=== Documentation Test ===${NC}\n"

if [ -f "$PROJECT_ROOT/docs/COMMUNICATION.md" ]; then
    test_result "COMMUNICATION.md exists" 0
    
    # Check for correct CLI examples
    if grep -q "python main.py chat" "$PROJECT_ROOT/docs/COMMUNICATION.md" 2>/dev/null; then
        test_result "Documentation has correct CLI examples" 0
    else
        test_result "Documentation has correct CLI examples" 1
    fi
else
    test_result "COMMUNICATION.md exists" 1
fi

# ============================================================================
# Summary
# ============================================================================

echo -e "\n${CYAN}╔══════════════════════════════════════════════════════════════╗"
echo "║   📊 Test Summary                                            ║"
echo "╚══════════════════════════════════════════════════════════════╝${NC}\n"

TOTAL=$((PASSED + FAILED))
echo -e "Total Tests: $TOTAL"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"

if [ $FAILED -eq 0 ]; then
    echo -e "\n${GREEN}🎉 All tests passed!${NC}\n"
    exit 0
else
    echo -e "\n${YELLOW}⚠️  Some tests failed. Check the output above.${NC}\n"
    exit 1
fi
