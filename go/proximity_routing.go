package main

import (
	"sort"
	"sync"
	"time"

	"github.com/libp2p/go-libp2p/core/peer"
)

// PeerProximity represents proximity information for a peer
type PeerProximity struct {
	PeerID     peer.ID
	RTT        time.Duration
	LastUpdate time.Time
	Score      float64 // Combined proximity score (0-1, higher is better)
}

// ProximityRouter implements RTT-aware peer selection
type ProximityRouter struct {
	mu          sync.RWMutex
	proximity   map[peer.ID]*PeerProximity
	pingService *PingService
}

// PingService provides RTT measurements (simplified interface)
type PingService interface {
	Ping(peer.ID) (time.Duration, error)
}

// NewProximityRouter creates a new proximity-based router
func NewProximityRouter(pingService *PingService) *ProximityRouter {
	return &ProximityRouter{
		proximity:   make(map[peer.ID]*PeerProximity),
		pingService: pingService,
	}
}

// UpdateRTT updates the RTT for a peer
func (pr *ProximityRouter) UpdateRTT(peerID peer.ID, rtt time.Duration) {
	pr.mu.Lock()
	defer pr.mu.Unlock()

	prox, exists := pr.proximity[peerID]
	if !exists {
		prox = &PeerProximity{
			PeerID: peerID,
		}
		pr.proximity[peerID] = prox
	}

	prox.RTT = rtt
	prox.LastUpdate = time.Now()
	prox.Score = pr.calculateScore(rtt)
}

// calculateScore converts RTT to a proximity score (0-1)
func (pr *ProximityRouter) calculateScore(rtt time.Duration) float64 {
	// Score decreases with RTT
	// < 10ms = 1.0 (excellent)
	// < 50ms = 0.8 (very good)
	// < 100ms = 0.6 (good)
	// < 200ms = 0.4 (acceptable)
	// < 500ms = 0.2 (poor)
	// >= 500ms = 0.1 (very poor)

	ms := float64(rtt.Milliseconds())
	switch {
	case ms < 10:
		return 1.0
	case ms < 50:
		return 0.8 + (50-ms)/40*0.2 // Linear interpolation
	case ms < 100:
		return 0.6 + (100-ms)/50*0.2
	case ms < 200:
		return 0.4 + (200-ms)/100*0.2
	case ms < 500:
		return 0.2 + (500-ms)/300*0.2
	default:
		return 0.1
	}
}

// GetBestPeers returns the N best peers sorted by proximity
func (pr *ProximityRouter) GetBestPeers(n int) []peer.ID {
	pr.mu.RLock()
	defer pr.mu.RUnlock()

	// Convert map to slice for sorting
	proximities := make([]*PeerProximity, 0, len(pr.proximity))
	now := time.Now()

	for _, prox := range pr.proximity {
		// Only include peers with recent measurements (< 5 minutes old)
		if now.Sub(prox.LastUpdate) < 5*time.Minute {
			proximities = append(proximities, prox)
		}
	}

	// Sort by score (highest first)
	sort.Slice(proximities, func(i, j int) bool {
		return proximities[i].Score > proximities[j].Score
	})

	// Take top N
	count := n
	if count > len(proximities) {
		count = len(proximities)
	}

	result := make([]peer.ID, count)
	for i := 0; i < count; i++ {
		result[i] = proximities[i].PeerID
	}

	return result
}

// GetPeersByRTT returns peers within a specific RTT range
func (pr *ProximityRouter) GetPeersByRTT(maxRTT time.Duration) []peer.ID {
	pr.mu.RLock()
	defer pr.mu.RUnlock()

	result := make([]peer.ID, 0)
	now := time.Now()

	for peerID, prox := range pr.proximity {
		// Check if measurement is recent and RTT is within range
		if now.Sub(prox.LastUpdate) < 5*time.Minute && prox.RTT <= maxRTT {
			result = append(result, peerID)
		}
	}

	return result
}

