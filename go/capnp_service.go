// Package main implements the Cap'n Proto RPC server for Python-Go communication.
//
// IMPORTANT: This file requires generated code from schema.capnp.
// Before building, run: capnp compile -ogo schema.capnp
// This will generate types like NodeService_getNode, NodeService_ServerToClient, etc.
package main

import (
	"context"
	"fmt"
	"log"
	"net"

	"capnproto.org/go/capnp/v3"
	"capnproto.org/go/capnp/v3/rpc"
)

// nodeServiceServer implements the Cap'n Proto NodeService interface
// Note: NodeService_Server interface is generated in schema.capnp.go
type nodeServiceServer struct {
	store   *NodeStore
	network NetworkAdapter
	shmMgr  *SharedMemoryManager
}

// NewNodeServiceServer creates a new NodeService server
func NewNodeServiceServer(store *NodeStore, network NetworkAdapter, shmMgr *SharedMemoryManager) NodeService_Server {
	return &nodeServiceServer{
		store:   store,
		network: network,
		shmMgr:  shmMgr,
	}
}

// GetNode implements the getNode method
func (s *nodeServiceServer) GetNode(ctx context.Context, call NodeService_getNode) error {
	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	args := call.Args()
	query, err := args.Query()
	if err != nil {
		return err
	}

	nodeID := query.NodeId()
	localNode, exists := s.store.GetNode(nodeID)
	if !exists {
		return fmt.Errorf("node %d not found", nodeID)
	}

	nodeMsg, err := results.NewNode()
	if err != nil {
		return err
	}

	nodeMsg.SetId(localNode.ID)
	nodeMsg.SetStatus(uint32(localNode.Status))
	nodeMsg.SetLatencyMs(localNode.LatencyMs)
	nodeMsg.SetThreatScore(localNode.ThreatScore)

	return nil
}

// GetAllNodes implements the getAllNodes method
func (s *nodeServiceServer) GetAllNodes(ctx context.Context, call NodeService_getAllNodes) error {
	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	localNodes := s.store.GetAllNodes()
	nodeList, err := results.NewNodes()
	if err != nil {
		return err
	}

	// Create a list of nodes using generated code
	seg := results.Segment()
	nodesList, err := NewNode_List(seg, int32(len(localNodes)))
	if err != nil {
		return err
	}

	for i, localNode := range localNodes {
		nodeMsg := nodesList.At(i)
		nodeMsg.SetId(localNode.ID)
		nodeMsg.SetStatus(uint32(localNode.Status))
		nodeMsg.SetLatencyMs(localNode.LatencyMs)
		nodeMsg.SetThreatScore(localNode.ThreatScore)
	}

	nodeList.SetNodes(nodesList)
	return nil
}

// UpdateNode implements the updateNode method
func (s *nodeServiceServer) UpdateNode(ctx context.Context, call NodeService_updateNode) error {
	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	args := call.Args()
	update, err := args.Update()
	if err != nil {
		return err
	}

	nodeID := update.NodeId()
	latencyMs := update.LatencyMs()
	threatScore := update.ThreatScore()

	success := s.store.UpdateLatency(nodeID, latencyMs)
	if success {
		success = s.store.UpdateThreatScore(nodeID, threatScore)
	}

	results.SetSuccess(success)
	return nil
}

// UpdateLatency implements the updateLatency method
func (s *nodeServiceServer) UpdateLatency(ctx context.Context, call NodeService_updateLatency) error {
	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	args := call.Args()
	nodeID := args.NodeId()
	latencyMs := args.LatencyMs()

	success := s.store.UpdateLatency(nodeID, latencyMs)
	results.SetSuccess(success)
	return nil
}

// StreamUpdates implements the streamUpdates method
// NOTE: Real-time streaming would require event-driven architecture
// For high-throughput data, use shared memory (see WriteToSharedMemory/ReadFromSharedMemory)
func (s *nodeServiceServer) StreamUpdates(ctx context.Context, call NodeService_streamUpdates) error {
	// UNTESTABLE: Requires multi-node deployment with real network events
	// This is a placeholder that demonstrates the intended structure

	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	// In production, this would:
	// 1. Subscribe to node state change events
	// 2. Stream updates as they occur
	// 3. For large data streams, write to shared memory and return pointers

	// Return current snapshot for now
	update, err := results.NewUpdate()
	if err != nil {
		return err
	}

	// Get first node as example
	nodes := s.store.GetAllNodes()
	if len(nodes) > 0 {
		update.SetNodeId(nodes[0].ID)
		update.SetLatencyMs(nodes[0].LatencyMs)
		update.SetThreatScore(nodes[0].ThreatScore)
	}

	return nil
}

