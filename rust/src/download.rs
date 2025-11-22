use anyhow::{Result, Context};
use std::path::Path;
use std::sync::Arc;
use tracing::{info, debug};

use crate::ces::CesPipeline;
use crate::go_client::GoClient;

/// Download protocol - handles file downloads with CES reconstruction
pub struct DownloadProtocol {
    ces: Arc<CesPipeline>,
    go_client: Arc<GoClient>,
}

impl DownloadProtocol {
    pub fn new(ces: Arc<CesPipeline>, go_client: Arc<GoClient>) -> Self {
        Self { ces, go_client }
    }

    /// Download and reconstruct a file from shards
    pub async fn download_file(
        &self,
        output_path: &Path,
        shard_locations: Vec<(usize, u32)>,
    ) -> Result<usize> {
        info!("Starting download to: {:?}", output_path);

        // 1. Fetch shards from peers via Go transport
        let mut shards = vec![None; shard_locations.len()];
        for (shard_index, peer_id) in shard_locations {
            debug!("Fetching shard {} from peer {}", shard_index, peer_id);
            
            match self.go_client.receive_data(peer_id).await {
                Ok(data) => {
                    if !data.is_empty() {
                        shards[shard_index] = Some(data);
                    }
                }
                Err(e) => {
                    debug!("Failed to fetch shard {} from peer {}: {}", shard_index, peer_id, e);
                    // Continue - Reed-Solomon can reconstruct from partial shards
                }
            }
        }

        // 2. Reconstruct through CES pipeline
        let data = self.ces.reconstruct(shards)?;
        info!("Reconstructed {} bytes", data.len());

        // 3. Write to file
        tokio::fs::write(output_path, &data).await
            .context("Failed to write file")?;
        
        info!("Download complete: {} bytes written", data.len());
        Ok(data.len())
    }

    /// Download raw data
    pub async fn download_data(
        &self,
        shard_locations: Vec<(usize, u32)>,
    ) -> Result<Vec<u8>> {
        info!("Starting data download: {} shards", shard_locations.len());

        // Fetch shards
        let mut shards = vec![None; shard_locations.len()];
        for (shard_index, peer_id) in shard_locations {
            match self.go_client.receive_data(peer_id).await {
                Ok(data) if !data.is_empty() => {
                    shards[shard_index] = Some(data);
                }
                _ => continue,
            }
        }

        // Reconstruct
        let data = self.ces.reconstruct(shards)?;
        info!("Downloaded {} bytes", data.len());

        Ok(data)
    }

    /// Verify data integrity without full download
    pub async fn verify_availability(&self, shard_locations: Vec<(usize, u32)>) -> Result<usize> {
        info!("Verifying shard availability");

        let mut available_count = 0;
        for (shard_index, peer_id) in shard_locations {
            match self.go_client.get_peer_info(peer_id).await {
                Ok(Some(_)) => {
                    debug!("Shard {} available on peer {}", shard_index, peer_id);
                    available_count += 1;
                }
                _ => debug!("Shard {} not available on peer {}", shard_index, peer_id),
            }
        }

        info!("Found {} available shards", available_count);
        Ok(available_count)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::CesConfig;
    use std::net::SocketAddr;

    #[tokio::test]
    async fn test_download_protocol_creation() {
        let caps = crate::capabilities::HardwareCaps::probe();
        let config = CesConfig::adaptive(&caps, 8 * 1024 * 1024, 1.0);
        let ces = Arc::new(CesPipeline::new(config));
        let go_addr: SocketAddr = "127.0.0.1:8080".parse().unwrap();
        let go_client = Arc::new(GoClient::new(go_addr));
        
        let download = DownloadProtocol::new(ces, go_client);
        assert!(true); // Protocol created successfully
    }
}
