// Package communication provides P2P communication using libp2p for chat, voice, and video.
// This module follows the Golden Rule: Go handles all networking, Python handles AI and CLI.
package communication

import (
	"bufio"
	"context"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net"
	"os"
	"path/filepath"
	"sync"
	"time"

	"github.com/libp2p/go-libp2p/core/host"
	"github.com/libp2p/go-libp2p/core/network"
	"github.com/libp2p/go-libp2p/core/peer"
	"github.com/libp2p/go-libp2p/core/protocol"
)

// Protocol IDs for communication
const (
	ChatProtocol  protocol.ID = "/pangea/chat/1.0.0"
	VideoProtocol protocol.ID = "/pangea/video/1.0.0"
	VoiceProtocol protocol.ID = "/pangea/voice/1.0.0"

	// Stream read timeout for context-aware reads
	StreamReadTimeout = 5 * time.Second

	// Debounce interval for saving chat history
	SaveDebounceInterval = 2 * time.Second
)

// ChatMessage represents a chat message
type ChatMessage struct {
	ID        string    `json:"id"`
	From      string    `json:"from"`
	To        string    `json:"to"`
	Content   string    `json:"content"`
	Timestamp time.Time `json:"timestamp"`
}

// VideoFrame represents a video frame for streaming
type VideoFrame struct {
	FrameID   uint32
	Width     uint16
	Height    uint16
	Quality   uint8
	Data      []byte
	Timestamp time.Time
}

// VoiceChunk represents an audio chunk for streaming
type VoiceChunk struct {
	SampleRate uint32
	Channels   uint8
	Data       []byte
	Timestamp  time.Time
}

// CommunicationService handles P2P communication for chat, voice, and video
type CommunicationService struct {
	host       host.Host
	ctx        context.Context
	cancel     context.CancelFunc
	mu         sync.RWMutex
	running    bool
	dataDir    string
	wg         sync.WaitGroup // Track goroutines for clean shutdown

	// Callbacks
	onChatMessage func(msg ChatMessage)
	onVideoFrame  func(peerID string, frame VideoFrame)
	onVoiceChunk  func(peerID string, chunk VoiceChunk)

	// Chat history storage
	chatHistory     map[string][]ChatMessage // key: peer ID
	chatHistoryFile string
	historyMu       sync.RWMutex

	// Debounced save mechanism (fixes race condition from review comment)
	saveChan      chan struct{}
	saveTimer     *time.Timer
	saveTimerMu   sync.Mutex

	// Connected peers for streaming
	chatStreams  map[peer.ID]network.Stream
	videoStreams map[peer.ID]network.Stream
	voiceStreams map[peer.ID]network.Stream
	streamMu     sync.RWMutex
}

// Config holds configuration for the communication service
type Config struct {
	DataDir string // Directory for storing chat history
}

// NewCommunicationService creates a new communication service
func NewCommunicationService(h host.Host, cfg Config) *CommunicationService {
	ctx, cancel := context.WithCancel(context.Background())

	dataDir := cfg.DataDir
	if dataDir == "" {
		homeDir, err := os.UserHomeDir()
		if err != nil {
			dataDir = "/tmp/pangea"
		} else {
			dataDir = filepath.Join(homeDir, ".pangea", "communication")
		}
	}

	// Ensure data directory exists
	if err := os.MkdirAll(dataDir, 0755); err != nil {
		log.Printf("Warning: could not create data directory: %v", err)
	}

	cs := &CommunicationService{
		host:            h,
		ctx:             ctx,
		cancel:          cancel,
		dataDir:         dataDir,
		chatHistory:     make(map[string][]ChatMessage),
		chatHistoryFile: filepath.Join(dataDir, "chat_history.json"),
		chatStreams:     make(map[peer.ID]network.Stream),
		videoStreams:    make(map[peer.ID]network.Stream),
		voiceStreams:    make(map[peer.ID]network.Stream),
		saveChan:        make(chan struct{}, 1), // Buffered channel for debouncing
	}

	// Load existing chat history
	cs.loadChatHistory()

	return cs
}

