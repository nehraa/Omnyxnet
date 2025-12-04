#!/bin/bash
# Single Node Compute - One Go node, simple compute tasks
# Tests compute without requiring peer connectivity

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"
cd "$PROJECT_ROOT"

echo "🖥️  Single Node Compute Test"
echo "=============================="
echo ""

# Check if go-node is running
if ! pgrep -f "bin/go-node" > /dev/null; then
    echo "❌ Go node not running. Start it with:"
    echo "   ./bin/go-node -node-id=1 -capnp-addr=:8080 -libp2p=true -local"
    exit 1
fi

echo "✅ Go node detected"
echo ""

# Connect to Go node and run a compute task
cd python
source .venv/bin/activate 2>/dev/null || python3 -m venv .venv && source .venv/bin/activate
pip install -q -r requirements.txt 2>/dev/null || true

python3 - <<'PYTHON'
import sys
sys.path.insert(0, 'src')
from client.go_client import GoNodeClient
import time

client = GoNodeClient(host="localhost", port=8080)
if not client.connect():
    print("❌ Failed to connect to Go node")
    sys.exit(1)

print("✅ Connected to Go node")
print("")

# Get node info
nodes = client.get_all_nodes()
print(f"📊 Node info: {len(nodes)} node(s) available")
for node in nodes:
    print(f"   Node {node['id']}: latency={node['latencyMs']:.1f}ms")

# Test compute task
print("")
print("⚙️  Running compute task on node...")

test_data = b"Sample data for computation" * 100
print(f"   Input size: {len(test_data)} bytes")

start = time.time()
shards = client.ces_process(test_data, compression_level=3)
elapsed = time.time() - start

if shards:
    total_size = sum(len(s) for s in shards)
    ratio = len(test_data) / total_size if total_size > 0 else 0
    print(f"   ✅ Computed in {elapsed*1000:.1f}ms")
    print(f"   Output: {len(shards)} shards, {total_size} bytes total")
    print(f"   Compression: {ratio:.2f}x")
    print("")
    print("✅ Single node compute test PASSED")
else:
    print("❌ Compute failed")
    sys.exit(1)

client.disconnect()
PYTHON

cd "$PROJECT_ROOT"
