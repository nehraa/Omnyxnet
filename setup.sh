#!/bin/bash

# WGT Automated Setup Script
# This script installs all dependencies and provides a CLI to run the system

set -e  # Exit on error

LOG_FILE="setup.log"
TEST_LOG_FILE="test_log.txt"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Install system dependencies
install_system_deps() {
    log_info "Installing system dependencies..."
    
    if command_exists apt-get; then
        log_info "Detected apt-get (Debian/Ubuntu)"
        sudo apt-get update
        sudo apt-get install -y build-essential pkg-config libssl-dev capnproto python3 python3-pip python3-venv
        log_success "System dependencies installed"
    elif command_exists brew; then
        log_info "Detected Homebrew (macOS)"
        brew install capnp openssl pkg-config python3
        log_success "System dependencies installed"
    else
        log_error "Unsupported package manager. Please install dependencies manually:"
        log_error "  - build-essential / gcc"
        log_error "  - pkg-config"
        log_error "  - libssl-dev / openssl"
        log_error "  - capnproto"
        log_error "  - python3, python3-pip, python3-venv"
        exit 1
    fi
}

# Install Go
install_go() {
    log_info "Checking Go installation..."
    
    if command_exists go; then
        GO_VERSION=$(go version | awk '{print $3}')
        log_success "Go already installed: $GO_VERSION"
    else
        log_info "Installing Go 1.24..."
        wget https://go.dev/dl/go1.24.0.linux-amd64.tar.gz -O /tmp/go.tar.gz
        sudo rm -rf /usr/local/go
        sudo tar -C /usr/local -xzf /tmp/go.tar.gz
        echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc
        export PATH=$PATH:/usr/local/go/bin
        log_success "Go installed successfully"
    fi
}

# Install Rust
install_rust() {
    log_info "Checking Rust installation..."
    
    if command_exists rustc; then
        RUST_VERSION=$(rustc --version)
        log_success "Rust already installed: $RUST_VERSION"
    else
        log_info "Installing Rust..."
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
        source "$HOME/.cargo/env"
        log_success "Rust installed successfully"
    fi
}

# Setup Python environment
setup_python() {
    log_info "Setting up Python environment..."
    
    cd python
    
    if [ ! -d ".venv" ]; then
        log_info "Creating Python virtual environment..."
        python3 -m venv .venv
    fi
    
    source .venv/bin/activate
    log_info "Installing Python dependencies..."
    pip install --upgrade pip
    
    # Install minimal requirements by default (torch is optional and very large)
    if [ -f "requirements-minimal.txt" ]; then
        log_info "Installing minimal requirements (for testing)..."
        pip install -r requirements-minimal.txt
        log_info "Note: For AI features, install torch separately: pip install torch>=2.0.0"
    else
        log_warning "requirements-minimal.txt not found, installing full requirements..."
        pip install -r requirements.txt
    fi
    
    deactivate
    
    cd ..
    log_success "Python environment setup complete"
}

# Build Go components
build_go() {
    log_info "Building Go components..."
    
    cd go
    log_info "Installing Go dependencies..."
    go mod download
    log_info "Compiling Go node..."
    make build
    # Also copy to root of go directory for backward compatibility
    if [ -f "bin/go-node" ]; then
        cp bin/go-node go-node
    fi
    cd ..
    
    log_success "Go components built successfully"
}

# Build Rust components
build_rust() {
    log_info "Building Rust components..."
    
    cd rust
    log_info "Compiling Rust node (release mode)..."
    cargo build --release
    cd ..
    
    log_success "Rust components built successfully"
}

# Full installation
full_install() {
    log_info "Starting full installation..."
    log_info "==========================================="
    
    install_system_deps
    install_go
    install_rust
    setup_python
    
    # Build in correct order: Rust library first (needed by Go FFI), then Go, then Rust binary
    log_info "Building components in correct order..."
    build_rust  # This builds both the library and binary
    build_go    # This depends on Rust library for FFI
    
    log_success "==========================================="
    log_success "Installation complete!"
    log_info ""
    log_info "Components built:"
    log_info "  ✓ Rust library: rust/target/release/libpangea_ces.so"
    log_info "  ✓ Rust node: rust/target/release/pangea-rust-node"
    log_info "  ✓ Go node: go/bin/go-node"
    log_info "  ✓ Python venv: python/.venv"
    log_info ""
    log_info "You can now run tests or start nodes using this CLI"
}

