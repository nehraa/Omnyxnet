package main

import (
	"context"
	"crypto/rand"
	"fmt"
	"log"
	"net"
	"sync"
	"time"

	"github.com/flynn/noise"
)

// NoiseConfig holds the Noise Protocol configuration
type NoiseConfig struct {
	staticKey noise.DHKey
}

// P2PNode represents a P2P network node
type P2PNode struct {
	id           uint32
	store        *NodeStore
	noiseConfig  *NoiseConfig
	connections  map[uint32]*P2PConnection
	mu           sync.RWMutex
	listener     net.Listener
	ctx          context.Context
	cancel       context.CancelFunc
}

// P2PConnection represents a connection to another peer
type P2PConnection struct {
	id         uint32
	conn       net.Conn
	cipherState *noise.CipherState // Encryption state after handshake
	mu         sync.Mutex
	lastPing   time.Time
	latency    time.Duration
}

// NewP2PNode creates a new P2P node
func NewP2PNode(id uint32, store *NodeStore) (*P2PNode, error) {
	// Generate Noise Protocol key pair using Curve25519
	staticKey, err := noise.DH25519.GenerateKeypair(rand.Reader)
	if err != nil {
		return nil, fmt.Errorf("failed to generate Noise keypair: %w", err)
	}

	ctx, cancel := context.WithCancel(context.Background())

	return &P2PNode{
		id:          id,
		store:       store,
		noiseConfig: &NoiseConfig{
			staticKey: staticKey,
		},
		connections: make(map[uint32]*P2PConnection),
		ctx:         ctx,
		cancel:      cancel,
	}, nil
}

// Start starts the P2P node listener
func (p *P2PNode) Start(listenAddr string) error {
	listener, err := net.Listen("tcp", listenAddr)
	if err != nil {
		return fmt.Errorf("failed to listen on %s: %w", listenAddr, err)
	}

	p.listener = listener
	log.Printf("P2P Node %d listening on %s", p.id, listenAddr)

	// Start accepting connections
	go p.acceptConnections()

	// Start latency measurement loop
	go p.measureLatency()

	return nil
}

// acceptConnections accepts incoming P2P connections
func (p *P2PNode) acceptConnections() {
	for {
		select {
		case <-p.ctx.Done():
			return
		default:
			conn, err := p.listener.Accept()
			if err != nil {
				log.Printf("Error accepting connection: %v", err)
				continue
			}

			go p.handleIncomingConnection(conn)
		}
	}
}

// handleIncomingConnection handles a new incoming connection
func (p *P2PNode) handleIncomingConnection(conn net.Conn) {
	defer conn.Close()

	// Perform Noise Protocol handshake (as responder)
	cipherState, peerID, err := p.performHandshake(conn, false)
	if err != nil {
		log.Printf("Handshake failed: %v", err)
		return
	}

	p2pConn := &P2PConnection{
		id:          peerID,
		conn:        conn,
		cipherState: cipherState,
		lastPing:    time.Now(),
	}

	p.mu.Lock()
	p.connections[peerID] = p2pConn
	p.mu.Unlock()

	log.Printf("New P2P connection established with node %d", peerID)

	// Handle connection messages
	p.handleConnectionMessages(p2pConn)
}