// ConnectToPeer implements the connectToPeer method
func (s *nodeServiceServer) ConnectToPeer(ctx context.Context, call NodeService_connectToPeer) error {
	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	args := call.Args()
	peer, err := args.Peer()
	if err != nil {
		return err
	}

	peerID := peer.PeerId()
	host, err := peer.Host()
	if err != nil {
		return err
	}
	port := peer.Port()

	// Construct peer address
	peerAddr := fmt.Sprintf("%s:%d", host, port)

	// Connect using network adapter
	err = s.network.ConnectToPeer(peerAddr, peerID)
	if err != nil {
		results.SetSuccess(false)
		return nil // Don't fail RPC call, just indicate failure
	}

	// Get connection quality
	latencyMs, jitterMs, packetLoss, err := s.network.GetConnectionQuality(peerID)
	if err != nil {
		latencyMs = 0
		jitterMs = 0
		packetLoss = 0
	}

	// Set success and quality
	results.SetSuccess(true)
	quality, err := results.NewQuality()
	if err != nil {
		return err
	}
	quality.SetLatencyMs(latencyMs)
	quality.SetJitterMs(jitterMs)
	quality.SetPacketLoss(packetLoss)

	return nil
}

// SendMessage implements the sendMessage method
func (s *nodeServiceServer) SendMessage(ctx context.Context, call NodeService_sendMessage) error {
	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	args := call.Args()
	msg, err := args.Msg()
	if err != nil {
		return err
	}

	toPeerID := msg.ToPeerId()
	data, err := msg.Data()
	if err != nil {
		return err
	}

	// Send message using network adapter
	err = s.network.SendMessage(toPeerID, data)
	if err != nil {
		log.Printf("Failed to send message to peer %d: %v", toPeerID, err)
		results.SetSuccess(false)
	} else {
		results.SetSuccess(true)
	}

	return nil
}

// GetConnectionQuality implements the getConnectionQuality method
func (s *nodeServiceServer) GetConnectionQuality(ctx context.Context, call NodeService_getConnectionQuality) error {
	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	args := call.Args()
	peerID := args.PeerId()

	// Get quality metrics from network adapter
	latencyMs, jitterMs, packetLoss, err := s.network.GetConnectionQuality(peerID)
	if err != nil {
		// Return zero values if error
		latencyMs = 0
		jitterMs = 0
		packetLoss = 0
	}

	quality, err := results.NewQuality()
	if err != nil {
		return err
	}

	quality.SetLatencyMs(latencyMs)
	quality.SetJitterMs(jitterMs)
	quality.SetPacketLoss(packetLoss)

	return nil
}

// DisconnectPeer implements the disconnectPeer method
func (s *nodeServiceServer) DisconnectPeer(ctx context.Context, call NodeService_disconnectPeer) error {
	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	args := call.Args()
	peerID := args.PeerId()

	// Disconnect using network adapter
	err = s.network.DisconnectPeer(peerID)
	if err != nil {
		log.Printf("Failed to disconnect peer %d: %v", peerID, err)
		results.SetSuccess(false)
	} else {
		results.SetSuccess(true)
	}

	return nil
}

// GetConnectedPeers implements the getConnectedPeers method
func (s *nodeServiceServer) GetConnectedPeers(ctx context.Context, call NodeService_getConnectedPeers) error {
	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	// Get connected peers from network adapter
	peerIDs := s.network.GetConnectedPeers()

	// Create uint32 list
	seg := results.Segment()
	peersList, err := capnp.NewUInt32List(seg, int32(len(peerIDs)))
	if err != nil {
		return err
	}

	for i, peerID := range peerIDs {
		peersList.Set(i, peerID)
	}

	if err := results.SetPeers(peersList); err != nil {
		return err
	}

	return nil
}

// GetNetworkMetrics implements the getNetworkMetrics method
func (s *nodeServiceServer) GetNetworkMetrics(ctx context.Context, call NodeService_getNetworkMetrics) error {
	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	// Get network metrics from network adapter
	// For now, return mock data - this should be implemented properly
	metrics, err := results.NewMetrics()
	if err != nil {
		return err
	}

	metrics.SetAvgRttMs(50.0)
	metrics.SetPacketLoss(0.01)
	metrics.SetBandwidthMbps(100.0)
	metrics.SetPeerCount(uint32(len(s.network.GetConnectedPeers())))
	metrics.SetCpuUsage(0.3)
	metrics.SetIoCapacity(0.8)

	// Add warning to response and log
	metrics.SetWarning("WARNING: All metrics except PeerCount are mock values. See server logs and documentation.")
	log.Println("WARNING: GetNetworkMetrics returned mock values for all fields except PeerCount. This should be replaced with real metrics gathering.")
	return nil
}