# Run tests with logging
run_test() {
    local test_name=$1
    local test_script=$2
    
    log_info "Running $test_name..."
    echo "========================================" >> "$TEST_LOG_FILE"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Running: $test_name" >> "$TEST_LOG_FILE"
    echo "========================================" >> "$TEST_LOG_FILE"
    
    if bash "$test_script" >> "$TEST_LOG_FILE" 2>&1; then
        log_success "$test_name passed"
        echo "[PASSED] $test_name" >> "$TEST_LOG_FILE"
    else
        log_error "$test_name failed (check $TEST_LOG_FILE for details)"
        echo "[FAILED] $test_name" >> "$TEST_LOG_FILE"
        return 1
    fi
    
    echo "" >> "$TEST_LOG_FILE"
}

# CLI Menu
show_menu() {
    clear
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}       WGT System Control Panel${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo "1) Full Installation (Install all dependencies)"
    echo "2) Run Go Tests"
    echo "3) Run Python Tests"
    echo "4) Run Rust Tests"
    echo "5) Run Integration Tests"
    echo "6) Run 2-Node StreamUpdates Test"
    echo "7) Run All Localhost Tests"
    echo "8) Run Comprehensive Localhost Test (Multi-node)"
    echo "9) Setup Cross-Device/WAN Testing"
    echo "10) Run Upload/Download Tests (Local)"
    echo "11) Run Upload/Download Tests (Cross-Device)"
    echo "12) Run FFI Integration Test"
    echo "13) Run CES Wiring Test"
    echo "14) View Setup Log"
    echo "15) View Test Log"
    echo "16) Clean Build Artifacts"
    echo "0) Exit"
    echo ""
    echo -n "Select an option: "
}

# Clean build artifacts
clean_builds() {
    log_info "Cleaning build artifacts..."
    
    # Clean Go
    if [ -d "go" ]; then
        cd go
        make clean 2>/dev/null || rm -f go-node go-node.log
        cd ..
    fi
    
    # Clean Rust
    if [ -d "rust/target" ]; then
        cd rust
        cargo clean
        cd ..
    fi
    
    # Clean Python cache
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    
    log_success "Build artifacts cleaned"
}

