//! Distributed Compute Engine Module
//! 
//! This module implements the compute engine for the Distributed Compute System.
//! Following the Golden Rule: Rust handles the compute sandbox, verification, and split/merge execution.
//!
//! # Architecture
//! 
//! ```text
//! ┌─────────────────────────────────────────────────────────────┐
//! │                     Rust Compute Engine                      │
//! ├─────────────────────────────────────────────────────────────┤
//! │  Sandbox (WASM)     │ Verification      │ Executor          │
//! │  ├─→ Wasmtime       │ ├─→ Merkle Trees  │ ├─→ Split()       │
//! │  ├─→ Metering       │ ├─→ SHA256        │ ├─→ Execute()     │
//! │  └─→ Resource Limits│ └─→ Result Hash   │ └─→ Merge()       │
//! └─────────────────────────────────────────────────────────────┘
//! ```

mod types;
mod sandbox;
mod metering;
mod verification;
mod executor;

// Re-export public types
pub use types::{
    ComputeConfig, ComputeTask, TaskResult, TaskStatus,
    JobManifest, ChunkInfo, VerificationMode, SplitStrategy,
    ComputeError, ComputeCapacity,
};

pub use sandbox::{WasmSandbox, SandboxConfig};
pub use metering::{ResourceLimits, ResourceUsage, Metering};
pub use verification::{MerkleTree, ResultVerifier, VerificationResult};
pub use executor::{ComputeExecutor, ExecutionContext};

use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::{info, debug};

/// Main entry point for the Compute Engine
/// 
/// The ComputeEngine coordinates sandboxed execution, resource management,
/// and verification of compute tasks.
pub struct ComputeEngine {
    config: ComputeConfig,
    sandbox: Arc<RwLock<WasmSandbox>>,
    executor: Arc<ComputeExecutor>,
    verifier: Arc<ResultVerifier>,
    capacity: Arc<RwLock<ComputeCapacity>>,
}

impl ComputeEngine {
    /// Create a new ComputeEngine with the given configuration
    pub fn new(config: ComputeConfig) -> Result<Self, ComputeError> {
        info!("Initializing Compute Engine with config: {:?}", config);
        
        let sandbox_config = SandboxConfig {
            max_memory_bytes: config.max_memory_mb * 1024 * 1024,
            max_cpu_cycles: config.max_cpu_cycles,
            max_execution_time_ms: config.max_execution_time_ms,
            enable_wasi: config.enable_wasi,
        };
        
        let sandbox = WasmSandbox::new(sandbox_config)?;
        let executor = ComputeExecutor::new(config.clone());
        let verifier = ResultVerifier::new(config.verification_mode);
        
        // Probe system capacity
        let capacity = ComputeCapacity::probe();
        info!("Compute capacity: {:?}", capacity);
        
        Ok(Self {
            config,
            sandbox: Arc::new(RwLock::new(sandbox)),
            executor: Arc::new(executor),
            verifier: Arc::new(verifier),
            capacity: Arc::new(RwLock::new(capacity)),
        })
    }
    
    /// Process a compute task
    /// 
    /// This is the main entry point for executing a compute task.
    /// The task's WASM module is loaded into the sandbox, executed with
    /// resource limits, and the result is verified before returning.
    pub async fn process_task(&self, task: ComputeTask) -> Result<TaskResult, ComputeError> {
        let start = std::time::Instant::now();
        debug!("Processing task: {}", task.task_id);
        
        // Load WASM module if not already loaded
        let sandbox = self.sandbox.write().await;
        
        // Execute in sandbox
        let result_data = sandbox.execute(
            &task.wasm_module,
            &task.input_data,
            &task.function_name,
        )?;
        
        drop(sandbox);
        
        // Verify result
        let result_hash = self.verifier.hash_result(&result_data);
        let merkle_proof = if self.config.verification_mode == VerificationMode::Merkle {
            Some(self.verifier.create_merkle_proof(&result_data)?)
        } else {
            None
        };
        
        let execution_time_ms = start.elapsed().as_millis() as u64;
        
        let result = TaskResult {
            task_id: task.task_id.clone(),
            status: TaskStatus::Completed,
            result_data,
            result_hash,
            merkle_proof,
            execution_time_ms,
            error_message: None,
        };
        
        info!("Task {} completed in {}ms", task.task_id, execution_time_ms);
        Ok(result)
    }
    
    /// Split data using the job's split function
    pub async fn split_data(&self, job: &JobManifest, data: &[u8]) -> Result<Vec<Vec<u8>>, ComputeError> {
        debug!("Splitting data for job: {}", job.job_id);
        
        let sandbox = self.sandbox.write().await;
        
        // Execute split function
        let chunks_data = sandbox.execute(
            &job.wasm_module,
            data,
            "split",
        )?;
        
        drop(sandbox);
        
        // Deserialize chunks (assuming they're length-prefixed)
        let chunks = self.executor.deserialize_chunks(&chunks_data)?;
        
        info!("Split data into {} chunks for job {}", chunks.len(), job.job_id);
        Ok(chunks)
    }
    
    /// Merge results using the job's merge function
    pub async fn merge_results(&self, job: &JobManifest, results: Vec<Vec<u8>>) -> Result<Vec<u8>, ComputeError> {
        debug!("Merging {} results for job: {}", results.len(), job.job_id);
        
        // Serialize results for WASM
        let merged_input = self.executor.serialize_chunks(&results)?;
        
        let sandbox = self.sandbox.write().await;
        
        // Execute merge function
        let merged = sandbox.execute(
            &job.wasm_module,
            &merged_input,
            "merge",
        )?;
        
        drop(sandbox);
        
        info!("Merged {} results for job {}", results.len(), job.job_id);
        Ok(merged)
    }
    
    /// Get current compute capacity
    pub async fn get_capacity(&self) -> ComputeCapacity {
        self.capacity.read().await.clone()
    }
    
    /// Update capacity with current load
    pub async fn update_load(&self, current_load: f32) {
        let mut capacity = self.capacity.write().await;
        capacity.current_load = current_load;
    }
    
    /// Verify a task result
    pub fn verify_result(&self, result: &TaskResult, expected_hash: Option<&str>) -> VerificationResult {
        self.verifier.verify(result, expected_hash)
    }
}

impl Default for ComputeEngine {
    fn default() -> Self {
        Self::new(ComputeConfig::default()).expect("Failed to create default ComputeEngine")
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[tokio::test]
    async fn test_compute_engine_creation() {
        let config = ComputeConfig::default();
        let engine = ComputeEngine::new(config);
        assert!(engine.is_ok());
    }
    
    #[tokio::test]
    async fn test_get_capacity() {
        let engine = ComputeEngine::default();
        let capacity = engine.get_capacity().await;
        assert!(capacity.cpu_cores > 0);
        assert!(capacity.ram_mb > 0);
    }
}