// performHandshake performs Noise Protocol XX handshake
// Returns: cipher state, peer ID, error
func (p *P2PNode) performHandshake(conn net.Conn, isInitiator bool) (*noise.CipherState, uint32, error) {
	// Configure Noise Protocol with XX handshake pattern
	config := noise.Config{
		CipherSuite:   noise.NewCipherSuite(noise.DH25519, noise.CipherChaChaPoly, noise.HashBLAKE2b),
		Random:        rand.Reader,
		Pattern:       noise.HandshakeXX,
		Initiator:     isInitiator,
		StaticKeypair: p.noiseConfig.staticKey,
	}

	handshake, err := noise.NewHandshakeState(config)
	if err != nil {
		return nil, 0, fmt.Errorf("failed to create handshake state: %w", err)
	}

	var message, plaintext []byte

	// XX handshake: 3 messages
	// Message 1: -> e
	var cs1, cs2 *noise.CipherState
	if isInitiator {
		message, cs1, cs2, err = handshake.WriteMessage(nil, nil)
		if err != nil {
			return nil, 0, fmt.Errorf("handshake message 1 failed: %w", err)
		}
		if _, err := conn.Write(message); err != nil {
			return nil, 0, fmt.Errorf("failed to send handshake message 1: %w", err)
		}
	} else {
		buffer := make([]byte, 64) // XX message 1 is typically 48 bytes
		n, err := conn.Read(buffer)
		if err != nil {
			return nil, 0, fmt.Errorf("failed to read handshake message 1: %w", err)
		}
		_, _, _, err = handshake.ReadMessage(nil, buffer[:n])
		if err != nil {
			return nil, 0, fmt.Errorf("handshake message 1 read failed: %w", err)
		}
	}

	// Message 2: <- e, ee, s, es (contains peer's static public key)
	var peerID uint32
	
	if !isInitiator {
		// Include our node ID in the payload
		nodeIDPayload := make([]byte, 4)
		nodeIDPayload[0] = byte(p.id)
		nodeIDPayload[1] = byte(p.id >> 8)
		nodeIDPayload[2] = byte(p.id >> 16)
		nodeIDPayload[3] = byte(p.id >> 24)

		var msg []byte
		msg, cs1, cs2, err = handshake.WriteMessage(nil, nodeIDPayload)
		if err != nil {
			return nil, 0, fmt.Errorf("handshake message 2 failed: %w", err)
		}
		message = msg
		if _, err := conn.Write(message); err != nil {
			return nil, 0, fmt.Errorf("failed to send handshake message 2: %w", err)
		}
	} else {
		buffer := make([]byte, 128) // XX message 2 is typically 96 bytes + payload
		n, err := conn.Read(buffer)
		if err != nil {
			return nil, 0, fmt.Errorf("failed to read handshake message 2: %w", err)
		}
		var pt []byte
		pt, cs1, cs2, err = handshake.ReadMessage(nil, buffer[:n])
		if err != nil {
			return nil, 0, fmt.Errorf("handshake message 2 read failed: %w", err)
		}
		plaintext = pt
		// Extract peer ID from payload
		if len(plaintext) >= 4 {
			peerID = uint32(plaintext[0]) | uint32(plaintext[1])<<8 | uint32(plaintext[2])<<16 | uint32(plaintext[3])<<24
		}
	}

	// Message 3: -> s, se (contains our static public key)
	if isInitiator {
		// Include our node ID in the payload
		nodeIDPayload := make([]byte, 4)
		nodeIDPayload[0] = byte(p.id)
		nodeIDPayload[1] = byte(p.id >> 8)
		nodeIDPayload[2] = byte(p.id >> 16)
		nodeIDPayload[3] = byte(p.id >> 24)

		var msg []byte
		msg, _, _, err = handshake.WriteMessage(nil, nodeIDPayload)
		if err != nil {
			return nil, 0, fmt.Errorf("handshake message 3 failed: %w", err)
		}
		message = msg
		if _, err := conn.Write(message); err != nil {
			return nil, 0, fmt.Errorf("failed to send handshake message 3: %w", err)
		}
		cipherState := cs1
		if cipherState == nil {
			cipherState = cs2
		}
		// Peer ID was extracted from message 2
		return cipherState, peerID, nil
	} else {
		buffer := make([]byte, 80) // XX message 3 is typically 64 bytes + payload
		n, err := conn.Read(buffer)
		if err != nil {
			return nil, 0, fmt.Errorf("failed to read handshake message 3: %w", err)
		}
		var pt []byte
		pt, _, _, err = handshake.ReadMessage(nil, buffer[:n])
		if err != nil {
			return nil, 0, fmt.Errorf("handshake message 3 read failed: %w", err)
		}
		plaintext = pt
		// Extract peer ID from payload (though we already know it from ConnectToPeer)
		if len(plaintext) >= 4 {
			peerID = uint32(plaintext[0]) | uint32(plaintext[1])<<8 | uint32(plaintext[2])<<16 | uint32(plaintext[3])<<24
		}
		cipherState := cs1
		if cipherState == nil {
			cipherState = cs2
		}
		return cipherState, peerID, nil
	}
}

