#!/bin/bash
# Test script to verify all paths work from different directories

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "🧪 Testing Path Resolution"
echo "==========================="

# Get absolute paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "Project root: $PROJECT_ROOT"

# Test 1: Test from project root
echo -e "\n${BLUE}Test 1: From project root${NC}"
cd "$PROJECT_ROOT"
if python3 -c "
import sys
sys.path.insert(0, 'python/src')
from utils.paths import get_go_schema_path, get_project_root
import os
schema = get_go_schema_path()
root = get_project_root()
print(f'   Schema: {schema}')
print(f'   Root: {root}')
assert os.path.exists(schema), 'Schema file not found'
assert os.path.exists(root / 'go'), 'Go directory not found'
assert os.path.exists(root / 'python'), 'Python directory not found'
print('   ✅ All paths resolved correctly')
"; then
    echo -e "${GREEN}✅ Test 1 passed${NC}"
else
    echo -e "${RED}❌ Test 1 failed${NC}"
    exit 1
fi

# Test 2: Test from python directory
echo -e "\n${BLUE}Test 2: From python directory${NC}"
cd "$PROJECT_ROOT/python"
if python3 -c "
import sys
sys.path.insert(0, 'src')
from utils.paths import get_go_schema_path, get_project_root
import os
schema = get_go_schema_path()
root = get_project_root()
print(f'   Schema: {schema}')
print(f'   Root: {root}')
assert os.path.exists(schema), 'Schema file not found'
print('   ✅ All paths resolved correctly')
"; then
    echo -e "${GREEN}✅ Test 2 passed${NC}"
else
    echo -e "${RED}❌ Test 2 failed${NC}"
    exit 1
fi

# Test 3: Test from go directory
echo -e "\n${BLUE}Test 3: From go directory${NC}"
cd "$PROJECT_ROOT/go"
if python3 -c "
import sys
sys.path.insert(0, '../python/src')
from utils.paths import get_go_schema_path, get_project_root
import os
schema = get_go_schema_path()
root = get_project_root()
print(f'   Schema: {schema}')
print(f'   Root: {root}')
assert os.path.exists(schema), 'Schema file not found'
print('   ✅ All paths resolved correctly')
"; then
    echo -e "${GREEN}✅ Test 3 passed${NC}"
else
    echo -e "${RED}❌ Test 3 failed${NC}"
    exit 1
fi

# Test 4: Test from tests directory
echo -e "\n${BLUE}Test 4: From tests directory${NC}"
cd "$PROJECT_ROOT/tests"
if python3 -c "
import sys
sys.path.insert(0, '../python/src')
from utils.paths import get_go_schema_path, get_project_root
import os
schema = get_go_schema_path()
root = get_project_root()
print(f'   Schema: {schema}')
print(f'   Root: {root}')
assert os.path.exists(schema), 'Schema file not found'
print('   ✅ All paths resolved correctly')
"; then
    echo -e "${GREEN}✅ Test 4 passed${NC}"
else
    echo -e "${RED}❌ Test 4 failed${NC}"
    exit 1
fi

# Test 5: Verify schema file exists
echo -e "\n${BLUE}Test 5: Verify schema file${NC}"
SCHEMA_PATH="$PROJECT_ROOT/go/schema/schema.capnp"
if [ -f "$SCHEMA_PATH" ]; then
    echo -e "${GREEN}✅ Schema file exists at: $SCHEMA_PATH${NC}"
else
    echo -e "${RED}❌ Schema file not found at: $SCHEMA_PATH${NC}"
    exit 1
fi

echo -e "\n${GREEN}✅ All path tests passed!${NC}"
echo -e "${BLUE}Paths work correctly from any directory${NC}"

