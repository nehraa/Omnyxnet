use anyhow::Result;
use std::env;
use std::fs;
use std::time::Instant;

use pangea_ces::{
    ces::CesPipeline,
    types::{CesConfig, CompressionAlgorithm},
};

/// CES Test Binary - ZSTD Algorithm Only
fn main() -> Result<()> {
    let args: Vec<String> = env::args().collect();

    if args.len() < 2 {
        eprintln!("Usage: {} <input_file>", args[0]);
        std::process::exit(1);
    }

    let input_file = &args[1];

    // Read input file
    let input_data = fs::read(input_file)?;
    println!("📂 Input file: {} ({} bytes)", input_file, input_data.len());

    // Configure CES pipeline for ZSTD ONLY
    // Optimize for large video files (>1MB)
    let is_large_file = input_data.len() > 1_000_000;
    let optimal_chunk_size = if is_large_file {
        // For large files like HD video, use bigger chunks for better compression
        std::cmp::min(input_data.len() / 8, 256 * 1024) // Up to 256KB chunks
    } else {
        std::cmp::min(input_data.len() / 4, 64 * 1024) // Original 64KB chunks
    };

    let config = CesConfig {
        compression_algorithm: CompressionAlgorithm::Zstd, // ZSTD algorithm test
        compression_level: if is_large_file { 4 } else { 6 }, // Faster compression for large files
        shard_count: if is_large_file { 8 } else { 4 },    // More shards for large files
        parity_count: 2,
        chunk_size: optimal_chunk_size,
    };

    println!("🔧 CES Config - ZSTD ALGORITHM:");
    println!("  Algorithm: {:?}", config.compression_algorithm);
    println!(
        "  Level: {} {}",
        config.compression_level,
        if is_large_file {
            "(optimized for large files)"
        } else {
            ""
        }
    );
    println!(
        "  Shards: {} data + {} parity {}",
        config.shard_count,
        config.parity_count,
        if is_large_file {
            "(scaled for HD video)"
        } else {
            ""
        }
    );
    println!(
        "  Chunk size: {} bytes ({:.1}KB)",
        config.chunk_size,
        config.chunk_size as f64 / 1024.0
    );
    println!(
        "  File type: {}",
        if is_large_file {
            "Large video file (>1MB)"
        } else {
            "Standard test file"
        }
    );

    // Process through CES pipeline
    let start_time = Instant::now();
    let pipeline = CesPipeline::new(config);
    let result = pipeline.process(&input_data)?;
    let processing_time = start_time.elapsed();

    // Calculate results
    let total_compressed_size: usize = result.iter().map(|shard| shard.len()).sum();
    let compression_ratio = input_data.len() as f64 / total_compressed_size as f64;
    let latency_ms = processing_time.as_millis() as f64;

    println!("🚀 ZSTD CES Processing Results:");
    println!("  Original size: {} bytes", input_data.len());
    println!("  Compressed size: {} bytes", total_compressed_size);
    println!("  Compression ratio: {:.2}x", compression_ratio);
    println!("  Processing latency: {:.2}ms", latency_ms);
    println!(
        "  Throughput: {:.2} MB/s",
        (input_data.len() as f64) / (processing_time.as_secs_f64() * 1024.0 * 1024.0)
    );
    println!("  Shards created: {}", result.len());

    // Algorithm validation
    let compression_ok = compression_ratio > 1.0;
    let latency_ok = latency_ms < 100.0;

    println!("✅ ZSTD Algorithm Validation:");
    println!(
        "  Latency target (<100ms): {}",
        if latency_ok { "✅ PASS" } else { "❌ FAIL" }
    );
    println!(
        "  Compression effective: {}",
        if compression_ok {
            "✅ PASS"
        } else {
            "❌ NEUTRAL"
        }
    );

    Ok(())
}
