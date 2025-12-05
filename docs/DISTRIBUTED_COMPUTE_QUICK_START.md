# Quick Start: Cross-Device Distributed Compute Testing

## New: Matrix Multiply CLI

The easiest way to test distributed compute is now the Matrix Multiply CLI:

```bash
# Activate Python environment
cd python && source .venv/bin/activate

# Local test (no network needed)
python main.py compute matrix-multiply --size 10 --generate --verify

# Distributed test (requires network connection)
python main.py compute matrix-multiply --size 50 --generate --verify --connect
```

See [CLI_MATRIX_MULTIPLY.md](CLI_MATRIX_MULTIPLY.md) for full documentation.

---

## 3-Minute Setup (Traditional Method)

### Option 1: Using setup.sh Menu (Recommended)

**Device 1 (Manager):**
```bash
./scripts/setup.sh
# Select: 2) Establish Network Connection
# Select: 1) Manager (Initiator)
```

**Device 2 (Worker):**
```bash
./scripts/setup.sh
# Select: 2) Establish Network Connection
# Select: 2) Worker (Responder)
# Enter Manager's IP address when prompted
```

### Option 2: Using Example Scripts

### Device 1 (Initiator)
```bash
cd /path/to/WGT
./tests/compute/examples/03_distributed_compute_initiator.sh
```

**You'll see:**
```
╔════════════════════════════════════════════════════════════╗
║   DISTRIBUTED COMPUTE - INITIATOR (Device 1)              ║
╚════════════════════════════════════════════════════════════╝

Building Go node (if needed)...
Starting Node 1 (initiator)...

✅ Node 1 started on port 8080

📋 Copy this address for the responder:

/ip4/192.168.1.100/tcp/7777/p2p/Qm[very long peer ID]

Keep this terminal open. It will show the peer address above.
Share it with someone running the responder script on another device.

Waiting for responder to connect... (timeout in 60 seconds)
```

**Copy the multiaddr (the long `/ip4/...` line) and share it with Device 2**

---

### Device 2 (Responder)
On a different machine, run:

```bash
./tests/compute/examples/03_distributed_compute_responder.sh
```

**You'll see:**
```
╔════════════════════════════════════════════════════════════╗
║   DISTRIBUTED COMPUTE - RESPONDER (Device 2)              ║
╚════════════════════════════════════════════════════════════╝

Building Go node (if needed)...

Enter the peer address from the initiator device:
> 
```

**Paste the address from Device 1:**
```
> /ip4/192.168.1.100/tcp/7777/p2p/Qm[very long peer ID]
```

**Then you'll see:**
```
Starting Node 2 (responder)...
Connecting to initiator...

✅ Connected to initiator!

Responder ready. Keep this terminal open.
The initiator will now run the distributed compute test.
```

---

### Device 1 (Initiator) - Continued
Once the responder connects, you'll see:

```
✅ Responder connected!

Running distributed compute test...
  Delegating matrix_multiply (1024x1024) to remote worker...
  ✅ Remote execution successful
  Result verified: ✅

Test completed successfully!

Cleaning up...
```

---

## What Just Happened?

1. **Node 1 (initiator)** started a libp2p node and waited for connections
2. **Node 2 (responder)** connected to Node 1 via the shared peer address
3. Both nodes ran a distributed matrix multiplication:
   - Created a 1024x1024 matrix
   - Node 1 delegated computation to Node 2
   - Node 2 executed and returned the result
   - Both verified correctness

## Troubleshooting

### "Timeout waiting for responder"
- Responder script didn't run
- Peer address was incorrect (copy without extra spaces)
- Network connectivity issue between devices
→ Try again, making sure both scripts are running

### "Port already in use"
```bash
lsof -i :8080
kill -9 <PID>  # Kill the process
```

### "No library found"
```bash
cd rust && cargo build --release
```

### "Connection refused"
- Check both devices are on the same network
- Verify firewall allows port 7777
- Make sure you're copying the full peer address

## Architecture Behind the Scenes

```
Device 1                          Device 2
┌──────────────────────────────────────────────────┐
│                                                  │
│  Node 1 (Port 8080)                             │
│  ├─ libp2p protocol handler                     │
│  │  └─ /pangea/compute/1.0.0 (task protocol)   │
│  │                                              │
│  └─ Waiting for peer connection                │
│                                                 │
│  "Copy this peer address:" ──────────────────→ │
│                                                 │
│                      ←────── [User pastes]      │
│                                                 │
│  ✅ Peer connected                             │
│  └─ Send: compute task (matrix multiply)       │
│  ← Receive: result (computed matrix)           │
│  └─ Verify: result correctness                 │
│                                                 │
└──────────────────────────────────────────────────┘
                                 │
                        Node 2 (Port 8080)
                        ├─ libp2p protocol handler
                        │  └─ /pangea/compute/1.0.0
                        │
                        └─ Connected to peer
                           ├─ Receive: task
                           ├─ Execute: matrix multiply (Rust)
                           └─ Send: result back
```

## Files Involved

- **go/libp2p_node.go** - Network node setup
- **go/compute_protocol.go** - Task delegation protocol
- **go/pkg/compute/manager.go** - Computation orchestration
- **rust/src/lib.rs** - Actual matrix computation
- **python/src/distributed_compute.py** - Python test client

## Advanced: Running via Setup Menu

Instead of running scripts directly, you can use the setup menu:

```bash
./scripts/setup.sh
# Select: 18 (Run Distributed Compute Test)
# Choose: 3) distributed compute initiator OR 3) distributed compute responder
```

The menu automatically discovers and lists all scripts in `tests/compute/examples/`.

---

**That's it!** You now have a working distributed compute system across two devices. 🎉
