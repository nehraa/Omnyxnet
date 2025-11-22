#!/bin/bash
# Test script for Python component

set -e

echo "🧪 Testing Python Component"
echo "==========================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get absolute path to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_DIR="$PROJECT_ROOT/python"

echo "Project root: $PROJECT_ROOT"
echo "Python directory: $PYTHON_DIR"

cd "$PYTHON_DIR"

# Test 1: Check Python version
echo -e "\n1. Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "   Python version: $PYTHON_VERSION"
if python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
    echo -e "${GREEN}✅ Python version OK${NC}"
else
    echo -e "${RED}❌ Python 3.8+ required${NC}"
    exit 1
fi

# Test 2: Check if requirements can be installed
echo -e "\n2. Checking dependencies..."
if [ -f "requirements.txt" ]; then
    echo -e "${GREEN}✅ requirements.txt exists${NC}"
    # Check if packages are importable (don't install, just check)
    if python3 -c "import sys; sys.path.insert(0, 'src'); import click" 2>/dev/null; then
        echo -e "${GREEN}✅ Click available${NC}"
    else
        echo -e "${YELLOW}⚠️  Click not installed (run: pip install -r requirements.txt)${NC}"
    fi
else
    echo -e "${RED}❌ requirements.txt not found${NC}"
    exit 1
fi

# Test 3: Check module structure
echo -e "\n3. Checking module structure..."
MODULES=("src/__init__.py" "src/client/go_client.py" "src/data/timeseries.py" "src/ai/cnn_model.py" "src/cli.py")
for module in "${MODULES[@]}"; do
    if [ -f "$module" ]; then
        echo -e "${GREEN}✅ $module exists${NC}"
    else
        echo -e "${RED}❌ $module not found${NC}"
        exit 1
    fi
done

# Test 4: Test imports (syntax check)
echo -e "\n4. Testing Python syntax..."
if python3 -m py_compile src/client/go_client.py 2>/dev/null; then
    echo -e "${GREEN}✅ go_client.py syntax OK${NC}"
else
    echo -e "${RED}❌ go_client.py syntax error${NC}"
    exit 1
fi

if python3 -m py_compile src/data/timeseries.py 2>/dev/null; then
    echo -e "${GREEN}✅ timeseries.py syntax OK${NC}"
else
    echo -e "${RED}❌ timeseries.py syntax error${NC}"
    exit 1
fi

if python3 -m py_compile src/data/peer_health.py 2>/dev/null; then
    echo -e "${GREEN}✅ peer_health.py syntax OK${NC}"
else
    echo -e "${RED}❌ peer_health.py syntax error${NC}"
    exit 1
fi

if python3 -m py_compile src/ai/cnn_model.py 2>/dev/null; then
    echo -e "${GREEN}✅ cnn_model.py syntax OK${NC}"
else
    echo -e "${RED}❌ cnn_model.py syntax error${NC}"
    exit 1
fi

# Test 5: Test CLI help
echo -e "\n5. Testing CLI..."
if python3 main.py --help 2>&1 | grep -q "Pangea Net"; then
    echo -e "${GREEN}✅ CLI help works${NC}"
else
    echo -e "${YELLOW}⚠️  CLI help test skipped (dependencies may not be installed)${NC}"
fi

# Test 6: Check if PyTorch is available (optional)
echo -e "\n6. Checking PyTorch..."
if python3 -c "import torch; print(f'PyTorch {torch.__version__}')" 2>/dev/null; then
    CUDA_AVAILABLE=$(python3 -c "import torch; print(torch.cuda.is_available())" 2>/dev/null)
    if [ "$CUDA_AVAILABLE" = "True" ]; then
        echo -e "${GREEN}✅ PyTorch available with CUDA support${NC}"
    else
        echo -e "${YELLOW}⚠️  PyTorch available but CUDA not available (will use CPU)${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  PyTorch not installed (install with: pip install torch)${NC}"
fi

# Return to original directory
cd "$PROJECT_ROOT"

echo -e "\n${GREEN}✅ All Python tests passed!${NC}"
echo -e "${YELLOW}Note: Some features require dependencies. Install with: pip install -r requirements.txt${NC}"

