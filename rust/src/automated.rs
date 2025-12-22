/// Automated high-level file operations
///
/// This module provides simple, one-function interfaces for uploading and downloading files
/// that handle all the complexity internally:
/// - DHT integration for peer discovery
/// - Automatic shard distribution
/// - Manifest management
/// - Cache integration
/// - Error recovery
use anyhow::{bail, Context, Result};
use std::path::{Path, PathBuf};
use std::sync::Arc;
use tracing::{debug, info, warn};

use crate::cache::Cache;
use crate::ces::CesPipeline;
use crate::dht::DhtNode;
use crate::download::DownloadProtocol;
use crate::go_client::GoClient;
use crate::lookup::LookupService;
use crate::store::NodeStore;
use crate::upload::UploadProtocol;

/// Reserved node ID for the local node (not included in peer discovery)
const LOCAL_NODE_ID: u32 = 0;

/// Constant for bytes to MB conversion
const BYTES_PER_MB: f64 = 1_048_576.0;

/// High-level automated uploader
/// Just provide a file path and it handles everything
pub struct AutomatedUploader {
    upload: Arc<UploadProtocol>,
    lookup: Arc<LookupService>,
    store: Arc<NodeStore>,
    dht: Option<Arc<tokio::sync::RwLock<DhtNode>>>,
}

impl AutomatedUploader {
    /// Create a new automated uploader
    pub fn new(
        ces: Arc<CesPipeline>,
        go_client: Arc<GoClient>,
        cache: Arc<Cache>,
        store: Arc<NodeStore>,
        dht: Option<Arc<tokio::sync::RwLock<DhtNode>>>,
    ) -> Self {
        let upload = Arc::new(UploadProtocol::with_cache(ces, go_client, cache.clone()));
        let lookup = Arc::new(LookupService::new(cache, dht.clone(), store.clone()));

        Self {
            upload,
            lookup,
            store,
            dht,
        }
    }

    /// Upload a file with full automation
    ///
    /// This function:
    /// 1. Validates the file path
    /// 2. Discovers available peers via DHT
    /// 3. Processes file through CES pipeline
    /// 4. Distributes shards to peers
    /// 5. Creates and caches manifest
    /// 6. Registers file in DHT
    /// 7. Returns file hash and manifest
    pub async fn upload(&self, file_path: impl AsRef<Path>) -> Result<UploadResult> {
        let file_path = file_path.as_ref();

        // 1. Validate file
        info!("🚀 Starting automated upload: {:?}", file_path);

        if !file_path.exists() {
            bail!("File not found: {:?}", file_path);
        }

        if !file_path.is_file() {
            bail!("Path is not a file: {:?}", file_path);
        }

        let metadata = tokio::fs::metadata(file_path).await?;
        let file_size = metadata.len();
        info!(
            "📁 File size: {} bytes ({:.2} MB)",
            file_size,
            file_size as f64 / BYTES_PER_MB
        );

        // 2. Discover available peers
        info!("🔍 Discovering available peers...");
        let target_peers = self.discover_target_peers().await?;

        if target_peers.is_empty() {
            bail!("No available peers found. Start at least one other node.");
        }

        info!(
            "✅ Found {} available peer(s): {:?}",
            target_peers.len(),
            target_peers
        );

        // 3. Upload file
        info!("📤 Uploading file and distributing shards...");
        let manifest_json = self
            .upload
            .upload_file(file_path, target_peers)
            .await
            .context("Upload failed")?;

        // Parse manifest to get file hash
        let manifest: crate::cache::FileManifest = serde_json::from_str(&manifest_json)?;
        let file_hash = manifest.file_hash.clone();

        // 4. Register in DHT
        if self.dht.is_some() {
            info!("📡 Registering file in DHT...");
            self.lookup.register_file(&manifest).await?;
        }

        info!("✅ Upload complete!");
        info!("🔑 File hash: {}", file_hash);
        info!("📦 Shards created: {}", manifest.shard_count);
        info!("📍 Shard locations: {:?}", manifest.shard_locations);

        Ok(UploadResult {
            file_hash,
            manifest_json,
            shard_count: manifest.shard_count,
            total_peers: manifest.shard_locations.len(),
        })
    }

