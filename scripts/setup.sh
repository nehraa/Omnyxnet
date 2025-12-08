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
            portaudio19-dev libportaudio2 libportaudiocpp0 libopencv-dev \
            python3-dev libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev \
            libgstreamer1.0-dev gstreamer1.0-plugins-base gstreamer1.0-plugins-good
        log_success "System dependencies installed"
    elif command_exists brew; then
        log_info "Detected Homebrew (macOS)"
        brew install capnp openssl pkg-config python3 sdl2 sdl2_image sdl2_mixer sdl2_ttf gstreamer
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
    echo -e "${GREEN}2) Establish Network Connection (Manager/Worker)${NC}"
    echo "3) Run Go Tests"
    echo "4) Run Python Tests"
    echo "5) Run Rust Tests"
    echo "6) Run Integration Tests"
    echo "7) Run 2-Node StreamUpdates Test"
    echo "8) Run All Localhost Tests"
    echo "9) Run Comprehensive Localhost Test (Multi-node)"
    echo "10) Setup Cross-Device/WAN Testing"
    echo "11) Run Upload/Download Tests (Local)"
    echo "12) Run Upload/Download Tests (Cross-Device)"
    echo "13) Run FFI Integration Test"
    echo "14) Run CES Wiring Test"
    echo "15) Run Phase 1 Features Test (Brotli, Opus, Metrics)"
    echo "16) Run Phase 1 Audio Integration Test"
    echo "17) Run Phase 1 Performance Benchmarks"
    echo "18) Run Streaming & AI Wiring Test (Phase 1&2)"
    echo "19) Distributed Compute Menu"
    echo "20) DCDN Demo (Distributed CDN System)"
    echo "21) Run Live P2P Test (Chat/Voice/Video)"
    echo "22) Launch Desktop App (Kivy+KivyMD GUI)"
    echo "23) Check Network Status"
    echo "24) View Setup Log"
    echo "25) View Test Log"
    echo "26) Clean Build Artifacts"
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

# =============================================================================
# Network Connection - Establish peer connections for distributed computing
# =============================================================================

# Source the network registry module
source "$SCRIPT_DIR/network_registry.sh" 2>/dev/null || true

establish_network_connection() {
    clear
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}   ESTABLISH NETWORK CONNECTION${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "This will connect your node to the WGT distributed network."
    echo ""
    echo -e "${CYAN}Choose your role:${NC}"
    echo ""
    echo "  1) ${GREEN}Manager (Initiator)${NC}"
    echo "     - Start first on the primary device"
    echo "     - Wait for Workers to connect"
    echo "     - Orchestrates distributed compute jobs"
    echo ""
    echo "  2) ${YELLOW}Worker (Responder)${NC}"
    echo "     - Connect to an existing Manager"
    echo "     - Execute compute tasks"
    echo "     - Requires Manager's peer address"
    echo ""
    echo "  3) ${BLUE}Check Network Status${NC}"
    echo "     - View connected peers"
    echo "     - Show network health"
    echo ""
    echo "  q) Back to main menu"
    echo ""
    read -p "Select role (1/2/3/q): " role_choice
    
    case "$role_choice" in
        1)
            start_manager_node
            ;;
        2)
            start_worker_node
            ;;
        3)
            "$SCRIPT_DIR/check_network.sh" --status
            echo ""
            read -p "Press Enter to continue..."
            ;;
        q|Q)
            return
            ;;
        *)
            echo -e "${RED}Invalid option${NC}"
            sleep 1
            ;;
    esac
}

