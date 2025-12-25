#!/bin/bash
# =============================================================================
# Comprehensive Linting and Testing Script
# =============================================================================
# This script runs all linters and tests to ensure code quality and 
# functionality across Python, Rust, and Go components.
#
# Usage:
#   ./run_all_linters_and_tests.sh [OPTIONS]
#
# Options:
#   --lint-only       Run only linting checks
#   --test-only       Run only tests
#   --quick           Run quick tests only
#   --full            Run full test suite
#   --help            Show this help message
#
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
LINT_ONLY=false
TEST_ONLY=false
QUICK_MODE=false
FULL_MODE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --lint-only)
            LINT_ONLY=true
            shift
            ;;
        --test-only)
            TEST_ONLY=true
            shift
            ;;
        --quick)
            QUICK_MODE=true
            shift
            ;;
        --full)
            FULL_MODE=true
            shift
            ;;
        --help|-h)
            echo ""
            echo "Comprehensive Linting and Testing Script"
            echo "========================================"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --lint-only       Run only linting checks"
            echo "  --test-only       Run only tests"
            echo "  --quick           Run quick tests only"
            echo "  --full            Run full test suite"
            echo "  --help            Show this help message"
            echo ""
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# =============================================================================
# Helper Functions
# =============================================================================

print_header() {
    echo ""
    echo -e "${CYAN}============================================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}============================================================${NC}"
    echo ""
}

print_section() {
    echo ""
    echo -e "${BLUE}------------------------------------------------------------${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}------------------------------------------------------------${NC}"
}

check_success() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $1 passed${NC}"
        return 0
    else
        echo -e "${RED}✗ $1 failed${NC}"
        return 1
    fi
}

# =============================================================================
# Linting Functions
# =============================================================================

run_python_linting() {
    print_section "Python Linting"
    
    cd "$PROJECT_ROOT/python"
    
    # Ruff
    echo "Running ruff..."
    ruff check .
    check_success "ruff"
    
    # Black
    echo "Running black..."
    black --check .
    check_success "black format check"
    
    # MyPy
    echo "Running mypy..."
    mypy .
    check_success "mypy type check"
}

run_rust_linting() {
    print_section "Rust Linting"
    
    cd "$PROJECT_ROOT/rust"
    
    # Cargo fmt
    echo "Running cargo fmt..."
    cargo fmt --check
    check_success "cargo fmt"
    
    # Cargo clippy on lib only (most critical)
    echo "Running cargo clippy on library..."
    cargo clippy --lib --all-features -- -D warnings
    check_success "cargo clippy (lib)"
}

run_go_linting() {
    print_section "Go Linting"
    
    cd "$PROJECT_ROOT/go"
    
    # Go fmt
    echo "Running go fmt..."
    gofmt_output=$(gofmt -l .)
    if [ -z "$gofmt_output" ]; then
        check_success "go fmt"
    else
        echo "Files need formatting: $gofmt_output"
        return 1
    fi
    
    # Go vet
    echo "Running go vet..."
    go vet ./...
    check_success "go vet"
}

# =============================================================================
# Build Functions
# =============================================================================

build_rust() {
    print_section "Building Rust"
    
    cd "$PROJECT_ROOT/rust"
    
    echo "Building Rust library in release mode..."
    cargo build --release --lib
    check_success "Rust build"
}

build_go() {
    print_section "Building Go"
    
    cd "$PROJECT_ROOT/go"
    
    echo "Building Go binary..."
    go build -o /tmp/go-node .
    check_success "Go build"
}

# =============================================================================
# Testing Functions
# =============================================================================

run_rust_tests() {
    print_section "Rust Tests"
    
    cd "$PROJECT_ROOT/rust"
    
    echo "Running Rust unit tests..."
    cargo test --lib
    check_success "Rust unit tests"
}

run_go_tests() {
    print_section "Go Tests"
    
    cd "$PROJECT_ROOT/go"
    
    echo "Running Go tests..."
    go test ./... -v -short
    check_success "Go tests"
}

run_integration_tests() {
    print_section "Integration Tests"
    
    if [ "$QUICK_MODE" = true ]; then
        echo "Skipping integration tests in quick mode"
        return 0
    fi
    
    cd "$PROJECT_ROOT"
    
    # Run existing container tests
    if [ -f "$PROJECT_ROOT/scripts/run_container_tests.sh" ]; then
        echo "Running container tests..."
        bash "$PROJECT_ROOT/scripts/run_container_tests.sh" --quick
        check_success "Container tests"
    fi
}

run_feature_tests() {
    print_section "Comprehensive Feature Tests"
    
    if [ "$QUICK_MODE" = true ]; then
        echo "Running quick feature tests..."
        bash "$PROJECT_ROOT/scripts/container_tests/comprehensive_feature_tests.sh" --quick --no-build
    else
        echo "Running full feature test suite..."
        bash "$PROJECT_ROOT/scripts/container_tests/comprehensive_feature_tests.sh" --no-build
    fi
    check_success "Feature tests"
}

run_advanced_feature_tests() {
    print_section "Advanced Feature Tests"
    
    cd "$PROJECT_ROOT/scripts/container_tests"
    
    # WASM I/O Encryption
    echo "Testing WASM I/O encrypted tunneling..."
    bash test_wasm_io_encryption.sh
    check_success "WASM I/O encryption"
    
    # DHT
    echo "Testing Distributed Hash Table..."
    bash test_dht.sh
    check_success "DHT"
    
    # DKG
    echo "Testing Distributed Key Generation..."
    bash test_dkg.sh
    check_success "DKG"
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    print_header "Starting Comprehensive Linting and Testing"
    
    FAILED=0
    
    # Linting Phase
    if [ "$TEST_ONLY" = false ]; then
        print_header "PHASE 1: LINTING"
        
        run_python_linting || FAILED=$((FAILED+1))
        run_rust_linting || FAILED=$((FAILED+1))
        run_go_linting || FAILED=$((FAILED+1))
    fi
    
    # Build Phase
    if [ "$LINT_ONLY" = false ] && [ "$TEST_ONLY" = false ]; then
        print_header "PHASE 2: BUILDING"
        
        build_rust || FAILED=$((FAILED+1))
        build_go || FAILED=$((FAILED+1))
    fi
    
    # Testing Phase
    if [ "$LINT_ONLY" = false ]; then
        print_header "PHASE 3: TESTING"
        
        run_rust_tests || FAILED=$((FAILED+1))
        run_go_tests || FAILED=$((FAILED+1))
        
        if [ "$FULL_MODE" = true ]; then
            run_integration_tests || FAILED=$((FAILED+1))
            run_feature_tests || FAILED=$((FAILED+1))
            run_advanced_feature_tests || FAILED=$((FAILED+1))
        fi
    fi
    
    # Summary
    print_header "SUMMARY"
    
    if [ $FAILED -eq 0 ]; then
        echo -e "${GREEN}✓ All checks passed!${NC}"
        return 0
    else
        echo -e "${RED}✗ $FAILED check(s) failed${NC}"
        return 1
    fi
}

# Run main
main "$@"
