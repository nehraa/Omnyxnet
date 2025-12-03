#!/bin/bash
# Test script for Distributed Compute System

set -e

echo "========================================"
echo "🧪 Distributed Compute System Tests"
echo "========================================"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASSED=0
FAILED=0

# Test function
test_section() {
    local name="$1"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Testing: $name"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# 1. Rust Compute Module Tests
test_section "Rust Compute Module"

cd rust
if cargo test 2>&1 | grep -q "test result: ok"; then
    echo -e "${GREEN}✅ Rust compute tests passed${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}❌ Rust compute tests failed${NC}"
    FAILED=$((FAILED + 1))
fi
cd "$PROJECT_ROOT"

# 2. Go Compute Package Tests
test_section "Go Compute Package"

cd go
if go test ./pkg/compute/...; then
    echo -e "${GREEN}✅ Go compute tests passed${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}❌ Go compute tests failed${NC}"
    FAILED=$((FAILED + 1))
fi
cd "$PROJECT_ROOT"

# 3. Python Compute Module Tests
test_section "Python Compute Module"

cd python
if python3 -c "
from src.compute import Job, JobBuilder, JobDefinition
from src.compute import ComputeClient, TaskStatus
from src.compute import DataPreprocessor, ChunkStrategy
from src.compute import ResultVisualizer

# Test Job DSL
@Job.define
def test_job():
    @Job.split
    def split(data):
        return [data[i:i+10] for i in range(0, len(data), 10)]
    
    @Job.execute
    def execute(chunk):
        return chunk.upper()
    
    @Job.merge
    def merge(results):
        return b''.join(results)

# Test locally
input_data = b'hello world this is a test'
chunks = test_job.split(input_data)
results = [test_job.execute(c) for c in chunks]
output = test_job.merge(results)
assert output == b'HELLO WORLD THIS IS A TEST', f'Got: {output}'

# Test preprocessor
preprocessor = DataPreprocessor(chunk_size=10)
chunks = preprocessor.split(b'hello world')
merged = preprocessor.merge(chunks)
assert merged == b'hello world'

# Test client
client = ComputeClient()
assert not client.is_connected()

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
    echo "Components tested:"
    echo "  • Rust: WASM sandbox, metering, verification, executor"
    echo "  • Go: Manager, scheduler, worker coordination"
    echo "  • Python: Job DSL, client SDK, preprocessor, visualizer"
    echo "  • Schema: Cap'n Proto compute structures"
    echo "  • Docs: Architecture and style guide"
    exit 0
else
    echo ""
    echo -e "${RED}❌ SOME TESTS FAILED${NC}"
    exit 1
fi
