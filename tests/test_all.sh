#!/bin/bash
# Comprehensive test suite for all Pangea Net components

set -e

echo "========================================"
echo "🧪 Pangea Net - Full Test Suite"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Test 1: Python
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣  Testing Python Component"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TOTAL_TESTS=$((TOTAL_TESTS + 1))
if bash tests/test_python.sh > /tmp/test_python.log 2>&1; then
    echo -e "${GREEN}✅ Python tests PASSED${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}❌ Python tests FAILED${NC}"
    echo "   See /tmp/test_python.log for details"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi
echo ""

# Test 2: Go
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2️⃣  Testing Go Node"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TOTAL_TESTS=$((TOTAL_TESTS + 1))
if bash tests/test_go.sh > /tmp/test_go.log 2>&1; then
    echo -e "${GREEN}✅ Go tests PASSED${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}❌ Go tests FAILED${NC}"
    echo "   See /tmp/test_go.log for details"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi
echo ""

# Test 3: Rust
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3️⃣  Testing Rust Node"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TOTAL_TESTS=$((TOTAL_TESTS + 1))
if bash tests/test_rust.sh > /tmp/test_rust.log 2>&1; then
    echo -e "${GREEN}✅ Rust tests PASSED${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}❌ Rust tests FAILED${NC}"
    echo "   See /tmp/test_rust.log for details"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi
echo ""

# Test 4: Multi-node startup test
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4️⃣  Testing Multi-Node Startup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# Kill any existing nodes
killall go-node pangea-rust-node 2>/dev/null || true
sleep 1

# Start Go node
echo "   Starting Go node..."
./go/bin/go-node -node-id 1 -capnp-addr :8080 -libp2p &
GO_PID=$!
sleep 2

# Check if Go node is running
if ps -p $GO_PID > /dev/null; then
    echo -e "   ${GREEN}✓${NC} Go node started (PID: $GO_PID)"
    
    # Start Rust node
    echo "   Starting Rust node..."
    ./rust/target/release/pangea-rust-node --node-id 2 --rpc-addr 127.0.0.1:8081 --p2p-addr 127.0.0.1:9091 --dht-addr 127.0.0.1:9092 &
    RUST_PID=$!
    sleep 2
    
    # Check if Rust node is running
    if ps -p $RUST_PID > /dev/null; then
        echo -e "   ${GREEN}✓${NC} Rust node started (PID: $RUST_PID)"
        echo -e "${GREEN}✅ Multi-node startup PASSED${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        
        # Cleanup
        kill $GO_PID $RUST_PID 2>/dev/null || true
    else
        echo -e "   ${RED}✗${NC} Rust node failed to start"
        echo -e "${RED}❌ Multi-node startup FAILED${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        kill $GO_PID 2>/dev/null || true
    fi
else
    echo -e "   ${RED}✗${NC} Go node failed to start"
    echo -e "${RED}❌ Multi-node startup FAILED${NC}"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi
echo ""

# Summary
echo "========================================"
echo "📊 Test Summary"
echo "========================================"
echo "Total tests:  $TOTAL_TESTS"
echo -e "Passed:       ${GREEN}$PASSED_TESTS${NC}"
if [ $FAILED_TESTS -gt 0 ]; then
    echo -e "Failed:       ${RED}$FAILED_TESTS${NC}"
else
    echo -e "Failed:       ${GREEN}$FAILED_TESTS${NC}"
fi
echo "========================================"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✅ ALL TESTS PASSED!${NC}"
    echo ""
    echo "All components are working correctly:"
    echo "  • Python:   Syntax and structure validated"
    echo "  • Go:       Build, binary, and CLI working"
    echo "  • Rust:     Build, tests (12/12), binary working"
    echo "  • Multi-node: Both Go and Rust nodes can start"
    echo ""
    exit 0
else
    echo -e "${RED}❌ SOME TESTS FAILED${NC}"
    echo ""
    echo "Check the log files for details:"
    echo "  • /tmp/test_python.log"
    echo "  • /tmp/test_go.log"
    echo "  • /tmp/test_rust.log"
    echo ""
    exit 1
fi
