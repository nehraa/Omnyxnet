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
	"time"

	"capnproto.org/go/capnp/v3"
	"capnproto.org/go/capnp/v3/rpc"
	"github.com/pangea-net/go-node/pkg/compute"
)

// nodeServiceServer implements the Cap'n Proto NodeService interface
// Note: NodeService_Server interface is generated in schema.capnp.go
type nodeServiceServer struct {
	store            *NodeStore
	network          NetworkAdapter
	shmMgr           *SharedMemoryManager
	streamingService *StreamingService
	streamStats      *StreamingStats
	peerAddr         *net.UDPAddr // Current streaming peer address
	computeManager   *compute.Manager
	cesPipeline      *CESPipeline // Shared CES pipeline for consistent encryption
}

// NewNodeServiceServer creates a new NodeService server
func NewNodeServiceServer(store *NodeStore, network NetworkAdapter, shmMgr *SharedMemoryManager) NodeService_Server {
	return NewNodeServiceServerWithManager(store, network, shmMgr, nil)
}

// NewNodeServiceServerWithManager creates a new NodeService server with an external compute manager
func NewNodeServiceServerWithManager(store *NodeStore, network NetworkAdapter, shmMgr *SharedMemoryManager, manager *compute.Manager) NodeService_Server {
	// Create a shared CES pipeline with default compression level 3
	// This ensures the same encryption key is used across process and reconstruct
	cesPipeline := NewCESPipeline(3)
	if cesPipeline == nil {
		log.Printf("WARNING: Failed to create shared CES pipeline")
	}

	if manager == nil {
		manager = compute.NewManager(compute.DefaultConfig())
	}

	return &nodeServiceServer{
		store:          store,
		network:        network,
		shmMgr:         shmMgr,
		streamStats:    &StreamingStats{},
		computeManager: manager,
		cesPipeline:    cesPipeline,
	}
}

// GetComputeManager returns the compute manager for external integration
func (s *nodeServiceServer) GetComputeManager() *compute.Manager {
	return s.computeManager
}

// Error Handling Convention for Cap'n Proto RPC methods:
// - Return Go error for internal/allocation failures (RPC fails)
// - For application-level errors where response has success/errorMsg fields,
//   set success=false, errorMsg=description, and return nil (RPC succeeds with error info)
// - For simple query methods without success fields, return Go error (client handles as RPC error)

// GetNode implements the getNode method
// Returns Go error if node not found (propagates as RPC error to client)
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

	metrics, err := results.NewMetrics()
	if err != nil {
		return err
	}

	// Get real peer count
	connectedPeers := s.network.GetConnectedPeers()
	peerCount := uint32(len(connectedPeers))
	metrics.SetPeerCount(peerCount)

	// Calculate average RTT from connected peers
	var totalLatency float32
	var latencyCount int
	for _, peerID := range connectedPeers {
		latency, _, packetLoss, err := s.network.GetConnectionQuality(peerID)
		if err == nil && latency > 0 {
			totalLatency += latency
			latencyCount++
			// Use actual packet loss if available
			if packetLoss > 0 {
				metrics.SetPacketLoss(packetLoss)
			}
		}
	}

	if latencyCount > 0 {
		metrics.SetAvgRttMs(totalLatency / float32(latencyCount))
	} else {
		metrics.SetAvgRttMs(0.0)
	}

	// Set packet loss to 0 if no measurements available
	if metrics.PacketLoss() == 0 && peerCount > 0 {
		metrics.SetPacketLoss(0.0)
	}

	// Bandwidth estimation requires active measurement - use conservative estimate based on peer count
	// More peers typically means more available network capacity
	estimatedBandwidth := float32(10.0) // Base 10 Mbps
	if peerCount > 0 {
		estimatedBandwidth = float32(peerCount) * 10.0 // Scale with peer count
		if estimatedBandwidth > 1000.0 {
			estimatedBandwidth = 1000.0 // Cap at 1 Gbps
		}
	}
	metrics.SetBandwidthMbps(estimatedBandwidth)

	// CPU usage from compute manager if available
	if s.computeManager != nil {
		capacity := s.computeManager.GetCapacity()
		metrics.SetCpuUsage(capacity.CurrentLoad)
		// IO capacity based on load (inverse relationship)
		metrics.SetIoCapacity(1.0 - capacity.CurrentLoad)
	} else {
		metrics.SetCpuUsage(0.0)
		metrics.SetIoCapacity(1.0)
	}

	return nil
}

