//! Cryptographic signature verification for chunk authenticity

use crate::dcdn::types::{ChunkData, PeerId, PublicKey};
use anyhow::{Context, Result};
use dashmap::DashMap;
use std::collections::HashSet;
use std::sync::Arc;
use parking_lot::RwLock;

/// Ed25519 signature verifier
pub struct SignatureVerifier {
    /// Trusted public keys for peers
    trusted_keys: DashMap<PeerId, PublicKey>,
    /// Revoked peer IDs
    revoked_keys: Arc<RwLock<HashSet<PeerId>>>,
    /// Verification metrics
    metrics: Arc<VerificationMetrics>,
}

#[derive(Debug, Default)]
pub struct VerificationMetrics {
    pub verifications_total: std::sync::atomic::AtomicU64,
    pub verifications_success: std::sync::atomic::AtomicU64,
    pub verifications_failed: std::sync::atomic::AtomicU64,
    pub batch_verifications: std::sync::atomic::AtomicU64,
}

impl SignatureVerifier {
    /// Create a new signature verifier
    pub fn new() -> Self {
        Self {
            trusted_keys: DashMap::new(),
            revoked_keys: Arc::new(RwLock::new(HashSet::new())),
            metrics: Arc::new(VerificationMetrics::default()),
        }
    }

    /// Verify a single chunk's signature
    pub fn verify(&self, chunk: &ChunkData) -> Result<bool> {
        use std::sync::atomic::Ordering;
        
        self.metrics.verifications_total.fetch_add(1, Ordering::Relaxed);

        // Check if peer is revoked
        {
            let revoked = self.revoked_keys.read();
            if revoked.contains(&chunk.source_peer) {
                self.metrics.verifications_failed.fetch_add(1, Ordering::Relaxed);
                return Ok(false);
            }
        }

        // Get public key for peer
        let public_key = self.trusted_keys.get(&chunk.source_peer)
            .context("Public key not found for peer")?;

        // Verify signature using ed25519-dalek
        let result = self.verify_ed25519(&chunk.data, &chunk.signature.0, &public_key.0)?;

        if result {
            self.metrics.verifications_success.fetch_add(1, Ordering::Relaxed);
        } else {
            self.metrics.verifications_failed.fetch_add(1, Ordering::Relaxed);
        }

        Ok(result)
    }

    /// Verify multiple chunks in a batch (more efficient)
    pub fn verify_batch(&self, chunks: &[ChunkData]) -> Result<Vec<bool>> {
        use std::sync::atomic::Ordering;
        
        self.metrics.batch_verifications.fetch_add(1, Ordering::Relaxed);

        let mut results = Vec::with_capacity(chunks.len());

        for chunk in chunks {
            let result = self.verify(chunk)?;
            results.push(result);
        }

        Ok(results)
    }

    /// Add a trusted public key for a peer
    pub fn add_trusted_key(&self, peer: PeerId, public_key: PublicKey) {
        self.trusted_keys.insert(peer, public_key);
    }

    /// Revoke a peer's key
    pub fn revoke_key(&self, peer: PeerId) {
        let mut revoked = self.revoked_keys.write();
        revoked.insert(peer);
        self.trusted_keys.remove(&peer);
    }

    /// Check if a peer is revoked
    pub fn is_revoked(&self, peer: &PeerId) -> bool {
        let revoked = self.revoked_keys.read();
        revoked.contains(peer)
    }

    /// Get number of trusted keys
    pub fn trusted_key_count(&self) -> usize {
        self.trusted_keys.len()
    }

    /// Get verification metrics
    pub fn get_metrics(&self) -> (u64, u64, u64, u64) {
        use std::sync::atomic::Ordering;
        
        (
            self.metrics.verifications_total.load(Ordering::Relaxed),
            self.metrics.verifications_success.load(Ordering::Relaxed),
            self.metrics.verifications_failed.load(Ordering::Relaxed),
            self.metrics.batch_verifications.load(Ordering::Relaxed),
        )
    }

    /// Internal Ed25519 verification using ed25519-dalek
    fn verify_ed25519(&self, data: &[u8], signature: &[u8; 64], public_key: &[u8; 32]) -> Result<bool> {
        use ed25519_dalek::{Signature, VerifyingKey, Verifier};
        
        let pk = VerifyingKey::from_bytes(public_key)
            .map_err(|e| anyhow::anyhow!("Invalid public key: {}", e))?;
        let sig = Signature::from_bytes(signature);
        
        Ok(pk.verify(data, &sig).is_ok())
    }
}

impl Default for SignatureVerifier {
    fn default() -> Self {
        Self::new()
    }
}

/// Batch processor for verification
pub struct VerificationBatch {
    chunks: Vec<ChunkData>,
    max_size: usize,
    /// Timeout for batch processing (intended for future timeout-based flushing logic)
    /// Currently stored but not actively used - could be used to trigger batch verification
    /// when timeout expires even if batch is not full
    timeout: std::time::Duration,
}