// Start initializes the communication service and sets up protocol handlers
func (cs *CommunicationService) Start() error {
	cs.mu.Lock()
	defer cs.mu.Unlock()

	if cs.running {
		return nil
	}

	// Set up stream handlers for each protocol
	cs.host.SetStreamHandler(ChatProtocol, cs.handleChatStream)
	cs.host.SetStreamHandler(VideoProtocol, cs.handleVideoStream)
	cs.host.SetStreamHandler(VoiceProtocol, cs.handleVoiceStream)

	// Start debounced save goroutine
	cs.wg.Add(1)
	go cs.debouncedSaveLoop()

	cs.running = true
	log.Printf("💬 Communication service started")
	log.Printf("   Chat Protocol:  %s", ChatProtocol)
	log.Printf("   Video Protocol: %s", VideoProtocol)
	log.Printf("   Voice Protocol: %s", VoiceProtocol)

	return nil
}

// debouncedSaveLoop handles debounced saving of chat history
// This fixes the race condition identified in review comment about spawning
// goroutines on every addToHistory call
func (cs *CommunicationService) debouncedSaveLoop() {
	defer cs.wg.Done()

	for {
		select {
		case <-cs.ctx.Done():
			// Final save before exit
			cs.saveChatHistory()
			return
		case <-cs.saveChan:
			// Debounce: wait for more save requests before actually saving
			cs.saveTimerMu.Lock()
			if cs.saveTimer != nil {
				cs.saveTimer.Stop()
			}
			cs.saveTimer = time.AfterFunc(SaveDebounceInterval, func() {
				cs.saveChatHistory()
			})
			cs.saveTimerMu.Unlock()
		}
	}
}

// Stop shuts down the communication service
func (cs *CommunicationService) Stop() error {
	cs.mu.Lock()
	if !cs.running {
		cs.mu.Unlock()
		return nil
	}
	cs.running = false
	cs.mu.Unlock()

	// Cancel context to signal all goroutines to stop
	cs.cancel()

	// Close all streams - this will unblock any blocking reads
	cs.streamMu.Lock()
	for _, s := range cs.chatStreams {
		s.Close()
	}
	for _, s := range cs.videoStreams {
		s.Close()
	}
	for _, s := range cs.voiceStreams {
		s.Close()
	}
	cs.chatStreams = make(map[peer.ID]network.Stream)
	cs.videoStreams = make(map[peer.ID]network.Stream)
	cs.voiceStreams = make(map[peer.ID]network.Stream)
	cs.streamMu.Unlock()

	// Wait for all goroutines to finish with timeout
	done := make(chan struct{})
	go func() {
		cs.wg.Wait()
		close(done)
	}()

	select {
	case <-done:
		// All goroutines finished
	case <-time.After(5 * time.Second):
		log.Printf("⚠️  Timeout waiting for goroutines to finish")
	}

	// Save chat history one final time
	cs.saveChatHistory()

	log.Printf("💬 Communication service stopped")

	return nil
}

// SetChatCallback sets the callback for incoming chat messages
func (cs *CommunicationService) SetChatCallback(cb func(msg ChatMessage)) {
	cs.mu.Lock()
	defer cs.mu.Unlock()
	cs.onChatMessage = cb
}

// SetVideoCallback sets the callback for incoming video frames
func (cs *CommunicationService) SetVideoCallback(cb func(peerID string, frame VideoFrame)) {
	cs.mu.Lock()
	defer cs.mu.Unlock()
	cs.onVideoFrame = cb
}

// SetVoiceCallback sets the callback for incoming voice chunks
func (cs *CommunicationService) SetVoiceCallback(cb func(peerID string, chunk VoiceChunk)) {
	cs.mu.Lock()
	defer cs.mu.Unlock()
	cs.onVoiceChunk = cb
}

// ============================================================================
// Chat Functions
// ============================================================================

