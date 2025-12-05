# Distributed Compute Testing - Verification Guide

## How to Tell If Execution Was Remote or Local

After running the test, you should see one of these messages:

### ✅ Remote Execution (Correct)
```
🌐 Connecting to compute node at localhost:8080...
✅ Successfully connected to remote node

⚡ Submitting job to DISTRIBUTED NETWORK...
   Target: localhost:8080
   ✅ Job submitted successfully
   Job ID: job-xxxxx
   Waiting for remote execution...
   ✅ Result received from remote node

[Results show]:
   🌐 Execution Mode: REMOTE (distributed)
      Executed on: localhost:8080
```

### ❌ Local Execution (Fallback)
```
🌐 Connecting to compute node at localhost:8080...
❌ Failed to connect to remote node at localhost:8080
⚠️  FALLING BACK TO LOCAL EXECUTION

⚡ Running computation LOCALLY on this machine...

[Results show]:
   💻 Execution Mode: LOCAL (this machine)
```

---

## Troubleshooting

### Problem: Test says "LOCAL" but responder is running

**Check 1: Port conflict**
- Initiator uses port 8080 for Cap'n Proto RPC
- Responder also uses port 8080
- If both on same machine, second one fails to bind

```bash
# Check what's using port 8080
lsof -i :8080

# Should show TWO processes if both nodes are running
```

**Check 2: Connection timing**
- Responder might not have fully connected yet
- Solution: Wait longer before running the test on initiator
- Responder script waits 4 seconds, but libp2p connection takes 5-8 seconds

**Check 3: Peer address format**
- Responder needs EXACT peer address from initiator
- Must include `/ip4/`, `/tcp/`, and `/p2p/Qm...` parts
- Any spaces or typos cause connection failure

```bash
# Check responder logs
cat ~/.pangea/compute_test/responder_node.log | grep -i "connect\|peer\|error"
```

**Check 4: Go node logs**
Examine the actual node logs to see what's happening:

```bash
# Initiator node log
tail -50 ~/.pangea/compute_test/node.log

# Look for:
# - "Connected peers:" with count > 0
# - "libp2p node started"
# - "listening on" messages
```

```bash
# Responder node log
tail -50 ~/.pangea/compute_test/responder_node.log

# Look for:
# - "Connecting to peer"
# - "Stream opened"
# - "Connected peers:" with count > 0
```

---

## Step-by-Step Verification

### Device 1 (Initiator)

1. **Start the initiator**
   ```bash
   ./tests/compute/examples/03_distributed_compute_initiator.sh
   ```

2. **Wait for it to show peer address**
   Look for:
   ```
   ✅ Node 1 started!
   
   Copy this address for responder:
   /ip4/192.168.1.100/tcp/7777/p2p/QmXxxx...
   
   Waiting for responder to connect...
   ```

3. **Keep terminal open** - don't close it

---

### Device 2 (Responder)

1. **Start the responder**
   ```bash
   ./tests/compute/examples/03_distributed_compute_responder.sh
   ```

2. **When prompted, paste EXACTLY**
   ```
   Enter the peer address from the initiator device:
   > /ip4/192.168.1.100/tcp/7777/p2p/QmXxxx...
   ```

3. **Watch for connection message**
   ```
   Starting Node 2 (responder)...
   Connecting to initiator...
   ✅ Connected to initiator!
   
   Responder ready. Keep this terminal open.
   ```

4. **Keep terminal open** - it stays running

---

### Device 1 (Initiator) - Continued

5. **Wait for responder to connect**
   Once responder connects, you'll see:
   ```
   ✅ Responder connected!
   
   Running Distributed Matrix Multiplication
   
   ⚠️  No responder connected yet
   The test will run LOCALLY on this machine
   ```

   **OR** (if it detected):
   ```
   ✅ Responder is connected
   The test will run REMOTELY on the responder node
   ```

6. **Look at test output**
   The test runs with clear indication of execution mode:
   ```
   🌐 Execution Mode: REMOTE (distributed)
      Executed on: localhost:8080
   ```

---

## Why Might It Run Locally?

### Reason 1: Responder not connected yet
- Initiator waits 60 seconds for responder
- If responder takes >60 seconds to connect, test runs locally
- Solution: Make sure responder connects quickly (< 4 seconds usually)

### Reason 2: Cap'n Proto RPC not listening
- Go node started but RPC server didn't bind
- Check: `lsof -i :8080` should show go-node
- Check logs: `grep "Cap'n Proto" ~/.pangea/compute_test/*.log`

### Reason 3: Connection established but RPC call fails
- Node connects via libp2p but Cap'n Proto RPC connection fails
- This would show: "✅ Responder connected!" but then "❌ Failed to connect to remote node"
- Check: responder node logs for RPC errors

### Reason 4: Same machine testing
- Both nodes on localhost:8080 - second binding fails
- Solution: Use different machines OR test with responder on different port (not supported yet)

---

## Debug Mode: View All Logs

**Initiator node log:**
```bash
cat ~/.pangea/compute_test/node.log
```

**Responder node log:**
```bash
cat ~/.pangea/compute_test/responder_node.log
```

**Python client log:**
Look at stdout from test output (shows connection attempts and RPC calls)

---

## Network Verification

If suspecting network issues:

```bash
# Test if devices can see each other
ping <other_device_ip>

# Test if port 7777 is reachable (libp2p)
nc -zv <other_device_ip> 7777

# Test if port 8080 is reachable (Cap'n Proto)
nc -zv <other_device_ip> 8080
```

---

## What SHOULD Happen (Ideal Flow)

1. Initiator starts → Shows peer address
2. Responder starts → Connects to peer address
3. Initiator detects connection → "✅ Responder connected!"
4. Initiator runs test → "⚡ Submitting job to DISTRIBUTED NETWORK..."
5. Responder receives job → Executes matrix multiplication
6. Responder sends result → Back to initiator
7. Initiator displays → "🌐 Execution Mode: REMOTE (distributed)"
8. Both cleanup → Processes exit cleanly

---

## Quick Checklist

- [ ] Initiator shows peer address clearly
- [ ] Responder accepts peer address without errors
- [ ] Responder says "✅ Connected to initiator!"
- [ ] Initiator shows "✅ Responder connected!" before running test
- [ ] Test output shows "🌐 Execution Mode: REMOTE"
- [ ] Computation completes without errors

If any step fails, check the corresponding logs above.
