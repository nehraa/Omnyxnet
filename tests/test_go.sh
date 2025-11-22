#!/bin/bash
# Test script for Go node

set -e

echo "🧪 Testing Go Node"
echo "=================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get absolute path to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
GO_DIR="$PROJECT_ROOT/go"

echo "Project root: $PROJECT_ROOT"
echo "Go directory: $GO_DIR"

# Test 1: Build
echo -e "\n1. Testing build..."
cd "$GO_DIR"
if go build -o bin/go-node-test .; then
    echo -e "${GREEN}✅ Build successful${NC}"
else
    echo -e "${RED}❌ Build failed${NC}"
    exit 1
fi

# Test 2: Check if binary exists
echo -e "\n2. Checking binary..."
if [ -f "bin/go-node-test" ]; then
    echo -e "${GREEN}✅ Binary created${NC}"
else
    echo -e "${RED}❌ Binary not found${NC}"
    exit 1
fi

# Test 3: Run with help (should not crash)
echo -e "\n3. Testing help command..."
if ./bin/go-node-test -h 2>&1 | grep -q "node-id"; then
    echo -e "${GREEN}✅ Help command works${NC}"
else
    echo -e "${RED}❌ Help command failed${NC}"
    exit 1
fi

# Test 4: Check port availability (if port 8080 is free)
echo -e "\n4. Testing port availability..."
if lsof -Pi :8080 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${RED}⚠️  Port 8080 is in use, skipping port test${NC}"
else
    echo -e "${GREEN}✅ Port 8080 is available${NC}"
fi

# Test 5: Check schema file exists
echo -e "\n5. Checking schema file..."
SCHEMA_PATH="$GO_DIR/schema/schema.capnp"
if [ -f "$SCHEMA_PATH" ]; then
    echo -e "${GREEN}✅ Schema file exists at $SCHEMA_PATH${NC}"
else
    echo -e "${RED}❌ Schema file not found at $SCHEMA_PATH${NC}"
    exit 1
fi

# Return to original directory
cd "$PROJECT_ROOT"

echo -e "\n${GREEN}✅ All Go tests passed!${NC}"

