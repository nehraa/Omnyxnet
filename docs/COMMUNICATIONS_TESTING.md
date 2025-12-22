# Communications Testing Guide

This guide explains how to test the communications features (chat, video, voice) and DCDN video streaming in the Pangea Net desktop application.

## Overview

The desktop application now includes comprehensive communications testing features:

- **Chat Messaging**: Text-based peer-to-peer communication
- **Video Calls**: Live video streaming between peers
- **Voice Calls**: Real-time audio communication
- **DCDN Video Streaming**: Distributed video streaming with packet recovery
- **Tor Integration**: Optional routing through Tor for privacy testing

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Testing Chat](#testing-chat)
3. [Testing Video Calls](#testing-video-calls)
4. [Testing Voice Calls](#testing-voice-calls)
5. [Testing DCDN Video Streaming](#testing-dcdn-video-streaming)
6. [Testing Tor Integration](#testing-tor-integration)
7. [IP Address Verification](#ip-address-verification)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software

1. **Python 3.8+**
2. **Desktop Application**
   - Kivy (for desktop/desktop_app_kivy.py): `pip install kivy kivymd`
   - OR Tkinter (for desktop/desktop_app.py): Usually included with Python

3. **Communication Dependencies**
   - For video: `pip install opencv-python numpy`
   - For voice: `pip install sounddevice` or `pip install pyaudio`

4. **Optional: Tor**
   - Tor Browser or tor service for privacy testing
   - Default SOCKS5 proxy: 127.0.0.1:9050

### Network Setup

- Ensure devices are on the same network or can reach each other via IP
- Configure firewall to allow connections on required ports:
  - Chat: Port 9999
  - Video: Port 9997
  - Voice: Port 9998
  - DCDN: Uses Go node ports (configurable)

## Testing Chat

### Using the Desktop App

1. **Launch the desktop application**:
   ```bash
   python desktop/desktop_app_kivy.py
   # OR
   python desktop/desktop_app.py
   ```

2. **Navigate to the Communications tab**

3. **On Device A (Server)**:
   - Enter "server" in the Peer IP field
   - Click "Start Chat"
   - Wait for connection

4. **On Device B (Client)**:
   - Enter Device A's IP address (e.g., "192.168.1.100")
   - Click "Start Chat"
   - Type messages in the message field
   - Click "Send Message"

5. **Verify**:
   - Messages appear on both sides
   - Sender IP is displayed
   - Tor indicator shows if enabled

### Using Command Line

1. **On Device A (Server)**:
   ```bash
   python python/src/communication/live_chat.py true
   ```

2. **On Device B (Client)**:
   ```bash
   python python/src/communication/live_chat.py false 192.168.1.100
   ```

3. Type messages and press Enter to send

## Testing Video Calls

### Using the Desktop App

1. **On Device A (Server)**:
   - Navigate to Communications tab
   - Enter "server" in Video Call peer IP field
   - Click "Start Video"

2. **On Device B (Client)**:
   - Enter Device A's IP address
   - Click "Start Video"

3. **Verify**:
   - Both devices show local and remote video feeds
   - Peer IP address is displayed
   - Frame rate and quality are acceptable

### Using Command Line

1. **On Device A (Server)**:
   ```bash
   python python/src/communication/live_video.py true
   ```

2. **On Device B (Client)**:
   ```bash
   python python/src/communication/live_video.py false 192.168.1.100
   ```

3. Press 'q' to quit

### Features

- **Adaptive Quality**: Automatically adjusts quality based on bandwidth
- **Dynamic Frame Rate**: Adapts to network conditions
- **Large Frame Support**: Handles high-resolution cameras
- **Statistics**: Shows FPS, bandwidth usage, frame sizes

## Testing Voice Calls

### Using the Desktop App

1. **On Device A (Server)**:
   - Navigate to Communications tab
   - Enter "server" in Voice Call peer IP field
   - Click "Start Voice"

2. **On Device B (Client)**:
   - Enter Device A's IP address
   - Click "Start Voice"

3. **Verify**:
   - Audio is transmitted both ways
   - Latency is acceptable
   - No significant audio dropouts

### Using Command Line

1. **On Device A (Server)**:
   ```bash
   python python/src/communication/live_voice.py true
   ```

2. **On Device B (Client)**:
   ```bash
   python python/src/communication/live_voice.py false 192.168.1.100
   ```

3. Press Ctrl+C to quit

### Audio Settings

- Sample Rate: 48kHz (Opus-compatible)
- Channels: Mono
- Chunk Size: 960 samples (20ms at 48kHz)

## Testing DCDN Video Streaming

DCDN (Distributed CDN) provides advanced video streaming with:
- QUIC transport for low latency
- Reed-Solomon FEC for packet recovery
- P2P bandwidth allocation
- Ed25519 signature verification

### Generate Test Video

First, create a test video:

```bash
python tools/generate_test_video.py test_video.mp4 10
```

Options:
- Duration: 10 seconds (customizable)
- FPS: 30 (customizable with --fps)
- Resolution: 640x480 (customizable with --width --height)

### Using the Desktop App

1. **Navigate to DCDN tab**

2. **Select Video File**:
   - Click "Browse" to select test_video.mp4
   - OR click "Test Video" to verify file

3. **On Device A (Receiver)**:
   - Enter "server" in Stream Peer IP field
   - Click "Start Stream"

4. **On Device B (Sender)**:
   - Enter Device A's IP address
   - Click "Start Stream"

5. **Verify**:
   - Video plays on receiver device
   - Stream statistics show packet transmission
   - Packet recovery occurs (if packets are lost)
   - Peer IP addresses are displayed

### Run DCDN Demo

To see DCDN system in action without full streaming:

```bash
cd rust
cargo run --example dcdn_demo
```

This demonstrates:
- ChunkStore with ring buffer
- FEC encoding and recovery
- P2P bandwidth allocation
- Signature verification

### Run DCDN Tests

```bash
cd rust
cargo test --test test_dcdn
```

## Testing Tor Integration

### Setup Tor

1. **Install Tor**:
   - Download Tor Browser: https://www.torproject.org
   - OR install tor service: `sudo apt install tor` (Linux)

2. **Start Tor**:
   - Launch Tor Browser
   - OR start service: `sudo systemctl start tor`

3. **Verify Tor is Running**:
   - Check SOCKS5 proxy on 127.0.0.1:9050

### Test with Desktop App

1. **Navigate to Communications tab**

2. **Enable Tor**:
   - Toggle the "Use Tor Proxy" switch to ON

3. **Test Tor Connection**:
   - Click "Test Tor" button
   - Verify proxy is reachable

4. **Check IP Address**:
   - Click "Show My IP" button
   - Note your public IP address
   - Enable Tor and check again (should show Tor exit node IP)

5. **Use Communications with Tor**:
   - Start chat, video, or voice with Tor enabled
   - Verify connection works through Tor
   - Note: Performance may be slower through Tor

### Verify Tor Usage

When receiving messages or connections, check the displayed IP address:
- **Without Tor**: Shows peer's actual IP
- **With Tor**: Shows Tor exit node IP

This confirms that traffic is being routed through Tor.

## IP Address Verification

The application displays IP addresses to help verify connectivity and Tor usage:

### In Desktop App

- **Communications Tab**:
  - "Show My IP" displays your local and public IP
  - Chat/Video/Voice sessions show peer IP in output

- **Network Info Tab**:
  - Shows multiaddrs with complete IP information
  - Displays peer connection details

### Expected IP Formats

- **Local Network**: 192.168.x.x, 10.x.x.x
- **Public IP**: Standard IPv4/IPv6 address
- **Tor Exit Node**: Different IP, often from another country

## Troubleshooting

### Chat Issues

**Problem**: Cannot connect to peer
- **Solution**: Verify IP address is correct
- Check firewall allows port 9999
- Ensure "server" mode is running first

**Problem**: Messages not displaying
- **Solution**: Check network connectivity
- Verify both peers are connected
- Restart chat session

### Video Issues

**Problem**: No video feed
- **Solution**: Check webcam permissions
- Verify opencv-python is installed: `pip install opencv-python`
- Test webcam: `python -c "import cv2; cap = cv2.VideoCapture(0); print('OK' if cap.isOpened() else 'FAIL')"`

**Problem**: Poor video quality
- **Solution**: Check network bandwidth
- Reduce resolution in video settings
- Close other bandwidth-intensive applications

**Problem**: High latency
- **Solution**: Reduce frame rate
- Use wired connection instead of WiFi
- Check for network congestion

### Voice Issues

**Problem**: No audio
- **Solution**: Check microphone/speaker permissions
- Verify audio library: `pip install sounddevice` or `pip install pyaudio`
- Test audio: `python -c "import sounddevice as sd; print(sd.query_devices())"`

**Problem**: Audio choppy/laggy
- **Solution**: Check network latency
- Close other audio applications
- Verify sample rate compatibility

### DCDN Issues

**Problem**: Test video not playing
- **Solution**: Verify video file exists and is valid
- Click "Test Video" to check file properties
- Regenerate test video: `python tools/generate_test_video.py test_video.mp4 10`

**Problem**: DCDN demo fails
- **Solution**: Ensure Rust toolchain is installed
- Build Rust components: `cd rust && cargo build`
- Check Rust examples: `cargo run --example dcdn_demo`

### Tor Issues

**Problem**: Cannot connect to Tor
- **Solution**: Verify Tor is running
- Check SOCKS5 proxy: `curl --socks5 127.0.0.1:9050 https://check.torproject.org`
- Restart Tor service

**Problem**: Tor very slow
- **Solution**: This is expected - Tor adds latency
- For testing, use without Tor first
- Try different Tor exit nodes

## Important Notes

### Reference Implementation

The chat, video, and voice modules are **reference implementations** for testing. They currently use direct Python networking which violates the project's "Golden Rule":

- **Golden Rule**: Go handles all networking (libp2p), Rust handles files/memory, Python handles AI/CLI

### Production Implementation

For production use, these features should be integrated through:
1. Go node's libp2p networking
2. Cap'n Proto RPC for control
3. DCDN system for video streaming

The current reference implementations are kept as:
- Educational examples
- Testing/demonstration tools
- Protocol references

### Future Enhancements

Planned improvements include:
- Full libp2p integration for all communications
- Video streaming through DCDN system
- Tor integration at the Go networking layer
- Multi-peer streaming support
- Advanced quality adaptation
- Network metrics and monitoring

## Related Documentation

- [DCDN Design Specification](../dcdn_design_spec.txt)
- [Communication Modules](../python/src/communication/)
- [Desktop Application Guide](../desktop/desktop_app_kivy.py)
- [Network Connection Guide](NETWORK_CONNECTION.md)
- [Testing Documentation](testing/TESTING_INDEX.md)

## Feedback

If you encounter issues or have suggestions for improving communications testing, please:
1. Check this guide for solutions
2. Review existing issues on GitHub
3. Open a new issue with details about your setup and the problem
