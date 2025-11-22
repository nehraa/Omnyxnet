#!/bin/bash
# Test upload/download across devices
#
# IMPORTANT: For cross-device testing, use -peers flag with bootstrap multiaddr
# mDNS discovery is for local network only - cross-device requires manual peer exchange
#
# Usage:
#   Device 1: ./test_upload_download_cross_device.sh 1
#   Device 2: ./test_upload_download_cross_device.sh 2
#
# Connection Status: ✅ IP/PeerID connection working reliably
# mDNS Status: Not applicable for cross-device (local network only)

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "${CYAN}╔════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  Upload/Download Cross-Device Test    ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════╝${NC}"
echo ""

# Check if this is device 1 or device 2
if [ "$#" -eq 0 ]; then
    echo -e "${CYAN}Select device role:${NC}"
    echo "  1. Device 1 (Bootstrap node + uploader)"
    echo "  2. Device 2 (Join network + downloader)"
    echo ""
    read -p "Enter choice (1 or 2): " DEVICE_ROLE
else
    DEVICE_ROLE=$1
fi

# Common setup
TEST_FILE="/tmp/pangea_test_file.txt"

if [ "$DEVICE_ROLE" == "1" ]; then
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo -e "${BLUE}Device 1: Bootstrap Node + Upload${NC}"
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo ""
    
    # Create test file
    echo -e "${GREEN}Creating test file...${NC}"
    echo "Pangea Net Cross-Device Test File" > "$TEST_FILE"
    echo "Created on Device 1 at $(date)" >> "$TEST_FILE"
    echo "Lorem ipsum dolor sit amet, consectetur adipiscing elit." >> "$TEST_FILE"
    for i in {1..10}; do
        echo "Line $i: The quick brown fox jumps over the lazy dog $i" >> "$TEST_FILE"
    done
    
    FILE_SIZE=$(wc -c < "$TEST_FILE")
    FILE_HASH=$(sha256sum "$TEST_FILE" | awk '{print $1}')
    echo -e "${GREEN}✓ Test file created${NC}"
    echo -e "  Path: $TEST_FILE"
    echo -e "  Size: $FILE_SIZE bytes"
    echo -e "  Hash: $FILE_HASH"
    echo ""
    
    # Start bootstrap node
    echo -e "${GREEN}Starting bootstrap node...${NC}"
    echo -e "${YELLOW}Press Ctrl+C when you see the connection info, then:${NC}"
    echo -e "  1. Copy the multiaddr (IP/port/peerID)"
    echo -e "  2. Run this script on Device 2"
    echo -e "  3. Paste the multiaddr when prompted"
    echo ""
    
    ./scripts/easy_test.sh
    
elif [ "$DEVICE_ROLE" == "2" ]; then
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo -e "${BLUE}Device 2: Join Network + Download${NC}"
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo ""
    
    echo -e "${CYAN}From Device 1 output, enter connection details:${NC}"
    echo ""
    read -p "Bootstrap IP: " BOOTSTRAP_IP
    read -p "Bootstrap Port: " BOOTSTRAP_PORT
    read -p "Bootstrap Peer ID: " PEER_ID
    
    BOOTSTRAP="/ip4/${BOOTSTRAP_IP}/tcp/${BOOTSTRAP_PORT}/p2p/${PEER_ID}"
    
    echo ""
    echo -e "${GREEN}✓ Will connect to: $BOOTSTRAP${NC}"
    echo ""
    
    echo -e "${GREEN}Starting node and connecting...${NC}"
    ./scripts/easy_test.sh 2 "$BOOTSTRAP"
    
    echo ""
    echo -e "${YELLOW}═══════════════════════════════════════${NC}"
    echo -e "${YELLOW}Next Steps (Manual):${NC}"
    echo -e "${YELLOW}═══════════════════════════════════════${NC}"
    echo ""
    echo "Once connected, you can test download:"
    echo ""
    echo "1. On Device 1: Upload the file"
    echo "   ${CYAN}pangea upload $TEST_FILE${NC}"
    echo "   (Copy the file hash from output)"
    echo ""
    echo "2. On Device 2: Download using the hash"
    echo "   ${CYAN}pangea download <file_hash>${NC}"
    echo ""
    echo "3. Verify the downloaded file:"
    echo "   ${CYAN}sha256sum /tmp/pangea_downloaded_file.txt${NC}"
    echo "   Should match Device 1's hash"
    echo ""
    
else
    echo -e "${RED}Invalid choice. Use 1 or 2.${NC}"
    exit 1
fi
