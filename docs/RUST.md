# Pangea Rust Node - Complete Implementation Guide

## Overview

The Rust implementation of Pangea Net provides a high-performance, production-ready node with advanced features including QUIC transport, libp2p DHT, adaptive CES pipeline, and optional eBPF firewall. This implementation demonstrates extreme concurrency, zero-copy data handling, and adaptive performance optimization.

## System Architecture

Pangea Net is a high-performance, decentralized storage and compute fabric. This specification details the Rust-Native Implementation, focusing on extreme concurrency, zero-copy data handling, and kernel-bypass networking.

    Core Philosophy: Eliminate bottlenecks. Use QUIC to fix TCP head-of-line blocking, eBPF to fix firewall CPU load, and io_uring to fix disk I/O blocking.

    Language Stack:

        Core: Rust (Systems Programming)

        Control: Python (AI/Logic via PyO3 bindings)

        Kernel: C/eBPF (Packet Filtering)

2. Architectural Stack

Layer	Component	Technology Stack	Role
Kernel	The Guard	aya (eBPF/XDP)	Drops malicious packets at the NIC driver level.
Transport	Multiplexer	quinn (QUIC/UDP)	Manages thousands of concurrent streams over one UDP port.
Compute	CES Pipeline	zstd, chacha20, reed-solomon	Compresses, Encrypts, and Shards data streams.
Storage	Async IO	tokio-uring, O_DIRECT	Writes data to NVMe without OS page cache overhead.
Logic	Middleman	libp2p-kad (DHT)	Decentralized routing and secret distribution.

3. The "Smart" CES Pipeline (Computation)

The CES (Compression, Encryption, Sharding) pipeline is CPU-bound. We must ensure it does not block the async network runtime.

3.1 Dynamic Configuration (The "Lightweight Model")

Before processing, the system runs a heuristic to determine optimal parameters based on current conditions.

    Input: Network Bandwidth (B), CPU Load (C), File Size (S).

    Heuristic Function:
    ShardSize=min(MAX_MTU,BS×C​)

        Logic: If CPU is high (C≈1) but Bandwidth is low (B≪1), use larger shards to reduce protocol overhead. If Bandwidth is huge, use smaller shards for finer-grained parallelism.

    Implementation: Simple Rust function returning a CesConfig struct.

3.2 The Pipeline Flow (Zero-Copy)

Data flows through this pipeline using Buffer Recycling to avoid allocation.

    Stream Compression (zstd):

        Read chunk from QUIC stream into a pre-allocated buffer BufA.

        Compress BufA → BufB. Use zstd-safe for raw C bindings (faster) or zstd crate.

    In-Place Encryption (chacha20poly1305):

        Encrypt BufB in place. The ciphertext overwrites the compressed data.

        Keying: Use a per-file symmetric key derived from the Middleman's secret.

        Nonce: Use XChaCha20 (192-bit nonce) to safely generate random nonces without collision risk.

    Sharding (reed-solomon-erasure):

        Take BufB (Encrypted).

        Use SIMD-accelerated Reed-Solomon to generate K parity shards.

        Output: A vector of references Vec<&[u8]> pointing to the shards, ready for network transmission.

4. Upload Protocol (The Push)

This process is One-to-Many. The Origin node pushes shards to multiple Target nodes simultaneously.

Phase 1: Route Discovery (The Middleman)

    Request: Origin opens a stream to a known Middleman Node.

        Protocol ID: /pangea/route/1.0.0

        Message: FindRoutes { file_hash: [u8; 32], size: u64 }

    Middleman Action:

        Checks local Kademlia DHT for peers "close" to the file_hash.

        Filters peers against local Health/Threat Score (from Shared Memory).

        Generates a Time-Bound Shared Secret (Stemp​).

    Response: Middleman sends RouteResponse { peers: Vec<Multiaddr>, secret: S_{temp} } to Origin.

Phase 2: Parallel Dispersal

    Connection: Origin spawns N parallel Tokio tasks. Each task dials one Target Peer using quinn.

    Handshake:

        Origin sends: AuthChallenge { secret: S_{temp} }.

        Target verifies Stemp​ (received independently from Middleman via gossip/DHT).

    Push:

        Origin opens a uni-directional stream: /pangea/store/1.0.0.

        Origin pumps the CES-processed shard data.

        Zero-Copy: The buffer from the CES pipeline is passed directly to quinn::SendStream::write_chunk.

5. Download Protocol (The Aggregation)

This process is Many-to-One. The Requester pulls shards from multiple holders to maximize bandwidth.

Phase 1: Localization

    DHT Query: Requester queries the DHT for file_hash.

    Discovery: Returns a list of Providers (nodes holding shards).

