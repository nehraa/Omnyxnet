//! Executor module for split, execute, and merge operations
//!
//! This module handles the actual execution of compute tasks,
//! including data serialization for WASM and result processing.

use crate::compute::types::{ChunkInfo, ComputeConfig, ComputeError, JobManifest, TaskStatus};
use rayon::prelude::*;
use sha2::{Digest, Sha256};
use tracing::{debug, info};

/// Execution context for a compute task
#[derive(Debug, Clone)]
pub struct ExecutionContext {
    /// Job ID
    pub job_id: String,
    /// Current chunk index being processed
    pub chunk_index: u32,
    /// Total number of chunks
    pub total_chunks: u32,
    /// Delegation depth
    pub delegation_depth: u32,
    /// Start time
    pub start_time: std::time::Instant,
}

impl ExecutionContext {
    /// Create a new execution context
    pub fn new(job_id: String, chunk_index: u32, total_chunks: u32) -> Self {
        Self {
            job_id,
            chunk_index,
            total_chunks,
            delegation_depth: 0,
            start_time: std::time::Instant::now(),
        }
    }

    /// Get elapsed time in milliseconds
    pub fn elapsed_ms(&self) -> u64 {
        self.start_time.elapsed().as_millis() as u64
    }
}

/// Compute executor for split, execute, and merge operations
pub struct ComputeExecutor {
    config: ComputeConfig,
}

impl ComputeExecutor {
    /// Create a new compute executor
    pub fn new(config: ComputeConfig) -> Self {
        Self { config }
    }

    /// Split data into chunks based on job configuration
    ///
    /// Uses the job's split strategy to divide data into manageable chunks.
    /// Returns a vector of chunks and their metadata.
    pub fn split_data(
        &self,
        job: &JobManifest,
        data: &[u8],
    ) -> Result<(Vec<Vec<u8>>, Vec<ChunkInfo>), ComputeError> {
        let chunk_size = self.calculate_chunk_size(job, data.len());
        debug!(
            "Splitting {} bytes into chunks of ~{} bytes",
            data.len(),
            chunk_size
        );

        let chunks: Vec<Vec<u8>> = data.chunks(chunk_size).map(|c| c.to_vec()).collect();

        let chunk_infos: Vec<ChunkInfo> = chunks
            .par_iter()
            .enumerate()
            .map(|(i, chunk)| ChunkInfo {
                index: i as u32,
                size: chunk.len() as u64,
                hash: self.hash_data(chunk),
                status: TaskStatus::Pending,
                assigned_worker: None,
            })
            .collect();

        info!("Split data into {} chunks", chunks.len());
        Ok((chunks, chunk_infos))
    }

    /// Calculate optimal chunk size based on job config and data size
    fn calculate_chunk_size(&self, job: &JobManifest, data_size: usize) -> usize {
        let min_size = job.min_chunk_size as usize;
        let max_size = job.max_chunk_size as usize;

        // Aim for 4-16 chunks
        let target_chunks = 8;
        let calculated_size = data_size / target_chunks;

        calculated_size.clamp(min_size, max_size).max(1)
    }

    /// Merge multiple result chunks into a single result
    ///
    /// This is the reverse of split - combines results back together.
    pub fn merge_results(&self, results: Vec<Vec<u8>>) -> Result<Vec<u8>, ComputeError> {
        if results.is_empty() {
            return Ok(Vec::new());
        }

        let num_results = results.len();
        debug!("Merging {} result chunks", num_results);

        // Simple concatenation merge
        // Real implementations might need more sophisticated merging
        let total_size: usize = results.iter().map(|r| r.len()).sum();
        let mut merged = Vec::with_capacity(total_size);

        for result in &results {
            merged.extend_from_slice(result);
        }

        info!("Merged {} chunks into {} bytes", num_results, merged.len());
        Ok(merged)
    }

    /// Serialize chunks for passing to WASM
    ///
    /// Format: [num_chunks(4 bytes), [chunk_len(4 bytes), chunk_data]...]
    pub fn serialize_chunks(&self, chunks: &[Vec<u8>]) -> Result<Vec<u8>, ComputeError> {
        let mut output = Vec::new();

        // Write number of chunks
        output.extend_from_slice(&(chunks.len() as u32).to_le_bytes());

        // Write each chunk with length prefix
        for chunk in chunks {
            output.extend_from_slice(&(chunk.len() as u32).to_le_bytes());
            output.extend_from_slice(chunk);
        }

        Ok(output)
    }

    /// Deserialize chunks from WASM output
    ///
    /// Format: [num_chunks(4 bytes), [chunk_len(4 bytes), chunk_data]...]
    pub fn deserialize_chunks(&self, data: &[u8]) -> Result<Vec<Vec<u8>>, ComputeError> {
        if data.len() < 4 {
            return Err(ComputeError::SerializationError(
                "Data too small for chunk header".to_string(),
            ));
        }

        let num_chunks = u32::from_le_bytes([data[0], data[1], data[2], data[3]]) as usize;
        let mut chunks = Vec::with_capacity(num_chunks);
        let mut offset = 4;

        for i in 0..num_chunks {
            if offset + 4 > data.len() {
                return Err(ComputeError::SerializationError(format!(
                    "Truncated chunk header at chunk {}",
                    i
                )));
            }

            let chunk_len = u32::from_le_bytes([
                data[offset],
                data[offset + 1],
                data[offset + 2],
                data[offset + 3],
            ]) as usize;
            offset += 4;

            if offset + chunk_len > data.len() {
                return Err(ComputeError::SerializationError(format!(
                    "Truncated chunk data at chunk {} (need {} bytes, have {})",
                    i,
                    chunk_len,
                    data.len() - offset
                )));
            }

            chunks.push(data[offset..offset + chunk_len].to_vec());
            offset += chunk_len;
        }

        Ok(chunks)
    }

