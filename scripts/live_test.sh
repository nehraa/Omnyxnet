#!/bin/bash
# ╔═══════════════════════════════════════════════════════════════╗
# ║   🎯 PANGEA NET - ONE-CLICK LIVE STREAMING TEST               ║
# ║   Just run this on BOTH devices, select 1/2/3, BOOM!          ║
# ╚═══════════════════════════════════════════════════════════════╝
#
# USAGE:
#   Device 1: ./live_test.sh  → Press Y → Copy the peer address
#   Device 2: ./live_test.sh  → Press N → Paste address → Done!
#   Both: Select 1 (Chat), 2 (Voice), or 3 (Video)
#
# REQUIREMENTS:
#   - Both devices on same network (WiFi/LAN) OR have open ports for WAN
#   - Python3 with numpy installed
#   - Project built (script auto-builds if needed)

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

# Get project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Create directories
mkdir -p test_media/samples
mkdir -p ~/.pangea/live_test

# Session files
SESSION_FILE="$HOME/.pangea/live_test/session.json"
PEER_FILE="$HOME/.pangea/live_test/peer_address.txt"
NODE_PID_FILE="$HOME/.pangea/live_test/node.pid"
LOG_FILE="$HOME/.pangea/live_test/node.log"
REMOTE_PEER_FILE="$HOME/.pangea/live_test/remote_peer.txt"

# ============================================================
# UTILITY FUNCTIONS
# ============================================================

