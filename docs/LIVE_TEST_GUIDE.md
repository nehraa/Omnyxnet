# 🎯 Live Streaming Test - Quick Reference

**One script. Two devices. Select 1/2/3/4 and GO!**

> **Note:** This script uses the **Go libp2p implementation** for all networking.
> Python files (live_chat.py, live_video.py, etc.) are deprecated reference implementations only.

## 🚀 Quick Start

### Device 1 (First Device / Bootstrap)

```bash
cd /path/to/WGT
./scripts/live_test.sh
```

1. Press **Y** (you're the first device)
2. Wait for the connection info to appear:
   ```
   ╔══════════════════════════════════════════════════════════════════╗
   ║   🌍 PANGEA NET - CONNECTION INFORMATION                        ║
   ╠══════════════════════════════════════════════════════════════════╣
   ║  ✓ Peer ID:   12D3KooWNN2GVrf...
   ║  ✓ P2P Port:  44119 (dynamically assigned)
   ║  ✓ Your IP:   192.168.1.100
   ║                                                                  ║
   ║  ℹ️  Note: Port and Peer ID change on each restart              ║
   ╠══════════════════════════════════════════════════════════════════╣
   ║  📋 COPY THIS FULL ADDRESS TO OTHER DEVICE:                     ║
   ║                                                                  ║
   ║  /ip4/192.168.1.100/tcp/44119/p2p/12D3KooWNN2GVrf...            ║
   ║                                                                  ║
   ╚══════════════════════════════════════════════════════════════════╝
   ```
3. Copy the full `/ip4/...` address and share it with Device 2
4. Press ENTER when Device 2 is ready

### Device 2 (Second Device / Joiner)

```bash
cd /path/to/WGT
./scripts/live_test.sh
```

1. Press **N** (connecting to existing device)
2. Paste the peer address from Device 1
3. Done!

### Both Devices - Select Test

```
  1 - 💬 Live Chat      (text messaging)
  2 - 🎤 Live Voice     (audio call)
  3 - 🎥 Live Video     (video call, TCP)
  4 - 🎥 Live Video     (low-latency, UDP)
```

Just press **1**, **2**, **3**, or **4** and BOOM - it works!

---

## 📋 Requirements

### Both Devices Need:

1. **Same network (LAN/WiFi)** or open ports for WAN

2. **Project built** (script auto-builds if needed):
   ```bash
   cd go && make build
   cd ../rust && cargo build --release
   ```

3. **Python3 with numpy:**
   ```bash
   pip install numpy
   ```

### For Live Voice (Option 2):

```bash
pip install sounddevice   # Recommended, easier to install
# OR
pip install pyaudio       # Requires portaudio system library
```

### For Live Video (Option 3):

```bash
pip install opencv-python
```

---

## 🔧 How Connection Works

```
Device 1 (Bootstrap)              Device 2 (Joiner)
      │                                  │
      │  1. Starts libp2p node           │
      │  2. Gets dynamic port + peer ID  │
      │     (e.g., port 44119)           │
      │                                  │
      │  3. Shows full multiaddr:        │
      │     /ip4/192.168.x.x/tcp/PORT/p2p/PEER_ID
      │            ─────────────────────►│
      │                                  │
      │                                  │  4. Connects using multiaddr
      │  ◄───────────────────────────────┤
      │                                  │
      │  5. Both select same test (1/2/3)│
      │                                  │
      └────────────── 🎉 ────────────────┘
               Connected!
```

**Important:** The port and Peer ID are **dynamically assigned** by libp2p on each restart. Always copy the exact values shown!

---

## 🔌 Network Ports Used

| Port | Purpose |
|------|---------|
| 8080/8081 | Cap'n Proto RPC |
| Dynamic | libp2p P2P (shown in output) |
| 9999 | Chat |
| 9998 | Voice |
| 9997 | Video |

**Firewall:** Make sure chat/voice/video ports (9997-9999) are open!

---

## 🐛 Troubleshooting

### "Cannot connect to peer"
- Both devices on same WiFi/LAN?
- Firewall blocking ports 9997-9999?
- Peer address copied correctly (including the dynamic port)?

### "Failed to extract peer address"
- Wait a few more seconds for node to start
- Check log: `tail -f ~/.pangea/live_test/node.log`

### "No audio library found"
```bash
pip install sounddevice
```

### "OpenCV not found"
```bash
pip install opencv-python
```

---

## 📁 Files Location

```
~/.pangea/live_test/
├── peer_address.txt   # Your peer address (if bootstrap)
├── remote_peer.txt    # Remote peer address (if joiner)
├── node.pid           # Node process ID
└── node.log           # Node logs
```

---

## 🛑 Stopping

- Press **Q** in the menu to quit and stop the node
- Or press **Ctrl+C** anytime
- Manual stop: `kill $(cat ~/.pangea/live_test/node.pid)`

---

## 🎉 That's It!

No complex setup. No configuration files. Just run `./scripts/live_test.sh` on both devices and test!
