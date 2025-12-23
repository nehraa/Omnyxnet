use anyhow::{Context, Result};
use lru::LruCache;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::num::NonZeroUsize;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::{debug, info, warn};

/// File manifest - stores metadata about uploaded files
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FileManifest {
    /// SHA256 hash of the original file
    pub file_hash: String,
    /// Original file name
    pub file_name: String,
    /// Total file size in bytes
    pub file_size: usize,
    /// Number of shards (total = k + m)
    pub shard_count: usize,
    /// Number of parity shards (m)
    #[serde(default)]
    pub parity_count: usize,
    /// Shard locations: (shard_index, peer_id)
    pub shard_locations: Vec<(usize, u32)>,
    /// Timestamp of upload
    pub timestamp: i64,
    /// TTL in seconds (0 = permanent)
    pub ttl: u64,
}

/// Cached shard entry
#[derive(Debug, Clone)]
struct CachedShard {
    data: Vec<u8>,
    timestamp: i64,
}

/// Cache statistics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CacheStats {
    pub shard_hits: u64,
    pub shard_misses: u64,
    pub manifest_hits: u64,
    pub manifest_misses: u64,
    pub total_shards_cached: usize,
    pub total_manifests_cached: usize,
    pub cache_size_bytes: usize,
}

/// Caching layer for shards and manifests
pub struct Cache {
    /// LRU cache for shards (key: file_hash:shard_index)
    shard_cache: Arc<RwLock<LruCache<String, CachedShard>>>,

    /// Manifest cache (key: file_hash)
    manifest_cache: Arc<RwLock<HashMap<String, FileManifest>>>,

    /// Cache statistics
    stats: Arc<RwLock<CacheStats>>,

    /// Persistent storage directory
    cache_dir: PathBuf,

    /// Maximum cache size in bytes
    max_cache_size: usize,
}

impl Cache {
    /// Create a new cache with specified capacity
    pub fn new(
        cache_dir: impl AsRef<Path>,
        max_entries: usize,
        max_size_bytes: usize,
    ) -> Result<Self> {
        let cache_dir = cache_dir.as_ref().to_path_buf();

        // Create cache directory if it doesn't exist
        std::fs::create_dir_all(&cache_dir).context("Failed to create cache directory")?;

        let capacity = NonZeroUsize::new(max_entries).context("Cache capacity must be > 0")?;

        Ok(Self {
            shard_cache: Arc::new(RwLock::new(LruCache::new(capacity))),
            manifest_cache: Arc::new(RwLock::new(HashMap::new())),
            stats: Arc::new(RwLock::new(CacheStats {
                shard_hits: 0,
                shard_misses: 0,
                manifest_hits: 0,
                manifest_misses: 0,
                total_shards_cached: 0,
                total_manifests_cached: 0,
                cache_size_bytes: 0,
            })),
            cache_dir,
            max_cache_size: max_size_bytes,
        })
    }

    /// Get a shard from cache
    pub async fn get_shard(&self, file_hash: &str, shard_index: usize) -> Option<Vec<u8>> {
        let key = format!("{}:{}", file_hash, shard_index);
        let mut cache = self.shard_cache.write().await;

        if let Some(cached) = cache.get(&key) {
            let mut stats = self.stats.write().await;
            stats.shard_hits += 1;
            debug!("Cache hit: {}", key);
            Some(cached.data.clone())
        } else {
            let mut stats = self.stats.write().await;
            stats.shard_misses += 1;
            debug!("Cache miss: {}", key);
            None
        }
    }

    /// Put a shard into cache
    pub async fn put_shard(
        &self,
        file_hash: &str,
        shard_index: usize,
        data: Vec<u8>,
    ) -> Result<()> {
        let key = format!("{}:{}", file_hash, shard_index);
        let data_size = data.len();

        // Check if adding this shard would exceed max cache size
        let current_size = {
            let stats = self.stats.read().await;
            stats.cache_size_bytes
        };

        if current_size + data_size > self.max_cache_size {
            // Evict entries until we have space
            self.evict_to_fit(data_size).await?;
        }

        let cached = CachedShard {
            data,
            timestamp: chrono::Utc::now().timestamp(),
        };

        let mut cache = self.shard_cache.write().await;
        cache.put(key.clone(), cached);

        let mut stats = self.stats.write().await;
        stats.total_shards_cached = cache.len();
        stats.cache_size_bytes += data_size;

        debug!("Cached shard: {} ({} bytes)", key, data_size);
        Ok(())
    }