start_manager_node() {
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}   Starting Manager Node${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    
    # Initialize registry
    init_registry
    
    # Build Go node if needed
    if [ ! -f "$PROJECT_ROOT/go/bin/go-node" ]; then
        log_info "Building Go node..."
        build_go
    fi
    
    # Default ports
    local CAPNP_PORT=8080
    local LIBP2P_PORT=9081
    
    echo "Using default ports:"
    echo "  Cap'n Proto RPC: ${CAPNP_PORT}"
    echo "  libp2p:          ${LIBP2P_PORT}"
    echo ""
    read -p "Change ports? (y/N): " change_ports
    
    if [ "$change_ports" = "y" ] || [ "$change_ports" = "Y" ]; then
        read -p "Cap'n Proto port [8080]: " new_capnp
        read -p "libp2p port [9081]: " new_libp2p
        CAPNP_PORT="${new_capnp:-8080}"
        LIBP2P_PORT="${new_libp2p:-9081}"
    fi
    
    # Set library path
    export LD_LIBRARY_PATH="$PROJECT_ROOT/rust/target/release:$LD_LIBRARY_PATH"
    export DYLD_LIBRARY_PATH="$PROJECT_ROOT/rust/target/release:$DYLD_LIBRARY_PATH"
    
    echo ""
    log_info "Starting Manager node on port ${CAPNP_PORT}..."
    echo ""
    
    # Start Go node as Manager
    cd "$PROJECT_ROOT/go"
    
    # Run node in background with mDNS discovery
    ./bin/go-node \
        -node-id=1 \
        -capnp-addr=":${CAPNP_PORT}" \
        -libp2p=true \
        -libp2p-port="${LIBP2P_PORT}" \
        -local \
        2>&1 | tee -a "$HOME/.wgt/logs/network.log" &
    
    local NODE_PID=$!
    
    # Wait for node to start
    echo ""
    echo "Waiting for node to initialize..."
    sleep 3
    
    # Check if process is running
    if ! kill -0 $NODE_PID 2>/dev/null; then
        log_error "Node failed to start. Check logs at ~/.wgt/logs/network.log"
        return 1
    fi
    
    # Extract peer info from logs (adapted from live_test.sh)
    local LOG_FILE="$HOME/.wgt/logs/network.log"
    local LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")
    local attempts=0
    local peer_id=""
    local full_multiaddr=""
    
    echo "Extracting peer information from logs..."
    while [ $attempts -lt 15 ]; do
        # Look for full multiaddr in logs
        full_multiaddr=$(grep -oE "/ip4/[0-9.]+/tcp/[0-9]+/p2p/[a-zA-Z0-9]+" "$LOG_FILE" 2>/dev/null | \
                        grep -v "127.0.0.1" | tail -1 || true)
        
        if [ -n "$full_multiaddr" ]; then
            peer_id=$(echo "$full_multiaddr" | grep -oP '/p2p/\K[a-zA-Z0-9]+' || true)
            break
        fi
        
        # Fallback: look for peer ID in logs
        if [ -z "$peer_id" ]; then
            peer_id=$(grep -oP 'Node ID: \K[a-zA-Z0-9]+' "$LOG_FILE" 2>/dev/null | tail -1 || true)
        fi
        
        sleep 1
        attempts=$((attempts + 1))
    done
    
    # If we got a full multiaddr, use it
    if [ -n "$full_multiaddr" ]; then
        local extracted_ip=$(echo "$full_multiaddr" | grep -oP '/ip4/\K[0-9.]+' || true)
        # Replace 0.0.0.0 with actual local IP
        if [ "$extracted_ip" = "0.0.0.0" ]; then
            full_multiaddr=$(echo "$full_multiaddr" | sed "s|/ip4/0.0.0.0|/ip4/$LOCAL_IP|")
        fi
    elif [ -n "$peer_id" ]; then
        # Construct multiaddr from components
        full_multiaddr="/ip4/${LOCAL_IP}/tcp/${LIBP2P_PORT}/p2p/${peer_id}"
    else
        log_warning "Could not extract peer ID from logs. Connection may not work."
        full_multiaddr="/ip4/${LOCAL_IP}/tcp/${LIBP2P_PORT}"
    fi
    
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}   ✅ Manager Node Started!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "   Node ID:     1"
    echo "   RPC Address: ${LOCAL_IP}:${CAPNP_PORT}"
    echo "   P2P Port:    ${LIBP2P_PORT}"
    echo "   Mode:        MANAGER (Initiator)"
    
    if [ -n "$peer_id" ]; then
        # Truncate peer_id for display if too long
        local peer_id_display="$peer_id"
        if [ ${#peer_id} -gt 20 ]; then
            peer_id_display="${peer_id:0:20}..."
        fi
        echo "   Peer ID:     ${peer_id_display}"
    fi
    
    echo ""
    echo -e "${YELLOW}📋 Share this FULL ADDRESS with Workers:${NC}"
    echo ""
    echo -e "   ${CYAN}${full_multiaddr}${NC}"
    echo ""
    echo "   (Copy the full line above)"
    echo ""
    echo "   Workers should run: setup.sh → Option 2 → Worker"
    echo "   and paste this address when prompted."
    echo ""
    
    # Save to registry
    save_local_node "node-1" "$full_multiaddr" "${CAPNP_PORT}" "manager"
    
    echo "   Process ID: ${NODE_PID}"
    echo "   Logs: ~/.wgt/logs/network.log"
    echo ""
    echo -e "${CYAN}Press Ctrl+C to stop the node${NC}"
    echo ""
    
    # Wait for user or process to exit
    wait $NODE_PID 2>/dev/null || true
    
    echo ""
    log_info "Manager node stopped"
}

start_worker_node() {
    echo ""
    echo -e "${YELLOW}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}   Starting Worker Node${NC}"
    echo -e "${YELLOW}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    
    # Initialize registry
    init_registry
    
    # Build Go node if needed
    if [ ! -f "$PROJECT_ROOT/go/bin/go-node" ]; then
        log_info "Building Go node..."
        build_go
    fi
    
    echo "Enter the Manager's connection info:"
    echo ""
    echo "You can either:"
    echo "  1) Paste the full multiaddr (e.g., /ip4/192.168.1.100/tcp/9081/p2p/12D3...)"
    echo "  2) Enter IP and ports separately"
    echo ""
    read -p "Enter full multiaddr (or press Enter to use IP/port): " MANAGER_MULTIADDR
    
    local MANAGER_IP=""
    local MANAGER_PORT=""
    local MANAGER_PEER=""
    
    if [ -n "$MANAGER_MULTIADDR" ]; then
        # User provided full multiaddr
        MANAGER_PEER="$MANAGER_MULTIADDR"
        # Extract IP and RPC port for display (if possible)
        MANAGER_IP=$(echo "$MANAGER_MULTIADDR" | grep -oP '/ip4/\K[0-9.]+' || echo "unknown")
        echo ""
        read -p "Manager RPC port [8080]: " MANAGER_PORT
        MANAGER_PORT="${MANAGER_PORT:-8080}"
    else
        # Manual IP/port entry
        read -p "Manager IP address: " MANAGER_IP
        read -p "Manager RPC port [8080]: " MANAGER_PORT
        MANAGER_PORT="${MANAGER_PORT:-8080}"
        
        # Prompt for Manager's libp2p port and peer ID
        read -p "Manager's libp2p port [9081]: " input_manager_p2p_port
        local MANAGER_P2P_PORT="${input_manager_p2p_port:-9081}"
        read -p "Manager's peer ID (optional, for better connection): " MANAGER_PEER_ID
        
        if [ -n "$MANAGER_PEER_ID" ]; then
            MANAGER_PEER="/ip4/${MANAGER_IP}/tcp/${MANAGER_P2P_PORT}/p2p/${MANAGER_PEER_ID}"
        else
            MANAGER_PEER="/ip4/${MANAGER_IP}/tcp/${MANAGER_P2P_PORT}"
            log_warning "No peer ID provided. Connection may rely on mDNS discovery."
        fi
    fi
    
    # Worker ports (offset from manager)
    local CAPNP_PORT=8081
    local LIBP2P_PORT=9082
    local NODE_ID=2
    
    echo ""
    echo "Worker node configuration:"
    echo "  Node ID:     ${NODE_ID}"
    echo "  RPC Port:    ${CAPNP_PORT}"
    echo "  P2P Port:    ${LIBP2P_PORT}"
    echo ""
    read -p "Change Worker ports? (y/N): " change_ports
    
    if [ "$change_ports" = "y" ] || [ "$change_ports" = "Y" ]; then
        read -p "Node ID [2]: " new_id
        read -p "RPC port [8081]: " new_capnp
        read -p "P2P port [9082]: " new_libp2p
        NODE_ID="${new_id:-2}"
        CAPNP_PORT="${new_capnp:-8081}"
        LIBP2P_PORT="${new_libp2p:-9082}"
    fi
    
    # Set library path
    export LD_LIBRARY_PATH="$PROJECT_ROOT/rust/target/release:$LD_LIBRARY_PATH"
    export DYLD_LIBRARY_PATH="$PROJECT_ROOT/rust/target/release:$DYLD_LIBRARY_PATH"
    
    echo ""
    log_info "Starting Worker node, connecting to Manager at ${MANAGER_IP}:${MANAGER_PORT}..."
    log_info "Using peer address: ${MANAGER_PEER}"
    echo ""
    
    # Get local IP
    local LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")
    
    cd "$PROJECT_ROOT/go"
    
    # Start Worker node with connection to Manager
    ./bin/go-node \
        -node-id="${NODE_ID}" \
        -capnp-addr=":${CAPNP_PORT}" \
        -libp2p=true \
        -libp2p-port="${LIBP2P_PORT}" \
        -peers="${MANAGER_PEER}" \
        -local \
        2>&1 | tee -a "$HOME/.wgt/logs/network.log" &
    
    local NODE_PID=$!
    
    # Wait for connection
    echo ""
    echo "Connecting to Manager..."
    sleep 3
    
    if ! kill -0 $NODE_PID 2>/dev/null; then
        log_error "Worker failed to start. Check logs at ~/.wgt/logs/network.log"
        return 1
    fi
    
    # Extract worker's own peer info from logs
    local LOG_FILE="$HOME/.wgt/logs/network.log"
    local attempts=0
    local worker_peer_id=""
    local worker_multiaddr=""
    
    echo "Extracting worker peer information..."
    while [ $attempts -lt 15 ]; do
        # Look for full multiaddr in logs (get the last one which should be this worker)
        worker_multiaddr=$(grep -oE "/ip4/[0-9.]+/tcp/[0-9]+/p2p/[a-zA-Z0-9]+" "$LOG_FILE" 2>/dev/null | \
                          tail -1 || true)
        
        if [ -n "$worker_multiaddr" ]; then
            worker_peer_id=$(echo "$worker_multiaddr" | grep -oP '/p2p/\K[a-zA-Z0-9]+' || true)
            # Check if this is actually our worker's address by verifying the port
            local addr_port=$(echo "$worker_multiaddr" | grep -oP '/tcp/\K[0-9]+' || true)
            if [ "$addr_port" = "$LIBP2P_PORT" ]; then
                break
            fi
        fi
        
        sleep 1
        attempts=$((attempts + 1))
    done
    
    # Construct worker multiaddr if not found
    if [ -z "$worker_multiaddr" ] || [ -z "$worker_peer_id" ]; then
        # Try to get just peer ID
        worker_peer_id=$(grep -oP 'Node ID: \K[a-zA-Z0-9]+' "$LOG_FILE" 2>/dev/null | tail -1 || true)
        if [ -n "$worker_peer_id" ]; then
            worker_multiaddr="/ip4/${LOCAL_IP}/tcp/${LIBP2P_PORT}/p2p/${worker_peer_id}"
        else
            worker_multiaddr="/ip4/${LOCAL_IP}/tcp/${LIBP2P_PORT}"
        fi
    else
        # Replace 0.0.0.0 with actual local IP
        local extracted_ip=$(echo "$worker_multiaddr" | grep -oP '/ip4/\K[0-9.]+' || true)
        if [ "$extracted_ip" = "0.0.0.0" ]; then
            worker_multiaddr=$(echo "$worker_multiaddr" | sed "s|/ip4/0.0.0.0|/ip4/$LOCAL_IP|")
        fi
    fi
    
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}   ✅ Worker Node Started!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "   Node ID:       ${NODE_ID}"
    echo "   Local Address: ${LOCAL_IP}:${CAPNP_PORT}"
    echo "   P2P Port:      ${LIBP2P_PORT}"
    
    if [ -n "$worker_peer_id" ]; then
        # Truncate peer_id for display if too long
        local peer_id_display="$worker_peer_id"
        if [ ${#worker_peer_id} -gt 20 ]; then
            peer_id_display="${worker_peer_id:0:20}..."
        fi
        echo "   Peer ID:       ${peer_id_display}"
    fi
    
    echo "   Manager:       ${MANAGER_IP}:${MANAGER_PORT}"
    echo "   Mode:          WORKER (Responder)"
    echo ""
    echo -e "${CYAN}📋 This worker's full address:${NC}"
    echo ""
    echo -e "   ${CYAN}${worker_multiaddr}${NC}"
    echo ""
    
    # Save to registry
    save_local_node "node-${NODE_ID}" "$worker_multiaddr" "${CAPNP_PORT}" "worker"
    save_peer "manager" "${MANAGER_PEER}" "${MANAGER_PORT}" "connected"
    
    echo "   Process ID: ${NODE_PID}"
    echo "   Logs: ~/.wgt/logs/network.log"
    echo ""
    echo -e "${CYAN}Press Ctrl+C to stop the node${NC}"
    echo ""
    
    # Wait for user or process to exit
    wait $NODE_PID 2>/dev/null || true
    
    echo ""
    log_info "Worker node stopped"
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
                log_info "User selected: Establish Network Connection"
                establish_network_connection
                echo ""
                read -p "Press Enter to continue..."
                ;;
            3)
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
            4)
                log_info "User selected: Run Python Tests"
                run_test "Python Tests" "tests/test_python.sh"
                echo ""
                read -p "Press Enter to continue..."
                ;;
            5)
                log_info "User selected: Run Rust Tests"
                run_test "Rust Tests" "tests/test_rust.sh"
                echo ""
                read -p "Press Enter to continue..."
                ;;
            6)
                log_info "User selected: Run Integration Tests"
                run_test "Integration Tests" "tests/integration/test_integration.sh"
                echo ""
                read -p "Press Enter to continue..."
                ;;
            7)
                log_info "User selected: Run 2-Node StreamUpdates Test"
                run_test "StreamUpdates Test" "tests/streaming/test_stream_updates.sh"
                echo ""
                read -p "Press Enter to continue..."
                ;;
            8)
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
            9)
                log_info "User selected: Run Comprehensive Localhost Test"
                run_test "Comprehensive Localhost Test" "tests/integration/test_localhost_full.sh"
                echo ""
                read -p "Press Enter to continue..."
                ;;
            10)
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
            11)
                log_info "User selected: Run Upload/Download Tests (Local)"
                run_test "Upload/Download Local Test" "tests/integration/test_upload_download_local.sh"
                echo ""
                read -p "Press Enter to continue..."
                ;;
            12)
                log_info "User selected: Run Upload/Download Tests (Cross-Device)"
                echo ""
                echo -e "${YELLOW}Note: This requires nodes already running on different devices.${NC}"
                echo "Have you set up nodes on multiple devices? (y/n)"
                read -p "> " setup_done
                if [ "$setup_done" = "y" ]; then
                    run_interactive_test "Cross-Device Upload/Download Test" "tests/integration/test_upload_download_cross_device.sh"
                else
                    echo "Please use option 10 to setup cross-device testing first."
                fi
                echo ""
                read -p "Press Enter to continue..."
                ;;
            13)
                log_info "User selected: Run FFI Integration Test"
                run_test "FFI Integration Test" "tests/integration/test_ffi_integration.sh"
                echo ""
                read -p "Press Enter to continue..."
                ;;
            14)
                log_info "User selected: Run CES Wiring Test"
                run_test "CES Wiring Test" "tests/ces/test_ces_simple.sh"
                echo ""
                read -p "Press Enter to continue..."
                ;;
            15)
                log_info "User selected: Run Phase 1 Features Test"
                run_test "Phase 1 Features Test" "tests/test_phase1_features.sh"
                echo ""
                read -p "Press Enter to continue..."
                ;;
            16)
                log_info "User selected: Run Phase 1 Audio Integration Test"
                run_interactive_test "Phase 1 Audio Integration Test" "tests/test_phase1_audio.py"
                echo ""
                read -p "Press Enter to continue..."
                ;;
            17)
                log_info "User selected: Run Phase 1 Performance Benchmarks"
                run_interactive_test "Phase 1 Performance Benchmarks" "tests/test_phase1_benchmarks.sh"
                echo ""
                read -p "Press Enter to continue..."
                ;;
            18)
                log_info "User selected: Run Streaming & AI Wiring Test"
                run_test "Streaming & AI Wiring Test" "tests/streaming/test_streaming.sh"
                echo ""
                read -p "Press Enter to continue..."
                ;;
            19)
                log_info "User selected: Distributed Compute Menu"
                echo ""
                echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
                echo -e "${BLUE}   DISTRIBUTED COMPUTE MENU${NC}"
                echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
                echo ""
                echo -e "${CYAN}Connection Setup:${NC}"
                echo "  1) Start Node (Initiator) - Run on Device 1 first"
                echo "  2) Start Node (Responder) - Run on Device 2, connect to Initiator"
                echo ""
                echo -e "${CYAN}Run Tests (after connection established):${NC}"
                echo "  3) Run Distributed Test - Matrix multiplication"
                echo "  4) Run Distributed Test (Custom) - Specify host/port/size"
                echo "  5) Run Matrix Multiply CLI (New!)"
                echo ""
                echo -e "${CYAN}Local Tests (no connection needed):${NC}"
                echo "  6) Run Local Compute Tests - Unit tests, single node"
                echo ""
                echo "  q) Back to main menu"
                echo ""
                read -p "Select option: " dc_choice
                
                case "$dc_choice" in
                    1)
                        log_info "Starting Initiator Node"
                        echo ""
                        echo -e "${YELLOW}Starting initiator node...${NC}"
                        echo -e "${YELLOW}Keep this running and note the peer address${NC}"
                        echo ""
                        "$PROJECT_ROOT/scripts/start_initiator.sh"
                        ;;
                    2)
                        log_info "Starting Responder Node"
                        echo ""
                        "$PROJECT_ROOT/scripts/start_responder.sh"
                        echo ""
                        read -p "Press Enter to continue..."
                        ;;
                    3)
                        log_info "Running Distributed Test"
                        echo ""
                        "$PROJECT_ROOT/scripts/run_distributed_test.sh"
                        echo ""
                        read -p "Press Enter to continue..."
                        ;;
                    4)
                        log_info "Running Custom Distributed Test"
                        echo ""
                        read -p "Enter host (default: localhost): " custom_host
                        read -p "Enter port (default: 8080): " custom_port
                        read -p "Enter matrix size (default: 100): " custom_size
                        custom_host="${custom_host:-localhost}"
                        custom_port="${custom_port:-8080}"
                        custom_size="${custom_size:-100}"
                        "$PROJECT_ROOT/scripts/run_distributed_test.sh" "$custom_host" "$custom_port" "$custom_size"
                        echo ""
                        read -p "Press Enter to continue..."
                        ;;
                    5)
                        log_info "Running Matrix Multiply CLI"
                        echo ""
                        cd "$PROJECT_ROOT/python"
                        source .venv/bin/activate 2>/dev/null || python3 -m venv .venv && source .venv/bin/activate
                        read -p "Matrix size (default: 10): " mm_size
                        mm_size="${mm_size:-10}"
                        python main.py compute matrix-multiply --size "$mm_size" --generate --verify
                        echo ""
                        read -p "Press Enter to continue..."
                        ;;
                    6)
                        log_info "Running Local Compute Tests"
                        echo ""
                        # Run local tests from examples directory
                        if [ -x "$PROJECT_ROOT/tests/compute/examples/01_local_unit_tests.sh" ]; then
                            "$PROJECT_ROOT/tests/compute/examples/01_local_unit_tests.sh"
                        elif [ -x "$PROJECT_ROOT/tests/compute/examples/02_single_node_compute.sh" ]; then
                            "$PROJECT_ROOT/tests/compute/examples/02_single_node_compute.sh"
                        else
                            echo "No local tests found"
                        fi
                        echo ""
                        read -p "Press Enter to continue..."
                        ;;
                    q|Q)
                        continue
                        ;;
                    *)
                        echo -e "${RED}Invalid option${NC}"
                        echo ""
                        read -p "Press Enter to continue..."
                        ;;
                esac
                ;;
            20)
                log_info "User selected: DCDN Demo"
                echo ""
                echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
                echo -e "${BLUE}   DCDN DEMO - Distributed CDN System${NC}"
                echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
                echo ""
                echo "Choose DCDN test type:"
                echo "  1) Interactive Demo (local)"
                echo "  2) Container Tests (virtual containers)"
                echo "  3) Cross-Device Tests (assumes connection established)"
                echo "  q) Back to main menu"
                echo ""
                read -p "Select option (1-3/q): " dcdn_choice
                
                case "$dcdn_choice" in
                    1)
                        echo ""
                        echo "Running interactive DCDN demo..."
                        echo "This demonstrates:"
                        echo "  • ChunkStore (lock-free ring buffer)"
                        echo "  • FEC Engine (Reed-Solomon recovery)"
                        echo "  • P2P Engine (tit-for-tat bandwidth allocation)"
                        echo "  • Ed25519 signature verification"
                        echo "  • Complete chunk lifecycle"
                        echo ""
                        read -p "Press Enter to start demo..."
                        
                        cd "$PROJECT_ROOT/rust" || {
                            log_error "Failed to navigate to rust directory"
                            read -p "Press Enter to continue..."
                            continue
                        }
                        
                        if ! cargo run --example dcdn_demo 2>&1 | tee -a "$TEST_LOG_FILE"; then
                            log_error "DCDN demo failed"
                        else
                            log_success "DCDN demo completed"
                        fi
                        ;;
                    
                    2)
                        echo ""
                        echo "Running DCDN Container Tests..."
                        echo ""
                        echo "This will:"
                        echo "  • Create virtual container environment"
                        echo "  • Deploy DCDN nodes in containers"
                        echo "  • Test chunk transfer between containers"
                        echo "  • Verify FEC recovery in isolated network"
                        echo ""
                        read -p "Press Enter to start container tests..."
                        
                        # Check if Docker/Podman is available
                        if command_exists docker; then
                            CONTAINER_CMD="docker"
                        elif command_exists podman; then
                            CONTAINER_CMD="podman"
                        else
                            log_error "Docker or Podman required for container tests"
                            echo "Install with:"
                            echo "  Debian/Ubuntu: sudo apt-get install docker.io"
                            echo "  macOS: brew install docker"
                            read -p "Press Enter to continue..."
                            continue
                        fi
                        
                        log_info "Using container runtime: $CONTAINER_CMD"
                        
                        # Run DCDN container tests
                        cd "$PROJECT_ROOT/rust" || {
                            log_error "Failed to navigate to rust directory"
                            read -p "Press Enter to continue..."
                            continue
                        }
                        
                        # Build DCDN test image
                        log_info "Building DCDN test container..."
                        $CONTAINER_CMD build -t pangea-dcdn-test -f - . <<'EOF'
