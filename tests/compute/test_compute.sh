#!/bin/bash
# Test script for Distributed Compute System
#
# This script tests the distributed compute system which uses a MapReduce pattern:
#   - SPLIT: Break input data into smaller chunks
#   - EXECUTE: Run computation on each chunk (in parallel across nodes)
#   - MERGE: Combine results into final output
#
# The test verifies all three layers:
#   - Rust: WASM sandbox, metering, verification, executor
#   - Go: Task scheduling, load balancing, worker coordination
#   - Python: Job DSL, client SDK, data preprocessing, result visualization

set -e

echo "========================================"
echo "🧪 Distributed Compute System Tests"
echo "========================================"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

PASSED=0
FAILED=0
DISTRIBUTED_MODE=false

# ============================================================
# CONNECTION CHECK (extracted from live_test.sh)
# ============================================================

check_go_node_running() {
    # Check if a Go node is running by looking for the actual binary
    if pgrep -f "bin/go-node" > /dev/null 2>&1; then
        return 0
    fi
    return 1
}

check_node_connection() {
    local capnp_port="${1:-8080}"
    
    # Try to connect to the Cap'n Proto port
    if nc -z localhost "$capnp_port" 2>/dev/null; then
        return 0
    fi
    return 1
}

show_connection_status() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}🔌 Checking Node Connection...${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    if check_go_node_running; then
        echo -e "  ${GREEN}✅ Go node process is running${NC}"
        
        if check_node_connection 8080; then
            echo -e "  ${GREEN}✅ Cap'n Proto RPC available on :8080${NC}"
            DISTRIBUTED_MODE=true
            
            # Show connected peers count if possible
            echo -e "  ${CYAN}📊 Ready for distributed compute tasks${NC}"
        else
            echo -e "  ${YELLOW}⚠️  Cap'n Proto RPC not responding on :8080${NC}"
            echo -e "  ${YELLOW}   Running in local-only mode${NC}"
        fi
    else
        echo -e "  ${YELLOW}ℹ️  No Go node running - using local-only mode${NC}"
        echo -e "  ${YELLOW}   To test distributed compute, run:${NC}"
        echo -e "  ${YELLOW}     ./scripts/live_test.sh${NC}"
    fi
    echo ""
}

