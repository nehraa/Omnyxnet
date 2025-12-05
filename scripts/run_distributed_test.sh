#!/bin/bash
# Distributed Compute - Run Test
# Runs matrix multiplication test using existing connection
# Run this AFTER nodes are connected

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Default values
HOST="${1:-localhost}"
PORT="${2:-8080}"
SIZE="${3:-100}"

echo -e "${CYAN}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║         DISTRIBUTED MATRIX MULTIPLICATION TEST            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""
echo -e "${YELLOW}NOTE: Run this test on the INITIATOR device.${NC}"
echo -e "${YELLOW}      The initiator will delegate the task to connected workers.${NC}"
echo ""
echo -e "   Connecting to local Go node: ${GREEN}${HOST}:${PORT}${NC}"
echo -e "   Matrix size: ${GREEN}${SIZE}x${SIZE}${NC}"
echo ""

# Setup Python
cd "$PROJECT_ROOT/python"
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Setting up Python environment...${NC}"
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt 2>/dev/null || pip install -q pycapnp numpy

# Run test
echo -e "${YELLOW}Running distributed compute test...${NC}"
echo ""

python3 examples/distributed_matrix_multiply.py \
    --connect \
    --host "$HOST" \
    --port "$PORT" \
    --size "$SIZE" \
    --generate \
    --verify

echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Test completed!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
