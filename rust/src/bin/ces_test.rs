use anyhow::Result;
use std::env;
use std::fs;
use std::path::Path;
use std::time::Instant;

use pangea_ces::{
    ces::CesPipeline,
    types::{CesConfig, CompressionAlgorithm},
};

/// CES Test Binary for streaming validation
fn main() -> Result<()> {
    let args: Vec<String> = env::args().collect();

    if args.len() < 2 {
        eprintln!("Usage: {} <input_file>", args[0]);
        eprintln!("       {} --ces-test <input_file>", args[0]);
        std::process::exit(1);
    }

    let input_file = if args.len() > 2 && args[1] == "--ces-test" {
        &args[2]
    } else {
        &args[1]
    };

    // Read input file
    let input_data = fs::read(input_file)?;
    println!("📂 Input file: {} ({} bytes)", input_file, input_data.len());

    // Configure CES pipeline for Phase 1 testing
    let config = CesConfig {
        compression_algorithm: CompressionAlgorithm::Brotli, // Phase 1 feature
        compression_level: 6,
        shard_count: 4,
        parity_count: 2,
        chunk_size: std::cmp::min(input_data.len() / 4, 64 * 1024), // Max 64KB chunks
    };

    println!("🔧 CES Config:");
    println!("  Algorithm: {:?}", config.compression_algorithm);
    println!("  Level: {}", config.compression_level);
    println!(
        "  Shards: {} data + {} parity",
        config.shard_count, config.parity_count
    );
    println!("  Chunk size: {} bytes", config.chunk_size);

    // Process through CES pipeline
    let start_time = Instant::now();
    let pipeline = CesPipeline::new(config);
    let result = pipeline.process(&input_data)?;
    let processing_time = start_time.elapsed();

    // Calculate results
    let total_compressed_size: usize = result.iter().map(|shard| shard.len()).sum();
    let compression_ratio = input_data.len() as f64 / total_compressed_size as f64;
    let latency_ms = processing_time.as_millis() as f64;

    println!("🚀 CES Processing Results:");
    println!("  Original size: {} bytes", input_data.len());
    println!("  Compressed size: {} bytes", total_compressed_size);
    println!("  Compression ratio: {:.2}x", compression_ratio);
    println!("  Processing latency: {:.2}ms", latency_ms);
    println!(
        "  Throughput: {:.2} MB/s",
        (input_data.len() as f64) / (processing_time.as_secs_f64() * 1024.0 * 1024.0)
    );
    println!("  Shards created: {}", result.len());

    // Phase 1 validation
    let phase1_latency_ok = latency_ms < 100.0;
    let phase1_compression_ok = compression_ratio > 1.0;

    println!("✅ Phase 1 Validation:");
    println!(
        "  Latency target (<100ms): {}",
        if phase1_latency_ok {
            "✅ PASS"
        } else {
            "❌ FAIL"
        }
    );
    println!(
        "  Compression working: {}",
        if phase1_compression_ok {
            "✅ PASS"
        } else {
            "❌ FAIL"
        }
    );

    // Output for parsing by test scripts
    if args.len() > 1 && args[1] == "--ces-test" {
        println!(
            "CES_TEST_RESULT:compressed_size={},latency_ms={:.2},ratio={:.2}",
            total_compressed_size, latency_ms, compression_ratio
        );
    }

    Ok(())
}