cleanup() {
    if [ -f "$NODE_PID_FILE" ]; then
        local pid=$(cat "$NODE_PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            kill "$pid" 2>/dev/null || true
        fi
        rm -f "$NODE_PID_FILE"
    fi
}

get_local_ip() {
    # Try multiple methods to get local IP
    local ip=""
    
    # Method 1: hostname -I (Linux)
    ip=$(hostname -I 2>/dev/null | awk '{print $1}')
    
    # Method 2: ip route (Linux)
    if [ -z "$ip" ]; then
        ip=$(ip route get 1 2>/dev/null | awk '{print $(NF-2);exit}')
    fi
    
    # Method 3: ifconfig (macOS/BSD)
    if [ -z "$ip" ]; then
        ip=$(ifconfig 2>/dev/null | grep 'inet ' | grep -v '127.0.0.1' | head -1 | awk '{print $2}')
    fi
    
    # Fallback
    if [ -z "$ip" ]; then
        ip="127.0.0.1"
    fi
    
    echo "$ip"
}

is_node_running() {
    if [ -f "$NODE_PID_FILE" ]; then
        local pid=$(cat "$NODE_PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

# ============================================================
# BUILD PROJECT
# ============================================================

build_if_needed() {
    echo -e "${CYAN}Checking build...${NC}"
    
    # Build Go node if needed
    if [ ! -f "$PROJECT_ROOT/go/bin/go-node" ]; then
        echo -e "${YELLOW}Building Go node...${NC}"
        cd "$PROJECT_ROOT/go"
        make build 2>/dev/null || go build -o bin/go-node . 2>/dev/null || {
            echo -e "${RED}Failed to build Go node. Please run: cd go && make build${NC}"
            exit 1
        }
        cd "$PROJECT_ROOT"
        echo -e "${GREEN}✅ Go node built${NC}"
    fi
    
    # Build Rust library if needed
    if [ ! -f "$PROJECT_ROOT/rust/target/release/libpangea_ces.so" ] && \
       [ ! -f "$PROJECT_ROOT/rust/target/release/libpangea_ces.dylib" ]; then
        echo -e "${YELLOW}Building Rust library...${NC}"
        cd "$PROJECT_ROOT/rust"
        cargo build --release 2>/dev/null || {
            echo -e "${RED}Failed to build Rust. Please run: cd rust && cargo build --release${NC}"
            exit 1
        }
        cd "$PROJECT_ROOT"
        echo -e "${GREEN}✅ Rust library built${NC}"
    fi
    
    echo -e "${GREEN}✅ Build ready${NC}"
}

# ============================================================
# EXTRACT PEER INFO FROM LOGS (THE CORRECT WAY!)
# ============================================================
# The Go node outputs:
#   📍 Node ID: 12D3KooW...
#   🌐 Listening addresses:
#      /ip4/192.168.1.100/tcp/44119/p2p/12D3KooW...
#      /ip4/127.0.0.1/tcp/44119/p2p/12D3KooW...
#
# We need to extract the multiaddr with the local network IP (not 127.0.0.1)

extract_peer_info() {
    local log_file="$1"
    local local_ip=$(get_local_ip)
    
    # Wait for log to have peer info
    local attempts=0
    local peer_id=""
    local p2p_port=""
    local full_multiaddr=""
    
    echo -e "${CYAN}Extracting peer information...${NC}"
    
    while [ $attempts -lt 15 ]; do
        # Method 1: Try to extract from "Listening addresses" format
        # The Go node outputs: /ip4/x.x.x.x/tcp/PORT/p2p/PEER_ID
        full_multiaddr=$(grep -oE "/ip4/[0-9.]+/tcp/[0-9]+/p2p/[a-zA-Z0-9]+" "$log_file" 2>/dev/null | \
                        grep -v "127.0.0.1" | head -1 || true)
        
        if [ -n "$full_multiaddr" ]; then
            # Extract components from multiaddr
            peer_id=$(echo "$full_multiaddr" | grep -oP '/p2p/\K[a-zA-Z0-9]+' || true)
            p2p_port=$(echo "$full_multiaddr" | grep -oP '/tcp/\K[0-9]+' || true)
            break
        fi
        
        # Method 2: Extract Node ID separately
        if [ -z "$peer_id" ]; then
            peer_id=$(grep -oP 'Node ID: \K[a-zA-Z0-9]+' "$log_file" 2>/dev/null | head -1 || true)
        fi
        
        # Method 3: Try Peer ID format
        if [ -z "$peer_id" ]; then
            peer_id=$(grep -oP 'Peer ID: \K[a-zA-Z0-9]+' "$log_file" 2>/dev/null | head -1 || true)
        fi
        
        sleep 1
        attempts=$((attempts + 1))
    done
    
    # If we got a full multiaddr, use it
    if [ -n "$full_multiaddr" ]; then
        # Replace the IP with our detected local IP (in case log shows 0.0.0.0)
        local extracted_ip=$(echo "$full_multiaddr" | grep -oP '/ip4/\K[0-9.]+' || true)
        if [ "$extracted_ip" = "0.0.0.0" ]; then
            full_multiaddr=$(echo "$full_multiaddr" | sed "s|/ip4/0.0.0.0|/ip4/$local_ip|")
        fi
        echo "$full_multiaddr"
        return 0
    fi
    
    # Fallback: construct multiaddr from components
    if [ -n "$peer_id" ]; then
        # Try to find the port from listening address
        if [ -z "$p2p_port" ]; then
            p2p_port=$(grep -oP '/tcp/\K[0-9]+' "$log_file" 2>/dev/null | head -1 || echo "0")
        fi
        
        if [ "$p2p_port" != "0" ] && [ -n "$p2p_port" ]; then
            echo "/ip4/${local_ip}/tcp/${p2p_port}/p2p/${peer_id}"
            return 0
        fi
    fi
    
    # Complete fallback
    echo ""
    return 1
}

# ============================================================
# START/STOP NODE
# ============================================================

start_bootstrap_node() {
    echo -e "${CYAN}Starting bootstrap node...${NC}"
    
    cleanup  # Clean up any existing node
    
    # Clear old log
    > "$LOG_FILE"
    
    cd "$PROJECT_ROOT/go"
    # Note: libp2p uses random ports by default (tcp/0), which is correct!
    # The actual port is assigned by the OS and shown in the logs
    ./bin/go-node -node-id=1 -capnp-addr=:8080 -libp2p=true > "$LOG_FILE" 2>&1 &
    echo $! > "$NODE_PID_FILE"
    cd "$PROJECT_ROOT"
    
    # Wait for node to fully start
    echo -e "${YELLOW}Waiting for node to start...${NC}"
    sleep 4
    
    # Extract peer info using the correct method
    local peer_addr=$(extract_peer_info "$LOG_FILE")
    
    if [ -z "$peer_addr" ]; then
        echo -e "${RED}❌ Failed to extract peer address from logs${NC}"
        echo -e "${YELLOW}Log contents:${NC}"
        tail -20 "$LOG_FILE"
        return 1
    fi
    
    echo "$peer_addr" > "$PEER_FILE"
    
    # Also extract individual components for display
    local peer_id=$(echo "$peer_addr" | grep -oP '/p2p/\K[a-zA-Z0-9]+' || echo "unknown")
    local p2p_port=$(echo "$peer_addr" | grep -oP '/tcp/\K[0-9]+' || echo "unknown")
    local local_ip=$(echo "$peer_addr" | grep -oP '/ip4/\K[0-9.]+' || echo "unknown")
    
    echo -e "${GREEN}✅ Bootstrap node started!${NC}"
    echo ""
    # Use same display format as easy_test.sh to avoid user errors
    echo -e "╔════════════════════════════════════════╗"
    echo -e "║   🌍 Pangea Net - Easy Device Test    ║"
    echo -e "╚════════════════════════════════════════╝"
    echo ""
    echo -e "Select mode:"
    echo -e "  1. First device (bootstrap node)"
    echo -e "  2. Additional device (connect to network)"
    echo ""
    echo -e "Configuration:"
    echo -e "  Node ID: 1"
    echo -e "  Your IP: ${local_ip}"
    echo ""
    echo -e "✓ Peer ID: ${peer_id}"
    echo -e "✓ P2P Port: ${p2p_port}"
    echo -e "ℹ  Note: Both Peer ID and port change on each restart"
    echo ""
    echo -e "For other devices to join this network:"
    echo -e "  ./scripts/live_test.sh 2 ${peer_addr}"
    
    return 0
}

start_joining_node() {
    local bootstrap_peer="$1"
    
    echo -e "${CYAN}Connecting to network...${NC}"
    
    cleanup  # Clean up any existing node
    
    # Save remote peer for Python scripts
    echo "$bootstrap_peer" > "$REMOTE_PEER_FILE"
    
    # Clear old log
    > "$LOG_FILE"
    
    cd "$PROJECT_ROOT/go"
    ./bin/go-node -node-id=2 -capnp-addr=:8081 -libp2p=true \
                  -peers="$bootstrap_peer" > "$LOG_FILE" 2>&1 &
    echo $! > "$NODE_PID_FILE"
    cd "$PROJECT_ROOT"
    
    echo -e "${YELLOW}Connecting to peer...${NC}"
    sleep 4
    
    # Check if connected
    if grep -q "Connected to peer\|connected\|New connection" "$LOG_FILE" 2>/dev/null; then
        echo -e "${GREEN}✅ Connected to network!${NC}"
    else
        # Check if node is at least running
        if is_node_running; then
            echo -e "${YELLOW}⚠️  Node running, connection may still be establishing...${NC}"
        else
            echo -e "${RED}❌ Failed to start node${NC}"
            echo -e "${YELLOW}Log contents:${NC}"
            tail -10 "$LOG_FILE"
            return 1
        fi
    fi
    
    return 0
}

# ============================================================
# LIVE CHAT (Option 1)
# ============================================================

run_live_chat() {
    echo -e "\n${BOLD}${MAGENTA}💬 LIVE CHAT MODE${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}Type messages and press Enter to send.${NC}"
    echo -e "${YELLOW}Type 'quit' or Ctrl+C to exit.${NC}"
    echo ""
    
    # Determine role and get peer IP
    local is_server=false
    local peer_ip=""
    
    if [ -f "$PEER_FILE" ] && [ ! -f "$REMOTE_PEER_FILE" ]; then
        is_server=true
    elif [ -f "$REMOTE_PEER_FILE" ]; then
        # Extract IP from multiaddr
        peer_ip=$(grep -oP '/ip4/\K[0-9.]+' "$REMOTE_PEER_FILE" | head -1)
    fi
    
        # Convert bash bool to Python True/False
        if [ "$is_server" = true ]; then
            py_is_server=True
        else
            py_is_server=False
        fi

    # Call the chat Python script
    python3 "$PROJECT_ROOT/python/live_chat.py" "$py_is_server" "$peer_ip"
}

# ============================================================
# LIVE VOICE (Option 2)
# ============================================================

run_live_voice() {
    echo -e "\n${BOLD}${MAGENTA}🎤 LIVE VOICE MODE${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # Check for audio libraries
    python3 -c "import pyaudio" 2>/dev/null && HAS_PYAUDIO=true || HAS_PYAUDIO=false
    python3 -c "import sounddevice" 2>/dev/null && HAS_SOUNDDEVICE=true || HAS_SOUNDDEVICE=false
    
    if [ "$HAS_PYAUDIO" = false ] && [ "$HAS_SOUNDDEVICE" = false ]; then
        echo -e "${YELLOW}⚠️  No audio library found for live microphone.${NC}"
        echo -e "${CYAN}Install one of these for live microphone support:${NC}"
        echo -e "  ${GREEN}pip install sounddevice${NC}  (recommended)"
        echo -e "  ${GREEN}pip install pyaudio${NC}      (requires portaudio)"
        echo ""
        echo -e "${YELLOW}Running Opus codec demo instead...${NC}"
        echo ""
        
        # Run the Rust voice streaming demo
        cd "$PROJECT_ROOT/rust"
        cargo run --example voice_streaming_demo --release 2>&1 || {
            echo -e "${RED}Failed to run voice demo${NC}"
        }
        cd "$PROJECT_ROOT"
        return
    fi
    
    # Determine role and get peer IP
    local is_server=false
    local peer_ip=""
    
    if [ -f "$PEER_FILE" ] && [ ! -f "$REMOTE_PEER_FILE" ]; then
        is_server=true
    elif [ -f "$REMOTE_PEER_FILE" ]; then
        peer_ip=$(grep -oP '/ip4/\K[0-9.]+' "$REMOTE_PEER_FILE" | head -1)
    fi
    
    echo -e "${GREEN}🎤 Starting live voice streaming...${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop${NC}\n"
    
    # Convert bash bool to lowercase for Python (sh/zsh compatible)
    local is_server_lower=$([ "$is_server" = true ] && echo "true" || echo "false")
    
    # Call the voice Python script
    python3 "$PROJECT_ROOT/python/live_voice.py" "$is_server_lower" "$peer_ip"
}

# ============================================================
# LIVE VIDEO (Option 3)
# ============================================================

run_live_video() {
    echo -e "\n${BOLD}${MAGENTA}🎥 LIVE VIDEO MODE${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # Check for OpenCV
    python3 -c "import cv2" 2>/dev/null && HAS_CV2=true || HAS_CV2=false
    
    if [ "$HAS_CV2" = false ]; then
        echo -e "${YELLOW}⚠️  OpenCV not found.${NC}"
        echo -e "${CYAN}Install for live webcam support:${NC}"
        echo -e "  ${GREEN}pip install opencv-python${NC}"
        echo ""
        echo -e "${YELLOW}Running video compression demo instead...${NC}"
        echo ""
        
        # Run video compression test
        if [ -f "$PROJECT_ROOT/test_media/samples/test_video.mp4" ]; then
            cd "$PROJECT_ROOT/rust"
            cargo run --release --bin ces_test -- "../test_media/samples/test_video.mp4" 2>&1 | tail -10 || true
            cd "$PROJECT_ROOT"
        else
            echo -e "${YELLOW}Generating synthetic video frames...${NC}"
            python3 -c "
import numpy as np
frames = np.random.randint(0, 255, (100, 480, 640, 3), dtype=np.uint8)
print(f'Generated 100 frames, {frames.nbytes / 1024 / 1024:.1f} MB')
compressed_size = len(frames.tobytes()) // 15
print(f'Simulated compression: {frames.nbytes / compressed_size:.1f}x ratio')
print('✅ Video streaming simulation complete')
"
        fi
        return
    fi
    
    # Determine role and get peer IP
    local is_server=false
    local peer_ip=""
    
    if [ -f "$PEER_FILE" ] && [ ! -f "$REMOTE_PEER_FILE" ]; then
        is_server=true
    elif [ -f "$REMOTE_PEER_FILE" ]; then
        peer_ip=$(grep -oP '/ip4/\K[0-9.]+' "$REMOTE_PEER_FILE" | head -1)
    fi
    
    echo -e "${GREEN}🎥 Starting live video streaming...${NC}"
    echo -e "${YELLOW}Press 'q' in video window or Ctrl+C to stop${NC}\n"
    
    # Convert bash bool to lowercase for Python (sh/zsh compatible)
    local is_server_lower=$([ "$is_server" = true ] && echo "true" || echo "false")
    
    # Call the video Python script
    python3 "$PROJECT_ROOT/python/live_video.py" "$is_server_lower" "$peer_ip"
}

run_live_video_udp() {
    echo -e "\n${BOLD}${MAGENTA}🎥 LIVE VIDEO MODE (UDP - Low Latency)${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # Check for OpenCV
    python3 -c "import cv2" 2>/dev/null && HAS_CV2=true || HAS_CV2=false
    
    if [ "$HAS_CV2" = false ]; then
        echo -e "${YELLOW}⚠️  OpenCV not found.${NC}"
        echo -e "${CYAN}Install for live webcam support:${NC}"
        echo -e "  ${GREEN}pip install opencv-python${NC}"
        return
    fi
    
    # Determine role and get peer IP
    local is_server=false
    local peer_ip=""
    
    if [ -f "$PEER_FILE" ] && [ ! -f "$REMOTE_PEER_FILE" ]; then
        is_server=true
    elif [ -f "$REMOTE_PEER_FILE" ]; then
        peer_ip=$(grep -oP '/ip4/\K[0-9.]+' "$REMOTE_PEER_FILE" | head -1)
    fi
    
    echo -e "${GREEN}🎥 Starting UDP video streaming (low-latency, best effort)...${NC}"
    echo -e "${YELLOW}UDP trades reliability for speed - a few dropped frames is normal${NC}"
    echo -e "${YELLOW}Press 'q' in video window or Ctrl+C to stop${NC}\n"
    
    # Convert bash bool to lowercase for Python (sh/zsh compatible)
    local is_server_lower=$([ "$is_server" = true ] && echo "true" || echo "false")
    
    # Call the UDP video Python script
    python3 "$PROJECT_ROOT/python/live_video_udp.py" "$is_server_lower" "$peer_ip"
}

# ============================================================
# MAIN MENU
# ============================================================

show_header() {
    clear
    echo -e "${BOLD}${CYAN}"
    cat << "EOF"
╔═══════════════════════════════════════════════════════════════╗
║   🌍 PANGEA NET - LIVE STREAMING TEST                        ║
║   One script. Two devices. Select 1/2/3 and GO!              ║
╚═══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

show_test_menu() {
    echo -e "\n${BOLD}${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}${MAGENTA}  SELECT TEST MODE${NC}"
    echo -e "${BOLD}${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    
    echo -e "  ${GREEN}${BOLD}1${NC} - 💬 ${CYAN}Live Chat${NC}      (text messaging)"
    echo -e "  ${GREEN}${BOLD}2${NC} - 🎤 ${CYAN}Live Voice${NC}     (audio call)"
    echo -e "  ${GREEN}${BOLD}3${NC} - 🎥 ${CYAN}Live Video${NC}     (video call, TCP)"
    echo -e "  ${GREEN}${BOLD}4${NC} - 🎥 ${CYAN}Live Video UDP${NC}  (video call, low-latency)"
    echo -e ""
    echo -e "  ${YELLOW}Q${NC} - Quit"
    echo ""
}

# ============================================================
# MAIN SCRIPT
# ============================================================

main() {
    show_header
    
    # Build if needed
    build_if_needed
    
    # Check if node is already running
    if is_node_running; then
        echo -e "${GREEN}✅ Node already running${NC}"
        
        # Show existing peer info if available
        if [ -f "$PEER_FILE" ]; then
            echo -e "${CYAN}Peer address: $(cat $PEER_FILE)${NC}"
        fi
    else
        # Clean up old session files
        rm -f "$PEER_FILE" "$REMOTE_PEER_FILE" 2>/dev/null || true
        
        echo -e "\n${CYAN}${BOLD}Is this the FIRST device (bootstrap)?${NC}"
        echo -e "  ${GREEN}Y${NC} = Yes, start as first device (others will connect to me)"
        echo -e "  ${GREEN}N${NC} = No, connect to existing device"
        echo ""
        read -p "Choice [Y/n]: " IS_FIRST
        IS_FIRST=${IS_FIRST:-Y}
        
        if [[ "$IS_FIRST" =~ ^[Yy]$ ]]; then
            # Start as bootstrap
            start_bootstrap_node || {
                echo -e "${RED}Failed to start node. Check the logs at: $LOG_FILE${NC}"
                exit 1
            }
            
            echo -e "\n${YELLOW}Press ENTER when the other device is ready...${NC}"
            read
        else
            # Connect to existing network
            echo -e "\n${CYAN}Paste the peer address from the first device:${NC}"
            echo -e "${YELLOW}(the /ip4/... line)${NC}"
            echo ""
            read -p "Peer address: " BOOTSTRAP_PEER
            
            if [ -z "$BOOTSTRAP_PEER" ]; then
                echo -e "${RED}No peer address provided. Exiting.${NC}"
                exit 1
            fi
            
            start_joining_node "$BOOTSTRAP_PEER" || {
                echo -e "${RED}Failed to connect. Check the logs at: $LOG_FILE${NC}"
                exit 1
            }
        fi
    fi
    
    # Test loop
    while true; do
        show_test_menu
        
        read -p "Select test [1-4, Q]: " CHOICE
        
        case $CHOICE in
            1)
                run_live_chat
                ;;
            2)
                run_live_voice
                ;;
            3)
                run_live_video
                ;;
            4)
                run_live_video_udp
                ;;
            [Qq])
                echo -e "\n${CYAN}Stopping node...${NC}"
                cleanup
                echo -e "${GREEN}Goodbye!${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}Invalid choice. Please select 1, 2, 3, 4, or Q.${NC}"
                ;;
        esac
        
        echo ""
        echo -e "${YELLOW}Press ENTER to return to menu...${NC}"
        read
    done
}

# Run main
main "$@"
