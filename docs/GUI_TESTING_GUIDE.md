# GUI Testing Guide - Pangea Net Desktop Application

**Version:** 0.6.0-alpha  
**Last Updated:** 2025-12-07  
**Status:** Complete Multi-Node GUI Testing Environment

## Overview

This guide explains how to test **all Pangea Net features** using the desktop GUI application (`desktop/desktop_app_kivy.py`) with a local multi-node Docker network. The GUI provides full access to:

- **Node Management** - View nodes, connection info, health status
- **Compute Tasks** - Submit distributed compute jobs, monitor workers
- **File Operations** - Upload/download files with CES (Compression, Encryption, Sharding)
- **Communications** - P2P messaging, liveness testing, network health
- **Network Info** - View peers, topology, connection statistics

---

## Prerequisites

### Required Software

1. **Python 3.8+** with dependencies:
   ```bash
   pip install -r python/requirements.txt
   ```
   Key packages: `kivy>=2.2.0`, `kivymd>=1.1.1`, `capnp>=1.3.0`

2. **Docker** or **Podman** for multi-node network:
   ```bash
   # Debian/Ubuntu
   sudo apt-get install docker.io docker-compose
   
   # macOS
   brew install docker docker-compose
   ```

3. **System Dependencies** (for Kivy):
   ```bash
   # Debian/Ubuntu
   sudo apt-get install libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev \
                        libgstreamer1.0-dev gstreamer1.0-plugins-base gstreamer1.0-plugins-good
   
   # macOS
   brew install sdl2 sdl2_image sdl2_mixer sdl2_ttf gstreamer
   ```

---

## Quick Start (3 Commands)

```bash
# 1. Start 5-node Docker network
./scripts/gui_test_network.sh start

# 2. Launch GUI (auto-connects to node1 on localhost:8080)
python3 desktop/desktop_app_kivy.py

# 3. Test features through GUI tabs
```

That's it! The GUI will auto-connect and you can test all features.

---

## Detailed Setup

### Step 1: Start Multi-Node Network

The `gui_test_network.sh` script manages a 5-node Docker network optimized for GUI testing.

```bash
# Start network
./scripts/gui_test_network.sh start

# Expected output:
# ✓ Building Go node images...
# ✓ Starting network...
# ✓ Network started successfully!
#
# Container Status:
# NAME              STATUS              PORTS
# wgt-gui-node1     Up (healthy)        0.0.0.0:8080->8080/tcp, 0.0.0.0:9081->9081/tcp
# wgt-gui-node2     Up (healthy)        0.0.0.0:8081->8080/tcp, 0.0.0.0:9082->9082/tcp
# wgt-gui-node3     Up (healthy)        0.0.0.0:8082->8080/tcp, 0.0.0.0:9083->9083/tcp
# wgt-gui-node4     Up (healthy)        0.0.0.0:8083->8080/tcp, 0.0.0.0:9084->9084/tcp
# wgt-gui-node5     Up (healthy)        0.0.0.0:8084->8080/tcp, 0.0.0.0:9085->9085/tcp
```

**Network Details:**
- **Node 1 (Bootstrap)**: `localhost:8080` - GUI connects here
- **Nodes 2-5 (Workers)**: `localhost:8081-8084` - Available as peers
- **Internal IPs**: `172.30.0.10-14`
- **Auto-Discovery**: mDNS enabled - nodes discover each other automatically
- **Logs**: Stored in containers, accessible via `docker logs`

### Step 2: Launch Desktop GUI

```bash
python3 desktop/desktop_app_kivy.py
```

**What Happens on Startup:**

1. GUI checks for Go node on `localhost:8080`
2. If found, auto-connects via Cap'n Proto RPC
3. If not found, attempts to build and start Go node locally
4. Once connected, runs health checks
5. GUI is ready to use

**GUI Layout:**

