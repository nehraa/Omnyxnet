#!/bin/bash
# =============================================================================
# Container Test Runner - Orchestrates all container tests
# =============================================================================
# This script runs all containerized tests in sequence and generates a report.
#
# Usage:
#   ./run_container_tests.sh [OPTIONS]
#
# Options:
#   --quick           Run quick tests only (no Docker containers)
#   --matrix-only     Only run matrix multiplication tests
#   --network-only    Only run network tests
#   --full            Run full test suite with all container configurations
#   --help            Show this help message
#
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONTAINER_TESTS_DIR="$SCRIPT_DIR/container_tests"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Configuration
QUICK_MODE=false
MATRIX_ONLY=false
NETWORK_ONLY=false
FULL_MODE=false
LOG_DIR="$HOME/.wgt/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/container_tests_${TIMESTAMP}.log"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --quick)
            QUICK_MODE=true
            shift
            ;;
        --matrix-only)
            MATRIX_ONLY=true
            shift
            ;;
        --network-only)
            NETWORK_ONLY=true
            shift
            ;;
        --full)
            FULL_MODE=true
            shift
            ;;
        --help|-h)
            echo ""
            echo "WGT Container Test Runner"
            echo "========================="
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --quick           Run quick tests only (no Docker containers)"
            echo "  --matrix-only     Only run matrix multiplication tests"
            echo "  --network-only    Only run network tests"
            echo "  --full            Run full test suite with all container configurations"
            echo "  --help            Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 --quick        # Fast local tests"
            echo "  $0 --full         # Complete test suite"
            echo "  $0 --matrix-only  # Just matrix tests"
            echo ""
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# =============================================================================
# Logging
# =============================================================================

setup_logging() {
    mkdir -p "$LOG_DIR"
    touch "$LOG_FILE"
    
    # Log header
    {
        echo "============================================"
        echo "WGT Container Test Run"
        echo "Started: $(date)"
        echo "Quick Mode: $QUICK_MODE"
        echo "Full Mode: $FULL_MODE"
        echo "============================================"
        echo ""
    } >> "$LOG_FILE"
}

log() {
    local msg="$1"
    echo "[$(date '+%H:%M:%S')] $msg" | tee -a "$LOG_FILE"
}

# =============================================================================
# Test Functions
# =============================================================================

check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log "ERROR: Python 3 not found"
        return 1
    fi
    log "✓ Python 3 found"
    
    # Check Docker (optional for quick mode)
    if [ "$QUICK_MODE" = false ]; then
        if command -v docker &> /dev/null && docker info &> /dev/null 2>&1; then
            log "✓ Docker available"
        else
            log "WARNING: Docker not available, some tests will be skipped"
        fi
    fi
    
    # Check test scripts exist
    if [ ! -d "$CONTAINER_TESTS_DIR" ]; then
        log "ERROR: Container tests directory not found at $CONTAINER_TESTS_DIR"
        return 1
    fi
    log "✓ Test scripts found"
    
    return 0
}

run_test_suite() {
    local test_name="$1"
    local test_script="$2"
    local test_args="${3:-}"
    local start_time=$(date +%s)
    
    echo ""
    echo -e "${MAGENTA}════════════════════════════════════════════════════════════${NC}"
    echo -e "${MAGENTA}  $test_name${NC}"
    echo -e "${MAGENTA}════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    log "Starting: $test_name"
    
    if bash "$test_script" $test_args 2>&1 | tee -a "$LOG_FILE"; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        log "PASSED: $test_name (${duration}s)"
        return 0
    else
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        log "FAILED: $test_name (${duration}s)"
        return 1
    fi
}

# =============================================================================
# Main
# =============================================================================

