# Python API Guide

**Version:** 0.3.0-alpha  
**Last Updated:** 2025-11-22

> 📋 This guide describes the Python API for interacting with Pangea Net nodes. For version status, see [../VERSION.md](../VERSION.md).

This document explains how Python can interact with the Go node via Cap'n Proto RPC.

## Quick Start

```python
import capnp
import socket

# Load the schema
schema = capnp.load('schema/schema.capnp')

# Connect to Go node
client = capnp.TwoPartyClient(socket.create_connection(('localhost', 8080)))
node_service = client.bootstrap().cast_as(schema.NodeService)

# Now you can call functions directly!
```

## Available Functions

### Node Management

#### StartNode(nodeID, capnpPort, p2pPort)
Start a new node instance.
```python
# This is handled by the Go binary, but you can check status
```

#### StopNode()
Stop the node.
```python
# Handled via signal, but you can disconnect
```

### Peer Connections

#### ConnectToPeer(peerID, host, port)
Connect to a new peer. This is the easiest way to add connections!
```python
peer = schema.PeerAddress.new_message()
peer.peerId = 2
peer.host = "localhost"
peer.port = 9091

result = node_service.connectToPeer(peer).wait()
if result.success:
    print(f"Connected! Quality: {result.quality.latencyMs}ms")
```

#### DisconnectPeer(peerID)
Disconnect from a peer.
```python
result = node_service.disconnectPeer(2).wait()
```

#### GetConnectedPeers()
Get list of all connected peer IDs.
```python
peers = node_service.getConnectedPeers().wait()
for peer_id in peers.peers:
    print(f"Connected to peer {peer_id}")
```

### Messaging

#### SendMessage(toPeerID, data)
Send a message to a peer.
```python
msg = schema.Message.new_message()
msg.toPeerId = 2
msg.data = b"Hello from Python!"

result = node_service.sendMessage(msg).wait()
if result.success:
    print("Message sent!")
```

### Node Data

#### GetNodeData(nodeID)
Get data for a specific node.
```python
query = schema.NodeQuery.new_message()
query.nodeId = 1

result = node_service.getNode(query).wait()
node = result.node
print(f"Node {node.id}: latency={node.latencyMs}ms, threat={node.threatScore}")
```

#### GetAllNodesData()
Get data for all nodes.
```python
result = node_service.getAllNodes().wait()
for node in result.nodes.nodes:
    print(f"Node {node.id}: {node.latencyMs}ms")
```

### Threat Score (AI Control)

#### UpdateThreatScore(nodeID, threatScore)
Update the threat score (called by Python AI).
```python
update = schema.NodeUpdate.new_message()
update.nodeId = 1
update.threatScore = 0.95  # High threat

result = node_service.updateNode(update).wait()
```

### Connection Quality

#### GetConnectionQuality(peerID)
Get connection quality metrics for a peer.
```python
quality = node_service.getConnectionQuality(2).wait()
print(f"Latency: {quality.quality.latencyMs}ms")
print(f"Jitter: {quality.quality.jitterMs}ms")
print(f"Packet Loss: {quality.quality.packetLoss * 100}%")
```

## Example: Complete Workflow

```python
import capnp
import socket
import time

# Connect
schema = capnp.load('schema/schema.capnp')
client = capnp.TwoPartyClient(socket.create_connection(('localhost', 8080)))
service = client.bootstrap().cast_as(schema.NodeService)

# Connect to a peer
peer = schema.PeerAddress.new_message()
peer.peerId = 2
peer.host = "localhost"
peer.port = 9091
service.connectToPeer(peer).wait()

# Send a message
msg = schema.Message.new_message()
msg.toPeerId = 2
msg.data = b"Test message"
service.sendMessage(msg).wait()

# Get connection quality
quality = service.getConnectionQuality(2).wait()
print(f"Quality: {quality.quality.latencyMs}ms latency")

# Get all nodes
nodes = service.getAllNodes().wait()
for node in nodes.nodes.nodes:
    print(f"Node {node.id}: {node.latencyMs}ms")

# Update threat score (from AI)
update = schema.NodeUpdate.new_message()
update.nodeId = 2
update.threatScore = 0.8
service.updateNode(update).wait()
```

## Connection Quality Metrics

The system automatically collects:
- **latencyMs**: Round-trip time in milliseconds
- **jitterMs**: Latency variance (how much latency varies)
- **packetLoss**: Percentage of lost packets (0.0-1.0)

These are updated automatically as the node measures latency via ping/pong.

## Error Handling

All RPC calls return a result with a `success` field:
```python
result = node_service.connectToPeer(peer).wait()
if not result.success:
    print("Connection failed!")
```

## Notes

- All P2P communication is automatically encrypted via Noise Protocol
- Latency is measured automatically every 5 seconds
- Connection quality metrics are updated in real-time
- You can add multiple connections easily - just call `connectToPeer()` multiple times
- Each connection runs in its own goroutine, so they don't block each other

