use prometheus::{
    Counter, Encoder, Gauge, Histogram, HistogramOpts, IntCounter, Opts, Registry, TextEncoder,
};
use std::sync::Arc;

pub struct Metrics {
    pub registry: Registry,
    pub requests_total: IntCounter,
    pub processing_duration: Histogram,
    pub active_tasks: Gauge,
    pub data_bytes_processed: Counter,
    pub errors_total: IntCounter,
}

impl Metrics {
    pub fn new() -> Arc<Self> {
        let registry = Registry::new();

        let requests_total = IntCounter::with_opts(
            Opts::new("http_requests_total", "Total number of HTTP requests")
                .namespace("pangea")
                .subsystem("rust_compute"),
        )
        .unwrap();

        let processing_duration = Histogram::with_opts(
            HistogramOpts::new(
                "processing_duration_seconds",
                "Time spent processing data",
            )
            .namespace("pangea")
            .subsystem("rust_compute"),
        )
        .unwrap();

        let active_tasks = Gauge::with_opts(
            Opts::new("active_tasks", "Number of active processing tasks")
                .namespace("pangea")
                .subsystem("rust_compute"),
        )
        .unwrap();

        let data_bytes_processed = Counter::with_opts(
            Opts::new("data_bytes_processed_total", "Total bytes of data processed")
                .namespace("pangea")
                .subsystem("rust_compute"),
        )
        .unwrap();

        let errors_total = IntCounter::with_opts(
            Opts::new("errors_total", "Total number of errors")
                .namespace("pangea")
                .subsystem("rust_compute"),
        )
        .unwrap();

        registry.register(Box::new(requests_total.clone())).unwrap();
        registry
            .register(Box::new(processing_duration.clone()))
            .unwrap();
        registry.register(Box::new(active_tasks.clone())).unwrap();
        registry
            .register(Box::new(data_bytes_processed.clone()))
            .unwrap();
        registry.register(Box::new(errors_total.clone())).unwrap();

        Arc::new(Self {
            registry,
            requests_total,
            processing_duration,
            active_tasks,
            data_bytes_processed,
            errors_total,
        })
    }

    pub fn encode(&self) -> Result<String, std::fmt::Error> {
        let encoder = TextEncoder::new();
        let mut buffer = Vec::new();
        let metric_families = self.registry.gather();
        encoder.encode(&metric_families, &mut buffer).unwrap();
        String::from_utf8(buffer).map_err(|_| std::fmt::Error)
    }
}