// handleChatStream handles incoming chat connections with context-aware reads
// Fixes the blocking I/O issue identified in review comments by using deadlines
func (cs *CommunicationService) handleChatStream(stream network.Stream) {
	remotePeer := stream.Conn().RemotePeer()
	peerStr := remotePeer.String()
	if len(peerStr) > 12 {
		peerStr = peerStr[:12]
	}
	log.Printf("💬 New chat connection from peer: %s", peerStr)

	// Store the stream
	cs.streamMu.Lock()
	cs.chatStreams[remotePeer] = stream
	cs.streamMu.Unlock()

	defer func() {
		cs.streamMu.Lock()
		delete(cs.chatStreams, remotePeer)
		cs.streamMu.Unlock()
		stream.Close()
	}()

	reader := bufio.NewReader(stream)
	for {
		// Check context first
		select {
		case <-cs.ctx.Done():
			return
		default:
		}

		// Set read deadline to ensure we can check context periodically
		// This fixes the blocking ReadFull issue from review comments
		// Set read deadline directly on the stream
		stream.SetReadDeadline(time.Now().Add(StreamReadTimeout))
		// Read message length (4 bytes)
		lengthBuf := make([]byte, 4)
		_, err := io.ReadFull(reader, lengthBuf)
		if err != nil {
			if netErr, ok := err.(net.Error); ok && netErr.Timeout() {
				// Timeout is expected, continue loop to check context
				continue
			}
			if err != io.EOF && cs.ctx.Err() == nil {
				log.Printf("Chat read error: %v", err)
			}
			return
		}

		length := binary.BigEndian.Uint32(lengthBuf)
		if length > 1024*1024 { // Max 1MB message
			log.Printf("Chat message too large: %d bytes", length)
			return
		}

		// Read message content
		msgBuf := make([]byte, length)
		if _, err := io.ReadFull(reader, msgBuf); err != nil {
			if cs.ctx.Err() == nil {
				log.Printf("Chat read error: %v", err)
			}
			return
		}

		// Parse message
		var msg ChatMessage
		if err := json.Unmarshal(msgBuf, &msg); err != nil {
			log.Printf("Chat parse error: %v", err)
			continue
		}

		msg.From = remotePeer.String()
		msg.Timestamp = time.Now()

		// Store in history
		cs.addToHistory(msg)

		// Invoke callback
		cs.mu.RLock()
		cb := cs.onChatMessage
		cs.mu.RUnlock()

		if cb != nil {
			cb(msg)
		}

		fromStr := msg.From
		if len(fromStr) > 12 {
			fromStr = fromStr[:12]
		}
		log.Printf("📨 Chat from %s: %s", fromStr, msg.Content)
	}
}

// SendChatMessage sends a chat message to a peer
func (cs *CommunicationService) SendChatMessage(peerID peer.ID, content string) error {
	msg := ChatMessage{
		ID:        fmt.Sprintf("%d", time.Now().UnixNano()),
		From:      cs.host.ID().String(),
		To:        peerID.String(),
		Content:   content,
		Timestamp: time.Now(),
	}

	// Get or create stream
	stream, err := cs.getChatStream(peerID)
	if err != nil {
		return fmt.Errorf("failed to get chat stream: %w", err)
	}

	// Serialize message
	msgData, err := json.Marshal(msg)
	if err != nil {
		return fmt.Errorf("failed to serialize message: %w", err)
	}

	// Send length-prefixed message
	lengthBuf := make([]byte, 4)
	binary.BigEndian.PutUint32(lengthBuf, uint32(len(msgData)))

	if _, err := stream.Write(lengthBuf); err != nil {
		return fmt.Errorf("failed to send message length: %w", err)
	}
	if _, err := stream.Write(msgData); err != nil {
		return fmt.Errorf("failed to send message: %w", err)
	}

	// Store in our history
	cs.addToHistory(msg)

	peerStr := peerID.String()
	if len(peerStr) > 12 {
		peerStr = peerStr[:12]
	}
	log.Printf("📤 Chat to %s: %s", peerStr, content)
	return nil
}

// getChatStream gets or creates a chat stream to a peer
func (cs *CommunicationService) getChatStream(peerID peer.ID) (network.Stream, error) {
	cs.streamMu.RLock()
	stream, exists := cs.chatStreams[peerID]
	cs.streamMu.RUnlock()

	if exists && stream != nil {
		return stream, nil
	}

	// Create new stream
	ctx, cancel := context.WithTimeout(cs.ctx, 10*time.Second)
	defer cancel()

	newStream, err := cs.host.NewStream(ctx, peerID, ChatProtocol)
	if err != nil {
		return nil, err
	}

	cs.streamMu.Lock()
	cs.chatStreams[peerID] = newStream
	cs.streamMu.Unlock()

	// Start reading from stream in background with proper tracking
	cs.wg.Add(1)
	go func() {
		defer cs.wg.Done()
		cs.handleChatStream(newStream)
	}()

	return newStream, nil
}

// GetChatHistory returns chat history for a peer
func (cs *CommunicationService) GetChatHistory(peerID string) []ChatMessage {
	cs.historyMu.RLock()
	defer cs.historyMu.RUnlock()

	history, exists := cs.chatHistory[peerID]
	if !exists {
		return []ChatMessage{}
	}

	// Return a copy
	result := make([]ChatMessage, len(history))
	copy(result, history)
	return result
}

