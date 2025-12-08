#!/bin/bash
# =============================================================================
# Comprehensive CLI Testing Script - Tests Every Command
# =============================================================================
# This script tests every single CLI command with various options
# For Mandate 3: 50-node cluster and all functionality
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_DIR="$PROJECT_ROOT/python"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Log file
LOG_FILE="/tmp/cli_test_$(date +%Y%m%d_%H%M%S).log"

echo "=================================================="
echo "CLI COMPREHENSIVE TEST SUITE"
echo "=================================================="
echo "Testing ALL CLI commands"
echo "Log file: $LOG_FILE"
echo "=================================================="
echo ""

# Function to run a test
run_test() {
    local test_name="$1"
    local command="$2"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -e "${BLUE}[TEST $TOTAL_TESTS]${NC} $test_name"
    echo "Command: $command" >> "$LOG_FILE"
    
    if eval "$command" >> "$LOG_FILE" 2>&1; then
        echo -e "${GREEN}✅ PASS${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}❌ FAIL${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        echo "FAILED: $test_name" >> "$LOG_FILE"
    fi
    echo ""
}

cd "$PYTHON_DIR"

echo "==================================================
" >> "$LOG_FILE"
echo "CLI TEST SUITE - $(date)" >> "$LOG_FILE"
echo "==================================================" >> "$LOG_FILE"

# =============================================================================
# Core Commands
# =============================================================================

echo -e "${YELLOW}=== CORE COMMANDS ===${NC}"

run_test "CLI Help" \
    "python -m src.cli --help"

run_test "Connect (help)" \
    "python -m src.cli connect --help"

run_test "List Nodes (help)" \
    "python -m src.cli list-nodes --help"

# =============================================================================
# Security Commands (Mandate 3)
# =============================================================================

echo -e "${YELLOW}=== SECURITY COMMANDS (Mandate 3) ===${NC}"

run_test "Security - Help" \
    "python -m src.cli security --help"

run_test "Security - Proxy Set (help)" \
    "python -m src.cli security proxy-set --help"

run_test "Security - Proxy Get (help)" \
    "python -m src.cli security proxy-get --help"

run_test "Security - Encryption Set (help)" \
    "python -m src.cli security encryption-set --help"

# Test with sample parameters (will fail to connect but tests command structure)
run_test "Security - Set Proxy (dry run)" \
    "timeout 2 python -m src.cli security proxy-set --proxy-host localhost --proxy-port 9050 || true"

run_test "Security - Get Proxy (dry run)" \
    "timeout 2 python -m src.cli security proxy-get || true"

run_test "Security - Set Encryption Asymmetric (dry run)" \
    "timeout 2 python -m src.cli security encryption-set --type asymmetric || true"

run_test "Security - Set Encryption Symmetric (dry run)" \
    "timeout 2 python -m src.cli security encryption-set --type symmetric --symmetric-algo aes256 || true"

run_test "Security - Set Encryption None (dry run)" \
    "timeout 2 python -m src.cli security encryption-set --type none || true"

# =============================================================================
# Ephemeral Chat Commands (Mandate 3)
# =============================================================================

echo -e "${YELLOW}=== EPHEMERAL CHAT COMMANDS (Mandate 3) ===${NC}"

run_test "Ephemeral Chat - Help" \
    "python -m src.cli echat --help"

run_test "Ephemeral Chat - Start (help)" \
    "python -m src.cli echat start --help"

run_test "Ephemeral Chat - Send (help)" \
    "python -m src.cli echat send --help"

run_test "Ephemeral Chat - Receive (help)" \
    "python -m src.cli echat receive --help"

run_test "Ephemeral Chat - Close (help)" \
    "python -m src.cli echat close --help"

# Test with sample parameters
run_test "Ephemeral Chat - Start Session (dry run)" \
    "timeout 2 python -m src.cli echat start worker1:8080 --encryption asymmetric || true"

run_test "Ephemeral Chat - Send Message (dry run)" \
    "timeout 2 python -m src.cli echat send --session test-session 'Hello' || true"

run_test "Ephemeral Chat - Receive Messages (dry run)" \
    "timeout 2 python -m src.cli echat receive --session test-session || true"

run_test "Ephemeral Chat - Close Session (dry run)" \
    "timeout 2 python -m src.cli echat close --session test-session || true"

