use anyhow::{Context, Result};
use std::path::Path;
use std::sync::Arc;
use tracing::{debug, info};

use crate::cache::Cache;
use crate::ces::CesPipeline;
use crate::go_client::GoClient;

/// Download protocol - handles file downloads with CES reconstruction
pub struct DownloadProtocol {
    ces: Arc<CesPipeline>,
    go_client: Arc<GoClient>,
    cache: Option<Arc<Cache>>,
}

impl DownloadProtocol {
    pub fn new(ces: Arc<CesPipeline>, go_client: Arc<GoClient>) -> Self {
        Self {
            ces,
            go_client,
            cache: None,
        }
    }

    /// Create with caching support
    pub fn with_cache(ces: Arc<CesPipeline>, go_client: Arc<GoClient>, cache: Arc<Cache>) -> Self {
        Self {
            ces,
            go_client,
            cache: Some(cache),
        }
    }

    /// Download and reconstruct a file from shards
    pub async fn download_file(
        &self,
        output_path: &Path,
        shard_locations: Vec<(usize, u32)>,
    ) -> Result<usize> {
        self.download_file_with_hash(output_path, shard_locations, None)
            .await
    }

    /// Download with optional file hash for cache lookup
    pub async fn download_file_with_hash(
        &self,
        output_path: &Path,
        shard_locations: Vec<(usize, u32)>,
        file_hash: Option<&str>,
    ) -> Result<usize> {
        info!("Starting download to: {:?}", output_path);

        // 1. Fetch shards from cache or peers
        let mut shards = vec![None; shard_locations.len()];
        for (shard_index, peer_id) in shard_locations {
            // First, try to get from cache if file_hash is provided
            if let (Some(hash), Some(cache)) = (file_hash, &self.cache) {
                if let Some(cached_shard) = cache.get_shard(hash, shard_index).await {
                    debug!("Cache hit for shard {} of {}", shard_index, hash);
                    shards[shard_index] = Some(cached_shard);
                    continue;
                }
            }

            // If not in cache, fetch from peer
            debug!("Fetching shard {} from peer {}", shard_index, peer_id);

            match self.go_client.receive_data(peer_id).await {
                Ok(data) => {
                    if !data.is_empty() {
                        shards[shard_index] = Some(data.clone());

                        // Cache the shard for future downloads
                        if let (Some(hash), Some(cache)) = (file_hash, &self.cache) {
                            let _ = cache.put_shard(hash, shard_index, data).await;
                        }
                    }
                }
                Err(e) => {
                    debug!(
                        "Failed to fetch shard {} from peer {}: {}",
                        shard_index, peer_id, e
                    );
                    // Continue - Reed-Solomon can reconstruct from partial shards
                }
            }
        }

        // 2. Reconstruct through CES pipeline
        let data = self.ces.reconstruct(shards)?;
        info!("Reconstructed {} bytes", data.len());

        // 3. Write to file
        tokio::fs::write(output_path, &data)
            .await
            .context("Failed to write file")?;

        info!("Download complete: {} bytes written", data.len());
        Ok(data.len())
    }

    /// Download raw data
    pub async fn download_data(&self, shard_locations: Vec<(usize, u32)>) -> Result<Vec<u8>> {
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
    #[allow(clippy::arc_with_non_send_sync)]
    async fn test_download_protocol_creation() {
        let caps = crate::capabilities::HardwareCaps::probe();
        let config = CesConfig::adaptive(&caps, 8 * 1024 * 1024, 1.0);
        let ces = Arc::new(CesPipeline::new(config));
        let go_addr: SocketAddr = "127.0.0.1:8080"
            .parse()
            .expect("Hard-coded Go addr 127.0.0.1:8080 must be a valid SocketAddr");
        let go_client = Arc::new(GoClient::new(go_addr));

        let download = DownloadProtocol::new(ces, go_client);
        // Protocol created successfully - just checking it doesn't panic
        drop(download);
    }
}
