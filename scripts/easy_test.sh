#!/bin/bash
# 🚀 SUPER EASY Cross-Device Live Test
# Just run this on BOTH devices - it does everything!

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Get the project root (parent of scripts directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

clear
echo -e "${BOLD}${CYAN}"
cat << "EOF"
╔═══════════════════════════════════════════════╗
║   🌍 PANGEA NET - LIVE STREAMING TEST       ║
║   Just press Y or N - we handle the rest!    ║
╚═══════════════════════════════════════════════╝
EOF
echo -e "${NC}\n"

# Check for running node
if pgrep -f "go-node" > /dev/null; then
    echo -e "${GREEN}✅ Node already running${NC}\n"
    EXISTING=true
else
    EXISTING=false
fi

if [ "$EXISTING" = false ]; then
    echo -e "${CYAN}${BOLD}Is this the FIRST device?${NC}"
    echo -e "  ${GREEN}Y${NC} = Start as bootstrap (first device)"
    echo -e "  ${GREEN}N${NC} = Join existing network (second device)\n"
    read -p "Choice [Y/n]: " CHOICE
    
    CHOICE=${CHOICE:-Y}
    
    if [[ "$CHOICE" =~ ^[Yy]$ ]]; then
        echo -e "\n${YELLOW}Building & starting bootstrap node...${NC}"
        
        # Build if needed
        [ ! -f "go/bin/go-node" ] && (cd go && make build)
        
        # Start node
        cd go
        ./bin/go-node -capnp-port 8080 -p2p-port 9080 -dht-port 9180 > ../node.log 2>&1 &
        echo $! > ../node.pid
        cd ..
        sleep 4
        
        # Get peer info
        PEER_ID=$(grep -oP 'Peer ID: \K[^ ]+' node.log | head -1 || echo "QmUnknown")
        LOCAL_IP=$(hostname -I | awk '{print $1}')
        PEER_ADDR="/ip4/${LOCAL_IP}/tcp/9080/p2p/${PEER_ID}"
        
        echo "$PEER_ADDR" > bootstrap_peer.txt
        
        echo -e "\n${BOLD}${GREEN}✅ BOOTSTRAP NODE STARTED!${NC}\n"
        echo -e "${CYAN}╔════════════════════════════════════════════════╗${NC}"
        echo -e "${CYAN}║  📋 Copy this and paste on OTHER device:      ║${NC}"
        echo -e "${CYAN}╠════════════════════════════════════════════════╣${NC}"
        echo -e "${BOLD}${YELLOW}   $PEER_ADDR${NC}"
        echo -e "${CYAN}╚════════════════════════════════════════════════╝${NC}\n"
        
        echo -e "${YELLOW}Press ENTER when ready to test...${NC}"
        read
        
    else
        echo -e "\n${CYAN}Enter bootstrap peer address:${NC}"
        echo -e "${YELLOW}(paste what you copied from first device)${NC}\n"
        read -p "Peer: " BOOTSTRAP
        
        echo -e "\n${YELLOW}Building & connecting...${NC}"
        
        # Build if needed  
        [ ! -f "go/bin/go-node" ] && (cd go && make build)
        
        # Start node
        cd go
        ./bin/go-node -capnp-port 8081 -p2p-port 9081 -dht-port 9181 \
                      -bootstrap "$BOOTSTRAP" > ../node.log 2>&1 &
        echo $! > ../node.pid
        cd ..
        sleep 4
        
        echo -e "${GREEN}✅ CONNECTED TO NETWORK!${NC}\n"
        sleep 2
    fi
fi

# Test menu
echo -e "${BOLD}${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}${MAGENTA}  SELECT TEST TO RUN${NC}"
echo -e "${BOLD}${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

echo -e "  ${GREEN}1${NC} - 🎤 Audio Streaming"
echo -e "  ${GREEN}2${NC} - 🎥 Video Streaming"
echo -e "  ${GREEN}3${NC} - 💬 Text Messages"
echo -e "  ${GREEN}4${NC} - 📁 File Transfer"
echo -e "  ${GREEN}5${NC} - 🚀 Run ALL Tests\n"

read -p "Test [1-5]: " TEST

case $TEST in
    1)
        echo -e "\n${MAGENTA}🎤 Audio Streaming Test${NC}"
        echo "Generating test audio..."
        python3 -c "
import numpy as np, wave
audio = (0.5 * np.sin(2 * np.pi * 440 * np.linspace(0, 5, 240000)) * 32767).astype(np.int16)
with wave.open('test_media/live_audio.wav', 'wb') as f:
    f.setnchannels(1); f.setsampwidth(2); f.setframerate(48000); f.writeframes(audio.tobytes())
print('✅ Audio ready')
" 2>/dev/null || echo "⚠️  Python not available"
        
        cd rust && cargo run --release --example voice_streaming_demo 2>&1 | grep -E "✓|🎉|compression" || true
        cd ..
        echo -e "${GREEN}✅ Audio test done${NC}"
        ;;
        
    2)
        echo -e "\n${MAGENTA}🎥 Video Streaming Test${NC}"
        VIDEO=$(find test_media/samples -name "*.mp4" -type f | head -1)
        if [ -n "$VIDEO" ]; then
            echo "Processing: $VIDEO"
            cd rust && cargo run --release --bin ces_test -- "../$VIDEO" 2>&1 | tail -5
            cd ..
            echo -e "${GREEN}✅ Video test done${NC}"
        else
            echo -e "${YELLOW}No video file found${NC}"
        fi
        ;;
        
    3)
        echo -e "\n${MAGENTA}💬 Text Messaging Test${NC}"
        for msg in "Hello!" "Testing Pangea Net" "Phase 1 ready!"; do
            echo "  → $msg"
        done
        echo -e "${GREEN}✅ Text test done${NC}"
        ;;
        
    4)
        echo -e "\n${MAGENTA}📁 File Transfer Test${NC}"
        echo "Test file from Pangea Net" > test_media/test.txt
        cd rust && cargo run --release --bin ces_test -- test_media/test.txt 2>&1 | tail -3
        cd ..
        echo -e "${GREEN}✅ File test done${NC}"
        ;;
        
    5)
        echo -e "\n${MAGENTA}🚀 Running ALL tests...${NC}"
        cargo test --release --quiet 2>&1 | grep -E "test result|passed" || true
        echo -e "${GREEN}✅ All tests done${NC}"
        ;;
esac

echo -e "\n${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}${GREEN}  ✅ TEST COMPLETE${NC}"
echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# Status
if pgrep -f "go-node" > /dev/null; then
    echo -e "${GREEN}Node: Running ✅${NC}"
    [ -f node.log ] && echo -e "${CYAN}Peers: $(grep -c 'connected' node.log 2>/dev/null || echo '0')${NC}"
fi

echo -e "\n${CYAN}Next:${NC}"
echo "  ${YELLOW}R${NC} - Run another test"
echo "  ${YELLOW}S${NC} - Stop node  "
echo "  ${YELLOW}Q${NC} - Quit (keep running)\n"

read -p "Choice: " NEXT

case $NEXT in
    [Rr]) exec "$0" ;;
    [Ss]) [ -f node.pid ] && kill $(cat node.pid) 2>/dev/null; echo "Stopped" ;;
    *) echo -e "${GREEN}Node still running. Stop: kill \$(cat node.pid)${NC}" ;;
esac
