package main

import (
	"fmt"

	"github.com/libp2p/go-libp2p/core/peer"
)

// NetworkAdapter provides a unified interface for both libp2p and legacy P2P implementations
type NetworkAdapter interface {
	// ConnectToPeer connects to a peer by address
	ConnectToPeer(peerAddr string, peerID uint32) error

	// DisconnectPeer disconnects from a peer
	DisconnectPeer(peerID uint32) error

	// SendMessage sends a message to a peer
	SendMessage(peerID uint32, data []byte) error

	// FetchShard fetches a shard from a peer
	FetchShard(peerID uint32, shardIndex uint32) ([]byte, error)

	// GetConnectedPeers returns list of connected peer IDs
	GetConnectedPeers() []uint32

	// GetConnectionQuality returns connection quality metrics for a peer
	GetConnectionQuality(peerID uint32) (latencyMs, jitterMs, packetLoss float32, err error)
}

// LibP2PAdapter wraps LibP2PPangeaNode to implement NetworkAdapter
type LibP2PAdapter struct {
	node  *LibP2PPangeaNode
	store *NodeStore
}

func NewLibP2PAdapter(node *LibP2PPangeaNode, store *NodeStore) *LibP2PAdapter {
	return &LibP2PAdapter{
		node:  node,
		store: store,
	}
}

func (a *LibP2PAdapter) ConnectToPeer(peerAddr string, peerID uint32) error {
	return a.node.ConnectToPeer(peerAddr)
}

func (a *LibP2PAdapter) DisconnectPeer(peerID uint32) error {
	// Find peer in libp2p network and close connections
	peers := a.node.GetConnectedPeers()
	for _, p := range peers {
		// Simple match - in production you'd maintain a peerID->libp2pID mapping
		if len(p.ID) > 0 {
			// Parse peer ID from libp2p peer info
			if pid, err := peer.Decode(p.ID); err == nil {
				if err := a.node.host.Network().ClosePeer(pid); err != nil {
					return err
				}
			}
		}
	}
	return nil
}

func (a *LibP2PAdapter) SendMessage(peerID uint32, data []byte) error {
	// Find peer and send message through libp2p stream
	peers := a.node.GetConnectedPeers()
	for _, p := range peers {
		if pid, err := peer.Decode(p.ID); err == nil {
			stream, err := a.node.host.NewStream(a.node.ctx, pid, PangeaRPCProtocol)
			if err != nil {
				return err
			}
			defer stream.Close()

			_, err = stream.Write(data)
			return err
		}
	}
	return nil
}

func (a *LibP2PAdapter) GetConnectedPeers() []uint32 {
	peers := a.node.GetConnectedPeers()
	// Convert libp2p peer IDs to uint32 (simplified)
	// In production, maintain a bidirectional mapping
	result := make([]uint32, 0, len(peers))
	for i := range peers {
		result = append(result, uint32(i+1)) // Placeholder mapping
	}
	return result
}

func (a *LibP2PAdapter) GetConnectionQuality(peerID uint32) (latencyMs, jitterMs, packetLoss float32, err error) {
	// Get quality metrics from node store
	node, exists := a.store.GetNode(peerID)
	if !exists {
		node, exists = a.store.GetNode(a.node.nodeID)
		if !exists {
			return 0, 0, 0, nil // No data available
		}
	}

	return node.LatencyMs, node.JitterMs, node.PacketLoss, nil
}

func (a *LibP2PAdapter) FetchShard(peerID uint32, shardIndex uint32) ([]byte, error) {
	// Find peer and request shard through libp2p stream
	peers := a.node.GetConnectedPeers()

	// TODO: In production, maintain proper peerID <-> libp2p peer.ID mapping
	// For now, try to fetch from any connected peer
	for _, p := range peers {
		if pid, err := peer.Decode(p.ID); err == nil {
			stream, err := a.node.host.NewStream(a.node.ctx, pid, PangeaRPCProtocol)
			if err != nil {
				continue // Try next peer
			}
			defer stream.Close()

			// Send shard request: [REQUEST_TYPE=1][SHARD_INDEX]
			request := make([]byte, 5)
			request[0] = 1 // Request type: fetch shard
			request[1] = byte(shardIndex >> 24)
			request[2] = byte(shardIndex >> 16)
			request[3] = byte(shardIndex >> 8)
			request[4] = byte(shardIndex)

			_, err = stream.Write(request)
			if err != nil {
				continue
			}

			// Read response
			buffer := make([]byte, 1024*1024) // 1MB max shard size
			n, err := stream.Read(buffer)
			if err != nil {
				continue
			}

			return buffer[:n], nil
		}
	}

	return nil, fmt.Errorf("failed to fetch shard %d from peer %d: no route available", shardIndex, peerID)
}

