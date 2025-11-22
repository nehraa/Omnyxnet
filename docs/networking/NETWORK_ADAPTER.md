# Network Adapter Documentation

**File**: `go/network_adapter.go`  
**Last Updated**: November 22, 2025  
**Status**: ✅ Fully Implemented

## Overview

The Network Adapter provides a unified interface for both libp2p and legacy P2P implementations in Pangea Net. It abstracts the networking layer to allow seamless switching between different P2P protocols.

## Interface

```go
type NetworkAdapter interface {
    ConnectToPeer(peerAddr string, peerID uint32) error
    DisconnectPeer(peerID uint32) error
    SendMessage(peerID uint32, data []byte) error
    FetchShard(peerID uint32, shardIndex uint32) ([]byte, error)
    GetConnectedPeers() []uint32
    GetConnectionQuality(peerID uint32) (latencyMs, jitterMs, packetLoss float32, err error)
}
```

## Implementations

### 1. LibP2PAdapter

**Purpose**: Wraps libp2p for modern P2P networking with DHT, NAT traversal, and encryption.

**Key Methods**:

- **ConnectToPeer**: Connects to a peer using multiaddr format
- **SendMessage**: Sends data over libp2p streams
- **FetchShard**: **[NEW]** Fetches file shards from peers for download reconstruction
  - Protocol: Sends `[REQUEST_TYPE=1][SHARD_INDEX=4 bytes]`
  - Response: Raw shard data (up to 1MB)
  - Used by: `Download` RPC method in `capnp_service.go`

**Status**: ✅ Complete with FetchShard implementation (Nov 22, 2025)

### 2. LegacyP2PAdapter

**Purpose**: Legacy P2P implementation with Noise Protocol encryption.

**Key Methods**:
- Same interface as LibP2PAdapter
- Uses Noise Protocol for encryption
- FetchShard also implemented with Noise-encrypted transport

**Status**: ✅ Complete

## Recent Changes

### November 22, 2025 - FetchShard Implementation

**Location**: Lines 103-142 (LibP2PAdapter), Lines 218-276 (LegacyP2PAdapter)

**Added**:
```go
func (a *LibP2PAdapter) FetchShard(peerID uint32, shardIndex uint32) ([]byte, error)
```

**Purpose**: Enable the Download RPC method to fetch file shards from remote peers.

**Protocol**:
1. Send 5-byte request: `[0x01][shard_index as uint32]`
2. Read response up to 1MB
3. Return shard data or error

**Integration**: Called by `capnp_service.go` Download function to reconstruct files from distributed shards.

## Connection Modes

### Localhost Testing (`-local` flag)

- **mDNS Discovery**: Automatic peer discovery on local network
- **No bootstrap required**: Nodes find each other automatically
- **Use case**: Development, testing, single-machine multi-node setup
- **Note**: mDNS implementation exists but auto-connect may not be fully working yet. Manual connection via IP/PeerID works reliably.

### Cross-Device (`-peers` flag)

- **Manual Bootstrap**: Requires peer multiaddr from bootstrap node
- **Format**: `/ip4/<IP>/tcp/<PORT>/p2p/<PEER_ID>`
- **Use case**: Production, distributed networks, different machines
- **Status**: ✅ Working - connections established successfully

## Usage Examples

### Localhost (3 nodes, mDNS)

```bash
# Node 1
./go/bin/go-node -node-id=1 -capnp-addr=:18080 -libp2p -local

# Node 2  
./go/bin/go-node -node-id=2 -capnp-addr=:18081 -libp2p -local

# Node 3
./go/bin/go-node -node-id=3 -capnp-addr=:18082 -libp2p -local
```

### Cross-Device (with bootstrap)

```bash
# Device 1 (Bootstrap node)
./go/bin/go-node -node-id=1 -libp2p

# Copy the multiaddr from output, then on Device 2:
./go/bin/go-node -node-id=2 -libp2p -peers="/ip4/192.168.1.100/tcp/40225/p2p/12D3KooW..."
```

## Known Issues

- **mDNS Auto-Connect**: mDNS discovery detects peers but automatic connection may not always work
- **Workaround**: Manual connection via `-peers` flag with explicit multiaddr works reliably
- **Status**: Not critical - manual peer connection is functional for both local and cross-device

## Dependencies

- `go-libp2p`: Core P2P library
- `libpangea_ces.so`: Rust CES library (for shard processing)
- `NodeStore`: Peer information storage

## Testing

See: `tests/test_upload_download_local.sh` for localhost multi-node testing.

## Related Files

- `go/capnp_service.go` - Uses NetworkAdapter for Upload/Download
- `go/libp2p_node.go` - LibP2P implementation
- `go/legacy_p2p.go` - Legacy P2P implementation
