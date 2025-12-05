package main

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"sync"
	"time"

	"github.com/libp2p/go-libp2p/core/host"
	"github.com/libp2p/go-libp2p/core/network"
	"github.com/libp2p/go-libp2p/core/peer"
	"github.com/libp2p/go-libp2p/core/protocol"

	"github.com/pangea-net/go-node/pkg/compute"
)

const (
	// ComputeProtocolID is the libp2p protocol for distributed compute
	ComputeProtocolID = "/pangea/compute/1.0.0"

	// Message types for compute protocol
	MsgTypeTaskRequest  uint8 = 1
	MsgTypeTaskResponse uint8 = 2
	MsgTypeCapacity     uint8 = 3
)

// ComputeProtocol handles distributed compute over libp2p
type ComputeProtocol struct {
	host        host.Host
	manager     *compute.Manager
	workers     map[peer.ID]*WorkerInfo
	mu          sync.RWMutex
	ctx         context.Context
	cancel      context.CancelFunc
	localNodeID uint32
}

// WorkerInfo tracks information about a compute worker
type WorkerInfo struct {
	PeerID      peer.ID
	Capacity    compute.ComputeCapacity
	ActiveTasks int
	LastSeen    time.Time
	TrustScore  float32
}

// TaskRequest is sent to a worker to execute a compute task
type TaskRequest struct {
	TaskID       string `json:"taskId"`
	ParentJobID  string `json:"parentJobId"`
	ChunkIndex   uint32 `json:"chunkIndex"`
	InputData    []byte `json:"inputData"`
	FunctionName string `json:"functionName"`
	TimeoutMs    uint64 `json:"timeoutMs"`
}

// TaskResponse is returned by a worker after executing a task
type TaskResponse struct {
	TaskID          string   `json:"taskId"`
	Success         bool     `json:"success"`
	ResultData      []byte   `json:"resultData"`
	ResultHash      string   `json:"resultHash"`
	MerkleProof     []string `json:"merkleProof,omitempty"`
	ExecutionTimeMs uint64   `json:"executionTimeMs"`
	Error           string   `json:"error,omitempty"`
}

// NewComputeProtocol creates a new compute protocol handler
func NewComputeProtocol(h host.Host, manager *compute.Manager, nodeID uint32) *ComputeProtocol {
	ctx, cancel := context.WithCancel(context.Background())

	cp := &ComputeProtocol{
		host:        h,
		manager:     manager,
		workers:     make(map[peer.ID]*WorkerInfo),
		ctx:         ctx,
		cancel:      cancel,
		localNodeID: nodeID,
	}

	// Register stream handler for compute protocol
	h.SetStreamHandler(protocol.ID(ComputeProtocolID), cp.handleStream)

	log.Printf("⚙️ [COMPUTE] Protocol registered: %s", ComputeProtocolID)

	return cp
}

// handleStream handles incoming compute protocol streams
func (cp *ComputeProtocol) handleStream(s network.Stream) {
	defer s.Close()

	remotePeer := s.Conn().RemotePeer()
	log.Printf("📥 [COMPUTE] Incoming stream from %s", remotePeer.String()[:12])

	// Read message type
	msgType := make([]byte, 1)
	if _, err := io.ReadFull(s, msgType); err != nil {
		log.Printf("❌ [COMPUTE] Failed to read message type: %v", err)
		return
	}

	switch msgType[0] {
	case MsgTypeTaskRequest:
		cp.handleTaskRequest(s, remotePeer)
	case MsgTypeCapacity:
		cp.handleCapacityRequest(s, remotePeer)
	default:
		log.Printf("❌ [COMPUTE] Unknown message type: %d", msgType[0])
	}
}

