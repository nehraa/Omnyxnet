use anyhow::Result;
use std::sync::Arc;
use tracing::{info, debug, warn};
use serde::{Serialize, Deserialize};

use crate::cache::{Cache, FileManifest};
use crate::dht::DhtNode;
use crate::store::NodeStore;

/// Lookup result containing file information and availability
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LookupResult {
    /// File manifest
    pub manifest: FileManifest,
    /// Number of available shards
    pub available_shards: usize,
    /// Whether the file is fully reconstructible
    pub is_complete: bool,
    /// Peer availability for each shard
    pub peer_availability: Vec<PeerAvailability>,
}

/// Peer availability for a specific shard
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PeerAvailability {
    pub shard_index: usize,
    pub peer_id: u32,
    pub is_online: bool,
    pub last_seen: Option<i64>,
}

/// File discovery result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DiscoveryResult {
    pub file_hash: String,
    pub providers: Vec<u32>,
    pub source: DiscoverySource,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum DiscoverySource {
    LocalCache,
    DhtLookup,
    PeerQuery,
}

/// Lookup service for finding files in the network
pub struct LookupService {
    cache: Arc<Cache>,
    dht: Option<Arc<tokio::sync::RwLock<DhtNode>>>,
    store: Arc<NodeStore>,
}

impl LookupService {
    /// Create a new lookup service
    pub fn new(
        cache: Arc<Cache>,
        dht: Option<Arc<tokio::sync::RwLock<DhtNode>>>,
        store: Arc<NodeStore>,
    ) -> Self {
        Self { cache, dht, store }
    }

    /// Lookup a file by hash
    pub async fn lookup_file(&self, file_hash: &str) -> Result<Option<LookupResult>> {
        info!("Looking up file: {}", file_hash);
        
        // First check local cache
        if let Some(manifest) = self.cache.get_manifest(file_hash).await {
            debug!("Found file in local cache");
            return self.check_availability(manifest).await.map(Some);
        }
        
        // Then check DHT
        if let Some(manifest) = self.lookup_in_dht(file_hash).await? {
            debug!("Found file via DHT lookup");
            // Cache the manifest for future lookups
            self.cache.put_manifest(manifest.clone()).await?;
            return self.check_availability(manifest).await.map(Some);
        }
        
        warn!("File not found: {}", file_hash);
        Ok(None)
    }

    /// Discover files available in the network
    pub async fn discover_files(&self) -> Result<Vec<DiscoveryResult>> {
        let mut results = Vec::new();
        
        // Get all locally cached manifests
        let local_manifests = self.cache.list_manifests().await;
        for manifest in local_manifests {
            results.push(DiscoveryResult {
                file_hash: manifest.file_hash,
                providers: vec![], // Local cache doesn't track providers
                source: DiscoverySource::LocalCache,
            });
        }
        
        // Query DHT for additional files
        if let Some(dht_results) = self.discover_from_dht().await? {
            results.extend(dht_results);
        }
        
        info!("Discovered {} files", results.len());
        Ok(results)
    }

    /// Check if a file is available (fully reconstructible)
    pub async fn is_available(&self, file_hash: &str) -> Result<bool> {
        if let Some(result) = self.lookup_file(file_hash).await? {
            Ok(result.is_complete)
        } else {
            Ok(false)
        }
    }

    /// Get all files in cache
    pub async fn list_cached_files(&self) -> Result<Vec<FileManifest>> {
        Ok(self.cache.list_manifests().await)
    }

    /// Search for files by name pattern
    pub async fn search_files(&self, pattern: &str) -> Result<Vec<FileManifest>> {
        let all_manifests = self.cache.list_manifests().await;
        let pattern_lower = pattern.to_lowercase();
        
        let matches: Vec<FileManifest> = all_manifests
            .into_iter()
            .filter(|m| m.file_name.to_lowercase().contains(&pattern_lower))
            .collect();
        
        info!("Search for '{}' returned {} results", pattern, matches.len());
        Ok(matches)
    }

    /// Lookup file in DHT
    async fn lookup_in_dht(&self, file_hash: &str) -> Result<Option<FileManifest>> {
        if let Some(dht) = &self.dht {
            debug!("Querying DHT for file: {}", file_hash);
            
            // Query DHT for providers
            let mut dht_guard = dht.write().await;
            // Convert file hash to bytes
            let file_hash_bytes = file_hash.as_bytes().to_vec();
            let _ = dht_guard.find_providers(file_hash_bytes);
            
            // TODO: Query providers for manifest
            // For now, return None - full implementation would involve:
            // 1. Wait for DHT event with provider list
            // 2. Connect to providers
            // 3. Request manifest
            // 4. Verify and return
            
            return Ok(None);
        }
        
        Ok(None)
    }

    /// Discover files from DHT
    async fn discover_from_dht(&self) -> Result<Option<Vec<DiscoveryResult>>> {
        if let Some(_dht) = &self.dht {
            debug!("Discovering files from DHT");
            
            // This is a placeholder - actual implementation would:
            // 1. Perform DHT walk to find provider records
            // 2. Collect unique file hashes
            // 3. Return discovery results
            
            // For now, return empty result
            return Ok(Some(Vec::new()));
        }
        
        Ok(None)
    }

