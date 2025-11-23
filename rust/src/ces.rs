use anyhow::Result;
use chacha20poly1305::{
    aead::{Aead, KeyInit},
    XChaCha20Poly1305, XNonce,
};
use rand::RngCore;
use rayon::prelude::*;
use reed_solomon_erasure::ReedSolomon;
use sha2::{Sha256, Digest};
use std::io::{Read, Write};
use tracing::{debug, info};

use crate::types::{CesConfig, CompressionAlgorithm};
use crate::file_detector::FileDetector;

/// CES Pipeline: Compression, Encryption, Sharding
pub struct CesPipeline {
    config: CesConfig,
    encryption_key: [u8; 32],
}

impl CesPipeline {
    /// Create a new CES pipeline with the given config
    pub fn new(config: CesConfig) -> Self {
        // Generate a random encryption key (in production, derive from shared secret)
        let mut encryption_key = [0u8; 32];
        rand::thread_rng().fill_bytes(&mut encryption_key);

        Self {
            config,
            encryption_key,
        }
    }

    /// Set the encryption key explicitly
    pub fn with_key(mut self, key: [u8; 32]) -> Self {
        self.encryption_key = key;
        self
    }

    /// Get the parity count from config
    pub fn parity_count(&self) -> usize {
        self.config.parity_count
    }

    /// Process data through the CES pipeline
    pub fn process(&self, data: &[u8]) -> Result<Vec<Vec<u8>>> {
        // Step 0: Detect file type (from content)
        let file_type = FileDetector::detect_from_content(data);
        debug!("Detected file type: {}", file_type.name());
        
        // Step 1: Compress (skip if already compressed)
        let compressed = if file_type.skip_compression() {
            info!("Skipping compression for {} type", file_type.name());
            data.to_vec()
        } else {
            let level = file_type.recommended_compression_level();
            debug!("Using compression level {} for {}", level, file_type.name());
            self.compress_with_level(data, level)?
        };
        
        if compressed.len() < data.len() {
            info!("Compressed {} bytes to {} bytes ({:.1}% reduction)", 
                  data.len(), compressed.len(), 
                  (1.0 - compressed.len() as f64 / data.len() as f64) * 100.0);
        } else {
            info!("Data not compressed ({} bytes)", data.len());
        }

        // Step 2: Encrypt
        let encrypted = self.encrypt(&compressed)?;
        info!("Encrypted {} bytes", encrypted.len());
        
        // Prepend encrypted length (4 bytes) to help with reconstruction
        let enc_len = encrypted.len() as u32;
        let mut data_to_shard = enc_len.to_le_bytes().to_vec();
        data_to_shard.extend_from_slice(&encrypted);

        // Step 3: Shard with Reed-Solomon
        let shards = self.shard(&data_to_shard)?;
        info!("Created {} data shards + {} parity shards", 
              self.config.shard_count, self.config.parity_count);

        Ok(shards)
    }

    /// Reconstruct data from shards (reverse CES pipeline)
    pub fn reconstruct(&self, shards: Vec<Option<Vec<u8>>>) -> Result<Vec<u8>> {
        // Step 1: Reconstruct from Reed-Solomon shards
        let reconstructed = self.reconstruct_shards(shards)?;
        info!("Reconstructed {} bytes from shards", reconstructed.len());
        
        // Extract encrypted length
        if reconstructed.len() < 4 {
            anyhow::bail!("Reconstructed data too small");
        }
        let enc_len = u32::from_le_bytes([reconstructed[0], reconstructed[1], reconstructed[2], reconstructed[3]]) as usize;
        
        // Extract encrypted data (trim RS padding)
        if reconstructed.len() < 4 + enc_len {
            anyhow::bail!("Reconstructed data smaller than expected encrypted length");
        }
        let encrypted_data = &reconstructed[4..4 + enc_len];

        // Step 2: Decrypt
        let decrypted = self.decrypt(encrypted_data)?;
        info!("Decrypted {} bytes", decrypted.len());

        // Step 3: Decompress
        let decompressed = self.decompress(&decrypted)?;
        info!("Decompressed {} bytes", decompressed.len());

        Ok(decompressed)
    }

