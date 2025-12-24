package main

import (
	"fmt"
	"sync"

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

	// FetchShare fetches a DKG share for a fileID from a peer
	FetchShare(peerID uint32, fileID string) ([]byte, error)
	GetConnectedPeers() []uint32

	// GetConnectionQuality returns connection quality metrics for a peer
	GetConnectionQuality(peerID uint32) (latencyMs, jitterMs, packetLoss float32, err error)
}

// LibP2PAdapter wraps LibP2PPangeaNode to implement NetworkAdapter
type LibP2PAdapter struct {
	node  *LibP2PPangeaNode
	store *NodeStore
	// Bidirectional peer ID mapping
	peerIDToUint32 map[string]uint32
	uint32ToPeerID map[uint32]string
	nextPeerID     uint32
	peerIDMu       sync.RWMutex
}

func NewLibP2PAdapter(node *LibP2PPangeaNode, store *NodeStore) *LibP2PAdapter {
	return &LibP2PAdapter{
		node:           node,
		store:          store,
		peerIDToUint32: make(map[string]uint32),
		uint32ToPeerID: make(map[uint32]string),
		nextPeerID:     1,
	}
}

// LegacyP2PAdapter wraps the legacy TCP-based P2P node for tests and backwards compatibility
// This is a thin adapter that maps the older P2P node API to NetworkAdapter.
type LegacyP2PAdapter struct {
	node  *P2PNode
	store *NodeStore
}

func NewLegacyP2PAdapter(node *P2PNode, store *NodeStore) *LegacyP2PAdapter {
	return &LegacyP2PAdapter{node: node, store: store}
}

type ErrorString string

var ErrPeerNotConnected = ErrorString("peer not connected")

// Minimal ConnectToPeer implementation for legacy adapter (no-op for tests)
func (a *LegacyP2PAdapter) ConnectToPeer(peerAddr string, peerID uint32) error {
	// In the legacy adapter, explicit dialing may be out-of-band (test harness connects nodes),
	// so for now this is a no-op that succeeds when used in local tests.
	return nil
}

// getPeerUint32ID returns the uint32 ID for a libp2p peer ID, creating one if needed
func (a *LibP2PAdapter) getPeerUint32ID(peerIDStr string) uint32 {
	a.peerIDMu.Lock()
	defer a.peerIDMu.Unlock()

	if id, exists := a.peerIDToUint32[peerIDStr]; exists {
		return id
	}

	// Create new mapping
	id := a.nextPeerID
	a.nextPeerID++
	a.peerIDToUint32[peerIDStr] = id
	a.uint32ToPeerID[id] = peerIDStr
	return id
}

// getLibp2pPeerID returns the libp2p peer ID string for a uint32 ID
func (a *LibP2PAdapter) getLibp2pPeerID(id uint32) (string, bool) {
	a.peerIDMu.RLock()
	defer a.peerIDMu.RUnlock()

	peerIDStr, exists := a.uint32ToPeerID[id]
	return peerIDStr, exists
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
	// Look up the libp2p peer ID
	peerIDStr, exists := a.getLibp2pPeerID(peerID)
	if !exists {
		return fmt.Errorf("peer %d not found in mapping", peerID)
	}

	pid, err := peer.Decode(peerIDStr)
	if err != nil {
		return fmt.Errorf("invalid peer ID: %w", err)
	}

	stream, err := a.node.host.NewStream(a.node.ctx, pid, PangeaRPCProtocol)
	if err != nil {
		return err
	}
	defer stream.Close()

	_, err = stream.Write(data)
	return err
}

