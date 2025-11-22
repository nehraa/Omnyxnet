/// Auto-Healing module for maintaining shard redundancy
/// Monitors local shard count and requests replacement data when needed
use anyhow::Result;
use std::collections::HashMap;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::RwLock;
use tokio::time::{interval, sleep};
use tracing::{debug, info, warn, error};

use crate::cache::{Cache, FileManifest};
use crate::ces::CesPipeline;
use crate::go_client::GoClient;
use crate::store::NodeStore;

/// Configuration for auto-healing
#[derive(Debug, Clone)]
pub struct AutoHealConfig {
    /// Minimum number of shard copies to maintain
    pub min_shard_copies: usize,
    /// Target number of shard copies
    pub target_shard_copies: usize,
    /// Check interval in seconds
    pub check_interval_secs: u64,
    /// Enable/disable auto-healing
    pub enabled: bool,
}

impl Default for AutoHealConfig {
    fn default() -> Self {
        Self {
            min_shard_copies: 3,
            target_shard_copies: 5,
            check_interval_secs: 300, // 5 minutes
            enabled: true,
        }
    }
}

/// Tracks healing status for a file
#[derive(Debug, Clone)]
struct HealingStatus {
    file_hash: String,
    current_copies: usize,
    needed_copies: usize,
    last_heal_attempt: Option<std::time::SystemTime>,
    heal_failures: u32,
}

/// Auto-healing service
pub struct AutoHealer {
    config: AutoHealConfig,
    cache: Arc<Cache>,
    ces: Arc<CesPipeline>,
    go_client: Arc<GoClient>,
    store: Arc<NodeStore>,
    
    /// Track files being healed
    healing_status: Arc<RwLock<HashMap<String, HealingStatus>>>,
    
    /// Statistics
    stats: Arc<RwLock<HealStats>>,
}

/// Healing statistics
#[derive(Debug, Clone, Default)]
pub struct HealStats {
    pub files_monitored: usize,
    pub heals_attempted: u64,
    pub heals_succeeded: u64,
    pub heals_failed: u64,
    pub shards_recovered: u64,
}

impl AutoHealer {
    /// Create a new auto-healer
    pub fn new(
        config: AutoHealConfig,
        cache: Arc<Cache>,
        ces: Arc<CesPipeline>,
        go_client: Arc<GoClient>,
        store: Arc<NodeStore>,
    ) -> Self {
        Self {
            config,
            cache,
            ces,
            go_client,
            store,
            healing_status: Arc::new(RwLock::new(HashMap::new())),
            stats: Arc::new(RwLock::new(HealStats::default())),
        }
    }

    /// Start the auto-healing background task
    pub async fn start(self: Arc<Self>) {
        if !self.config.enabled {
            info!("Auto-healing is disabled");
            return;
        }

        info!(
            "🔧 Auto-healing started: min_copies={}, target={}, interval={}s",
            self.config.min_shard_copies,
            self.config.target_shard_copies,
            self.config.check_interval_secs
        );

        let mut check_interval = interval(Duration::from_secs(self.config.check_interval_secs));

        loop {
            check_interval.tick().await;
            
            if let Err(e) = self.run_healing_cycle().await {
                error!("Healing cycle failed: {}", e);
            }
        }
    }

    /// Run a single healing cycle
    async fn run_healing_cycle(&self) -> Result<()> {
        debug!("Running healing cycle...");

        // Get all manifests from cache
        let manifests = self.cache.get_all_manifests().await?;
        
        {
            let mut stats = self.stats.write().await;
            stats.files_monitored = manifests.len();
        }

        debug!("Checking {} files for healing needs", manifests.len());

        for manifest in manifests {
            if let Err(e) = self.check_and_heal_file(&manifest).await {
                warn!("Failed to heal file {}: {}", manifest.file_hash, e);
            }
            
            // Small delay between files to avoid overwhelming the network
            sleep(Duration::from_millis(100)).await;
        }

        debug!("Healing cycle complete");
        Ok(())
    }