    /// Check availability of shards for a file
    async fn check_availability(&self, manifest: FileManifest) -> Result<LookupResult> {
        let mut peer_availability = Vec::new();
        let mut available_count = 0;
        
        for (shard_index, peer_id) in &manifest.shard_locations {
            // Check if peer is in our store and online
            let is_online = if let Some(node) = self.store.get_node(*peer_id).await {
                node.status == crate::types::NodeStatus::Active
            } else {
                false
            };
            
            if is_online {
                available_count += 1;
            }
            
            peer_availability.push(PeerAvailability {
                shard_index: *shard_index,
                peer_id: *peer_id,
                is_online,
                last_seen: None, // TODO: Track last seen time
            });
        }
        
        // A file is complete if we have enough shards to reconstruct
        // For now, consider it complete if all shards are available
        // In a real system with Reed-Solomon, we'd need K out of N shards
        let is_complete = available_count >= manifest.shard_count;
        
        debug!(
            "File {} availability: {}/{} shards, complete: {}",
            manifest.file_hash, available_count, manifest.shard_count, is_complete
        );
        
        Ok(LookupResult {
            manifest,
            available_shards: available_count,
            is_complete,
            peer_availability,
        })
    }

    /// Verify file integrity by checking if enough shards are available
    pub async fn verify_file(&self, file_hash: &str) -> Result<bool> {
        if let Some(result) = self.lookup_file(file_hash).await? {
            // Check if we have enough shards for reconstruction
            // For now, we require all shards
            Ok(result.is_complete)
        } else {
            Ok(false)
        }
    }

    /// Get file metadata without checking availability
    pub async fn get_metadata(&self, file_hash: &str) -> Result<Option<FileManifest>> {
        // Check cache first
        if let Some(manifest) = self.cache.get_manifest(file_hash).await {
            return Ok(Some(manifest));
        }
        
        // Then check DHT
        self.lookup_in_dht(file_hash).await
    }

    /// Register a file in the DHT
    pub async fn register_file(&self, manifest: &FileManifest) -> Result<()> {
        // First, cache it locally
        self.cache.put_manifest(manifest.clone()).await?;
        
        // Then publish to DHT if available
        if let Some(dht) = &self.dht {
            info!("Registering file in DHT: {}", manifest.file_hash);
            let mut dht_guard = dht.write().await;
            let key = manifest.file_hash.as_bytes().to_vec();
            // Store file metadata as the value
            let value = serde_json::to_vec(manifest)?;
            dht_guard.put_record(key, value)?;
        }
        
        Ok(())
    }

    /// Remove a file from cache and DHT
    pub async fn unregister_file(&self, file_hash: &str) -> Result<bool> {
        // Remove from cache
        let removed = self.cache.remove_manifest(file_hash).await?;
        
        // TODO: Remove from DHT (DHT doesn't have a direct remove API)
        // In practice, provider records expire automatically
        
        if removed {
            info!("Unregistered file: {}", file_hash);
        }
        
        Ok(removed)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::cache::FileManifest;
    use tempfile::tempdir;

    #[tokio::test]
    async fn test_lookup_cached_file() {
        let temp_dir = tempdir().unwrap();
        let cache = Arc::new(Cache::new(temp_dir.path(), 100, 10 * 1024 * 1024).unwrap());
        let store = Arc::new(NodeStore::new());
        let lookup = LookupService::new(cache.clone(), None, store);
        
        // Add a manifest to cache
        let manifest = FileManifest {
            file_hash: "test_hash".to_string(),
            file_name: "test.txt".to_string(),
            file_size: 1000,
            shard_count: 3,
            shard_locations: vec![(0, 1), (1, 2), (2, 3)],
            timestamp: chrono::Utc::now().timestamp(),
            ttl: 3600,
        };
        
        cache.put_manifest(manifest.clone()).await.unwrap();
        
        // Lookup should find it
        let result = lookup.lookup_file("test_hash").await.unwrap();
        assert!(result.is_some());
        assert_eq!(result.unwrap().manifest.file_name, "test.txt");
    }

    #[tokio::test]
    async fn test_search_files() {
        let temp_dir = tempdir().unwrap();
        let cache = Arc::new(Cache::new(temp_dir.path(), 100, 10 * 1024 * 1024).unwrap());
        let store = Arc::new(NodeStore::new());
        let lookup = LookupService::new(cache.clone(), None, store);
        
        // Add some manifests
        for i in 0..5 {
            let manifest = FileManifest {
                file_hash: format!("hash_{}", i),
                file_name: format!("document_{}.txt", i),
                file_size: 1000,
                shard_count: 3,
                shard_locations: vec![(0, 1), (1, 2), (2, 3)],
                timestamp: chrono::Utc::now().timestamp(),
                ttl: 3600,
            };
            cache.put_manifest(manifest).await.unwrap();
        }
        
        // Search for documents
        let results = lookup.search_files("document").await.unwrap();
        assert_eq!(results.len(), 5);
        
        // Search for specific document
        let results = lookup.search_files("document_3").await.unwrap();
        assert_eq!(results.len(), 1);
    }
}
