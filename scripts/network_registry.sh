#!/bin/bash
# =============================================================================
# Network Registry - Peer Connection Storage and Management
# =============================================================================
# This module provides functions for managing peer connections in the WGT
# distributed network. It stores peer information in ~/.wgt/network.json
# for automatic peer discovery in tests and CLI commands.
#
# Usage:
#   source scripts/network_registry.sh
#   init_registry
#   save_peer "peer_id" "/ip4/192.168.1.100/tcp/9081/p2p/QmXYZ..."
#   get_peers
#
# =============================================================================

# Registry file location
WGT_HOME="${HOME}/.wgt"
NETWORK_REGISTRY="${WGT_HOME}/network.json"
NETWORK_LOG="${WGT_HOME}/logs/network.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# =============================================================================
# Logging Functions
# =============================================================================

network_log() {
    local msg="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    mkdir -p "${WGT_HOME}/logs"
    echo "[${timestamp}] ${msg}" >> "${NETWORK_LOG}"
}

network_log_info() {
    local msg="$1"
    echo -e "${BLUE}[INFO]${NC} ${msg}"
    network_log "INFO: ${msg}"
}

network_log_success() {
    local msg="$1"
    echo -e "${GREEN}[SUCCESS]${NC} ${msg}"
    network_log "SUCCESS: ${msg}"
}

network_log_error() {
    local msg="$1"
    echo -e "${RED}[ERROR]${NC} ${msg}"
    network_log "ERROR: ${msg}"
}

network_log_warning() {
    local msg="$1"
    echo -e "${YELLOW}[WARNING]${NC} ${msg}"
    network_log "WARNING: ${msg}"
}

# =============================================================================
# Registry Initialization
# =============================================================================

init_registry() {
    # Create WGT home directory structure
    mkdir -p "${WGT_HOME}"
    mkdir -p "${WGT_HOME}/logs"
    
    # Create registry file if it doesn't exist
    if [ ! -f "${NETWORK_REGISTRY}" ]; then
        echo '{
  "version": "1.0.0",
  "created_at": "'$(date -Iseconds)'",
  "updated_at": "'$(date -Iseconds)'",
  "local_node": null,
  "peers": []
}' > "${NETWORK_REGISTRY}"
        network_log "Initialized new network registry at ${NETWORK_REGISTRY}"
    fi
    
    return 0
}

# =============================================================================
# Local Node Management
# =============================================================================

save_local_node() {
    # Save information about the local node
    # Args: node_id, multiaddr, capnp_port, mode (manager/worker)
    local node_id="$1"
    local multiaddr="$2"
    local capnp_port="${3:-8080}"
    local mode="${4:-manager}"
    
    init_registry
    
    local timestamp=$(date -Iseconds)
    
    # Use Python for JSON manipulation (more reliable than jq)
    python3 << EOF
import json

try:
    with open("${NETWORK_REGISTRY}", 'r') as f:
        registry = json.load(f)
except (FileNotFoundError, json.JSONDecodeError, IOError):
    registry = {"version": "1.0.0", "created_at": "${timestamp}", "peers": []}

registry["updated_at"] = "${timestamp}"
registry["local_node"] = {
    "node_id": "${node_id}",
    "multiaddr": "${multiaddr}",
    "capnp_port": int("${capnp_port}"),
    "mode": "${mode}",
    "started_at": "${timestamp}",
    "status": "running"
}

with open("${NETWORK_REGISTRY}", 'w') as f:
    json.dump(registry, f, indent=2)

print("Local node saved successfully")
EOF
    
    network_log "Saved local node: ${node_id} (${mode}) on port ${capnp_port}"
    return 0
}

get_local_node() {
    # Get local node information
    # Returns: JSON object or empty string
    if [ ! -f "${NETWORK_REGISTRY}" ]; then
        echo ""
        return 1
    fi
    
    python3 << EOF
import json
try:
    with open("${NETWORK_REGISTRY}", 'r') as f:
        registry = json.load(f)
    if registry.get("local_node"):
        print(json.dumps(registry["local_node"]))
    else:
        print("")
except Exception:
    print("")
EOF
}

# =============================================================================
# Peer Management
# =============================================================================

