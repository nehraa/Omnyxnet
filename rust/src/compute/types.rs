//! Type definitions for the Distributed Compute System
//!
//! This module contains all the core types used throughout the compute engine.

use serde::{Deserialize, Serialize};
use std::fmt;
use thiserror::Error;

/// Compute configuration
#[derive(Debug, Clone)]
pub struct ComputeConfig {
    /// Maximum memory in megabytes for WASM execution
    pub max_memory_mb: u64,
    /// Maximum CPU cycles before termination
    pub max_cpu_cycles: u64,
    /// Maximum execution time in milliseconds
    pub max_execution_time_ms: u64,
    /// Enable WASI (filesystem, env vars - disabled by default for security)
    pub enable_wasi: bool,
    /// Verification mode for results
    pub verification_mode: VerificationMode,
    /// Number of worker threads for parallel execution
    pub worker_threads: usize,
    /// Simulation mode - when true, execute returns input unchanged (for testing only)
    /// SECURITY: MUST be set to false in production environments
    pub simulation_mode: bool,
}

impl Default for ComputeConfig {
    fn default() -> Self {
        Self {
            max_memory_mb: 256,
            max_cpu_cycles: 1_000_000_000, // 1 billion cycles
            max_execution_time_ms: 30_000, // 30 seconds
            enable_wasi: false,
            verification_mode: VerificationMode::Hash,
            worker_threads: num_cpus::get().max(1),
            // SECURITY: Default to false - simulation mode should only be enabled explicitly for testing
            simulation_mode: false,
        }
    }
}

/// Verification mode for compute results
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum VerificationMode {
    /// No verification (fastest, least secure)
    None,
    /// Simple SHA256 hash verification
    Hash,
    /// Full Merkle tree proof (most secure)
    Merkle,
    /// Redundant execution with comparison
    Redundancy,
}

impl Default for VerificationMode {
    fn default() -> Self {
        Self::Hash
    }
}

/// Split strategy for data chunking
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum SplitStrategy {
    /// Split by fixed size chunks
    FixedSize,
    /// Split by row/line boundaries
    RowBased,
    /// Split by custom delimiters
    Delimiter,
    /// Use WASM split function
    Custom,
}

impl Default for SplitStrategy {
    fn default() -> Self {
        Self::FixedSize
    }
}

/// Status of a compute task
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TaskStatus {
    /// Task is pending execution
    Pending,
    /// Task has been assigned to a worker
    Assigned,
    /// Task is currently executing
    Computing,
    /// Task is being verified
    Verifying,
    /// Task completed successfully
    Completed,
    /// Task failed
    Failed,
    /// Task timed out
    Timeout,
    /// Task was cancelled
    Cancelled,
}

impl fmt::Display for TaskStatus {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            TaskStatus::Pending => write!(f, "pending"),
            TaskStatus::Assigned => write!(f, "assigned"),
            TaskStatus::Computing => write!(f, "computing"),
            TaskStatus::Verifying => write!(f, "verifying"),
            TaskStatus::Completed => write!(f, "completed"),
            TaskStatus::Failed => write!(f, "failed"),
            TaskStatus::Timeout => write!(f, "timeout"),
            TaskStatus::Cancelled => write!(f, "cancelled"),
        }
    }
}

/// A compute job manifest
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JobManifest {
    /// Unique job identifier
    pub job_id: String,
    /// Compiled WASM module
    pub wasm_module: Vec<u8>,
    /// Input data for the job
    pub input_data: Vec<u8>,
    /// Split strategy
    pub split_strategy: SplitStrategy,
    /// Minimum chunk size in bytes
    pub min_chunk_size: u64,
    /// Maximum chunk size in bytes
    pub max_chunk_size: u64,
    /// Verification mode
    pub verification_mode: VerificationMode,
    /// Timeout in seconds
    pub timeout_secs: u32,
    /// Number of retries on failure
    pub retry_count: u32,
    /// Priority level (higher = more urgent)
    pub priority: u32,
    /// Redundancy level (1 = no redundancy, 2+ = multiple workers)
    pub redundancy: u32,
}

impl JobManifest {
    /// Create a new job manifest with default settings
    pub fn new(job_id: String, wasm_module: Vec<u8>, input_data: Vec<u8>) -> Self {
        Self {
            job_id,
            wasm_module,
            input_data,
            split_strategy: SplitStrategy::default(),
            min_chunk_size: 65536,   // 64 KB
            max_chunk_size: 1048576, // 1 MB
            verification_mode: VerificationMode::default(),
            timeout_secs: 300, // 5 minutes
            retry_count: 3,
            priority: 5,   // Medium priority
            redundancy: 1, // No redundancy
        }
    }

    /// Calculate estimated complexity score
    pub fn complexity_score(&self) -> f64 {
        let data_size = self.input_data.len() as f64;
        let module_size = self.wasm_module.len() as f64;

        // Simple heuristic: larger data and module = more complex
        (data_size * 0.8 + module_size * 0.2) / 1_000_000.0
    }
}