FROM rust:1.75-slim
WORKDIR /app
RUN apt-get update && apt-get install -y pkg-config libssl-dev
COPY Cargo.toml Cargo.lock ./
COPY src ./src
COPY examples ./examples
COPY tests ./tests
COPY config ./config
RUN cargo build --release --example dcdn_demo
RUN cargo build --release --lib
CMD ["cargo", "test", "--test", "test_dcdn"]
EOF
                        
                        if [ $? -eq 0 ]; then
                            log_success "Container image built successfully"
                            
                            # Run tests in container
                            log_info "Running DCDN tests in container..."
                            $CONTAINER_CMD run --rm pangea-dcdn-test 2>&1 | tee -a "$TEST_LOG_FILE"
                            
                            if [ ${PIPESTATUS[0]} -eq 0 ]; then
                                log_success "Container tests passed"
                            else
                                log_error "Container tests failed"
                            fi
                        else
                            log_error "Failed to build container image"
                        fi
                        ;;
                    
                    3)
                        echo ""
                        echo "Running DCDN Cross-Device Tests..."
                        echo ""
                        echo "Prerequisites:"
                        echo "  • Two devices must be on the same network"
                        echo "  • Connection should already be established"
                        echo "  • Firewall ports opened for QUIC"
                        echo ""
                        
                        read -p "Enter remote device IP address: " remote_ip
                        read -p "Enter remote device DCDN port (default 9090): " remote_port
                        remote_port="${remote_port:-9090}"
                        
                        log_info "Testing DCDN connection to ${remote_ip}:${remote_port}"
                        
                        # Test if remote is reachable
                        if nc -z -w 5 "$remote_ip" "$remote_port" 2>/dev/null; then
                            log_success "Remote DCDN node is reachable"
                            
                            # Run cross-device DCDN test
                            cd "$PROJECT_ROOT/python" || {
                                log_error "Failed to navigate to python directory"
                                read -p "Press Enter to continue..."
                                continue
                            }
                            
                            source .venv/bin/activate 2>/dev/null || {
                                log_error "Python virtual environment not found"
                                read -p "Press Enter to continue..."
                                continue
                            }
                            
                            log_info "Running DCDN cross-device connectivity test..."
                            # Note: DCDN test runs locally, but we can test connectivity
                            python3 -c "import socket; sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM); sock.settimeout(5); result = sock.connect_ex(('${remote_ip}', ${remote_port})); sock.close(); exit(0 if result == 0 else 1)" 2>&1
                            
                            if [ $? -eq 0 ]; then
                                log_success "Successfully connected to remote DCDN node"
                                log_info "Running local DCDN tests..."
                                python3 main.py dcdn test 2>&1 | tee -a "$TEST_LOG_FILE"
                            else
                                log_error "Failed to connect to remote node"
                            fi
                            
                            if [ ${PIPESTATUS[0]} -eq 0 ]; then
                                log_success "Cross-device test completed"
                            else
                                log_error "Cross-device test failed"
                            fi
                        else
                            log_error "Cannot reach remote DCDN node at ${remote_ip}:${remote_port}"
                            echo "Make sure:"
                            echo "  1. Remote device is running DCDN node"
                            echo "  2. Firewall allows port ${remote_port}"
                            echo "  3. Devices are on same network or have route"
                        fi
                        ;;
                    
                    q|Q)
                        continue
                        ;;
                    
                    *)
                        echo -e "${RED}Invalid option${NC}"
                        ;;
                esac
                
                echo ""
                read -p "Press Enter to continue..."
                ;;
            21)
                log_info "User selected: Run Live P2P Test"
                echo ""
                echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
                echo -e "${BLUE}   LIVE P2P TEST (Chat/Voice/Video)${NC}"
                echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
                echo ""
                read -p "Press Enter to start live test..."
                ./scripts/live_test.sh
                echo ""
                read -p "Press Enter to continue..."
                ;;
            22)
                log_info "User selected: Launch Desktop App"
                echo ""
                echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
                echo -e "${BLUE}   PANGEA NET DESKTOP APPLICATION (Kivy+KivyMD)${NC}"
                echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
                echo ""
                echo "Launching Desktop GUI Application..."
                echo ""
                echo "The desktop app provides:"
                echo "  • Graphical interface for all CLI features"
                echo "  • Node connection management"
                echo "  • Compute task submission"
                echo "  • File operations (upload/download)"
                echo "  • P2P communications (chat/voice/video)"
                echo "  • Network monitoring"
                echo "  • DCDN operations"
                echo ""
                
                # Check if Kivy and KivyMD are available
                if ! python3 -c "import kivy, kivymd" 2>/dev/null; then
                    log_error "Kivy or KivyMD is not installed"
                    echo ""
                    echo "Please install Kivy dependencies:"
                    echo "  cd python && source .venv/bin/activate"
                    echo "  pip install kivy>=2.2.0 kivymd>=1.1.1"
                    echo ""
                    read -p "Press Enter to continue..."
                    continue
                fi
                
                # Launch desktop app
                cd "$PROJECT_ROOT"
                python3 desktop_app_kivy.py
                
                echo ""
                read -p "Press Enter to continue..."
                ;;
            23)
                log_info "User selected: Check Network Status"
                "$SCRIPT_DIR/check_network.sh" --status
                echo ""
                read -p "Press Enter to continue..."
                ;;
            24)
                log_info "User selected: View Setup Log"
                less "$LOG_FILE"
                ;;
            25)
                log_info "User selected: View Test Log"
                less "$TEST_LOG_FILE"
                ;;
            26)
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