    /// Get a manifest from cache
    pub async fn get_manifest(&self, file_hash: &str) -> Option<FileManifest> {
        let cache = self.manifest_cache.read().await;

        if let Some(manifest) = cache.get(file_hash) {
            let mut stats = self.stats.write().await;
            stats.manifest_hits += 1;
            debug!("Manifest cache hit: {}", file_hash);
            Some(manifest.clone())
        } else {
            let mut stats = self.stats.write().await;
            stats.manifest_misses += 1;
            debug!("Manifest cache miss: {}", file_hash);
            None
        }
    }

    /// Put a manifest into cache
    pub async fn put_manifest(&self, manifest: FileManifest) -> Result<()> {
        let mut cache = self.manifest_cache.write().await;
        cache.insert(manifest.file_hash.clone(), manifest.clone());

        let mut stats = self.stats.write().await;
        stats.total_manifests_cached = cache.len();

        // Also persist to disk
        self.persist_manifest(&manifest).await?;

        info!(
            "Cached manifest: {} ({} shards)",
            manifest.file_hash, manifest.shard_count
        );
        Ok(())
    }

    /// List all cached manifests
    pub async fn list_manifests(&self) -> Vec<FileManifest> {
        let cache = self.manifest_cache.read().await;
        cache.values().cloned().collect()
    }

    /// Get cache statistics
    pub async fn get_stats(&self) -> CacheStats {
        self.stats.read().await.clone()
    }

    /// Clear all cached shards
    pub async fn clear_shards(&self) -> Result<()> {
        let mut cache = self.shard_cache.write().await;
        cache.clear();

        let mut stats = self.stats.write().await;
        stats.total_shards_cached = 0;
        stats.cache_size_bytes = 0;

        info!("Cleared all cached shards");
        Ok(())
    }

    /// Clear all manifests
    pub async fn clear_manifests(&self) -> Result<()> {
        let mut cache = self.manifest_cache.write().await;
        cache.clear();

        let mut stats = self.stats.write().await;
        stats.total_manifests_cached = 0;

        // Also clear persisted manifests
        let manifest_dir = self.cache_dir.join("manifests");
        if manifest_dir.exists() {
            std::fs::remove_dir_all(&manifest_dir)?;
            std::fs::create_dir_all(&manifest_dir)?;
        }

        info!("Cleared all manifests");
        Ok(())
    }

    /// Evict shards to make room for new data
    async fn evict_to_fit(&self, required_space: usize) -> Result<()> {
        let mut cache = self.shard_cache.write().await;
        let mut stats = self.stats.write().await;

        let mut freed_space = 0;
        let target_space = required_space + (self.max_cache_size / 10); // Free 10% extra

        while freed_space < target_space && cache.len() > 0 {
            if let Some((_, evicted)) = cache.pop_lru() {
                let evicted_size = evicted.data.len();
                freed_space += evicted_size;
                stats.cache_size_bytes = stats.cache_size_bytes.saturating_sub(evicted_size);
                debug!("Evicted shard ({} bytes freed)", evicted_size);
            } else {
                break;
            }
        }

        stats.total_shards_cached = cache.len();
        info!("Evicted {} bytes to make room for new data", freed_space);
        Ok(())
    }

    /// Persist a manifest to disk
    async fn persist_manifest(&self, manifest: &FileManifest) -> Result<()> {
        let manifest_dir = self.cache_dir.join("manifests");
        tokio::fs::create_dir_all(&manifest_dir).await?;

        let manifest_path = manifest_dir.join(format!("{}.json", manifest.file_hash));
        let json = serde_json::to_string_pretty(manifest)?;

        tokio::fs::write(&manifest_path, json)
            .await
            .context("Failed to persist manifest")?;

        debug!("Persisted manifest to: {:?}", manifest_path);
        Ok(())
    }

    /// Load persisted manifests from disk
    pub async fn load_persisted_manifests(&self) -> Result<usize> {
        let manifest_dir = self.cache_dir.join("manifests");

        if !manifest_dir.exists() {
            return Ok(0);
        }

        let mut count = 0;
        let mut entries = tokio::fs::read_dir(&manifest_dir).await?;

        while let Some(entry) = entries.next_entry().await? {
            let path = entry.path();
            if path.extension().and_then(|s| s.to_str()) == Some("json") {
                match tokio::fs::read_to_string(&path).await {
                    Ok(json) => match serde_json::from_str::<FileManifest>(&json) {
                        Ok(manifest) => {
                            let mut cache = self.manifest_cache.write().await;
                            cache.insert(manifest.file_hash.clone(), manifest);
                            count += 1;
                        }
                        Err(e) => {
                            warn!("Failed to parse manifest {:?}: {}", path, e);
                        }
                    },
                    Err(e) => {
                        warn!("Failed to read manifest {:?}: {}", path, e);
                    }
                }
            }
        }

        info!("Loaded {} persisted manifests", count);
        Ok(count)
    }