    /// Discover target peers for upload
    async fn discover_target_peers(&self) -> Result<Vec<u32>> {
        let mut peers = Vec::new();

        // Get all active nodes from store
        let nodes = self.store.get_all_nodes().await;
        for node in nodes {
            // Skip local node (reserved ID) and only include active peers
            if node.status == crate::types::NodeStatus::Active && node.id != LOCAL_NODE_ID {
                peers.push(node.id);
            }
        }

        // DHT peer discovery: Currently we rely on the NodeStore for peer tracking.
        // The DHT is used for file registration and lookup (see lookup.rs) but not
        // for discovering arbitrary peers. Peers are discovered through the node store
        // which is populated via the Go network layer's peer tracking mechanisms.
        if self.dht.is_some() {
            debug!("DHT available for file operations");
        }

        Ok(peers)
    }
}

/// Result of an automated upload
#[derive(Debug, Clone)]
pub struct UploadResult {
    pub file_hash: String,
    pub manifest_json: String,
    pub shard_count: usize,
    pub total_peers: usize,
}

/// High-level automated downloader
/// Just provide a file hash and it handles everything
pub struct AutomatedDownloader {
    download: Arc<DownloadProtocol>,
    lookup: Arc<LookupService>,
}

impl AutomatedDownloader {
    /// Create a new automated downloader
    pub fn new(
        ces: Arc<CesPipeline>,
        go_client: Arc<GoClient>,
        cache: Arc<Cache>,
        store: Arc<NodeStore>,
        dht: Option<Arc<tokio::sync::RwLock<DhtNode>>>,
    ) -> Self {
        let download = Arc::new(DownloadProtocol::with_cache(ces, go_client, cache.clone()));
        let lookup = Arc::new(LookupService::new(cache, dht, store));

        Self { download, lookup }
    }

    /// Download a file with full automation
    ///
    /// This function:
    /// 1. Looks up file in cache and DHT
    /// 2. Discovers all peers with shards
    /// 3. Fetches shards from available peers
    /// 4. Reconstructs the file
    /// 5. Writes to output path
    /// 6. Returns download stats
    pub async fn download(
        &self,
        file_hash: &str,
        output_path: impl AsRef<Path>,
    ) -> Result<DownloadResult> {
        let output_path = output_path.as_ref();

        info!("🚀 Starting automated download");
        info!("🔑 File hash: {}", file_hash);
        info!("💾 Output path: {:?}", output_path);

        // 1. Lookup file
        info!("🔍 Looking up file in cache and DHT...");
        let lookup_result = self
            .lookup
            .lookup_file(file_hash)
            .await?
            .context("File not found in cache or DHT")?;

        if !lookup_result.is_complete {
            warn!(
                "⚠️  File may not be fully reconstructible. Available shards: {}/{}",
                lookup_result.available_shards, lookup_result.manifest.shard_count
            );
        }

        info!("✅ Found file: {}", lookup_result.manifest.file_name);
        info!("📊 File size: {} bytes", lookup_result.manifest.file_size);
        info!(
            "📦 Shards: {}/{} available",
            lookup_result.available_shards, lookup_result.manifest.shard_count
        );

        // 2. Prepare shard locations
        let shard_locations = lookup_result.manifest.shard_locations.clone();
        info!(
            "📍 Fetching shards from {} location(s)...",
            shard_locations.len()
        );

        // 3. Download and reconstruct
        info!("📥 Downloading shards and reconstructing file...");
        let bytes_written = self
            .download
            .download_file_with_hash(output_path, shard_locations, Some(file_hash))
            .await
            .context("Download failed")?;

        info!("✅ Download complete!");
        info!("💾 Bytes written: {}", bytes_written);

        Ok(DownloadResult {
            file_hash: file_hash.to_string(),
            file_name: lookup_result.manifest.file_name,
            bytes_written,
            shards_fetched: lookup_result.available_shards,
            output_path: output_path.to_path_buf(),
        })
    }