// LegacyP2PAdapter wraps P2PNode to implement NetworkAdapter
type LegacyP2PAdapter struct {
	node  *P2PNode
	store *NodeStore
}

func NewLegacyP2PAdapter(node *P2PNode, store *NodeStore) *LegacyP2PAdapter {
	return &LegacyP2PAdapter{
		node:  node,
		store: store,
	}
}

func (a *LegacyP2PAdapter) ConnectToPeer(peerAddr string, peerID uint32) error {
	return a.node.ConnectToPeer(peerAddr, peerID)
}

func (a *LegacyP2PAdapter) DisconnectPeer(peerID uint32) error {
	a.node.mu.Lock()
	defer a.node.mu.Unlock()

	conn, exists := a.node.connections[peerID]
	if !exists {
		return nil
	}

	conn.conn.Close()
	delete(a.node.connections, peerID)
	return nil
}

func (a *LegacyP2PAdapter) SendMessage(peerID uint32, data []byte) error {
	a.node.mu.RLock()
	conn, exists := a.node.connections[peerID]
	a.node.mu.RUnlock()

	if !exists {
		return ErrPeerNotConnected
	}

	conn.mu.Lock()
	defer conn.mu.Unlock()

	// Encrypt message if cipher state exists
	var encryptedMsg []byte
	var err error
	if conn.cipherState != nil {
		encryptedMsg, err = conn.cipherState.Encrypt(nil, nil, data)
		if err != nil {
			return err
		}
	} else {
		encryptedMsg = data
	}

	_, err = conn.conn.Write(encryptedMsg)
	return err
}

func (a *LegacyP2PAdapter) GetConnectedPeers() []uint32 {
	a.node.mu.RLock()
	defer a.node.mu.RUnlock()

	peers := make([]uint32, 0, len(a.node.connections))
	for peerID := range a.node.connections {
		peers = append(peers, peerID)
	}
	return peers
}

func (a *LegacyP2PAdapter) GetConnectionQuality(peerID uint32) (latencyMs, jitterMs, packetLoss float32, err error) {
	node, exists := a.store.GetNode(peerID)
	if !exists {
		return 0, 0, 0, nil
	}

	return node.LatencyMs, node.JitterMs, node.PacketLoss, nil
}

func (a *LegacyP2PAdapter) FetchShard(peerID uint32, shardIndex uint32) ([]byte, error) {
	a.node.mu.RLock()
	conn, exists := a.node.connections[peerID]
	a.node.mu.RUnlock()

	if !exists {
		return nil, ErrPeerNotConnected
	}

	conn.mu.Lock()
	defer conn.mu.Unlock()

	// Send shard request: [REQUEST_TYPE=1][SHARD_INDEX]
	request := make([]byte, 5)
	request[0] = 1 // Request type: fetch shard
	request[1] = byte(shardIndex >> 24)
	request[2] = byte(shardIndex >> 16)
	request[3] = byte(shardIndex >> 8)
	request[4] = byte(shardIndex)

	// Encrypt if we have cipher state
	var toSend []byte
	var err error
	if conn.cipherState != nil {
		toSend, err = conn.cipherState.Encrypt(nil, nil, request)
		if err != nil {
			return nil, err
		}
	} else {
		toSend = request
	}

	_, err = conn.conn.Write(toSend)
	if err != nil {
		return nil, err
	}

	// Read response
	buffer := make([]byte, 1024*1024) // 1MB max
	n, err := conn.conn.Read(buffer)
	if err != nil {
		return nil, err
	}

	// Decrypt if needed
	var response []byte
	if conn.cipherState != nil {
		response, err = conn.cipherState.Decrypt(nil, nil, buffer[:n])
		if err != nil {
			return nil, err
		}
	} else {
		response = buffer[:n]
	}

	return response, nil
}

// Common errors
var (
	ErrPeerNotConnected = ErrorString("peer not connected")
)

type ErrorString string

func (e ErrorString) Error() string {
	return string(e)
}