// handleTaskRequest handles an incoming compute task
func (cp *ComputeProtocol) handleTaskRequest(s network.Stream, from peer.ID) {
	// Read request length
	lengthBuf := make([]byte, 4)
	if _, err := io.ReadFull(s, lengthBuf); err != nil {
		log.Printf("❌ [COMPUTE] Failed to read request length: %v", err)
		return
	}
	length := binary.BigEndian.Uint32(lengthBuf)

	// Read request data
	reqData := make([]byte, length)
	if _, err := io.ReadFull(s, reqData); err != nil {
		log.Printf("❌ [COMPUTE] Failed to read request data: %v", err)
		return
	}

	// Parse request
	var req TaskRequest
	if err := json.Unmarshal(reqData, &req); err != nil {
		log.Printf("❌ [COMPUTE] Failed to parse task request: %v", err)
		return
	}

	log.Printf("🔧 [COMPUTE] Received task %s (chunk %d, %d bytes) from %s",
		req.TaskID, req.ChunkIndex, len(req.InputData), from.String()[:12])

	// Execute the compute task
	startTime := time.Now()
	response := cp.executeTask(&req)
	response.ExecutionTimeMs = uint64(time.Since(startTime).Milliseconds())

	log.Printf("✅ [COMPUTE] Task %s completed in %dms (result: %d bytes)",
		req.TaskID, response.ExecutionTimeMs, len(response.ResultData))

	// Send response
	respData, err := json.Marshal(response)
	if err != nil {
		log.Printf("❌ [COMPUTE] Failed to marshal response: %v", err)
		return
	}

	// Write response type + length + data
	respBuf := bytes.NewBuffer(nil)
	respBuf.WriteByte(MsgTypeTaskResponse)
	binary.Write(respBuf, binary.BigEndian, uint32(len(respData)))
	respBuf.Write(respData)

	if _, err := s.Write(respBuf.Bytes()); err != nil {
		log.Printf("❌ [COMPUTE] Failed to send response: %v", err)
	}
}

// executeTask executes a compute task locally
func (cp *ComputeProtocol) executeTask(req *TaskRequest) *TaskResponse {
	response := &TaskResponse{
		TaskID:  req.TaskID,
		Success: false,
	}

	// Execute matrix block multiplication
	result, err := compute.ExecuteMatrixBlockMultiply(req.InputData)
	if err != nil {
		response.Error = err.Error()
		log.Printf("❌ [COMPUTE] Task execution failed: %v", err)
		return response
	}

	// Calculate hash of result
	hash := sha256.Sum256(result)
	response.ResultHash = hex.EncodeToString(hash[:])
	response.ResultData = result
	response.Success = true

	return response
}

// handleCapacityRequest responds with this node's compute capacity
func (cp *ComputeProtocol) handleCapacityRequest(s network.Stream, from peer.ID) {
	capacity := cp.manager.GetCapacity()

	respData, err := json.Marshal(capacity)
	if err != nil {
		log.Printf("❌ [COMPUTE] Failed to marshal capacity: %v", err)
		return
	}

	// Write response
	respBuf := bytes.NewBuffer(nil)
	respBuf.WriteByte(MsgTypeCapacity)
	binary.Write(respBuf, binary.BigEndian, uint32(len(respData)))
	respBuf.Write(respData)

	s.Write(respBuf.Bytes())
}

// SendTask sends a compute task to a remote worker
func (cp *ComputeProtocol) SendTask(ctx context.Context, workerPeer peer.ID, task *TaskRequest) (*TaskResponse, error) {
	log.Printf("📤 [COMPUTE] Sending task %s to %s", task.TaskID, workerPeer.String()[:12])

	// Open stream to worker
	s, err := cp.host.NewStream(ctx, workerPeer, protocol.ID(ComputeProtocolID))
	if err != nil {
		return nil, fmt.Errorf("failed to open stream to %s: %w", workerPeer.String()[:12], err)
	}
	defer s.Close()

	// Marshal task request
	reqData, err := json.Marshal(task)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal task: %w", err)
	}

	// Write request: type + length + data
	reqBuf := bytes.NewBuffer(nil)
	reqBuf.WriteByte(MsgTypeTaskRequest)
	binary.Write(reqBuf, binary.BigEndian, uint32(len(reqData)))
	reqBuf.Write(reqData)

	if _, err := s.Write(reqBuf.Bytes()); err != nil {
		return nil, fmt.Errorf("failed to send task: %w", err)
	}

	// Read response type
	respType := make([]byte, 1)
	if _, err := io.ReadFull(s, respType); err != nil {
		return nil, fmt.Errorf("failed to read response type: %w", err)
	}

	if respType[0] != MsgTypeTaskResponse {
		return nil, fmt.Errorf("unexpected response type: %d", respType[0])
	}

	// Read response length
	lengthBuf := make([]byte, 4)
	if _, err := io.ReadFull(s, lengthBuf); err != nil {
		return nil, fmt.Errorf("failed to read response length: %w", err)
	}
	length := binary.BigEndian.Uint32(lengthBuf)

	// Read response data
	respData := make([]byte, length)
	if _, err := io.ReadFull(s, respData); err != nil {
		return nil, fmt.Errorf("failed to read response data: %w", err)
	}

	// Parse response
	var resp TaskResponse
	if err := json.Unmarshal(respData, &resp); err != nil {
		return nil, fmt.Errorf("failed to parse response: %w", err)
	}

	log.Printf("📥 [COMPUTE] Received result for task %s (success=%t, %d bytes)",
		task.TaskID, resp.Success, len(resp.ResultData))

	return &resp, nil
}

