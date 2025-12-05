#!/bin/bash
# Local Unit Tests - No node required
# Tests Rust and Python components in isolation

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"
cd "$PROJECT_ROOT"

echo "🧪 Local Unit Tests (No Network Required)"
echo "============================================"
echo ""

# Test 1: Rust library compilation
echo "Test 1: Rust library builds and links..."
cd rust
if cargo test --lib 2>&1 | grep -q "test result: ok"; then
    echo "  ✅ Rust unit tests passed"
else
    echo "  ❌ Rust unit tests failed"
    exit 1
fi
cd "$PROJECT_ROOT"

# Test 2: Python compute client
echo ""
echo "Test 2: Python compute client..."
cd python
source .venv/bin/activate 2>/dev/null || python3 -m venv .venv && source .venv/bin/activate
pip install -q -r requirements.txt 2>/dev/null || true

python3 - <<'PYTEST'
import sys
sys.path.insert(0, 'src')
try:
    from compute import ComputeClient
    print("  ✅ Python compute client imports successfully")
except Exception as e:
    print(f"  ❌ Import failed: {e}")
    sys.exit(1)
PYTEST

cd "$PROJECT_ROOT"

echo ""
echo "✅ All local unit tests passed!"
