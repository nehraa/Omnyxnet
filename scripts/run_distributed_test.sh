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
HOST="${1:-auto}"
PORT="${2:-8080}"
SIZE="${3:-100}"

# AUTO-DETECT: Check for saved connection info first
CONNECTION_FILE="$HOME/.pangea/distributed/connection.txt"
if [ "$HOST" = "auto" ] && [ -f "$CONNECTION_FILE" ]; then
    source "$CONNECTION_FILE"
    if [ -n "$INITIATOR_IP" ]; then
        HOST="$INITIATOR_IP"
        echo -e "${CYAN}Auto-detected initiator: ${HOST}:${PORT}${NC}"
        sleep 1
    fi
fi

# If still no host, ask user
if [ "$HOST" = "auto" ] || [ -z "$HOST" ]; then
    echo -e "${YELLOW}No initiator connection detected.${NC}"
    echo -e "${YELLOW}Enter initiator IP (or press Enter for localhost):${NC}"
    read -p "> " HOST
    HOST="${HOST:-localhost}"
fi

echo -e "${CYAN}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║         DISTRIBUTED MATRIX MULTIPLICATION TEST            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo -e "   Target: ${GREEN}${HOST}:${PORT}${NC}"
echo -e "   Matrix: ${GREEN}${SIZE}x${SIZE}${NC}"
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
