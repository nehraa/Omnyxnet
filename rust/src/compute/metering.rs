//! Resource metering for WASM execution
//!
//! This module provides resource limiting and monitoring for WASM execution.
//! It tracks CPU cycles, memory usage, and execution time to prevent
//! runaway computations and ensure fair resource allocation.

use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use tracing::warn;

/// Resource limits for WASM execution
#[derive(Debug, Clone)]
pub struct ResourceLimits {
    /// Maximum memory in bytes
    pub max_memory_bytes: u64,
    /// Maximum CPU cycles
    pub max_cpu_cycles: u64,
    /// Maximum execution time in milliseconds
    pub max_execution_time_ms: u64,
    /// Maximum stack size in bytes
    pub max_stack_bytes: u64,
}

impl Default for ResourceLimits {
    fn default() -> Self {
        Self {
            max_memory_bytes: 256 * 1024 * 1024, // 256 MB
            max_cpu_cycles: 1_000_000_000,       // 1 billion cycles
            max_execution_time_ms: 30_000,       // 30 seconds
            max_stack_bytes: 1024 * 1024,        // 1 MB stack
        }
    }
}

/// Current resource usage
#[derive(Debug, Clone, Default)]
pub struct ResourceUsage {
    /// Current memory usage in bytes
    pub memory_bytes: u64,
    /// CPU cycles consumed
    pub cpu_cycles: u64,
    /// Execution time in milliseconds
    pub execution_time_ms: u64,
}

impl ResourceUsage {
    /// Check if usage is within limits
    pub fn is_within_limits(&self, limits: &ResourceLimits) -> bool {
        self.memory_bytes <= limits.max_memory_bytes
            && self.cpu_cycles <= limits.max_cpu_cycles
            && self.execution_time_ms <= limits.max_execution_time_ms
    }

    /// Calculate percentage of limit used
    pub fn limit_percentage(&self, limits: &ResourceLimits) -> ResourcePercentage {
        ResourcePercentage {
            memory: (self.memory_bytes as f64 / limits.max_memory_bytes as f64 * 100.0) as u32,
            cpu_cycles: (self.cpu_cycles as f64 / limits.max_cpu_cycles as f64 * 100.0) as u32,
            time: (self.execution_time_ms as f64 / limits.max_execution_time_ms as f64 * 100.0)
                as u32,
        }
    }
}

/// Percentage of limits used
#[derive(Debug, Clone)]
pub struct ResourcePercentage {
    /// Memory percentage (0-100+)
    pub memory: u32,
    /// CPU cycles percentage (0-100+)
    pub cpu_cycles: u32,
    /// Time percentage (0-100+)
    pub time: u32,
}

/// Metering system for tracking and limiting resource usage
///
/// This struct provides thread-safe tracking of resource consumption
/// and can be used to interrupt execution when limits are exceeded.
pub struct Metering {
    limits: ResourceLimits,
    /// Current memory usage (atomic for thread safety)
    memory_bytes: AtomicU64,
    /// Current CPU cycles (atomic for thread safety)  
    cpu_cycles: AtomicU64,
    /// Start time for execution timing
    start_time: std::time::Instant,
    /// Interrupt flag
    interrupted: Arc<std::sync::atomic::AtomicBool>,
}

impl Metering {
    /// Create a new metering instance with the given limits
    pub fn new(limits: ResourceLimits) -> Self {
        Self {
            limits,
            memory_bytes: AtomicU64::new(0),
            cpu_cycles: AtomicU64::new(0),
            start_time: std::time::Instant::now(),
            interrupted: Arc::new(std::sync::atomic::AtomicBool::new(false)),
        }
    }

    /// Start metering (resets counters)
    pub fn start(&mut self) {
        self.memory_bytes.store(0, Ordering::SeqCst);
        self.cpu_cycles.store(0, Ordering::SeqCst);
        self.start_time = std::time::Instant::now();
        self.interrupted.store(false, Ordering::SeqCst);
    }

