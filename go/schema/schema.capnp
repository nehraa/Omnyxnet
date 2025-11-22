@0x8513e0c6129c1f4c;

# Cap'n Proto schema for Pangea Net
# Removed Go-specific imports for compatibility

struct Node {
    id @0 :UInt32;
    status @1 :UInt32;  # Active, Purgatory, Dead
    latencyMs @2 :Float32;
    threatScore @3 :Float32;
}

struct NodeList {
    nodes @0 :List(Node);
}

struct NodeUpdate {
    nodeId @0 :UInt32;
    latencyMs @1 :Float32;
    threatScore @2 :Float32;
}

struct NodeQuery {
    nodeId @0 :UInt32;
}

struct PeerAddress {
    peerId @0 :UInt32;
    host @1 :Text;
    port @2 :UInt16;
}

struct Message {
    toPeerId @0 :UInt32;
    data @1 :Data;
}

struct ConnectionQuality {
    latencyMs @0 :Float32;
    jitterMs @1 :Float32;
    packetLoss @2 :Float32;
}

struct NetworkMetrics {
    avgRttMs @0 :Float32;
    packetLoss @1 :Float32;
    bandwidthMbps @2 :Float32;
    peerCount @3 :UInt32;
    cpuUsage @4 :Float32;
    ioCapacity @5 :Float32;
}

interface NodeService {
    # Get a specific node by ID
    getNode @0 (query :NodeQuery) -> (node :Node);
    
    # Get all nodes
    getAllNodes @1 () -> (nodes :NodeList);
    
    # Update node state (called by Python AI)
    updateNode @2 (update :NodeUpdate) -> (success :Bool);
    
    # Update latency (called by network layer)
    updateLatency @3 (nodeId :UInt32, latencyMs :Float32) -> (success :Bool);
    
    # Stream node updates (for real-time monitoring)
    streamUpdates @4 () -> (update :NodeUpdate);
    
    # Connect to a new peer (Python can call this directly)
    connectToPeer @5 (peer :PeerAddress) -> (success :Bool, quality :ConnectionQuality);
    
    # Send a message to a peer
    sendMessage @6 (msg :Message) -> (success :Bool);
    
    # Get connection quality for a peer
    getConnectionQuality @7 (peerId :UInt32) -> (quality :ConnectionQuality);
    
    # Disconnect from a peer
    disconnectPeer @8 (peerId :UInt32) -> (success :Bool);
    
    # Get list of connected peers
    getConnectedPeers @9 () -> (peers :List(UInt32));
    
    # Get network metrics for shard optimization
    getNetworkMetrics @10 () -> (metrics :NetworkMetrics);
}

