# Network Connection Guide

This guide explains how to establish and manage network connections in the WGT distributed system.

## Overview

The WGT network uses a **Manager/Worker** model:
- **Manager (Initiator)**: Starts first, orchestrates compute tasks
- **Worker (Responder)**: Connects to Manager, executes tasks

All connection information is stored in a local registry at `~/.wgt/network.json`.

## Quick Start

### Option 1: Using setup.sh Menu

```bash
./scripts/setup.sh
# Select: 2) Establish Network Connection
# Choose: 1) Manager  or  2) Worker
```

### Option 2: Direct Commands

**Start Manager (Device 1):**
```bash
cd go && ./bin/go-node \
    -node-id=1 \
    -capnp-addr=:8080 \
    -libp2p=true \
    -libp2p-port=9081 \
    -mdns=true \
    -local
```

**Start Worker (Device 2):**
```bash
cd go && ./bin/go-node \
    -node-id=2 \
    -capnp-addr=:8081 \
    -libp2p=true \
    -libp2p-port=9082 \
    -mdns=true \
    -peers=/ip4/192.168.1.100/tcp/9081 \
    -local
```

## Network Registry

### Location

All network information is stored at:
```
~/.wgt/
├── network.json    # Peer registry
└── logs/
    └── network.log # Connection logs
```

### Registry Structure

```json
{
  "version": "1.0.0",
  "created_at": "2025-12-05T14:00:00+00:00",
  "updated_at": "2025-12-05T14:30:00+00:00",
  "local_node": {
    "node_id": "node-1",
    "multiaddr": "/ip4/192.168.1.100/tcp/9081/p2p/12D3KooWBhSNFXL9HQQBAJDsmMM4bFgFxN9pRJ9xGmBQd3bVZwjx",
    "capnp_port": 8080,
    "mode": "manager",
    "started_at": "2025-12-05T14:00:00+00:00",
    "status": "running"
  },
  "peers": [
    {
      "node_id": "node-2",
      "multiaddr": "/ip4/192.168.1.101/tcp/9082/p2p/Qm...",
      "capnp_port": 8081,
      "status": "connected",
      "connected_at": "2025-12-05T14:05:00+00:00",
      "last_seen": "2025-12-05T14:30:00+00:00"
    }
  ]
}
```

## Check Network Status

Use the check_network.sh script:

```bash
# Show status summary
./scripts/check_network.sh --status

# List all peers
./scripts/check_network.sh --list

# Test connectivity to peers
./scripts/check_network.sh --test

# Get specific peer address
./scripts/check_network.sh --get-peer node-2

# Clear registry (fresh start)
./scripts/check_network.sh --clear

# Show raw registry file
./scripts/check_network.sh --registry
```

### Example Output

```
═══════════════════════════════════════════════════════════
   Network Status Summary
═══════════════════════════════════════════════════════════

   🟢 Local Node: MANAGER on port 8080

   📊 Peers:
      Connected:    2
      Disconnected: 0
      Total:        2

   📅 Last Updated: 2025-12-05 14:30:00

   ✅ Network Status: CONNECTED
```

## Network Registry Functions

For use in shell scripts:

```bash
# Source the registry module
source scripts/network_registry.sh

# Initialize registry
init_registry

# Save local node info (with full multiaddr including peer ID)
save_local_node "node-1" "/ip4/192.168.1.100/tcp/9081/p2p/12D3KooWBhSNFXL9HQQBAJDsmMM4bFgFxN9pRJ9xGmBQd3bVZwjx" "8080" "manager"

# Save a peer (with full multiaddr including peer ID)
save_peer "node-2" "/ip4/192.168.1.101/tcp/9082/p2p/12D3KooWAnotherValidPeerIDGoesHereBase58Encoded52Chars" "8081" "connected"

# Get all peers
get_peers  # Returns JSON array

# Get specific peer
get_peer_by_id "node-2"  # Returns JSON object

# Get first peer (for quick access)
get_first_peer  # Returns multiaddr string

# Check if connected
if is_connected; then
    echo "Connected to peers"
fi

# List peers in human format
list_peers

# Update peer status
update_peer_status "node-2" "disconnected"

# Remove a peer
remove_peer "node-2"

# Clear all peers
clear_registry
```

