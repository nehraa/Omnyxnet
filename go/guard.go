package main

import (
	"crypto/sha256"
	"crypto/subtle"
	"encoding/hex"
	"fmt"
	"log"
	"sync"
	"time"

	"github.com/libp2p/go-libp2p/core/network"
	"github.com/libp2p/go-libp2p/core/peer"
)

// GuardConfig holds configuration for the Guard Object
type GuardConfig struct {
	// Enable/disable whitelist checking
	EnableWhitelist bool
	// Enable/disable token verification
	EnableTokenAuth bool
	// Shared secret for token authentication
	SharedSecret []byte
	// Rate limiting: max requests per peer per minute
	MaxRequestsPerMin int
	// Banned peer timeout in seconds
	BanTimeoutSec int
}

// PeerStats tracks statistics for a peer
type PeerStats struct {
	RequestCount  int
	LastRequestAt time.Time
	BannedUntil   time.Time
	FailedAuth    int
}

// GuardObject implements security checks for incoming streams
type GuardObject struct {
	config GuardConfig

	// Whitelist of allowed peer IDs
	whitelist   map[peer.ID]bool
	whitelistMu sync.RWMutex

	// Token registry for authenticated sessions
	tokens   map[string]time.Time
	tokensMu sync.RWMutex

	// Peer statistics for rate limiting
	peerStats map[peer.ID]*PeerStats
	statsMu   sync.RWMutex

	// CES pipeline for processing authenticated data
	cesPipeline *CESPipeline

	// Shutdown channel for graceful cleanup goroutine termination
	stopChan chan struct{}
	stopped  bool
	stopMu   sync.Mutex
}

// NewGuardObject creates a new guard with the specified configuration
func NewGuardObject(config GuardConfig, cesPipeline *CESPipeline) *GuardObject {
	guard := &GuardObject{
		config:      config,
		whitelist:   make(map[peer.ID]bool),
		tokens:      make(map[string]time.Time),
		peerStats:   make(map[peer.ID]*PeerStats),
		cesPipeline: cesPipeline,
		stopChan:    make(chan struct{}),
	}

	// Start cleanup goroutine for expired tokens and stats
	go guard.cleanupLoop()

	return guard
}

// AddToWhitelist adds a peer to the whitelist
func (g *GuardObject) AddToWhitelist(peerID peer.ID) {
	g.whitelistMu.Lock()
	defer g.whitelistMu.Unlock()
	g.whitelist[peerID] = true
	log.Printf("🔓 Added peer %s to whitelist", peerID.ShortString())
}

// RemoveFromWhitelist removes a peer from the whitelist
func (g *GuardObject) RemoveFromWhitelist(peerID peer.ID) {
	g.whitelistMu.Lock()
	defer g.whitelistMu.Unlock()
	delete(g.whitelist, peerID)
	log.Printf("🔒 Removed peer %s from whitelist", peerID.ShortString())
}

// IsWhitelisted checks if a peer is whitelisted
func (g *GuardObject) IsWhitelisted(peerID peer.ID) bool {
	g.whitelistMu.RLock()
	defer g.whitelistMu.RUnlock()
	return g.whitelist[peerID]
}

// hashToken returns a SHA256 hash of the token for secure storage
func hashToken(token string) string {
	hash := sha256.Sum256([]byte(token))
	return hex.EncodeToString(hash[:])
}

// RegisterToken registers a new authentication token
// The token is hashed before storage to prevent token theft via memory dumps
func (g *GuardObject) RegisterToken(token string, validFor time.Duration) {
	g.tokensMu.Lock()
	defer g.tokensMu.Unlock()
	hashedToken := hashToken(token)
	g.tokens[hashedToken] = time.Now().Add(validFor)
	log.Printf("🔑 Registered auth token (expires in %v)", validFor)
}

// VerifyToken checks if a token is valid
// The token is hashed before lookup to match the stored hash
func (g *GuardObject) VerifyToken(token string) bool {
	g.tokensMu.RLock()
	defer g.tokensMu.RUnlock()

	hashedToken := hashToken(token)
	expiry, exists := g.tokens[hashedToken]
	if !exists {
		return false
	}

	return time.Now().Before(expiry)
}

// VerifySharedSecret verifies a shared secret using constant-time comparison
func (g *GuardObject) VerifySharedSecret(provided []byte) bool {
	if len(g.config.SharedSecret) == 0 {
		return true // No secret configured, allow
	}
	return subtle.ConstantTimeCompare(g.config.SharedSecret, provided) == 1
}