    /// Add memory usage
    pub fn add_memory(&self, bytes: u64) -> Result<(), MeteringError> {
        let new_usage = self.memory_bytes.fetch_add(bytes, Ordering::SeqCst) + bytes;

        if new_usage > self.limits.max_memory_bytes {
            warn!(
                "Memory limit exceeded: {} > {}",
                new_usage, self.limits.max_memory_bytes
            );
            self.interrupt();
            return Err(MeteringError::MemoryLimitExceeded {
                used: new_usage,
                limit: self.limits.max_memory_bytes,
            });
        }

        Ok(())
    }

    /// Free memory usage
    pub fn free_memory(&self, bytes: u64) {
        self.memory_bytes.fetch_sub(
            bytes.min(self.memory_bytes.load(Ordering::SeqCst)),
            Ordering::SeqCst,
        );
    }

    /// Add CPU cycles
    pub fn add_cycles(&self, cycles: u64) -> Result<(), MeteringError> {
        let new_cycles = self.cpu_cycles.fetch_add(cycles, Ordering::SeqCst) + cycles;

        if new_cycles > self.limits.max_cpu_cycles {
            warn!(
                "CPU cycle limit exceeded: {} > {}",
                new_cycles, self.limits.max_cpu_cycles
            );
            self.interrupt();
            return Err(MeteringError::CpuLimitExceeded {
                used: new_cycles,
                limit: self.limits.max_cpu_cycles,
            });
        }

        Ok(())
    }

    /// Check execution time limit
    pub fn check_time(&self) -> Result<(), MeteringError> {
        let elapsed = self.start_time.elapsed().as_millis() as u64;

        if elapsed > self.limits.max_execution_time_ms {
            warn!(
                "Time limit exceeded: {}ms > {}ms",
                elapsed, self.limits.max_execution_time_ms
            );
            self.interrupt();
            return Err(MeteringError::TimeLimitExceeded {
                elapsed,
                limit: self.limits.max_execution_time_ms,
            });
        }

        Ok(())
    }

    /// Check all limits
    pub fn check_all(&self) -> Result<(), MeteringError> {
        self.check_time()?;

        // Memory and cycles are checked on increment
        // Just verify we haven't been interrupted
        if self.is_interrupted() {
            return Err(MeteringError::Interrupted);
        }

        Ok(())
    }

    /// Get current resource usage
    pub fn get_usage(&self) -> ResourceUsage {
        ResourceUsage {
            memory_bytes: self.memory_bytes.load(Ordering::SeqCst),
            cpu_cycles: self.cpu_cycles.load(Ordering::SeqCst),
            execution_time_ms: self.start_time.elapsed().as_millis() as u64,
        }
    }

    /// Interrupt execution
    pub fn interrupt(&self) {
        self.interrupted.store(true, Ordering::SeqCst);
    }

    /// Check if interrupted
    pub fn is_interrupted(&self) -> bool {
        self.interrupted.load(Ordering::SeqCst)
    }

    /// Get interrupt handle for async interruption
    pub fn interrupt_handle(&self) -> Arc<std::sync::atomic::AtomicBool> {
        Arc::clone(&self.interrupted)
    }

    /// Get limits
    pub fn limits(&self) -> &ResourceLimits {
        &self.limits
    }
}

/// Errors that can occur during metering
#[derive(Debug, thiserror::Error)]
pub enum MeteringError {
    #[error("Memory limit exceeded: used {used} bytes, limit {limit} bytes")]
    MemoryLimitExceeded { used: u64, limit: u64 },

    #[error("CPU cycle limit exceeded: used {used} cycles, limit {limit} cycles")]
    CpuLimitExceeded { used: u64, limit: u64 },

    #[error("Time limit exceeded: elapsed {elapsed}ms, limit {limit}ms")]
    TimeLimitExceeded { elapsed: u64, limit: u64 },

    #[error("Execution interrupted")]
    Interrupted,
}

/// A metering callback that can be injected into WASM execution
///
/// This is designed to be called periodically during WASM execution
/// to check resource limits.
#[allow(dead_code)]
pub struct MeteringCallback {
    metering: Arc<Metering>,
    check_interval: u64,
    cycles_since_check: AtomicU64,
}

