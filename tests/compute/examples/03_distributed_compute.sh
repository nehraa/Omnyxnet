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
    echo "     Start with: ./bin/go-node -node-id=1 -capnp-addr=:8080 -libp2p=true"
fi

echo ""

if [ "$NODE1_OK" = false ]; then
    echo "❌ Go node required. Cannot proceed."
    exit 1
fi


echo "✅ Go node running"
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

