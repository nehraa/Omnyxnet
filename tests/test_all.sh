#!/bin/bash
# Comprehensive test suite for all Pangea Net components
# This runs ALL localhost tests that don't require cross-device setup

set -e

echo "========================================"
echo "🧪 Pangea Net - Full Test Suite"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
SKIPPED_TESTS=0

# Helper function to run a test
run_test() {
    local test_num=$1
    local test_name=$2
    local test_script=$3
    local log_file=$4
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "${test_num}️⃣  ${test_name}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    if bash "$test_script" > "$log_file" 2>&1; then
        echo -e "${GREEN}✅ ${test_name} PASSED${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}❌ ${test_name} FAILED${NC}"
        echo "   See $log_file for details"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
    echo ""
}

# Test 1: Python
run_test "1" "Python Component" "tests/test_python.sh" "/tmp/test_python.log"

# Test 2: Go
run_test "2" "Go Node" "tests/test_go.sh" "/tmp/test_go.log"

# Test 3: Rust
run_test "3" "Rust Node" "tests/test_rust.sh" "/tmp/test_rust.log"

# Test 4: Integration
run_test "4" "Integration Tests" "tests/test_integration.sh" "/tmp/test_integration.log"

# Test 5: FFI Integration
run_test "5" "FFI Integration (Go-Rust)" "tests/test_ffi_integration.sh" "/tmp/test_ffi.log"

# Test 6: Stream Updates
run_test "6" "Stream Updates (2-Node)" "tests/test_stream_updates.sh" "/tmp/test_stream.log"

# Test 7: CES Wiring
run_test "7" "CES Wiring" "tests/test_ces_simple.sh" "/tmp/test_ces.log"

# Test 8: Upload/Download Local
run_test "8" "Upload/Download (Local)" "tests/test_upload_download_local.sh" "/tmp/test_upload_local.log"

# Test 9: Compilation Check
run_test "9" "Compilation Verification" "tests/test_compilation.sh" "/tmp/test_compilation.log"

# Test 10: Phase 1 Features (NEW)
run_test "🔟" "Phase 1 Features (Brotli, Opus, Metrics)" "tests/test_phase1_features.sh" "/tmp/test_phase1.log"

# Test 11: Multi-node startup test (inline test)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣1️⃣  Testing Multi-Node Startup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# Kill any existing nodes (limited to current user's processes)
pkill -u "$USER" -f "go-node" 2>/dev/null || true
pkill -u "$USER" -f "pangea-rust-node" 2>/dev/null || true
sleep 1

# Start Go node
echo "   Starting Go node..."
export LD_LIBRARY_PATH="$PROJECT_ROOT/rust/target/release:${LD_LIBRARY_PATH:-}"
export DYLD_LIBRARY_PATH="$PROJECT_ROOT/rust/target/release:${DYLD_LIBRARY_PATH:-}"

# Try both possible locations for go-node
if [ -f "./go/bin/go-node" ]; then
    GO_BINARY="./go/bin/go-node"
elif [ -f "./go/go-node" ]; then
    GO_BINARY="./go/go-node"
else
    echo -e "${RED}❌ Go binary not found${NC}"
    FAILED_TESTS=$((FAILED_TESTS + 1))
    echo ""
    GO_BINARY=""
fi

if [ -n "$GO_BINARY" ]; then
    $GO_BINARY -node-id 1 -capnp-addr :8080 -libp2p &
    GO_PID=$!
    sleep 2

    # Check if Go node is running
    if ps -p $GO_PID > /dev/null 2>&1; then
        echo -e "   ${GREEN}✓${NC} Go node started (PID: $GO_PID)"
        
        # Start Rust node
        echo "   Starting Rust node..."
        if [ -f "./rust/target/release/pangea-rust-node" ]; then
            ./rust/target/release/pangea-rust-node --node-id 2 --rpc-addr 127.0.0.1:8081 --p2p-addr 127.0.0.1:9091 --dht-addr 127.0.0.1:9092 &
            RUST_PID=$!
            sleep 2
            
            # Check if Rust node is running
            if ps -p $RUST_PID > /dev/null 2>&1; then
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
            echo -e "${RED}❌ Rust binary not found${NC}"
            FAILED_TESTS=$((FAILED_TESTS + 1))
            kill $GO_PID 2>/dev/null || true
        fi
    else
        echo -e "   ${RED}✗${NC} Go node failed to start"
        echo -e "${RED}❌ Multi-node startup FAILED${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
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
    echo "All localhost components are working correctly:"
    echo "  • Python:      Syntax and structure validated"
    echo "  • Go:          Build, binary, and CLI working"
    echo "  • Rust:        Build, tests (12/12), binary working"
    echo "  • Integration: All components can communicate"
    echo "  • FFI:         Go-Rust FFI working"
    echo "  • Streaming:   Shared memory and updates working"
    echo "  • CES:         Compression/Encryption/Sharding pipeline"
    echo "  • Upload/Download: Local file operations"
    echo "  • Phase 1:     Brotli compression, Opus codec, Metrics tracking"
    echo "  • Multi-node:  Both Go and Rust nodes can start"
    echo ""
    echo "Next steps:"
    echo "  1. For cross-device testing: Use ./scripts/easy_test.sh"
    echo "  2. For comprehensive multi-node test: Run tests/test_localhost_full.sh"
    echo "  3. For WAN testing: Use setup.sh menu option 9"
    echo ""
    exit 0
else
    echo -e "${RED}❌ SOME TESTS FAILED${NC}"
    echo ""
    echo "Check the log files for details:"
    echo "  • /tmp/test_python.log"
    echo "  • /tmp/test_go.log"
    echo "  • /tmp/test_rust.log"
    echo "  • /tmp/test_integration.log"
    echo "  • /tmp/test_ffi.log"
    echo "  • /tmp/test_stream.log"
    echo "  • /tmp/test_ces.log"
    echo "  • /tmp/test_upload_local.log"
    echo "  • /tmp/test_compilation.log"
    echo ""
    exit 1
fi