Phase 2: Hyper-Parallel Pull

    Task Spawning: Requester spawns a Tokio task for every Provider found.

    Request:

        Stream ID: /pangea/fetch/1.0.0

        Message: GetShard { file_hash, shard_index }

    Aggregation:

        As chunks arrive, they are written into a Reorder Buffer (a HashMap<Index, Bytes>).

        Once enough shards (K) arrive for a segment, the Reassembly Task (running on a separate thread) triggers.

    Reconstruction:

        Reed-Solomon reconstructs missing shards.

        Decrypt → Decompress.

        Write to Disk via io_uring.

6. The Guard (Security Layer)

Level 1: eBPF XDP Filter (The Kernel Wall)

    Tool: aya-rs.

    Mechanism: A shared BPF_MAP_TYPE_HASH stores u32 IP addresses.

    Logic:
    Rust

    // Kernel Space (XDP)
    if let Some(_) = ALLOWED_MAP.get(&src_ip) {
        return XDP_PASS;
    }
    return XDP_DROP;

    Update: The User-space app updates this map instantly when the AI or Middleman validates a new peer.

Level 2: Application Handshake (The Secret)

    Tool: Cap'n Proto (or simple binary struct).

    Logic: Even if a packet passes XDP, the connection is dropped if the first bytes on the QUIC stream do not decrypt correctly using the Shared Secret.

7. Implicit DHT (Storage Logic)

We do not create a separate "DHT Network." The storage is the DHT.

    Record: When a node stores a shard, it automatically publishes a Provider Record to the Kademlia network.

        Key: SHA256(File)

        Value: My_PeerID

    Libp2p Integration: We use libp2p::kad behavior.

        Optimization: We implement a custom RecordStore trait in Rust. Instead of saving provider records to a generic DB, we check our actual on-disk shard storage to confirm "Yes, I still have this file."

1. The Capability Scanner (The "Bootloader")

Before the node starts, it runs a probe. This isn't just "Checking RAM"; it's checking instruction sets and kernel versions.

The Rust Implementation (capabilities.rs):
Rust

use sysinfo::{System, SystemExt};
use std::arch::is_x86_feature_detected;

pub struct HardwareCaps {
    pub has_avx2: bool,      // Intel "God Mode" Math
    pub has_neon: bool,      // Apple/ARM "God Mode" Math
    pub has_io_uring: bool,  // Linux Kernel 5.1+ Async Disk
    pub has_ebpf: bool,      // Linux Kernel XDP Support
    pub ram_gb: u64,
    pub cpu_cores: usize,
}

impl HardwareCaps {
    pub fn probe() -> Self {
        let mut sys = System::new_all();
        sys.refresh_all();

        let kernel_supports_uring = check_kernel_version(5, 1); // Helper fn
        
        // Runtime Check for SIMD (Safe on any CPU)
        let avx2 = if cfg!(target_arch = "x86_64") { 
            is_x86_feature_detected!("avx2") 
        } else { false };

        let neon = if cfg!(target_arch = "aarch64") { 
            std::arch::is_aarch64_feature_detected!("neon") 
        } else { false };

        Self {
            has_avx2: avx2,
            has_neon: neon,
            has_io_uring: kernel_supports_uring && cfg!(target_os = "linux"),
            has_ebpf: check_root_permissions() && cfg!(target_os = "linux"),
            ram_gb: sys.total_memory() / 1024 / 1024 / 1024,
            cpu_cores: sys.cpus().len(),
        }
    }
}

2. The Adaptive Storage Engine (Trait-Based Fallback)

We define a Trait (Interface) called StorageEngine. We implement it twice.

    UringEngine: Uses tokio-uring for zero-copy, interrupt-free DMA transfers (NVMe speeds).

    ThreadedEngine: Uses tokio::fs (Standard thread pool) for Windows/Mac/Old Linux.

The Switch Logic:
Rust

// main.rs
let caps = HardwareCaps::probe();

let storage: Box<dyn StorageEngine> = if caps.has_io_uring {
    println!("🚀 Mode: io_uring (Kernel Bypass)");
    Box::new(UringEngine::new())
} else {
    println!("⚠️ Mode: Standard IO (Compatibility)");
    Box::new(ThreadedEngine::new())
};

// Now the rest of the app just calls `storage.write()`. 
// It doesn't care which engine is running.

3. The Adaptive CES Pipeline (SIMD Dispatch)

For Encryption and Sharding, we use Function Pointers that are set once at startup.

    Scenario: You are sharding a 1GB file.

    High-End PC (AVX2): We use the reed-solomon-erasure crate with the simd-accel feature. It processes 32 bytes per clock cycle.

    Low-End Device: We fall back to the standard scalar implementation.

