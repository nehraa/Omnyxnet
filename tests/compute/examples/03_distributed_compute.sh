#!/bin/bash
# Distributed Compute - Matrix Multiplication
# Tests the real distributed_matrix_multiply.py example

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"
cd "$PROJECT_ROOT"

echo "🌐 Distributed Compute Test (Matrix Multiplication)"
echo "====================================================="
echo ""

# Check nodes
echo "🔌 Checking node connections..."
echo ""

NODE1_OK=false

# Check node
if pgrep -f "bin/go-node" > /dev/null 2>&1 && nc -z localhost 8080 2>/dev/null; then
    echo "  ✅ Go node running on :8080"
    NODE1_OK=true
else
    echo "  ⚠️  Go node not found on :8080"
    echo "  ⏳ Starting Go node automatically..."
    
    # Build if needed
    if [ ! -f "$PROJECT_ROOT/go/bin/go-node" ]; then
        echo "  🔨 Building go-node..."
        cd "$PROJECT_ROOT/go" && make build > /dev/null 2>&1 && cd "$PROJECT_ROOT"
    fi
    
    # Set library path for Rust
    export LD_LIBRARY_PATH="$PROJECT_ROOT/rust/target/release:$LD_LIBRARY_PATH"
    export DYLD_LIBRARY_PATH="$PROJECT_ROOT/rust/target/release:$DYLD_LIBRARY_PATH"
    
    # Start node in background
    "$PROJECT_ROOT/go/bin/go-node" -node-id=1 -capnp-addr=:8080 -libp2p=true -local > /tmp/go_node_1.log 2>&1 &
    NODE_PID=$!
    
    echo "  Started (PID: $NODE_PID)"
    echo "  ⏳ Waiting for node to initialize..."
    
    # Wait for node to be ready
    sleep 3
    
    # Check if it's running
    if pgrep -f "bin/go-node.*node-id=1" > /dev/null 2>&1 && nc -z localhost 8080 2>/dev/null; then
        echo "  ✅ Go node running on :8080"
        NODE1_OK=true
    else
        echo "  ❌ Failed to start Go node"
        echo "  Check log: tail /tmp/go_node_1.log"
        exit 1
    fi
fi

echo ""


echo "✅ Go node ready"
echo ""

# Run matrix multiplication
cd python
source .venv/bin/activate 2>/dev/null || python3 -m venv .venv && source .venv/bin/activate
pip install -q -r requirements.txt 2>/dev/null || true

echo "⚙️  Running Distributed Matrix Multiplication"
echo "=============================================="
echo ""

python3 examples/distributed_matrix_multiply.py --size 5 --generate --verify

echo ""
echo "✅ Matrix multiplication distributed compute test completed!"

