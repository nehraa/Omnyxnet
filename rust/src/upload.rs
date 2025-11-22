use anyhow::{Result, Context};
use std::path::Path;
use std::sync::Arc;
use tracing::{info, debug};

use crate::ces::CesPipeline;
use crate::go_client::GoClient;

/// Upload protocol - handles file uploads with CES pipeline
pub struct UploadProtocol {
    ces: Arc<CesPipeline>,
    go_client: Arc<GoClient>,
}

impl UploadProtocol {
    pub fn new(ces: Arc<CesPipeline>, go_client: Arc<GoClient>) -> Self {
        Self { ces, go_client }
    }

    /// Upload a file with compression, encryption, and sharding
    pub async fn upload_file(&self, file_path: &Path, target_peers: Vec<u32>) -> Result<String> {
        info!("Starting upload: {:?}", file_path);

        // 1. Read file
        let data = tokio::fs::read(file_path).await
            .context("Failed to read file")?;
        info!("Read {} bytes from file", data.len());

        // 2. Process through CES pipeline
        let shards = self.ces.process(&data)?;
        info!("Created {} shards from file", shards.len());

        // 3. Distribute shards to peers via Go transport
        let mut shard_locations = Vec::new();
        for (i, shard) in shards.iter().enumerate() {
            let peer_id = target_peers[i % target_peers.len()];
            
            debug!("Sending shard {} ({} bytes) to peer {}", i, shard.len(), peer_id);
            self.go_client.send_data(peer_id, shard.clone()).await?;
            
            shard_locations.push((i, peer_id));
        }

        // 4. Return manifest
        let manifest = format!(
            "{{\"file\":\"{}\",\"shards\":{},\"locations\":{:?}}}",
            file_path.display(),
            shards.len(),
            shard_locations
        );
        
        info!("Upload complete: {}", manifest);
        Ok(manifest)
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