    /// Remove a manifest from cache
    pub async fn remove_manifest(&self, file_hash: &str) -> Result<bool> {
        let mut cache = self.manifest_cache.write().await;
        let removed = cache.remove(file_hash).is_some();

        if removed {
            // Also remove from disk
            let manifest_path = self
                .cache_dir
                .join("manifests")
                .join(format!("{}.json", file_hash));
            if manifest_path.exists() {
                tokio::fs::remove_file(&manifest_path).await?;
            }

            let mut stats = self.stats.write().await;
            stats.total_manifests_cached = cache.len();

            info!("Removed manifest: {}", file_hash);
        }

        Ok(removed)
    }

    /// Check if a shard exists in cache
    pub async fn has_shard(&self, file_hash: &str, shard_index: usize) -> bool {
        let key = format!("{}:{}", file_hash, shard_index);
        let cache = self.shard_cache.read().await;
        cache.contains(&key)
    }

    /// Get all manifests (for auto-healing)
    pub async fn get_all_manifests(&self) -> Result<Vec<FileManifest>> {
        let cache = self.manifest_cache.read().await;
        Ok(cache.values().cloned().collect())
    }

    /// Refresh TTL for a manifest (called on download)
    pub async fn refresh_ttl(&self, file_hash: &str, new_ttl: u64) -> Result<bool> {
        // Acquire write lock and update manifest, then clone for persistence
        let manifest_to_persist = {
            let mut cache = self.manifest_cache.write().await;
            if let Some(manifest) = cache.get_mut(file_hash) {
                manifest.ttl = new_ttl;
                manifest.timestamp = chrono::Utc::now().timestamp();
                Some(manifest.clone())
            } else {
                None
            }
        };
        if let Some(manifest) = manifest_to_persist {
            self.persist_manifest(&manifest).await?;
            info!("Refreshed TTL for {}: {} seconds", file_hash, new_ttl);
            Ok(true)
        } else {
            Ok(false)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[tokio::test]
    async fn test_shard_cache() {
        let temp_dir = tempdir().unwrap();
        let cache = Cache::new(temp_dir.path(), 100, 10 * 1024 * 1024).unwrap();

        let data = vec![1, 2, 3, 4, 5];
        cache.put_shard("test_hash", 0, data.clone()).await.unwrap();

        let retrieved = cache.get_shard("test_hash", 0).await;
        assert_eq!(retrieved, Some(data));

        let stats = cache.get_stats().await;
        assert_eq!(stats.shard_hits, 1);
        assert_eq!(stats.total_shards_cached, 1);
    }

    #[tokio::test]
    async fn test_manifest_cache() {
        let temp_dir = tempdir().unwrap();
        let cache = Cache::new(temp_dir.path(), 100, 10 * 1024 * 1024).unwrap();

        let manifest = FileManifest {
            file_hash: "test_hash".to_string(),
            file_name: "test.txt".to_string(),
            file_size: 1000,
            shard_count: 5,
            parity_count: 2,
            shard_locations: vec![(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)],
            timestamp: chrono::Utc::now().timestamp(),
            ttl: 3600,
        };

        cache.put_manifest(manifest.clone()).await.unwrap();

        let retrieved = cache.get_manifest("test_hash").await;
        assert!(retrieved.is_some());
        assert_eq!(retrieved.unwrap().file_name, "test.txt");

        let stats = cache.get_stats().await;
        assert_eq!(stats.manifest_hits, 1);
        assert_eq!(stats.total_manifests_cached, 1);
    }

    #[tokio::test]
    async fn test_cache_eviction() {
        let temp_dir = tempdir().unwrap();
        let cache = Cache::new(temp_dir.path(), 2, 10).unwrap(); // Very small cache

        cache.put_shard("hash1", 0, vec![1, 2, 3]).await.unwrap();
        cache.put_shard("hash2", 0, vec![4, 5, 6]).await.unwrap();
        cache.put_shard("hash3", 0, vec![7, 8, 9]).await.unwrap(); // Should trigger eviction

        let stats = cache.get_stats().await;
        assert!(stats.total_shards_cached <= 2);
    }
}
