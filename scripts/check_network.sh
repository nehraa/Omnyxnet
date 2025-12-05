#!/bin/bash
# =============================================================================
# Network Health Check - Check and manage network connections
# =============================================================================
# This script provides utilities to check network health and manage peers.
#
# Usage:
#   ./check_network.sh --list          # List all connected peers
#   ./check_network.sh --status        # Show network status summary
#   ./check_network.sh --get-peer ID   # Get peer multiaddr by ID
#   ./check_network.sh --clear         # Clear registry (fresh start)
#   ./check_network.sh --test          # Test connection to peers
#
# =============================================================================

set -e

# Get the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Source the network registry module
source "$SCRIPT_DIR/network_registry.sh"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# =============================================================================
# Helper Functions
# =============================================================================

show_help() {
    echo ""
    echo -e "${CYAN}WGT Network Health Check${NC}"
    echo "========================="
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --list, -l         List all connected peers with details"
    echo "  --status, -s       Show network status summary"
    echo "  --get-peer ID      Get multiaddr for a specific peer ID"
    echo "  --clear            Clear network registry (fresh start)"
    echo "  --test, -t         Test connectivity to all peers"
    echo "  --registry, -r     Show raw registry file"
    echo "  --help, -h         Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --list"
    echo "  $0 --status"
    echo "  $0 --get-peer Qm123..."
    echo "  $0 --clear"
    echo ""
}

show_status() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}   Network Status Summary${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    
    # Check registry exists
    if [ ! -f "${NETWORK_REGISTRY}" ]; then
        echo -e "   ${YELLOW}⚠️  No network registry found${NC}"
        echo ""
        echo "   Run './setup.sh' → Option 2: Establish Network Connection"
        echo ""
        return 1
    fi
    
    # Get status from Python
    python3 << 'EOF'
import json
import os
from datetime import datetime

registry_file = os.path.expanduser("~/.wgt/network.json")

try:
    with open(registry_file, 'r') as f:
        registry = json.load(f)
    
    # Local node
    local_node = registry.get("local_node")
    if local_node:
        mode = local_node.get("mode", "unknown").upper()
        status = local_node.get("status", "unknown")
        port = local_node.get("capnp_port", "?")
        
        status_icon = "🟢" if status == "running" else "🔴"
        print(f"   {status_icon} Local Node: {mode} on port {port}")
    else:
        print("   ⚪ Local Node: Not started")
    
    # Peers
    peers = registry.get("peers", [])
    connected = [p for p in peers if p.get("status") == "connected"]
    disconnected = [p for p in peers if p.get("status") != "connected"]
    
    print(f"\n   📊 Peers:")
    print(f"      Connected:    {len(connected)}")
    print(f"      Disconnected: {len(disconnected)}")
    print(f"      Total:        {len(peers)}")
    
    # Last update
    updated = registry.get("updated_at", "unknown")
    if updated != "unknown":
        try:
            dt = datetime.fromisoformat(updated.replace('Z', '+00:00'))
            updated = dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            pass
    print(f"\n   📅 Last Updated: {updated}")
    
    # Overall status
    if len(connected) > 0:
        print(f"\n   ✅ Network Status: CONNECTED")
    elif len(peers) > 0:
        print(f"\n   ⚠️  Network Status: PEERS KNOWN (not connected)")
    else:
        print(f"\n   ❌ Network Status: NO PEERS")
        print(f"      Run './setup.sh' → Option 2")
    
except FileNotFoundError:
    print("   ❌ Registry file not found")
except Exception as e:
    print(f"   ❌ Error: {e}")

print()
EOF
}

test_connectivity() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}   Testing Peer Connectivity${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    
    if [ ! -f "${NETWORK_REGISTRY}" ]; then
        echo -e "   ${RED}No network registry found${NC}"
        return 1
    fi
    
    python3 << 'EOF'
import json
import os
import socket
import re

registry_file = os.path.expanduser("~/.wgt/network.json")

def test_connection(host, port, timeout=2):
    """Test TCP connection to host:port"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, int(port)))
        sock.close()
        return result == 0
    except:
        return False

def extract_host_port(multiaddr):
    """Extract host and port from multiaddr"""
    match = re.search(r'/ip4/([^/]+)/tcp/(\d+)', multiaddr)
    if match:
        return match.group(1), int(match.group(2))
    return None, None

try:
    with open(registry_file, 'r') as f:
        registry = json.load(f)
    
    peers = registry.get("peers", [])
    
    if not peers:
        print("   No peers in registry")
        exit(0)
    
    print(f"   Testing {len(peers)} peer(s)...")
    print()
    
    for i, peer in enumerate(peers, 1):
        node_id = peer.get("node_id", "unknown")
        multiaddr = peer.get("multiaddr", "")
        status = peer.get("status", "unknown")
        
        # Truncate long IDs
        if len(node_id) > 20:
            node_id = node_id[:20] + "..."
        
        host, port = extract_host_port(multiaddr)
        
        if host and port:
            reachable = test_connection(host, port)
            if reachable:
                print(f"   {i}. {node_id}")
                print(f"      ✅ {host}:{port} - REACHABLE")
            else:
                print(f"   {i}. {node_id}")
                print(f"      ❌ {host}:{port} - NOT REACHABLE")
        else:
            print(f"   {i}. {node_id}")
            print(f"      ⚠️  Could not parse address")
        print()
    
except Exception as e:
    print(f"   Error: {e}")
EOF
}

get_peer() {
    local peer_id="$1"
    
    if [ -z "$peer_id" ]; then
        echo "Error: Peer ID required"
        echo "Usage: $0 --get-peer <peer_id>"
        exit 1
    fi
    
    local result=$(get_peer_by_id "$peer_id")
    
    if [ -z "$result" ]; then
        # Try partial match
        python3 << EOF
import json
import os

registry_file = os.path.expanduser("~/.wgt/network.json")
search_id = "${peer_id}"

try:
    with open(registry_file, 'r') as f:
        registry = json.load(f)
    
    for peer in registry.get("peers", []):
        if search_id in peer.get("node_id", ""):
            print(peer.get("multiaddr", ""))
            exit(0)
    
    print("")
except:
    print("")
EOF
    else
        echo "$result" | python3 -c "import json, sys; d = json.load(sys.stdin); print(d.get('multiaddr', ''))"
    fi
}

# =============================================================================
# Main
# =============================================================================

main() {
    case "${1:-}" in
        --list|-l)
            list_peers
            ;;
        --status|-s)
            show_status
            ;;
        --get-peer)
            get_peer "$2"
            ;;
        --clear)
            echo ""
            echo -e "${YELLOW}⚠️  This will clear all peer information!${NC}"
            read -p "Are you sure? (y/N) " confirm
            if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
                clear_registry
                echo -e "${GREEN}✅ Registry cleared${NC}"
            else
                echo "Cancelled"
            fi
            ;;
        --test|-t)
            test_connectivity
            ;;
        --registry|-r)
            show_registry
            ;;
        --help|-h|"")
            show_help
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
