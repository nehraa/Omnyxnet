# Testing Quick Start - For the Impatient

**Version:** 0.6.0-alpha  
**Last Updated:** 2025-12-07

**You asked for simple. Here it is.**

> 📚 **For detailed testing information:**
> - **[testing/TESTING_INDEX.md](testing/TESTING_INDEX.md)** - Complete testing hub with 86+ tests ⭐
> - **[testing/PHASE1_TEST_SUITE.md](testing/PHASE1_TEST_SUITE.md)** - Phase 1 P2P & Streaming tests
> - **[testing/PHASE2_TEST_SUITE.md](testing/PHASE2_TEST_SUITE.md)** - Phase 2 ML Framework tests ⭐
> - **[testing/COMPUTE_TEST_SUITE.md](testing/COMPUTE_TEST_SUITE.md)** - Distributed Compute tests ⭐

## 🚀 Test on Localhost (One Command)

```bash
./tests/test_localhost_full.sh
```

This starts 3 nodes on your machine and tests everything. Takes ~30 seconds.

---

## 🌍 Test on 3 Devices (Two Commands)

### Device 1 (your main machine)

```bash
./scripts/easy_test.sh
```

- Select option `1` (first device)
- It shows you a command like this:

```
For other devices to join:
  ./scripts/easy_test.sh 2 /ip4/192.168.1.100/tcp/9180
```

### Devices 2 & 3 (your other machines)

Copy that exact command and run it:

```bash
./scripts/easy_test.sh 2 /ip4/192.168.1.100/tcp/9180
./scripts/easy_test.sh 3 /ip4/192.168.1.100/tcp/9180
```

**Done.** They're connected.

---

## 📁 Upload/Download Files

The script tells you how. Look for "Quick Commands" section in the output.

Short version:

```bash
# After running easy_test.sh, you get a shortcut:
source ~/.pangea/node-1/alias.sh

# Then:
pangea upload /path/to/file.txt
pangea download <file_hash>
pangea status
pangea logs
```

---

## 🐛 If Something Breaks

**Nodes won't start?**
```bash
# Check the log:
tail ~/.pangea/node-1/logs/node.log
```

**Library not found?**
```bash
# Build it:
cd rust && cargo build --release
```

**Firewall blocking?**
```bash
# Allow ports 8080-8090, 9080-9090, 9180-9190
sudo ufw allow 8080:8090/tcp
sudo ufw allow 9080:9090/tcp
sudo ufw allow 9180:9190/tcp
sudo ufw allow 9180:9190/udp  # For mDNS
```

---

## 📚 Want More Details?

- **Full guide**: [CROSS_DEVICE_TESTING.md](CROSS_DEVICE_TESTING.md)
- **Architecture**: [docs/BLUEPRINT_IMPLEMENTATION.md](docs/BLUEPRINT_IMPLEMENTATION.md)
- **Status**: [VERSION.md](VERSION.md)

---

## ✅ What's Actually Tested

When you run these scripts, you're testing:

| Feature | What It Does | Status |
|---------|--------------|--------|
| **Discovery** | Nodes find each other via mDNS (local) or DHT (WAN) | ✅ Works |
| **P2P Network** | libp2p with Noise encryption, QUIC transport | ✅ Works |
| **Multi-node** | 3+ nodes running simultaneously | ✅ Works |
| **CES Pipeline** | Compress → Encrypt → Shard (Rust) | ✅ Code ready |
| **Upload** | File → CES → Distribute shards to peers | 🚧 CLI pending |
| **Download** | Fetch shards → Reconstruct → Decrypt → Decompress | 🚧 CLI pending |
| **Cache** | LRU cache for shards, persistent manifests | ✅ Code ready |
| **Auto-heal** | Monitor & maintain shard redundancy | ✅ Code ready |
| **AI Optimizer** | ML predicts optimal shard parameters | ✅ Code ready |
| **Python RPC** | Python ↔ Go communication | 🚧 Needs deps |
| **Shared Memory** | Go → Python data streaming | ✅ Code ready |
| **Security** | Token auth, rate limiting, whitelist | ✅ Code ready |

**Legend:**
- ✅ Works = Running and tested
- ✅ Code ready = Implemented, needs runtime integration
- 🚧 CLI pending = Command-line interface needs wiring
- 🚧 Needs deps = Requires Python packages

---

## 🎯 What Happens in Each Mode

### Localhost Test (`test_localhost_full.sh`)

1. Builds binaries if needed
2. Starts 3 Go nodes with libp2p
3. Waits for mDNS discovery (5 seconds)
4. Checks if nodes see each other
5. Tests file operations (basic)
6. Monitors health
7. Analyzes logs
8. Cleans up

**Time:** ~30 seconds  
**Output:** Detailed test report

### Easy Test (`easy_test.sh`)

1. Asks if first device or additional
2. Builds if needed
3. Starts one node with proper config
4. Shows connection info for other devices
5. Creates helper commands (upload/download/status)
6. Tails logs (Ctrl+C to detach)
7. Keeps running in background

**Time:** ~10 seconds setup  
**Output:** Connection info + helper commands

---

## 💡 Pro Tips

1. **Localhost first**: Run `test_localhost_full.sh` before trying cross-device
2. **Same network**: Devices must be on same subnet for mDNS
3. **Check IPs**: Make sure you use the right IP for bootstrap node
4. **Library path**: The scripts handle this, but if manual: `export LD_LIBRARY_PATH=$(pwd)/rust/target/release`
5. **View everything**: Each node logs to `~/.pangea/node-N/logs/node.log`

---

## 🚦 Current Status (v0.3.0-alpha)

**What works NOW:**
- ✅ Multi-node startup
- ✅ Peer discovery
- ✅ Encrypted P2P communication
- ✅ Network health monitoring

**What's coded but needs CLI:**
- File upload/download commands
- Cache operations
- Auto-healing triggers

**What needs Python:**
- AI optimization
- Threat prediction
- RPC client demos

**What's NOT ready:**
- WAN deployment (needs testing)
- Production security (needs audit)
- Scale testing (needs validation)

See [VERSION.md](VERSION.md) for complete status.

---

## 🎬 That's It

You now have:
1. A localhost test script
2. A cross-device test script
3. Helper commands for file operations
4. Complete documentation if you want it

Go test stuff. Break things. The logs will tell you what happened.

---

*Created: 2025-11-22 | Keep it simple.*
