# Pangea Net Go Node - Architecture

## Overview

This document explains the code organization and architecture of the Go node implementation.

## Folder Structure

```
WGT/
├── cmd/
│   └── go-node/          # Main application entry point
│       └── main.go       # CLI and node initialization
│
├── internal/             # Internal packages (not exposed to Python)
│   ├── store/           # Node data storage
│   │   └── store.go     # Thread-safe node store with quality metrics
│   ├── network/         # P2P networking layer
│   │   └── p2p.go       # Noise Protocol, connections, latency measurement
│   ├── rpc/             # Cap'n Proto RPC server
│   │   └── server.go    # RPC server implementation
│   └── utils/           # Utility functions
│       └── ports.go     # Port cleanup and availability checking
│
├── pkg/
│   └── api/             # Public API for Python (high-level functions)
│       └── node.go      # NodeManager - easy-to-use functions for Python
│
├── schema/              # Cap'n Proto schema definitions
│   └── schema.capnp     # RPC interface definition
│
├── docs/                # Documentation
│   └── ARCHITECTURE.md  # This file
│
└── scripts/             # Utility scripts
    └── cleanup.sh       # Port cleanup script
```

## Package Responsibilities

### cmd/go-node
**Purpose**: Main application entry point
**What it does**:
- Parses command-line arguments
- Initializes all components (store, network, RPC)
- Handles graceful shutdown
- Manages port cleanup on errors

**Key Functions**:
- `main()` - Entry point
- Port cleanup on startup errors
- Signal handling for graceful shutdown

### internal/store
**Purpose**: Node data storage and management
**What it does**:
- Stores node state (ID, status, latency, threat score)
- Tracks connection quality metrics (jitter, packet loss)
- Thread-safe operations
- Automatic state transitions

**Key Types**:
- `Node` - Represents a network node with quality metrics
- `Store` - Thread-safe storage for nodes

**Key Functions**:
- `GetNode(id)` - Get node by ID
- `GetAllNodes()` - Get all nodes
- `UpdateLatency()` - Update latency and calculate jitter
- `UpdateThreatScore()` - Update threat score and auto-transition states
- `UpdatePacketLoss()` - Update packet loss percentage

### internal/network
**Purpose**: P2P networking with Noise Protocol
**What it does**:
- Manages P2P connections
- Implements Noise Protocol XX handshake
- Measures latency via ping/pong
- Encrypts/decrypts messages
- Tracks connection quality

**Key Types**:
- `P2PNode` - Main P2P node manager
- `P2PConnection` - Individual peer connection

**Key Functions**:
- `ConnectToPeer()` - Connect to a new peer
- `SendMessage()` - Send encrypted message
- `GetConnectionQuality()` - Get latency/jitter/packet loss
- `DisconnectPeer()` - Close connection
- `GetConnectedPeers()` - List all connected peers

### internal/rpc
**Purpose**: Cap'n Proto RPC server for Python communication
**What it does**:
- Implements Cap'n Proto RPC interface
- Handles Python requests
- Converts between Go types and Cap'n Proto types
- Manages RPC connections

**Key Functions**:
- `StartCapnpServer()` - Start RPC server
- Implements all NodeService methods from schema

### pkg/api
**Purpose**: High-level API for Python to use
**What it does**:
- Provides simple, direct functions Python can call
- Abstracts away internal complexity
- Makes it easy to add new connections/streams
- One-stop interface for all node operations

**Key Functions** (Python can call these directly):
- `StartNode()` - Start a node
- `StopNode()` - Stop a node
- `ConnectToPeer()` - Connect to new peer
- `SendMessage()` - Send message to peer
- `GetNodeData()` - Get node information
- `GetAllNodesData()` - Get all nodes
- `UpdateThreatScore()` - Update threat score (from AI)
- `GetConnectionQuality()` - Get connection metrics
- `DisconnectPeer()` - Disconnect from peer
- `GetConnectedPeers()` - List connected peers

### internal/utils
**Purpose**: Utility functions
**What it does**:
- Port availability checking
- Port cleanup utilities
- Error handling helpers

**Key Functions**:
- `CheckPortAvailable()` - Check if port is free
- `WaitForPort()` - Wait for port to become available
- `CleanupPort()` - Attempt to free a port

## Data Flow

1. **Python → Go (via Cap'n Proto RPC)**:
   - Python calls RPC methods defined in `schema.capnp`
   - RPC server (`internal/rpc`) receives request
   - Calls appropriate function in `pkg/api`
   - API function uses `internal/store` and `internal/network`

2. **Go → Python (via Cap'n Proto RPC)**:
   - Network layer updates node data in `internal/store`
   - Python can query this data via RPC calls
   - Real-time updates via streaming (future)

3. **P2P Communication**:
   - `internal/network` handles all P2P connections
   - Measures latency, calculates jitter
   - Updates `internal/store` with quality metrics
   - All communication encrypted via Noise Protocol

## Connection Quality Metrics

The system collects:
- **Latency**: Round-trip time (RTT) in milliseconds
- **Jitter**: Latency variance (calculated from latency changes)
- **Packet Loss**: Percentage of lost packets (0.0-1.0)
- **Last Seen**: Timestamp of last successful ping

These metrics are stored in `Node` struct and accessible via RPC.

## Adding New Connections

To add a new connection from Python:
```python
# Python code
client.connectToPeer(peerId=2, host="localhost", port=9091)
```

This calls:
1. `pkg/api.ConnectToPeer()` - High-level API
2. `internal/network.ConnectToPeer()` - Network layer
3. Noise Protocol handshake
4. Connection added to connection pool
5. Latency measurement starts automatically

## Port Cleanup

Ports are automatically checked and cleaned up:
- On startup: Checks if ports are available, waits if needed
- On error: Attempts to free ports before exiting
- On shutdown: All connections closed, ports freed

## Go Structs vs Classes

**Question**: Did we use classes?

**Answer**: Go doesn't have classes, but we use **structs** which are similar:
- `Node` struct = data + methods (like a class)
- Methods are defined on structs: `func (n *Node) Method()`
- Encapsulation via package boundaries (internal/ vs pkg/)
- Interfaces for abstraction (like abstract classes)

The code is organized in an object-oriented style using Go's structs and methods.

