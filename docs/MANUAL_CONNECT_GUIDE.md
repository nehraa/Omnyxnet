# Manual Peer Connection - Quick Reference

## TL;DR: What You Need

**Only 2 things:**
1. Remote node's IP address
2. Remote node's libp2p port

**That's it!** Peer ID is auto-detected.

---

## Step 1: Start Remote Node

On the **REMOTE MACHINE**, run:

```bash
cd go
./bin/go-node -node-id=2 -capnp-addr=:8081 -libp2p=true
```

## Step 2: Copy the IP and Port

Look at the output - you'll see something like:

```
2025-01-21 10:30:45 listening on /ip4/192.168.1.100/tcp/9081/p2p/Qmxyz...
```

**Copy these two parts:**
- `192.168.1.100` ← IP address
- `9081` ← Port

## Step 3: Connect from Local Machine

Use **any** of these methods:

### Method A: CLI (Easiest)
```bash
cd python && source .venv/bin/activate
python main.py test manual-connect 192.168.1.100:9081
```

### Method B: Interactive Shell
```bash
./scripts/test_pangea.sh
# Select option 6 and enter: 192.168.1.100:9081
```

### Method C: Python Script
```bash
cd python && source .venv/bin/activate
python examples/manual_connect.py 192.168.1.100:9081
```

---

## What Happens

The tool will:
1. Connect to your local Go node
2. **Try different peer IDs automatically** until it connects
3. Show connection quality (latency, jitter, packet loss)
4. Send a test message
5. Show you're connected ✅

You'll see output like:
```
🔍 Looking for peer at 192.168.1.100:9081...
   Trying peer ID 2... ✅

✅ Connected to peer 2!
   Address: 192.168.1.100:9081
   Latency: 12.5ms
   Jitter: 1.2ms
   Packet Loss: 0.00%

📤 Sending test message...
✅ Test message sent!
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Could not connect" | Check remote node is running on that port |
| Connection refused | IP might be wrong, verify with `ping 192.168.1.100` |
| Still fails | Try different port (9082, 9083, etc.) |
| Firewall blocks | Open the port on both machines |

---

## That's All!

No peer ID needed - it figures it out automatically 🎯

*Last Updated: 2025-01-21*