// SendShare sends a DKG share to the peer for the given fileID
// New message format: [TYPE=4][fileIDLen(2)][fileID][fromPeer(4)][shareLen(4)][share]
func (a *LibP2PAdapter) SendShare(peerID uint32, fileID string, share []byte) error {
	peerIDStr, exists := a.getLibp2pPeerID(peerID)
	if !exists {
		return fmt.Errorf("peer %d not found in mapping", peerID)
	}

	pid, err := peer.Decode(peerIDStr)
	if err != nil {
		return fmt.Errorf("invalid peer ID: %w", err)
	}

	stream, err := a.node.host.NewStream(a.node.ctx, pid, PangeaRPCProtocol)
	if err != nil {
		return err
	}
	defer stream.Close()

	fromPeer := a.node.nodeID

	// Build message: [TYPE=4][fileIDLen(2)][fileID][fromPeer(4)][shareLen(4)][share]
	msg := make([]byte, 1+2+len(fileID)+4+4+len(share))
	msg[0] = 4
	msg[1] = byte(len(fileID) >> 8)
	msg[2] = byte(len(fileID) & 0xff)
	off := 3
	copy(msg[off:off+len(fileID)], []byte(fileID))
	off += len(fileID)
	msg[off] = byte(fromPeer >> 24)
	msg[off+1] = byte(fromPeer >> 16)
	msg[off+2] = byte(fromPeer >> 8)
	msg[off+3] = byte(fromPeer)
	off += 4
	msg[off] = byte(len(share) >> 24)
	msg[off+1] = byte(len(share) >> 16)
	msg[off+2] = byte(len(share) >> 8)
	msg[off+3] = byte(len(share) & 0xff)
	off += 4
	copy(msg[off:], share)

	_, err = stream.Write(msg)
	return err
}

// SendShard instructs the peer to store shard bytes for fileHash
func (a *LibP2PAdapter) SendShard(peerID uint32, fileHash string, shardIndex uint32, data []byte) error {
	peerIDStr, exists := a.getLibp2pPeerID(peerID)
	if !exists {
		return fmt.Errorf("peer %d not found in mapping", peerID)
	}

	pid, err := peer.Decode(peerIDStr)
	if err != nil {
		return fmt.Errorf("invalid peer ID: %w", err)
	}

	stream, err := a.node.host.NewStream(a.node.ctx, pid, PangeaRPCProtocol)
	if err != nil {
		return err
	}
	defer stream.Close()

	// Message: [TYPE=3][fileHashLen(2)][fileHash][shardIndex(4)][data]
	msg := make([]byte, 1+2+len(fileHash)+4+len(data))
	msg[0] = 3
	msg[1] = byte(len(fileHash) >> 8)
	msg[2] = byte(len(fileHash) & 0xff)
	off := 3
	copy(msg[off:off+len(fileHash)], []byte(fileHash))
	off += len(fileHash)
	msg[off] = byte(shardIndex >> 24)
	msg[off+1] = byte(shardIndex >> 16)
	msg[off+2] = byte(shardIndex >> 8)
	msg[off+3] = byte(shardIndex & 0xff)
	off += 4
	copy(msg[off:], data)

	_, err = stream.Write(msg)
	return err
}