#[allow(dead_code)]
impl MeteringCallback {
    /// Create a new metering callback
    pub fn new(metering: Arc<Metering>, check_interval: u64) -> Self {
        Self {
            metering,
            check_interval,
            cycles_since_check: AtomicU64::new(0),
        }
    }

    /// Called for each WASM instruction
    pub fn on_instruction(&self) -> Result<(), MeteringError> {
        let cycles = self.cycles_since_check.fetch_add(1, Ordering::Relaxed) + 1;

        if cycles >= self.check_interval {
            self.cycles_since_check.store(0, Ordering::Relaxed);
            self.metering.add_cycles(cycles)?;
            self.metering.check_time()?;
        }

        Ok(())
    }

    /// Called on memory allocation
    pub fn on_memory_alloc(&self, bytes: u64) -> Result<(), MeteringError> {
        self.metering.add_memory(bytes)
    }

    /// Called on memory free
    pub fn on_memory_free(&self, bytes: u64) {
        self.metering.free_memory(bytes)
    }
}

/// Estimate CPU cycles for common operations
#[allow(dead_code)]
pub mod cycle_estimates {
    /// Cycles for a simple arithmetic operation
    pub const ARITHMETIC: u64 = 1;

    /// Cycles for a memory load
    pub const MEMORY_LOAD: u64 = 3;

    /// Cycles for a memory store
    pub const MEMORY_STORE: u64 = 3;

    /// Cycles for a function call
    pub const FUNCTION_CALL: u64 = 10;

    /// Cycles for a branch
    pub const BRANCH: u64 = 2;

    /// Cycles for a loop iteration
    pub const LOOP_ITERATION: u64 = 5;

    /// Estimate cycles for processing N bytes
    pub fn for_data_processing(bytes: usize) -> u64 {
        // Estimate: ~10 cycles per byte for typical processing
        (bytes as u64) * 10
    }

    /// Estimate cycles for sorting N elements
    pub fn for_sorting(n: usize) -> u64 {
        // O(n log n) estimate
        let n = n as f64;
        (n * n.log2() * 100.0) as u64
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_metering_creation() {
        let limits = ResourceLimits::default();
        let metering = Metering::new(limits);

        let usage = metering.get_usage();
        assert_eq!(usage.memory_bytes, 0);
        assert_eq!(usage.cpu_cycles, 0);
    }

    #[test]
    fn test_memory_tracking() {
        let limits = ResourceLimits {
            max_memory_bytes: 1000,
            ..Default::default()
        };
        let metering = Metering::new(limits);

        // Add memory within limits
        assert!(metering.add_memory(500).is_ok());
        assert_eq!(metering.get_usage().memory_bytes, 500);

        // Add more memory within limits
        assert!(metering.add_memory(400).is_ok());
        assert_eq!(metering.get_usage().memory_bytes, 900);

        // Exceed limits
        assert!(metering.add_memory(200).is_err());
    }

    #[test]
    fn test_cpu_cycle_tracking() {
        let limits = ResourceLimits {
            max_cpu_cycles: 1000,
            ..Default::default()
        };
        let metering = Metering::new(limits);

        // Add cycles within limits
        assert!(metering.add_cycles(500).is_ok());
        assert_eq!(metering.get_usage().cpu_cycles, 500);

        // Exceed limits
        assert!(metering.add_cycles(600).is_err());
    }

    #[test]
    fn test_interrupt() {
        let metering = Metering::new(ResourceLimits::default());

        assert!(!metering.is_interrupted());

        metering.interrupt();

        assert!(metering.is_interrupted());
        assert!(metering.check_all().is_err());
    }

    #[test]
    fn test_resource_percentage() {
        let usage = ResourceUsage {
            memory_bytes: 128 * 1024 * 1024, // 128 MB
            cpu_cycles: 500_000_000,
            execution_time_ms: 15_000,
        };

        let limits = ResourceLimits::default();
        let percentages = usage.limit_percentage(&limits);

        assert_eq!(percentages.memory, 50);
        assert_eq!(percentages.cpu_cycles, 50);
        assert_eq!(percentages.time, 50);
    }
}
