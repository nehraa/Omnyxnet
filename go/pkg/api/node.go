// Package api provides a high-level API for Python to interact with Go nodes.
// This package exposes simple, direct functions that Python can call via Cap'n Proto RPC.
package api

import (
	"fmt"
	"sync"
)

// NodeManager provides high-level node management functions
// This is the main interface that Python will interact with
type NodeManager struct {
	store   NodeStore
	network NetworkManager
	rpc     RPCServer
	mu      sync.RWMutex
}

// NodeStore interface for node storage operations
type NodeStore interface {
	GetNode(id uint32) (*Node, bool)
	GetAllNodes() []*Node
	UpdateLatency(nodeID uint32, latencyMs float32) bool
	UpdateThreatScore(nodeID uint32, threatScore float32) bool
	CreateNode(id uint32) *Node
}

// NetworkManager interface for network operations
type NetworkManager interface {
	ConnectToPeer(peerID uint32, address string) error
	SendMessage(peerID uint32, data []byte) error
	GetConnectionQuality(peerID uint32) (*ConnectionQuality, error)
	DisconnectPeer(peerID uint32) error
	GetConnectedPeers() []uint32
}

// RPCServer interface for RPC operations
type RPCServer interface {
	Start(address string) error
	Stop() error
}

// Node represents a network node
type Node struct {
	ID          uint32
	Status      uint32
	LatencyMs   float32
	ThreatScore float32
	JitterMs    float32
	PacketLoss  float32
}

// ConnectionQuality represents connection quality metrics
type ConnectionQuality struct {
	LatencyMs  float32
	JitterMs   float32
	PacketLoss float32
}

// NewNodeManager creates a new node manager
func NewNodeManager(store NodeStore, network NetworkManager, rpc RPCServer) *NodeManager {
	return &NodeManager{
		store:   store,
		network: network,
		rpc:     rpc,
	}
}

// StartNode starts the node with the given configuration
func (nm *NodeManager) StartNode(nodeID uint32, capnpPort string, p2pPort string) error {
	nm.mu.Lock()
	defer nm.mu.Unlock()

	// Create the node in store
	nm.store.CreateNode(nodeID)

	// Start RPC server
	if err := nm.rpc.Start(capnpPort); err != nil {
		return fmt.Errorf("failed to start RPC server: %w", err)
	}

	return nil
}

// StopNode stops the node and cleans up resources
func (nm *NodeManager) StopNode() error {
	nm.mu.Lock()
	defer nm.mu.Unlock()

	return nm.rpc.Stop()
}

// ConnectToPeer connects to a new peer (called by Python)
func (nm *NodeManager) ConnectToPeer(peerID uint32, host string, port uint16) error {
	address := fmt.Sprintf("%s:%d", host, port)
	return nm.network.ConnectToPeer(peerID, address)
}

// SendMessage sends a message to a peer (called by Python)
func (nm *NodeManager) SendMessage(toPeerID uint32, data []byte) error {
	return nm.network.SendMessage(toPeerID, data)
}

// GetNodeData gets node data by ID (called by Python)
func (nm *NodeManager) GetNodeData(nodeID uint32) (*Node, error) {
	node, exists := nm.store.GetNode(nodeID)
	if !exists {
		return nil, fmt.Errorf("node %d not found", nodeID)
	}
	return &Node{
		ID:          node.ID,
		Status:      uint32(node.Status),
		LatencyMs:   node.LatencyMs,
		ThreatScore: node.ThreatScore,
		JitterMs:    node.JitterMs,
		PacketLoss:  node.PacketLoss,
	}, nil
}

// GetAllNodesData gets all nodes data (called by Python)
func (nm *NodeManager) GetAllNodesData() []*Node {
	localNodes := nm.store.GetAllNodes()
	nodes := make([]*Node, len(localNodes))
	for i, n := range localNodes {
		nodes[i] = &Node{
			ID:          n.ID,
			Status:      uint32(n.Status),
			LatencyMs:   n.LatencyMs,
			ThreatScore: n.ThreatScore,
			JitterMs:    n.JitterMs,
			PacketLoss:  n.PacketLoss,
		}
	}
	return nodes
}

// UpdateThreatScore updates the threat score for a node (called by Python AI)
func (nm *NodeManager) UpdateThreatScore(nodeID uint32, threatScore float32) error {
	if !nm.store.UpdateThreatScore(nodeID, threatScore) {
		return fmt.Errorf("failed to update threat score for node %d", nodeID)
	}
	return nil
}

// GetConnectionQuality gets connection quality for a peer (called by Python)
func (nm *NodeManager) GetConnectionQuality(peerID uint32) (*ConnectionQuality, error) {
	return nm.network.GetConnectionQuality(peerID)
}

// DisconnectPeer disconnects from a peer (called by Python)
func (nm *NodeManager) DisconnectPeer(peerID uint32) error {
	return nm.network.DisconnectPeer(peerID)
}

// GetConnectedPeers gets list of connected peer IDs (called by Python)
func (nm *NodeManager) GetConnectedPeers() []uint32 {
	return nm.network.GetConnectedPeers()
}