// SelectUploadTargets selects optimal peers for file upload
// Returns peers sorted by proximity, up to the requested count
func (pr *ProximityRouter) SelectUploadTargets(targetCount int, excludePeers []peer.ID) []peer.ID {
	pr.mu.RLock()
	defer pr.mu.RUnlock()

	// Create exclusion map
	exclude := make(map[peer.ID]bool)
	for _, pid := range excludePeers {
		exclude[pid] = true
	}

	// Collect eligible peers
	proximities := make([]*PeerProximity, 0)
	now := time.Now()

	for peerID, prox := range pr.proximity {
		if exclude[peerID] {
			continue
		}
		if now.Sub(prox.LastUpdate) < 5*time.Minute {
			proximities = append(proximities, prox)
		}
	}

	// Sort by score
	sort.Slice(proximities, func(i, j int) bool {
		return proximities[i].Score > proximities[j].Score
	})

	// Prefer geographically diverse peers (avoid clustering)
	// This is a simple strategy: take every Nth peer to increase diversity
	diversityFactor := 1
	if len(proximities) > targetCount*2 {
		diversityFactor = 2
	}

	result := make([]peer.ID, 0, targetCount)
	idx := 0
	for len(result) < targetCount && idx < len(proximities) {
		result = append(result, proximities[idx].PeerID)
		idx += diversityFactor
		
		// If we run out using diversity factor, go back and fill remaining
		if idx >= len(proximities) && len(result) < targetCount {
			diversityFactor = 1
			idx = len(result) // Continue from where we left off
		}
	}

	return result
}

// GetProximityInfo returns proximity information for a peer
func (pr *ProximityRouter) GetProximityInfo(peerID peer.ID) (*PeerProximity, bool) {
	pr.mu.RLock()
	defer pr.mu.RUnlock()

	prox, exists := pr.proximity[peerID]
	if !exists {
		return nil, false
	}

	// Return a copy to avoid race conditions
	proxCopy := *prox
	return &proxCopy, true
}

// RefreshPeerRTT actively pings a peer to update RTT
func (pr *ProximityRouter) RefreshPeerRTT(peerID peer.ID) error {
	if pr.pingService == nil {
		return nil // Ping service not configured
	}

	rtt, err := (*pr.pingService).Ping(peerID)
	if err != nil {
		return err
	}

	pr.UpdateRTT(peerID, rtt)
	return nil
}

// StartProximityMonitoring periodically updates RTT for all known peers
func (pr *ProximityRouter) StartProximityMonitoring(interval time.Duration) {
	if pr.pingService == nil {
		return
	}

	go func() {
		ticker := time.NewTicker(interval)
		defer ticker.Stop()

		for range ticker.C {
			pr.mu.RLock()
			peers := make([]peer.ID, 0, len(pr.proximity))
			for peerID := range pr.proximity {
				peers = append(peers, peerID)
			}
			pr.mu.RUnlock()

			// Ping each peer
			for _, peerID := range peers {
				pr.RefreshPeerRTT(peerID)
				// Small delay to avoid overwhelming the network
				time.Sleep(100 * time.Millisecond)
			}
		}
	}()
}

// GetStats returns proximity routing statistics
func (pr *ProximityRouter) GetStats() map[string]interface{} {
	pr.mu.RLock()
	defer pr.mu.RUnlock()

	totalPeers := len(pr.proximity)
	recentPeers := 0
	avgRTT := time.Duration(0)
	now := time.Now()

	for _, prox := range pr.proximity {
		if now.Sub(prox.LastUpdate) < 5*time.Minute {
			recentPeers++
			avgRTT += prox.RTT
		}
	}

	if recentPeers > 0 {
		avgRTT = avgRTT / time.Duration(recentPeers)
	}

	return map[string]interface{}{
		"total_peers":  totalPeers,
		"recent_peers": recentPeers,
		"avg_rtt_ms":   avgRTT.Milliseconds(),
	}
}
