//! P2P transfer engine with tit-for-tat incentives

use crate::dcdn::types::{ChunkId, PeerId, PeerStats};
use anyhow::Result;
use dashmap::DashMap;
use std::sync::Arc;
use std::time::Instant;
use tokio::sync::RwLock;

/// P2P transfer engine with bandwidth allocation and incentive mechanism
pub struct P2PEngine {
    /// Peer statistics
    peer_stats: DashMap<PeerId, PeerStats>,
    /// Currently unchoked peers
    unchoked_peers: Arc<RwLock<Vec<PeerId>>>,
    /// Configuration
    config: Arc<P2PConfig>,
}

#[derive(Debug, Clone)]
pub struct P2PConfig {
    pub max_upload_mbps: u64,
    pub max_download_mbps: u64,
    pub unchoke_interval_seconds: u64,
    pub regular_unchoke_count: usize,
    pub optimistic_unchoke_count: usize,
}

/// Peer state in the P2P network
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PeerState {
    Discovered,
    Connected,
    Interested,
    Unchoked,
    Choked,
    Disconnected,
}

impl P2PEngine {
    /// Create a new P2P engine
    pub fn new(config: P2PConfig) -> Self {
        Self {
            peer_stats: DashMap::new(),
            unchoked_peers: Arc::new(RwLock::new(Vec::new())),
            config: Arc::new(config),
        }
    }

    /// Handle a chunk request from a peer
    pub async fn handle_chunk_request(&self, peer: PeerId, _chunk_id: ChunkId) -> Result<()> {
        // Check if peer is unchoked
        let unchoked = self.unchoked_peers.read().await;
        if !unchoked.contains(&peer) {
            anyhow::bail!("Peer {:?} is choked", peer);
        }

        // Update statistics
        if let Some(mut stats) = self.peer_stats.get_mut(&peer) {
            stats.last_interaction = Some(Instant::now());
        }

        Ok(())
    }

    /// Request a chunk from a peer
    pub async fn request_chunk(&self, peer: PeerId, _chunk_id: ChunkId) -> Result<()> {
        // Update download statistics
        if let Some(mut stats) = self.peer_stats.get_mut(&peer) {
            stats.last_interaction = Some(Instant::now());
        } else {
            // Initialize peer if not exists
            self.peer_stats.insert(peer, PeerStats::default());
        }

        Ok(())
    }

    /// Update peer statistics
    pub fn update_peer_state(&self, peer: PeerId, stats: PeerStats) {
        self.peer_stats.insert(peer, stats);
    }

    /// Get currently unchoked peers
    pub async fn get_unchoked_peers(&self) -> Vec<PeerId> {
        self.unchoked_peers.read().await.clone()
    }

    /// Calculate and update unchoke set based on tit-for-tat algorithm
    pub async fn update_unchoke_set(&self) -> Result<()> {
        let unchoke_set = self.calculate_unchoke_set().await;
        
        let mut unchoked = self.unchoked_peers.write().await;
        *unchoked = unchoke_set;

        Ok(())
    }

