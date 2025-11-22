package main

import (
	"sync"
)

// NodeState represents the state of a network node
type NodeState uint32

const (
	StateActive NodeState = iota
	StatePurgatory
	StateDead
)

// LocalNode represents a network node in the system (local storage)
// Note: This is separate from the Cap'n Proto generated Node type
type LocalNode struct {
	ID          uint32
	Status      NodeState
	LatencyMs   float32
	ThreatScore float32
	JitterMs    float32 // Latency variance
	PacketLoss  float32 // Packet loss percentage (0.0-1.0)
	LastSeen    int64   // Unix timestamp of last successful ping
	mu          sync.RWMutex
}

// NodeStore manages the in-memory storage of nodes
type NodeStore struct {
	nodes map[uint32]*LocalNode
	mu    sync.RWMutex
}

// NewNodeStore creates a new node store
func NewNodeStore() *NodeStore {
	return &NodeStore{
		nodes: make(map[uint32]*LocalNode),
	}
}

// GetNode retrieves a node by ID
func (ns *NodeStore) GetNode(id uint32) (*LocalNode, bool) {
	ns.mu.RLock()
	defer ns.mu.RUnlock()
	node, exists := ns.nodes[id]
	return node, exists
}

// GetAllNodes returns all nodes
func (ns *NodeStore) GetAllNodes() []*LocalNode {
	ns.mu.RLock()
	defer ns.mu.RUnlock()
	nodes := make([]*LocalNode, 0, len(ns.nodes))
	for _, node := range ns.nodes {
		nodes = append(nodes, node)
	}
	return nodes
}

// AddOrUpdateNode adds or updates a node
func (ns *NodeStore) AddOrUpdateNode(node *LocalNode) {
	ns.mu.Lock()
	defer ns.mu.Unlock()
	ns.nodes[node.ID] = node
}

// UpdateLatency updates the latency for a node and calculates jitter
func (ns *NodeStore) UpdateLatency(nodeID uint32, latencyMs float32) bool {
	ns.mu.Lock()
	defer ns.mu.Unlock()
	node, exists := ns.nodes[nodeID]
	if !exists {
		return false
	}
	node.mu.Lock()
	defer node.mu.Unlock()

	// Calculate jitter (latency variance)
	oldLatency := node.LatencyMs
	if oldLatency > 0 {
		// Simple jitter calculation: difference from previous latency
		jitter := latencyMs - oldLatency
		if jitter < 0 {
			jitter = -jitter
		}
		node.JitterMs = (node.JitterMs*0.9 + jitter*0.1) // Exponential moving average
	}

	node.LatencyMs = latencyMs
	return true
}

// UpdatePacketLoss updates the packet loss for a node
func (ns *NodeStore) UpdatePacketLoss(nodeID uint32, packetLoss float32) bool {
	ns.mu.Lock()
	defer ns.mu.Unlock()
	node, exists := ns.nodes[nodeID]
	if !exists {
		return false
	}
	node.mu.Lock()
	defer node.mu.Unlock()
	node.PacketLoss = packetLoss
	return true
}

// UpdateThreatScore updates the threat score for a node
func (ns *NodeStore) UpdateThreatScore(nodeID uint32, threatScore float32) bool {
	ns.mu.Lock()
	defer ns.mu.Unlock()
	node, exists := ns.nodes[nodeID]
	if !exists {
		return false
	}
	node.mu.Lock()
	defer node.mu.Unlock()
	node.ThreatScore = threatScore

	// Auto-transition to Purgatory if threat score is high
	if threatScore > 0.8 {
		node.Status = StatePurgatory
	} else if threatScore < 0.3 {
		node.Status = StateActive
	}
	return true
}

// CreateNode creates a new node
func (ns *NodeStore) CreateNode(id uint32) *LocalNode {
	node := &LocalNode{
		ID:          id,
		Status:      StateActive,
		LatencyMs:   0.0,
		ThreatScore: 0.0,
		JitterMs:    0.0,
		PacketLoss:  0.0,
		LastSeen:    0,
	}
	ns.AddOrUpdateNode(node)
	return node
}
