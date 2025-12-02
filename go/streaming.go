// Package main provides streaming services for real-time communication.
// This implements the "golden rule": Go handles all networking.
// Python/CLI manages high-level operations, but actual network I/O is in Go.
package main

import (
	"context"
	"encoding/binary"
	"fmt"
	"io"
	"log"
	"net"
	"sync"
	"time"
)

// StreamType indicates the type of streaming data
type StreamType int

const (
	StreamTypeVideo StreamType = iota
	StreamTypeAudio
	StreamTypeChat
)

// GoStreamConfig holds configuration for streaming (Go-internal)
type GoStreamConfig struct {
	Port          int
	MaxPacketSize int
	BufferSize    int
}

// DefaultGoStreamConfig returns default streaming configuration
func DefaultGoStreamConfig() GoStreamConfig {
	return GoStreamConfig{
		Port:          9996, // Default streaming port
		MaxPacketSize: 65000, // Safe UDP packet size (leave room for headers)
		BufferSize:    1024 * 1024, // 1MB buffer
	}
}

// StreamingService manages UDP and TCP streaming for video/audio/chat
// This is the Go network layer that Python calls via RPC
type StreamingService struct {
	config    GoStreamConfig
	udpConn   *net.UDPConn
	tcpListener net.Listener
	mu        sync.RWMutex
	running   bool
	ctx       context.Context
	cancel    context.CancelFunc

	// Callbacks for received data
	onVideoFrame  func(peerAddr string, frameID uint32, data []byte)
	onAudioChunk  func(peerAddr string, data []byte)
	onChatMessage func(peerAddr string, message string)

	// Peer connections for TCP chat
	tcpPeers map[string]net.Conn
	peerMu   sync.RWMutex
}

// NewStreamingService creates a new streaming service
func NewStreamingService(config GoStreamConfig) *StreamingService {
	ctx, cancel := context.WithCancel(context.Background())
	return &StreamingService{
		config:   config,
		ctx:      ctx,
		cancel:   cancel,
		tcpPeers: make(map[string]net.Conn),
	}
}

// SetVideoCallback sets the callback for received video frames
func (s *StreamingService) SetVideoCallback(cb func(peerAddr string, frameID uint32, data []byte)) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.onVideoFrame = cb
}

// SetAudioCallback sets the callback for received audio chunks
func (s *StreamingService) SetAudioCallback(cb func(peerAddr string, data []byte)) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.onAudioChunk = cb
}

// SetChatCallback sets the callback for received chat messages
func (s *StreamingService) SetChatCallback(cb func(peerAddr string, message string)) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.onChatMessage = cb
}

// StartUDP starts the UDP listener for video/audio streaming
func (s *StreamingService) StartUDP(port int) error {
	addr := &net.UDPAddr{
		Port: port,
		IP:   net.IPv4zero,
	}

	conn, err := net.ListenUDP("udp", addr)
	if err != nil {
		return fmt.Errorf("failed to start UDP listener: %w", err)
	}

	// Set large buffer for high-quality video
	if err := conn.SetReadBuffer(s.config.BufferSize); err != nil {
		log.Printf("Warning: failed to set UDP read buffer: %v", err)
	}
	if err := conn.SetWriteBuffer(s.config.BufferSize); err != nil {
		log.Printf("Warning: failed to set UDP write buffer: %v", err)
	}

	s.mu.Lock()
	s.udpConn = conn
	s.running = true
	s.mu.Unlock()

	log.Printf("📡 UDP streaming service started on port %d", port)

	// Start receiving goroutine
	go s.receiveUDP()

	return nil
}

// StartTCP starts the TCP listener for chat/reliable messaging
func (s *StreamingService) StartTCP(port int) error {
	listener, err := net.Listen("tcp", fmt.Sprintf(":%d", port))
	if err != nil {
		return fmt.Errorf("failed to start TCP listener: %w", err)
	}

	s.mu.Lock()
	s.tcpListener = listener
	s.mu.Unlock()

	log.Printf("💬 TCP chat service started on port %d", port)

	// Accept connections
	go s.acceptTCP()

	return nil
}

// receiveUDP handles incoming UDP packets
func (s *StreamingService) receiveUDP() {
	buffer := make([]byte, s.config.MaxPacketSize+100) // Extra for headers

	for {
		select {
		case <-s.ctx.Done():
			return
		default:
		}

		// Set read deadline for graceful shutdown
		s.udpConn.SetReadDeadline(time.Now().Add(1 * time.Second))

		n, remoteAddr, err := s.udpConn.ReadFromUDP(buffer)
		if err != nil {
			if netErr, ok := err.(net.Error); ok && netErr.Timeout() {
				continue // Timeout is normal, just retry
			}
			if s.running {
				log.Printf("UDP read error: %v", err)
			}
			continue
		}

		if n < 8 {
			continue // Too small, skip
		}

		// Parse header: [streamType:1][frameID:4][packetNum:2][totalPackets:2][data...]
		streamType := StreamType(buffer[0])
		frameID := binary.BigEndian.Uint32(buffer[1:5])
		_ = binary.BigEndian.Uint16(buffer[5:7]) // packetNum (for future fragmentation)
		_ = binary.BigEndian.Uint16(buffer[7:9]) // totalPackets

		data := buffer[9:n]
		peerAddr := remoteAddr.String()

		s.mu.RLock()
		switch streamType {
		case StreamTypeVideo:
			if s.onVideoFrame != nil {
				s.onVideoFrame(peerAddr, frameID, data)
			}
		case StreamTypeAudio:
			if s.onAudioChunk != nil {
				s.onAudioChunk(peerAddr, data)
			}
		}
		s.mu.RUnlock()
	}
}

