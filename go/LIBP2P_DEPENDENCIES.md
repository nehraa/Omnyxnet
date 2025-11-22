# libp2p Dependencies

**Version:** 0.3.0-alpha  
**Last Updated:** 2025-11-22  
**Status:** Implemented - Testing Required

> 📋 This document lists libp2p dependencies used in the Go node. The dependencies are installed but integration testing is still in progress.

## Installation

```bash
# Add libp2p dependencies to go.mod
go get github.com/libp2p/go-libp2p@latest
go get github.com/libp2p/go-libp2p-kad-dht@latest
go get github.com/multiformats/go-multiaddr@latest
```

# Core libp2p components
github.com/libp2p/go-libp2p v0.32.0
github.com/libp2p/go-libp2p-kad-dht v0.25.0

# Transport layers
github.com/libp2p/go-libp2p/p2p/transport/tcp
github.com/libp2p/go-libp2p/p2p/transport/quic
github.com/libp2p/go-libp2p/p2p/transport/websocket  # For browser compatibility

# Security
github.com/libp2p/go-libp2p/p2p/security/noise
github.com/libp2p/go-libp2p/p2p/security/tls

# Stream multiplexing  
github.com/libp2p/go-libp2p/p2p/muxer/yamux
github.com/libp2p/go-libp2p/p2p/muxer/mplex

# NAT traversal (THE KEY COMPONENTS!)
github.com/libp2p/go-libp2p/p2p/protocol/holepunch  # Direct NAT hole punching
github.com/libp2p/go-libp2p/p2p/protocol/circuitv2  # Relay circuits
github.com/libp2p/go-libp2p/p2p/net/swarm           # Connection management
github.com/libp2p/go-libp2p/p2p/protocol/autonat    # NAT detection

# Discovery
github.com/libp2p/go-libp2p/p2p/discovery/mdns      # Local network discovery
github.com/libp2p/go-libp2p/p2p/discovery/routing   # DHT-based discovery