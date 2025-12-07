# DCDN Setup Guide

## Overview

The DCDN (Distributed Content Delivery Network) module provides a complete distributed CDN implementation built in Rust for maximum performance. It includes QUIC transport, Reed-Solomon FEC, P2P mesh networking, and Ed25519 signature verification.

## Architecture

The DCDN system is primarily implemented in Rust with Python CLI wrappers for convenience:

```
Python CLI ─→ subprocess ─→ Rust DCDN Implementation
                                 │
                                 ├─→ QUIC Transport (quinn)
                                 ├─→ FEC Engine (reed-solomon)
                                 ├─→ P2P Engine (tit-for-tat)
                                 ├─→ ChunkStore (lock-free ring buffer)
                                 └─→ Signature Verifier (Ed25519)
```

## System Requirements

### Required Dependencies

The DCDN module requires:

1. **Rust**: For the core DCDN implementation
   ```bash
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
   ```

2. **System Libraries**: Installed via setup.sh
   - OpenSSL (`libssl-dev` on Linux)
   - pkg-config
   - build-essential/gcc

### Rust Crate Dependencies

These are automatically installed by Cargo:
- `quinn`: QUIC transport
- `reed-solomon-erasure`: FEC implementation
- `ed25519-dalek`: Signature verification
- `dashmap`: Concurrent hash map
- `parking_lot`: High-performance locks
- `tokio`: Async runtime

## Installation

### Via Setup Script (Recommended)

The setup script installs all dependencies:

```bash
./scripts/setup.sh
# Select option 1: Full Installation
```

This will:
1. Install system dependencies (including Rust)
2. Build the Go components
3. Build the Rust components (including DCDN)
4. Set up Python environment

### Manual Installation

If you prefer manual installation:

```bash
# 1. Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

# 2. Install system dependencies
# Linux (Debian/Ubuntu):
sudo apt-get install build-essential pkg-config libssl-dev

# macOS:
brew install openssl pkg-config

# 3. Build DCDN module
cd rust
cargo build --release
```

## Running DCDN

### Method 1: Via Setup Script

```bash
./scripts/setup.sh
# Select option 20: DCDN Demo (Distributed CDN System)
```

### Method 2: Via Python CLI

The Python CLI now includes DCDN commands:

```bash
cd python
source .venv/bin/activate

# Run interactive demo
python main.py dcdn demo

# Show DCDN information
python main.py dcdn info

# Run DCDN tests
python main.py dcdn test
```

### Method 3: Direct Rust Execution

```bash
cd rust

# Run the DCDN demo
cargo run --example dcdn_demo

# Run DCDN tests
cargo test --test test_dcdn

# Run specific test
cargo test --test test_dcdn test_chunk_store_operations
```

## DCDN Demo

The interactive DCDN demo demonstrates:

1. **ChunkStore**: Lock-free ring buffer for high-performance chunk storage
2. **FEC Engine**: Reed-Solomon encoding and decoding with packet loss simulation
3. **P2P Engine**: Tit-for-tat bandwidth allocation algorithm
4. **Signature Verifier**: Ed25519 cryptographic verification
5. **Complete Lifecycle**: End-to-end chunk processing

### Demo Output

The demo will show:
- Chunk store operations (insert, retrieve, evict)
- FEC encoding/decoding with recovery
- P2P unchoke set updates
- Signature verification results
- Performance metrics

## Configuration

The DCDN system is configured via `rust/config/dcdn.toml`:

```toml
[node]
role = "edge"  # edge, relay, or origin

[quic]
max_connections = 1000
max_streams_per_connection = 100
congestion_algorithm = "bbr"

[storage]
ring_buffer_size_mb = 1024
chunk_ttl_seconds = 3600

[fec]
default_block_size = 8
default_parity_count = 2
adaptive_mode = true

[p2p]
max_upload_mbps = 100
max_download_mbps = 1000
regular_unchoke_count = 4
optimistic_unchoke_count = 1

[crypto]
signature_algorithm = "ed25519"
```

## Integration with Pangea Net