    /// List all available files
    pub async fn list_files(&self) -> Result<Vec<FileInfo>> {
        info!("📋 Listing all available files...");
        let manifests = self.lookup.list_cached_files().await?;

        let mut files = Vec::new();
        for manifest in manifests {
            // Check availability
            let is_available = self.lookup.verify_file(&manifest.file_hash).await?;

            files.push(FileInfo {
                file_hash: manifest.file_hash,
                file_name: manifest.file_name,
                file_size: manifest.file_size,
                shard_count: manifest.shard_count,
                is_available,
                timestamp: manifest.timestamp,
            });
        }

        info!("📊 Found {} file(s)", files.len());
        Ok(files)
    }

    /// Search files by name
    pub async fn search(&self, pattern: &str) -> Result<Vec<FileInfo>> {
        info!("🔍 Searching files matching: '{}'", pattern);
        let manifests = self.lookup.search_files(pattern).await?;

        let mut files = Vec::new();
        for manifest in manifests {
            let is_available = self.lookup.verify_file(&manifest.file_hash).await?;

            files.push(FileInfo {
                file_hash: manifest.file_hash,
                file_name: manifest.file_name,
                file_size: manifest.file_size,
                shard_count: manifest.shard_count,
                is_available,
                timestamp: manifest.timestamp,
            });
        }

        info!("📊 Found {} matching file(s)", files.len());
        Ok(files)
    }

    /// Get file info without downloading
    pub async fn get_info(&self, file_hash: &str) -> Result<Option<FileInfo>> {
        let lookup_result = self.lookup.lookup_file(file_hash).await?;

        if let Some(result) = lookup_result {
            Ok(Some(FileInfo {
                file_hash: result.manifest.file_hash,
                file_name: result.manifest.file_name,
                file_size: result.manifest.file_size,
                shard_count: result.manifest.shard_count,
                is_available: result.is_complete,
                timestamp: result.manifest.timestamp,
            }))
        } else {
            Ok(None)
        }
    }
}

/// Result of an automated download
#[derive(Debug, Clone)]
pub struct DownloadResult {
    pub file_hash: String,
    pub file_name: String,
    pub bytes_written: usize,
    pub shards_fetched: usize,
    pub output_path: PathBuf,
}

/// File information for listing
#[derive(Debug, Clone)]
pub struct FileInfo {
    pub file_hash: String,
    pub file_name: String,
    pub file_size: usize,
    pub shard_count: usize,
    pub is_available: bool,
    pub timestamp: i64,
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::capabilities::HardwareCaps;
    use crate::types::CesConfig;

    #[tokio::test]
    async fn test_automated_uploader_creation() {
        let caps = HardwareCaps::probe();
        let config = CesConfig::adaptive(&caps, 8 * 1024 * 1024, 1.0);
        let ces = Arc::new(CesPipeline::new(config));
        let go_addr: std::net::SocketAddr = "127.0.0.1:8080"
            .parse()
            .expect("Hard-coded Go addr 127.0.0.1:8080 must be a valid SocketAddr");
        let go_client = Arc::new(GoClient::new(go_addr));
        let cache = Arc::new(Cache::new("/tmp/test_cache", 1000, 100 * 1024 * 1024).unwrap());
        let store = Arc::new(NodeStore::new());

        let _uploader = AutomatedUploader::new(
            ces.clone(),
            go_client.clone(),
            cache.clone(),
            store.clone(),
            None,
        );
        assert!(true); // Uploader created successfully
    }

    #[tokio::test]
    async fn test_automated_downloader_creation() {
        let caps = HardwareCaps::probe();
        let config = CesConfig::adaptive(&caps, 8 * 1024 * 1024, 1.0);
        let ces = Arc::new(CesPipeline::new(config));
        let go_addr: std::net::SocketAddr = "127.0.0.1:8080"
            .parse()
            .expect("Hard-coded Go addr 127.0.0.1:8080 must be a valid SocketAddr");
        let go_client = Arc::new(GoClient::new(go_addr));
        let cache = Arc::new(Cache::new("/tmp/test_cache", 1000, 100 * 1024 * 1024).unwrap());
        let store = Arc::new(NodeStore::new());

        let _downloader = AutomatedDownloader::new(ces, go_client, cache, store, None);
        assert!(true); // Downloader created successfully
    }
}
