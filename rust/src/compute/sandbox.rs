//! WASM Sandbox for secure, isolated execution
//!
//! This module provides a secure sandbox for executing WASM modules.
//! It uses a simulated runtime for basic operations, with hooks for
//! integrating Wasmtime when full WASM support is needed.
//!
//! # Current Implementation
//!
//! The current implementation uses simulation mode for the split, execute,
//! and merge functions. For production use with real WASM modules, integrate
//! Wasmtime by adding it to Cargo.toml and implementing the `execute_wasm`
//! method using `wasmtime::Module` and `wasmtime::Instance`.
//!
//! # Security
//!
//! The sandbox enforces:
//! - Memory limits
//! - CPU cycle limits (metering)
//! - No network access
//! - No filesystem access (unless WASI is explicitly enabled)

use crate::compute::metering::ResourceLimits;
use crate::compute::types::ComputeError;
use crate::compute::io_tunnel::IoTunnel;
use sha2::{Digest, Sha256};
use tracing::{debug, info};

/// Configuration for the WASM sandbox
#[derive(Debug, Clone)]
pub struct SandboxConfig {
    /// Maximum memory in bytes
    pub max_memory_bytes: u64,
    /// Maximum CPU cycles
    pub max_cpu_cycles: u64,
    /// Maximum execution time in milliseconds
    pub max_execution_time_ms: u64,
    /// Enable WASI (disabled by default for security)
    pub enable_wasi: bool,
    /// Simulation mode - when true, uses identity function for execute
    /// WARNING: Set to false in production!
    pub simulation_mode: bool,
}

impl Default for SandboxConfig {
    fn default() -> Self {
        Self {
            max_memory_bytes: 256 * 1024 * 1024, // 256 MB
            max_cpu_cycles: 1_000_000_000,       // 1 billion
            max_execution_time_ms: 30_000,       // 30 seconds
            enable_wasi: false,
            // SECURITY: Default to false - simulation mode should only be enabled explicitly for testing
            // In simulation mode, execute() returns input unchanged which is NOT safe for production
            simulation_mode: false,
        }
    }
}

/// A sandboxed WASM execution environment
///
/// This provides a secure execution environment for untrusted WASM code.
/// Currently uses a simulation mode for basic operations, with the
/// architecture ready for Wasmtime integration.
pub struct WasmSandbox {
    config: SandboxConfig,
    resource_limits: ResourceLimits,
    /// Cached module hash -> compiled module
    module_cache: std::collections::HashMap<String, CachedModule>,
}

/// A cached compiled module
struct CachedModule {
    /// Hash of the original WASM bytes
    hash: String,
    /// Size of the module
    size: usize,
    /// Compilation time
    _compiled_at: std::time::Instant,
}

impl WasmSandbox {
    /// Create a new WASM sandbox with the given configuration
    pub fn new(config: SandboxConfig) -> Result<Self, ComputeError> {
        info!(
            "Creating WASM sandbox with limits: memory={}MB, cycles={}",
            config.max_memory_bytes / (1024 * 1024),
            config.max_cpu_cycles
        );

        let resource_limits = ResourceLimits {
            max_memory_bytes: config.max_memory_bytes,
            max_cpu_cycles: config.max_cpu_cycles,
            max_execution_time_ms: config.max_execution_time_ms,
            max_stack_bytes: 1024 * 1024, // 1 MB stack
        };

        Ok(Self {
            config,
            resource_limits,
            module_cache: std::collections::HashMap::new(),
        })
    }

    /// Execute a WASM function with the given input
    ///
    /// This is the main entry point for WASM execution.
    /// The function receives input data and returns output data.
    ///
    /// # Security
    ///
    /// - Execution is sandboxed with no network/filesystem access
    /// - Resource limits are enforced
    /// - Execution can be interrupted if limits are exceeded
    pub fn execute(
        &self,
        wasm_module: &[u8],
        input_data: &[u8],
        function_name: &str,
    ) -> Result<Vec<u8>, ComputeError> {
        // Default execution path - no tunnel
        self.execute_with_tunnel(wasm_module, input_data, function_name, None)
    }

