use serde::{Deserialize, Serialize};
use std::fmt;
use std::time::{SystemTime, UNIX_EPOCH};

/// Node status enum matching Go implementation
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum NodeStatus {
    Active = 0,
    Purgatory = 1,
    Dead = 2,
}

impl From<u32> for NodeStatus {
    fn from(value: u32) -> Self {
        match value {
            0 => NodeStatus::Active,
            1 => NodeStatus::Purgatory,
            2 => NodeStatus::Dead,
            _ => NodeStatus::Dead,
        }
    }
}

/// Node represents a network node with quality metrics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Node {
    pub id: u32,
    pub status: NodeStatus,
    pub latency_ms: f32,
    pub threat_score: f32,
    pub jitter_ms: f32,
    pub packet_loss: f32,
    pub last_seen: u64,
}

impl Node {
    pub fn new(id: u32) -> Self {
        Self {
            id,
            status: NodeStatus::Active,
            latency_ms: 0.0,
            threat_score: 0.0,
            jitter_ms: 0.0,
            packet_loss: 0.0,
            last_seen: current_timestamp(),
        }
    }

    /// Update latency and calculate jitter
    pub fn update_latency(&mut self, new_latency: f32) {
        if self.latency_ms > 0.0 {
            let diff = (new_latency - self.latency_ms).abs();
            self.jitter_ms = self.jitter_ms * 0.8 + diff * 0.2; // Exponential moving average
        }
        self.latency_ms = new_latency;
        self.last_seen = current_timestamp();
    }

    /// Update threat score and potentially change status
    pub fn update_threat_score(&mut self, score: f32) {
        self.threat_score = score;
        self.status = if score > 0.8 {
            NodeStatus::Dead
        } else if score > 0.5 {
            NodeStatus::Purgatory
        } else {
            NodeStatus::Active
        };
        self.last_seen = current_timestamp();
    }

    /// Update packet loss percentage
    pub fn update_packet_loss(&mut self, loss: f32) {
        self.packet_loss = loss.clamp(0.0, 1.0);
        self.last_seen = current_timestamp();
    }

    /// Calculate overall health score (0.0 = unhealthy, 1.0 = perfect)
    pub fn health_score(&self) -> f32 {
        let latency_score = (1.0 - (self.latency_ms / 1000.0).min(1.0)) * 0.4;
        let jitter_score = (1.0 - (self.jitter_ms / 100.0).min(1.0)) * 0.3;
        let packet_score = (1.0 - self.packet_loss) * 0.3;
        latency_score + jitter_score + packet_score
    }
}

/// Connection quality metrics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConnectionQuality {
    pub latency_ms: f32,
    pub jitter_ms: f32,
    pub packet_loss: f32,
}

impl Default for ConnectionQuality {
    fn default() -> Self {
        Self {
            latency_ms: 0.0,
            jitter_ms: 0.0,
            packet_loss: 0.0,
        }
    }
}

/// Message to send between peers
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Message {
    pub to_peer_id: u32,
    pub data: Vec<u8>,
}

/// Peer address information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PeerAddress {
    pub peer_id: u32,
    pub host: String,
    pub port: u16,
}

impl fmt::Display for PeerAddress {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}:{}:{}", self.peer_id, self.host, self.port)
    }
}

/// Get current Unix timestamp in seconds
pub fn current_timestamp() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs()
}

/// Compression algorithm selection (Phase 1 requirement)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum CompressionAlgorithm {
    /// Zstandard - fast, good compression ratio (default)
    Zstd,
    /// Brotli - better compression for text, slower
    Brotli,
    /// No compression
    None,
}

impl Default for CompressionAlgorithm {
    fn default() -> Self {
        CompressionAlgorithm::Zstd
    }
}

/// Configuration for CES pipeline
#[derive(Debug, Clone)]
pub struct CesConfig {
    pub compression_level: i32,
    pub compression_algorithm: CompressionAlgorithm,
    pub shard_count: usize,
    pub parity_count: usize,
    pub chunk_size: usize,
}

impl CesConfig {
    /// Create adaptive config based on system capabilities and file size
    pub fn adaptive(
        caps: &crate::capabilities::HardwareCaps,
        file_size: u64,
        _bandwidth: f32,
    ) -> Self {
        let chunk_size = if caps.ram_gb > 16 {
            100 * 1024 * 1024 // 100 MB for high-memory systems
        } else if caps.ram_gb > 4 {
            10 * 1024 * 1024 // 10 MB for medium-memory systems
        } else {
            64 * 1024 // 64 KB for low-memory systems
        };

        let compression_level = if caps.cpu_cores > 8 { 9 } else { 3 };

        // Dynamic sharding based on file size
        let shard_count = ((file_size / chunk_size as u64).max(4).min(32)) as usize;
        let parity_count = shard_count / 2; // 50% redundancy

        Self {
            compression_level,
            compression_algorithm: CompressionAlgorithm::default(),
            shard_count,
            parity_count,
            chunk_size,
        }
    }

    pub fn default() -> Self {
        Self {
            compression_level: 3,
            compression_algorithm: CompressionAlgorithm::default(),
            shard_count: 8,
            parity_count: 4,
            chunk_size: 1024 * 1024, // 1 MB
        }
    }
}
