# Compute Test Examples

This directory contains example scripts demonstrating various aspects of the distributed compute system.

## Quick Start

Run any of these scripts directly, or access them through the setup menu:

```bash
./scripts/setup.sh  # → Option 18 → Select an example
```

## Test Scripts

### 01_local_unit_tests.sh
Basic unit tests for compute functions. Run on a single machine.
- Tests: Matrix operations, compression, basic compute pipeline
- Duration: ~2 minutes
- Requirements: Python 3.7+

### 02_single_node_compute.sh
Single-node compute test with Cap'n Proto integration.
- Tests: Local task execution, Cap'n Proto RPC, serialization
- Duration: ~3 minutes
- Requirements: Go, Rust libraries, Python

### 03_distributed_compute.sh (Legacy)
Experimental monolithic cross-device test. **Deprecated** - use 03_distributed_compute_initiator.sh and 03_distributed_compute_responder.sh instead.

### 03_distributed_compute_initiator.sh ⭐ NEW
**Start this FIRST on Device 1**

Starts Node 1 (initiator) and displays a peer address for the responder to connect to.

```bash
./tests/compute/examples/03_distributed_compute_initiator.sh
```

Output: Shows a multiaddr like `/ip4/192.168.1.100/tcp/7777/p2p/QmXxxx...`

- Starts Go node with libp2p protocol handler
- Waits for responder connection (60 second timeout)
- Runs distributed compute test
- Cleans up on exit

### 03_distributed_compute_responder.sh ⭐ NEW
**Start this SECOND on Device 2**

Connects Node 2 (responder) to the initiator using the peer address.

```bash
./tests/compute/examples/03_distributed_compute_responder.sh
# Then paste the peer address from the initiator terminal
```

- Prompts for peer address from initiator
- Starts Go node with connection string
- Runs same distributed compute test
- Cleans up on exit

### Cross-Device Testing Flow

```
Device 1:
$ ./tests/compute/examples/03_distributed_compute_initiator.sh
Starting Node 1 (initiator)...
✅ Node 1 started
Copy this address for responder:
/ip4/192.168.1.100/tcp/7777/p2p/QmXxxx...
Waiting for responder to connect...

Device 2:
$ ./tests/compute/examples/03_distributed_compute_responder.sh
Enter the peer address from the initiator device:
> /ip4/192.168.1.100/tcp/7777/p2p/QmXxxx...
✅ Connected to initiator!
```

### 04_ces_pipeline.sh
Compression, Encryption, Serialization pipeline test.
- Tests: Full CES pipeline with various compression methods
- Duration: ~5 minutes
- Requirements: Python 3.7+

## Distributed Compute Stack

Each test uses the stack defined in `/docs/DISTRIBUTED_COMPUTE.md`:

- **Go**: libp2p networking, task delegation (`/pangea/compute/1.0.0` protocol)
- **Rust**: Matrix operations library (optimized computation)
- **Python**: Cap'n Proto RPC client for job submission

## Session Files

Tests create a session directory at `~/.pangea/compute_test/` for:
- Node PIDs (for cleanup)
- Log files (for debugging)
- Peer addresses (for cross-device testing)

Clean up manually with:
```bash
rm -rf ~/.pangea/compute_test/
```

## Troubleshooting

### "Port already in use"
Another test is still running. Check for stray processes:
```bash
lsof -i :8080  # Find process using port 8080
kill -9 <PID>   # Kill it
```

### "Connection timeout"
The responder isn't connecting to the initiator. Check:
1. Both scripts are running
2. Peer address is correct (copy/pasted without extra whitespace)
3. Devices are on same network
4. Firewall isn't blocking port 7777

### "No library found"
Rust libraries aren't built. Run:
```bash
cd rust && cargo build --release && cd ..
```

### "Cap'n Proto compilation failed"
Ensure Cap'n Proto is installed:
```bash
brew install capnp  # macOS
apt-get install capnproto  # Linux
```

## Documentation

- Full architecture: `/docs/DISTRIBUTED_COMPUTE.md`
- Go implementation: `/go/compute_protocol.go`
- Rust compute library: `/rust/src/lib.rs`
- Python client: `/python/src/distributed_compute.py`
