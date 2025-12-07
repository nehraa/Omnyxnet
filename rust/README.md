# Pangea Rust Node: High-Performance Storage, CES Pipeline & Compute Engine

**Version:** 0.6.0-alpha  
**Status:** ✅ Operational - 86+ Tests Passing  
**Last Updated:** 2025-12-07

> 📚 **Related Documentation:**
> - **[../docs/testing/COMPUTE_TEST_SUITE.md](../docs/testing/COMPUTE_TEST_SUITE.md)** - Compute engine tests (61 tests)
> - **[../docs/testing/PHASE1_TEST_SUITE.md](../docs/testing/PHASE1_TEST_SUITE.md)** - Streaming & CES tests
> - **[../docs/DISTRIBUTED_COMPUTE.md](../docs/DISTRIBUTED_COMPUTE.md)** - Compute architecture
> - **[../docs/RUST.md](../docs/RUST.md)** - Complete Rust documentation

> ⚠️ **Development Status:** All features implemented and comprehensively tested with 86+ passing tests. Distributed compute system complete with WASM sandbox. Not recommended for production deployment yet.

High-performance Rust implementation of Pangea Net with QUIC transport, libp2p DHT, adaptive CES pipeline, Cap'n Proto RPC, and optional eBPF firewall.

## Features ✅

- **QUIC Transport**: Ultra-fast P2P networking with quinn
- **libp2p DHT**: Kademlia-based peer discovery and routing
- **CES Pipeline**: Adaptive compression, encryption, and Reed-Solomon sharding
- **Cap'n Proto RPC**: Full compatibility with Go node schema for Python interop
- **Adaptive Firewall**: eBPF/XDP on Linux (with root), userspace fallback elsewhere
- **Hardware-Aware**: Auto-detects AVX2, NEON, io_uring, eBPF capabilities
- **Async Everything**: Tokio-based async/await throughout
- **Comprehensive Tests**: Unit and integration tests included

## Quick Start

```bash
# Build (standard, portable)
cargo build --release

# Run with default settings
cargo run --release

# Run with custom configuration
cargo run --release -- --node-id 1 --verbose

# Run tests
cargo test

# Run comprehensive test suite
../tests/test_rust.sh
```

## Architecture

```
src/
├── main.rs           # CLI entry point with full node orchestration
├── lib.rs            # Public API exports
├── capabilities.rs   # Hardware capability detection (AVX2, io_uring, eBPF)
├── network.rs        # QUIC transport with ping/pong and metrics
├── dht.rs            # libp2p Kademlia DHT for discovery
├── ces.rs            # Compression-Encryption-Sharding pipeline
├── store.rs          # Thread-safe node store with health tracking
├── rpc.rs            # Cap'n Proto RPC server (Python interop)
├── firewall.rs       # Adaptive firewall (eBPF + userspace)
├── storage.rs        # Pluggable storage (io_uring + standard)
└── types.rs          # Core data types (Node, Message, etc.)
```

## Requirements

- **Rust**: 1.70+ (install from https://rustup.rs)
- **Cap'n Proto**: For RPC schema compilation
  - macOS: `brew install capnp`
  - Ubuntu/Debian: `apt-get install capnproto`
- **Optional**: Linux kernel 5.1+ for io_uring
- **Optional**: Linux with root for eBPF/XDP

## Building

```bash
# Standard build (works everywhere)
cargo build --release

# With io_uring support (Linux only)
cargo build --release --features uring

# With eBPF support (Linux only, requires root at runtime)
cargo build --release --features ebpf

# All features
cargo build --release --features uring,ebpf
```

Binary location: `target/release/pangea-rust-node`

## Running

```bash
# Default (node ID 1, standard ports)
./target/release/pangea-rust-node

# Custom configuration
./target/release/pangea-rust-node \
  --node-id 1 \
  --rpc-addr 127.0.0.1:8080 \
  --p2p-addr 127.0.0.1:9090 \
  --dht-addr 127.0.0.1:9091 \
  --verbose

# With DHT bootstrap
./target/release/pangea-rust-node \
  --node-id 2 \
  --bootstrap /ip4/127.0.0.1/tcp/9091
```

## Testing

```bash
# All tests
cargo test

# Unit tests only
cargo test --lib

# Integration tests
cargo test --test integration_test

# With output
cargo test -- --nocapture

# Comprehensive test script
../tests/test_rust.sh
```

## Multi-Node Example

```bash
# Terminal 1: First node
cargo run --release -- --node-id 1 --rpc-addr :8080 --p2p-addr :9090 --dht-addr :9091

# Terminal 2: Second node (bootstraps from first)
cargo run --release -- --node-id 2 --rpc-addr :8081 --p2p-addr :9190 --dht-addr :9191 \
  --bootstrap /ip4/127.0.0.1/tcp/9091

# Terminal 3: Third node
cargo run --release -- --node-id 3 --rpc-addr :8082 --p2p-addr :9290 --dht-addr :9291 \
  --bootstrap /ip4/127.0.0.1/tcp/9091
```

## Python Interop

The Rust node uses the same Cap'n Proto schema as the Go node:

```python
import capnp
import socket

schema = capnp.load('../go/schema/schema.capnp')
client = capnp.TwoPartyClient(socket.create_connection(('localhost', 8080)))
service = client.bootstrap().cast_as(schema.NodeService)

# Get all nodes
nodes = service.getAllNodes().wait()

# Connect to peer
peer = schema.PeerAddress.new_message()
peer.peerId = 2
peer.host = "localhost"
peer.port = 9190
result = service.connectToPeer(peer).wait()
```

## Performance

- **Localhost latency**: < 1ms (QUIC)
- **WAN latency**: 2-50ms (network dependent)
- **Memory**: ~10-50 MB baseline + ~1-5 MB per connection
- **CPU idle**: <1% (event-driven)
- **Adaptive CES**: Auto-configures chunk sizes based on RAM (64KB to 100MB)

## Documentation

See [`../docs/RUST.md`](../docs/RUST.md) for complete documentation including:
- Detailed architecture
- Module documentation
- Performance characteristics
- Troubleshooting guide
- Comparison with Go implementation

## Contributing

1. Maintain Cap'n Proto schema compatibility
2. Add tests for new features
3. Update documentation
4. Ensure cross-platform portability
5. Use adaptive patterns that respect hardware capabilities

## License

Same as main project (see root LICENSE).
