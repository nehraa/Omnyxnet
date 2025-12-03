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
- **Debounced saving**: History is saved with debouncing to prevent race conditions

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

# Chat commands
python main.py chat send <peer_id> "Hello!"
python main.py chat history
python main.py chat peers

# Voice commands
python main.py voice start
python main.py voice stop
python main.py voice stats

# Video commands
python main.py video start
python main.py video stop
python main.py video stats
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

### Chat Commands

```bash
# Send a chat message
python main.py chat send <peer_id> "Hello!"

# View chat history
python main.py chat history

# View history with specific peer
python main.py chat history --peer <peer_id>

# View last 50 messages
python main.py chat history --limit 50

# List connected peers
python main.py chat peers
```

### Voice Commands

```bash
# Start voice streaming
python main.py voice start

# Start voice and connect to peer
python main.py voice start --peer-host 192.168.1.100 --peer-port 9000

# Stop voice streaming
python main.py voice stop

# View voice statistics
python main.py voice stats
```

### Video Commands

```bash
# Start video streaming
python main.py video start

# Start video and connect to peer
python main.py video start --peer-host 192.168.1.100 --peer-port 9000

# Stop video streaming
python main.py video stop

# View video statistics
python main.py video stats
```

### Legacy Streaming Commands

The existing streaming commands also work:

```bash
# Start streaming service
python main.py streaming start --type video
python main.py streaming start --type audio
python main.py streaming start --type chat

# Stop streaming
python main.py streaming stop

# Get statistics
python main.py streaming stats
```

## Testing

Run the communication test suite:

```bash
./tests/test_communication.sh
```

The test suite checks:
- Go compilation with communication package
- Node startup and mDNS discovery
- Python CLI command availability
- Chat history file reading
- Documentation correctness

## Implementation Notes

### Context-Aware Reads

The stream handlers use read deadlines to ensure proper context cancellation handling. This prevents goroutines from blocking indefinitely on reads when the service is shutting down.

### Debounced Chat History Saving

Instead of spawning a goroutine on every message to save history, the service uses a debounced save mechanism. This prevents race conditions and reduces disk I/O.

### Stream Type Constants

The Python CLI uses named constants for stream types:
- `STREAM_TYPE_VIDEO = 0` - Video streaming
- `STREAM_TYPE_AUDIO = 1` - Audio/voice streaming
- `STREAM_TYPE_CHAT = 2` - Chat messaging

## Troubleshooting

### No peers discovered

1. **Check network**: Ensure both nodes are on the same subnet
2. **Firewall**: mDNS uses port 5353/UDP - ensure it's open
3. **Local mode**: Use `-local` flag for local testing

### Connection timeout

1. **Verify peer address**: Check the peer ID is correct
2. **Check ports**: Ensure Cap'n Proto port (default 8080) is not blocked
3. **Retry**: mDNS discovery may take a few seconds

### Chat history not showing

1. **Check file**: Verify `~/.pangea/communication/chat_history.json` exists
2. **Permissions**: Ensure the directory is readable/writable
3. **Format**: Ensure the JSON is valid

## Future Enhancements

- [ ] RPC methods for chat history retrieval (currently reads from file)
- [ ] End-to-end encryption for messages
- [ ] Message delivery receipts
- [ ] Typing indicators
- [ ] Group chat support
