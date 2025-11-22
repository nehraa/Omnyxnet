#!/bin/bash
# Test FFI integration between Go and Rust

set -e

echo "========================================="
echo "🔗 Testing Go-Rust FFI Integration"
echo "========================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)

echo ""
echo "1️⃣  Checking Rust library..."
if [ -f "$PROJECT_ROOT/rust/target/release/libpangea_ces.so" ]; then
    echo -e "${GREEN}✅ Rust library found${NC}"
    ls -lh "$PROJECT_ROOT/rust/target/release/libpangea_ces.so"
else
    echo -e "${RED}❌ Rust library not found${NC}"
    echo "Building Rust library..."
    cd "$PROJECT_ROOT/rust"
    cargo build --release --lib
    cd "$PROJECT_ROOT"
fi

echo ""
echo "2️⃣  Checking Go binary..."
if [ -f "$PROJECT_ROOT/go/bin/go-node" ]; then
    echo -e "${GREEN}✅ Go binary found${NC}"
    ls -lh "$PROJECT_ROOT/go/bin/go-node"
else
    echo -e "${RED}❌ Go binary not found${NC}"
    echo "Building Go binary..."
    cd "$PROJECT_ROOT/go"
    CGO_LDFLAGS="-L../rust/target/release" go build -o bin/go-node .
    cd "$PROJECT_ROOT"
fi

echo ""
echo "3️⃣  Checking linked libraries..."
echo "Go binary dependencies:"
ldd "$PROJECT_ROOT/go/bin/go-node" | grep -E "pangea|libstdc" || echo "No Rust library linked (will be loaded at runtime)"

echo ""
echo "4️⃣  Testing Go compilation with FFI..."
cd "$PROJECT_ROOT/go"
cat > test_ces_ffi_simple.go << 'EOF'
package main

import (
    "fmt"
    "testing"
)

func TestCESPipelineBasic(t *testing.T) {
    // Create pipeline
    pipeline := NewCESPipeline(3)
    if pipeline == nil {
        t.Fatal("Failed to create CES pipeline")
    }
    defer pipeline.Close()

    // Test data
    testData := []byte("Hello, World! This is a test of the CES FFI.")
    
    // Process
    shards, err := pipeline.Process(testData)
    if err != nil {
        t.Fatalf("Failed to process: %v", err)
    }
    
    if len(shards) == 0 {
        t.Fatal("No shards returned")
    }
    
    fmt.Printf("✅ Created %d shards\n", len(shards))
    
    // Mark all shards as present
    present := make([]bool, len(shards))
    for i := range present {
        present[i] = true
    }
    
    // Reconstruct
    reconstructed, err := pipeline.Reconstruct(shards, present)
    if err != nil {
        t.Fatalf("Failed to reconstruct: %v", err)
    }
    
    // Verify
    if string(reconstructed) != string(testData) {
        t.Fatalf("Data mismatch: got %q, want %q", reconstructed, testData)
    }
    
    fmt.Printf("✅ Successfully reconstructed data\n")
}
EOF

echo "Running FFI test..."
export LD_LIBRARY_PATH="$PROJECT_ROOT/rust/target/release:$LD_LIBRARY_PATH"
export CGO_LDFLAGS="-L$PROJECT_ROOT/rust/target/release"

if go test -v -run TestCESPipelineBasic test_ces_ffi_simple.go ces_ffi.go 2>&1 | tee /tmp/ffi_test.log; then
    echo -e "${GREEN}✅ FFI test PASSED${NC}"
    rm -f test_ces_ffi_simple.go
else
    echo -e "${RED}❌ FFI test FAILED${NC}"
    echo "Test output:"
    cat /tmp/ffi_test.log
    rm -f test_ces_ffi_simple.go
    exit 1
fi

echo ""
echo "5️⃣  Testing file type detection (Rust)..."
cd "$PROJECT_ROOT/rust"
if cargo test --release --lib file_detector 2>&1 | grep "test result: ok"; then
    echo -e "${GREEN}✅ File detector tests PASSED${NC}"
else
    echo -e "${RED}❌ File detector tests FAILED${NC}"
    exit 1
fi

echo ""
echo "6️⃣  Summary"
echo "========================================="
echo -e "${GREEN}✅ All FFI integration tests PASSED${NC}"
echo "========================================="
echo ""
echo "Components verified:"
echo "  ✅ Rust library (libpangea_ces.so)"
echo "  ✅ Go binary with FFI support"
echo "  ✅ FFI roundtrip (Process + Reconstruct)"
echo "  ✅ File type detection"
echo ""
echo "The Pangea Net Blueprint implementation is ready!"
