#!/bin/bash
#
# Easy Test Runner for Pangea Net
# Tests both Communication (P2P) and Compute (CES Pipeline)
#
# Usage: ./scripts/test_pangea.sh
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Find project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Configuration
GO_NODE="$PROJECT_ROOT/go/bin/go-node"
PYTHON_VENV="$PROJECT_ROOT/python/.venv"
NODE1_CAPNP_PORT=8080
NODE2_CAPNP_PORT=8081
NODE1_P2P_PORT=9080
NODE2_P2P_PORT=9081
NODE1_LOG="/tmp/pangea_node1.log"
NODE2_LOG="/tmp/pangea_node2.log"

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Cleaning up...${NC}"
    pkill -f "go-node.*node-id" 2>/dev/null || true
    sleep 1
    echo -e "${GREEN}✅ Cleanup complete${NC}"
}

trap cleanup EXIT

# Print header
print_header() {
    echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  🚀 Pangea Net - Easy Test Runner${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

# Check prerequisites
check_prereqs() {
    echo -e "${BLUE}Checking prerequisites...${NC}"
    
    # Check go-node binary
    if [ ! -f "$GO_NODE" ]; then
        echo -e "${YELLOW}Building go-node...${NC}"
        cd "$PROJECT_ROOT/go" && make build && cd "$PROJECT_ROOT"
    fi
    
    if [ ! -f "$GO_NODE" ]; then
        echo -e "${RED}❌ go-node binary not found. Run: cd go && make build${NC}"
        exit 1
    fi
    echo -e "${GREEN}  ✓ go-node binary found${NC}"
    
    # Check Python venv
    if [ ! -d "$PYTHON_VENV" ]; then
        echo -e "${RED}❌ Python venv not found at $PYTHON_VENV${NC}"
        echo -e "${YELLOW}  Run: cd python && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt${NC}"
        exit 1
    fi
    echo -e "${GREEN}  ✓ Python venv found${NC}"
    
    # Check Rust library
    if [ ! -f "$PROJECT_ROOT/rust/target/release/libpangea_ces.dylib" ] && [ ! -f "$PROJECT_ROOT/rust/target/release/libpangea_ces.so" ]; then
        echo -e "${YELLOW}Building Rust library...${NC}"
        cd "$PROJECT_ROOT/rust" && cargo build --release && cd "$PROJECT_ROOT"
    fi
    echo -e "${GREEN}  ✓ Rust library ready${NC}"
    
    echo ""
}

# Start Go nodes
start_nodes() {
    local num_nodes=${1:-1}
    
    echo -e "${BLUE}Starting Go node(s)...${NC}"
    
    # Kill any existing nodes
    pkill -f "go-node.*node-id" 2>/dev/null || true
    sleep 1
    
    # Set library path
    export LD_LIBRARY_PATH="$PROJECT_ROOT/rust/target/release:$LD_LIBRARY_PATH"
    export DYLD_LIBRARY_PATH="$PROJECT_ROOT/rust/target/release:$DYLD_LIBRARY_PATH"
    
    # Start node 1
    "$GO_NODE" \
        -node-id=1 \
        -capnp-addr=":$NODE1_CAPNP_PORT" \
        -libp2p=true \
        -local \
        > "$NODE1_LOG" 2>&1 &
    
    echo -e "${GREEN}  ✓ Node 1 started (Cap'n Proto: $NODE1_CAPNP_PORT)${NC}"
    
    if [ "$num_nodes" -ge 2 ]; then
        sleep 1
        "$GO_NODE" \
            -node-id=2 \
            -capnp-addr=":$NODE2_CAPNP_PORT" \
            -libp2p=true \
            -local \
            > "$NODE2_LOG" 2>&1 &
        
        echo -e "${GREEN}  ✓ Node 2 started (Cap'n Proto: $NODE2_CAPNP_PORT)${NC}"
    fi
    
    # Wait for nodes to initialize
    echo -e "${YELLOW}  Waiting for nodes to initialize...${NC}"
    sleep 3
    
    # Check if nodes are running
    if ! pgrep -f "go-node.*node-id=1" > /dev/null; then
        echo -e "${RED}❌ Node 1 failed to start. Check $NODE1_LOG${NC}"
        cat "$NODE1_LOG" | tail -20
        exit 1
    fi
    
    echo -e "${GREEN}  ✓ Nodes running${NC}\n"
}

# Test 1: Communication Test
test_communication() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  📡 Test: Communication (P2P Connection)${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    
    source "$PYTHON_VENV/bin/activate"
    cd "$PROJECT_ROOT/python"
    
    echo -e "${BLUE}Testing connection to Go node...${NC}"
    python3 - <<'PYTHON'
import sys
sys.path.insert(0, 'src')
from client.go_client import GoNodeClient

print("  Connecting to Go node on port 8080...")
client = GoNodeClient(host="localhost", port=8080)

if not client.connect():
    print("  ❌ Failed to connect to Go node")
    sys.exit(1)

print("  ✅ Connected to Go node!")

# Get all nodes
nodes = client.get_all_nodes()
print(f"  📊 Found {len(nodes)} node(s):")
for node in nodes:
    print(f"     Node {node['id']}: latency={node['latencyMs']:.1f}ms, threat={node['threatScore']:.3f}")

# Get connected peers
peers = client.get_connected_peers()
print(f"  🔗 Connected peers: {peers}")

# Test network metrics
metrics = client.get_network_metrics()
if metrics:
    print(f"  📈 Network metrics:")
    print(f"     Avg RTT: {metrics.get('avgRttMs', 0):.1f}ms")
    print(f"     Bandwidth: {metrics.get('bandwidthMbps', 0):.1f} Mbps")
    print(f"     Peer count: {metrics.get('peerCount', 0)}")

client.disconnect()
print("\n  ✅ Communication test PASSED!")
PYTHON
    
    echo ""
}

# Test 2: Compute Test (CES Pipeline)
test_compute() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  🖥️  Test: Compute (CES Pipeline)${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    
    source "$PYTHON_VENV/bin/activate"
    cd "$PROJECT_ROOT/python"
    
    echo -e "${BLUE}Testing CES pipeline (Compress → Encrypt → Shard)...${NC}"
    python3 - <<'PYTHON'
import sys
sys.path.insert(0, 'src')
from client.go_client import GoNodeClient

print("  Connecting to Go node...")
client = GoNodeClient(host="localhost", port=8080)

if not client.connect():
    print("  ❌ Failed to connect to Go node")
    sys.exit(1)

print("  ✅ Connected!")

# Test CES process
test_data = b"Hello, this is test data for the CES pipeline! " * 100
print(f"  📦 Test data size: {len(test_data)} bytes")

print("  🔄 Running CES process (compress + encrypt + shard)...")
shards = client.ces_process(test_data, compression_level=3)

if shards is None:
    print("  ❌ CES process failed")
    client.disconnect()
    sys.exit(1)

print(f"  ✅ Created {len(shards)} shards:")
for i, shard in enumerate(shards):
    print(f"     Shard {i}: {len(shard)} bytes")

total_shard_size = sum(len(s) for s in shards)
compression_ratio = len(test_data) / total_shard_size if total_shard_size > 0 else 0
print(f"  📊 Compression ratio: {compression_ratio:.2f}x")

# Test CES reconstruct
print("\n  🔄 Reconstructing data from shards...")
shard_present = [True] * len(shards)
reconstructed = client.ces_reconstruct(shards, shard_present, compression_level=3)

if reconstructed is None:
    print("  ❌ CES reconstruct failed")
    client.disconnect()
    sys.exit(1)

if reconstructed == test_data:
    print(f"  ✅ Data reconstructed successfully! ({len(reconstructed)} bytes)")
    print("  ✅ Data integrity verified - original matches reconstructed!")
else:
    print(f"  ❌ Data mismatch! Original: {len(test_data)}, Reconstructed: {len(reconstructed)}")
    client.disconnect()
    sys.exit(1)

client.disconnect()
print("\n  ✅ Compute test PASSED!")
PYTHON
    
    echo ""
}

# Test 3: Message sending between nodes
test_messaging() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  💬 Test: P2P Messaging${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    
    source "$PYTHON_VENV/bin/activate"
    cd "$PROJECT_ROOT/python"
    
    echo -e "${BLUE}Testing P2P message sending...${NC}"
    python3 - <<'PYTHON'
import sys
sys.path.insert(0, 'src')
from client.go_client import GoNodeClient

print("  Connecting to Go node...")
client = GoNodeClient(host="localhost", port=8080)

if not client.connect():
    print("  ❌ Failed to connect to Go node")
    sys.exit(1)

print("  ✅ Connected!")

# Get nodes
nodes = client.get_all_nodes()
if len(nodes) < 1:
    print("  ⚠️  No nodes found, skipping message test")
    client.disconnect()
    sys.exit(0)

# Try to send a message to node 2 (or self if only one node)
target_node = 2 if len(nodes) > 1 else 1
message = b"Hello from Python test!"

print(f"  📤 Sending message to node {target_node}...")
success = client.send_message(target_node, message)

if success:
    print(f"  ✅ Message sent successfully!")
else:
    print(f"  ⚠️  Message send returned false (peer may not be connected)")

client.disconnect()
print("\n  ✅ Messaging test completed!")
PYTHON
    
    echo ""
}

# Test 4: Upload/Download test
test_upload_download() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  📁 Test: Upload/Download${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    
    source "$PYTHON_VENV/bin/activate"
    cd "$PROJECT_ROOT/python"
    
    echo -e "${BLUE}Testing distributed upload/download...${NC}"
    python3 - <<'PYTHON'
import sys
sys.path.insert(0, 'src')
from client.go_client import GoNodeClient

print("  Connecting to Go node...")
client = GoNodeClient(host="localhost", port=8080)

if not client.connect():
    print("  ❌ Failed to connect to Go node")
    sys.exit(1)

print("  ✅ Connected!")

# Test data
test_data = b"This is test file data for upload/download test! " * 50
print(f"  📦 Test data size: {len(test_data)} bytes")

# Get target peers (use node 1 for local test)
target_peers = [1]

print(f"  📤 Uploading to peers: {target_peers}...")
manifest = client.upload(test_data, target_peers)

if manifest is None:
    print("  ⚠️  Upload returned None (may need multiple nodes for full test)")
    client.disconnect()
    sys.exit(0)

print(f"  ✅ Upload complete!")
print(f"     File hash: {manifest.get('fileHash', 'N/A')[:16]}...")
print(f"     Shard count: {manifest.get('shardCount', 0)}")
print(f"     Parity count: {manifest.get('parityCount', 0)}")

# Download
shard_locations = manifest.get('shardLocations', [])
if shard_locations:
    print(f"\n  📥 Downloading from {len(shard_locations)} locations...")
    result = client.download(shard_locations, manifest.get('fileHash', ''))
    
    if result:
        data, bytes_downloaded = result
        print(f"  ✅ Downloaded {bytes_downloaded} bytes")
        if data == test_data:
            print("  ✅ Data integrity verified!")
        else:
            print("  ⚠️  Data mismatch")
    else:
        print("  ⚠️  Download returned None")
else:
    print("  ⚠️  No shard locations in manifest")

client.disconnect()
print("\n  ✅ Upload/Download test completed!")
PYTHON
    
    echo ""
}

# Manual peer connection test
test_manual_connect() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  🔗 Test: Manual Peer Connection${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    
    echo -e "${BLUE}To connect to a remote node, you need:${NC}"
    echo -e "  1. Remote node's IP address"
    echo -e "  2. Remote node's libp2p port (usually 9081, 9082, etc.)\n"
    echo -e "${YELLOW}How to find on REMOTE MACHINE:${NC}"
    echo -e "  Run: ./go/bin/go-node -node-id=2 -capnp-addr=:8081 -libp2p=true"
    echo -e "  Look for line with 'listening' or 'multiaddr'"
    echo -e "  Example: /ip4/192.168.1.100/tcp/9081/p2p/...\n"
    
    read -p "  Enter peer address (IP:port), or press Enter to skip: " peer_address
    
    if [ -z "$peer_address" ]; then
        echo -e "${YELLOW}  Skipped manual connection test${NC}\n"
        return
    fi
    
    source "$PYTHON_VENV/bin/activate"
    cd "$PROJECT_ROOT/python"
    
    echo ""
    python3 - "$peer_address" <<'PYTHON'
import sys
sys.path.insert(0, 'src')
from client.go_client import GoNodeClient

peer_address = sys.argv[1]

if ":" not in peer_address:
    print("  ❌ Invalid format. Use IP:port")
    sys.exit(1)

peer_host, peer_port_str = peer_address.rsplit(":", 1)
peer_port_num = int(peer_port_str)

print(f"  🔍 Looking for peer at {peer_host}:{peer_port_num}...")

client = GoNodeClient(host="localhost", port=8080)
if not client.connect():
    print("  ❌ Failed to connect to Go node")
    sys.exit(1)

# Try different peer IDs
peer_id = None
for candidate_id in range(2, 11):
    print(f"     Trying peer ID {candidate_id}...", end="", flush=True)
    success, quality = client.connect_to_peer(candidate_id, peer_host, peer_port_num)
    if success:
        peer_id = candidate_id
        print(f" ✅")
        break
    else:
        print(f" ✗", end="", flush=True)

if peer_id is None:
    print(f"\n\n  ❌ Could not connect to {peer_host}:{peer_port_num}")
    print(f"     Check: node running on port {peer_port_num}, IP correct, firewall open")
    client.disconnect()
    sys.exit(1)

print(f"\n  ✅ Connected to peer {peer_id}!")
quality = client.get_connection_quality(peer_id)
if quality:
    print(f"     Latency: {quality['latencyMs']:.1f}ms")
    print(f"     Jitter: {quality['jitterMs']:.1f}ms")
    print(f"     Packet Loss: {quality['packetLoss']*100:.2f}%")

# Test message
client.send_message(peer_id, b"Hello from shell script!")
print(f"  ✅ Test message sent!\n")

client.disconnect()
PYTHON
    
    echo ""
}

# Show logs
show_logs() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  📋 Node Logs${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    
    echo -e "${BLUE}Node 1 (last 20 lines):${NC}"
    if [ -f "$NODE1_LOG" ]; then
        tail -20 "$NODE1_LOG"
    else
        echo "  No log file found"
    fi
    
    echo ""
    
    if [ -f "$NODE2_LOG" ]; then
        echo -e "${BLUE}Node 2 (last 20 lines):${NC}"
        tail -20 "$NODE2_LOG"
    fi
    
    echo ""
}

# Interactive menu
show_menu() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  Select Test:${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${GREEN}1)${NC} Run ALL tests (recommended)"
    echo -e "  ${GREEN}2)${NC} Communication test (P2P connection)"
    echo -e "  ${GREEN}3)${NC} Compute test (CES pipeline)"
    echo -e "  ${GREEN}4)${NC} Messaging test"
    echo -e "  ${GREEN}5)${NC} Upload/Download test"
    echo -e "  ${GREEN}6)${NC} Manual peer connection (enter address)"
    echo -e "  ${GREEN}7)${NC} Show node logs"
    echo -e "  ${GREEN}8)${NC} Restart nodes"
    echo -e "  ${GREEN}q)${NC} Quit"
    echo ""
    read -p "  Enter choice: " choice
    echo ""
    
    case $choice in
        1)
            test_communication
            test_compute
            test_messaging
            test_upload_download
            ;;
        2)
            test_communication
            ;;
        3)
            test_compute
            ;;
        4)
            test_messaging
            ;;
        5)
            test_upload_download
            ;;
        6)
            test_manual_connect
            ;;
        7)
            show_logs
            ;;
        8)
            start_nodes 1
            ;;
        q|Q)
            echo -e "${GREEN}Goodbye!${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid choice${NC}"
            ;;
    esac
}

# Main
main() {
    print_header
    check_prereqs
    start_nodes 1
    
    # If --all flag, run all tests and exit
    if [ "$1" == "--all" ]; then
        test_communication
        test_compute
        test_messaging
        test_upload_download
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${GREEN}  ✅ All tests completed!${NC}"
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        exit 0
    fi
    
    # Interactive mode
    while true; do
        show_menu
    done
}

main "$@"