// GetAllChatHistory returns all chat history
func (cs *CommunicationService) GetAllChatHistory() map[string][]ChatMessage {
	cs.historyMu.RLock()
	defer cs.historyMu.RUnlock()

	result := make(map[string][]ChatMessage)
	for k, v := range cs.chatHistory {
		messages := make([]ChatMessage, len(v))
		copy(messages, v)
		result[k] = messages
	}
	return result
}

// addToHistory adds a message to chat history with debounced saving
// Fixes race condition by using a channel-based debounce instead of goroutine per call
func (cs *CommunicationService) addToHistory(msg ChatMessage) {
	cs.historyMu.Lock()
	defer cs.historyMu.Unlock()

	// Determine the peer ID (the other party)
	peerID := msg.From
	if msg.From == cs.host.ID().String() {
		peerID = msg.To
	}

	cs.chatHistory[peerID] = append(cs.chatHistory[peerID], msg)

	// Keep only last 1000 messages per peer
	if len(cs.chatHistory[peerID]) > 1000 {
		cs.chatHistory[peerID] = cs.chatHistory[peerID][len(cs.chatHistory[peerID])-1000:]
	}

	// Signal debounced save (non-blocking)
	select {
	case cs.saveChan <- struct{}{}:
	default:
		// Channel already has a pending save signal
	}
}

// saveChatHistory saves chat history to disk
func (cs *CommunicationService) saveChatHistory() {
	cs.historyMu.RLock()
	defer cs.historyMu.RUnlock()

	data, err := json.MarshalIndent(cs.chatHistory, "", "  ")
	if err != nil {
		log.Printf("Failed to serialize chat history: %v", err)
		return
	}

	if err := os.WriteFile(cs.chatHistoryFile, data, 0644); err != nil {
		log.Printf("Failed to save chat history: %v", err)
	}
}

// loadChatHistory loads chat history from disk
func (cs *CommunicationService) loadChatHistory() {
	cs.historyMu.Lock()
	defer cs.historyMu.Unlock()

	data, err := os.ReadFile(cs.chatHistoryFile)
	if err != nil {
		if !os.IsNotExist(err) {
			log.Printf("Failed to load chat history: %v", err)
		}
		return
	}

	if err := json.Unmarshal(data, &cs.chatHistory); err != nil {
		log.Printf("Failed to parse chat history: %v", err)
	}
}

// ============================================================================
// Video Functions
// ============================================================================

// handleVideoStream handles incoming video streams with context-aware reads
func (cs *CommunicationService) handleVideoStream(stream network.Stream) {
	remotePeer := stream.Conn().RemotePeer()
	peerStr := remotePeer.String()
	if len(peerStr) > 12 {
		peerStr = peerStr[:12]
	}
	log.Printf("🎥 New video connection from peer: %s", peerStr)

	cs.streamMu.Lock()
	cs.videoStreams[remotePeer] = stream
	cs.streamMu.Unlock()

	defer func() {
		cs.streamMu.Lock()
		delete(cs.videoStreams, remotePeer)
		cs.streamMu.Unlock()
		stream.Close()
	}()

	// Use buffered reader for improved performance with small reads
	reader := bufio.NewReaderSize(stream, 64*1024) // 64KB buffer

	for {
		// Check context first
		select {
		case <-cs.ctx.Done():
			return
		default:
		}

		// Set read deadline for context-aware reads
		stream.SetReadDeadline(time.Now().Add(StreamReadTimeout))

		// Read frame header (12 bytes): frameID(4) + width(2) + height(2) + quality(1) + reserved(3)
		header := make([]byte, 12)
		_, err := io.ReadFull(reader, header)
		if err != nil {
			if netErr, ok := err.(net.Error); ok && netErr.Timeout() {
				continue
			}
			if err != io.EOF && cs.ctx.Err() == nil {
				log.Printf("Video header read error: %v", err)
			}
			return
		}

		frameID := binary.BigEndian.Uint32(header[0:4])
		width := binary.BigEndian.Uint16(header[4:6])
		height := binary.BigEndian.Uint16(header[6:8])
		quality := header[8]

		// Read data length (4 bytes)
		lengthBuf := make([]byte, 4)
		if _, err := io.ReadFull(reader, lengthBuf); err != nil {
			if cs.ctx.Err() == nil {
				log.Printf("Video length read error: %v", err)
			}
			return
		}
		dataLen := binary.BigEndian.Uint32(lengthBuf)

		if dataLen > 10*1024*1024 { // Max 10MB frame
			log.Printf("Video frame too large: %d bytes", dataLen)
			return
		}

		// Read frame data
		data := make([]byte, dataLen)
		if _, err := io.ReadFull(reader, data); err != nil {
			if cs.ctx.Err() == nil {
				log.Printf("Video data read error: %v", err)
			}
			return
		}

		frame := VideoFrame{
			FrameID:   frameID,
			Width:     width,
			Height:    height,
			Quality:   quality,
			Data:      data,
			Timestamp: time.Now(),
		}

		cs.mu.RLock()
		cb := cs.onVideoFrame
		cs.mu.RUnlock()

		if cb != nil {
			cb(remotePeer.String(), frame)
		}
	}
}