Implementation Pattern:
Rust

// We define a type for our Shard Function
type ShardFn = fn(data: &[u8], shards: usize) -> Vec<Vec<u8>>;

fn get_optimized_sharding(caps: &HardwareCaps) -> ShardFn {
    if caps.has_avx2 {
        return sharding_avx2; // Calls unsafe AVX intrinsics
    } else if caps.has_neon {
        return sharding_neon; // Calls unsafe ARM intrinsics
    } else {
        return sharding_scalar; // Safe, slower Rust code
    }
}

// The AVX2 implementation (Enabled only on supported compilers)
#[target_feature(enable = "avx2")]
unsafe fn sharding_avx2(data: &[u8], shards: usize) -> Vec<Vec<u8>> {
    // SIMD magic happens here
}

4. The Adaptive Guard (eBPF vs User Filter)

If the user is running as root on Linux, we load the XDP Kernel Program. If they are on Windows or non-root, we fall back to a standard Application-Layer Filter.

    Mode A (Kernel Wall): The XDP program drops packets at the Network Card. 0% CPU Load.

    Mode B (App Wall): We accept the packet into Rust, check the IP map, and drop it. 5% CPU Load.

Why this matters: If a student runs this on a university laptop (no root), the XDP loader will fail. Instead of crashing, Pangea Net catches the error: "Warning: XDP Load Failed. Falling back to User-Space Firewall." The node still works, just slightly slower under attack.

5. The Resource-Aware "Chunker"

The Shard Size should not be random. It depends on your RAM.

    High RAM (>16GB): We read 100MB chunks into memory. This maximizes throughput for the AES-NI / AVX instructions (CPU loves big contiguous data).

    Low RAM (<4GB): We switch to Streaming Mode (64KB chunks). We process tiny pieces so we don't crash the Raspberry Pi.

The Logic:
Rust

let chunk_size = if caps.ram_gb > 16 {
    100 * 1024 * 1024 // 100 MB
} else if caps.ram_gb > 4 {
    10 * 1024 * 1024  // 10 MB
} else {
    64 * 1024         // 64 KB (Tiny Mode)
};

---

## Implementation Status ✅

The Rust implementation is **complete and functional** with the following components:

### Core Components
- ✅ **Hardware Capability Probing** - Adaptive detection of AVX2, NEON, io_uring, eBPF
- ✅ **QUIC Transport Layer** - quinn-based P2P networking with automatic ping/pong
- ✅ **libp2p DHT Integration** - Kademlia DHT for peer discovery and routing
- ✅ **CES Pipeline** - Compression (zstd), Encryption (XChaCha20-Poly1305), Sharding (Reed-Solomon)
- ✅ **Node Store** - Thread-safe storage with quality metrics
- ✅ **Cap'n Proto RPC** - Python interop matching Go schema
- ✅ **Adaptive Firewall** - eBPF on Linux (with root), userspace fallback elsewhere
- ✅ **Storage Engine** - Pluggable with io_uring support (feature-gated)

### Features
- ✅ Adaptive configuration based on system capabilities
- ✅ Zero-copy data paths where possible
- ✅ Comprehensive error handling with `anyhow` and `thiserror`
- ✅ Structured logging with `tracing`
- ✅ Full async/await using Tokio
- ✅ Extensive unit and integration tests

---

## Building the Rust Node

### Prerequisites

```bash
# Install Rust (if not already installed)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Install Cap'n Proto (for RPC schema compilation)
# macOS:
brew install capnp

# Ubuntu/Debian:
sudo apt-get install capnproto

# Verify installations
rustc --version
cargo --version
capnp --version
```

### Build Commands

```bash
# Navigate to rust directory
cd rust

# Standard build (portable, works everywhere)
cargo build --release

# Build with io_uring support (Linux only, requires kernel 5.1+)
cargo build --release --features uring

# Build with eBPF support (Linux only, requires root at runtime)
cargo build --release --features ebpf

# Build with all features
cargo build --release --features uring,ebpf

# Development build (faster compile, slower runtime)
cargo build
```

The binary will be at `rust/target/release/pangea-rust-node`

---

## Running the Node

### Basic Usage

```bash
# Start a node with default settings
cargo run --release

# Or run the binary directly
./target/release/pangea-rust-node

# With custom node ID
cargo run --release -- --node-id 1

# With custom ports
cargo run --release -- \
  --node-id 1 \
  --rpc-addr 127.0.0.1:8080 \
  --p2p-addr 127.0.0.1:9090 \
  --dht-addr 127.0.0.1:9091

# With verbose logging
cargo run --release -- --node-id 1 --verbose

# With DHT bootstrap peers
cargo run --release -- \
  --node-id 2 \
  --bootstrap /ip4/127.0.0.1/tcp/9091/p2p/<peer-id>
```