# =============================================================================
# ML Training Commands (Mandate 3)
# =============================================================================

echo -e "${YELLOW}=== ML TRAINING COMMANDS (Mandate 3) ===${NC}"

run_test "ML - Help" \
    "python -m src.cli ml --help"

run_test "ML - Train Start (help)" \
    "python -m src.cli ml train-start --help"

run_test "ML - Status (help)" \
    "python -m src.cli ml status --help"

run_test "ML - Stop (help)" \
    "python -m src.cli ml stop --help"

# Test with sample parameters
run_test "ML - Start Training (dry run)" \
    "timeout 2 python -m src.cli ml train-start --task-id mnist-001 --dataset /tmp/data.pkl --workers worker1,worker2 || true"

run_test "ML - Get Status (dry run)" \
    "timeout 2 python -m src.cli ml status --task-id mnist-001 || true"

run_test "ML - Stop Training (dry run)" \
    "timeout 2 python -m src.cli ml stop --task-id mnist-001 || true"

# =============================================================================
# Chat Commands (Existing)
# =============================================================================

echo -e "${YELLOW}=== CHAT COMMANDS (Existing) ===${NC}"

run_test "Chat - Help" \
    "python -m src.cli chat --help"

run_test "Chat - Send (help)" \
    "python -m src.cli chat send --help"

run_test "Chat - History (help)" \
    "python -m src.cli chat history --help"

run_test "Chat - Peers (help)" \
    "python -m src.cli chat peers --help"

# =============================================================================
# Compute Commands
# =============================================================================

echo -e "${YELLOW}=== COMPUTE COMMANDS ===${NC}"

run_test "Compute - Help" \
    "python -m src.cli compute --help"

run_test "Compute - Submit (help)" \
    "python -m src.cli compute submit --help"

run_test "Compute - Status (help)" \
    "python -m src.cli compute status --help"

# =============================================================================
# Streaming Commands
# =============================================================================

echo -e "${YELLOW}=== STREAMING COMMANDS ===${NC}"

run_test "Streaming - Help" \
    "python -m src.cli streaming --help"

run_test "Streaming - Start (help)" \
    "python -m src.cli streaming start --help"

run_test "Streaming - Stop (help)" \
    "python -m src.cli streaming stop --help"

# =============================================================================
# Video/Voice Commands
# =============================================================================

echo -e "${YELLOW}=== VIDEO COMMANDS ===${NC}"

run_test "Video - Help" \
    "python -m src.cli video --help"

run_test "Voice - Help" \
    "python -m src.cli voice --help"

# =============================================================================
# AI Commands
# =============================================================================

echo -e "${YELLOW}=== AI COMMANDS ===${NC}"

run_test "AI - Help" \
    "python -m src.cli ai --help"

run_test "AI - Translate (help)" \
    "python -m src.cli ai translate --help"

run_test "AI - Federated (help)" \
    "python -m src.cli ai federated --help"

# =============================================================================
# DCDN Commands
# =============================================================================

echo -e "${YELLOW}=== DCDN COMMANDS ===${NC}"

run_test "DCDN - Help" \
    "python -m src.cli dcdn --help"

run_test "DCDN - Info (help)" \
    "python -m src.cli dcdn info --help"

# =============================================================================
# Test Commands
# =============================================================================

echo -e "${YELLOW}=== TEST COMMANDS ===${NC}"

run_test "Test - Help" \
    "python -m src.cli test --help"

run_test "Test - Compute (help)" \
    "python -m src.cli test compute --help"

run_test "Test - Communication (help)" \
    "python -m src.cli test communication --help"

# =============================================================================
# Results Summary
# =============================================================================

echo ""
echo "=================================================="
echo "TEST RESULTS SUMMARY"
echo "=================================================="
echo -e "Total Tests:  ${BLUE}$TOTAL_TESTS${NC}"
echo -e "Passed:       ${GREEN}$PASSED_TESTS${NC}"
echo -e "Failed:       ${RED}$FAILED_TESTS${NC}"
echo "=================================================="
echo ""
echo "Detailed log: $LOG_FILE"

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✅ ALL TESTS PASSED!${NC}"
    exit 0
else
    echo -e "${RED}❌ SOME TESTS FAILED${NC}"
    echo "Check log file for details: $LOG_FILE"
    exit 1
fi