// StartCapnpServer starts the Cap'n Proto RPC server
func StartCapnpServer(store *NodeStore, network NetworkAdapter, shmMgr *SharedMemoryManager, address string) error {
	return StartCapnpServerWithManager(store, network, shmMgr, address, nil)
}

// StartCapnpServerWithManager starts the Cap'n Proto RPC server with an external compute manager
func StartCapnpServerWithManager(store *NodeStore, network NetworkAdapter, shmMgr *SharedMemoryManager, address string, manager *compute.Manager) error {
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

		go handleCapnpConnectionWithManager(conn, store, network, shmMgr, manager)
	}
}

func handleCapnpConnection(conn net.Conn, store *NodeStore, network NetworkAdapter, shmMgr *SharedMemoryManager) {
	handleCapnpConnectionWithManager(conn, store, network, shmMgr, nil)
}

func handleCapnpConnectionWithManager(conn net.Conn, store *NodeStore, network NetworkAdapter, shmMgr *SharedMemoryManager, manager *compute.Manager) {
	defer conn.Close()

	transport := rpc.NewStreamTransport(conn)
	defer transport.Close()

	// Create the service implementation
	serviceImpl := NewNodeServiceServerWithManager(store, network, shmMgr, manager)

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
	// Note: compressionLevel from request is currently ignored - using shared pipeline's level

	// Use shared CES pipeline for consistent encryption
	if s.cesPipeline == nil {
		response, err := results.NewResponse()
		if err != nil {
			return err
		}
		response.SetSuccess(false)
		response.SetErrorMsg("CES pipeline not initialized")
		return nil
	}

	// Process through CES pipeline
	shards, err := s.cesPipeline.Process(data)
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

	// Note: compressionLevel from request is currently ignored - using shared pipeline's level

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

	// Use shared CES pipeline for consistent encryption
	if s.cesPipeline == nil {
		response, err := results.NewResponse()
		if err != nil {
			return err
		}
		response.SetSuccess(false)
		response.SetErrorMsg("CES pipeline not initialized")
		return nil
	}

	// Reconstruct data
	data, err := s.cesPipeline.Reconstruct(shards, present)
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

	// Use shared CES pipeline for consistent encryption key management
	// This ensures the same key is used for encryption and decryption
	if s.cesPipeline == nil {
		response, err := results.NewResponse()
		if err != nil {
			return err
		}
		response.SetSuccess(false)
		response.SetErrorMsg("CES pipeline not initialized - encryption key would be inconsistent")
		return nil
	}

	// Process through shared CES pipeline
	shards, err := s.cesPipeline.Process(data)
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
	var fileHash string
	if len(data) >= 32 {
		fileHash = fmt.Sprintf("%x", data[:32])
	} else {
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
	// Set default filename (UploadRequest doesn't include fileName field)
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

	shardCount := shardLocationsList.Len()
	log.Printf("Download requested for %d shard locations", shardCount)

	// Fetch shards from peers
	shards := make([]ShardData, shardCount)
	present := make([]bool, shardCount)

	for i := 0; i < shardCount; i++ {
		loc := shardLocationsList.At(i)
		shardIndex := loc.ShardIndex()
		peerID := loc.PeerId()

		// Fetch shard from peer using network layer
		log.Printf("Fetching shard %d from peer %d", shardIndex, peerID)
		shardData, err := s.network.FetchShard(peerID, shardIndex)
		if err != nil {
			log.Printf("Warning: Failed to fetch shard %d from peer %d: %v", shardIndex, peerID, err)
			present[i] = false
			shards[i] = ShardData{Data: nil}
			continue
		}

		present[i] = true
		shards[i] = ShardData{Data: shardData}
		log.Printf("Successfully fetched shard %d (%d bytes)", shardIndex, len(shardData))
	}

	// Check if we have enough shards to reconstruct
	presentCount := 0
	for _, p := range present {
		if p {
			presentCount++
		}
	}

	response, err := results.NewResponse()
	if err != nil {
		return err
	}

	// Need at least K shards to reconstruct (K = dataShards from Reed-Solomon)
	// With 8 data + 4 parity shards, we need at least 8
	minRequired := 8 // TODO: Get this from CES config
	if presentCount < minRequired {
		response.SetSuccess(false)
		response.SetErrorMsg(fmt.Sprintf("Insufficient shards: have %d, need at least %d", presentCount, minRequired))
		response.SetBytesDownloaded(0)
		return nil
	}

	// Create CES pipeline for reconstruction
	pipeline := NewCESPipeline(3)
	if pipeline == nil {
		response.SetSuccess(false)
		response.SetErrorMsg("Failed to create CES pipeline")
		response.SetBytesDownloaded(0)
		return nil
	}
	defer pipeline.Close()

	// Reconstruct data from shards
	reconstructed, err := pipeline.Reconstruct(shards, present)
	if err != nil {
		response.SetSuccess(false)
		response.SetErrorMsg(fmt.Sprintf("CES reconstruction failed: %v", err))
		response.SetBytesDownloaded(0)
		return nil
	}

	// Return reconstructed data
	response.SetSuccess(true)
	response.SetData(reconstructed)
	response.SetBytesDownloaded(uint64(len(reconstructed)))

	log.Printf("Successfully reconstructed %d bytes from %d shards", len(reconstructed), presentCount)

	return nil
}

// ============================================================================
// Streaming Services (Go handles all networking per Golden Rule)
// ============================================================================

// StartStreaming implements the startStreaming method
func (s *nodeServiceServer) StartStreaming(ctx context.Context, call NodeService_startStreaming) error {
	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	args := call.Args()
	config, err := args.Config()
	if err != nil {
		return err
	}

	port := config.Port()
	peerHost, err := config.PeerHost()
	if err != nil {
		return err
	}
	peerPort := config.PeerPort()
	streamType := config.StreamType()

	// Create streaming service if not exists
	if s.streamingService == nil {
		streamConfig := DefaultGoStreamConfig()
		s.streamingService = NewStreamingService(streamConfig)
	}

	// Start UDP for video/audio
	if streamType == 0 || streamType == 1 { // video or audio
		err = s.streamingService.StartUDP(int(port))
		if err != nil {
			results.SetSuccess(false)
			results.SetErrorMsg(fmt.Sprintf("Failed to start UDP: %v", err))
			return nil
		}
	}

	// Start TCP for chat
	if streamType == 2 { // chat
		err = s.streamingService.StartTCP(int(port))
		if err != nil {
			results.SetSuccess(false)
			results.SetErrorMsg(fmt.Sprintf("Failed to start TCP: %v", err))
			return nil
		}
	}

	// Store peer address if provided
	if peerHost != "" && peerPort > 0 {
		s.peerAddr, err = s.streamingService.GetPeerAddress(peerHost, int(peerPort))
		if err != nil {
			log.Printf("Warning: Failed to resolve peer address: %v", err)
		}
	}

	log.Printf("🎥 Streaming started on port %d for type %d", port, streamType)
	results.SetSuccess(true)
	results.SetErrorMsg("")
	return nil
}

// StopStreaming implements the stopStreaming method
func (s *nodeServiceServer) StopStreaming(ctx context.Context, call NodeService_stopStreaming) error {
	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	if s.streamingService != nil {
		s.streamingService.Stop()
		s.streamingService = nil
	}

	log.Printf("🛑 Streaming stopped")
	results.SetSuccess(true)
	return nil
}

// SendVideoFrame implements the sendVideoFrame method
func (s *nodeServiceServer) SendVideoFrame(ctx context.Context, call NodeService_sendVideoFrame) error {
	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	if s.streamingService == nil || s.peerAddr == nil {
		results.SetSuccess(false)
		return nil
	}

	args := call.Args()
	frame, err := args.Frame()
	if err != nil {
		results.SetSuccess(false)
		return nil
	}

	frameID := frame.FrameId()
	data, err := frame.Data()
	if err != nil {
		results.SetSuccess(false)
		return nil
	}

	// Send via Go's UDP (handles fragmentation for large frames)
	err = s.streamingService.SendVideoFrame(s.peerAddr, frameID, data)
	if err != nil {
		log.Printf("Failed to send video frame: %v", err)
		results.SetSuccess(false)
		return nil
	}

	s.streamStats.RecordSent(len(data))
	results.SetSuccess(true)
	return nil
}

// SendAudioChunk implements the sendAudioChunk method
func (s *nodeServiceServer) SendAudioChunk(ctx context.Context, call NodeService_sendAudioChunk) error {
	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	if s.streamingService == nil || s.peerAddr == nil {
		results.SetSuccess(false)
		return nil
	}

	args := call.Args()
	chunk, err := args.Chunk()
	if err != nil {
		results.SetSuccess(false)
		return nil
	}

	data, err := chunk.Data()
	if err != nil {
		results.SetSuccess(false)
		return nil
	}

	// Send via Go's UDP
	err = s.streamingService.SendAudioChunk(s.peerAddr, data)
	if err != nil {
		log.Printf("Failed to send audio chunk: %v", err)
		results.SetSuccess(false)
		return nil
	}

	s.streamStats.RecordSent(len(data))
	results.SetSuccess(true)
	return nil
}

// SendChatMessage implements the sendChatMessage method
func (s *nodeServiceServer) SendChatMessage(ctx context.Context, call NodeService_sendChatMessage) error {
	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	if s.streamingService == nil {
		results.SetSuccess(false)
		return nil
	}

	args := call.Args()
	chatMsg, err := args.Message_()
	if err != nil {
		results.SetSuccess(false)
		return nil
	}

	peerAddr, err := chatMsg.PeerAddr()
	if err != nil {
		results.SetSuccess(false)
		return nil
	}

	message, err := chatMsg.Message_()
	if err != nil {
		results.SetSuccess(false)
		return nil
	}

	// Send via Go's TCP
	err = s.streamingService.SendChatMessage(peerAddr, message)
	if err != nil {
		log.Printf("Failed to send chat message: %v", err)
		results.SetSuccess(false)
		return nil
	}

	results.SetSuccess(true)
	return nil
}

// ConnectStreamPeer implements the connectStreamPeer method
func (s *nodeServiceServer) ConnectStreamPeer(ctx context.Context, call NodeService_connectStreamPeer) error {
	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	if s.streamingService == nil {
		results.SetSuccess(false)
		results.SetPeerAddr("")
		return nil
	}

	args := call.Args()
	host, err := args.Host()
	if err != nil {
		results.SetSuccess(false)
		return nil
	}
	port := args.Port()

	// Connect via TCP for chat
	err = s.streamingService.ConnectTCPPeer(host, int(port))
	if err != nil {
		log.Printf("Failed to connect to stream peer: %v", err)
		results.SetSuccess(false)
		results.SetPeerAddr("")
		return nil
	}

	// Also store UDP address for video/audio
	s.peerAddr, err = s.streamingService.GetPeerAddress(host, int(port))
	if err != nil {
		log.Printf("Warning: Failed to resolve UDP peer address: %v", err)
	}

	peerAddrStr := fmt.Sprintf("%s:%d", host, port)
	results.SetSuccess(true)
	results.SetPeerAddr(peerAddrStr)
	return nil
}

// GetStreamStats implements the getStreamStats method
func (s *nodeServiceServer) GetStreamStats(ctx context.Context, call NodeService_getStreamStats) error {
	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	stats, err := results.NewStats()
	if err != nil {
		return err
	}

	if s.streamStats != nil {
		framesSent, framesRecv, bytesSent, bytesRecv := s.streamStats.GetStats()
		stats.SetFramesSent(framesSent)
		stats.SetFramesReceived(framesRecv)
		stats.SetBytesSent(bytesSent)
		stats.SetBytesReceived(bytesRecv)
		stats.SetAvgLatencyMs(0.0) // TODO: Calculate actual latency
	}

	return nil
}

// ============================================================================
// Distributed Compute Services
// ============================================================================

// SubmitComputeJob implements the submitComputeJob method
func (s *nodeServiceServer) SubmitComputeJob(ctx context.Context, call NodeService_submitComputeJob) error {
	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	args := call.Args()
	manifest, err := args.Manifest()
	if err != nil {
		results.SetSuccess(false)
		results.SetErrorMsg(fmt.Sprintf("Failed to get manifest: %v", err))
		return nil
	}

	// Extract manifest fields
	jobID, _ := manifest.JobId()
	wasmModule, _ := manifest.WasmModule()
	inputDataRef, _ := manifest.InputData()
	minChunkSize := manifest.MinChunkSize()
	maxChunkSize := manifest.MaxChunkSize()
	timeoutSecs := manifest.TimeoutSecs()
	retryCount := manifest.RetryCount()
	priority := manifest.Priority()
	redundancy := manifest.Redundancy()

	// IMPORTANT: Copy input data - Cap'n Proto slices reference the message buffer
	// which gets recycled after RPC completes
	inputData := make([]byte, len(inputDataRef))
	copy(inputData, inputDataRef)

	// Debug: log first bytes of input data
	if len(inputData) > 16 {
		log.Printf("📊 [COMPUTE] Input data first 16 bytes: %x", inputData[:16])
	}

	// Create job manifest for manager
	jobManifest := &compute.JobManifest{
		JobID:            jobID,
		WASMModule:       wasmModule,
		InputData:        inputData,
		MinChunkSize:     int64(minChunkSize),
		MaxChunkSize:     int64(maxChunkSize),
		TimeoutSecs:      timeoutSecs,
		RetryCount:       retryCount,
		Priority:         priority,
		Redundancy:       redundancy,
		VerificationMode: compute.VerificationHash,
	}

	// Submit job
	log.Printf("📤 [COMPUTE] Received job submission: %s (input size: %d bytes)", jobID, len(inputData))
	submittedJobID, err := s.computeManager.SubmitJob(jobManifest)
	if err != nil {
		log.Printf("❌ [COMPUTE] Job submission failed: %v", err)
		results.SetSuccess(false)
		results.SetErrorMsg(fmt.Sprintf("Failed to submit job: %v", err))
		return nil
	}

	log.Printf("✅ [COMPUTE] Job submitted successfully: %s", submittedJobID)
	results.SetJobId(submittedJobID)
	results.SetSuccess(true)
	results.SetErrorMsg("")
	return nil
}

// GetComputeJobStatus implements the getComputeJobStatus method
func (s *nodeServiceServer) GetComputeJobStatus(ctx context.Context, call NodeService_getComputeJobStatus) error {
	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	args := call.Args()
	jobID, err := args.JobId()
	if err != nil {
		return err
	}

	// Get job status from manager
	jobStatus, err := s.computeManager.GetJobStatus(jobID)
	if err != nil {
		log.Printf("❌ [COMPUTE] Failed to get job status for %s: %v", jobID, err)
		status, _ := results.NewStatus()
		status.SetJobId(jobID)
		status.SetStatus("failed")
		status.SetErrorMsg(fmt.Sprintf("Failed to get status: %v", err))
		return nil
	}

	// Map status to string
	statusStr := jobStatus.Status.String()
	log.Printf("📊 [COMPUTE] Job %s status: %s (%.1f%% complete, %d/%d chunks)",
		jobID, statusStr, jobStatus.Progress*100, jobStatus.CompletedChunks, jobStatus.TotalChunks)

	status, err := results.NewStatus()
	if err != nil {
		return err
	}
	status.SetJobId(jobID)
	status.SetStatus(statusStr)
	status.SetProgress(jobStatus.Progress)
	status.SetCompletedChunks(jobStatus.CompletedChunks)
	status.SetTotalChunks(jobStatus.TotalChunks)
	status.SetEstimatedTimeRemaining(jobStatus.EstimatedTimeRemaining)
	status.SetErrorMsg("")

	return nil
}

// GetComputeJobResult implements the getComputeJobResult method
func (s *nodeServiceServer) GetComputeJobResult(ctx context.Context, call NodeService_getComputeJobResult) error {
	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	args := call.Args()
	jobID, err := args.JobId()
	if err != nil {
		return err
	}
	timeoutMs := args.TimeoutMs()

	log.Printf("⏳ [COMPUTE] Waiting for job result: %s (timeout: %dms)", jobID, timeoutMs)

	// Get job result from manager (blocking with timeout)
	timeout := time.Duration(timeoutMs) * time.Millisecond
	if timeout == 0 {
		timeout = 5 * time.Minute // Default timeout
	}

	result, workerID, err := s.computeManager.GetJobResultWithWorker(jobID, timeout)
	if err != nil {
		log.Printf("❌ [COMPUTE] Failed to get job result for %s: %v", jobID, err)
		results.SetSuccess(false)
		results.SetErrorMsg(fmt.Sprintf("Failed to get result: %v", err))
		return nil
	}

	// Format worker info - show IP if remote, "local" if local
	workerNode := workerID
	if workerID == "local" {
		workerNode = "local (this node)"
	} else if len(workerID) > 20 {
		// It's a peer ID, show abbreviated version
		workerNode = "remote:" + workerID[:12] + "..."
	}

	log.Printf("✅ [COMPUTE] Job %s completed by %s, result size: %d bytes", jobID, workerNode, len(result))
	results.SetResult(result)
	results.SetSuccess(true)
	results.SetErrorMsg("")
	results.SetWorkerNode(workerNode)
	return nil
}

// CancelComputeJob implements the cancelComputeJob method
func (s *nodeServiceServer) CancelComputeJob(ctx context.Context, call NodeService_cancelComputeJob) error {
	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	args := call.Args()
	jobID, err := args.JobId()
	if err != nil {
		return err
	}

	log.Printf("🛑 [COMPUTE] Cancelling job: %s", jobID)

	err = s.computeManager.CancelJob(jobID)
	if err != nil {
		log.Printf("❌ [COMPUTE] Failed to cancel job %s: %v", jobID, err)
		results.SetSuccess(false)
		return nil
	}

	log.Printf("✅ [COMPUTE] Job %s cancelled successfully", jobID)
	results.SetSuccess(true)
	return nil
}

// GetComputeCapacity implements the getComputeCapacity method
func (s *nodeServiceServer) GetComputeCapacity(ctx context.Context, call NodeService_getComputeCapacity) error {
	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	// Get capacity from manager
	cap := s.computeManager.GetCapacity()

	log.Printf("💻 [COMPUTE] Reporting capacity: %d cores, %d MB RAM, %.1f%% load",
		cap.CPUCores, cap.RAMMB, cap.CurrentLoad*100)

	capacity, err := results.NewCapacity()
	if err != nil {
		return err
	}
	capacity.SetCpuCores(cap.CPUCores)
	capacity.SetRamMb(cap.RAMMB)
	capacity.SetCurrentLoad(cap.CurrentLoad)
	capacity.SetDiskMb(cap.DiskMB)
	capacity.SetBandwidthMbps(cap.BandwidthMbps)

	return nil
}
