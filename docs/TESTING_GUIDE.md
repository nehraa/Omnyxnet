# Pangea Net - Testing Quick Reference

## 🚀 Easiest Way to Test

```bash
# Interactive menu with all test options
./scripts/test_pangea.sh

# Or run all tests automatically
./scripts/test_pangea.sh --all
```

This will:
1. Check prerequisites (go-node, python venv, rust library)
2. Start the Go node automatically
3. Run tests for communication and compute
4. Clean up on exit

---

## 📡 Test Communication

Tests P2P connection, peer discovery, network metrics.

```bash
# Via shell script
./scripts/test_pangea.sh
# Then select option 2

# Via Python CLI
cd python && source .venv/bin/activate
python main.py test communication
```

---

## 🖥️ Test Compute (CES Pipeline)

Tests Compress → Encrypt → Shard pipeline.

```bash
# Via shell script
./scripts/test_pangea.sh
# Then select option 3

# Via Python CLI
cd python && source .venv/bin/activate
python main.py test ces

# With custom data size
python main.py test ces --size 10000
```

---

## 🔗 Manual Peer Connection

Use when mDNS auto-discovery fails (e.g., different subnets).

```bash
# Via shell script
./scripts/test_pangea.sh
# Then select option 6 and enter peer details

# Via Python CLI
python main.py test manual-connect <host>:<port> [peer_id]
python main.py test manual-connect 192.168.1.100:9081
python main.py test manual-connect 10.0.0.5:9081 3
```

**To find peer address on remote machine:**
1. Run: `./bin/go-node -node-id=2 -capnp-addr=:8081 -libp2p=true`
2. Note the IP address
3. Default P2P port is 9081 for node 2

---

## 🐳 Container Tests (DCDN)

Tests the Rust DCDN implementation in an isolated Docker/Podman container.

```bash
# Via shell script
./scripts/test_pangea.sh
# Then select option 20.2

# This will:
# 1. Build the Rust DCDN container image
# 2. Run the test suite inside the container
# 3. Verify chunk transfer and FEC recovery
```

---

## 💬 Test Messaging

```bash
# Via shell script
./scripts/test_pangea.sh
# Then select option 4

# Via Python CLI
python main.py test send 2
python main.py test send 2 -m "Custom message"
```

---

## 📁 Standalone Python Tests

```bash
cd python && source .venv/bin/activate

# Quick test (requires go-node running)
python examples/quick_test.py

# Connect to different node
python examples/quick_test.py localhost:8081

# Manual connection utility
python examples/manual_connect.py 192.168.1.100:9081
```

---

## 🛠️ Prerequisites

Before running tests, ensure:

1. **Go node built:**
   ```bash
   cd go && make build
   ```

2. **Python venv ready:**
   ```bash
   cd python
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Rust library built:**
   ```bash
   cd rust && cargo build --release
   ```

The `test_pangea.sh` script will check and build these automatically.

---

## 🔍 Troubleshooting

**"Failed to connect to Go node"**
- Ensure go-node is running: `./go/bin/go-node -node-id=1 -capnp-addr=:8080 -libp2p=true -local`
- Check port 8080 is not in use

**"CES process failed"**
- Ensure Rust library is built: `cd rust && cargo build --release`
- Check library path is set (macOS): `export DYLD_LIBRARY_PATH=$PWD/rust/target/release`

**"No peers found"**
- Use manual connection: `python main.py test manual-connect <host>:<port>`
- For mDNS, devices must be on same subnet

**"Connection refused"**
- Check firewall allows the port
- Verify the peer is actually running
- Try ping to verify network connectivity

---

## 📋 Test Commands Summary

| Command | Description |
|---------|-------------|
| `./scripts/test_pangea.sh` | Interactive test menu |
| `./scripts/test_pangea.sh --all` | Run all tests |
| `python main.py test all` | Run all Python tests |
| `python main.py test communication` | Test P2P connection |
| `python main.py test ces` | Test CES pipeline |
| `python main.py test manual-connect <addr>` | Manual peer connection |
| `python main.py test send <peer_id>` | Send test message |

---

*Last Updated: 2025-01-21*