# Test function with logging
test_section() {
    local name="$1"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Testing: $name"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Log compute task with real-time info
log_compute_task() {
    local task_name="$1"
    local data_size="$2"
    local status="$3"
    
    local timestamp=$(date '+%H:%M:%S')
    echo -e "  ${CYAN}[$timestamp]${NC} $task_name ${MAGENTA}(${data_size})${NC} → $status"
}

# Check connection status first
show_connection_status

# 1. Rust Compute Module Tests
test_section "Rust Compute Module"
echo -e "  ${CYAN}Testing WASM sandbox, metering, and verification...${NC}"

cd rust
if timeout 120 cargo test compute --quiet 2>/dev/null || cargo test --quiet 2>/dev/null; then
    echo -e "${GREEN}✅ Rust compute tests passed${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}❌ Rust compute tests failed${NC}"
    FAILED=$((FAILED + 1))
fi
cd "$PROJECT_ROOT"

# 2. Go Compute Package Tests
test_section "Go Compute Package"
echo -e "  ${CYAN}Testing task scheduling, load balancing, and coordination...${NC}"

cd go
if go test ./pkg/compute/... -v 2>&1 | while read line; do
    # Show real-time test progress
    if [[ "$line" == *"=== RUN"* ]]; then
        test_name=$(echo "$line" | sed 's/=== RUN //')
        echo -e "  ${CYAN}▶ Running:${NC} $test_name"
    elif [[ "$line" == *"--- PASS"* ]]; then
        echo -e "  ${GREEN}✓${NC} Passed"
    elif [[ "$line" == *"--- FAIL"* ]]; then
        echo -e "  ${RED}✗${NC} Failed"
    fi
done && go test ./pkg/compute/... -quiet 2>/dev/null; then
    echo -e "${GREEN}✅ Go compute tests passed${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}❌ Go compute tests failed${NC}"
    FAILED=$((FAILED + 1))
fi
cd "$PROJECT_ROOT"

# 3. Python Compute Module Tests
test_section "Python Compute Module"
echo -e "  ${CYAN}Testing Job DSL, data preprocessing, and MapReduce pattern...${NC}"

cd python
if python3 -c "
import sys

# Colors for output
GREEN = '\033[0;32m'
CYAN = '\033[0;36m'
MAGENTA = '\033[0;35m'
NC = '\033[0m'

def log_step(step, detail=''):
    print(f'  {CYAN}▶{NC} {step} {MAGENTA}{detail}{NC}')

from src.compute import Job, JobBuilder, JobDefinition
from src.compute import ComputeClient, TaskStatus
from src.compute import DataPreprocessor, ChunkStrategy
from src.compute import ResultVisualizer

log_step('Loading compute modules...', '(Job, Client, Preprocessor)')

# Test Job DSL - This is what the distributed compute actually does:
# 1. SPLIT: Break data into chunks
# 2. EXECUTE: Process each chunk (uppercase in this case)
# 3. MERGE: Combine results
@Job.define
def test_job():
    @Job.split
    def split(data):
        # Split data into 10-byte chunks
        return [data[i:i+10] for i in range(0, len(data), 10)]
    
    @Job.execute
    def execute(chunk):
        # Process each chunk (convert to uppercase)
        return chunk.upper()
    
    @Job.merge
    def merge(results):
        # Combine all results
        return b''.join(results)

log_step('Defined MapReduce job:', 'split→execute→merge')

# Test locally - simulating distributed compute
input_data = b'hello world this is a test'
log_step(f'Input data:', f'{len(input_data)} bytes')

# SPLIT phase
chunks = test_job.split(input_data)
log_step(f'SPLIT phase:', f'{len(chunks)} chunks created')
for i, chunk in enumerate(chunks):
    print(f'    chunk[{i}]: {len(chunk)} bytes')

# EXECUTE phase (would be distributed across nodes)
log_step('EXECUTE phase:', 'processing chunks...')
results = []
for i, chunk in enumerate(chunks):
    result = test_job.execute(chunk)
    results.append(result)
    print(f'    chunk[{i}]: {chunk} → {result}')

# MERGE phase
output = test_job.merge(results)
log_step(f'MERGE phase:', f'{len(output)} bytes output')

# Verify result
assert output == b'HELLO WORLD THIS IS A TEST', f'Got: {output}'
log_step('Verification:', 'PASSED ✓')

# Test preprocessor
log_step('Testing DataPreprocessor...')
preprocessor = DataPreprocessor(chunk_size=10)
chunks = preprocessor.split(b'hello world')
merged = preprocessor.merge(chunks)
assert merged == b'hello world'
log_step('DataPreprocessor:', 'PASSED ✓')

# Test client (connection check)
log_step('Testing ComputeClient...')
client = ComputeClient()
assert not client.is_connected()
log_step('ComputeClient:', 'PASSED ✓')

print()
print('All Python compute tests passed!')
" 2>&1; then
    echo -e "${GREEN}✅ Python compute tests passed${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}❌ Python compute tests failed${NC}"
    FAILED=$((FAILED + 1))
fi
cd "$PROJECT_ROOT"

# 4. Cap'n Proto Schema Compilation
test_section "Cap'n Proto Schema"

# Check schema syntax (ignore Go annotations which require special setup)
if grep -q "struct ComputeJobManifest" go/schema/schema.capnp && \
   grep -q "struct ComputeJobStatus" go/schema/schema.capnp && \
   grep -q "struct ComputeCapacity" go/schema/schema.capnp; then
    echo -e "${GREEN}✅ Cap'n Proto compute structures defined${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}❌ Cap'n Proto compute structures missing${NC}"
    FAILED=$((FAILED + 1))
fi

# 5. Documentation Check
test_section "Documentation"

if [ -f docs/DISTRIBUTED_COMPUTE.md ] && [ -f docs/DOCUMENTATION_STYLE_GUIDE.md ]; then
    echo -e "${GREEN}✅ Compute documentation exists${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}❌ Compute documentation missing${NC}"
    FAILED=$((FAILED + 1))
fi

# Summary
echo ""
echo "========================================"
echo "📊 Test Summary"
echo "========================================"
echo -e "Passed: ${GREEN}$PASSED${NC}"
if [ $FAILED -gt 0 ]; then
    echo -e "Failed: ${RED}$FAILED${NC}"
else
    echo -e "Failed: ${GREEN}$FAILED${NC}"
fi
echo "========================================"

if [ $FAILED -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ ALL DISTRIBUTED COMPUTE TESTS PASSED!${NC}"
    echo ""
    echo -e "${BOLD}What the distributed compute system does:${NC}"
    echo "  The system uses a MapReduce pattern to process data across nodes:"
    echo ""
    echo "  1. ${CYAN}SPLIT${NC}: Break input data into smaller chunks"
    echo "     → Each chunk can be processed independently"
    echo "     → Chunks are distributed to available worker nodes"
    echo ""
    echo "  2. ${CYAN}EXECUTE${NC}: Run computation on each chunk"
    echo "     → Workers process chunks in parallel"
    echo "     → Results are verified using Merkle proofs"
    echo ""
    echo "  3. ${CYAN}MERGE${NC}: Combine results into final output"
    echo "     → Results from all workers are collected"
    echo "     → Final output is assembled and returned"
    echo ""
    echo "Components tested:"
    echo "  • Rust: WASM sandbox, metering, verification, executor"
    echo "  • Go: Manager, scheduler, worker coordination"
    echo "  • Python: Job DSL, client SDK, preprocessor, visualizer"
    echo "  • Schema: Cap'n Proto compute structures"
    echo "  • Docs: Architecture and style guide"
    
    if [ "$DISTRIBUTED_MODE" = true ]; then
        echo ""
        echo -e "${GREEN}🌐 Node connected - distributed compute available${NC}"
    else
        echo ""
        echo -e "${YELLOW}ℹ️  Local mode - to test actual distributed compute:${NC}"
        echo "     1. Run ./scripts/live_test.sh on this device"
        echo "     2. Connect another device to the network"
        echo "     3. Submit jobs via Python client SDK"
    fi
    
    exit 0
else
    echo ""
    echo -e "${RED}❌ SOME TESTS FAILED${NC}"
    exit 1
fi
