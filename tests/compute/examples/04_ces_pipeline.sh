#!/bin/bash
# CES Pipeline Test - Compress, Encrypt, Shard
# Tests the complete CES (Compress-Encrypt-Shard) pipeline

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"
cd "$PROJECT_ROOT"

echo "🔐 CES Pipeline Test (Compress → Encrypt → Shard)"
echo "===================================================="
echo ""

# Check go-node
if ! pgrep -f "bin/go-node" > /dev/null; then
    echo "❌ Go node not running. Start it with:"
    echo "   ./bin/go-node -node-id=1 -capnp-addr=:8080 -libp2p=true -local"
    exit 1
fi

echo "✅ Go node detected"
echo ""

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

# Test different data sizes
test_cases = [
    ("Small", b"Hello World " * 10),
    ("Medium", b"Test data " * 500),
    ("Large", b"Large test data " * 1000),
]

all_passed = True

for name, test_data in test_cases:
    print(f"Test: {name} ({len(test_data)} bytes)")
    print("-" * 50)
    
    # CES Process
    print("  [1/3] Compressing...")
    start = time.time()
    shards = client.ces_process(test_data, compression_level=3)
    compress_time = time.time() - start
    
    if not shards:
        print(f"  ❌ Compression failed")
        all_passed = False
        continue
    
    total_size = sum(len(s) for s in shards)
    ratio = len(test_data) / total_size if total_size > 0 else 0
    print(f"     ✅ {len(shards)} shards created in {compress_time*1000:.1f}ms")
    print(f"     Compression ratio: {ratio:.2f}x")
    
    # CES Reconstruct
    print("  [2/3] Reconstructing...")
    start = time.time()
    shard_present = [True] * len(shards)
    reconstructed = client.ces_reconstruct(shards, shard_present, compression_level=3)
    reconstruct_time = time.time() - start
    
    if not reconstructed:
        print(f"  ❌ Reconstruction failed")
        all_passed = False
        continue
    
    print(f"     ✅ Reconstructed in {reconstruct_time*1000:.1f}ms")
    
    # Verify
    print("  [3/3] Verifying integrity...")
    if reconstructed == test_data:
        print(f"     ✅ Data integrity verified - MATCH!")
    else:
        print(f"     ❌ Data mismatch!")
        print(f"        Original: {len(test_data)} bytes")
        print(f"        Reconstructed: {len(reconstructed)} bytes")
        all_passed = False
    
    print("")

if all_passed:
    print("✅ All CES pipeline tests PASSED!")
else:
    print("❌ Some CES tests failed")
    sys.exit(1)

client.disconnect()
PYTHON

cd "$PROJECT_ROOT"
