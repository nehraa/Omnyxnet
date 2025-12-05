# 🎯 START HERE - Cross-Device Testing

**You want to test Pangea Net on multiple devices. This is your guide.**

---

## ⚡ Super Quick Start

### Step 1: Establish Network Connection

```bash
./scripts/setup.sh
# Select: 2) Establish Network Connection
# Choose: Manager (Device 1) or Worker (Device 2+)
```

### Step 2: Run Matrix Multiply (Test Distributed Compute)

```bash
cd python && source .venv/bin/activate
python main.py compute matrix-multiply --size 10 --generate --verify
```

### Test Everything on Localhost (30 seconds)

```bash
./tests/test_localhost_full.sh
```

This verifies all components work on your machine before testing across devices.

### Test on 3+ Devices (2 minutes)

**Device 1 (Manager):**
```bash
./scripts/setup.sh
# Select: 2) Establish Network Connection
# Select: 1) Manager (Initiator)
# Note the IP address shown
```

**Devices 2, 3, ... (Workers):**
```bash
./scripts/setup.sh
# Select: 2) Establish Network Connection
# Select: 2) Worker (Responder)
# Enter Manager's IP address
```

**Done.** Nodes are connected and running.

---

## 📚 Documentation Structure

We have five guides:

| Guide | When to Use | What's Inside |
|-------|-------------|---------------|
| **[TESTING_QUICK_START.md](TESTING_QUICK_START.md)** | You want TL;DR | Commands only, no fluff |
| **[CROSS_DEVICE_TESTING.md](CROSS_DEVICE_TESTING.md)** | You want details | Architecture, data flows, debugging |
| **[CLI_MATRIX_MULTIPLY.md](CLI_MATRIX_MULTIPLY.md)** | Matrix multiply | CLI reference, examples |
| **[NETWORK_CONNECTION.md](NETWORK_CONNECTION.md)** | Network setup | Registry, Manager/Worker modes |
| **[CONTAINERIZED_TESTING.md](CONTAINERIZED_TESTING.md)** | Docker tests | Container testing guide |

---

## 🎮 What You Can Do

After running `setup.sh` → Option 2, you get:

```bash
# On each device, set up the alias:
source ~/.pangea/node-1/alias.sh

# Then use these commands:
pangea status                    # Check if node is running
pangea upload /path/to/file      # Upload a file (distributes shards)
pangea download <file_hash>      # Download and reconstruct a file
pangea list                      # List cached files
pangea logs                      # View live logs (Ctrl+C to exit)
pangea stop                      # Stop the node
```

---

## 🏗️ What's Being Tested

Your test validates the **Golden Triangle architecture**:

```
┌─────────────────────────────────────────────────┐
│              Pangea Net Node                    │
├─────────────────────────────────────────────────┤
│                                                 │
│  GO (Soldier)     RUST (Worker)    PYTHON (Mgr) │
│  ──────────────   ──────────────   ──────────── │
│  • Network I/O    • CES Pipeline   • AI/ML      │
│  • libp2p P2P     • Upload/Down    • Optimizer  │
│  • DHT            • Caching        • Prediction │
│  • Security       • Auto-heal      • RPC Client │
│                                                 │
└─────────────────────────────────────────────────┘
```

### Features Tested

| Feature | Description | Status |
|---------|-------------|--------|
| **Discovery** | Nodes find each other (mDNS/DHT) | ✅ Working |
| **P2P Network** | Encrypted libp2p communication | ✅ Working |
| **Multi-node** | 3+ nodes running simultaneously | ✅ Working |
| **CES Pipeline** | Compress→Encrypt→Shard in Rust | ✅ Code ready |
| **Upload** | File→shards→distribute to peers | 🚧 CLI pending |
| **Download** | Fetch→reconstruct→decrypt→decompress | 🚧 CLI pending |
| **Cache** | LRU cache for shards & manifests | ✅ Code ready |
| **Auto-heal** | Maintain shard redundancy | ✅ Code ready |
| **AI Optimizer** | ML predicts shard parameters | ✅ Code ready |

**Legend:**
- ✅ Working = Tested and functional
- ✅ Code ready = Implemented, needs CLI wiring
- 🚧 CLI pending = Command interface in progress

---

## 📁 What You Actually Made

Based on reading the architecture docs (BLUEPRINT_IMPLEMENTATION.md, RUST.md, CACHING.md), you now have:

### Test Scripts

1. **`tests/test_localhost_full.sh`**
   - Comprehensive localhost validation
   - Starts 3 nodes, checks discovery, monitors health
   - Takes ~30 seconds
   - Shows detailed test report

2. **`scripts/easy_test.sh`**
   - Interactive cross-device setup
   - Auto-builds binaries
   - Creates helper commands
   - Shows connection info for additional devices

3. **`scripts/cross_device_setup.sh`**
   - Manual deployment option
   - More control over configuration

### Documentation

1. **TESTING_QUICK_START.md** - Commands only (5KB)
2. **CROSS_DEVICE_TESTING.md** - Full guide with architecture (11KB)
3. **START_HERE.md** - This navigation guide

### What Gets Tested

**When you run the scripts, they test:**

1. **Build System**
   - Go binary compilation
   - Rust library (libpangea_ces.so)
   - Library path configuration