// StartCapnpServer starts the Cap'n Proto RPC server
func StartCapnpServer(store *NodeStore, network NetworkAdapter, shmMgr *SharedMemoryManager, address string) error {
	listener, err := net.Listen("tcp", address)
	if err != nil {
		return fmt.Errorf("failed to listen on %s: %w", address, err)
	}

	log.Printf("Cap'n Proto server listening on %s", address)

	for {
		conn, err := listener.Accept()
		if err != nil {
			log.Printf("Error accepting connection: %v", err)
			continue
		}

		go handleCapnpConnection(conn, store, network, shmMgr)
	}
}

func handleCapnpConnection(conn net.Conn, store *NodeStore, network NetworkAdapter, shmMgr *SharedMemoryManager) {
	defer conn.Close()

	transport := rpc.NewStreamTransport(conn)
	defer transport.Close()

	// Create the service implementation
	serviceImpl := NewNodeServiceServer(store, network, shmMgr)

	// Create RPC connection with our service as bootstrap
	// NodeService_ServerToClient returns a NodeService which is a capnp.Client
	bootstrapClient := NodeService_ServerToClient(serviceImpl)
	conn_rpc := rpc.NewConn(transport, &rpc.Options{
		BootstrapClient: capnp.Client(bootstrapClient),
	})
	defer conn_rpc.Close()

	<-conn_rpc.Done()
}

// WriteToSharedMemory writes data to shared memory and returns the offset
// Python can call this to efficiently transfer large data (shards, messages)
func (s *nodeServiceServer) WriteToSharedMemory(ringName string, data []byte) (uint64, error) {
	ring, ok := s.shmMgr.GetRing(ringName)
	if !ok {
		// Create ring on first use (16MB default)
		var err error
		ring, err = s.shmMgr.CreateRing(ringName, 16*1024*1024)
		if err != nil {
			return 0, fmt.Errorf("failed to create shared memory ring: %w", err)
		}
	}
	return ring.Write(data)
}

// ReadFromSharedMemory reads data from shared memory at the given offset
func (s *nodeServiceServer) ReadFromSharedMemory(ringName string, offset uint64) ([]byte, error) {
	ring, ok := s.shmMgr.GetRing(ringName)
	if !ok {
		return nil, fmt.Errorf("shared memory ring %s not found", ringName)
	}
	return ring.ReadAt(offset)
}

// CesProcess implements the cesProcess method - Compress, Encrypt, Shard
func (s *nodeServiceServer) CesProcess(ctx context.Context, call NodeService_cesProcess) error {
	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	args := call.Args()
	request, err := args.Request()
	if err != nil {
		return err
	}

	// Get input data
	data, err := request.Data()
	if err != nil {
		return err
	}
	compressionLevel := request.CompressionLevel()

	// Create CES pipeline
	pipeline := NewCESPipeline(int(compressionLevel))
	if pipeline == nil {
		response, err := results.NewResponse()
		if err != nil {
			return err
		}
		response.SetSuccess(false)
		response.SetErrorMsg("Failed to create CES pipeline")
		return nil
	}
	defer pipeline.Close()

	// Process through CES pipeline
	shards, err := pipeline.Process(data)
	if err != nil {
		response, err := results.NewResponse()
		if err != nil {
			return err
		}
		response.SetSuccess(false)
		response.SetErrorMsg(fmt.Sprintf("CES processing failed: %v", err))
		return nil
	}

	// Build response
	response, err := results.NewResponse()
	if err != nil {
		return err
	}
	response.SetSuccess(true)

	// Create shards list
	seg := results.Segment()
	shardsList, err := NewShard_List(seg, int32(len(shards)))
	if err != nil {
		return err
	}

	for i, shard := range shards {
		shardMsg := shardsList.At(i)
		shardMsg.SetIndex(uint32(i))
		err = shardMsg.SetData(shard.Data)
		if err != nil {
			return err
		}
	}

	response.SetShards(shardsList)
	return nil
}