save_peer() {
    # Save a peer connection to the registry
    # Args: node_id, multiaddr, [capnp_port], [status]
    local node_id="$1"
    local multiaddr="$2"
    local capnp_port="${3:-8080}"
    local status="${4:-connected}"
    
    init_registry
    
    local timestamp=$(date -Iseconds)
    
    python3 << EOF
import json

try:
    with open("${NETWORK_REGISTRY}", 'r') as f:
        registry = json.load(f)
except Exception:
    registry = {"version": "1.0.0", "created_at": "${timestamp}", "peers": [], "local_node": None}

registry["updated_at"] = "${timestamp}"

# Check if peer already exists
peer_exists = False
for i, peer in enumerate(registry.get("peers", [])):
    if peer.get("node_id") == "${node_id}" or peer.get("multiaddr") == "${multiaddr}":
        # Update existing peer
        registry["peers"][i] = {
            "node_id": "${node_id}",
            "multiaddr": "${multiaddr}",
            "capnp_port": int("${capnp_port}"),
            "status": "${status}",
            "connected_at": "${timestamp}",
            "last_seen": "${timestamp}"
        }
        peer_exists = True
        break

if not peer_exists:
    # Add new peer
    if "peers" not in registry:
        registry["peers"] = []
    registry["peers"].append({
        "node_id": "${node_id}",
        "multiaddr": "${multiaddr}",
        "capnp_port": int("${capnp_port}"),
        "status": "${status}",
        "connected_at": "${timestamp}",
        "last_seen": "${timestamp}"
    })

with open("${NETWORK_REGISTRY}", 'w') as f:
    json.dump(registry, f, indent=2)

print("Peer saved successfully")
EOF
    
    network_log "Saved peer: ${node_id} at ${multiaddr}"
    return 0
}

get_peers() {
    # Get all peers from the registry
    # Returns: JSON array of peers
    if [ ! -f "${NETWORK_REGISTRY}" ]; then
        echo "[]"
        return 1
    fi
    
    python3 << EOF
import json
try:
    with open("${NETWORK_REGISTRY}", 'r') as f:
        registry = json.load(f)
    peers = registry.get("peers", [])
    print(json.dumps(peers))
except Exception:
    print("[]")
EOF
}

get_peer_by_id() {
    # Get a specific peer by node ID
    # Args: node_id
    # Returns: JSON object or empty string
    local node_id="$1"
    
    if [ ! -f "${NETWORK_REGISTRY}" ]; then
        echo ""
        return 1
    fi
    
    python3 << EOF
import json
try:
    with open("${NETWORK_REGISTRY}", 'r') as f:
        registry = json.load(f)
    for peer in registry.get("peers", []):
        if peer.get("node_id") == "${node_id}":
            print(json.dumps(peer))
            break
    else:
        print("")
except Exception:
    print("")
EOF
}

get_first_peer() {
    # Get the first peer from the registry (for quick access)
    # Returns: multiaddr string or empty
    if [ ! -f "${NETWORK_REGISTRY}" ]; then
        echo ""
        return 1
    fi
    
    python3 << EOF
import json
try:
    with open("${NETWORK_REGISTRY}", 'r') as f:
        registry = json.load(f)
    peers = registry.get("peers", [])
    if peers:
        print(peers[0].get("multiaddr", ""))
    else:
        print("")
except Exception:
    print("")
EOF
}

list_peers() {
    # List all peers in a human-readable format
    if [ ! -f "${NETWORK_REGISTRY}" ]; then
        echo "No network registry found. Run network connection first."
        return 1
    fi
    
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}   Connected Peers${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    
    python3 << EOF
import json
try:
    with open("${NETWORK_REGISTRY}", 'r') as f:
        registry = json.load(f)
    
    local_node = registry.get("local_node")
    if local_node:
        print(f"   Local Node ({local_node.get('mode', 'unknown').upper()}):")
        print(f"     ID:   {local_node.get('node_id', 'unknown')[:20]}...")
        print(f"     Port: {local_node.get('capnp_port', 'unknown')}")
        print(f"     Status: {local_node.get('status', 'unknown')}")
        print()
    
    peers = registry.get("peers", [])
    if not peers:
        print("   No connected peers.")
        print()
        print("   Run 'setup.sh' → Option 2: Establish Network Connection")
    else:
        for i, peer in enumerate(peers, 1):
            print(f"   Peer {i}:")
            node_id = peer.get('node_id', 'unknown')
            if len(node_id) > 20:
                node_id = node_id[:20] + "..."
            print(f"     ID:     {node_id}")
            print(f"     Addr:   {peer.get('multiaddr', 'unknown')[:50]}...")
            print(f"     Port:   {peer.get('capnp_port', 'unknown')}")
            print(f"     Status: {peer.get('status', 'unknown')}")
            print()
except Exception as e:
    print(f"   Error reading registry: {e}")
EOF
    
    return 0
}

is_connected() {
    # Check if we have any connected peers
    # Returns: 0 if connected, 1 if not
    if [ ! -f "${NETWORK_REGISTRY}" ]; then
        return 1
    fi
    
    local peer_count=$(python3 << EOF
import json
try:
    with open("${NETWORK_REGISTRY}", 'r') as f:
        registry = json.load(f)
    peers = [p for p in registry.get("peers", []) if p.get("status") == "connected"]
    print(len(peers))
except Exception:
    print("0")
EOF
)
    
    if [ "$peer_count" -gt 0 ]; then
        return 0
    else
        return 1
    fi
}