2. **Network Layer (Go)**
   - libp2p initialization
   - mDNS local discovery
   - DHT setup for WAN discovery
   - Noise encryption handshake
   - Cap'n Proto RPC server

3. **Storage Layer (Rust)**
   - CES pipeline (ready for CLI)
   - Upload protocol (ready for CLI)
   - Download protocol (ready for CLI)
   - Cache operations (ready for runtime)
   - Auto-healing service (ready for runtime)

4. **Intelligence Layer (Python)**
   - RPC client (needs dependencies)
   - AI shard optimizer (needs integration)
   - Threat prediction (needs integration)

---

## 🔍 Current Status (v0.3.0-alpha)

### ✅ What Works NOW

- Multi-node startup with proper configuration
- Peer discovery via mDNS (local networks)
- Encrypted P2P communication (Noise protocol)
- Network health monitoring
- Log analysis and error detection

### ✅ What's Coded (needs runtime integration)

- File upload: CES pipeline, shard distribution
- File download: Shard fetching, reconstruction
- Caching: LRU cache, persistent manifests
- Auto-healing: Redundancy monitoring & repair
- AI optimization: ML-based shard parameter tuning
- Security: Token auth, rate limiting, whitelist
- Shared memory: Go-Python data streaming

### 🚧 What Needs Work

- CLI commands for upload/download (in progress)
- Python dependencies for AI features
- WAN deployment testing
- Production security audit
- Scale testing (10+ nodes)

See [VERSION.md](VERSION.md) for complete status tracking.

---

## 🐛 Troubleshooting

### Nodes won't start?

```bash
# Check the log:
tail ~/.pangea/node-1/logs/node.log

# Common issue: Library not found
export LD_LIBRARY_PATH=$(pwd)/rust/target/release:$LD_LIBRARY_PATH
```

### Nodes don't see each other?

```bash
# Check firewall (allow UDP for mDNS):
sudo ufw allow 9180:9190/udp
sudo ufw allow 9180:9190/tcp

# Verify same subnet (mDNS only works locally):
ip addr show
```

### Build fails?

```bash
# Install dependencies:
sudo apt-get install capnproto  # For Rust build
go mod download                  # For Go build
```

### Want verbose logs?

```bash
./go/bin/go-node -test=true ...  # Go node debug mode
RUST_LOG=debug ...               # Rust debug logging
```

---

## 📖 Deep Dive

Want to understand what's under the hood?

### Architecture

- **[docs/BLUEPRINT_IMPLEMENTATION.md](docs/BLUEPRINT_IMPLEMENTATION.md)** - Feature implementation guide
- **[docs/RUST.md](docs/RUST.md)** - Rust node complete guide
- **[docs/CACHING.md](docs/CACHING.md)** - Cache & lookup system

### Components

- **[go/README.md](go/README.md)** - Go P2P networking
- **[rust/README.md](rust/README.md)** - Rust CES pipeline
- **[python/README.md](python/README.md)** - Python AI layer

### Status

- **[VERSION.md](VERSION.md)** - Current version and feature status
- **[IMPLEMENTATION_COMPLETE.md](IMPLEMENTATION_COMPLETE.md)** - Feature completion status (90%)

---

## 🎯 Testing Scenarios

### Scenario 1: Basic File Sharing

1. Start 3 devices with `easy_test.sh`
2. Upload file from Device 1
3. Download on Device 2
4. Verify integrity

### Scenario 2: Auto-Healing

1. Upload file with redundancy
2. Stop one device
3. Wait 5 minutes (auto-heal interval)
4. Check new shards created
5. Verify download still works

### Scenario 3: Cache Performance

1. Upload large file
2. Download on Device 2 (populates cache)
3. Download again (should be instant)
4. Check cache stats

### Scenario 4: Network Discovery

1. Start Device 1 (bootstrap)
2. Note its multiaddr from logs
3. Start Devices 2, 3 with bootstrap peer
4. Check logs for "Connected to peer"
5. Verify discovery working

---

## 💡 Next Steps

After successful cross-device testing:

1. **Enable security features**: Token auth, shared secrets
2. **Add monitoring**: Prometheus metrics, dashboards
3. **Performance testing**: Benchmark upload/download speed
4. **WAN deployment**: Test across different networks
5. **Scale testing**: Try 10+ nodes

---

## 🏁 Summary

You now have:
- ✅ Localhost test (one command)
- ✅ Cross-device setup (interactive script)
- ✅ Helper commands for operations
- ✅ Comprehensive documentation
- ✅ Architecture understanding

**Go test. Break things. Learn.**

The scripts handle the complexity. You just run commands and observe behavior.

---

## 🆘 Need Help?

1. **Quick answers**: [TESTING_QUICK_START.md](TESTING_QUICK_START.md)
2. **Detailed guide**: [CROSS_DEVICE_TESTING.md](CROSS_DEVICE_TESTING.md)
3. **Architecture**: [docs/BLUEPRINT_IMPLEMENTATION.md](docs/BLUEPRINT_IMPLEMENTATION.md)
4. **Status**: [VERSION.md](VERSION.md)
5. **Logs**: `~/.pangea/node-*/logs/node.log`

---

*Created: 2025-11-22 | Version: 0.3.0-alpha | You got this.* 🚀