// SendVideoFrame sends a video frame to a peer
func (cs *CommunicationService) SendVideoFrame(peerID peer.ID, frame VideoFrame) error {
	stream, err := cs.getVideoStream(peerID)
	if err != nil {
		return fmt.Errorf("failed to get video stream: %w", err)
	}

	// Build header (12 bytes)
	header := make([]byte, 12)
	binary.BigEndian.PutUint32(header[0:4], frame.FrameID)
	binary.BigEndian.PutUint16(header[4:6], frame.Width)
	binary.BigEndian.PutUint16(header[6:8], frame.Height)
	header[8] = frame.Quality

	// Build length
	lengthBuf := make([]byte, 4)
	binary.BigEndian.PutUint32(lengthBuf, uint32(len(frame.Data)))

	// Send header + length + data
	if _, err := stream.Write(header); err != nil {
		return err
	}
	if _, err := stream.Write(lengthBuf); err != nil {
		return err
	}
	if _, err := stream.Write(frame.Data); err != nil {
		return err
	}

	return nil
}

// getVideoStream gets or creates a video stream to a peer
func (cs *CommunicationService) getVideoStream(peerID peer.ID) (network.Stream, error) {
	cs.streamMu.RLock()
	stream, exists := cs.videoStreams[peerID]
	cs.streamMu.RUnlock()

	if exists && stream != nil {
		return stream, nil
	}

	ctx, cancel := context.WithTimeout(cs.ctx, 10*time.Second)
	defer cancel()

	newStream, err := cs.host.NewStream(ctx, peerID, VideoProtocol)
	if err != nil {
		return nil, err
	}

	cs.streamMu.Lock()
	cs.videoStreams[peerID] = newStream
	cs.streamMu.Unlock()

	cs.wg.Add(1)
	go func() {
		defer cs.wg.Done()
		cs.handleVideoStream(newStream)
	}()

	return newStream, nil
}

// ============================================================================
// Voice Functions
// ============================================================================

// handleVoiceStream handles incoming voice streams with context-aware reads
func (cs *CommunicationService) handleVoiceStream(stream network.Stream) {
	remotePeer := stream.Conn().RemotePeer()
	peerStr := remotePeer.String()
	if len(peerStr) > 12 {
		peerStr = peerStr[:12]
	}
	log.Printf("🎤 New voice connection from peer: %s", peerStr)

	cs.streamMu.Lock()
	cs.voiceStreams[remotePeer] = stream
	cs.streamMu.Unlock()

	defer func() {
		cs.streamMu.Lock()
		delete(cs.voiceStreams, remotePeer)
		cs.streamMu.Unlock()
		stream.Close()
	}()

	for {
		// Check context first
		select {
		case <-cs.ctx.Done():
			return
		default:
		}

		// Set read deadline for context-aware reads
		stream.SetReadDeadline(time.Now().Add(StreamReadTimeout))

		// Read chunk header (8 bytes): sampleRate(4) + channels(1) + reserved(3)
		header := make([]byte, 8)
		_, err := io.ReadFull(stream, header)
		if err != nil {
			if netErr, ok := err.(net.Error); ok && netErr.Timeout() {
				continue
			}
			if err != io.EOF && cs.ctx.Err() == nil {
				log.Printf("Voice header read error: %v", err)
			}
			return
		}

		sampleRate := binary.BigEndian.Uint32(header[0:4])
		channels := header[4]

		// Read data length (4 bytes)
		lengthBuf := make([]byte, 4)
		if _, err := io.ReadFull(stream, lengthBuf); err != nil {
			if cs.ctx.Err() == nil {
				log.Printf("Voice length read error: %v", err)
			}
			return
		}
		dataLen := binary.BigEndian.Uint32(lengthBuf)

		if dataLen > 1024*1024 { // Max 1MB chunk
			log.Printf("Voice chunk too large: %d bytes", dataLen)
			return
		}

		// Read audio data
		data := make([]byte, dataLen)
		if _, err := io.ReadFull(stream, data); err != nil {
			if cs.ctx.Err() == nil {
				log.Printf("Voice data read error: %v", err)
			}
			return
		}

		chunk := VoiceChunk{
			SampleRate: sampleRate,
			Channels:   channels,
			Data:       data,
			Timestamp:  time.Now(),
		}

		cs.mu.RLock()
		cb := cs.onVoiceChunk
		cs.mu.RUnlock()

		if cb != nil {
			cb(remotePeer.String(), chunk)
		}
	}
}