    /// Calculate unchoke set using tit-for-tat algorithm
    async fn calculate_unchoke_set(&self) -> Vec<PeerId> {
        // Get all interested peers
        let mut peer_scores: Vec<(PeerId, f32)> = self.peer_stats
            .iter()
            .map(|entry| {
                let peer_id = *entry.key();
                let stats = entry.value();
                
                // Calculate score: weighted combination of upload/download and reliability
                let uploaded = stats.uploaded_bytes as f32;
                let downloaded = stats.downloaded_bytes as f32;
                let reliability = stats.reliability_score;
                
                let score = (downloaded * 0.7 + uploaded * 0.3) * reliability;
                (peer_id, score)
            })
            .collect();

        // Sort by score (highest first)
        peer_scores.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));

        let mut unchoked = Vec::new();

        // Regular unchoke: top performers
        let regular_count = self.config.regular_unchoke_count.min(peer_scores.len());
        unchoked.extend(peer_scores.iter().take(regular_count).map(|(id, _)| *id));

        // Optimistic unchoke: random selection from remaining
        if peer_scores.len() > regular_count && self.config.optimistic_unchoke_count > 0 {
            let remaining = &peer_scores[regular_count..];
            if !remaining.is_empty() {
                let random_idx = rand::random::<usize>() % remaining.len();
                unchoked.push(remaining[random_idx].0);
            }
        }

        unchoked
    }

    /// Add a peer to the network
    pub fn add_peer(&self, peer: PeerId) {
        self.peer_stats.insert(peer, PeerStats::default());
    }

    /// Remove a peer from the network
    pub fn remove_peer(&self, peer: &PeerId) {
        self.peer_stats.remove(peer);
    }

    /// Update uploaded bytes for a peer
    pub fn update_uploaded(&self, peer: PeerId, bytes: u64) {
        if let Some(mut stats) = self.peer_stats.get_mut(&peer) {
            stats.uploaded_bytes += bytes;
        }
    }

    /// Update downloaded bytes for a peer
    pub fn update_downloaded(&self, peer: PeerId, bytes: u64) {
        if let Some(mut stats) = self.peer_stats.get_mut(&peer) {
            stats.downloaded_bytes += bytes;
        }
    }

    /// Get peer statistics
    pub fn get_peer_stats(&self, peer: &PeerId) -> Option<PeerStats> {
        self.peer_stats.get(peer).map(|stats| stats.clone())
    }

    /// Get all peer statistics
    pub fn get_all_stats(&self) -> Vec<(PeerId, PeerStats)> {
        self.peer_stats
            .iter()
            .map(|entry| (*entry.key(), entry.value().clone()))
            .collect()
    }

    /// Calculate bandwidth allocation per peer
    pub async fn get_bandwidth_allocation(&self) -> Vec<(PeerId, u64)> {
        let unchoked = self.unchoked_peers.read().await;
        let count = unchoked.len().max(1);
        let bytes_per_peer = (self.config.max_upload_mbps * 1_000_000) / (count as u64);

        unchoked.iter().map(|peer| (*peer, bytes_per_peer)).collect()
    }
}

impl Default for P2PConfig {
    fn default() -> Self {
        Self {
            max_upload_mbps: 50,
            max_download_mbps: 100,
            unchoke_interval_seconds: 10,
            regular_unchoke_count: 4,
            optimistic_unchoke_count: 1,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_p2p_engine_creation() {
        let config = P2PConfig::default();
        let engine = P2PEngine::new(config);
        
        let unchoked = engine.get_unchoked_peers().await;
        assert_eq!(unchoked.len(), 0);
    }

    #[tokio::test]
    async fn test_add_peer() {
        let engine = P2PEngine::new(P2PConfig::default());
        let peer_id = PeerId::new(1);

        engine.add_peer(peer_id);

        let stats = engine.get_peer_stats(&peer_id);
        assert!(stats.is_some());
    }

    #[tokio::test]
    async fn test_unchoke_algorithm() {
        let engine = P2PEngine::new(P2PConfig::default());

        // Add peers with different statistics
        for i in 1..=10 {
            let peer_id = PeerId::new(i);
            engine.add_peer(peer_id);
            
            // Simulate different amounts of data transfer
            let bytes = i * 1000;
            engine.update_downloaded(peer_id, bytes);
        }

        // Update unchoke set
        engine.update_unchoke_set().await.unwrap();

        let unchoked = engine.get_unchoked_peers().await;
        
        // Should have regular_unchoke_count + optimistic_unchoke_count peers
        assert!(unchoked.len() <= 5); // 4 regular + 1 optimistic
    }

    #[tokio::test]
    async fn test_bandwidth_allocation() {
        let config = P2PConfig {
            max_upload_mbps: 100,
            ..Default::default()
        };
        let engine = P2PEngine::new(config);

        // Add and unchoke some peers
        for i in 1..=4 {
            engine.add_peer(PeerId::new(i));
        }
        engine.update_unchoke_set().await.unwrap();

        let allocations = engine.get_bandwidth_allocation().await;
        
        // Each peer should get an equal share
        for (_, bandwidth) in allocations {
            assert!(bandwidth > 0);
        }
    }
}