// CesReconstruct implements the cesReconstruct method - reverse CES pipeline
func (s *nodeServiceServer) CesReconstruct(ctx context.Context, call NodeService_cesReconstruct) error {
	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	args := call.Args()
	request, err := args.Request()
	if err != nil {
		return err
	}

	// Get input shards
	shardsList, err := request.Shards()
	if err != nil {
		return err
	}
	
	presentList, err := request.ShardPresent()
	if err != nil {
		return err
	}
	
	compressionLevel := request.CompressionLevel()

	// Convert to Go shards
	shardCount := shardsList.Len()
	shards := make([]ShardData, shardCount)
	present := make([]bool, shardCount)

	for i := 0; i < shardCount; i++ {
		shardMsg := shardsList.At(i)
		data, err := shardMsg.Data()
		if err != nil {
			continue
		}
		shards[i] = ShardData{Data: data}
		present[i] = presentList.At(i)
	}

	// Create CES pipeline
	pipeline := NewCESPipeline(int(compressionLevel))
	if pipeline == nil {
		response, err := results.NewResponse()
		if err != nil {
			return err
		}
		response.SetSuccess(false)
		response.SetErrorMsg("Failed to create CES pipeline")
		return nil
	}
	defer pipeline.Close()

	// Reconstruct data
	data, err := pipeline.Reconstruct(shards, present)
	if err != nil {
		response, err := results.NewResponse()
		if err != nil {
			return err
		}
		response.SetSuccess(false)
		response.SetErrorMsg(fmt.Sprintf("CES reconstruction failed: %v", err))
		return nil
	}

	// Build response
	response, err := results.NewResponse()
	if err != nil {
		return err
	}
	response.SetSuccess(true)
	response.SetData(data)

	return nil
}

// Upload implements the upload method - high-level CES + distribute
func (s *nodeServiceServer) Upload(ctx context.Context, call NodeService_upload) error {
	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	args := call.Args()
	request, err := args.Request()
	if err != nil {
		return err
	}

	// Get input data
	data, err := request.Data()
	if err != nil {
		return err
	}

	targetPeersList, err := request.TargetPeers()
	if err != nil {
		return err
	}

	targetPeers := make([]uint32, targetPeersList.Len())
	for i := 0; i < targetPeersList.Len(); i++ {
		targetPeers[i] = targetPeersList.At(i)
	}

	// Create CES pipeline with adaptive compression
	pipeline := NewCESPipeline(3) // Default compression level
	if pipeline == nil {
		response, err := results.NewResponse()
		if err != nil {
			return err
		}
		response.SetSuccess(false)
		response.SetErrorMsg("Failed to create CES pipeline")
		return nil
	}
	defer pipeline.Close()

	// Process through CES
	shards, err := pipeline.Process(data)
	if err != nil {
		response, err := results.NewResponse()
		if err != nil {
			return err
		}
		response.SetSuccess(false)
		response.SetErrorMsg(fmt.Sprintf("CES processing failed: %v", err))
		return nil
	}

	// Distribute shards to peers
	shardLocations := make([][2]uint32, len(shards)) // [shardIndex, peerID]
	for i, shard := range shards {
		peerID := targetPeers[i%len(targetPeers)]
		
		// Send shard to peer
		err := s.network.SendMessage(peerID, shard.Data)
		if err != nil {
			log.Printf("Warning: Failed to send shard %d to peer %d: %v", i, peerID, err)
			// Continue - Reed-Solomon allows some failures
		}
		
		shardLocations[i] = [2]uint32{uint32(i), peerID}
	}

	// Build manifest
	// Calculate file hash (simple for now)
	fileHash := fmt.Sprintf("%x", data[:32])
	if len(data) < 32 {
		fileHash = fmt.Sprintf("%x", data)
	}

	response, err := results.NewResponse()
	if err != nil {
		return err
	}
	response.SetSuccess(true)

	manifest, err := response.NewManifest()
	if err != nil {
		return err
	}
	manifest.SetFileHash(fileHash)
	manifest.SetFileName("uploaded_file")
	manifest.SetFileSize(uint64(len(data)))
	manifest.SetShardCount(uint32(len(shards)))
	manifest.SetParityCount(4) // From CES config
	manifest.SetTimestamp(0)   // TODO: Add timestamp
	manifest.SetTtl(0)

	// Set shard locations
	seg := results.Segment()
	locationsList, err := NewShardLocation_List(seg, int32(len(shardLocations)))
	if err != nil {
		return err
	}

	for i, loc := range shardLocations {
		locMsg := locationsList.At(i)
		locMsg.SetShardIndex(loc[0])
		locMsg.SetPeerId(loc[1])
	}

	manifest.SetShardLocations(locationsList)

	return nil
}

// Download implements the download method - fetch shards + CES reconstruct
func (s *nodeServiceServer) Download(ctx context.Context, call NodeService_download) error {
	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	args := call.Args()
	request, err := args.Request()
	if err != nil {
		return err
	}

	// Get shard locations
	shardLocationsList, err := request.ShardLocations()
	if err != nil {
		return err
	}

	// TODO: Implement actual shard fetching from peers
	// For now, return error indicating not fully implemented
	response, err := results.NewResponse()
	if err != nil {
		return err
	}
	response.SetSuccess(false)
	response.SetErrorMsg("Download not yet fully implemented - needs peer shard fetching")
	response.SetBytesDownloaded(0)

	log.Printf("Download requested for %d shard locations", shardLocationsList.Len())

	return nil
}
