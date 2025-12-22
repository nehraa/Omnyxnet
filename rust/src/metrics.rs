/// Phase 1: Performance Metrics and Monitoring
///
/// This module provides latency measurement and throughput tracking
/// to validate Phase 1 success metrics:
/// - One-way audio latency under 100ms
/// - Real-time stream data throughput
use std::time::{Duration, Instant};
use std::collections::VecDeque;
use std::sync::{Arc, RwLock};
use serde::{Serialize, Deserialize};
use tracing::{info, warn};

/// Phase 1 success metric: maximum acceptable latency in milliseconds
const PHASE1_LATENCY_TARGET_MS: f64 = 100.0;

/// Latency measurement for a single operation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LatencyMeasurement {
    pub operation: String,
    pub latency_ms: f64,
    pub timestamp: u64,
}

/// Throughput measurement for streaming data
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ThroughputMeasurement {
    pub bytes_transferred: u64,
    pub duration_ms: u64,
    pub throughput_mbps: f64,
}

/// Performance metrics tracker
pub struct MetricsTracker {
    latencies: Arc<RwLock<VecDeque<LatencyMeasurement>>>,
    max_samples: usize,
}

impl MetricsTracker {
    /// Create a new metrics tracker
    pub fn new(max_samples: usize) -> Self {
        Self {
            latencies: Arc::new(RwLock::new(VecDeque::with_capacity(max_samples))),
            max_samples,
        }
    }

    /// Record a latency measurement
    pub fn record_latency(&self, operation: String, latency: Duration) {
        let measurement = LatencyMeasurement {
            operation: operation.clone(),
            latency_ms: latency.as_secs_f64() * 1000.0,
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs(),
        };

        let mut latencies = match self.latencies.write() {
            Ok(guard) => guard,
            Err(poisoned) => {
                // If the lock is poisoned we recover the inner value and log once;
                // metrics degradation should not take the whole process down.
                eprintln!("metrics: RwLock poisoned in record_latency, recovering");
                poisoned.into_inner()
            }
        };
        if latencies.len() >= self.max_samples {
            latencies.pop_front();
        }
        latencies.push_back(measurement.clone());

        // Log if latency exceeds Phase 1 target
        if measurement.latency_ms > PHASE1_LATENCY_TARGET_MS {
            warn!("⚠️  High latency detected: {} took {:.2}ms (target: <{}ms)",
                  operation, measurement.latency_ms, PHASE1_LATENCY_TARGET_MS);
        }
    }

    /// Get average latency for an operation
    pub fn average_latency(&self, operation: &str) -> Option<f64> {
        let latencies = match self.latencies.read() {
            Ok(guard) => guard,
            Err(poisoned) => {
                eprintln!("metrics: RwLock poisoned in average_latency, recovering");
                poisoned.into_inner()
            }
        };
        let matching: Vec<f64> = latencies
            .iter()
            .filter(|m| m.operation == operation)
            .map(|m| m.latency_ms)
            .collect();

        if matching.is_empty() {
            None
        } else {
            Some(matching.iter().sum::<f64>() / matching.len() as f64)
        }
    }

    /// Get percentile latency (p50, p95, p99)
    pub fn percentile_latency(&self, operation: &str, percentile: f64) -> Option<f64> {
        let latencies = match self.latencies.read() {
            Ok(guard) => guard,
            Err(poisoned) => {
                eprintln!("metrics: RwLock poisoned in percentile_latency, recovering");
                poisoned.into_inner()
            }
        };
        let mut matching: Vec<f64> = latencies
            .iter()
            .filter(|m| m.operation == operation)
            .map(|m| m.latency_ms)
            .collect();

        if matching.is_empty() {
            return None;
        }

        matching.sort_by(|a, b| a.total_cmp(b));  // Use total_cmp for NaN-safe comparison
        let index = ((matching.len() - 1) as f64 * percentile) as usize;
        Some(matching[index])
    }

    /// Get all measurements for an operation
    pub fn get_measurements(&self, operation: &str) -> Vec<LatencyMeasurement> {
        let latencies = match self.latencies.read() {
            Ok(guard) => guard,
            Err(poisoned) => {
                eprintln!("metrics: RwLock poisoned in percentiles, recovering");
                poisoned.into_inner()
            }
        };
        latencies
            .iter()
            .filter(|m| m.operation == operation)
            .cloned()
            .collect()
    }

    /// Generate a performance report
    pub fn generate_report(&self, operation: &str) -> Option<PerformanceReport> {
        let avg = self.average_latency(operation)?;
        let p50 = self.percentile_latency(operation, 0.5)?;
        let p95 = self.percentile_latency(operation, 0.95)?;
        let p99 = self.percentile_latency(operation, 0.99)?;

        let measurements = self.get_measurements(operation);
        let min = measurements.iter().map(|m| m.latency_ms).min_by(|a, b| a.total_cmp(b))?;  // NaN-safe
        let max = measurements.iter().map(|m| m.latency_ms).max_by(|a, b| a.total_cmp(b))?;  // NaN-safe

        Some(PerformanceReport {
            operation: operation.to_string(),
            sample_count: measurements.len(),
            avg_latency_ms: avg,
            min_latency_ms: min,
            max_latency_ms: max,
            p50_latency_ms: p50,
            p95_latency_ms: p95,
            p99_latency_ms: p99,
            meets_phase1_target: p95 < PHASE1_LATENCY_TARGET_MS,  // Phase 1: 95th percentile < 100ms
        })
    }
}