### Command-Line Options

```
OPTIONS:
    -n, --node-id <NODE_ID>          Node ID [default: 1]
        --rpc-addr <RPC_ADDR>        RPC server address [default: 127.0.0.1:8080]
        --p2p-addr <P2P_ADDR>        QUIC P2P listen address [default: 127.0.0.1:9090]
        --dht-addr <DHT_ADDR>        DHT listen address [default: 127.0.0.1:9091]
        --bootstrap <BOOTSTRAP>...   Bootstrap peers for DHT (multiaddr format)
    -v, --verbose                    Enable verbose logging
    -h, --help                       Print help information
```

---

## Running Tests

```bash
# Run all tests
cargo test

# Run only unit tests
cargo test --lib

# Run only integration tests
cargo test --test integration_test

# Run with output visible
cargo test -- --nocapture

# Run specific test
cargo test test_health_scoring

# Run the test script (comprehensive)
../tests/test_rust.sh

# Run with feature tests
../tests/test_rust.sh --with-features
```

---

## Multi-Node Testing

### Start Multiple Nodes Locally

```bash
# Terminal 1: Start first node
cargo run --release -- \
  --node-id 1 \
  --rpc-addr 127.0.0.1:8080 \
  --p2p-addr 127.0.0.1:9090 \
  --dht-addr 127.0.0.1:9091

# Terminal 2: Start second node (bootstrapping from first)
cargo run --release -- \
  --node-id 2 \
  --rpc-addr 127.0.0.1:8081 \
  --p2p-addr 127.0.0.1:9190 \
  --dht-addr 127.0.0.1:9191 \
  --bootstrap /ip4/127.0.0.1/tcp/9091

# Terminal 3: Start third node
cargo run --release -- \
  --node-id 3 \
  --rpc-addr 127.0.0.1:8082 \
  --p2p-addr 127.0.0.1:9290 \
  --dht-addr 127.0.0.1:9291 \
  --bootstrap /ip4/127.0.0.1/tcp/9091
```

---

## Project Structure

```
rust/
├── Cargo.toml              # Dependencies and features
├── build.rs                # Cap'n Proto schema compilation
├── README.md               # Rust-specific README
│
├── src/
│   ├── main.rs             # CLI entry point
│   ├── lib.rs              # Library exports
│   ├── capabilities.rs     # Hardware capability detection
│   ├── storage.rs          # Storage engine trait + implementations
│   ├── types.rs            # Core data types (Node, Message, etc.)
│   ├── network.rs          # QUIC transport layer
│   ├── dht.rs              # libp2p Kademlia DHT
│   ├── ces.rs              # Compression-Encryption-Sharding pipeline
│   ├── store.rs            # Thread-safe node store
│   ├── rpc.rs              # Cap'n Proto RPC server
│   └── firewall.rs         # Adaptive firewall (eBPF + userspace)
│
└── tests/
    └── integration_test.rs # Integration tests
```

---

## Module Documentation

### `capabilities.rs`
Probes hardware capabilities at runtime:
- SIMD support (AVX2 on x86_64, NEON on ARM)
- io_uring availability (Linux kernel 5.1+)
- eBPF/XDP support (Linux with root)
- System resources (RAM, CPU cores)

### `network.rs`
QUIC-based P2P networking:
- Self-signed certificates for TLS
- Automatic ping/pong for latency measurement
- Connection quality metrics (latency, jitter, packet loss)
- Bi-directional streaming

### `dht.rs`
libp2p Kademlia DHT:
- Peer discovery and routing
- Provider records for file shards
- Bootstrap support
- Multiaddr parsing

### `ces.rs`
Compression-Encryption-Sharding pipeline:
- **Compression**: zstd with adaptive levels
- **Encryption**: XChaCha20-Poly1305 (AEAD)
- **Sharding**: Reed-Solomon erasure coding
- Supports reconstruction with missing shards

### `store.rs`
Thread-safe node storage:
- Concurrent read/write with RwLock
- Automatic status transitions based on threat score
- Health scoring algorithm
- Query by status

### `rpc.rs`
Cap'n Proto RPC server:
- Compatible with Go schema
- Python interop
- Async request handling
- Connection pooling

### `firewall.rs`
Adaptive security layer:
- **eBPF Mode**: Kernel-level XDP filtering (Linux + root)
- **Userspace Mode**: Application-level filtering (portable)
- IP allowlist management
- Real-time updates

