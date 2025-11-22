# Cross-Device Testing Guide

**Version:** 0.3.0-alpha  
**Last Updated:** 2025-11-22  
**Status:** ✅ Cross-device communication tested and working!

## 🎯 Quick Start - Test on Multiple Devices

This guide shows you how to test Pangea Net across multiple devices on your local network or WAN. All the complex stuff is automated - just run one script on each device!

> ✅ **Verified Working:** Cross-device P2P connections successfully tested across different networks with dynamic port assignment and peer discovery.

### What Gets Tested

When you run cross-device tests, you're testing the complete "Golden Triangle" architecture:

1. **Go (Soldier)** - Network I/O, P2P communication with libp2p, DHT for discovery
2. **Rust (Worker)** - CES Pipeline (Compress, Encrypt, Shard), Upload/Download, Caching
3. **Python (Manager)** - AI/ML optimization, threat prediction, high-level orchestration

### Features in Action

- ✅ **Discovery**: Nodes find each other automatically via mDNS (local) or DHT (WAN)
- ✅ **Upload**: Files are compressed, encrypted, sharded, and distributed
- ✅ **Download**: Shards are fetched, reconstructed, decrypted, decompressed
- ✅ **Cache**: Shards and manifests are cached locally for speed
- ✅ **Auto-heal**: System monitors and maintains shard redundancy
- ✅ **AI Optimization**: ML model predicts optimal shard parameters
- ✅ **Security**: Token auth, rate limiting, whitelisting
- ✅ **Shared Memory**: Go-Python data streaming for real-time metrics

---

## 🚀 Method 1: Easy Test Script (Recommended)

The easiest way to test! Run this on each device:

### On First Device (Bootstrap Node)

```bash
cd /path/to/WGT
./scripts/easy_test.sh
```

The script will:
1. Ask if this is the first device → Select "1"
2. Auto-build binaries if needed
3. Start the node
4. Show you the connection info for other devices

Example output:
```
╔════════════════════════════════════════╗
║   🌍 Pangea Net - Easy Device Test    ║
╚════════════════════════════════════════╝

Select mode:
  1. First device (bootstrap node)
  2. Additional device (connect to network)

Enter choice (1 or 2): 1

Configuration:
  Node ID: 1
  Your IP: 192.168.1.100
  ...

✓ Peer ID: 12D3KooWNN2GVrfnsD9GuuER97Zzei8VAcHaZr7sMJv1CHedpubb
✓ P2P Port: 44119
ℹ  Note: Both Peer ID and port change on each restart

For other devices to join this network:
  ./scripts/easy_test.sh 2 /ip4/192.168.1.100/tcp/44119/p2p/12D3KooWNN2GVrfnsD9GuuER97Zzei8VAcHaZr7sMJv1CHedpubb
```

> **Important:** The P2P port (e.g., 44119) and Peer ID change on each restart because libp2p assigns them dynamically. Always copy the exact values shown in the output.

### On Additional Devices

Copy the **complete multiaddr** from the first device (including the dynamic port and peer ID):

```bash
cd /path/to/WGT
./scripts/easy_test.sh 2 /ip4/192.168.1.100/tcp/44119/p2p/12D3KooWNN2GVrfnsD9GuuER97Zzei8VAcHaZr7sMJv1CHedpubb
```

Or run interactively:
```bash
./scripts/easy_test.sh
# Select "2" for additional device
# Enter node ID (2, 3, 4, etc.)
# Enter bootstrap IP (192.168.1.100)
# Enter bootstrap Port (44119) - from the bootstrap node's output
# Enter bootstrap Peer ID (12D3Koo...) - from the bootstrap node's output
```

> **Note:** The script will prompt you for the IP, port, AND peer ID separately. Make sure to copy all three values from the bootstrap node's output.

### Quick Commands

Once your node is running, the script creates shortcuts:

```bash
# Add the alias (shown in script output)
source ~/.pangea/node-1/alias.sh

# Then use simple commands:
pangea status                    # Check node status
pangea upload /path/to/file      # Upload a file
pangea download <file_hash>      # Download a file
pangea list                      # List cached files
pangea logs                      # View live logs
pangea stop                      # Stop the node
```

---

## 🧪 Method 2: Localhost Testing Script

Test everything on one machine first (3 nodes):

```bash
cd /path/to/WGT
./tests/test_localhost_full.sh
```