// CheckRateLimit checks if a peer has exceeded rate limits
func (g *GuardObject) CheckRateLimit(peerID peer.ID) error {
	g.statsMu.Lock()
	defer g.statsMu.Unlock()

	now := time.Now()
	stats, exists := g.peerStats[peerID]

	if !exists {
		// First request from this peer
		g.peerStats[peerID] = &PeerStats{
			RequestCount:  1,
			LastRequestAt: now,
		}
		return nil
	}

	// Check if peer is banned
	if now.Before(stats.BannedUntil) {
		return fmt.Errorf("peer is banned until %v", stats.BannedUntil)
	}

	// Reset counter if more than a minute has passed
	if now.Sub(stats.LastRequestAt) > time.Minute {
		stats.RequestCount = 1
		stats.LastRequestAt = now
		return nil
	}

	// Check rate limit
	stats.RequestCount++
	stats.LastRequestAt = now

	if stats.RequestCount > g.config.MaxRequestsPerMin {
		// Ban the peer
		stats.BannedUntil = now.Add(time.Duration(g.config.BanTimeoutSec) * time.Second)
		log.Printf("⛔ Peer %s exceeded rate limit, banned for %ds",
			peerID.ShortString(), g.config.BanTimeoutSec)
		return fmt.Errorf("rate limit exceeded")
	}

	return nil
}

// RecordFailedAuth records a failed authentication attempt
func (g *GuardObject) RecordFailedAuth(peerID peer.ID) {
	g.statsMu.Lock()
	defer g.statsMu.Unlock()

	stats, exists := g.peerStats[peerID]
	if !exists {
		stats = &PeerStats{}
		g.peerStats[peerID] = stats
	}

	stats.FailedAuth++

	// Ban after 5 failed attempts
	if stats.FailedAuth >= 5 {
		stats.BannedUntil = time.Now().Add(time.Duration(g.config.BanTimeoutSec) * time.Second)
		log.Printf("⛔ Peer %s banned after %d failed auth attempts",
			peerID.ShortString(), stats.FailedAuth)
	}
}

// AuthenticateStream performs all security checks on an incoming stream
func (g *GuardObject) AuthenticateStream(stream network.Stream, token string, secret []byte) error {
	peerID := stream.Conn().RemotePeer()

	// 1. Check rate limit
	if err := g.CheckRateLimit(peerID); err != nil {
		return fmt.Errorf("rate limit check failed: %w", err)
	}

	// 2. Check whitelist (if enabled)
	if g.config.EnableWhitelist && !g.IsWhitelisted(peerID) {
		g.RecordFailedAuth(peerID)
		return fmt.Errorf("peer %s not in whitelist", peerID.ShortString())
	}

	// 3. Verify token (if enabled)
	if g.config.EnableTokenAuth && !g.VerifyToken(token) {
		g.RecordFailedAuth(peerID)
		return fmt.Errorf("invalid or expired token")
	}

	// 4. Verify shared secret
	if !g.VerifySharedSecret(secret) {
		g.RecordFailedAuth(peerID)
		return fmt.Errorf("invalid shared secret")
	}

	log.Printf("✅ Stream authenticated for peer %s", peerID.ShortString())
	return nil
}

// ProcessAuthenticatedData passes authenticated data to CES pipeline
func (g *GuardObject) ProcessAuthenticatedData(data []byte) ([]ShardData, error) {
	if g.cesPipeline == nil {
		return nil, fmt.Errorf("CES pipeline not configured")
	}

	return g.cesPipeline.Process(data)
}

// cleanupLoop periodically cleans up expired tokens and old stats
func (g *GuardObject) cleanupLoop() {
	ticker := time.NewTicker(5 * time.Minute)
	defer ticker.Stop()

	for {
		select {
		case <-g.stopChan:
			log.Printf("🛑 Guard cleanup goroutine stopped")
			return
		case <-ticker.C:
			now := time.Now()

			// Clean expired tokens
			g.tokensMu.Lock()
			for token, expiry := range g.tokens {
				if now.After(expiry) {
					delete(g.tokens, token)
				}
			}
			g.tokensMu.Unlock()

			// Clean old stats (peers not seen in 1 hour)
			g.statsMu.Lock()
			for peerID, stats := range g.peerStats {
				if now.Sub(stats.LastRequestAt) > time.Hour && now.After(stats.BannedUntil) {
					delete(g.peerStats, peerID)
				}
			}
			g.statsMu.Unlock()
		}
	}
}

// Close stops the cleanup goroutine and releases resources
func (g *GuardObject) Close() {
	g.stopMu.Lock()
	defer g.stopMu.Unlock()

	if g.stopped {
		return
	}
	g.stopped = true
	close(g.stopChan)
	log.Printf("🔒 GuardObject closed")
}

// GetStats returns current statistics
func (g *GuardObject) GetStats() map[string]interface{} {
	g.whitelistMu.RLock()
	whitelistCount := len(g.whitelist)
	g.whitelistMu.RUnlock()

	g.tokensMu.RLock()
	tokenCount := len(g.tokens)
	g.tokensMu.RUnlock()

	g.statsMu.RLock()
	peerCount := len(g.peerStats)
	bannedCount := 0
	for _, stats := range g.peerStats {
		if time.Now().Before(stats.BannedUntil) {
			bannedCount++
		}
	}
	g.statsMu.RUnlock()

	return map[string]interface{}{
		"whitelist_size": whitelistCount,
		"active_tokens":  tokenCount,
		"tracked_peers":  peerCount,
		"banned_peers":   bannedCount,
		"config":         g.config,
	}
}
