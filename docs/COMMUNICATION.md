# Communication Module Documentation

**Version:** 1.0.0  
**Last Updated:** 2025-12-03  
**Status:** ✅ Implemented

## Overview

The Communication module provides P2P communication capabilities for chat, voice, and video streaming using libp2p. This follows the **Golden Rule**:

- **Go**: All networking (libp2p, TCP, UDP, streams)
- **Rust**: Files, memory, CES pipeline
- **Python**: AI and CLI management

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Communication Stack                          │
├─────────────────────────────────────────────────────────────────┤
│  Python CLI                                                      │
│  └─→ High-level commands for chat, voice, video                 │
│                                                                  │
│  Go Communication Service (go/pkg/communication/)               │
│  ├─→ Chat Protocol    (/pangea/chat/1.0.0)                      │
│  ├─→ Video Protocol   (/pangea/video/1.0.0)                     │
│  └─→ Voice Protocol   (/pangea/voice/1.0.0)                     │
│                                                                  │
│  libp2p                                                          │
│  ├─→ mDNS Discovery (automatic local peer discovery)            │
│  ├─→ DHT Discovery (global peer discovery)                      │
│  ├─→ Noise Protocol (encryption)                                 │
│  └─→ Yamux Multiplexing (multiple streams per connection)       │
└─────────────────────────────────────────────────────────────────┘
```

## Features

### Chat
- **P2P messaging** over libp2p streams
- **Chat history persistence** stored in `~/.pangea/communication/chat_history.json`
- **Automatic reconnection** when peers become available
- **Message format**: JSON with timestamp, sender, and content

### Voice
- **Real-time audio streaming** over libp2p streams
- **Opus codec support** (handled by Rust CES pipeline)
- **Low latency design** with small chunk sizes
- **Sample rate**: 48kHz (Opus-compatible)

### Video
- **Real-time video streaming** over libp2p streams
- **JPEG compression** with dynamic quality adjustment
- **Resolution**: Configurable, default 640x480
- **Frame format**: Header (frameID, width, height, quality) + JPEG data

## Quick Start

### 1. Start Go Node

```bash
# Build if needed
cd go && make build && cd ..

# Start node with libp2p (mDNS enabled by default)
export LD_LIBRARY_PATH="$PWD/rust/target/release:$LD_LIBRARY_PATH"
./go/bin/go-node -node-id 1 -libp2p -local
```

### 2. Start Another Node (Same Network)

```bash
# On another terminal or device on the same network
./go/bin/go-node -node-id 2 -libp2p -local
```

Nodes will automatically discover each other via mDNS!

### 3. Use Python CLI

```bash
# Activate virtual environment
source .venv/bin/activate
cd python

# Start streaming
python3 main.py streaming start --type chat
python3 main.py streaming start --type voice
python3 main.py streaming start --type video

# Get streaming stats
python3 main.py streaming stats
```

## Protocol Details

### Chat Protocol (`/pangea/chat/1.0.0`)

**Message Format:**
```
[4 bytes: message length (big-endian)]
[N bytes: JSON message]
```

**JSON Message Structure:**
```json
{
    "id": "1234567890123456789",
    "from": "12D3KooW...",
    "to": "12D3KooW...",
    "content": "Hello, peer!",
    "timestamp": "2025-12-03T10:30:00Z"
}
```

### Video Protocol (`/pangea/video/1.0.0`)

**Frame Format:**
```
[4 bytes: frame ID (big-endian)]
[2 bytes: width (big-endian)]
[2 bytes: height (big-endian)]
[1 byte:  quality (0-100)]
[3 bytes: reserved]
[4 bytes: data length (big-endian)]
[N bytes: JPEG data]
```

### Voice Protocol (`/pangea/voice/1.0.0`)

**Chunk Format:**
```
[4 bytes: sample rate (big-endian)]
[1 byte:  channels]
[3 bytes: reserved]
[4 bytes: data length (big-endian)]
[N bytes: audio data (PCM or Opus)]
```

## mDNS Auto-Discovery

The communication module leverages libp2p's mDNS service for automatic peer discovery on local networks:

1. **Zero Configuration**: No need to specify peer addresses
2. **Automatic Discovery**: Nodes broadcast presence via mDNS
3. **Instant Connection**: When peers are found, they automatically connect
4. **Local Network**: Works on the same subnet (WiFi/Ethernet)

### How It Works

```
Node 1 Starts                    Node 2 Starts
     |                                |
     v                                v