main() {
    local start_time=$(date +%s)
    
    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                                                            ║${NC}"
    echo -e "${CYAN}║   WGT CONTAINER TEST RUNNER                               ║${NC}"
    echo -e "${CYAN}║                                                            ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Started: $(date)"
    echo "Log file: $LOG_FILE"
    echo ""
    echo "Mode:"
    echo "  Quick:       $QUICK_MODE"
    echo "  Full:        $FULL_MODE"
    echo "  Matrix only: $MATRIX_ONLY"
    echo "  Network only: $NETWORK_ONLY"
    echo ""
    
    setup_logging
    
    if ! check_prerequisites; then
        echo -e "${RED}❌ Prerequisites check failed${NC}"
        exit 1
    fi
    
    # Make test scripts executable
    chmod +x "$CONTAINER_TESTS_DIR"/*.sh 2>/dev/null || true
    
    # Track results
    PASSED=0
    FAILED=0
    SKIPPED=0
    RESULTS=""
    
    # Run tests based on mode
    if [ "$NETWORK_ONLY" = true ]; then
        # Network tests only
        if run_test_suite "Network Connection Tests" "$CONTAINER_TESTS_DIR/test_network_connection.sh"; then
            RESULTS="${RESULTS}✅ Network Connection\n"
            ((PASSED++))
        else
            RESULTS="${RESULTS}❌ Network Connection\n"
            ((FAILED++))
        fi
        
    elif [ "$MATRIX_ONLY" = true ]; then
        # Matrix tests only
        local args=""
        if [ "$QUICK_MODE" = true ]; then
            args="--local-only --size 5"
        fi
        
        if run_test_suite "Matrix Multiply Tests" "$CONTAINER_TESTS_DIR/test_matrix_cli.sh" "$args"; then
            RESULTS="${RESULTS}✅ Matrix Multiply\n"
            ((PASSED++))
        else
            RESULTS="${RESULTS}❌ Matrix Multiply\n"
            ((FAILED++))
        fi
        
    elif [ "$FULL_MODE" = true ]; then
        # Full test suite
        
        # 1. Network tests
        if run_test_suite "Network Connection Tests" "$CONTAINER_TESTS_DIR/test_network_connection.sh"; then
            RESULTS="${RESULTS}✅ Network Connection\n"
            ((PASSED++))
        else
            RESULTS="${RESULTS}❌ Network Connection\n"
            ((FAILED++))
        fi
        
        # 2. Matrix CLI tests (local)
        if run_test_suite "Matrix CLI Tests (Local)" "$CONTAINER_TESTS_DIR/test_matrix_cli.sh" "--local-only --size 10"; then
            RESULTS="${RESULTS}✅ Matrix CLI (Local)\n"
            ((PASSED++))
        else
            RESULTS="${RESULTS}❌ Matrix CLI (Local)\n"
            ((FAILED++))
        fi
        
        # 3. Distributed compute (2-node)
        if command -v docker &> /dev/null && docker info &> /dev/null 2>&1; then
            if run_test_suite "Distributed Compute (2-node)" "$CONTAINER_TESTS_DIR/test_compute_distributed.sh" "--nodes 2"; then
                RESULTS="${RESULTS}✅ Distributed Compute (2-node)\n"
                ((PASSED++))
            else
                RESULTS="${RESULTS}❌ Distributed Compute (2-node)\n"
                ((FAILED++))
            fi
            
            # 4. Distributed compute (3-node)
            if run_test_suite "Distributed Compute (3-node)" "$CONTAINER_TESTS_DIR/test_compute_distributed.sh" "--nodes 3"; then
                RESULTS="${RESULTS}✅ Distributed Compute (3-node)\n"
                ((PASSED++))
            else
                RESULTS="${RESULTS}❌ Distributed Compute (3-node)\n"
                ((FAILED++))
            fi
        else
            RESULTS="${RESULTS}⏭️  Distributed Compute: SKIPPED (Docker unavailable)\n"
            ((SKIPPED++))
            ((SKIPPED++))
        fi
        
    else
        # Default: Run all features test
        local args=""
        if [ "$QUICK_MODE" = true ]; then
            args="--quick"
        fi
        
        if run_test_suite "All Features Test" "$CONTAINER_TESTS_DIR/test_all_features.sh" "$args"; then
            RESULTS="${RESULTS}✅ All Features\n"
            ((PASSED++))
        else
            RESULTS="${RESULTS}❌ All Features\n"
            ((FAILED++))
        fi
    fi
    
    local end_time=$(date +%s)
    local total_duration=$((end_time - start_time))
    
    # Summary
    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║   FINAL TEST SUMMARY                                       ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "$RESULTS"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    TOTAL=$((PASSED + FAILED + SKIPPED))
    echo "Total Tests:  $TOTAL"
    echo -e "${GREEN}Passed:       $PASSED${NC}"
    echo -e "${RED}Failed:       $FAILED${NC}"
    echo -e "${YELLOW}Skipped:      $SKIPPED${NC}"
    echo "Duration:     ${total_duration}s"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Log file: $LOG_FILE"
    echo "Ended: $(date)"
    echo ""
    
    # Log summary
    {
        echo ""
        echo "============================================"
        echo "SUMMARY"
        echo "============================================"
        echo "Total: $TOTAL"
        echo "Passed: $PASSED"
        echo "Failed: $FAILED"
        echo "Skipped: $SKIPPED"
        echo "Duration: ${total_duration}s"
        echo "Ended: $(date)"
        echo "============================================"
    } >> "$LOG_FILE"
    
    if [ $FAILED -gt 0 ]; then
        echo -e "${RED}❌ Some tests failed!${NC}"
        exit 1
    else
        echo -e "${GREEN}✅ All tests passed!${NC}"
        exit 0
    fi
}

main
