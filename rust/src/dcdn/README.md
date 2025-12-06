# DCDN (Distributed Content Delivery Network) Module

Implementation of the DCDN system as specified in `dcdn_design_spec.txt`.

## Overview

The DCDN module provides a complete distributed CDN implementation with:
- **QUIC Transport**: Low-latency packet delivery using quinn
- **Reed-Solomon FEC**: Forward error correction for packet recovery
- **P2P Mesh**: Tit-for-tat incentive mechanism for fair bandwidth sharing
- **Ed25519 Verification**: Cryptographic signature verification for content authenticity
- **Lock-free Ring Buffer**: High-performance chunk storage

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   CONTROL PLANE                          │
│  (Configuration, Monitoring, Coordination)               │
└────────────────┬────────────────────────────────────────┘
                 │ Configuration Updates
                 │ Metrics Push
                 ▼
┌─────────────────────────────────────────────────────────┐
│                    DATA PLANE                            │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ QUIC Layer   │─▶│ FEC Engine   │─▶│ Ring Buffer  │ │
│  │ (quinn)      │  │ (reed-solomon)│  │ (lock-free)  │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│         │                  │                  │         │
│         └──────────────────┴──────────────────┘         │
│                          │                               │
│                ┌─────────▼──────────┐                   │
│                │  P2P Engine        │                   │
│                │  (tit-for-tat)     │                   │
│                └────────────────────┘                   │
└─────────────────────────────────────────────────────────┘
                 ▲                    │
                 │ Chunks             │ Chunks
                 │                    ▼
┌────────────────┴─────────────────────────────────────────┐
│                  INTEGRITY PLANE                          │
│  (Cryptographic verification)                             │
│  - Signature Verifier (Ed25519)                          │
│  - Key Manager                                            │
│  - Reputation Tracker                                     │
└───────────────────────────────────────────────────────────┘
```

## Components

### 1. Types (`types.rs`)
Core data structures used throughout the DCDN system:
- `ChunkData`: Chunk metadata and payload
- `ChunkId`, `PeerId`, `FecGroupId`: Unique identifiers
- `Signature`, `PublicKey`: Cryptographic types
- `StorageStats`, `PeerStats`: Statistics tracking

### 2. Configuration (`config.rs`)
TOML-based configuration system:
- `DcdnConfig`: Main configuration structure
- `QuicConfig`: QUIC transport settings
- `StorageConfig`: Ring buffer and TTL settings
- `FecConfig`: Reed-Solomon FEC parameters
- `P2PConfig`: Bandwidth and unchoke settings

### 3. Storage (`storage.rs`)
Lock-free ring buffer for chunk storage:
- Thread-safe concurrent access
- Automatic eviction based on TTL
- Fast lookup with DashMap
- Statistics tracking

### 4. FEC Engine (`fec.rs`)
Reed-Solomon forward error correction:
- Encoding: Generate parity packets
- Decoding: Recover missing packets
- Adaptive block sizing based on network conditions
- Support for various data rates

### 5. Transport (`transport.rs`)
QUIC-based transport layer:
- Connection management
- Stream multiplexing
- Chunk transmission
- Built on quinn for high performance

### 6. P2P Engine (`p2p.rs`)
Peer-to-peer transfer with incentives:
- Tit-for-tat unchoke algorithm
- Bandwidth allocation
- Peer statistics tracking
- Fair resource sharing

### 7. Signature Verifier (`verifier.rs`)
Cryptographic verification:
- Ed25519 signature verification
- Trusted key management
- Batch verification for efficiency
- Revocation support

## Usage

### Basic Setup

```rust
use pangea_ces::dcdn::*;
use std::time::Duration;

// Load configuration
let config = DcdnConfig::from_file("config/dcdn.toml")?;

// Create components
let store = ChunkStore::new(
    config.storage.ring_buffer_size_mb * 1024 * 1024,
    Duration::from_secs(config.storage.chunk_ttl_seconds)
);

let fec_config = FecEngineConfig {
    block_size: config.fec.default_block_size,
    parity_count: config.fec.default_parity_count,
    algorithm: FecAlgorithm::ReedSolomon,
};
let fec_engine = FecEngine::new(fec_config);

let p2p_config = P2PConfig {
    max_upload_mbps: config.p2p.max_upload_mbps,
    max_download_mbps: config.p2p.max_download_mbps,
    unchoke_interval_seconds: config.p2p.unchoke_interval_seconds,
    regular_unchoke_count: config.p2p.regular_unchoke_count,
    optimistic_unchoke_count: config.p2p.optimistic_unchoke_count,
};
let p2p_engine = P2PEngine::new(p2p_config);

let verifier = SignatureVerifier::new();
```

### Storing and Retrieving Chunks

```rust
use bytes::Bytes;

// Create a chunk
let chunk = ChunkData {
    id: ChunkId::new(1),
    sequence: 1,
    timestamp: Instant::now(),
    source_peer: PeerId::new(1),
    signature: Signature::from_bytes([0u8; 64]),
    data: Bytes::from(vec![0u8; 1024]),
    fec_group: Some(FecGroupId::new(1)),
};