/// Performance report for Phase 1 validation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformanceReport {
    pub operation: String,
    pub sample_count: usize,
    pub avg_latency_ms: f64,
    pub min_latency_ms: f64,
    pub max_latency_ms: f64,
    pub p50_latency_ms: f64,
    pub p95_latency_ms: f64,
    pub p99_latency_ms: f64,
    pub meets_phase1_target: bool,
}

impl PerformanceReport {
    /// Print a formatted report
    pub fn print(&self) {
        info!("📊 Performance Report: {}", self.operation);
        info!("   Samples: {}", self.sample_count);
        info!("   Average: {:.2}ms", self.avg_latency_ms);
        info!("   Min/Max: {:.2}ms / {:.2}ms", self.min_latency_ms, self.max_latency_ms);
        info!("   P50/P95/P99: {:.2}ms / {:.2}ms / {:.2}ms", 
              self.p50_latency_ms, self.p95_latency_ms, self.p99_latency_ms);
        
        if self.meets_phase1_target {
            info!("   ✅ Meets Phase 1 target (<100ms at P95)");
        } else {
            warn!("   ❌ Does NOT meet Phase 1 target (P95: {:.2}ms > 100ms)", self.p95_latency_ms);
        }
    }
}

/// Latency timer for measuring operation duration
pub struct LatencyTimer {
    operation: String,
    start: Instant,
    tracker: Arc<MetricsTracker>,
}

impl LatencyTimer {
    /// Start a new latency timer
    pub fn start(operation: String, tracker: Arc<MetricsTracker>) -> Self {
        Self {
            operation,
            start: Instant::now(),
            tracker,
        }
    }

    /// Stop the timer and record the measurement
    pub fn stop(self) {
        let elapsed = self.start.elapsed();
        self.tracker.record_latency(self.operation, elapsed);
    }
}

/// Calculate throughput in Mbps
pub fn calculate_throughput(bytes: u64, duration: Duration) -> f64 {
    let bits = bytes * 8;
    let seconds = duration.as_secs_f64();
    if seconds > 0.0 {
        (bits as f64 / seconds) / 1_000_000.0  // Convert to Mbps
    } else {
        0.0
    }
}

/// Throughput tracker for streaming operations
pub struct ThroughputTracker {
    start: Instant,
    bytes_transferred: u64,
}

impl Default for ThroughputTracker {
    fn default() -> Self {
        Self {
            start: Instant::now(),
            bytes_transferred: 0,
        }
    }
}

impl ThroughputTracker {
    /// Create a new throughput tracker
    pub fn new() -> Self {
        Self::default()
    }

    /// Record bytes transferred
    pub fn record_bytes(&mut self, bytes: u64) {
        self.bytes_transferred += bytes;
    }

    /// Get current throughput measurement
    pub fn measure(&self) -> ThroughputMeasurement {
        let duration = self.start.elapsed();
        let throughput_mbps = calculate_throughput(self.bytes_transferred, duration);

        ThroughputMeasurement {
            bytes_transferred: self.bytes_transferred,
            duration_ms: duration.as_millis() as u64,
            throughput_mbps,
        }
    }

    /// Reset the tracker
    pub fn reset(&mut self) {
        self.start = Instant::now();
        self.bytes_transferred = 0;
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::thread;

    #[test]
    fn test_latency_recording() {
        let tracker = MetricsTracker::new(100);
        
        tracker.record_latency("test_op".to_string(), Duration::from_millis(50));
        tracker.record_latency("test_op".to_string(), Duration::from_millis(75));
        tracker.record_latency("test_op".to_string(), Duration::from_millis(100));

        let avg = tracker.average_latency("test_op").unwrap();
        assert!((avg - 75.0).abs() < 1.0);
    }

    #[test]
    fn test_percentile_calculation() {
        let tracker = MetricsTracker::new(100);
        
        // Add 100 measurements from 1ms to 100ms
        for i in 1..=100 {
            tracker.record_latency("test_op".to_string(), Duration::from_millis(i));
        }

        let p50 = tracker.percentile_latency("test_op", 0.5).unwrap();
        let p95 = tracker.percentile_latency("test_op", 0.95).unwrap();
        let p99 = tracker.percentile_latency("test_op", 0.99).unwrap();

        assert!((p50 - 50.0).abs() < 5.0);
        assert!((p95 - 95.0).abs() < 5.0);
        assert!((p99 - 99.0).abs() < 5.0);
    }

    #[test]
    fn test_latency_timer() {
        let tracker = Arc::new(MetricsTracker::new(100));
        
        {
            let timer = LatencyTimer::start("sleep_test".to_string(), tracker.clone());
            thread::sleep(Duration::from_millis(50));
            timer.stop();
        }

        let avg = tracker.average_latency("sleep_test").unwrap();
        assert!(avg >= 50.0 && avg < 100.0);
    }

    #[test]
    fn test_throughput_calculation() {
        let throughput = calculate_throughput(1_000_000, Duration::from_secs(1));
        assert_eq!(throughput, 8.0);  // 1MB/s = 8 Mbps
    }

    #[test]
    fn test_throughput_tracker() {
        let mut tracker = ThroughputTracker::new();
        
        tracker.record_bytes(1_000_000);
        thread::sleep(Duration::from_millis(100));
        
        let measurement = tracker.measure();
        assert!(measurement.throughput_mbps > 70.0);  // Should be ~80 Mbps
    }

    #[test]
    fn test_performance_report() {
        let tracker = MetricsTracker::new(100);
        
        // Add measurements that meet Phase 1 target
        for _ in 0..50 {
            tracker.record_latency("audio_stream".to_string(), Duration::from_millis(50));
        }

        let report = tracker.generate_report("audio_stream").unwrap();
        assert!(report.meets_phase1_target);
        assert!(report.p95_latency_ms < 100.0);
    }
}
