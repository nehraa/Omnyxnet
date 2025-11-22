#!/bin/bash
# Test script for Rust node

set -e

echo "======================================"
echo "Pangea Rust Node - Test Suite"
echo "======================================"

cd "$(dirname "$0")/../rust"

# Check Rust installation
echo "1. Checking Rust installation..."
if ! command -v cargo &> /dev/null; then
    echo "❌ Cargo not found. Please install Rust: https://rustup.rs/"
    exit 1
fi
echo "✓ Rust version: $(rustc --version)"

# Check for required tools
echo ""
echo "2. Checking for Cap'n Proto..."
if ! command -v capnp &> /dev/null; then
    echo "⚠️  Cap'n Proto not found. Schema compilation may fail."
    echo "   Install: brew install capnp (macOS) or apt-get install capnproto (Linux)"
else
    echo "✓ Cap'n Proto version: $(capnp --version)"
fi

# Build the project
echo ""
echo "3. Building Rust node..."
cargo build --release
if [ $? -eq 0 ]; then
    echo "✓ Build successful"
else
    echo "❌ Build failed"
    exit 1
fi

# Run unit tests (disable incremental for external volumes)
echo ""
echo "4. Running unit tests..."
CARGO_INCREMENTAL=0 cargo test --lib --release
if [ $? -eq 0 ]; then
    echo "✓ Unit tests passed"
else
    echo "❌ Unit tests failed"
    exit 1
fi

# Run integration tests
echo ""
echo "5. Running integration tests..."
CARGO_INCREMENTAL=0 cargo test --test integration_test --release
if [ $? -eq 0 ]; then
    echo "✓ Integration tests passed"
else
    echo "❌ Integration tests failed"
    exit 1
fi

# Check binary
echo ""
echo "6. Checking binary..."
BINARY="target/release/pangea-rust-node"
if [ -f "$BINARY" ]; then
    echo "✓ Binary exists: $BINARY"
    SIZE=$(du -h "$BINARY" | cut -f1)
    echo "  Size: $SIZE"
else
    echo "❌ Binary not found"
    exit 1
fi

# Test binary help
echo ""
echo "7. Testing binary help..."
$BINARY --help > /dev/null
if [ $? -eq 0 ]; then
    echo "✓ Binary runs correctly"
else
    echo "❌ Binary execution failed"
    exit 1
fi

# Optional: Test with features
if [[ "$1" == "--with-features" ]]; then
    echo ""
    echo "8. Testing with optional features..."
    
    echo "  - Building with io_uring feature..."
    cargo build --release --features uring
    
    echo "  - Building with eBPF feature..."
    cargo build --release --features ebpf
    
    echo "✓ Feature builds completed"
fi

echo ""
echo "======================================"
echo "✅ All tests passed!"
echo "======================================"
echo ""
echo "Quick start:"
echo "  cd rust"
echo "  cargo run --release -- --node-id 1"
echo ""
echo "With custom ports:"
echo "  cargo run --release -- --node-id 1 --p2p-addr 127.0.0.1:9090 --rpc-addr 127.0.0.1:8080"
echo ""