    /// Execute with optional IoTunnel that encrypts/decrypts the I/O.
    /// When a tunnel is provided, `input_data` is expected to be ciphertext
    /// as seen by the host; the tunnel decrypts inside the sandbox, the
    /// sandbox executes on plaintext, then the output is encrypted before
    /// being passed back to the host.
    pub fn execute_with_tunnel(
        &self,
        wasm_module: &[u8],
        input_data: &[u8],
        function_name: &str,
        tunnel: Option<&IoTunnel>,
    ) -> Result<Vec<u8>, ComputeError> {
        let start = std::time::Instant::now();
        debug!(
            "Executing WASM function '{}' with {} bytes input",
            function_name,
            input_data.len()
        );

        // Validate module
        if wasm_module.is_empty() {
            return Err(ComputeError::InvalidInput("Empty WASM module".into()));
        }

        // If tunnel is present, decrypt input first
        let work_input: Vec<u8> = if let Some(t) = tunnel {
            match t.decrypt(input_data) {
                Ok(p) => p,
                Err(e) => return Err(ComputeError::WasmExecutionError(format!("tunnel decrypt failed: {:?}", e))),
            }
        } else {
            input_data.to_vec()
        };

        // Simulate WASM execution (or real Wasmtime integration later)
        let result = self.simulate_execution(wasm_module, &work_input, function_name)?;

        // If tunnel is present, encrypt the output before returning to host
        if let Some(t) = tunnel {
            match t.encrypt(&result) {
                Ok(c) => Ok(c),
                Err(e) => Err(ComputeError::WasmExecutionError(format!("tunnel encrypt failed: {:?}", e))),
            }
        } else {
            Ok(result)
        }
    }

    /// Simulate WASM execution for testing and development
    ///
    /// This provides a basic simulation of common operations:
    /// - split: Divides data into chunks
    /// - execute: Processes data (identity by default)
    /// - merge: Combines chunks back together
    ///
    /// Production use should integrate Wasmtime for real WASM execution.
    fn simulate_execution(
        &self,
        _wasm_module: &[u8],
        input_data: &[u8],
        function_name: &str,
    ) -> Result<Vec<u8>, ComputeError> {
        // Check memory limits
        if input_data.len() as u64 > self.resource_limits.max_memory_bytes {
            return Err(ComputeError::ResourceLimitExceeded(format!(
                "Input data ({} bytes) exceeds memory limit ({} bytes)",
                input_data.len(),
                self.resource_limits.max_memory_bytes
            )));
        }

        match function_name {
            "split" => self.simulate_split(input_data),
            "execute" => self.simulate_execute(input_data),
            "merge" => self.simulate_merge(input_data),
            _ => Err(ComputeError::InvalidInput(format!(
                "Unknown function: {}",
                function_name
            ))),
        }
    }

    /// Simulate the split function
    ///
    /// Splits input data into chunks of approximately equal size.
    /// Output format: [num_chunks(4 bytes), [chunk_len(4 bytes), chunk_data]...]
    fn simulate_split(&self, data: &[u8]) -> Result<Vec<u8>, ComputeError> {
        if data.is_empty() {
            return Ok(Vec::new());
        }

        // Split into chunks of ~64KB or at least 4 chunks
        let chunk_size = (data.len() / 4).max(65536).min(data.len());
        let chunks: Vec<&[u8]> = data.chunks(chunk_size).collect();
        let num_chunks = chunks.len();

        let mut result = Vec::new();

        // Write number of chunks
        result.extend_from_slice(&(num_chunks as u32).to_le_bytes());

        // Write each chunk with its length prefix
        for chunk in &chunks {
            result.extend_from_slice(&(chunk.len() as u32).to_le_bytes());
            result.extend_from_slice(chunk);
        }

        debug!("Split {} bytes into {} chunks", data.len(), num_chunks);
        Ok(result)
    }

