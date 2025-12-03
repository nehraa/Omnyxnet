#!/usr/bin/env python3
"""
DEPRECATED: This file uses direct Python networking which violates the Golden Rule.

The Golden Rule:
  - Go: All networking (libp2p, TCP, UDP)
  - Rust: Files, memory, CES pipeline  
  - Python: AI and CLI management

This file is kept as a REFERENCE ONLY for understanding the voice streaming protocol.
For actual P2P voice streaming, use the Go-based communication service:

    # Start Go node with libp2p (auto-discovers peers via mDNS)
    ./go/bin/go-node -node-id 1 -libp2p -local
    
    # Use Python CLI for high-level management
    python3 -m main streaming start --type voice

The Go communication service (go/pkg/communication/communication.go) handles:
  - P2P video streaming over libp2p streams
  - P2P audio streaming over libp2p streams
  - P2P chat messaging with history persistence
  - Automatic peer discovery via mDNS

See docs/COMMUNICATION.md for complete documentation.
"""

import socket
import threading
import sys
import struct
import time

try:
    import sounddevice as sd
    import numpy as np
    USE_SD = True
except ImportError:
    try:
        import pyaudio
        USE_SD = False
    except ImportError:
        print("❌ No audio library found. Install sounddevice or pyaudio.")
        sys.exit(1)

# Audio settings (Opus-compatible)
SAMPLE_RATE = 48000
CHANNELS = 1
CHUNK = 960  # 20ms at 48kHz

def audio_receiver(sock):
    """Receive and play audio from peer."""
    if USE_SD:
        stream = sd.OutputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype='int16')
        stream.start()
    else:
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=CHANNELS,
                       rate=SAMPLE_RATE, output=True, frames_per_buffer=CHUNK)

    print("🔊 Audio output started")

    try:
        while True:
            header = sock.recv(4)
            if not header:
                break
            length = struct.unpack('>I', header)[0]
            data = b''
            while len(data) < length:
                chunk = sock.recv(length - len(data))
                if not chunk:
                    break
                data += chunk

            if USE_SD:
                audio = np.frombuffer(data, dtype='int16')
                stream.write(audio)
            else:
                stream.write(data)
    except Exception as e:
        print(f"Receiver stopped: {e}")
    finally:
        if USE_SD:
            stream.stop()
        else:
            stream.stop_stream()
            stream.close()
            p.terminate()

def audio_sender(sock):
    """Capture and send audio to peer."""
    if USE_SD:
        stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS,
                               dtype='int16', blocksize=CHUNK)
        stream.start()
    else:
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=CHANNELS,
                       rate=SAMPLE_RATE, input=True, frames_per_buffer=CHUNK)

    print("🎤 Microphone started - speak now!")

    try:
        while True:
            if USE_SD:
                data, _ = stream.read(CHUNK)
                audio_bytes = data.tobytes()
            else:
                audio_bytes = stream.read(CHUNK)

            sock.send(struct.pack('>I', len(audio_bytes)) + audio_bytes)
    except Exception as e:
        print(f"Sender stopped: {e}")
    finally:
        if USE_SD:
            stream.stop()
        else:
            stream.stop_stream()
            stream.close()
            p.terminate()

def main():
    is_server = sys.argv[1].lower() == 'true' if len(sys.argv) > 1 else False
    peer_ip = sys.argv[2] if len(sys.argv) > 2 else ""
    port = 9998

    # Connect
    if is_server:
        print(f"🟢 Waiting for voice peer on port {port}...")
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(('0.0.0.0', port))
            server.listen(1)
            server.settimeout(60)  # 60 second timeout
            print(f"✅ Listening on 0.0.0.0:{port}")
            sock, addr = server.accept()
            print(f"🔗 Voice peer connected from {addr}")
        except socket.timeout:
            print("❌ Timeout waiting for peer to connect")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Bind/listen failed: {e}")
            sys.exit(1)
    else:
        if not peer_ip:
            print("❌ No peer IP found")
            sys.exit(1)
        print(f"🔗 Connecting to voice peer at {peer_ip}:{port}...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        try:
            sock.connect((peer_ip, port))
            print("✅ Connected!")
        except socket.timeout:
            print(f"❌ Connection timeout after 10s")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            sys.exit(1)

    # Start threads
    sender_thread = threading.Thread(target=audio_sender, args=(sock,), daemon=True)
    receiver_thread = threading.Thread(target=audio_receiver, args=(sock,), daemon=True)

    sender_thread.start()
    receiver_thread.start()

    print("\n🎤 Voice call active! Press Ctrl+C to end.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Voice call ended]")
    finally:
        sock.close()
        if is_server:
            server.close()

if __name__ == "__main__":
    main()
