package store

import (
	"sync"
	"time"
)

// NodeState represents the state of a network node
type NodeState uint32

const (
	StateActive NodeState = iota
	StatePurgatory
	StateDead
)

// Node represents a network node in the system (local storage)
// Note: This is separate from the Cap'n Proto generated Node type
type Node struct {
	ID          uint32
	Status      NodeState
	LatencyMs   float32
	ThreatScore float32
	// Connection quality metrics
	JitterMs    float32 // Latency variance
	PacketLoss  float32 // Packet loss percentage (0.0-1.0)
	LastSeen    int64   // Unix timestamp of last successful ping
	mu          sync.RWMutex
}

// Store manages the in-memory storage of nodes
type Store struct {
	nodes map[uint32]*Node
	mu    sync.RWMutex
}

// NewStore creates a new node store
func NewStore() *Store {
	return &Store{
		nodes: make(map[uint32]*Node),
	}
}

// GetNode retrieves a node by ID
func (s *Store) GetNode(id uint32) (*Node, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	node, exists := s.nodes[id]
	return node, exists
}

// GetAllNodes returns all nodes
func (s *Store) GetAllNodes() []*Node {
	s.mu.RLock()
	defer s.mu.RUnlock()
	nodes := make([]*Node, 0, len(s.nodes))
	for _, node := range s.nodes {
		nodes = append(nodes, node)
	}
	return nodes
}

// AddOrUpdateNode adds or updates a node
func (s *Store) AddOrUpdateNode(node *Node) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.nodes[node.ID] = node
}

// UpdateLatency updates the latency for a node and calculates jitter
func (s *Store) UpdateLatency(nodeID uint32, latencyMs float32) bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	node, exists := s.nodes[nodeID]
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
	node.LastSeen = time.Now().Unix()
	return true
}

// UpdateThreatScore updates the threat score for a node
func (s *Store) UpdateThreatScore(nodeID uint32, threatScore float32) bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	node, exists := s.nodes[nodeID]
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

// UpdatePacketLoss updates the packet loss for a node
func (s *Store) UpdatePacketLoss(nodeID uint32, packetLoss float32) bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	node, exists := s.nodes[nodeID]
	if !exists {
		return false
	}
	node.mu.Lock()
	defer node.mu.Unlock()
	node.PacketLoss = packetLoss
	return true
}

// CreateNode creates a new node
func (s *Store) CreateNode(id uint32) *Node {
	node := &Node{
		ID:          id,
		Status:      StateActive,
		LatencyMs:   0.0,
		ThreatScore: 0.0,
		JitterMs:    0.0,
		PacketLoss:  0.0,
		LastSeen:    time.Now().Unix(),
	}
	s.AddOrUpdateNode(node)
	return node
}