// SendVoiceChunk sends a voice chunk to a peer
func (cs *CommunicationService) SendVoiceChunk(peerID peer.ID, chunk VoiceChunk) error {
	stream, err := cs.getVoiceStream(peerID)
	if err != nil {
		return fmt.Errorf("failed to get voice stream: %w", err)
	}

	// Build header (8 bytes)
	header := make([]byte, 8)
	binary.BigEndian.PutUint32(header[0:4], chunk.SampleRate)
	header[4] = chunk.Channels

	// Build length
	lengthBuf := make([]byte, 4)
	binary.BigEndian.PutUint32(lengthBuf, uint32(len(chunk.Data)))

	// Send header + length + data
	if _, err := stream.Write(header); err != nil {
		return err
	}
	if _, err := stream.Write(lengthBuf); err != nil {
		return err
	}
	if _, err := stream.Write(chunk.Data); err != nil {
		return err
	}

	return nil
}

// getVoiceStream gets or creates a voice stream to a peer
func (cs *CommunicationService) getVoiceStream(peerID peer.ID) (network.Stream, error) {
	cs.streamMu.RLock()
	stream, exists := cs.voiceStreams[peerID]
	cs.streamMu.RUnlock()

	if exists && stream != nil {
		return stream, nil
	}

	ctx, cancel := context.WithTimeout(cs.ctx, 10*time.Second)
	defer cancel()

	newStream, err := cs.host.NewStream(ctx, peerID, VoiceProtocol)
	if err != nil {
		return nil, err
	}

	cs.streamMu.Lock()
	cs.voiceStreams[peerID] = newStream
	cs.streamMu.Unlock()

	cs.wg.Add(1)
	go func() {
		defer cs.wg.Done()
		cs.handleVoiceStream(newStream)
	}()

	return newStream, nil
}

// ============================================================================
// Utility Functions
// ============================================================================

// GetConnectedChatPeers returns list of peers with active chat streams
func (cs *CommunicationService) GetConnectedChatPeers() []peer.ID {
	cs.streamMu.RLock()
	defer cs.streamMu.RUnlock()

	peers := make([]peer.ID, 0, len(cs.chatStreams))
	for peerID := range cs.chatStreams {
		peers = append(peers, peerID)
	}
	return peers
}

// GetConnectedVideoPeers returns list of peers with active video streams
func (cs *CommunicationService) GetConnectedVideoPeers() []peer.ID {
	cs.streamMu.RLock()
	defer cs.streamMu.RUnlock()

	peers := make([]peer.ID, 0, len(cs.videoStreams))
	for peerID := range cs.videoStreams {
		peers = append(peers, peerID)
	}
	return peers
}

// GetConnectedVoicePeers returns list of peers with active voice streams
func (cs *CommunicationService) GetConnectedVoicePeers() []peer.ID {
	cs.streamMu.RLock()
	defer cs.streamMu.RUnlock()

	peers := make([]peer.ID, 0, len(cs.voiceStreams))
	for peerID := range cs.voiceStreams {
		peers = append(peers, peerID)
	}
	return peers
}

// IsRunning returns whether the communication service is running
func (cs *CommunicationService) IsRunning() bool {
	cs.mu.RLock()
	defer cs.mu.RUnlock()
	return cs.running
}

// GetHost returns the underlying libp2p host
func (cs *CommunicationService) GetHost() host.Host {
	return cs.host
}

// GetChatHistoryFilePath returns the path to the chat history file
func (cs *CommunicationService) GetChatHistoryFilePath() string {
	return cs.chatHistoryFile
}