impl VerificationBatch {
    /// Create a new verification batch
    pub fn new(max_size: usize, timeout: std::time::Duration) -> Self {
        Self {
            chunks: Vec::new(),
            max_size,
            timeout,
        }
    }

    /// Add a chunk to the batch
    pub fn add(&mut self, chunk: ChunkData) -> bool {
        if self.chunks.len() >= self.max_size {
            return false;
        }
        self.chunks.push(chunk);
        self.chunks.len() >= self.max_size
    }

    /// Check if batch is full
    pub fn is_full(&self) -> bool {
        self.chunks.len() >= self.max_size
    }

    /// Get chunks for verification
    pub fn chunks(&self) -> &[ChunkData] {
        &self.chunks
    }

    /// Clear the batch
    pub fn clear(&mut self) {
        self.chunks.clear();
    }

    /// Get timeout duration
    pub fn timeout(&self) -> std::time::Duration {
        self.timeout
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use bytes::Bytes;
    use crate::dcdn::types::ChunkId;
    use std::time::Instant;

    fn create_test_chunk(peer_id: u64, chunk_id: u64) -> ChunkData {
        ChunkData {
            id: ChunkId(chunk_id),
            sequence: chunk_id,
            timestamp: Instant::now(),
            source_peer: PeerId(peer_id),
            signature: Signature([0u8; 64]),
            data: Bytes::from(vec![1, 2, 3, 4, 5]),
            fec_group: None,
        }
    }

    #[test]
    fn test_verifier_creation() {
        let verifier = SignatureVerifier::new();
        assert_eq!(verifier.trusted_key_count(), 0);
    }

    #[test]
    fn test_add_trusted_key() {
        let verifier = SignatureVerifier::new();
        let peer_id = PeerId(1);
        let public_key = PublicKey([42u8; 32]);

        verifier.add_trusted_key(peer_id, public_key);

        assert_eq!(verifier.trusted_key_count(), 1);
    }

    #[test]
    fn test_verify_chunk() {
        let verifier = SignatureVerifier::new();
        let peer_id = PeerId(1);
        let public_key = PublicKey([42u8; 32]);

        verifier.add_trusted_key(peer_id, public_key);

        let chunk = create_test_chunk(1, 1);
        let result = verifier.verify(&chunk);

        assert!(result.is_ok());
        assert!(result.unwrap());
    }

    #[test]
    fn test_revoke_key() {
        let verifier = SignatureVerifier::new();
        let peer_id = PeerId(1);
        let public_key = PublicKey([42u8; 32]);

        verifier.add_trusted_key(peer_id, public_key);
        assert_eq!(verifier.trusted_key_count(), 1);

        verifier.revoke_key(peer_id);
        assert_eq!(verifier.trusted_key_count(), 0);
        assert!(verifier.is_revoked(&peer_id));
    }

    #[test]
    fn test_revoked_peer_verification() {
        let verifier = SignatureVerifier::new();
        let peer_id = PeerId(1);
        let public_key = PublicKey([42u8; 32]);

        verifier.add_trusted_key(peer_id, public_key);
        verifier.revoke_key(peer_id);

        let chunk = create_test_chunk(1, 1);
        let result = verifier.verify(&chunk);

        assert!(result.is_ok());
        assert!(!result.unwrap()); // Should fail for revoked peer
    }

    #[test]
    fn test_batch_verification() {
        let verifier = SignatureVerifier::new();
        let peer_id = PeerId(1);
        let public_key = PublicKey([42u8; 32]);

        verifier.add_trusted_key(peer_id, public_key);

        let chunks = vec![
            create_test_chunk(1, 1),
            create_test_chunk(1, 2),
            create_test_chunk(1, 3),
        ];

        let results = verifier.verify_batch(&chunks);
        assert!(results.is_ok());

        let results = results.unwrap();
        assert_eq!(results.len(), 3);
        assert!(results.iter().all(|&r| r));
    }

    #[test]
    fn test_verification_metrics() {
        let verifier = SignatureVerifier::new();
        let peer_id = PeerId(1);
        let public_key = PublicKey([42u8; 32]);

        verifier.add_trusted_key(peer_id, public_key);

        let chunk = create_test_chunk(1, 1);
        verifier.verify(&chunk).unwrap();

        let (total, success, failed, batch) = verifier.get_metrics();
        assert_eq!(total, 1);
        assert_eq!(success, 1);
        assert_eq!(failed, 0);
    }

    #[test]
    fn test_verification_batch() {
        let mut batch = VerificationBatch::new(3, std::time::Duration::from_millis(100));

        assert!(!batch.is_full());

        batch.add(create_test_chunk(1, 1));
        assert!(!batch.is_full());

        batch.add(create_test_chunk(1, 2));
        assert!(!batch.is_full());

        let is_full = batch.add(create_test_chunk(1, 3));
        assert!(is_full);
        assert!(batch.is_full());
    }
}