    /// Check and heal a specific file
    async fn check_and_heal_file(&self, manifest: &FileManifest) -> Result<()> {
        let file_hash = &manifest.file_hash;
        
        // Count available shards
        let available_count = self.count_available_shards(manifest).await?;
        
        debug!(
            "File {}: {} available shards (min: {}, target: {})",
            file_hash, available_count, self.config.min_shard_copies, self.config.target_shard_copies
        );

        // Check if healing is needed
        if available_count >= self.config.target_shard_copies {
            // File is healthy
            self.healing_status.write().await.remove(file_hash);
            return Ok(());
        }

        if available_count < self.config.min_shard_copies {
            warn!(
                "🚨 File {} critically low on shards: {} < {}",
                file_hash, available_count, self.config.min_shard_copies
            );
        }

        // Update healing status
        let mut status_map = self.healing_status.write().await;
        let status = status_map.entry(file_hash.clone()).or_insert_with(|| HealingStatus {
            file_hash: file_hash.clone(),
            current_copies: available_count,
            needed_copies: self.config.target_shard_copies - available_count,
            last_heal_attempt: None,
            heal_failures: 0,
        });

        // Check if we should attempt healing (avoid too frequent attempts)
        if let Some(last_attempt) = status.last_heal_attempt {
            let elapsed = std::time::SystemTime::now()
                .duration_since(last_attempt)
                .unwrap_or(Duration::from_secs(0));
            
            // Exponential backoff: wait longer after each failure
            let backoff_secs = 60 * (1 << status.heal_failures.min(5));
            if elapsed < Duration::from_secs(backoff_secs) {
                debug!("Skipping heal attempt for {} (backoff)", file_hash);
                return Ok(());
            }
        }

        status.last_heal_attempt = Some(std::time::SystemTime::now());
        drop(status_map); // Release lock before healing

        // Attempt to heal
        info!("🔧 Attempting to heal file {}", file_hash);
        
        {
            let mut stats = self.stats.write().await;
            stats.heals_attempted += 1;
        }

        match self.perform_healing(manifest).await {
            Ok(recovered) => {
                info!("✅ Successfully healed file {}, recovered {} shards", file_hash, recovered);
                
                let mut stats = self.stats.write().await;
                stats.heals_succeeded += 1;
                stats.shards_recovered += recovered as u64;
                
                // Reset failure count
                if let Some(status) = self.healing_status.write().await.get_mut(file_hash) {
                    status.heal_failures = 0;
                }
            }
            Err(e) => {
                warn!("❌ Failed to heal file {}: {}", file_hash, e);
                
                let mut stats = self.stats.write().await;
                stats.heals_failed += 1;
                
                // Increment failure count
                if let Some(status) = self.healing_status.write().await.get_mut(file_hash) {
                    status.heal_failures += 1;
                }
            }
        }

        Ok(())
    }

    /// Count available shards for a file
    async fn count_available_shards(&self, manifest: &FileManifest) -> Result<usize> {
        let mut available = 0;

        for (shard_idx, peer_id) in &manifest.shard_locations {
            // Check if shard is in cache
            if self.cache.has_shard(&manifest.file_hash, *shard_idx).await {
                available += 1;
                continue;
            }

            // Check if peer is online
            if let Some(node) = self.store.get_node(*peer_id).await {
                if node.status == crate::types::NodeStatus::Active {
                    available += 1;
                }
            }
        }

        Ok(available)
    }

    /// Perform the actual healing by requesting and re-encoding shards
    async fn perform_healing(&self, manifest: &FileManifest) -> Result<usize> {
        // 1. Collect available shards
        let mut shards = vec![None; manifest.shard_count];
        let mut collected = 0;

        for (shard_idx, peer_id) in &manifest.shard_locations {
            // Try to get from cache first
            if let Some(data) = self.cache.get_shard(&manifest.file_hash, *shard_idx).await {
                shards[*shard_idx] = Some(data);
                collected += 1;
                continue;
            }

            // TODO: Request from peer via go_client
            // This would involve RPC call to peer to fetch shard
            // For now, we'll just check cache
        }

        // 2. Check if we have enough shards to reconstruct
        // For Reed-Solomon, we need k (data shards) = total - parity
        let required = if manifest.parity_count > 0 {
            manifest.shard_count - manifest.parity_count
        } else {
            // Fallback for old manifests without parity_count: assume 2/3 threshold
            manifest.shard_count - (manifest.shard_count / 3)
        };
        if collected < required {
            return Err(anyhow::anyhow!(
                "Not enough shards to reconstruct: {} < {}",
                collected,
                required
            ));
        }

        // 3. Reconstruct the original data
        let original_data = self.ces.reconstruct(shards)?;
        debug!("Reconstructed {} bytes", original_data.len());

        // 4. Re-encode to create new shards
        let new_shards = self.ces.process(&original_data)?;
        debug!("Created {} new shards", new_shards.len());

        // 5. Store new shards in cache
        for (idx, shard) in new_shards.iter().enumerate() {
            self.cache
                .put_shard(&manifest.file_hash, idx, shard.clone())
                .await?;
        }

        // 6. TODO: Distribute new shards to peers
        // This would involve selecting healthy peers and uploading shards

        Ok(new_shards.len() - collected)
    }

    /// Get current statistics
    pub async fn get_stats(&self) -> HealStats {
        self.stats.read().await.clone()
    }

    /// Get healing status for all files
    pub async fn get_healing_status(&self) -> Vec<HealingStatus> {
        self.healing_status
            .read()
            .await
            .values()
            .cloned()
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_config_defaults() {
        let config = AutoHealConfig::default();
        assert_eq!(config.min_shard_copies, 3);
        assert_eq!(config.target_shard_copies, 5);
        assert!(config.enabled);
    }
}