// acceptTCP accepts incoming TCP connections for chat
func (s *StreamingService) acceptTCP() {
	for {
		conn, err := s.tcpListener.Accept()
		if err != nil {
			select {
			case <-s.ctx.Done():
				return
			default:
				log.Printf("TCP accept error: %v", err)
				continue
			}
		}

		peerAddr := conn.RemoteAddr().String()
		s.peerMu.Lock()
		s.tcpPeers[peerAddr] = conn
		s.peerMu.Unlock()

		log.Printf("💬 New chat connection from %s", peerAddr)

		go s.handleTCPConnection(conn)
	}
}

// handleTCPConnection handles a single TCP chat connection
func (s *StreamingService) handleTCPConnection(conn net.Conn) {
	defer conn.Close()
	peerAddr := conn.RemoteAddr().String()

	defer func() {
		s.peerMu.Lock()
		delete(s.tcpPeers, peerAddr)
		s.peerMu.Unlock()
	}()

	buffer := make([]byte, 4096)
	for {
		select {
		case <-s.ctx.Done():
			return
		default:
		}

		conn.SetReadDeadline(time.Now().Add(30 * time.Second))
		n, err := conn.Read(buffer)
		if err != nil {
			if err != io.EOF {
				log.Printf("Chat read error from %s: %v", peerAddr, err)
			}
			return
		}

		message := string(buffer[:n])
		s.mu.RLock()
		if s.onChatMessage != nil {
			s.onChatMessage(peerAddr, message)
		}
		s.mu.RUnlock()
	}
}

// SendVideoFrame sends a video frame via UDP
func (s *StreamingService) SendVideoFrame(peerAddr *net.UDPAddr, frameID uint32, data []byte) error {
	if s.udpConn == nil {
		return fmt.Errorf("UDP not started")
	}

	// Check if data is too large for a single packet
	if len(data) > s.config.MaxPacketSize {
		return s.sendFragmentedFrame(peerAddr, frameID, data)
	}

	// Build packet: [streamType:1][frameID:4][packetNum:2][totalPackets:2][data...]
	packet := make([]byte, 9+len(data))
	packet[0] = byte(StreamTypeVideo)
	binary.BigEndian.PutUint32(packet[1:5], frameID)
	binary.BigEndian.PutUint16(packet[5:7], 0) // packetNum
	binary.BigEndian.PutUint16(packet[7:9], 1) // totalPackets
	copy(packet[9:], data)

	_, err := s.udpConn.WriteToUDP(packet, peerAddr)
	return err
}

// sendFragmentedFrame sends a large frame in multiple packets
func (s *StreamingService) sendFragmentedFrame(peerAddr *net.UDPAddr, frameID uint32, data []byte) error {
	chunkSize := s.config.MaxPacketSize - 9 // Header size
	totalPackets := (len(data) + chunkSize - 1) / chunkSize

	for i := 0; i < totalPackets; i++ {
		start := i * chunkSize
		end := start + chunkSize
		if end > len(data) {
			end = len(data)
		}
		chunk := data[start:end]

		// Build packet
		packet := make([]byte, 9+len(chunk))
		packet[0] = byte(StreamTypeVideo)
		binary.BigEndian.PutUint32(packet[1:5], frameID)
		binary.BigEndian.PutUint16(packet[5:7], uint16(i))
		binary.BigEndian.PutUint16(packet[7:9], uint16(totalPackets))
		copy(packet[9:], chunk)

		if _, err := s.udpConn.WriteToUDP(packet, peerAddr); err != nil {
			return fmt.Errorf("failed to send fragment %d/%d: %w", i+1, totalPackets, err)
		}
	}

	return nil
}

// SendAudioChunk sends an audio chunk via UDP
func (s *StreamingService) SendAudioChunk(peerAddr *net.UDPAddr, data []byte) error {
	if s.udpConn == nil {
		return fmt.Errorf("UDP not started")
	}

	// Build packet: [streamType:1][reserved:8][data...]
	packet := make([]byte, 9+len(data))
	packet[0] = byte(StreamTypeAudio)
	// Reserved bytes for future use (sync info, etc.)
	copy(packet[9:], data)

	_, err := s.udpConn.WriteToUDP(packet, peerAddr)
	return err
}