This comprehensive test validates:
- ✅ Multi-node startup (3 nodes)
- ✅ Peer discovery via mDNS
- ✅ File upload with CES pipeline
- ✅ Cache functionality
- ✅ Shared memory operations
- ✅ Python RPC connectivity
- ✅ Network health monitoring
- ✅ Log analysis

Output shows what's working and what needs attention.

---

## 🔧 Method 3: Manual Setup

For more control over the configuration:

### On Each Device

1. **Clone and Build**
   ```bash
   git clone https://github.com/nehraa/WGT.git
   cd WGT
   
   # Build Go node
   cd go && go build -o bin/go-node .
   cd ..
   
   # Build Rust library
   cd rust && cargo build --release
   cd ..
   ```

2. **Start First Node (Bootstrap)**
   ```bash
   export LD_LIBRARY_PATH="$(pwd)/rust/target/release:$LD_LIBRARY_PATH"
   ./go/bin/go-node -node-id=1 -capnp-addr=:8080 -libp2p=true -local=true
   ```
   
   Note the libp2p multiaddr from the logs (looks like `/ip4/192.168.1.100/tcp/9180/p2p/12D3Koo...`)

3. **Start Additional Nodes**
   ```bash
   export LD_LIBRARY_PATH="$(pwd)/rust/target/release:$LD_LIBRARY_PATH"
   ./go/bin/go-node \
     -node-id=2 \
     -capnp-addr=:8081 \
     -libp2p=true \
     -peers=/ip4/192.168.1.100/tcp/9180/p2p/12D3Koo...
   ```

---

## 📁 Testing File Operations

### Upload a File

Once nodes are running, you can test file upload:

```bash
# Method 1: Using Rust CLI (if available)
./rust/target/release/pangea-rust-node upload /path/to/file.txt 1,2,3

# This will:
# 1. Read the file
# 2. Compress it (zstd)
# 3. Encrypt it (ChaCha20-Poly1305)
# 4. Shard it (Reed-Solomon: 8 data + 4 parity shards)
# 5. Distribute shards to nodes 1, 2, 3 via Go transport
# 6. Cache shards locally
# 7. Store manifest in cache
# 8. Return manifest JSON
```

### Download a File

```bash
# Method 1: Using Rust CLI (if available)
./rust/target/release/pangea-rust-node download manifest.json

# This will:
# 1. Parse the manifest
# 2. Query DHT for shard locations
# 3. Check local cache first
# 4. Fetch missing shards from peers
# 5. Reconstruct file (Reed-Solomon)
# 6. Decrypt (ChaCha20-Poly1305)
# 7. Decompress (zstd)
# 8. Save to output file
```

### Using Python Client

```bash
cd python
python3 main.py connect              # Test connection
python3 main.py list-nodes           # See all nodes
python3 main.py health-status        # Check peer health
python3 main.py predict              # Start AI prediction
```

---

## 🔍 What to Look For

### Successful Connection Signs

1. **In Logs** (`~/.pangea/node-1/logs/node.log`):
   ```
   ✅ Started libp2p host
   ✅ Listening on /ip4/127.0.0.1/tcp/9180
   ✅ Node discovered via mDNS: peer_id=12D3Koo...
   ✅ Connected to peer: /ip4/192.168.1.101/tcp/9180/p2p/12D3Koo...
   ```

2. **Discovery Working**:
   - Nodes see each other in logs
   - `list-nodes` command shows multiple peers
   - mDNS broadcasts detected

3. **File Operations**:
   - Upload creates manifest
   - Shards distributed to peers
   - Cache populated
   - Download reconstructs successfully

### Common Issues

1. **"libpangea_ces.so not found"**
   ```bash
   # Fix: Set library path
   export LD_LIBRARY_PATH="$(pwd)/rust/target/release:$LD_LIBRARY_PATH"
   ```

2. **Nodes don't discover each other**
   - Check firewall (allow UDP/TCP on ports 9180+)
   - Ensure same subnet for mDNS
   - Try explicit `-peers` flag with multiaddr

3. **Python import errors**
   ```bash
   cd python
   pip install -r requirements.txt
   ```

---

## 📊 Architecture Being Tested

### The Golden Triangle

