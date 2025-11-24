#!/bin/bash

# Phase 1 Features Test Suite
# Tests Brotli compression, Opus codec, and performance metrics

set -e

echo "🧪 Phase 1 Features Test Suite"
echo "==============================="

cd "$(dirname "$0")/.."

# Test 1: Phase 1 Demo (Brotli, Opus, Metrics)
echo "1. Running Phase 1 demo..."
cd rust
if cargo run --example phase1_demo --release 2>&1 | tee ../test_results.log; then
    echo "✅ Phase 1 demo completed successfully"
else
    echo "❌ Phase 1 demo failed"
    exit 1
fi
cd ..

# Test 2: Brotli compression performance
echo ""
echo "2. Testing Brotli compression performance..."
if cargo test --release test_brotli_performance 2>&1 | tee -a test_results.log; then
    echo "✅ Brotli compression tests passed"
else
    echo "❌ Brotli compression tests failed"
    exit 1
fi

# Test 3: Opus audio codec latency
echo ""
echo "3. Testing Opus codec latency (target: <100ms)..."
if cargo test --release test_opus_latency 2>&1 | tee -a test_results.log; then
    echo "✅ Opus latency tests passed"
else
    echo "❌ Opus latency tests failed"
    exit 1
fi

# Test 4: Metrics tracking validation
echo ""
echo "4. Testing performance metrics tracking..."
if cargo test --release test_metrics_tracking 2>&1 | tee -a test_results.log; then
    echo "✅ Metrics tracking tests passed"
else
    echo "❌ Metrics tracking tests failed"
    exit 1
fi

# Test 5: Phase 1 success criteria validation
echo ""
echo "5. Validating Phase 1 success criteria..."
if cargo test --release test_phase1_requirements 2>&1 | tee -a test_results.log; then
    echo "✅ Phase 1 requirements validation passed"
else
    echo "❌ Phase 1 requirements validation failed"
    exit 1
fi

echo ""
echo "🎉 All Phase 1 tests completed successfully!"
echo "📊 Check test_results.log for detailed output"
echo ""
echo "Phase 1 Success Metrics Validated:"
echo "- ✅ Brotli compression implemented"  
echo "- ✅ Opus codec with <100ms latency target"
echo "- ✅ Performance metrics tracking"
echo "- ✅ Real-time throughput monitoring"