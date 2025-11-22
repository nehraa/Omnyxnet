use anyhow::{Result, Context};
use std::path::Path;
use std::sync::Arc;
use tracing::{info, debug};
use sha2::{Sha256, Digest};
use chrono::Utc;

use crate::ces::CesPipeline;
use crate::go_client::GoClient;
use crate::cache::{Cache, FileManifest};

/// Upload protocol - handles file uploads with CES pipeline
pub struct UploadProtocol {
    ces: Arc<CesPipeline>,
    go_client: Arc<GoClient>,
    cache: Option<Arc<Cache>>,
}

impl UploadProtocol {
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

    /// Upload a file with compression, encryption, and sharding
    pub async fn upload_file(&self, file_path: &Path, target_peers: Vec<u32>) -> Result<String> {
        info!("Starting upload: {:?}", file_path);

        // 1. Read file
        let data = tokio::fs::read(file_path).await
            .context("Failed to read file")?;
        let file_size = data.len();
        info!("Read {} bytes from file", file_size);

        // 2. Calculate file hash
        let mut hasher = Sha256::new();
        hasher.update(&data);
        let file_hash = format!("{:x}", hasher.finalize());

        // 3. Process through CES pipeline
        let shards = self.ces.process(&data)?;
        info!("Created {} shards from file", shards.len());

        // 4. Distribute shards to peers via Go transport and cache them
        let mut shard_locations = Vec::new();
        for (i, shard) in shards.iter().enumerate() {
            let peer_id = target_peers[i % target_peers.len()];
            
            debug!("Sending shard {} ({} bytes) to peer {}", i, shard.len(), peer_id);
            self.go_client.send_data(peer_id, shard.clone()).await?;
            
            // Cache the shard locally if caching is enabled
            if let Some(cache) = &self.cache {
                cache.put_shard(&file_hash, i, shard.clone()).await?;
            }
            
            shard_locations.push((i, peer_id));
        }

        // 5. Create and cache manifest
        let file_name = file_path.file_name()
            .and_then(|n| n.to_str())
            .unwrap_or("unknown")
            .to_string();

        let manifest = FileManifest {
            file_hash: file_hash.clone(),
            file_name,
            file_size,
            shard_count: shards.len(),
            shard_locations: shard_locations.clone(),
            timestamp: chrono::Utc::now().timestamp(),
            ttl: 0, // 0 = permanent
        };

        if let Some(cache) = &self.cache {
            cache.put_manifest(manifest.clone()).await?;
            info!("Cached manifest for file: {}", file_hash);
        }

        // 6. Return manifest as JSON
        let manifest_json = serde_json::to_string_pretty(&manifest)?;
        info!("Upload complete: {}", file_hash);
        Ok(manifest_json)
    }

    /// Upload raw data
    pub async fn upload_data(&self, data: &[u8], target_peers: Vec<u32>) -> Result<Vec<(usize, u32)>> {
        info!("Starting data upload: {} bytes", data.len());

        // Process through CES pipeline
        let shards = self.ces.process(data)?;
        info!("Created {} shards", shards.len());

        // Distribute to peers
        let mut shard_locations = Vec::new();
        for (i, shard) in shards.iter().enumerate() {
            let peer_id = target_peers[i % target_peers.len()];
            self.go_client.send_data(peer_id, shard.clone()).await?;
            shard_locations.push((i, peer_id));
        }

        Ok(shard_locations)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::CesConfig;
    use std::net::SocketAddr;

    #[tokio::test]
    async fn test_upload_protocol_creation() {
        let caps = crate::capabilities::HardwareCaps::probe();
        let config = CesConfig::adaptive(&caps, 8 * 1024 * 1024, 1.0);
        let ces = Arc::new(CesPipeline::new(config));
        let go_addr: SocketAddr = "127.0.0.1:8080".parse().unwrap();
        let go_client = Arc::new(GoClient::new(go_addr));
        
        let upload = UploadProtocol::new(ces, go_client);
        assert!(true); // Protocol created successfully
    }
}
