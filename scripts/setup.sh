#!/bin/bash

# WGT Automated Setup Script
# This script installs all dependencies and provides a CLI to run the system
#
# SECURITY NOTE: Encryption Key Management
# For production deployments, set the CES_ENCRYPTION_KEY environment variable:
#   export CES_ENCRYPTION_KEY=$(openssl rand -hex 32)
# 
# Or use explicit key management in your code. See SECURITY.md for details.

set -e  # Exit on error

# Get the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

LOG_FILE="$PROJECT_ROOT/setup.log"
TEST_LOG_FILE="$PROJECT_ROOT/test_log.txt"

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

# Setup development environment PATH
setup_dev_env() {
    # Add Go tools to PATH if they exist
    if command_exists go; then
        GOPATH_BIN="$(go env GOPATH)/bin"
        if [ -d "$GOPATH_BIN" ]; then
            export PATH="$GOPATH_BIN:$PATH"
        fi
    fi
    
    # Add Rust tools to PATH if they exist
    if [ -d "$HOME/.cargo/bin" ]; then
        export PATH="$HOME/.cargo/bin:$PATH"
    fi
    
    # Add Python local bin to PATH
    if [ -d "$HOME/.local/bin" ]; then
        export PATH="$HOME/.local/bin:$PATH"
    fi
}

# Check system dependencies
check_system_dependencies() {
    log_info "Checking system dependencies..."
    local missing_deps=""
    
    # Check for essential build tools
    if ! command_exists make; then
        missing_deps="$missing_deps make"
    fi
    
    if ! command_exists gcc; then
        missing_deps="$missing_deps build-essential"
    fi
    
    if ! command_exists pkg-config; then
        missing_deps="$missing_deps pkg-config"
    fi
    
    # Check for Cap'n Proto
    if ! command_exists capnp; then
        missing_deps="$missing_deps capnproto"
    fi
    
    # Check for Git
    if ! command_exists git; then
        missing_deps="$missing_deps git"
    fi
    
    if [ -n "$missing_deps" ]; then
        log_error "Missing system dependencies:$missing_deps"
        log_warning "Please install them with: sudo apt-get install$missing_deps"
        return 1
    fi
    
    log_success "All system dependencies are satisfied"
    return 0
}