// Store chunk
store.insert(chunk)?;

// Retrieve chunk
if let Some(chunk) = store.get(&ChunkId::new(1)) {
    println!("Retrieved chunk: {:?}", chunk.id);
}

// Get statistics
let stats = store.stats();
println!("Stored {} chunks ({} bytes)", stats.chunk_count, stats.size_bytes);
```

### FEC Encoding/Decoding

```rust
// Create data packets
let packets = vec![
    Packet { group_id: FecGroupId::new(1), index: 0, data: Bytes::from(vec![0u8; 100]) },
    Packet { group_id: FecGroupId::new(1), index: 1, data: Bytes::from(vec![1u8; 100]) },
    // ... more packets
];

// Encode to generate parity
let parity = fec_engine.encode(&packets, &fec_config)?;

// Simulate packet loss and recovery
let mut group = FecGroup::new(FecGroupId::new(1), 8, 2);
// ... add received packets to group

if fec_engine.can_recover(&group) {
    let recovered = fec_engine.decode(&group)?;
    println!("Recovered {} missing packets", recovered.len());
}
```

### P2P Bandwidth Management

```rust
// Add peers
for i in 1..=10 {
    p2p_engine.add_peer(PeerId::new(i));
}

// Update statistics
p2p_engine.update_downloaded(PeerId::new(1), 1024 * 1024);
p2p_engine.update_uploaded(PeerId::new(1), 512 * 1024);

// Update unchoke set (run periodically)
p2p_engine.update_unchoke_set().await?;

// Get unchoked peers
let unchoked = p2p_engine.get_unchoked_peers().await;
println!("Unchoked peers: {:?}", unchoked);

// Get bandwidth allocation
let allocations = p2p_engine.get_bandwidth_allocation().await;
for (peer, bandwidth) in allocations {
    println!("Peer {:?}: {} bytes/sec", peer, bandwidth);
}
```

### Signature Verification

```rust
// Add trusted key
verifier.add_trusted_key(
    PeerId::new(1),
    PublicKey::from_bytes([42u8; 32])
);

// Verify chunk
if verifier.verify(&chunk)? {
    println!("Chunk verified successfully");
} else {
    println!("Chunk verification failed");
}

// Batch verification
let chunks = vec![chunk1, chunk2, chunk3];
let results = verifier.verify_batch(&chunks)?;
for (i, verified) in results.iter().enumerate() {
    println!("Chunk {}: {}", i, if *verified { "✓" } else { "✗" });
}

// Get metrics
let (total, success, failed, batch) = verifier.get_metrics();
println!("Verified {} chunks ({} success, {} failed, {} batches)",
         total, success, failed, batch);
```

## Configuration

See `config/dcdn.toml` for a complete example configuration file.

Key configuration parameters:

- **Node Role**: `edge`, `relay`, or `origin`
- **QUIC Settings**: Connection limits, congestion algorithm, timeouts
- **Storage**: Buffer size, chunk TTL, memory limits
- **FEC**: Block size, parity count, adaptive mode
- **P2P**: Upload/download limits, unchoke intervals and counts
- **Crypto**: Signature algorithm, key rotation period

## Testing

Run the DCDN tests:

```bash
cargo test --test test_dcdn
```

Run specific test:

```bash
cargo test --test test_dcdn test_chunk_store_operations
```

## Performance Considerations

### Memory Usage
- Ring buffer size: `ring_buffer_size_mb` MB
- Per-chunk overhead: ~200 bytes
- Index overhead: ~100 bytes per chunk
- Total memory ≈ buffer size + (chunk_count × 300 bytes)

### Throughput
- QUIC transport: Limited by network bandwidth
- FEC encoding: ~500 MB/s (depends on CPU)
- FEC decoding: ~300 MB/s (depends on CPU and loss rate)
- Storage: >1 GB/s (lock-free, in-memory)

### Latency
- Chunk lookup: O(1) - constant time
- FEC encoding: O(n) - linear in block size
- FEC decoding: O(n²) - depends on missing packets
- Signature verification: ~0.1 ms per chunk

## Integration with Pangea Net

The DCDN module integrates with existing Pangea Net infrastructure:

- **QUIC Transport**: Uses existing `quinn` setup from `network.rs`
- **libp2p DHT**: Can use `dht.rs` for peer discovery
- **Cap'n Proto RPC**: Compatible with existing RPC system
- **Metrics**: Uses existing `metrics.rs` framework
- **Storage**: Complements `cache.rs` and `storage.rs`

## Future Enhancements

As noted in `dcdn_design_spec.txt`:

1. **Control Plane**: gRPC server for configuration and monitoring
2. **Policy Engine**: Adaptive FEC parameter tuning
3. **Metrics Collection**: Prometheus-compatible metrics
4. **WAN Deployment**: Cross-datacenter optimization
5. **Video Streaming**: Integration with existing streaming module

## References

- Design Specification: `/dcdn_design_spec.txt`
- Rust Network Module: `src/network.rs`
- Streaming Module: `src/streaming.rs`
- CES Pipeline: `src/ces.rs`