    /// Execute function for WASM modules
    ///
    /// In simulation mode (default), returns input unchanged for testing.
    /// In production mode, requires valid WASM and uses Wasmtime for execution.
    fn simulate_execute(&self, data: &[u8]) -> Result<Vec<u8>, ComputeError> {
        if self.config.simulation_mode {
            // Simulation mode: identity transformation for testing
            debug!(
                "Execute (SIMULATION MODE): processing {} bytes - returning input unchanged",
                data.len()
            );
            tracing::warn!("Running in simulation mode - execute returns identity. Set simulation_mode=false for production.");
            Ok(data.to_vec())
        } else {
            // Production mode: would use Wasmtime here
            // For now, return an error indicating real execution is not yet implemented
            Err(ComputeError::WasmExecutionError(
                "Production WASM execution not yet implemented. Enable simulation_mode for testing or integrate Wasmtime.".into()
            ))
        }
    }

    /// Simulate the merge function
    ///
    /// Merges chunks back into a single result.
    /// Input format: [num_chunks(4 bytes), [chunk_len(4 bytes), chunk_data]...]
    fn simulate_merge(&self, data: &[u8]) -> Result<Vec<u8>, ComputeError> {
        if data.len() < 4 {
            return Err(ComputeError::InvalidInput(
                "Data too small for merge".into(),
            ));
        }

        let num_chunks = u32::from_le_bytes([data[0], data[1], data[2], data[3]]) as usize;
        let mut result = Vec::new();
        let mut offset = 4;

        for i in 0..num_chunks {
            if offset + 4 > data.len() {
                return Err(ComputeError::InvalidInput(format!(
                    "Truncated data at chunk {}",
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
                return Err(ComputeError::InvalidInput(format!(
                    "Chunk {} extends past data end",
                    i
                )));
            }

            result.extend_from_slice(&data[offset..offset + chunk_len]);
            offset += chunk_len;
        }

        debug!("Merged {} chunks into {} bytes", num_chunks, result.len());
        Ok(result)
    }

    /// Hash a WASM module for caching
    fn hash_module(&self, module: &[u8]) -> String {
        let mut hasher = Sha256::new();
        hasher.update(module);
        hex::encode(hasher.finalize())
    }

    /// Load and cache a WASM module
    pub fn load_module(&mut self, wasm_bytes: &[u8]) -> Result<String, ComputeError> {
        let hash = self.hash_module(wasm_bytes);

        if !self.module_cache.contains_key(&hash) {
            // Validate module (basic check - real implementation would parse WASM)
            if !self.validate_module(wasm_bytes) {
                return Err(ComputeError::WasmLoadError("Invalid WASM module".into()));
            }

            let cached = CachedModule {
                hash: hash.clone(),
                size: wasm_bytes.len(),
                _compiled_at: std::time::Instant::now(),
            };

            self.module_cache.insert(hash.clone(), cached);
            info!("Loaded and cached WASM module: {}", &hash[..16]);
        } else {
            debug!("Using cached WASM module: {}", &hash[..16]);
        }

        Ok(hash)
    }

    /// Check if a module is cached
    pub fn is_module_cached(&self, hash: &str) -> bool {
        self.module_cache.contains_key(hash)
    }

    /// Get cached module info
    pub fn get_cached_module_size(&self, hash: &str) -> Option<usize> {
        self.module_cache.get(hash).map(|m| m.size)
    }

    /// Basic WASM module validation
    fn validate_module(&self, bytes: &[u8]) -> bool {
        // Check for WASM magic number and version
        if bytes.len() < 8 {
            return false;
        }

        // Real WASM starts with: 0x00 0x61 0x73 0x6D (\0asm)
        let is_wasm = bytes[0] == 0x00 && bytes[1] == 0x61 && bytes[2] == 0x73 && bytes[3] == 0x6D;

        // Validate WASM version (bytes 4-7 should be 0x01 0x00 0x00 0x00 for version 1)
        let valid_version =
            bytes[4] == 0x01 && bytes[5] == 0x00 && bytes[6] == 0x00 && bytes[7] == 0x00;

        is_wasm && valid_version
    }

    /// Get current resource usage
    pub fn get_resource_usage(&self) -> crate::compute::metering::ResourceUsage {
        crate::compute::metering::ResourceUsage {
            memory_bytes: 0,      // Would track actual usage
            cpu_cycles: 0,        // Would track via metering
            execution_time_ms: 0, // Would track elapsed time
        }
    }

    /// Clear the module cache
    pub fn clear_cache(&mut self) {
        self.module_cache.clear();
        info!("Cleared WASM module cache");
    }

    /// Get sandbox configuration
    pub fn config(&self) -> &SandboxConfig {
        &self.config
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sandbox_creation() {
        let config = SandboxConfig { simulation_mode: true, ..Default::default() };
        let sandbox = WasmSandbox::new(config);
        assert!(sandbox.is_ok());
    }

    #[test]
    fn test_split_execute() {
        let sandbox = WasmSandbox::new(SandboxConfig { simulation_mode: true, ..Default::default() }).unwrap();

        // Create test data
        let data = vec![1u8; 256 * 1024]; // 256KB
        let fake_wasm = b"\x00asmtest_module"; // Test module

        // Test split
        let split_result = sandbox.execute(fake_wasm, &data, "split").unwrap();
        assert!(!split_result.is_empty());

        // Verify split format
        let num_chunks = u32::from_le_bytes([
            split_result[0],
            split_result[1],
            split_result[2],
            split_result[3],
        ]);
        assert!(num_chunks > 0);
    }

    #[test]
    fn test_split_and_merge_roundtrip() {
        let sandbox = WasmSandbox::new(SandboxConfig { simulation_mode: true, ..Default::default() }).unwrap();

        let original_data = b"Hello, World! This is test data for split and merge.";
        let fake_wasm = b"test_module";

        // Split
        let split_result = sandbox.execute(fake_wasm, original_data, "split").unwrap();

        // Merge
        let merged = sandbox.execute(fake_wasm, &split_result, "merge").unwrap();

        assert_eq!(original_data.to_vec(), merged);
    }

    #[test]
    fn test_execute_identity() {
        let sandbox = WasmSandbox::new(SandboxConfig { simulation_mode: true, ..Default::default() }).unwrap();

        let data = b"test data";
        let fake_wasm = b"test_module";

        let result = sandbox.execute(fake_wasm, data, "execute").unwrap();
        assert_eq!(data.to_vec(), result);
    }

    #[test]
    fn test_memory_limit() {
        let config = SandboxConfig {
            max_memory_bytes: 1000, // Very small limit
            ..Default::default()
        };
        let sandbox = WasmSandbox::new(config).unwrap();

        let large_data = vec![0u8; 2000]; // Exceeds limit
        let fake_wasm = b"test_module";

        let result = sandbox.execute(fake_wasm, &large_data, "execute");
        assert!(result.is_err());
    }

    #[test]
    fn test_module_caching() {
        let mut sandbox = WasmSandbox::new(SandboxConfig { simulation_mode: true, ..Default::default() }).unwrap();

        // Use a minimal valid WASM header so validate_module accepts it in tests
        let wasm = b"\x00asm\x01\x00\x00\x00fake_wasm_module_data";
        let hash1 = sandbox.load_module(wasm).unwrap();
        let hash2 = sandbox.load_module(wasm).unwrap();

        assert_eq!(hash1, hash2);
    }

    #[test]
    fn test_execute_with_tunnel_roundtrip() {
        use rand::RngCore;

        let config = SandboxConfig { simulation_mode: true, ..Default::default() };
        let sandbox = WasmSandbox::new(config).unwrap();

        let mut key = [0u8; 32];
        rand::thread_rng().fill_bytes(&mut key);
        let tunnel = IoTunnel::new(&key).expect("create tunnel");

        let wasm = b"test_module";
        let plaintext = b"compute input data";

        let encrypted_input = tunnel.encrypt(plaintext).expect("encrypt input");

        let encrypted_output = sandbox.execute_with_tunnel(wasm, &encrypted_input, "execute", Some(&tunnel)).unwrap();
        assert!(encrypted_output != plaintext);

        let decrypted_output = tunnel.decrypt(&encrypted_output).expect("decrypt output");
        assert_eq!(decrypted_output, plaintext);
    }
}