# Main CLI loop
main() {
    # Create log files if they don't exist
    touch "$LOG_FILE"
    touch "$TEST_LOG_FILE"
    
    log_info "WGT Setup Script Started"
    
    while true; do
        show_menu
        read -r choice
        
        case $choice in
            1)
                log_info "User selected: Full Installation"
                full_install
                echo ""
                read -p "Press Enter to continue..."
                ;;
            2)
                log_info "User selected: Run Go Tests"
                # Build Rust library first (required for Go)
                log_info "Building Rust library (required for Go)..."
                cd rust
                cargo build --release --lib >> "$LOG_FILE" 2>&1
                cd ..
                log_success "Rust library built"
                run_test "Go Tests" "tests/test_go.sh"
                echo ""
                read -p "Press Enter to continue..."
                ;;
            3)
                log_info "User selected: Run Python Tests"
                run_test "Python Tests" "tests/test_python.sh"
                echo ""
                read -p "Press Enter to continue..."
                ;;
            4)
                log_info "User selected: Run Rust Tests"
                run_test "Rust Tests" "tests/test_rust.sh"
                echo ""
                read -p "Press Enter to continue..."
                ;;
            5)
                log_info "User selected: Run Integration Tests"
                run_test "Integration Tests" "tests/test_integration.sh"
                echo ""
                read -p "Press Enter to continue..."
                ;;
            6)
                log_info "User selected: Run 2-Node StreamUpdates Test"
                run_test "StreamUpdates Test" "tests/test_stream_updates.sh"
                echo ""
                read -p "Press Enter to continue..."
                ;;
            7)
                log_info "User selected: Run All Localhost Tests"
                echo "Running complete test suite..."
                # Build Rust library first (required for Go tests)
                log_info "Building Rust library (required for Go)..."
                cd rust
                cargo build --release --lib >> "$LOG_FILE" 2>&1
                cd ..
                log_success "Rust library built"
                run_test "Go Tests" "tests/test_go.sh"
                run_test "Python Tests" "tests/test_python.sh"
                run_test "Rust Tests" "tests/test_rust.sh"
                run_test "Integration Tests" "tests/test_integration.sh"
                run_test "StreamUpdates Test" "tests/test_stream_updates.sh"
                run_test "FFI Integration Test" "tests/test_ffi_integration.sh"
                run_test "Upload/Download Local Test" "tests/test_upload_download_local.sh"
                log_success "All localhost tests completed!"
                echo ""
                read -p "Press Enter to continue..."
                ;;
            8)
                log_info "User selected: Run Comprehensive Localhost Test"
                run_test "Comprehensive Localhost Test" "tests/test_localhost_full.sh"
                echo ""
                read -p "Press Enter to continue..."
                ;;
            9)
                log_info "User selected: Setup Cross-Device/WAN Testing"
                echo ""
                echo -e "${BLUE}========================================${NC}"
                echo -e "${BLUE}   Cross-Device / WAN Testing Setup${NC}"
                echo -e "${BLUE}========================================${NC}"
                echo ""
                echo "This will help you set up nodes for cross-device testing."
                echo ""
                echo "Options:"
                echo "  1) Start first device (bootstrap node)"
                echo "  2) Start additional device (join network)"
                echo "  3) Run cross-device upload/download test"
                echo ""
                read -p "Select option (1-3): " cross_choice
                case $cross_choice in
                    1)
                        echo ""
                        echo -e "${GREEN}Starting bootstrap node...${NC}"
                        echo "Use: ./scripts/easy_test.sh 1"
                        ./scripts/easy_test.sh 1
                        ;;
                    2)
                        echo ""
                        echo "You will need connection info from the bootstrap node."
                        read -p "Press Enter when ready to continue..."
                        ./scripts/easy_test.sh
                        ;;
                    3)
                        run_test "Cross-Device Upload/Download Test" "tests/test_upload_download_cross_device.sh"
                        ;;
                    *)
                        echo -e "${RED}Invalid option${NC}"
                        ;;
                esac
                echo ""
                read -p "Press Enter to continue..."
                ;;
            10)
                log_info "User selected: Run Upload/Download Tests (Local)"
                run_test "Upload/Download Local Test" "tests/test_upload_download_local.sh"
                echo ""
                read -p "Press Enter to continue..."
                ;;
            11)
                log_info "User selected: Run Upload/Download Tests (Cross-Device)"
                echo ""
                echo -e "${YELLOW}Note: This requires nodes already running on different devices.${NC}"
                echo "Have you set up nodes on multiple devices? (y/n)"
                read -p "> " setup_done
                if [ "$setup_done" = "y" ]; then
                    run_test "Cross-Device Upload/Download Test" "tests/test_upload_download_cross_device.sh"
                else
                    echo "Please use option 9 to setup cross-device testing first."
                fi
                echo ""
                read -p "Press Enter to continue..."
                ;;
            12)
                log_info "User selected: Run FFI Integration Test"
                run_test "FFI Integration Test" "tests/test_ffi_integration.sh"
                echo ""
                read -p "Press Enter to continue..."
                ;;
            13)
                log_info "User selected: Run CES Wiring Test"
                run_test "CES Wiring Test" "tests/test_ces_simple.sh"
                echo ""
                read -p "Press Enter to continue..."
                ;;
            14)
                log_info "User selected: View Setup Log"
                less "$LOG_FILE"
                ;;
            15)
                log_info "User selected: View Test Log"
                less "$TEST_LOG_FILE"
                ;;
            16)
                log_info "User selected: Clean Build Artifacts"
                clean_builds
                echo ""
                read -p "Press Enter to continue..."
                ;;
            0)
                log_info "User selected: Exit"
                log_info "WGT Setup Script Ended"
                echo -e "${GREEN}Goodbye!${NC}"
                exit 0
                ;;
            *)
                log_warning "Invalid option selected: $choice"
                echo -e "${RED}Invalid option. Please try again.${NC}"
                sleep 2
                ;;
        esac
    done
}

# Run main
main