    /// Compress data using zstd
    fn compress(&self, data: &[u8]) -> Result<Vec<u8>> {
        self.compress_with_level(data, self.config.compression_level)
    }

    /// Compress data with specific level
    fn compress_with_level(&self, data: &[u8], level: i32) -> Result<Vec<u8>> {
        if level == 0 {
            // No compression
            return Ok(data.to_vec());
        }
        
        match self.config.compression_algorithm {
            CompressionAlgorithm::Zstd => {
                let mut compressed = Vec::new();
                let mut encoder = zstd::Encoder::new(&mut compressed, level)?;
                encoder.write_all(data)?;
                encoder.finish()?;
                Ok(compressed)
            }
            CompressionAlgorithm::Brotli => {
                // Brotli quality range: 0-11, map from our 1-22 range
                let quality = ((level as u32).min(11)).max(0);
                let buffer_size = 4096;
                let mut compressed = Vec::new();
                let mut compressor = brotli::CompressorReader::new(data, buffer_size, quality, 22);
                compressor.read_to_end(&mut compressed)?;
                Ok(compressed)
            }
            CompressionAlgorithm::None => Ok(data.to_vec()),
        }
    }

    /// Decompress data using configured algorithm
    fn decompress(&self, data: &[u8]) -> Result<Vec<u8>> {
        match self.config.compression_algorithm {
            CompressionAlgorithm::Zstd => {
                let mut decompressed = Vec::new();
                let mut decoder = zstd::Decoder::new(data)?;
                decoder.read_to_end(&mut decompressed)?;
                Ok(decompressed)
            }
            CompressionAlgorithm::Brotli => {
                let mut decompressed = Vec::new();
                let mut decompressor = brotli::Decompressor::new(data, 4096);
                decompressor.read_to_end(&mut decompressed)?;
                Ok(decompressed)
            }
            CompressionAlgorithm::None => Ok(data.to_vec()),
        }
    }

    /// Encrypt data using XChaCha20-Poly1305
    fn encrypt(&self, data: &[u8]) -> Result<Vec<u8>> {
        let cipher = XChaCha20Poly1305::new(&self.encryption_key.into());
        
        // Generate random nonce (24 bytes for XChaCha20)
        let mut nonce_bytes = [0u8; 24];
        rand::thread_rng().fill_bytes(&mut nonce_bytes);
        let nonce = XNonce::from_slice(&nonce_bytes);

        // Encrypt
        let ciphertext = cipher.encrypt(nonce, data)
            .map_err(|e| anyhow::anyhow!("Encryption failed: {}", e))?;

        // Prepend nonce to ciphertext
        let mut result = nonce_bytes.to_vec();
        result.extend_from_slice(&ciphertext);

        Ok(result)
    }

    /// Decrypt data using XChaCha20-Poly1305
    fn decrypt(&self, data: &[u8]) -> Result<Vec<u8>> {
        if data.len() < 24 {
            anyhow::bail!("Data too short to contain nonce");
        }

        let cipher = XChaCha20Poly1305::new(&self.encryption_key.into());

        // Extract nonce from the first 24 bytes
        let nonce = XNonce::from_slice(&data[..24]);
        let ciphertext = &data[24..];

        // Decrypt
        let plaintext = cipher.decrypt(nonce, ciphertext)
            .map_err(|e| anyhow::anyhow!("Decryption failed: {}", e))?;

        Ok(plaintext)
    }

    /// Shard data using Reed-Solomon erasure coding
    fn shard(&self, data: &[u8]) -> Result<Vec<Vec<u8>>> {
        let data_shards = self.config.shard_count;
        let parity_shards = self.config.parity_count;
        let total_shards = data_shards + parity_shards;

        // Calculate shard size (round up)
        let shard_size = (data.len() + data_shards - 1) / data_shards;

        // Create data shards in parallel using rayon
        let data_shards_vec: Vec<Vec<u8>> = (0..data_shards)
            .into_par_iter()
            .map(|i| {
                let start = i * shard_size;
                let end = std::cmp::min(start + shard_size, data.len());
                
                let mut shard = if start < data.len() {
                    data[start..end].to_vec()
                } else {
                    vec![]
                };
                
                // Pad to shard_size
                shard.resize(shard_size, 0);
                shard
            })
            .collect();

        let mut shards: Vec<Vec<u8>> = data_shards_vec;

        // Add empty parity shards
        for _ in 0..parity_shards {
            shards.push(vec![0u8; shard_size]);
        }

        // Generate parity shards using Reed-Solomon
        let rs = ReedSolomon::<reed_solomon_erasure::galois_8::Field>::new(data_shards, parity_shards)?;
        rs.encode(&mut shards)?;

        debug!("Created {} shards of {} bytes each", total_shards, shard_size);
        Ok(shards)
    }