The DCDN integrates with the existing Pangea Net infrastructure:

### Frontend Integration

The DCDN is accessible through:

1. **Setup Script Menu**: Option 20 provides easy access
2. **Python CLI**: `python main.py dcdn ...` commands
3. **Direct Rust**: For maximum performance

### Backend Integration

The DCDN uses:
- **QUIC Transport**: Shared with existing network.rs
- **libp2p DHT**: For peer discovery (via dht.rs)
- **Cap'n Proto RPC**: Compatible with existing RPC system
- **Metrics**: Integrates with metrics.rs framework

## Python CLI Commands

### dcdn demo

Runs the interactive DCDN demonstration:

```bash
python main.py dcdn demo
```

This executes the Rust `dcdn_demo` example, showing:
- ChunkStore operations
- FEC encoding/decoding
- P2P bandwidth management
- Signature verification

### dcdn info

Shows DCDN system information:

```bash
python main.py dcdn info
```

Displays:
- Component overview
- Performance characteristics
- Configuration file location
- Usage examples

### dcdn test

Runs the complete DCDN test suite:

```bash
python main.py dcdn test
```

Executes all Rust DCDN tests and reports results.

## Performance Characteristics

### Throughput
- **Chunk lookup**: O(1) - constant time
- **FEC encoding**: ~500 MB/s
- **FEC decoding**: ~300 MB/s
- **Storage**: >1 GB/s (lock-free, in-memory)

### Latency
- **Chunk insertion**: <1 µs (microsecond)
- **Chunk retrieval**: <1 µs
- **Signature verification**: ~100 µs per chunk
- **FEC encoding**: O(n) - linear in block size
- **FEC decoding**: O(n²) - depends on missing packets

### Memory Usage
- Ring buffer size: Configurable (default 1024 MB)
- Per-chunk overhead: ~200 bytes
- Index overhead: ~100 bytes per chunk
- Total: buffer_size + (chunk_count × 300 bytes)

## Troubleshooting

### Cargo Not Found

If you get "cargo: command not found":

```bash
# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

# Verify installation
cargo --version
```

### Build Failures

If the Rust build fails:

1. Ensure system dependencies are installed:
   ```bash
   # Linux
   sudo apt-get install build-essential pkg-config libssl-dev
   
   # macOS
   brew install openssl pkg-config
   export PKG_CONFIG_PATH="/usr/local/opt/openssl/lib/pkgconfig"
   ```

2. Clean and rebuild:
   ```bash
   cd rust
   cargo clean
   cargo build --release
   ```

### Module Not Found

If Python can't find the DCDN commands:

```bash
cd python
source .venv/bin/activate
pip install -r requirements.txt
```

## Testing

### Run All DCDN Tests

```bash
cd rust
cargo test --test test_dcdn
```

### Run Specific Test Category

```bash
# Chunk store tests
cargo test --test test_dcdn test_chunk_store

# FEC engine tests
cargo test --test test_dcdn test_fec

# P2P engine tests
cargo test --test test_dcdn test_p2p

# Signature verifier tests
cargo test --test test_dcdn test_verifier
```

### Run with Output

```bash
cargo test --test test_dcdn -- --nocapture
```

## Documentation

For more detailed information:

- **Design Specification**: [dcdn_design_spec.txt](dcdn_design_spec.txt)
- **Implementation Details**: [rust/src/dcdn/README.md](rust/src/dcdn/README.md)
- **Configuration Reference**: [rust/config/dcdn.toml](rust/config/dcdn.toml)
- **Example Code**: [rust/examples/dcdn_demo.rs](rust/examples/dcdn_demo.rs)

## Related Components

The DCDN integrates with:
- **Rust Network Module**: [rust/src/network.rs](rust/src/network.rs)
- **Streaming Module**: [rust/src/streaming.rs](rust/src/streaming.rs)
- **CES Pipeline**: [rust/src/ces.rs](rust/src/ces.rs)
- **Python Client**: [python/src/client/go_client.py](python/src/client/go_client.py)
