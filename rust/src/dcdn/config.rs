//! Configuration system for DCDN

use serde::{Deserialize, Serialize};
use std::path::Path;
use anyhow::Result;

/// Main DCDN configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DcdnConfig {
    pub node: NodeConfig,
    pub network: NetworkConfig,
    pub quic: QuicConfig,
    pub storage: StorageConfig,
    pub fec: FecConfig,
    pub p2p: P2PConfig,
    pub crypto: CryptoConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NodeConfig {
    pub id: String,
    pub role: NodeRole,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum NodeRole {
    #[serde(rename = "edge")]
    Edge,
    #[serde(rename = "relay")]
    Relay,
    #[serde(rename = "origin")]
    Origin,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NetworkConfig {
    pub listen_addr: String,
    pub control_plane_addr: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QuicConfig {
    pub max_concurrent_connections: usize,
    pub max_streams_per_connection: u64,
    pub congestion_algorithm: CongestionAlgo,
    pub enable_gso: bool,
    pub idle_timeout_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum CongestionAlgo {
    #[serde(rename = "bbr")]
    BBR,
    #[serde(rename = "cubic")]
    CUBIC,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StorageConfig {
    pub ring_buffer_size_mb: usize,
    pub chunk_ttl_seconds: u64,
    pub max_memory_mb: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FecConfig {
    pub default_block_size: usize,
    pub default_parity_count: usize,
    pub adaptive: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct P2PConfig {
    pub max_upload_mbps: u64,
    pub max_download_mbps: u64,
    pub unchoke_interval_seconds: u64,
    pub regular_unchoke_count: usize,
    pub optimistic_unchoke_count: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CryptoConfig {
    pub signature_algorithm: String,
    pub key_rotation_days: u64,
}

impl Default for DcdnConfig {
    fn default() -> Self {
        Self {
            node: NodeConfig {
                id: "node-001".to_string(),
                role: NodeRole::Edge,
            },
            network: NetworkConfig {
                listen_addr: "0.0.0.0:4433".to_string(),
                control_plane_addr: "control.example.com:50051".to_string(),
            },
            quic: QuicConfig {
                max_concurrent_connections: 1000,
                max_streams_per_connection: 256,
                congestion_algorithm: CongestionAlgo::BBR,
                enable_gso: true,
                idle_timeout_ms: 30000,
            },
            storage: StorageConfig {
                ring_buffer_size_mb: 100,
                chunk_ttl_seconds: 120,
                max_memory_mb: 500,
            },
            fec: FecConfig {
                default_block_size: 16,
                default_parity_count: 2,
                adaptive: true,
            },
            p2p: P2PConfig {
                max_upload_mbps: 50,
                max_download_mbps: 100,
                unchoke_interval_seconds: 10,
                regular_unchoke_count: 4,
                optimistic_unchoke_count: 1,
            },
            crypto: CryptoConfig {
                signature_algorithm: "ed25519".to_string(),
                key_rotation_days: 30,
            },
        }
    }
}

impl DcdnConfig {
    /// Load configuration from TOML file
    pub fn from_file<P: AsRef<Path>>(path: P) -> Result<Self> {
        let content = std::fs::read_to_string(path)?;
        let config: DcdnConfig = toml::from_str(&content)?;
        config.validate()?;
        Ok(config)
    }

    /// Save configuration to TOML file
    pub fn to_file<P: AsRef<Path>>(&self, path: P) -> Result<()> {
        let content = toml::to_string_pretty(self)?;
        std::fs::write(path, content)?;
        Ok(())
    }

    /// Validate configuration parameters
    fn validate(&self) -> Result<()> {
        if self.storage.ring_buffer_size_mb == 0 {
            anyhow::bail!("ring_buffer_size_mb must be > 0");
        }
        if self.fec.default_parity_count >= self.fec.default_block_size {
            anyhow::bail!("default_parity_count must be < default_block_size");
        }
        if self.p2p.regular_unchoke_count == 0 {
            anyhow::bail!("regular_unchoke_count must be > 0");
        }
        Ok(())
    }
}

impl FecConfig {
    /// Select FEC parameters based on network conditions
    pub fn select_params(&self, latency_budget_ms: u32, loss_rate: f32) -> (usize, usize) {
        if !self.adaptive {
            return (self.default_block_size, self.default_parity_count);
        }

        let block_size = match latency_budget_ms {
            0..=100 => 8,      // Ultra-low latency
            101..=200 => 16,   // Low latency
            201..=500 => 32,   // Moderate
            _ => 64,           // Standard
        };

        let parity_count = Self::calculate_parity(block_size, loss_rate);
        (block_size, parity_count)
    }

    fn calculate_parity(k: usize, loss_rate: f32) -> usize {
        // Meta's formula: m = ceil(k × loss_rate × safety_factor)
        let safety_factor = 1.5;
        let m = (k as f32 * loss_rate * safety_factor).ceil() as usize;
        m.clamp(2, k / 2)  // Minimum 2, maximum 50% overhead
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_config_valid() {
        let config = DcdnConfig::default();
        assert!(config.validate().is_ok());
    }

    #[test]
    fn test_fec_adaptive_params() {
        let config = FecConfig {
            default_block_size: 16,
            default_parity_count: 2,
            adaptive: true,
        };

        // Ultra-low latency
        let (block, parity) = config.select_params(50, 0.01);
        assert_eq!(block, 8);
        assert!(parity >= 2);

        // High loss rate
        let (block, parity) = config.select_params(200, 0.05);
        assert_eq!(block, 16);
        assert!(parity > 2);
    }
}