---

## Performance Characteristics

### Expected Performance
- **Localhost Latency**: < 1ms (QUIC)
- **WAN Latency**: 2-50ms (depends on network)
- **Throughput**: Limited by network, not CPU (zero-copy paths)
- **CES Pipeline**: Adaptive based on hardware
  - High-end: 100MB chunks, level 9 compression
  - Low-end: 64KB chunks, level 3 compression

### Memory Usage
- **Baseline**: ~10-50 MB (depending on connections)
- **Per Connection**: ~1-5 MB (QUIC buffers)
- **CES Processing**: Adaptive based on RAM
  - 16GB+ RAM: 100MB chunks
  - 4-16GB RAM: 10MB chunks
  - <4GB RAM: 64KB chunks

### CPU Usage
- **Idle**: <1% (event-driven async)
- **Active Networking**: 5-20% per core
- **CES Pipeline**: 50-100% of allocated cores (parallel)
- **eBPF Firewall**: 0% (kernel handles packets)

---

## Python Interop (RPC)

The Rust node exposes the same Cap'n Proto interface as the Go node, allowing Python to connect and control it:

```python
import capnp
import socket

# Load schema
schema = capnp.load('../go/schema/schema.capnp')

# Connect to Rust node
client = capnp.TwoPartyClient(socket.create_connection(('localhost', 8080)))
service = client.bootstrap().cast_as(schema.NodeService)

# Get all nodes
nodes = service.getAllNodes().wait()
for node in nodes.nodes.nodes:
    print(f"Node {node.id}: {node.latencyMs}ms, threat={node.threatScore}")

# Connect to peer
peer = schema.PeerAddress.new_message()
peer.peerId = 2
peer.host = "localhost"
peer.port = 9190
result = service.connectToPeer(peer).wait()
print(f"Connected: {result.success}, latency: {result.quality.latencyMs}ms")
```

---

## Comparison with Go Implementation

| Feature | Go | Rust | Notes |
|---------|-----|------|-------|
| Transport | Noise Protocol | QUIC (quinn) | Rust uses QUIC for better performance |
| DHT | libp2p (custom) | libp2p (kad) | Same protocol, different bindings |
| Encryption | ChaCha20 | XChaCha20-Poly1305 | Rust uses AEAD for authenticity |
| CES Pipeline | Manual | Adaptive | Rust auto-configures based on hardware |
| Firewall | User-space | eBPF + Fallback | Rust supports kernel-level filtering |
| Storage | In-memory | Pluggable | Rust supports io_uring for disk |
| Error Handling | Go errors | anyhow/thiserror | Rust has richer error context |
| Concurrency | Goroutines | Async/await | Both excellent, different models |

---

## Feature Flags

```toml
[features]
default = []
uring = ["tokio-uring"]    # Linux io_uring support
ebpf = ["aya"]             # Linux eBPF/XDP support
```

Build with features:
```bash
cargo build --release --features uring,ebpf
```

---

## Troubleshooting

### Cap'n Proto Schema Not Found
```bash
# Ensure Go schema exists
ls -l ../go/schema/schema.capnp

# Manually compile if build.rs fails
cd rust
capnpc -o rust ../go/schema/schema.capnp
```

### io_uring Build Errors
```bash
# io_uring requires Linux kernel 5.1+
uname -r

# Build without io_uring feature
cargo build --release
```

### eBPF Permission Denied
```bash
# eBPF requires root privileges
sudo ./target/release/pangea-rust-node

# Or use userspace firewall (automatic fallback)
./target/release/pangea-rust-node  # No root needed
```

### Port Already in Use
```bash
# Check what's using the port
lsof -i :8080

# Use different ports
cargo run --release -- --rpc-addr 127.0.0.1:8090 --p2p-addr 127.0.0.1:9099
```

---

## Next Steps

1. **WAN Testing**: Deploy nodes on different networks and test real NAT traversal
2. **Load Testing**: Use `tools/load-testing/` scripts to stress test
3. **Python Integration**: Connect Python AI to Rust nodes via RPC
4. **Container Deployment**: Use Docker/docker-compose for multi-node testing
5. **Monitoring**: Integrate with Prometheus for metrics collection

---

## Contributing

When adding new features to the Rust implementation:

1. Maintain compatibility with the Cap'n Proto schema
2. Add comprehensive tests (unit + integration)
3. Update this documentation
4. Ensure portability (test on Linux, macOS, Windows)
5. Use adaptive patterns that respect hardware capabilities

---

## License

Same as the main project (see root LICENSE file).