update_peer_status() {
    # Update the status of a peer
    # Args: node_id, new_status
    local node_id="$1"
    local new_status="$2"
    
    if [ ! -f "${NETWORK_REGISTRY}" ]; then
        return 1
    fi
    
    local timestamp=$(date -Iseconds)
    
    python3 << EOF
import json
try:
    with open("${NETWORK_REGISTRY}", 'r') as f:
        registry = json.load(f)
    
    registry["updated_at"] = "${timestamp}"
    
    for peer in registry.get("peers", []):
        if peer.get("node_id") == "${node_id}":
            peer["status"] = "${new_status}"
            peer["last_seen"] = "${timestamp}"
            break
    
    with open("${NETWORK_REGISTRY}", 'w') as f:
        json.dump(registry, f, indent=2)
    
    print("Status updated")
except Exception as e:
    print(f"Error: {e}")
EOF
    
    network_log "Updated peer ${node_id} status to ${new_status}"
    return 0
}

remove_peer() {
    # Remove a peer from the registry
    # Args: node_id
    local node_id="$1"
    
    if [ ! -f "${NETWORK_REGISTRY}" ]; then
        return 1
    fi
    
    local timestamp=$(date -Iseconds)
    
    python3 << EOF
import json
try:
    with open("${NETWORK_REGISTRY}", 'r') as f:
        registry = json.load(f)
    
    registry["updated_at"] = "${timestamp}"
    registry["peers"] = [p for p in registry.get("peers", []) if p.get("node_id") != "${node_id}"]
    
    with open("${NETWORK_REGISTRY}", 'w') as f:
        json.dump(registry, f, indent=2)
    
    print("Peer removed")
except Exception as e:
    print(f"Error: {e}")
EOF
    
    network_log "Removed peer ${node_id}"
    return 0
}

clear_registry() {
    # Clear all peers from the registry (fresh start)
    local timestamp=$(date -Iseconds)
    
    echo '{
  "version": "1.0.0",
  "created_at": "'$(date -Iseconds)'",
  "updated_at": "'$(date -Iseconds)'",
  "local_node": null,
  "peers": []
}' > "${NETWORK_REGISTRY}"
    
    network_log "Cleared network registry"
    network_log_success "Network registry cleared"
    return 0
}

# =============================================================================
# Helper Functions for Test Scripts
# =============================================================================

require_connection() {
    # Check if connection exists, print message if not
    # Use this at the start of test scripts
    if ! is_connected; then
        echo -e "${RED}═══════════════════════════════════════════════════════════${NC}"
        echo -e "${RED}   No peer connection found!${NC}"
        echo -e "${RED}═══════════════════════════════════════════════════════════${NC}"
        echo ""
        echo "   Run './setup.sh' → Option 2: Establish Network Connection first"
        echo ""
        echo "   Or manually specify peer address with --override-peer"
        echo ""
        return 1
    fi
    return 0
}

get_peer_multiaddr_for_tests() {
    # Get the first peer's multiaddr for use in tests
    # Fallback to override if provided
    local override="$1"
    
    if [ -n "$override" ]; then
        echo "$override"
        return 0
    fi
    
    get_first_peer
}

get_peer_host_port() {
    # Extract host and port from multiaddr
    # Args: multiaddr
    # Returns: "host:port" or empty
    local multiaddr="$1"
    
    if [ -z "$multiaddr" ]; then
        echo ""
        return 1
    fi
    
    python3 << EOF
import re
multiaddr = "${multiaddr}"
# Pattern: /ip4/HOST/tcp/PORT/...
match = re.search(r'/ip4/([^/]+)/tcp/(\d+)', multiaddr)
if match:
    print(f"{match.group(1)}:{match.group(2)}")
else:
    print("")
EOF
}

# =============================================================================
# Debug Functions
# =============================================================================

show_registry() {
    # Show the full registry file contents
    if [ ! -f "${NETWORK_REGISTRY}" ]; then
        echo "No registry file found at ${NETWORK_REGISTRY}"
        return 1
    fi
    
    echo -e "${CYAN}Registry file: ${NETWORK_REGISTRY}${NC}"
    echo ""
    cat "${NETWORK_REGISTRY}"
}

# =============================================================================
# Main (for testing)
# =============================================================================

if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    # Script is being run directly, show usage
    echo "Network Registry Module"
    echo "======================="
    echo ""
    echo "This script is meant to be sourced, not run directly."
    echo ""
    echo "Usage:"
    echo "  source scripts/network_registry.sh"
    echo ""
    echo "Available functions:"
    echo "  init_registry       - Initialize the registry"
    echo "  save_local_node     - Save local node info"
    echo "  save_peer           - Save a peer connection"
    echo "  get_peers           - Get all peers (JSON)"
    echo "  get_peer_by_id      - Get a specific peer"
    echo "  get_first_peer      - Get first peer multiaddr"
    echo "  list_peers          - Show peers in human format"
    echo "  is_connected        - Check if connected"
    echo "  update_peer_status  - Update peer status"
    echo "  remove_peer         - Remove a peer"
    echo "  clear_registry      - Clear all peers"
    echo "  require_connection  - Check connection for tests"
    echo "  show_registry       - Debug: show registry file"
    echo ""
    echo "Registry location: ${NETWORK_REGISTRY}"
fi
