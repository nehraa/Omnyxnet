/// Phase 1 Feature Demonstration - Run with: cargo run --example phase1_demo --release
use pangea_ces::{
    AudioConfig, AudioDecoder, AudioEncoder, CesConfig, CesPipeline, CompressionAlgorithm,
    LatencyTimer, MetricsTracker,
};
use std::sync::Arc;

fn main() -> anyhow::Result<()> {
    println!("🚀 Phase 1: Brotli, Opus, Metrics Demo\n");
    let metrics = Arc::new(MetricsTracker::new(1000));

    // 1. Compression demo
    let data = "Phase 1 test ".repeat(100).into_bytes();
    for alg in [CompressionAlgorithm::Zstd, CompressionAlgorithm::Brotli] {
        let timer = LatencyTimer::start(format!("compress_{:?}", alg), metrics.clone());
        let cfg = CesConfig {
            compression_level: 3,
            compression_algorithm: alg,
            shard_count: 8,
            parity_count: 4,
            chunk_size: 1024 * 1024,
        };
        let _shards = CesPipeline::new(cfg).process(&data)?;
        timer.stop();
    }
    println!("✅ Compression: Zstd & Brotli tested\n");

    // 2. Opus demo
    let cfg = AudioConfig::low_latency();
    let mut enc = AudioEncoder::new(cfg.clone())?;
    let mut dec = AudioDecoder::new(cfg.clone())?;
    // Generate test audio data (simple waveform for demonstration)
    let pcm: Vec<i16> = (0..cfg.frame_size())
        .map(|i| ((i as f32).sin() * 32767.0) as i16)
        .collect();
    let timer = LatencyTimer::start("opus_encode".to_string(), metrics.clone());
    let encoded = enc.encode(&pcm)?;
    timer.stop();
    let _decoded = dec.decode(&encoded)?;
    println!(
        "✅ Opus: {}ms latency\n",
        metrics.average_latency("opus_encode").unwrap_or(0.0)
    );

    // 3. Metrics report
    if let Some(r) = metrics.generate_report("opus_encode") {
        println!(
            "📊 Metrics: P95={:.2}ms {}",
            r.p95_latency_ms,
            if r.meets_phase1_target { "✅" } else { "❌" }
        );
    }
    Ok(())
}
