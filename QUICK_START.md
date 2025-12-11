# Quick Start Guide - P2P Chat/Video/Audio

## Simplified Workflow - Chat Messaging

### Setup (One Time)
1. Build the project:
   ```bash
   ./scripts/setup.sh
   # Select option 1 (Full Installation)
   ```

### Running Chat Between Two Devices

#### Device A (First Node):
```bash
# Terminal 1: Start Go node
cd go
export LD_LIBRARY_PATH="../rust/target/release:$LD_LIBRARY_PATH"
./bin/go-node -node-id=1 -capnp-addr=:8080 -libp2p=true -libp2p-port=9081 -local

# Terminal 2: Start GUI
python3 desktop/desktop_app_kivy.py
```

In GUI:
1. Click "Connect to Node" → Enter `localhost` and `8080` → Connect
2. Go to "Communications" tab
3. Click **"Show My IP"** (green button) → Note your IP (e.g., 192.168.1.100)
4. Share this IP with Device B (via phone, email, etc.)

#### Device B (Second Node):
```bash
# Terminal 1: Start Go node  
cd go
export LD_LIBRARY_PATH="../rust/target/release:$LD_LIBRARY_PATH"
./bin/go-node -node-id=2 -capnp-addr=:8080 -libp2p=true -libp2p-port=9082 -local

# Terminal 2: Start GUI
python3 desktop/desktop_app_kivy.py
```

In GUI:
1. Click "Connect to Node" → Enter `localhost` and `8080` → Connect  
2. Go to "Communications" tab
3. Click **"Show My IP"** → Note your IP (e.g., 192.168.1.101)
4. Share this IP with Device A

#### Establishing Chat Connection

**Device A**:
1. Enter Device B's IP in "Peer IP address" field → `192.168.1.101`
2. Click "Start Chat Session"
3. Wait for "Chat is now ACTIVE" message

**Device B**:
1. Enter Device A's IP in "Peer IP address" field → `192.168.1.100`
2. Click "Start Chat Session"
3. Wait for "Chat is now ACTIVE" message

#### Sending Messages

**Device A**:
- Type "Hello from A" in message field
- Click "Send Message"
- Should see: `You: Hello from A`

**Device B**:
- Should automatically see: `Peer (...): Hello from A`
- Type "Hello back from B"
- Click "Send Message"
- Should see: `You: Hello back from B`

**Device A**:
- Should automatically see: `Peer (...): Hello back from B`

✅ **Chat is working!** Messages now appear automatically without manual polling.

---

## DCDN Multiaddr Connection (via setup.sh)

### Device A (First to Start):
```bash
./scripts/setup.sh
# Select option 20 (DCDN Demo)
# Select option 1 (Show My Multiaddr)
```

You'll see output like:
```
✅ SHARE THIS MULTIADDR WITH THE OTHER NODE:

  /ip4/192.168.1.100/tcp/9081/p2p/12D3KooWAbc123...

(Copy the full line above)
```

**Copy this entire multiaddr** and send it to Device B.

### Device B (Connecting):
```bash
./scripts/setup.sh
# Select option 20 (DCDN Demo)
# Select option 2 (Connect to Peer)
# Paste the multiaddr from Device A
```

Should see:
```
✅ Connected to DCDN peer!
```

Now both nodes are connected via DCDN and can exchange data.

---

## DCDN Connection (via GUI)

### Device A:
1. Open desktop_app_kivy.py
2. Connect to Go node (localhost:8080)
3. Go to "DCDN" tab
4. Click **"Show My Multiaddr"** (green button)
5. Copy the displayed multiaddr
6. Share with Device B

### Device B:
1. Open desktop_app_kivy.py  
2. Connect to Go node (localhost:8080)
3. Go to "DCDN" tab
4. Paste Device A's multiaddr in the text field
5. Click **"Connect to Peer"** (blue button)

Connection should be established!

---

## Video Calling (Simplified)

### Device A:
1. Go to "Communications" tab
2. Click "Show My IP" → Note IP
3. Share IP with Device B
4. Enter Device B's IP in "Peer IP address" (under Video Call)
5. Click "Start Video"

### Device B:
1. Go to "Communications" tab
2. Click "Show My IP" → Note IP
3. Enter Device A's IP in "Peer IP address"
4. Click "Start Video"

### ⚠️ Current Limitation:
- Video is being **sent** but **not displayed**
- Backend changes needed to receive and display video
- See FIXES_SUMMARY.md for details

---

## Voice Calling (Simplified)

Same procedure as Video:

### Device A & B:
1. Click "Show My IP" to get IP
2. Exchange IPs
3. Enter peer's IP
4. Click "Start Voice"

### ⚠️ Current Limitation:
- Audio is being **sent** but **not played**
- Backend changes needed to receive and play audio
- See FIXES_SUMMARY.md for details

---

## Troubleshooting

### "Failed to connect to peer"
1. ✅ Both devices clicked "Start Chat/Video/Voice"?
2. ✅ IP addresses correct? (Use "Show My IP")
3. ✅ Firewall allows ports?
   - Chat: 9999
   - Video: 9996
   - Voice: 9998
   - DCDN: 9081, 9082
4. ✅ Both on same network?
5. ✅ Go node running on both? (Check "Connected" status)

### Messages not appearing
1. ✅ Chat session active on both sides?
2. ✅ Wait 1-2 seconds (polling interval)
3. ✅ Check terminal logs for errors
4. ✅ Try stopping and restarting chat

### Video/Audio not working
- See FIXES_SUMMARY.md
- Backend receiving not implemented yet
- Sending works, receiving needs Go schema changes

---

## What Works Now ✅

1. **Simplified IP Sharing**: Green "Show My IP" buttons everywhere
2. **DCDN Multiaddr Display**: Easy copy-paste workflow
3. **Chat Message Receiving**: Automatic polling and display
4. **Improved UI Layout**: Clearer workflow
5. **Better Instructions**: In-app help text

## What Needs Testing ⚠️

1. End-to-end chat between actual devices
2. DCDN connection via GUI
3. DCDN connection via setup.sh
4. Message exchange with delays/network issues

## What Doesn't Work Yet ❌

1. Video display (receives nothing)
2. Audio playback (receives nothing)
3. Requires Go backend changes (see FIXES_SUMMARY.md)

---

## Test Script

Run the automated test helper:
```bash
./tests/test_chat_gui.sh
```

This will:
1. Start two Go nodes
2. Provide step-by-step testing instructions
3. Help verify chat functionality

---

## Files Changed

- `scripts/setup.sh` - DCDN multiaddr options
- `desktop/desktop_app_kivy.py` - All UI improvements
- `FIXES_SUMMARY.md` - Detailed technical documentation
- `QUICK_START.md` - This file
- `tests/test_chat_gui.sh` - Test helper script

---

## Next Steps for Full Functionality

See FIXES_SUMMARY.md section "Backend Changes Needed" for what's required to enable video/audio receiving and display.