// RegisterWorker registers a peer as a compute worker
func (cp *ComputeProtocol) RegisterWorker(peerID peer.ID, capacity compute.ComputeCapacity) {
	cp.mu.Lock()
	defer cp.mu.Unlock()

	cp.workers[peerID] = &WorkerInfo{
		PeerID:     peerID,
		Capacity:   capacity,
		LastSeen:   time.Now(),
		TrustScore: 1.0,
	}

	// Also register with the manager so jobs get delegated
	if cp.manager != nil {
		cp.manager.RegisterWorker(peerID.String(), capacity)
		log.Printf("👷 [COMPUTE] Registered worker with manager: %s", peerID.String()[:12])
	}

	log.Printf("👷 [COMPUTE] Registered worker: %s (CPUs: %d, RAM: %dMB)",
		peerID.String()[:12], capacity.CPUCores, capacity.RAMMB)
}

// GetAvailableWorkerPeers returns a list of available compute worker peer IDs
func (cp *ComputeProtocol) GetAvailableWorkerPeers() []peer.ID {
	cp.mu.RLock()
	defer cp.mu.RUnlock()

	// Get all connected peers as potential workers
	workers := cp.host.Network().Peers()
	return workers
}

// ===== TaskDelegator Interface Implementation =====

// DelegateTask sends a task to a remote worker and returns the result
// Implements compute.TaskDelegator interface
func (cp *ComputeProtocol) DelegateTask(ctx context.Context, workerID string, task *compute.ComputeTask) (*compute.TaskResult, error) {
	// Parse peer ID from string
	peerID, err := peer.Decode(workerID)
	if err != nil {
		return nil, fmt.Errorf("invalid worker ID: %w", err)
	}

	// Convert compute.ComputeTask to TaskRequest
	req := &TaskRequest{
		TaskID:       task.TaskID,
		ParentJobID:  task.ParentJobID,
		ChunkIndex:   task.ChunkIndex,
		InputData:    task.InputData,
		FunctionName: task.FunctionName,
		TimeoutMs:    task.TimeoutMs,
	}

	// Send task and get response
	resp, err := cp.SendTask(ctx, peerID, req)
	if err != nil {
		return nil, err
	}

	// Convert TaskResponse to compute.TaskResult
	result := &compute.TaskResult{
		TaskID:          resp.TaskID,
		ResultData:      resp.ResultData,
		ResultHash:      resp.ResultHash,
		MerkleProof:     resp.MerkleProof,
		ExecutionTimeMs: resp.ExecutionTimeMs,
		WorkerID:        workerID,
	}

	if resp.Success {
		result.Status = compute.TaskCompleted
	} else {
		result.Status = compute.TaskFailed
		result.Error = resp.Error
	}

	return result, nil
}

// GetAvailableWorkers returns a list of available worker IDs as strings
// Implements compute.TaskDelegator interface
func (cp *ComputeProtocol) GetAvailableWorkers() []string {
	peers := cp.GetAvailableWorkerPeers()
	workers := make([]string, len(peers))
	for i, p := range peers {
		workers[i] = p.String()
	}
	return workers
}

// HasWorkers returns true if there are remote workers available
// Implements compute.TaskDelegator interface
func (cp *ComputeProtocol) HasWorkers() bool {
	peers := cp.host.Network().Peers()
	return len(peers) > 0
}

// Close shuts down the compute protocol
func (cp *ComputeProtocol) Close() {
	cp.cancel()
	cp.host.RemoveStreamHandler(protocol.ID(ComputeProtocolID))
}