// SendChatMessage sends a chat message via TCP
func (s *StreamingService) SendChatMessage(peerAddr string, message string) error {
	s.peerMu.RLock()
	conn, exists := s.tcpPeers[peerAddr]
	s.peerMu.RUnlock()

	if !exists {
		return fmt.Errorf("peer %s not connected", peerAddr)
	}

	_, err := conn.Write([]byte(message))
	return err
}

// ConnectTCPPeer connects to a peer via TCP for chat
func (s *StreamingService) ConnectTCPPeer(host string, port int) error {
	addr := fmt.Sprintf("%s:%d", host, port)
	conn, err := net.DialTimeout("tcp", addr, 10*time.Second)
	if err != nil {
		return fmt.Errorf("failed to connect to %s: %w", addr, err)
	}

	peerAddr := conn.RemoteAddr().String()
	s.peerMu.Lock()
	s.tcpPeers[peerAddr] = conn
	s.peerMu.Unlock()

	log.Printf("💬 Connected to chat peer: %s", peerAddr)

	go s.handleTCPConnection(conn)

	return nil
}

// GetPeerAddress resolves a hostname/IP to a UDP address
func (s *StreamingService) GetPeerAddress(host string, port int) (*net.UDPAddr, error) {
	return net.ResolveUDPAddr("udp", fmt.Sprintf("%s:%d", host, port))
}

// Stop stops all streaming services
func (s *StreamingService) Stop() {
	s.cancel()

	s.mu.Lock()
	s.running = false
	if s.udpConn != nil {
		s.udpConn.Close()
	}
	if s.tcpListener != nil {
		s.tcpListener.Close()
	}
	s.mu.Unlock()

	s.peerMu.Lock()
	for _, conn := range s.tcpPeers {
		conn.Close()
	}
	s.tcpPeers = make(map[string]net.Conn)
	s.peerMu.Unlock()

	log.Printf("📡 Streaming service stopped")
}

// VideoFrameAssembler reassembles fragmented video frames
type VideoFrameAssembler struct {
	frames map[uint32]*frameBuffer
	mu     sync.Mutex
	maxAge time.Duration
}

type frameBuffer struct {
	packets     map[uint16][]byte
	totalPkts   uint16
	lastUpdate  time.Time
}

// NewVideoFrameAssembler creates a new frame assembler
func NewVideoFrameAssembler() *VideoFrameAssembler {
	va := &VideoFrameAssembler{
		frames: make(map[uint32]*frameBuffer),
		maxAge: 5 * time.Second,
	}
	go va.cleanup()
	return va
}

// AddPacket adds a packet to the assembler and returns complete frame if available
func (va *VideoFrameAssembler) AddPacket(frameID uint32, packetNum, totalPackets uint16, data []byte) ([]byte, bool) {
	va.mu.Lock()
	defer va.mu.Unlock()

	buf, exists := va.frames[frameID]
	if !exists {
		buf = &frameBuffer{
			packets:   make(map[uint16][]byte),
			totalPkts: totalPackets,
		}
		va.frames[frameID] = buf
	}

	buf.packets[packetNum] = data
	buf.lastUpdate = time.Now()

	// Check if complete
	if uint16(len(buf.packets)) == buf.totalPkts {
		// Assemble frame
		var assembled []byte
		for i := uint16(0); i < buf.totalPkts; i++ {
			assembled = append(assembled, buf.packets[i]...)
		}
		delete(va.frames, frameID)
		return assembled, true
	}

	return nil, false
}

// cleanup removes old incomplete frames
func (va *VideoFrameAssembler) cleanup() {
	ticker := time.NewTicker(1 * time.Second)
	defer ticker.Stop()

	for range ticker.C {
		va.mu.Lock()
		now := time.Now()
		for id, buf := range va.frames {
			if now.Sub(buf.lastUpdate) > va.maxAge {
				delete(va.frames, id)
			}
		}
		va.mu.Unlock()
	}
}

// StreamingStats tracks streaming statistics
type StreamingStats struct {
	FramesSent     uint64
	FramesReceived uint64
	BytesSent      uint64
	BytesReceived  uint64
	PacketsLost    uint64
	AvgLatencyMs   float64
	mu             sync.RWMutex
}

// RecordSent records a sent frame
func (s *StreamingStats) RecordSent(bytes int) {
	s.mu.Lock()
	s.FramesSent++
	s.BytesSent += uint64(bytes)
	s.mu.Unlock()
}

// RecordReceived records a received frame
func (s *StreamingStats) RecordReceived(bytes int) {
	s.mu.Lock()
	s.FramesReceived++
	s.BytesReceived += uint64(bytes)
	s.mu.Unlock()
}

// GetStats returns current statistics
func (s *StreamingStats) GetStats() (framesSent, framesRecv, bytesSent, bytesRecv uint64) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.FramesSent, s.FramesReceived, s.BytesSent, s.BytesReceived
}
