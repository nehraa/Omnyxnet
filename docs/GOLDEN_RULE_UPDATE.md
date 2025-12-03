# Golden Rule Implementation Update

**Date:** 2024-12-02  
**Version:** 0.5.0-alpha  
**Status:** ✅ Complete

## Summary

This update implements the **Golden Rule architecture** for streaming and communication:

- **Rust:** Files and memory operations (CES pipeline, caching)
- **Go:** All networking (UDP, TCP, QUIC for video/audio/chat)
- **Python:** AI/ML and high-level management

## Changes Made

### 1. Go Networking Service (streaming.go)

New streaming service in Go that handles all network I/O:

```go
// UDP for video/audio (low latency)
streamingService.StartUDP(9996)

// TCP for chat (reliable)
streamingService.StartTCP(9997)

// Send video frame (Go handles fragmentation for large frames)
streamingService.SendVideoFrame(peerAddr, frameID, data)
```

**Features:**
- Automatic packet fragmentation for high-quality cameras
- Frame reassembly with timeout handling
- Statistics tracking (frames sent/received, bytes, latency)

### 2. Cap'n Proto Schema Updates

Added streaming RPC methods to schema.capnp:

```capnp
# Start streaming service
startStreaming @15 (config :StreamConfig) -> (success :Bool, errorMsg :Text);

# Stop streaming
stopStreaming @16 () -> (success :Bool);

# Send video frame (Go handles UDP)
sendVideoFrame @17 (frame :VideoFrame) -> (success :Bool);

# Send audio chunk (Go handles UDP)
sendAudioChunk @18 (chunk :AudioChunk) -> (success :Bool);

# Send chat message (Go handles TCP)
sendChatMessage @19 (message :ChatMessage) -> (success :Bool);

# Connect to streaming peer
connectStreamPeer @20 (host :Text, port :UInt16) -> (success :Bool, peerAddr :Text);

# Get streaming stats
getStreamStats @21 () -> (stats :StreamStats);
```

### 3. Python CLI Commands

New CLI commands that delegate to Go for networking:

```bash
# Start streaming service
python main.py streaming start --stream-port 9996 --type video

# Connect to peer
python main.py streaming connect-peer 192.168.1.100 9996

# Get statistics
python main.py streaming stats

# Stop streaming
python main.py streaming stop
```

### 4. AI Module Wiring

Added CLI commands to test AI modules (bypass mode):

```bash
# Test translation pipeline
python main.py ai translate-test --no-gpu

# Test lipsync pipeline
python main.py ai lipsync-test

# Test federated learning
python main.py ai federated-test
```

**Note:** These run in placeholder mode without torch. Install torch for full AI features:
```bash
pip install torch>=2.0.0
```

### 5. Fixed Issues

- **aioquic.asynch import error**: Fixed import to use `aioquic.asyncio`
- **"message too long" error**: Go now handles large frames with automatic fragmentation
- **Golden Rule compliance**: All network I/O moved to Go

## Testing

New test script: `tests/test_streaming.sh`

```bash
# Run streaming and AI wiring tests
./tests/test_streaming.sh

# Or via setup.sh (option 17)
./scripts/setup.sh
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Python CLI                           │
│                 (high-level management)                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Cap'n Proto RPC                         │    │
│  └─────────────────────────────────────────────────────┘    │
│                         ↓                                    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │            Go Streaming Service                      │    │
│  │  • UDP: Video/Audio (low latency)                   │    │
│  │  • TCP: Chat (reliable)                              │    │
│  │  • QUIC: Future (multiplexed, 0-RTT)                │    │
│  │  • Fragmentation & reassembly                        │    │
│  │  • Statistics tracking                               │    │
│  └─────────────────────────────────────────────────────┘    │
│                         ↓                                    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Network (UDP/TCP/QUIC)                  │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Files Changed

- `go/streaming.go` - New streaming service
- `go/capnp_service.go` - Added streaming RPC implementations
- `go/main.go` - Fixed test mode polling interval
- `go/schema/schema.capnp` - Added streaming types and methods
- `python/schema.capnp` - Synced with Go schema
- `rust/schema.capnp` - Synced with Go schema
- `python/src/cli.py` - Added streaming and AI commands
- `python/src/client/go_client.py` - Added streaming methods
- `python/src/ai/__init__.py` - Made imports conditional
- `python/live_video_quic.py` - Fixed import, added deprecation notice
- `tests/test_streaming.sh` - New test script
- `tests/test_all.sh` - Added streaming test
- `scripts/setup.sh` - Added streaming test menu option

## Next Steps

1. Test cross-device streaming with real hardware
2. Add QUIC support in Go (currently only UDP/TCP)
3. Integrate AI models with full torch installation
4. Benchmark streaming performance