# Install system dependencies
install_system_deps() {
    log_info "Installing system dependencies..."
    
    if command_exists apt-get; then
        log_info "Detected apt-get (Debian/Ubuntu)"
        sudo apt-get update
        sudo apt-get install -y build-essential pkg-config libssl-dev capnproto python3 python3-pip python3-venv \
            portaudio19-dev libportaudio2 libportaudiocpp0 libopencv-dev
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
    
    # Prompt user for installation type
    if [ -f "requirements-minimal.txt" ]; then
        echo ""
        echo -e "${BLUE}Python Dependency Installation:${NC}"
        echo "  1) Minimal (testing only, ~200MB, no AI features)"
        echo "  2) Full (with torch for AI, ~5GB)"
        echo ""
        read -t 10 -p "Select installation type (1 or 2, default: 1): " install_type || install_type="1"
        
        if [ "$install_type" = "2" ]; then
            log_info "Installing full requirements (including torch for AI)..."
            pip install -r requirements.txt
        else
            log_info "Installing minimal requirements (for testing)..."
            pip install -r requirements-minimal.txt
            log_info "Note: For AI features later, run: cd python && source .venv/bin/activate && pip install torch>=2.0.0"
        fi
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
    
    # Ensure GOPATH/bin is in PATH for go tools (including capnpc-go)
    GOPATH_BIN="$(go env GOPATH)/bin"
    export PATH="$GOPATH_BIN:$PATH"
    
    # Install capnpc-go plugin if needed
    if [ ! -f "$GOPATH_BIN/capnpc-go" ]; then
        log_info "Installing capnpc-go plugin..."
        go install capnproto.org/go/capnp/v3/capnpc-go@latest
    fi
    
    # Find the go.capnp import path from the installed module
    CAPNP_GO_MOD=$(go list -m -f '{{.Dir}}' capnproto.org/go/capnp/v3 2>/dev/null || echo "")
    if [ -z "$CAPNP_GO_MOD" ]; then
        log_warning "capnproto.org/go/capnp/v3 module not found, downloading..."
        go get capnproto.org/go/capnp/v3
        CAPNP_GO_MOD=$(go list -m -f '{{.Dir}}' capnproto.org/go/capnp/v3)
    fi
    
    # Compile Cap'n Proto schema to generate Go bindings
    log_info "Compiling Cap'n Proto schema..."
    if [ -f "schema/schema.capnp" ]; then
        # Remove old generated files
        rm -f schema.capnp.go
        rm -f schema/schema.capnp.go
        rm -rf schema/schema
        # Generate Go bindings - output to current directory (go/) for package main
        PATH="$GOPATH_BIN:$PATH" capnp compile -I"$CAPNP_GO_MOD/std" -ogo schema/schema.capnp
        # Move generated file to go/ root since it's package main
        if [ -f "schema/schema/schema.capnp.go" ]; then
            mv schema/schema/schema.capnp.go schema.capnp.go
            rmdir schema/schema 2>/dev/null || true
        elif [ -f "schema/schema.capnp.go" ]; then
            mv schema/schema.capnp.go schema.capnp.go
        fi
    fi
    
    # Set library path for Rust shared library (needed for CGO linking)
    export CGO_LDFLAGS="-L$PROJECT_ROOT/rust/target/release"
    export LD_LIBRARY_PATH="$PROJECT_ROOT/rust/target/release:$LD_LIBRARY_PATH"
    export DYLD_LIBRARY_PATH="$PROJECT_ROOT/rust/target/release:$DYLD_LIBRARY_PATH"
    
    log_info "Compiling Go node..."
    mkdir -p bin
    go build -o bin/go-node .
    
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
    
    # Setup development environment PATH first
    setup_dev_env
    
    # Check system dependencies before starting
    if ! check_system_dependencies; then
        log_error "Please install missing system dependencies and try again"
        return 1
    fi
    
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

# Run interactive test (shows output to user)
run_interactive_test() {
    local test_name=$1
    local test_script=$2
   
    log_info "Running $test_name (Interactive)..."
    echo "========================================" >> "$TEST_LOG_FILE"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Running: $test_name" >> "$TEST_LOG_FILE"
    echo "========================================" >> "$TEST_LOG_FILE"
   
    # Run with tee to show output and log it
    # We use pipefail to capture the exit code of the script, not tee
    set -o pipefail
    if bash "$test_script" 2>&1 | tee -a "$TEST_LOG_FILE"; then
        log_success "$test_name passed"
        echo "[PASSED] $test_name" >> "$TEST_LOG_FILE"
    else
        log_error "$test_name failed"
        echo "[FAILED] $test_name" >> "$TEST_LOG_FILE"
        set +o pipefail
        return 1
    fi
    set +o pipefail
   
    echo "" >> "$TEST_LOG_FILE"
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
    echo "14) Run Phase 1 Features Test (Brotli, Opus, Metrics)"
    echo "15) Run Phase 1 Audio Integration Test"
    echo "16) Run Phase 1 Performance Benchmarks"
    echo "17) Run Streaming & AI Wiring Test (Phase 1&2)"
    echo "18) Run Distributed Compute Test"
    echo "19) Run Live P2P Test (Chat/Voice/Video)"
    echo "20) View Setup Log"
    echo "21) View Test Log"
    echo "22) Clean Build Artifacts"
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
                run_test "Integration Tests" "tests/integration/test_integration.sh"
                echo ""
                read -p "Press Enter to continue..."
                ;;
            6)
                log_info "User selected: Run 2-Node StreamUpdates Test"
                run_test "StreamUpdates Test" "tests/streaming/test_stream_updates.sh"
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
                run_test "Integration Tests" "tests/integration/test_integration.sh"
                run_test "StreamUpdates Test" "tests/streaming/test_stream_updates.sh"
                run_test "FFI Integration Test" "tests/integration/test_ffi_integration.sh"
                run_test "Upload/Download Local Test" "tests/integration/test_upload_download_local.sh"
                log_success "All localhost tests completed!"
                echo ""
                read -p "Press Enter to continue..."
                ;;
            8)
                log_info "User selected: Run Comprehensive Localhost Test"
                run_test "Comprehensive Localhost Test" "tests/integration/test_localhost_full.sh"
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
                        run_interactive_test "Cross-Device Upload/Download Test" "tests/integration/test_upload_download_cross_device.sh"
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
                run_test "Upload/Download Local Test" "tests/integration/test_upload_download_local.sh"
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
                    run_interactive_test "Cross-Device Upload/Download Test" "tests/integration/test_upload_download_cross_device.sh"
                else
                    echo "Please use option 9 to setup cross-device testing first."
                fi
                echo ""
                read -p "Press Enter to continue..."
                ;;
            12)
                log_info "User selected: Run FFI Integration Test"
                run_test "FFI Integration Test" "tests/integration/test_ffi_integration.sh"
                echo ""
                read -p "Press Enter to continue..."
                ;;
            13)
                log_info "User selected: Run CES Wiring Test"
                run_test "CES Wiring Test" "tests/ces/test_ces_simple.sh"
                echo ""
                read -p "Press Enter to continue..."
                ;;
            14)
                log_info "User selected: Run Phase 1 Features Test"
                run_test "Phase 1 Features Test" "tests/test_phase1_features.sh"
                echo ""
                read -p "Press Enter to continue..."
                ;;
            15)
                log_info "User selected: Run Phase 1 Audio Integration Test"
                run_interactive_test "Phase 1 Audio Integration Test" "tests/test_phase1_audio.py"
                echo ""
                read -p "Press Enter to continue..."
                ;;
            16)
                log_info "User selected: Run Phase 1 Performance Benchmarks"
                run_interactive_test "Phase 1 Performance Benchmarks" "tests/test_phase1_benchmarks.sh"
                echo ""
                read -p "Press Enter to continue..."
                ;;
            17)
                log_info "User selected: Run Streaming & AI Wiring Test"
                run_test "Streaming & AI Wiring Test" "tests/streaming/test_streaming.sh"
                echo ""
                read -p "Press Enter to continue..."
                ;;
            18)
                log_info "User selected: Run Compute Tests"
                echo ""
                echo -e "${BLUE}========================================${NC}"
                echo -e "${BLUE}   Compute Tests (organized examples)${NC}"
                echo -e "${BLUE}========================================${NC}"
                echo ""
                
                # Dynamically list all compute examples
                EXAMPLES_DIR="$PROJECT_ROOT/tests/compute/examples"
                if [ ! -d "$EXAMPLES_DIR" ]; then
                    log_error "Examples directory not found: $EXAMPLES_DIR"
                    echo ""
                    read -p "Press Enter to continue..."
                    continue
                fi
                
                # Build array of example scripts
                declare -a example_scripts
                declare -a example_names
                i=1
                
                for script in $(ls -1 "$EXAMPLES_DIR"/*.sh 2>/dev/null | sort); do
                    # Extract name from filename (remove number prefix and .sh)
                    name=$(basename "$script" .sh | sed 's/^[0-9]*_//' | tr '_' ' ')
                    example_scripts[$i]="$script"
                    example_names[$i]="$name"
                    echo "  $i) $name"
                    i=$((i+1))
                done
                
                if [ $i -eq 1 ]; then
                    echo "No compute examples found in $EXAMPLES_DIR"
                    echo ""
                    read -p "Press Enter to continue..."
                    continue
                fi
                
                echo "  q) Back to main menu"
                echo ""
                read -p "Select example (1-$((i-1))) or (q) to quit: " example_choice
                
                if [ "$example_choice" = "q" ] || [ "$example_choice" = "Q" ]; then
                    echo ""
                    continue
                fi
                
                # Validate choice
                if ! [[ "$example_choice" =~ ^[0-9]+$ ]] || [ "$example_choice" -lt 1 ] || [ "$example_choice" -ge $i ]; then
                    echo -e "${RED}Invalid selection${NC}"
                    echo ""
                    read -p "Press Enter to continue..."
                    continue
                fi
                
                # Run selected example
                selected_script="${example_scripts[$example_choice]}"
                selected_name="${example_names[$example_choice]}"
                
                echo ""
                log_info "Running: $selected_name"
                echo ""
                
                if [ -x "$selected_script" ]; then
                    "$selected_script"
                else
                    log_error "Script not executable: $selected_script"
                fi
                
                echo ""
                read -p "Press Enter to continue..."
                ;;
            19)
                log_info "User selected: Run Live P2P Test"
                echo ""
                echo -e "${BLUE}========================================${NC}"
                echo -e "${BLUE}   Live P2P Test (Chat/Voice/Video)${NC}"
                echo -e "${BLUE}========================================${NC}"
                echo ""
                echo "This launches the interactive live_test.sh script."
                echo "You can test Chat, Voice, and Video streaming."
                echo ""
                read -p "Press Enter to start live test..."
                ./scripts/live_test.sh
                echo ""
                read -p "Press Enter to continue..."
                ;;
            20)
                log_info "User selected: View Setup Log"
                less "$LOG_FILE"
                ;;
            21)
                log_info "User selected: View Test Log"
                less "$TEST_LOG_FILE"
                ;;
            22)
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