## Using with Test Scripts

Test scripts automatically use the registry:

```bash
source scripts/network_registry.sh

# Check connection before running tests
if ! require_connection; then
    echo "Run setup.sh → Option 2 first"
    exit 1
fi

# Get peer address for tests
PEER_ADDR=$(get_first_peer)

# Or override with manual address
PEER_ADDR=$(get_peer_multiaddr_for_tests "$OVERRIDE_PEER")
```

## Manager Mode

When running as Manager:

1. **Starts listening** on configured ports
2. **Waits for Workers** to connect (up to 60 seconds by default)
3. **Saves connection info** to registry
4. **Orchestrates compute tasks** when Workers connect

```bash
./scripts/setup.sh
# Select: 2) Establish Network Connection
# Select: 1) Manager (Initiator)

# Output:
# ═══════════════════════════════════════════════════════════
#    ✅ Manager Node Started!
# ═══════════════════════════════════════════════════════════
#
#    Node ID:     1
#    RPC Address: 192.168.1.100:8080
#    P2P Port:    9081
#    Mode:        MANAGER (Initiator)
#
# 📋 Share this with Workers:
#
#    IP Address: 192.168.1.100
#    RPC Port:   8080
```

## Worker Mode

When running as Worker:

1. **Prompts for Manager address**
2. **Connects to Manager** via libp2p
3. **Saves connection info** to registry
4. **Waits for compute tasks** from Manager

```bash
./scripts/setup.sh
# Select: 2) Establish Network Connection
# Select: 2) Worker (Responder)

# Enter Manager IP: 192.168.1.100
# Enter Manager port: 8080

# Output:
# ═══════════════════════════════════════════════════════════
#    ✅ Worker Node Started!
# ═══════════════════════════════════════════════════════════
#
#    Node ID:       2
#    Local Address: 192.168.1.101:8081
#    Manager:       192.168.1.100:8080
#    Mode:          WORKER (Responder)
```

## Manual Peer Override

When mDNS discovery fails, use manual peer addresses:

```bash
# With CLI
python main.py compute matrix-multiply \
    --connect \
    --peer-address /ip4/192.168.1.100/tcp/9081/p2p/QmXYZ...

# With test scripts
./scripts/container_tests/test_matrix_cli.sh \
    --override-peer /ip4/192.168.1.100/tcp/9081/p2p/QmXYZ...
```

## Multiaddr Format

Peer addresses use the multiaddr format:

```
/ip4/<IP>/tcp/<PORT>/p2p/<PEER_ID>
```

Examples:
```
/ip4/192.168.1.100/tcp/9081
/ip4/192.168.1.100/tcp/9081/p2p/QmTest123...
/ip4/10.0.0.5/tcp/9082/p2p/12D3KooW...
```

## Troubleshooting

### Can't Find Peers

1. Check if Manager is running:
   ```bash
   ./scripts/check_network.sh --status
   ```

2. Verify network connectivity:
   ```bash
   ./scripts/check_network.sh --test
   ```

3. Check firewall allows ports:
   ```bash
   sudo ufw allow 8080/tcp  # RPC port
   sudo ufw allow 9081/tcp  # libp2p port
   ```

### mDNS Discovery Fails

Use manual peer address:
```bash
--peer-address /ip4/<MANAGER_IP>/tcp/<LIBP2P_PORT>
```

### Connection Timeout

1. Increase timeout (modify setup.sh)
2. Check network latency
3. Verify correct IP/port

### Registry Corrupted

```bash
./scripts/check_network.sh --clear
```

## See Also

- [CLI_MATRIX_MULTIPLY.md](CLI_MATRIX_MULTIPLY.md) - Matrix multiply CLI
- [CONTAINERIZED_TESTING.md](CONTAINERIZED_TESTING.md) - Container testing
- [DISTRIBUTED_COMPUTE_QUICK_START.md](DISTRIBUTED_COMPUTE_QUICK_START.md) - Quick start
- [MANUAL_CONNECT_GUIDE.md](MANUAL_CONNECT_GUIDE.md) - Manual connection