```
┌─────────────────────────────────────────────────────┐
│ Pangea Net - Command Center                    [≡] │
├─────────────────────────────────────────────────────┤
│ Node Connection                                     │
│ ● Connected to localhost:8080                       │
│ [ Connect to Local Node ] [ Disconnect ]           │
│                                                     │
│ Peer Connection (Multiaddr)                         │
│ [/ip4/172.30.0.11/tcp/9082/p2p/...] [Connect Peer] │
└─────────────────────────────────────────────────────┘
│ [Node Management] [Compute] [Files] [Comms] [Net]  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  (Tab content area)                                 │
│                                                     │
├─────────────────────────────────────────────────────┤
│ [15:27:30] ✓ Connected to localhost:8080           │
│ [15:27:31] ✓ All health checks passed!             │
└─────────────────────────────────────────────────────┘
```

---

## Feature Testing Guide

### 1. Node Management Tab

**List All Nodes**
- Click "List All Nodes"
- Expected: Shows all 5 nodes with their IDs, status, latency, threat score
- Example output:
  ```
  Found 5 node(s):
  
  Node 1:
    Status: 1 (Active)
    Latency: 0.50ms
    Threat Score: 0.000
  
  Node 2:
    Status: 1 (Active)
    Latency: 1.20ms
    Threat Score: 0.000
  ...
  ```

**Get Node Info**
- Click "Get Node Info"
- Expected: Shows current node info, connected peers, network metrics
- Example output:
  ```
  === Node Information ===
  
  Connected to: localhost:8080
  Connected Peers: 4
  Peer IDs: 2, 3, 4, 5
  
  Network Metrics:
    Average RTT: 1.35ms
    Packet Loss: 0.00%
    Bandwidth: 1000.00 Mbps
    Peer Count: 4
    CPU Usage: 5.2%
    I/O Capacity: 85.0%
  ```

**Health Status**
- Click "Health Status"
- Expected: Shows health of all nodes with overall network health score
- Example output:
  ```
  === Network Health Status ===
  
  Active Nodes: 5/5
  
  ✅ Node 1: Latency 0.5ms, Threat 0.000
  ✅ Node 2: Latency 1.2ms, Threat 0.000
  ✅ Node 3: Latency 1.1ms, Threat 0.000
  ✅ Node 4: Latency 1.3ms, Threat 0.000
  ✅ Node 5: Latency 1.0ms, Threat 0.000
  
  Overall Health Score: 98.5/100
  Network Status: Good
  ```

### 2. Compute Tasks Tab

**Submit Task**
- Enter task type (e.g., "Matrix Multiply")
- Click "Submit Task"
- Expected: Job submitted with unique job ID
- Example output:
  ```
  ✅ Task submitted successfully!
  
  Job ID: a3f4c2b89d14e5f6
  Type: Matrix Multiply
  Status: Submitted
  
  Use 'Check Task Status' to monitor progress.
  ```

**List Workers**
- Click "List Workers"
- Expected: Shows local node capacity and connected worker nodes
- Example output:
  ```
  === Available Compute Workers ===
  
  Local Node:
    CPU Cores: 4
    RAM: 8192 MB
    Current Load: 12.5%
    Disk Space: 102400 MB
    Bandwidth: 1000.00 Mbps
  
  Connected Workers: 4
    - Worker 2
    - Worker 3
    - Worker 4
    - Worker 5
  ```

**Task Status**
- Click "Check Task Status"
- Expected: Shows status of last submitted job
- Example output:
  ```
  === Task Status ===
  
  Job ID: a3f4c2b89d14e5f6
  Status: completed
  Progress: 100.0%
  Completed Chunks: 16/16
  Est. Time Remaining: 0s
  
  🎉 Task completed! Fetching result...
  Result Size: 2048 bytes
  Worker Node: 3
  Result Preview: b'matrix_result:...'
  ```

### 3. File Operations Tab

**Upload File**
- Click "Browse" to select a file
- Click "Upload"
- Expected: File uploaded with hash and manifest
- Example output:
  ```
  ✅ Upload complete! Hash: d4f5e6a7b8c9d0e1f2a3b4c5d6e7f8a9
  ```