/// A single compute task (a chunk of a larger job)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ComputeTask {
    /// Unique task identifier (job_id:chunk_index)
    pub task_id: String,
    /// Parent job ID
    pub parent_job_id: String,
    /// Chunk index within the job
    pub chunk_index: u32,
    /// WASM module to execute
    pub wasm_module: Vec<u8>,
    /// Input data for this chunk
    pub input_data: Vec<u8>,
    /// Name of the function to execute ("split", "execute", or "merge")
    pub function_name: String,
    /// Delegation depth (how many levels of delegation)
    pub delegation_depth: u32,
    /// Timeout in milliseconds
    pub timeout_ms: u64,
}

impl ComputeTask {
    /// Create a new compute task
    pub fn new(
        parent_job_id: String,
        chunk_index: u32,
        wasm_module: Vec<u8>,
        input_data: Vec<u8>,
    ) -> Self {
        let task_id = format!("{}:{}", parent_job_id, chunk_index);
        Self {
            task_id,
            parent_job_id,
            chunk_index,
            wasm_module,
            input_data,
            function_name: "execute".to_string(),
            delegation_depth: 0,
            timeout_ms: 30_000,
        }
    }
}

/// Result of a compute task
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskResult {
    /// Task identifier
    pub task_id: String,
    /// Status of the task
    pub status: TaskStatus,
    /// Result data (if successful)
    pub result_data: Vec<u8>,
    /// Hash of the result for verification
    pub result_hash: String,
    /// Merkle proof (if using Merkle verification)
    pub merkle_proof: Option<Vec<String>>,
    /// Execution time in milliseconds
    pub execution_time_ms: u64,
    /// Error message (if failed)
    pub error_message: Option<String>,
}

impl TaskResult {
    /// Create a failed result
    pub fn failed(task_id: String, error: String) -> Self {
        Self {
            task_id,
            status: TaskStatus::Failed,
            result_data: Vec::new(),
            result_hash: String::new(),
            merkle_proof: None,
            execution_time_ms: 0,
            error_message: Some(error),
        }
    }
}

/// Information about a data chunk
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChunkInfo {
    /// Index of the chunk
    pub index: u32,
    /// Size in bytes
    pub size: u64,
    /// Hash of the chunk data
    pub hash: String,
    /// Status of the chunk
    pub status: TaskStatus,
    /// Assigned worker (if any)
    pub assigned_worker: Option<String>,
}

/// Compute capacity of a node
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ComputeCapacity {
    /// Number of CPU cores
    pub cpu_cores: u32,
    /// Available RAM in megabytes
    pub ram_mb: u64,
    /// Current load (0.0 to 1.0)
    pub current_load: f32,
    /// Available disk space in megabytes
    pub disk_mb: u64,
    /// Network bandwidth estimate in Mbps
    pub bandwidth_mbps: f32,
}

impl ComputeCapacity {
    /// Probe the system for compute capacity
    pub fn probe() -> Self {
        use sysinfo::{CpuExt, System, SystemExt};

        let mut sys = System::new_all();
        sys.refresh_all();

        let cpu_cores = sys.cpus().len() as u32;
        let ram_mb = sys.total_memory() / (1024 * 1024);
        let disk_mb = 0; // Would need to check specific path

        // Calculate current load from CPU usage
        let current_load: f32 =
            sys.cpus().iter().map(|cpu| cpu.cpu_usage()).sum::<f32>() / (cpu_cores as f32 * 100.0);

        Self {
            cpu_cores,
            ram_mb,
            current_load: current_load.min(1.0),
            disk_mb,
            bandwidth_mbps: 100.0, // Default estimate
        }
    }

    /// Calculate available capacity score (0.0 to 1.0)
    pub fn available_score(&self) -> f32 {
        let cpu_score = 1.0 - self.current_load;
        let ram_score = (self.ram_mb as f32 / 8192.0).min(1.0); // Normalize to 8GB

        cpu_score * 0.6 + ram_score * 0.4
    }

    /// Check if node can accept work with given requirements
    pub fn can_accept(&self, required_ram_mb: u64, _complexity: f64) -> bool {
        self.current_load < 0.9 && self.ram_mb >= required_ram_mb
    }
}

impl Default for ComputeCapacity {
    fn default() -> Self {
        Self::probe()
    }
}

/// Errors that can occur during computation
#[derive(Error, Debug)]
pub enum ComputeError {
    #[error("WASM module loading failed: {0}")]
    WasmLoadError(String),

    #[error("WASM execution failed: {0}")]
    WasmExecutionError(String),

    #[error("Resource limit exceeded: {0}")]
    ResourceLimitExceeded(String),

    #[error("Verification failed: {0}")]
    VerificationFailed(String),

    #[error("Serialization error: {0}")]
    SerializationError(String),

    #[error("Task timeout after {0}ms")]
    Timeout(u64),

    #[error("Task cancelled")]
    Cancelled,

    #[error("Invalid input: {0}")]
    InvalidInput(String),

    #[error("Internal error: {0}")]
    Internal(String),
}

impl From<std::io::Error> for ComputeError {
    fn from(err: std::io::Error) -> Self {
        ComputeError::Internal(err.to_string())
    }
}

impl From<serde_json::Error> for ComputeError {
    fn from(err: serde_json::Error) -> Self {
        ComputeError::SerializationError(err.to_string())
    }
}
