//! Lock-free ring buffer for chunk storage

use crate::dcdn::types::{ChunkData, ChunkId, StorageStats};
use anyhow::Result;
use dashmap::DashMap;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant};

/// Thread-safe chunk storage with ring buffer and automatic eviction
pub struct ChunkStore {
    /// Fixed-size ring buffer slots
    slots: Vec<parking_lot::RwLock<Option<Arc<ChunkData>>>>,
    /// Atomic write head pointer
    write_head: AtomicUsize,
    /// Fast lookup: chunk_id → slot index
    index: DashMap<ChunkId, usize>,
    /// Configuration
    capacity: usize,
    chunk_ttl: Duration,
    /// Statistics
    evictions_total: AtomicUsize,
    hits_total: AtomicUsize,
    misses_total: AtomicUsize,
}

impl ChunkStore {
    /// Create a new chunk store
    pub fn new(capacity: usize, chunk_ttl: Duration) -> Self {
        let mut slots = Vec::with_capacity(capacity);
        for _ in 0..capacity {
            slots.push(parking_lot::RwLock::new(None));
        }

        Self {
            slots,
            write_head: AtomicUsize::new(0),
            index: DashMap::new(),
            capacity,
            chunk_ttl,
            evictions_total: AtomicUsize::new(0),
            hits_total: AtomicUsize::new(0),
            misses_total: AtomicUsize::new(0),
        }
    }

    /// Insert a chunk into the store
    pub fn insert(&self, chunk: ChunkData) -> Result<()> {
        let chunk_id = chunk.id;
        let chunk_arc = Arc::new(chunk);

        // Check if chunk already exists and remove from old slot to prevent memory waste
        if let Some((_, old_slot_idx)) = self.index.remove(&chunk_id) {
            let mut old_slot = self.slots[old_slot_idx].write();
            if let Some(ref old_chunk) = *old_slot {
                if old_chunk.id == chunk_id {
                    *old_slot = None;
                }
            }
        }

        // Get next slot (circular)
        let slot_idx = self.write_head.fetch_add(1, Ordering::SeqCst) % self.capacity;

        // Evict old chunk if slot is occupied and update index before releasing lock
        {
            let mut slot = self.slots[slot_idx].write();
            if let Some(old_chunk) = slot.take() {
                self.index.remove(&old_chunk.id);
                self.evictions_total.fetch_add(1, Ordering::Relaxed);
            }
            *slot = Some(chunk_arc);
            // Update index while holding the lock to avoid race condition
            self.index.insert(chunk_id, slot_idx);
        }

        Ok(())
    }

    /// Get a chunk by ID
    pub fn get(&self, id: &ChunkId) -> Option<Arc<ChunkData>> {
        if let Some(slot_idx) = self.index.get(id) {
            let slot = self.slots[*slot_idx].read();
            if let Some(chunk) = slot.as_ref() {
                self.hits_total.fetch_add(1, Ordering::Relaxed);
                return Some(Arc::clone(chunk));
            }
        }
        self.misses_total.fetch_add(1, Ordering::Relaxed);
        None
    }

    /// Remove a chunk by ID
    pub fn remove(&self, id: &ChunkId) -> Option<Arc<ChunkData>> {
        if let Some((_, slot_idx)) = self.index.remove(id) {
            let mut slot = self.slots[slot_idx].write();
            return slot.take();
        }
        None
    }

    /// List expired chunks
    pub fn list_expired(&self, now: Instant) -> Vec<ChunkId> {
        let mut expired = Vec::new();

        for entry in self.index.iter() {
            let slot_idx = *entry.value();
            let slot = self.slots[slot_idx].read();

            if let Some(chunk) = slot.as_ref() {
                if now.duration_since(chunk.timestamp) > self.chunk_ttl {
                    expired.push(*entry.key());
                }
            }
        }

        expired
    }

    /// Evict expired chunks
    pub fn evict_expired(&self, now: Instant) -> usize {
        let expired = self.list_expired(now);
        let count = expired.len();

        for chunk_id in expired {
            self.remove(&chunk_id);
        }

        count
    }

    /// Get storage statistics
    pub fn stats(&self) -> StorageStats {
        let chunk_count = self.index.len();
        let size_bytes = self.index.iter().fold(0, |acc, entry| {
            let slot_idx = *entry.value();
            let slot = self.slots[slot_idx].read();
            acc + slot.as_ref().map(|c| c.data.len()).unwrap_or(0)
        });

        StorageStats {
            size_bytes,
            chunk_count,
            evictions_total: self.evictions_total.load(Ordering::Relaxed) as u64,
            hits_total: self.hits_total.load(Ordering::Relaxed) as u64,
            misses_total: self.misses_total.load(Ordering::Relaxed) as u64,
        }
    }

    /// Get capacity
    pub fn capacity(&self) -> usize {
        self.capacity
    }

    /// Get chunk count
    pub fn len(&self) -> usize {
        self.index.len()
    }

    /// Check if empty
    pub fn is_empty(&self) -> bool {
        self.index.is_empty()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::dcdn::types::{PeerId, Signature};
    use bytes::Bytes;

    fn create_test_chunk(id: u64, data: Vec<u8>) -> ChunkData {
        ChunkData {
            id: ChunkId(id),
            sequence: id,
            timestamp: Instant::now(),
            source_peer: PeerId(1),
            signature: Signature([0u8; 64]),
            data: Bytes::from(data),
            fec_group: None,
        }
    }

    #[test]
    fn test_insert_and_get() {
        let store = ChunkStore::new(10, Duration::from_secs(120));
        let chunk = create_test_chunk(1, vec![1, 2, 3, 4]);

        store.insert(chunk.clone()).unwrap();

        let retrieved = store.get(&ChunkId(1)).unwrap();
        assert_eq!(retrieved.id, ChunkId(1));
        assert_eq!(retrieved.data.as_ref(), &[1, 2, 3, 4]);
    }

    #[test]
    fn test_eviction() {
        let store = ChunkStore::new(3, Duration::from_secs(120));

        // Insert 5 chunks into 3-slot buffer
        for i in 0..5 {
            let chunk = create_test_chunk(i, vec![i as u8]);
            store.insert(chunk).unwrap();
        }

        // First 2 chunks should be evicted
        assert!(store.get(&ChunkId(0)).is_none());
        assert!(store.get(&ChunkId(1)).is_none());

        // Last 3 chunks should be present
        assert!(store.get(&ChunkId(2)).is_some());
        assert!(store.get(&ChunkId(3)).is_some());
        assert!(store.get(&ChunkId(4)).is_some());
    }

    #[test]
    fn test_expired_chunks() {
        let store = ChunkStore::new(10, Duration::from_millis(10));

        let chunk = create_test_chunk(1, vec![1, 2, 3]);
        store.insert(chunk).unwrap();

        std::thread::sleep(Duration::from_millis(20));

        let expired = store.list_expired(Instant::now());
        assert_eq!(expired.len(), 1);
        assert_eq!(expired[0], ChunkId(1));
    }

    #[test]
    fn test_stats() {
        let store = ChunkStore::new(10, Duration::from_secs(120));

        let chunk = create_test_chunk(1, vec![1, 2, 3, 4, 5]);
        store.insert(chunk).unwrap();

        let stats = store.stats();
        assert_eq!(stats.chunk_count, 1);
        assert_eq!(stats.size_bytes, 5);
    }
}