Broadcast presence              Broadcast presence
     |                                |
     +--------→ mDNS ←-----------------+
                 |
                 v
        Mutual discovery
                 |
                 v
        Automatic connection
                 |
                 v
     Communication ready!
```

### Discovery Topic

All Pangea Net nodes advertise on the topic: `pangea-network`

## File Locations

| File | Description |
|------|-------------|
| `go/pkg/communication/communication.go` | Main communication service |
| `go/libp2p_node.go` | libp2p node with mDNS |
| `python/src/cli.py` | Python CLI for streaming |
| `~/.pangea/communication/chat_history.json` | Chat history storage |

## Python CLI Commands

### Streaming Commands

```bash
# Start streaming service
python3 main.py streaming start --type video
python3 main.py streaming start --type voice
python3 main.py streaming start --type chat

# Stop streaming
python3 main.py streaming stop

# Get statistics
python3 main.py streaming stats

# Connect to streaming peer
python3 main.py streaming connect-peer <host> <port>
```

### Chat Commands (Coming Soon)

```bash
# Send a chat message
python3 main.py chat send <peer_id> "Hello!"

# View chat history
python3 main.py chat history

# View history with specific peer
python3 main.py chat history --peer <peer_id>
```

## Testing

### Automated Test

```bash
# Run communication tests
./tests/test_communication.sh
```

### Manual Test

```bash
# Terminal 1: Start first node
./go/bin/go-node -node-id 1 -libp2p -local -test

# Terminal 2: Start second node
./go/bin/go-node -node-id 2 -libp2p -local -test

# Watch for mDNS discovery logs:
# 📡 mDNS discovered local peer: 12D3KooW...
# ✅ Successfully connected to mDNS peer 12D3KooW
```

## Troubleshooting

### "No peers discovered"

1. **Check network**: Ensure devices are on the same subnet
2. **Check firewall**: mDNS uses multicast (UDP port 5353)
3. **Wait longer**: Discovery can take 5-10 seconds
4. **Check logs**: Look for mDNS service initialization

### "Connection failed"

1. **Check libp2p**: Ensure `-libp2p` flag is used
2. **Check library**: Ensure `LD_LIBRARY_PATH` includes Rust library
3. **Check ports**: Ensure no port conflicts

### "Chat history not saving"

1. **Check permissions**: Ensure `~/.pangea/communication/` is writable
2. **Check disk space**: Ensure sufficient disk space
3. **Check logs**: Look for save errors in node output

## Performance

| Metric | Value |
|--------|-------|
| Chat latency | < 10ms (local network) |
| Video frame rate | 30 FPS (configurable) |
| Voice latency | 20-50ms (local network) |
| mDNS discovery | 2-5 seconds |

## Security

- **Transport encryption**: Noise Protocol (Curve25519 + ChaCha20Poly1305)
- **Authentication**: Peer ID verification via libp2p
- **No central server**: True P2P communication
- **Local discovery only**: mDNS doesn't expose to internet

## Deprecated Files

The following Python files are deprecated and kept only as references:

| File | Replacement |
|------|-------------|
| `python/live_chat.py` | Go communication service |
| `python/live_voice.py` | Go communication service |
| `python/live_video.py` | Go communication service |
| `python/live_video_udp.py` | Go communication service |
| `python/live_video_quic.py` | Removed (QUIC not needed) |

## Related Documentation

- [MDNS.md](MDNS.md) - mDNS auto-discovery details
- [STREAMING_GUIDE.md](STREAMING_GUIDE.md) - Streaming architecture
- [ARCHITECTURE.md](ARCHITECTURE.md) - Overall system architecture
- [TESTING_QUICK_START.md](TESTING_QUICK_START.md) - Testing guide

---

**Module**: Communication  
**Package**: `go/pkg/communication`  
**Protocol Version**: 1.0.0  
**Last Updated**: December 2025