```
┌─────────────────────────────────────────────────────────────┐
│                      Pangea Net Node                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐         │
│  │   GO     │      │   RUST   │      │  PYTHON  │         │
│  │ (Soldier)│◄────►│ (Worker) │◄────►│ (Manager)│         │
│  └──────────┘      └──────────┘      └──────────┘         │
│                                                             │
│  • Network I/O    • CES Pipeline    • AI/ML                │
│  • P2P (libp2p)   • Upload/Download • Optimization         │
│  • DHT            • Cache           • Prediction           │
│  • Security       • Auto-heal       • Monitoring           │
│  • Metrics        • File Detection  • Analysis             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow: Upload

```
1. User → upload file.txt
2. Rust reads file
3. CES Pipeline:
   ├─ Compress (zstd, adaptive level)
   ├─ Encrypt (ChaCha20-Poly1305)
   └─ Shard (Reed-Solomon: k=8, m=4)
4. Go distributes shards to peers via libp2p
5. Rust caches shards locally
6. Manifest stored in cache & DHT
```

### Data Flow: Download

```
1. User → download <hash>
2. Rust queries cache (fast path)
3. If miss, query DHT for locations
4. Go fetches shards from peers
5. Reed-Solomon reconstructs data
6. Decrypt → Decompress
7. Save file
```

---

## 🎯 Testing Scenarios

### Scenario 1: Basic File Sharing (3 devices)

1. Start node on Device A (bootstrap)
2. Start nodes on Devices B and C (connect to A)
3. Upload file from Device A
4. Download file on Device B
5. Verify file integrity

**Tests**: Discovery, upload, download, cache

### Scenario 2: Auto-Healing (3+ devices)

1. Upload file with redundancy
2. Stop one node holding shards
3. Wait for auto-heal to trigger (5 min default)
4. Verify new shards created on remaining nodes
5. Download file still works

**Tests**: Auto-healing, redundancy, reliability

### Scenario 3: Cache Performance

1. Upload large file
2. Download on Device B (populates cache)
3. Download same file again (should be instant)
4. Check cache stats

**Tests**: Caching, performance, LRU eviction

### Scenario 4: AI Optimization

1. Start Python client on Device A
2. Monitor network metrics
3. Upload files with varying conditions
4. Observe shard parameter adaptation
5. Check AI predictions vs. actual performance

**Tests**: AI optimizer, adaptive behavior, metrics collection

---

## 📝 Next Steps After Testing

Once cross-device testing is working:

1. **Security**: Enable token auth, configure shared secrets
2. **Monitoring**: Set up Prometheus metrics, health dashboards
3. **Performance**: Run load tests, benchmark throughput
4. **WAN**: Test across different networks (requires public IPs/NAT traversal)
5. **Scale**: Add more nodes (10+), test with large files (GB+)

---

## 🐛 Debugging

### Enable Verbose Logging

```bash
# Go node
./go/bin/go-node -test=true ...

# Rust node (if running separately)
RUST_LOG=debug ./rust/target/release/pangea-rust-node ...

# Python client
python3 -m pdb main.py ...
```

### Check Connectivity

```bash
# Test if port is open
nc -zv 192.168.1.100 9180

# Test if node is listening
lsof -i :8080

# Check firewall
sudo ufw status
sudo iptables -L
```

### View Metrics

```bash
# If Prometheus enabled
curl http://localhost:9101/metrics
```

---

## 📚 Related Documentation

- [VERSION.md](VERSION.md) - Project status and feature readiness
- [README.md](README.md) - Project overview and architecture
- [docs/BLUEPRINT_IMPLEMENTATION.md](docs/BLUEPRINT_IMPLEMENTATION.md) - Feature implementation details
- [docs/RUST.md](docs/RUST.md) - Rust node implementation
- [docs/CACHING.md](docs/CACHING.md) - Cache and lookup system

---

## ⚠️ Important Notes

- **Alpha Software**: This is v0.3.0-alpha - works locally, NOT production-ready
- **Same Network**: Devices must be on same subnet for mDNS discovery
- **Ports**: Default ports 8080+, 9080+, 9180+ must be available
- **Firewall**: May need to allow UDP/TCP traffic
- **Library Path**: LD_LIBRARY_PATH must include rust/target/release

---

**Questions or Issues?** Check logs in `~/.pangea/node-*/logs/` and see [VERSION.md](VERSION.md) for known limitations.

*Created: 2025-11-22 | Version: 0.3.0-alpha*