    /// Hash data using SHA256
    pub fn hash_data(&self, data: &[u8]) -> String {
        let mut hasher = Sha256::new();
        hasher.update(data);
        hex::encode(hasher.finalize())
    }

    /// Create execution context for a chunk
    pub fn create_context(
        &self,
        job_id: String,
        chunk_index: u32,
        total_chunks: u32,
    ) -> ExecutionContext {
        ExecutionContext::new(job_id, chunk_index, total_chunks)
    }

    /// Calculate complexity score for a job
    ///
    /// Higher score = more complex = more likely to delegate
    pub fn calculate_complexity(&self, job: &JobManifest) -> f64 {
        let data_factor = job.input_data.len() as f64 / (1024.0 * 1024.0); // MB
        let wasm_factor = job.wasm_module.len() as f64 / (64.0 * 1024.0); // 64KB units

        // Complexity is roughly data_size * module_complexity
        data_factor * (1.0 + wasm_factor * 0.1)
    }

    /// Determine if a task should be delegated
    ///
    /// Returns true if the complexity exceeds the node's capacity
    pub fn should_delegate(&self, complexity: f64, capacity: f64) -> bool {
        complexity > capacity
    }

    /// Get configuration
    pub fn config(&self) -> &ComputeConfig {
        &self.config
    }
}

impl Default for ComputeExecutor {
    fn default() -> Self {
        Self::new(ComputeConfig::default())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::compute::types::SplitStrategy;

    fn create_test_job(data_size: usize) -> JobManifest {
        JobManifest {
            job_id: "test_job".to_string(),
            wasm_module: vec![0; 1024],
            input_data: vec![0; data_size],
            split_strategy: SplitStrategy::FixedSize,
            min_chunk_size: 1024,
            max_chunk_size: 65536,
            verification_mode: crate::compute::types::VerificationMode::Hash,
            timeout_secs: 300,
            retry_count: 3,
            priority: 5,
            redundancy: 1,
        }
    }

    #[test]
    fn test_split_data() {
        let executor = ComputeExecutor::default();
        let job = create_test_job(100_000);
        let data = vec![42u8; 100_000];

        let (chunks, infos) = executor.split_data(&job, &data).unwrap();

        assert!(!chunks.is_empty());
        assert_eq!(chunks.len(), infos.len());

        // Verify total size
        let total: usize = chunks.iter().map(|c| c.len()).sum();
        assert_eq!(total, 100_000);
    }

    #[test]
    fn test_merge_results() {
        let executor = ComputeExecutor::default();

        let chunks = vec![vec![1, 2, 3], vec![4, 5, 6], vec![7, 8, 9]];

        let merged = executor.merge_results(chunks).unwrap();

        assert_eq!(merged, vec![1, 2, 3, 4, 5, 6, 7, 8, 9]);
    }

    #[test]
    fn test_serialize_deserialize_roundtrip() {
        let executor = ComputeExecutor::default();

        let chunks = vec![vec![1, 2, 3, 4], vec![5, 6, 7, 8], vec![9, 10, 11, 12]];

        let serialized = executor.serialize_chunks(&chunks).unwrap();
        let deserialized = executor.deserialize_chunks(&serialized).unwrap();

        assert_eq!(chunks, deserialized);
    }

    #[test]
    fn test_complexity_calculation() {
        let executor = ComputeExecutor::default();

        let small_job = create_test_job(1024); // 1 KB
        let large_job = create_test_job(10 * 1024 * 1024); // 10 MB

        let small_complexity = executor.calculate_complexity(&small_job);
        let large_complexity = executor.calculate_complexity(&large_job);

        assert!(large_complexity > small_complexity);
    }

    #[test]
    fn test_should_delegate() {
        let executor = ComputeExecutor::default();

        // Low complexity, high capacity = don't delegate
        assert!(!executor.should_delegate(1.0, 10.0));

        // High complexity, low capacity = delegate
        assert!(executor.should_delegate(10.0, 1.0));
    }

    #[test]
    fn test_hash_data() {
        let executor = ComputeExecutor::default();

        let data1 = b"test data 1";
        let data2 = b"test data 2";

        let hash1 = executor.hash_data(data1);
        let hash2 = executor.hash_data(data2);

        assert_ne!(hash1, hash2);
        assert_eq!(hash1.len(), 64); // SHA256 hex = 64 chars
    }

    #[test]
    fn test_execution_context() {
        let executor = ComputeExecutor::default();
        let ctx = executor.create_context("job1".to_string(), 0, 10);

        assert_eq!(ctx.job_id, "job1");
        assert_eq!(ctx.chunk_index, 0);
        assert_eq!(ctx.total_chunks, 10);

        // Wait a bit and check elapsed time
        std::thread::sleep(std::time::Duration::from_millis(10));
        assert!(ctx.elapsed_ms() >= 10);
    }
}
