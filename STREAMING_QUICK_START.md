# Voice Streaming Quick Start

**⚡ Get started with voice streaming in 5 minutes**

## Prerequisites

```bash
# Build the project
cd /home/runner/work/WGT/WGT
cd rust && cargo build --release
cd ../go && make build
```

## Run the Demo

```bash
cd rust
cargo run --example voice_streaming_demo --release
```

Expected output:
```
✓ 20.87x compression ratio achieved
✓ Sequence numbers working correctly
✓ Dynamic bitrate adjustment working
🎉 Voice streaming demo completed successfully!
```

## Run the Tests

```bash
cd rust
cargo test --test test_streaming --release
```

Expected output:
```
running 12 tests
test result: ok. 12 passed; 0 failed
```

## Basic Usage

### 1. Create a Streaming Session

```rust
use pangea_ces::{StreamConfig, StreamingSession};

let config = StreamConfig::voice();  // Low-latency voice
let session = StreamingSession::new(config);
```

### 2. Create Sender

```rust
let mut sender = session.create_audio_sender(peer_id)?;
```

### 3. Encode Audio

```rust
// Your PCM samples (16-bit signed integers)
let pcm_samples: Vec<i16> = /* capture from mic */;

// Encode to stream packet
let packet = sender.encode_audio(&pcm_samples)?;
```

### 4. Send Over Network

```rust
// Serialize packet
let bytes = packet.to_bytes()?;

// Send via your network layer (QUIC/UDP)
network.send_message(peer_id, bytes.into()).await?;
```

### 5. Receive and Decode

```rust
// Deserialize received packet
let packet = StreamPacket::from_bytes(&received_bytes)?;

// Create receiver and decode
let mut receiver = session.create_audio_receiver()?;
// Feed packet to receiver via channel...
if let Some(decoded_pcm) = receiver.receive_audio().await? {
    // Play decoded audio
}
```

## Configuration Options

### Voice (Default) - Low Latency
```rust
let config = StreamConfig::voice();
// - 48kHz, Mono, 32 kbps
// - 10ms frames (~5ms total latency)
// - Best for: VoIP, real-time calls
```

### High Quality - Better Audio
```rust
let config = StreamConfig::audio_hq();
// - 48kHz, Stereo, 128 kbps
// - 20ms frames (~9ms total latency)
// - Best for: Music, podcasts
```

### Custom
```rust
use pangea_ces::{StreamConfig, StreamType, AudioConfig};

let config = StreamConfig {
    stream_type: StreamType::Audio,
    audio_config: Some(AudioConfig {
        sample_rate: 48000,
        channels: opus::Channels::Mono,
        bitrate: 64000,
        frame_duration_ms: 20.0,
    }),
    max_packet_size: 1350,
    buffer_size: 100,
    enable_fec: true,
};
```

## Performance

| Config | Latency | Bandwidth | Quality |
|--------|---------|-----------|---------|
| Voice  | ~5ms    | ~40 kbps  | Good    |
| HQ     | ~9ms    | ~136 kbps | Excellent |

## Adjusting Bitrate

```rust
// Start with default (32 kbps for voice)
let mut sender = session.create_audio_sender(peer_id)?;

// Network congested? Reduce bitrate
sender.set_bitrate(16000)?;  // 16 kbps

// Network improved? Increase bitrate
sender.set_bitrate(64000)?;  // 64 kbps
```

## Packet Loss Handling

The receiver automatically handles packet loss:

```rust
// Lost packets are detected via sequence numbers
// PLC (Packet Loss Concealment) generates synthetic audio
// Quality degrades gracefully instead of silence/glitches
```

## Troubleshooting

### High Latency?
```rust
// Use smaller frame duration
let config = StreamConfig::voice();  // 10ms frames
```

### Poor Quality?
```rust
// Increase bitrate
sender.set_bitrate(64000)?;

// Or use HQ config
let config = StreamConfig::audio_hq();
```

### Packet Loss?
```rust
// Enable FEC
let mut config = StreamConfig::voice();
config.enable_fec = true;
```

## Files to Check

- **API Reference:** `docs/STREAMING_GUIDE.md`
- **Implementation:** `rust/src/streaming.rs`
- **Tests:** `rust/tests/test_streaming.rs`
- **Demo:** `rust/examples/voice_streaming_demo.rs`

## Integration with Network

The streaming module is transport-agnostic. To integrate with your network layer:

1. **Sender Side:**
   ```rust
   let packet = sender.encode_audio(&pcm)?;
   let bytes = packet.to_bytes()?;
   network.send_message(peer_id, bytes.into()).await?;
   ```

2. **Receiver Side:**
   ```rust
   let bytes = network.receive_message().await?;
   let packet = StreamPacket::from_bytes(&bytes)?;
   // Feed to receiver...
   ```

## Next Steps

1. Read the full guide: `docs/STREAMING_GUIDE.md`
2. Review the API: `rust/src/streaming.rs`
3. Run the demo: `cargo run --example voice_streaming_demo`
4. Check the tests: `cargo test --test test_streaming`
5. Integrate with your network layer

## Support

For issues or questions:
1. Check `docs/STREAMING_GUIDE.md` (troubleshooting section)
2. Review test cases in `rust/tests/test_streaming.rs`
3. Run the demo for working examples

---

**Status:** ✅ Ready to use  
**Version:** 0.4.0  
**Last Updated:** November 24, 2025
