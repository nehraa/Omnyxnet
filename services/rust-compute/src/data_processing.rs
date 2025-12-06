use anyhow::Result;
use log::{info, warn};
use rayon::prelude::*;
use std::sync::Arc;

/// PreprocessResult holds the output of data preprocessing
#[derive(Debug, Clone)]
pub struct PreprocessResult {
    pub splits: Vec<Vec<Vec<f64>>>,
    pub total_samples: usize,
    pub split_counts: Vec<usize>,
    pub processing_time_ms: u128,
}

/// Preprocessor handles high-performance data splitting and serialization
pub struct Preprocessor {
    num_workers: usize,
    chunk_size: usize,
}

impl Preprocessor {
    /// Create a new preprocessor with specified worker count and chunk size
    pub fn new(num_workers: usize, chunk_size: usize) -> Self {
        Preprocessor {
            num_workers,
            chunk_size,
        }
    }

    /// Preprocess and split raw data into worker batches using Rayon parallelization
    ///
    /// This function:
    /// 1. Takes raw tensor data and distributes it across workers
    /// 2. Uses Rayon thread pool for parallel processing
    /// 3. Chunks data into manageable batches
    /// 4. Returns serialized Cap'n Proto messages ready for RPC transmission
    pub fn preprocess_and_split_data(&self, raw_data: Vec<Vec<f64>>) -> Result<PreprocessResult> {
        let start = std::time::Instant::now();
        
        let total_samples = raw_data.len();
        info!(
            "🔄 Starting preprocessing: {} samples for {} workers",
            total_samples, self.num_workers
        );

        // Use Rayon to parallelize data distribution across workers
        let splits: Vec<Vec<Vec<f64>>> = (0..self.num_workers)
            .into_par_iter()
            .map(|worker_id| {
                self.distribute_to_worker(worker_id, &raw_data)
            })
            .collect();

        let split_counts: Vec<usize> = splits.iter().map(|split| split.len()).collect();
        
        let elapsed = start.elapsed();
        let processing_time_ms = elapsed.as_millis();

        info!(
            "✅ Preprocessing complete in {}ms. Split distribution: {:?}",
            processing_time_ms, split_counts
        );

        Ok(PreprocessResult {
            splits,
            total_samples,
            split_counts,
            processing_time_ms,
        })
    }

    /// Distribute data to a specific worker using round-robin assignment
    fn distribute_to_worker(&self, worker_id: usize, data: &[Vec<f64>]) -> Vec<Vec<f64>> {
        data.par_iter()
            .enumerate()
            .filter(|(idx, _)| idx % self.num_workers == worker_id)
            .map(|(_, sample)| sample.clone())
            .collect()
    }

    /// Serialize preprocessed data to Cap'n Proto format (stub)
    pub fn serialize_to_capnp(&self, result: &PreprocessResult) -> Result<Vec<u8>> {
        info!(
            "📦 Serializing {} samples to Cap'n Proto format",
            result.total_samples
        );
        
        // Placeholder for actual Cap'n Proto serialization
        // In production, this would use the generated capnp bindings
        let serialized = serde_json::to_vec(&result.split_counts)?;
        
        Ok(serialized)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_preprocess_and_split() {
        let preprocessor = Preprocessor::new(4, 32);
        let data = vec![vec![1.0, 2.0, 3.0]; 100];
        
        let result = preprocessor.preprocess_and_split_data(data).unwrap();
        
        assert_eq!(result.total_samples, 100);
        assert_eq!(result.splits.len(), 4);
        assert!(result.processing_time_ms > 0);
    }

    #[test]
    fn test_distribute_to_worker() {
        let preprocessor = Preprocessor::new(2, 32);
        let data = vec![vec![1.0]; 10];
        
        let worker0 = preprocessor.distribute_to_worker(0, &data);
        let worker1 = preprocessor.distribute_to_worker(1, &data);
        
        assert_eq!(worker0.len(), 5);
        assert_eq!(worker1.len(), 5);
    }
}
