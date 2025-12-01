#!/bin/bash
# Quick verification script to check if Pangea Net is properly set up
# Run this after installation to verify everything is working

set -e

# Get the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "========================================"
echo "🔍 Pangea Net Setup Verification"
echo "========================================"
echo ""

CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_WARNING=0

# Helper function
check() {
    local name=$1
    local command=$2
    local type=${3:-"error"}  # error or warning
    
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✅${NC} $name"
        CHECKS_PASSED=$((CHECKS_PASSED + 1))
        return 0
    else
        if [ "$type" = "warning" ]; then
            echo -e "${YELLOW}⚠️${NC}  $name (optional)"
            CHECKS_WARNING=$((CHECKS_WARNING + 1))
        else
            echo -e "${RED}❌${NC} $name"
            CHECKS_FAILED=$((CHECKS_FAILED + 1))
        fi
        return 1
    fi
}

# System dependencies
echo -e "${BLUE}System Dependencies:${NC}"
check "Go installed" "command -v go"
check "Rust installed" "command -v rustc"
check "Python 3 installed" "command -v python3"
check "Cap'n Proto installed" "command -v capnp"
check "pkg-config installed" "command -v pkg-config"
echo ""

# Go setup
echo -e "${BLUE}Go Components:${NC}"
check "Go node binary (bin/go-node)" "test -f go/bin/go-node"
check "Go node binary (go-node)" "test -f go/go-node" "warning"
check "Go modules downloaded" "test -f go/go.sum"
echo ""

# Rust setup
echo -e "${BLUE}Rust Components:${NC}"
check "Rust library (libpangea_ces.so)" "test -f rust/target/release/libpangea_ces.so || test -f rust/target/release/libpangea_ces.dylib"
check "Rust binary (pangea-rust-node)" "test -f rust/target/release/pangea-rust-node"
check "Rust dependencies built" "test -d rust/target/release/deps"
echo ""

# Python setup
echo -e "${BLUE}Python Components:${NC}"
check "Python venv created" "test -d python/.venv"
check "Python venv activated" "test -f python/.venv/bin/python"

if [ -f python/.venv/bin/python ]; then
    # Check Python packages
    if python/.venv/bin/python -c "import capnp" 2>/dev/null; then
        echo -e "${GREEN}✅${NC} pycapnp installed"
        CHECKS_PASSED=$((CHECKS_PASSED + 1))
    else
        echo -e "${RED}❌${NC} pycapnp not installed"
        CHECKS_FAILED=$((CHECKS_FAILED + 1))
    fi
    
    if python/.venv/bin/python -c "import numpy" 2>/dev/null; then
        echo -e "${GREEN}✅${NC} numpy installed"
        CHECKS_PASSED=$((CHECKS_PASSED + 1))
    else
        echo -e "${YELLOW}⚠️${NC}  numpy not installed (optional)"
        CHECKS_WARNING=$((CHECKS_WARNING + 1))
    fi
    
    if python/.venv/bin/python -c "import torch" 2>/dev/null; then
        echo -e "${GREEN}✅${NC} torch installed (AI features)"
        CHECKS_PASSED=$((CHECKS_PASSED + 1))
    else
        echo -e "${YELLOW}⚠️${NC}  torch not installed (optional, AI features)"
        CHECKS_WARNING=$((CHECKS_WARNING + 1))
    fi
fi
echo ""

# Environment variables
echo -e "${BLUE}Environment:${NC}"
if echo "${LD_LIBRARY_PATH:-}" | grep -q "rust/target/release"; then
    echo -e "${GREEN}✅${NC} LD_LIBRARY_PATH configured"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
else
    echo -e "${YELLOW}⚠️${NC}  LD_LIBRARY_PATH not set (scripts will set this)"
    CHECKS_WARNING=$((CHECKS_WARNING + 1))
fi

if command -v go > /dev/null && echo "${PATH:-}" | grep -q "go/bin"; then
    echo -e "${GREEN}✅${NC} Go in PATH"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
elif command -v go > /dev/null; then
    echo -e "${GREEN}✅${NC} Go available in PATH"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
else
    echo -e "${RED}❌${NC} Go not in PATH"
    CHECKS_FAILED=$((CHECKS_FAILED + 1))
fi
echo ""

# Quick functionality test
echo -e "${BLUE}Quick Functionality Test:${NC}"

# Try to run Go node --help
if [ -f go/bin/go-node ]; then
    export LD_LIBRARY_PATH="$(pwd)/rust/target/release:${LD_LIBRARY_PATH:-}"
    if timeout 2 ./go/bin/go-node --help > /dev/null 2>&1; then
        echo -e "${GREEN}✅${NC} Go node executable works"
        CHECKS_PASSED=$((CHECKS_PASSED + 1))
    else
        # Check if it's just missing --help
        if [ -x go/bin/go-node ]; then
            echo -e "${GREEN}✅${NC} Go node is executable"
            CHECKS_PASSED=$((CHECKS_PASSED + 1))
        else
            echo -e "${RED}❌${NC} Go node cannot execute"
            CHECKS_FAILED=$((CHECKS_FAILED + 1))
        fi
    fi
fi

# Try to run Rust node --help
if [ -f rust/target/release/pangea-rust-node ]; then
    if ./rust/target/release/pangea-rust-node --help > /dev/null 2>&1; then
        echo -e "${GREEN}✅${NC} Rust node executable works"
        CHECKS_PASSED=$((CHECKS_PASSED + 1))
    else
        echo -e "${RED}❌${NC} Rust node --help failed"
        CHECKS_FAILED=$((CHECKS_FAILED + 1))
    fi
fi
echo ""

# Summary
echo "========================================"
echo "📊 Verification Summary"
echo "========================================"
echo -e "Passed:   ${GREEN}$CHECKS_PASSED${NC}"
if [ $CHECKS_FAILED -gt 0 ]; then
    echo -e "Failed:   ${RED}$CHECKS_FAILED${NC}"
else
    echo -e "Failed:   ${GREEN}$CHECKS_FAILED${NC}"
fi
if [ $CHECKS_WARNING -gt 0 ]; then
    echo -e "Warnings: ${YELLOW}$CHECKS_WARNING${NC}"
fi
echo "========================================"
echo ""

# Recommendations
if [ $CHECKS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ Setup verification passed!${NC}"
    echo ""
    echo "You're ready to:"
    echo "  1. Run tests: ./setup.sh (option 7)"
    echo "  2. Start a node: ./scripts/easy_test.sh 1"
    echo "  3. Run comprehensive test: bash tests/test_localhost_full.sh"
    echo ""
    exit 0
else
    echo -e "${RED}❌ Setup verification found issues${NC}"
    echo ""
    echo "Recommended actions:"
    echo "  1. Run full installation: ./setup.sh (option 1)"
    
    if [ ! -d python/.venv ] || ! python/.venv/bin/python -c "import capnp" 2>/dev/null; then
        echo "  2. Install Python dependencies:"
        echo "     cd python && source .venv/bin/activate"
        echo "     pip install -r requirements-minimal.txt"
    fi
    
    if [ ! -f rust/target/release/libpangea_ces.so ] && [ ! -f rust/target/release/libpangea_ces.dylib ]; then
        echo "  3. Build Rust library:"
        echo "     cd rust && cargo build --release"
    fi
    
    if [ ! -f go/bin/go-node ]; then
        echo "  4. Build Go node:"
        echo "     cd go && make build"
    fi
    
    echo ""
    echo "See SETUP_GUIDE.md for detailed instructions"
    echo ""
    exit 1
fi