**Download File**
- Hash is auto-filled from upload
- Click "Download"
- Expected: File downloaded and saved
- Example output:
  ```
  ✅ Download complete!
  
  File Hash: d4f5e6a7b8c9d0e1f2a3b4c5d6e7f8a9
  Size: 4096 bytes
  Data Preview: b'test file contents...'
  
  Saved to: ~/Downloads/downloaded_d4f5e6a7.dat
  ```

**List Files**
- Click "List Available Files"
- Expected: Shows recently uploaded files
- Example output:
  ```
  === Available Files ===
  
  Recently Uploaded:
    Hash: d4f5e6a7b8c9d0e1f2a3b4c5d6e7f8a9
    Name: test.txt
    Size: 4096 bytes
    Shards: 8 (+ 4 parity)
    Locations: 4 node(s)
  ```

### 4. Communications Tab

**Test P2P Connection**
- Click "Test P2P Connection"
- Expected: Tests connection to all peers with quality metrics
- Example output:
  ```
  === P2P Connection Test ===
  
  Testing connection to 4 peer(s)...
  
  Peer 2:
    ✅ Latency: 1.20ms
    ✅ Jitter: 0.10ms
    ✅ Packet Loss: 0.00%
    ✅ Message sent successfully
  
  Peer 3:
    ✅ Latency: 1.10ms
    ...
  ```

**Ping All Nodes**
- Click "Ping All Nodes"
- Expected: Pings all nodes and shows latency
- Example output:
  ```
  === Ping All Nodes ===
  
  Pinging 5 node(s)...
  
  ✅ Node 1: 0.50ms
  ✅ Node 2: 1.20ms
  ✅ Node 3: 1.10ms
  ✅ Node 4: 1.30ms
  ✅ Node 5: 1.00ms
  ```

**Check Network Health**
- Click "Check Network Health"
- Expected: Comprehensive network health report
- Example output:
  ```
  === Network Health Check ===
  
  Network Metrics:
    Average RTT: 1.35ms
    Packet Loss: 0.00%
    Bandwidth: 1000.00 Mbps
    Peer Count: 4
    CPU Usage: 5.2%
    I/O Capacity: 85.0%
  
  Overall Health Score: 98.5/100
  Status: ✅ Excellent
  
  Active Nodes: 5
  Connected Peers: 4
  ```

### 5. Network Info Tab

**Show Peers**
- Click "Show Peers"
- Expected: Lists all connected peers with connection quality
- Example output:
  ```
  === Connected Peers ===
  
  Total Peers: 4
  
  Peer 2:
    Latency: 1.20ms
    Jitter: 0.10ms
    Packet Loss: 0.00%
    Quality: ✅ Excellent
  
  Peer 3:
    Latency: 1.10ms
    ...
  ```

**Network Topology**
- Click "Network Topology"
- Expected: ASCII tree view of network structure
- Example output:
  ```
  === Network Topology ===
  
  [Local Node] localhost:8080
    |
    +-- Connected Peers (4)
        +-- Peer 2
        +-- Peer 3
        +-- Peer 4
        +-- Peer 5
  
  Known Nodes in Network: 5
    ✅ Node 1 - 0.5ms
    ✅ Node 2 - 1.2ms
    ✅ Node 3 - 1.1ms
    ✅ Node 4 - 1.3ms
    ✅ Node 5 - 1.0ms
  ```

**Connection Stats**
- Click "Connection Stats"
- Expected: Detailed performance and resource statistics
- Example output:
  ```
  === Connection Statistics ===
  
  Network Performance:
    Average RTT: 1.35ms
    Packet Loss: 0.00%
    Bandwidth: 1000.00 Mbps
    Active Peers: 4
    CPU Usage: 5.2%
    I/O Capacity: 85.0%
  
  Local Node Resources:
    CPU Cores: 4
    RAM: 8192 MB
    Current Load: 12.5%
    Disk Space: 102400 MB
    Bandwidth: 1000.00 Mbps
  ```