// handleConnectionMessages handles messages from a connection
func (p *P2PNode) handleConnectionMessages(conn *P2PConnection) {
	buffer := make([]byte, 4096)
	for {
		select {
		case <-p.ctx.Done():
			return
		default:
			n, err := conn.conn.Read(buffer)
			if err != nil {
				log.Printf("Error reading from connection: %v", err)
				p.mu.Lock()
				delete(p.connections, conn.id)
				p.mu.Unlock()
				return
			}

			// Decrypt and process message using Noise Protocol
			if conn.cipherState != nil {
				plaintext, err := conn.cipherState.Decrypt(nil, nil, buffer[:n])
				if err != nil {
					log.Printf("Decryption failed: %v", err)
					continue
				}
				log.Printf("Received %d encrypted bytes from node %d (decrypted: %d bytes)", n, conn.id, len(plaintext))
			} else {
				log.Printf("Received %d unencrypted bytes from node %d", n, conn.id)
			}
		}
	}
}

// ConnectToPeer connects to another peer
func (p *P2PNode) ConnectToPeer(peerAddr string, peerID uint32) error {
	conn, err := net.Dial("tcp", peerAddr)
	if err != nil {
		return fmt.Errorf("failed to connect to %s: %w", peerAddr, err)
	}

	// Perform Noise Protocol handshake (as initiator)
	cipherState, remotePeerID, err := p.performHandshake(conn, true)
	if err != nil {
		conn.Close()
		return fmt.Errorf("handshake failed: %w", err)
	}

	p2pConn := &P2PConnection{
		id:          remotePeerID,
		conn:        conn,
		cipherState: cipherState,
		lastPing:    time.Now(),
	}

	p.mu.Lock()
	p.connections[peerID] = p2pConn
	p.mu.Unlock()

	log.Printf("Connected to peer %d at %s", peerID, peerAddr)

	// Handle connection messages
	go p.handleConnectionMessages(p2pConn)

	return nil
}

// measureLatency periodically measures latency to all connected peers
func (p *P2PNode) measureLatency() {
	ticker := time.NewTicker(5 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-p.ctx.Done():
			return
		case <-ticker.C:
			p.mu.RLock()
			connections := make([]*P2PConnection, 0, len(p.connections))
			for _, conn := range p.connections {
				connections = append(connections, conn)
			}
			p.mu.RUnlock()

			for _, conn := range connections {
				latency := p.pingPeer(conn)
				if latency > 0 {
					conn.mu.Lock()
					conn.latency = latency
					conn.lastPing = time.Now()
					conn.mu.Unlock()

					// Update node store with latency
					p.store.UpdateLatency(conn.id, float32(latency.Milliseconds()))
				}
			}
		}
	}
}

// pingPeer sends a ping to a peer and measures RTT
func (p *P2PNode) pingPeer(conn *P2PConnection) time.Duration {
	conn.mu.Lock()
	defer conn.mu.Unlock()

	start := time.Now()
	pingMsg := []byte("PING")

	// Encrypt ping message using Noise Protocol
	var encryptedMsg []byte
	var err error
	if conn.cipherState != nil {
		encryptedMsg, err = conn.cipherState.Encrypt(nil, nil, pingMsg)
		if err != nil {
			return 0
		}
	} else {
		encryptedMsg = pingMsg
	}

	if _, err := conn.conn.Write(encryptedMsg); err != nil {
		return 0
	}

	// Wait for PONG response (simplified - in real implementation, this would be async)
	buffer := make([]byte, 64) // Enough for encrypted response
	conn.conn.SetReadDeadline(time.Now().Add(2 * time.Second))
	n, err := conn.conn.Read(buffer)
	if err != nil {
		return 0
	}

	// Decrypt response if using Noise Protocol
	if conn.cipherState != nil {
		_, err = conn.cipherState.Decrypt(nil, nil, buffer[:n])
		if err != nil {
			return 0
		}
	}

	return time.Since(start)
}

// Stop stops the P2P node
func (p *P2PNode) Stop() {
	p.cancel()
	if p.listener != nil {
		p.listener.Close()
	}

	p.mu.Lock()
	defer p.mu.Unlock()
	for _, conn := range p.connections {
		conn.conn.Close()
	}
}

