# Desktop App Communication Features - User Guide

## Overview
This guide explains how to use the video, audio, and chat features in the Pangea Net desktop application.

## Important: Peer-to-Peer Setup Requirements

**CRITICAL**: All communication features (video, audio, chat) require **BOTH devices** to have the service running before they can connect to each other.

### Why Both Devices Need the Service Running

The desktop app uses a peer-to-peer (P2P) architecture where:
1. Each device acts as both a **server** (listening for connections) and a **client** (connecting to peers)
2. When you click "Start Video/Audio/Chat", your device starts **listening** on a specific port
3. You then need to **connect** to your peer's IP address
4. **The peer must ALSO be listening** for the connection to succeed

## Step-by-Step Setup Guide

### Prerequisites
1. Both devices must be on the same network (or have proper port forwarding configured)
2. Firewall must allow the following ports:
   - **Port 9996**: Video streaming
   - **Port 9998**: Audio streaming
   - **Port 9999**: Chat messaging
3. Both devices must have the desktop app running and connected to a Go node

### How to Find Your IP Address
1. In the desktop app, go to the **Communications** tab
2. Click **"Show My IP"** button
3. Your local IP will be displayed (e.g., 192.168.1.100)
4. Share this IP with the peer device

### Video Call Setup

**Device A Steps:**
1. Go to **Communications** tab
2. Click **"Start Video Call"** button
3. Enter Device B's IP address in the "Video Peer IP" field
4. Your device is now **listening** on port 9996
5. The app will attempt to connect to Device B

**Device B Steps:**
1. Go to **Communications** tab
2. Click **"Start Video Call"** button
3. Enter Device A's IP address in the "Video Peer IP" field
4. Your device is now **listening** on port 9996
5. The app will attempt to connect to Device A

**Result:** Both devices should connect and start streaming video to each other.

### Chat Setup

**Device A Steps:**
1. Go to **Communications** tab
2. Click **"Start Chat"** button
3. Enter Device B's IP address in the "Chat Peer IP" field
4. Your device is now **listening** on port 9999

**Device B Steps:**
1. Go to **Communications** tab
2. Click **"Start Chat"** button
3. Enter Device A's IP address in the "Chat Peer IP" field
4. Your device is now **listening** on port 9999

**Result:** Both devices should connect. Type messages and click "Send Message" to chat.

### Voice Call Setup

**Device A Steps:**
1. Go to **Communications** tab
2. Click **"Start Voice Call"** button
3. Enter Device B's IP address in the "Voice Peer IP" field
4. Your device is now **listening** on port 9998

**Device B Steps:**
1. Go to **Communications** tab
2. Click **"Start Voice Call"** button
3. Enter Device A's IP address in the "Voice Peer IP" field
4. Your device is now **listening** on port 9998

**Result:** Both devices should connect and start streaming audio.

## Troubleshooting

### "Connection Refused" Error
This error means the peer device is **NOT listening** on the expected port.

**Solutions:**
1. Verify the peer has clicked "Start Video/Audio/Chat" to begin listening
2. Verify the IP address is correct (use "Show My IP" on peer device)
3. Check that no firewall is blocking the port
4. Ensure both devices are on the same network

### "Connection Timeout" Error
This error means the peer device cannot be reached.

**Solutions:**
1. Verify the IP address is correct
2. Check network connectivity (can you ping the peer?)
3. Verify no firewall is blocking the connection
4. Ensure both devices are on the same local network

### Chat Message Error: "struct has no such member; name = message_"
This error has been **FIXED** in this release. Update to the latest version.

### IP Shows "127.0.0.1" Instead of Real IP
This issue has been **FIXED** in this release. The app now uses robust IP detection to show your actual local network IP address.

## Fixes Included in This Release

### 1. Chat Message Schema Fix
- **Problem**: Chat messages failed with Cap'n Proto error about missing field
- **Cause**: Python client was using wrong field name (`message_` instead of `message`)
- **Fix**: Corrected field name in `python/src/client/go_client.py`
- **Impact**: Chat messaging now works correctly

### 2. IP Detection Improvements
- **Problem**: IP address showed "127.0.0.1" instead of actual local IP
- **Cause**: Using `socket.gethostbyname(hostname)` which often returns localhost
- **Fix**: Implemented robust UDP-based IP detection in `_detect_local_ip()`
- **Impact**: "Show My IP" now displays the correct local network IP

### 3. Multiaddr IP Replacement
- **Problem**: Node multiaddrs showed 0.0.0.0 or 127.0.0.1
- **Fix**: Automatically replace these with detected local IP
- **Impact**: Multiaddrs now show actual reachable IP addresses

### 4. Improved Error Messages
- **Problem**: Connection failures had unclear error messages
- **Fix**: Added detailed setup instructions and troubleshooting steps
- **Impact**: Users now understand they need both devices listening

## Technical Details

### Port Assignments
- **9996**: Video streaming (UDP/TCP hybrid via Go backend)
- **9998**: Audio streaming (UDP/TCP hybrid via Go backend)
- **9999**: Chat messaging (TCP via Go backend)

### Data Flow
1. Python GUI → Cap'n Proto RPC → Go Node Backend
2. Go Node Backend handles all network communication
3. Frames/messages sent via libp2p networking stack
4. Peer receives data through their Go node

### Security Notes
- All communication goes through the Go node's networking layer
- Can be configured to use Tor for anonymity (see Tor checkbox in Communications tab)
- Encryption is handled by the libp2p layer in Go

## Known Limitations

1. **Same Network Requirement**: Currently, both devices must be on the same local network or have proper NAT traversal/port forwarding configured.

2. **One-Way vs Two-Way**: Video streaming is currently optimized for sending your camera to the peer. Receiving peer video requires additional UI components.

3. **No Built-in TURN/STUN**: For connections across different networks, you may need to configure port forwarding or VPN.

## Future Improvements

- Automatic peer discovery via mDNS
- Built-in NAT traversal using TURN/STUN servers
- Video receive UI components
- Group video/audio calls
- File sharing via chat
- Screen sharing capabilities

## Support

If you continue to experience issues:
1. Check the logs in the desktop app's log window
2. Verify both Go nodes are running correctly
3. Test basic network connectivity (ping between devices)
4. Check firewall settings on both devices
5. Review the error messages - they now contain detailed troubleshooting steps

## References

- Main README: `../README.md`
- Go Node Schema: `../go/schema/schema.capnp`
- Python Client: `../python/src/client/go_client.py`
- Desktop App: `../desktop/desktop_app_kivy.py`