---

## Advanced: Manual Peer Connection

By default, nodes discover each other via mDNS. To manually connect to a specific peer:

### Step 1: Get Peer Multiaddr

```bash
./scripts/gui_test_network.sh addrs
```

Example output:
```
Node 2 (IP: 172.30.0.11):
  /ip4/172.30.0.11/tcp/9082/p2p/12D3KooWBhSNFXL9HQQBAJDsmMM4bFgFxN9pRJ9xGmBQd3bVZwjx

Node 3 (IP: 172.30.0.12):
  /ip4/172.30.0.12/tcp/9083/p2p/12D3KooWAXYZ1234567890abcdefghijklmnopqrstuvwxyz
...
```

### Step 2: Connect via GUI

1. Copy a multiaddr (e.g., node 2's address)
2. Paste it in the "Peer Connection (Multiaddr)" field
3. Click "Connect to Peer"

Expected log output:
```
[15:30:15] 🔗 Attempting to connect to peer: /ip4/172.30.0.11/tcp/...
[15:30:15] 📡 Peer connection initiated to: /ip4/172.30.0.11/tcp/9082/p2p/12D3...
[15:30:15] ℹ️  Parsed multiaddr: IP=172.30.0.11, Port=9082, PeerID=12D3Koo...
[15:30:15] ℹ️  Testing network connectivity to 172.30.0.11:9082...
[15:30:15] ✅ Network connectivity OK - Port 9082 is reachable
[15:30:15] ℹ️  Sending connection request to Go node via Cap'n Proto RPC...
[15:30:16] ✅ Successfully connected to peer!
[15:30:16]    Connection Quality:
[15:30:16]    - Latency: 1.20ms
[15:30:16]    - Jitter: 0.10ms
[15:30:16]    - Packet Loss: 0.00%
```

**Error Handling:**

If connection fails, the GUI provides detailed diagnostic information:

```
❌ Network connectivity test FAILED:
   Cannot reach 172.30.0.11:9082
   Error code: 111
   Possible causes:
   - Port 9082 is not open on remote host
   - Firewall blocking connection
   - Remote node not running
   - Wrong IP address
```

---

## Network Management Commands

```bash
# Show network status
./scripts/gui_test_network.sh status

# View live logs
./scripts/gui_test_network.sh logs

# Show all multiaddrs
./scripts/gui_test_network.sh addrs

# Show connection instructions
./scripts/gui_test_network.sh connect

# Stop network
./scripts/gui_test_network.sh stop
```

---

## Troubleshooting

### GUI won't connect to node

**Problem:** GUI shows "Failed to connect to localhost:8080"

**Solution:**
```bash
# Check if node1 is running
docker ps | grep wgt-gui-node1

# Check node1 logs
docker logs wgt-gui-node1

# Restart network
./scripts/gui_test_network.sh stop
./scripts/gui_test_network.sh start
```

### Nodes can't discover each other

**Problem:** "No peers connected" after starting network

**Cause:** mDNS may take 10-30 seconds to discover peers

**Solution:**
- Wait 30 seconds after starting network
- Check logs: `./scripts/gui_test_network.sh logs`
- Manually connect using multiaddrs

### Docker build fails

**Problem:** "failed to solve with frontend dockerfile.v0"

**Solution:**
```bash
# Update Docker
sudo apt-get update && sudo apt-get upgrade docker.io

# Clean Docker cache
docker system prune -a

# Rebuild
./scripts/gui_test_network.sh stop
./scripts/gui_test_network.sh start
```

### Kivy/KivyMD import errors

**Problem:** "ModuleNotFoundError: No module named 'kivy'"

**Solution:**
```bash
# Install Python dependencies
pip install -r python/requirements.txt

# If SDL2 errors, install system dependencies
sudo apt-get install libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev
```

---

## Architecture Details

### Network Topology

```
Docker Bridge Network: 172.30.0.0/16
├─ Node 1 (Bootstrap)
│  ├─ Internal IP: 172.30.0.10
│  ├─ Cap'n Proto RPC: 0.0.0.0:8080 → localhost:8080
│  └─ libp2p P2P: 0.0.0.0:9081 → localhost:9081
├─ Node 2 (Worker)
│  ├─ Internal IP: 172.30.0.11
│  ├─ Cap'n Proto RPC: 0.0.0.0:8080 → localhost:8081
│  └─ libp2p P2P: 0.0.0.0:9082 → localhost:9082
├─ Node 3 (Worker)
│  └─ ... (pattern continues)
├─ Node 4 (Worker)
└─ Node 5 (Worker)
```

### Communication Flow

```
Desktop GUI (Python/Kivy)
     │
     │ Cap'n Proto RPC
     ↓
Node 1 (Go) - localhost:8080
     │
     │ libp2p (mDNS + direct)
     ↓
Nodes 2-5 (Go) - Auto-discovered
     │
     │ P2P messaging, file transfer, compute
     ↓
Distributed operations across all nodes
```

### Port Mappings

| Node | RPC (Host) | RPC (Container) | P2P (Host) | P2P (Container) | Internal IP   |
|------|-----------|-----------------|-----------|-----------------|---------------|
| 1    | 8080      | 8080            | 9081      | 9081            | 172.30.0.10   |
| 2    | 8081      | 8080            | 9082      | 9082            | 172.30.0.11   |
| 3    | 8082      | 8080            | 9083      | 9083            | 172.30.0.12   |
| 4    | 8083      | 8080            | 9084      | 9084            | 172.30.0.13   |
| 5    | 8084      | 8080            | 9085      | 9085            | 172.30.0.14   |

---

## Testing Checklist

Use this checklist to verify all features work through the GUI:

### Node Management
- [ ] List all 5 nodes successfully
- [ ] Get node info shows correct metrics
- [ ] Health status shows all nodes active

### Compute Tasks
- [ ] Submit task returns job ID
- [ ] List workers shows 5 workers
- [ ] Check task status shows progress
- [ ] Task completes and returns result

### File Operations
- [ ] Upload file succeeds with hash
- [ ] List files shows uploaded file
- [ ] Download file retrieves correct data

### Communications
- [ ] P2P test connects to all 4 peers
- [ ] Ping returns latency for all 5 nodes
- [ ] Network health shows excellent/good status

### Network Info
- [ ] Show peers lists 4 peers
- [ ] Topology shows correct tree structure
- [ ] Stats show accurate performance metrics

### Error Handling
- [ ] Invalid multiaddr shows clear error
- [ ] Unreachable peer provides diagnostic info
- [ ] Network test failure shows troubleshooting

---

## Next Steps

After completing GUI testing:

1. **Cross-Device Testing**: Connect GUI to nodes on different machines
   - See `docs/CROSS_DEVICE_TESTING.md`

2. **Production Deployment**: Deploy to real infrastructure
   - See `docs/DEPLOYMENT.md`

3. **Custom Compute Tasks**: Implement custom WASM modules
   - See `docs/DISTRIBUTED_COMPUTE.md`

4. **DCDN Testing**: Test distributed CDN features
   - See `docs/DCDN.md`

---

## Related Documentation

- [DESKTOP_APP.md](DESKTOP_APP.md) - Desktop app architecture
- [DISTRIBUTED_COMPUTE.md](DISTRIBUTED_COMPUTE.md) - Compute system details
- [NETWORK_CONNECTION.md](NETWORK_CONNECTION.md) - Network configuration
- [CONTAINERIZED_TESTING.md](CONTAINERIZED_TESTING.md) - Docker setup details
- [QUICK_START.md](QUICK_START.md) - Project quick start

---

**Status:** ✅ Complete  
**Tested On:** Ubuntu 22.04, macOS 13+  
**Docker Version:** 20.10+  
**Python Version:** 3.8+