    /// Reconstruct data from Reed-Solomon shards (some may be missing)
    fn reconstruct_shards(&self, mut shards: Vec<Option<Vec<u8>>>) -> Result<Vec<u8>> {
        let data_shards = self.config.shard_count;
        let parity_shards = self.config.parity_count;

        let rs = ReedSolomon::<reed_solomon_erasure::galois_8::Field>::new(data_shards, parity_shards)?;
        rs.reconstruct(&mut shards)?;

        // Concatenate data shards  
        let mut result = Vec::new();
        for i in 0..data_shards {
            if let Some(ref shard) = shards[i] {
                result.extend_from_slice(shard);
            }
        }

        Ok(result)
    }

    /// Calculate SHA256 hash of data
    pub fn hash(data: &[u8]) -> Vec<u8> {
        let mut hasher = Sha256::new();
        hasher.update(data);
        hasher.finalize().to_vec()
    }
}

/// Adaptive CES configuration based on hardware capabilities
pub fn adaptive_ces_config(
    caps: &crate::capabilities::HardwareCaps,
    file_size: u64,
    bandwidth: f32,
) -> CesConfig {
    CesConfig::adaptive(caps, file_size, bandwidth)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_compression() {
        let config = CesConfig::default();
        let pipeline = CesPipeline::new(config);
        
        let data = b"Hello, World! ".repeat(100);
        let compressed = pipeline.compress(&data).unwrap();
        assert!(compressed.len() < data.len());
        
        let decompressed = pipeline.decompress(&compressed).unwrap();
        assert_eq!(data, decompressed.as_slice());
    }

    #[test]
    fn test_encryption() {
        let config = CesConfig::default();
        let pipeline = CesPipeline::new(config);
        
        let data = b"Secret message";
        let encrypted = pipeline.encrypt(data).unwrap();
        assert_ne!(data.to_vec(), encrypted);
        
        let decrypted = pipeline.decrypt(&encrypted).unwrap();
        assert_eq!(data.to_vec(), decrypted);
    }

    #[test]
    fn test_sharding() {
        let config = CesConfig {
            compression_level: 3,
            compression_algorithm: CompressionAlgorithm::Zstd,
            shard_count: 4,
            parity_count: 2,
            chunk_size: 1024,
        };
        let pipeline = CesPipeline::new(config);
        
        let data = b"Test data for sharding".repeat(10);
        let shards = pipeline.shard(&data).unwrap();
        
        assert_eq!(shards.len(), 6); // 4 data + 2 parity
        
        // Simulate losing 2 shards
        let recovery_shards = shards.into_iter()
            .enumerate()
            .map(|(i, s)| if i == 1 || i == 3 { None } else { Some(s) })
            .collect();
        
        let reconstructed = pipeline.reconstruct_shards(recovery_shards).unwrap();
        // Note: reconstructed will be padded, so we check prefix
        assert!(reconstructed.starts_with(&data));
    }

    #[test]
    fn test_full_pipeline() {
        let config = CesConfig::default();
        let key = [0u8; 32]; // Use a fixed key for testing
        let pipeline = CesPipeline::new(config).with_key(key);
        
        let data = b"Full pipeline test data!".repeat(50);
        let shards = pipeline.process(&data).unwrap();
        
        // Simulate some shard loss (up to parity_count shards can be lost)
        let recovery_shards = shards.into_iter()
            .enumerate()
            .map(|(i, s)| if i == 2 { None } else { Some(s) })
            .collect();
        
        let reconstructed = pipeline.reconstruct(recovery_shards).unwrap();
        assert_eq!(data.to_vec(), reconstructed);
    }
}