func (a *LibP2PAdapter) GetConnectedPeers() []uint32 {
	peers := a.node.GetConnectedPeers()
	// Use proper bidirectional mapping
	result := make([]uint32, 0, len(peers))
	for _, p := range peers {
		if p.ID != "" {
			id := a.getPeerUint32ID(p.ID)
			result = append(result, id)
		}
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
	// Look up the libp2p peer ID
	peerIDStr, exists := a.getLibp2pPeerID(peerID)
	if !exists {
		return nil, fmt.Errorf("peer %d not found in mapping", peerID)
	}

	pid, err := peer.Decode(peerIDStr)
	if err != nil {
		return nil, fmt.Errorf("invalid peer ID: %w", err)
	}

	stream, err := a.node.host.NewStream(a.node.ctx, pid, PangeaRPCProtocol)
	if err != nil {
		return nil, fmt.Errorf("failed to open stream: %w", err)
	}
	defer stream.Close()

	// Send shard request: [TYPE=1][fileHashLen(2)][fileHash][shardIndex(4)]
	// For backwards compatibility, support short form where caller only provided shardIndex earlier
	// However our callers will send full request via Stream write directly.
	// Here we assume caller builds it; keep the simple legacy support for tests where stream expects full message.

	// Read response
	buffer := make([]byte, 1024*1024) // 1MB max shard size
	n, err := stream.Read(buffer)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	return buffer[:n], nil
}

// FetchShare requests a DKG share for fileID from the peer
func (a *LibP2PAdapter) FetchShare(peerID uint32, fileID string) ([]byte, error) {
	peerIDStr, exists := a.getLibp2pPeerID(peerID)
	if !exists {
		return nil, fmt.Errorf("peer %d not found in mapping", peerID)
	}

	pid, err := peer.Decode(peerIDStr)
	if err != nil {
		return nil, fmt.Errorf("invalid peer ID: %w", err)
	}

	stream, err := a.node.host.NewStream(a.node.ctx, pid, PangeaRPCProtocol)
	if err != nil {
		return nil, fmt.Errorf("failed to open stream: %w", err)
	}
	defer stream.Close()

	// Request: [TYPE=2][fileIDLen(2)][fileID]
	req := make([]byte, 1+2+len(fileID))
	req[0] = 2
	req[1] = byte(len(fileID) >> 8)
	req[2] = byte(len(fileID) & 0xff)
	copy(req[3:], []byte(fileID))

	if _, err := stream.Write(req); err != nil {
		return nil, fmt.Errorf("failed to write request: %w", err)
	}

	// Read response
	buf := make([]byte, 4096)
	n, err := stream.Read(buf)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	if n == 0 {
		return nil, fmt.Errorf("no share returned")
	}
	return buf[:n], nil
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

	// Send shard request: [REQUEST_TYPE=1][fileHashLen(2)][fileHash][shardIndex(4)]
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

// FetchShare requests a DKG share for fileID from the peer
func (a *LegacyP2PAdapter) FetchShare(peerID uint32, fileID string) ([]byte, error) {
	a.node.mu.RLock()
	conn, exists := a.node.connections[peerID]
	a.node.mu.RUnlock()

	if !exists {
		return nil, ErrPeerNotConnected
	}

	conn.mu.Lock()
	defer conn.mu.Unlock()

	// Request: [TYPE=2][fileIDLen(2)][fileID]
	req := make([]byte, 1+2+len(fileID))
	req[0] = 2
	req[1] = byte(len(fileID) >> 8)
	req[2] = byte(len(fileID) & 0xff)
	copy(req[3:], []byte(fileID))

	var toSend []byte
	var err error
	if conn.cipherState != nil {
		toSend, err = conn.cipherState.Encrypt(nil, nil, req)
		if err != nil {
			return nil, err
		}
	} else {
		toSend = req
	}

	_, err = conn.conn.Write(toSend)
	if err != nil {
		return nil, err
	}

	// Read response
	buf := make([]byte, 4096)
	n, err := conn.conn.Read(buf)
	if err != nil {
		return nil, err
	}

	if n == 0 {
		return nil, fmt.Errorf("no share returned")
	}
	// Decrypt if needed
	var response []byte
	if conn.cipherState != nil {
		response, err = conn.cipherState.Decrypt(nil, nil, buf[:n])
		if err != nil {
			return nil, err
		}
	} else {
		response = buf[:n]
	}

	return response, nil
}

// SendShare sends a DKG share to the peer (legacy path)
// Message format: [TYPE=4][fileIDLen(2)][fileID][fromPeer(4)][shareLen(4)][share]
func (a *LegacyP2PAdapter) SendShare(peerID uint32, fileID string, share []byte) error {
	a.node.mu.RLock()
	conn, exists := a.node.connections[peerID]
	a.node.mu.RUnlock()

	if !exists {
		return ErrPeerNotConnected
	}

	conn.mu.Lock()
	defer conn.mu.Unlock()

	fromPeer := a.node.id

	// Message: [TYPE=4][fileIDLen(2)][fileID][fromPeer(4)][shareLen(4)][share]
	msg := make([]byte, 1+2+len(fileID)+4+4+len(share))
	msg[0] = 4
	msg[1] = byte(len(fileID) >> 8)
	msg[2] = byte(len(fileID) & 0xff)
	off := 3
	copy(msg[off:off+len(fileID)], []byte(fileID))
	off += len(fileID)
	msg[off] = byte(fromPeer >> 24)
	msg[off+1] = byte(fromPeer >> 16)
	msg[off+2] = byte(fromPeer >> 8)
	msg[off+3] = byte(fromPeer)
	off += 4
	msg[off+1] = byte(len(share) >> 16)
	msg[off+2] = byte(len(share) >> 8)
	msg[off+3] = byte(len(share) & 0xff)
	off += 4
	copy(msg[off:], share)

	var toSend []byte
	var err error
	if conn.cipherState != nil {
		toSend, err = conn.cipherState.Encrypt(nil, nil, msg)
		if err != nil {
			return err
		}
	} else {
		toSend = msg
	}

	_, err = conn.conn.Write(toSend)
	return err
}

func (e ErrorString) Error() string {
	return string(e)
}
