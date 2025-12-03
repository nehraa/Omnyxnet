#!/usr/bin/env python3
"""
DEPRECATED: This file uses direct Python networking which violates the Golden Rule.
The Golden Rule: Go handles all networking, Python handles AI and CLI.

Use the new Go-based streaming service instead via Cap'n Proto RPC:
  1. Start Go node: ./go/bin/go-node -node-id 1
  2. Use Python CLI: python3 -m main.py streaming start --type video

This file is kept for reference only. For actual video streaming, the networking
is now handled by Go's streaming.go and exposed via RPC.
"""

import cv2
import asyncio
import struct
import numpy as np
import sys
import time
import os
import tempfile
import subprocess
from queue import Queue, Empty
from aioquic.asyncio.client import connect
from aioquic.asyncio.server import serve
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import StreamDataReceived, HandshakeCompleted

# Global state
received_frames = Queue(maxsize=30)
local_frames = Queue(maxsize=30)
running = True
active_protocol = None
STREAM_ID = 0


class DynamicFrameRateAdapter:
    """Dynamically adjust frame rate and quality based on network conditions."""
    
    def __init__(self):
        self.jpeg_quality = 60
        self.frame_skip = 0
        self.target_fps = 30
        self.send_times = []
        self.last_adjustment = time.time()
        self.adjustment_interval = 2.0
        
    def record_send(self, size_bytes, duration_sec):
        """Record a frame send operation."""
        self.send_times.append({
            'size': size_bytes,
            'time': time.time(),
            'duration': duration_sec
        })
        if len(self.send_times) > 100:
            self.send_times.pop(0)
    
    def estimate_bandwidth_mbps(self):
        """Estimate current bandwidth in Mbps."""
        if len(self.send_times) < 5:
            return None
        
        recent = self.send_times[-10:]
        total_bytes = sum(s['size'] for s in recent)
        total_time = recent[-1]['time'] - recent[0]['time']
        
        if total_time <= 0:
            return None
        
        mbps = (total_bytes * 8) / (total_time * 1_000_000)
        return mbps
    
    def should_adjust(self):
        """Check if it's time to adjust parameters."""
        return (time.time() - self.last_adjustment) > self.adjustment_interval
    
    def adjust_for_bandwidth(self, bandwidth_mbps):
        """Adjust quality and skip rate based on bandwidth."""
        self.last_adjustment = time.time()
        
        if bandwidth_mbps is None:
            return
        
        old_quality = self.jpeg_quality
        old_skip = self.frame_skip
        
        if bandwidth_mbps > 5:
            self.jpeg_quality = 85
            self.frame_skip = 0
        elif bandwidth_mbps > 2:
            self.jpeg_quality = 70
            self.frame_skip = 0
        elif bandwidth_mbps > 1:
            self.jpeg_quality = 50
            self.frame_skip = 1
        elif bandwidth_mbps > 0.5:
            self.jpeg_quality = 40
            self.frame_skip = 2
        else:
            self.jpeg_quality = 30
            self.frame_skip = 3
        
        if old_quality != self.jpeg_quality or old_skip != self.frame_skip:
            print(f"[QUIC Adapter] BW: {bandwidth_mbps:.2f} Mbps → Quality: {self.jpeg_quality} | Skip: {self.frame_skip}")
    
    def should_send_frame(self, frame_count):
        """Determine if this frame should be sent based on skip rate."""
        return (frame_count % (self.frame_skip + 1)) == 0
    
    def get_jpeg_quality(self):
        """Get current JPEG quality setting."""
        return self.jpeg_quality


class VideoStreamProtocol(QuicConnectionProtocol):
    """Custom QUIC protocol for bidirectional video streaming."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.receive_buffer = b''
        self.connected = False
        
    def quic_event_received(self, event):
        global running
        
        if isinstance(event, HandshakeCompleted):
            self.connected = True
            print("✅ QUIC Handshake completed")
            
        elif isinstance(event, StreamDataReceived):
            self.receive_buffer += event.data
            self._process_frames()
    
    def _process_frames(self):
        """Process received frame data from buffer."""
        while len(self.receive_buffer) >= 8:
            # Parse header
            frame_id, frame_size = struct.unpack('>II', self.receive_buffer[:8])
            
            # Check if we have complete frame
            total_size = 8 + frame_size
            if len(self.receive_buffer) < total_size:
                break
            
            # Extract frame data
            frame_data = self.receive_buffer[8:total_size]
            self.receive_buffer = self.receive_buffer[total_size:]
            
            # Decode JPEG
            try:
                frame = cv2.imdecode(np.frombuffer(frame_data, np.uint8), cv2.IMREAD_COLOR)
                if frame is not None:
                    try:
                        received_frames.put_nowait(frame)
                    except:
                        try:
                            received_frames.get_nowait()
                            received_frames.put_nowait(frame)
                        except:
                            pass
            except Exception as e:
                pass
    
    def send_frame(self, frame_id, frame_data):
        """Send a video frame over QUIC stream."""
        header = struct.pack('>II', frame_id, len(frame_data))
        packet = header + frame_data
        self._quic.send_stream_data(STREAM_ID, packet)
        self.transmit()


async def sender_task(protocol):
    """Capture video and send via QUIC."""
    global running
    frame_count = 0
    print("📹 QUIC Sender started")
    adapter = DynamicFrameRateAdapter()
    cap = None
    start_time = time.time()
    
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ Could not open webcam")
            running = False
            return
        
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
        
        frame_times = []
        
        # Wait for connection
        while running and not protocol.connected:
            await asyncio.sleep(0.1)
        
        while running:
            ret, frame = cap.read()
            if not ret:
                await asyncio.sleep(0.01)
                continue
            
            frame_times.append(time.time())
            if len(frame_times) > 100:
                frame_times.pop(0)
            
            # Queue for local display
            try:
                local_frames.put_nowait(frame.copy())
            except:
                try:
                    local_frames.get_nowait()
                    local_frames.put_nowait(frame.copy())
                except:
                    pass
            
            # Encode and send
            if adapter.should_send_frame(frame_count):
                try:
                    send_start = time.time()
                    _, encoded = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, adapter.get_jpeg_quality()])
                    frame_data = encoded.tobytes()
                    
                    protocol.send_frame(frame_count, frame_data)
                    
                    send_duration = time.time() - send_start
                    adapter.record_send(len(frame_data), send_duration)
                    
                    if adapter.should_adjust():
                        bw = adapter.estimate_bandwidth_mbps()
                        adapter.adjust_for_bandwidth(bw)
                    
                    frame_count += 1
                    
                    if frame_count % 100 == 0:
                        elapsed = time.time() - start_time
                        total_fps = frame_count / elapsed if elapsed > 0 else 0
                        print(f"[QUIC Sender] {frame_count} frames | Send: {total_fps:.1f} FPS | Quality: {adapter.get_jpeg_quality()}")
                    
                except Exception as e:
                    if running:
                        print(f"[Sender] Error: {e}")
            
            await asyncio.sleep(0.001)
    
    except Exception as e:
        if running:
            print(f"[Sender] Fatal error: {e}")
    finally:
        elapsed = time.time() - start_time
        fps = frame_count / elapsed if elapsed > 0 else 0
        print(f"📹 QUIC Sender stopped. {frame_count} frames at {fps:.1f} FPS")
        if cap:
            cap.release()


async def run_quic_server(port=9995):
    """QUIC server - listen for incoming connections."""
    global running, active_protocol
    
    print(f"🟢 QUIC Server listening on port {port}...")
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            cert_file = f"{tmpdir}/cert.pem"
            key_file = f"{tmpdir}/key.pem"
            
            # Generate self-signed cert
            result = subprocess.run([
                "openssl", "req", "-x509", "-newkey", "rsa:2048",
                "-keyout", key_file, "-out", cert_file, "-days", "1",
                "-nodes", "-subj", "/CN=localhost"
            ], capture_output=True, check=False)
            
            if not os.path.exists(cert_file):
                print("❌ Failed to generate certificate")
                running = False
                return
            
            # Create QUIC configuration
            config = QuicConfiguration(is_client=False)
            config.load_cert_chain(cert_file, key_file)
            
            def create_protocol():
                global active_protocol
                active_protocol = VideoStreamProtocol(config)
                return active_protocol
            
            # Start server
            server = await serve(
                "0.0.0.0",
                port,
                configuration=config,
                create_protocol=create_protocol,
            )
            
            print("✅ QUIC Server started, waiting for peer connection...")
            
            # Wait for connection
            while running and (active_protocol is None or not active_protocol.connected):
                await asyncio.sleep(0.1)
            
            if active_protocol and active_protocol.connected:
                print("✅ Peer connected!")
                # Start sender task
                sender = asyncio.create_task(sender_task(active_protocol))
                
                while running:
                    await asyncio.sleep(0.1)
                
                sender.cancel()
                try:
                    await sender
                except asyncio.CancelledError:
                    pass
            
            server.close()
    
    except Exception as e:
        if running:
            print(f"[Server] Fatal error: {e}")
            import traceback
            traceback.print_exc()
        running = False


async def run_quic_client(peer_ip, port=9995):
    """QUIC client - connect to peer and stream."""
    global running, active_protocol
    
    print(f"🔗 QUIC Client connecting to {peer_ip}:{port}...")
    
    try:
        # Create QUIC configuration (allow self-signed certs)
        config = QuicConfiguration(is_client=True)
        config.verify_mode = False  # Allow self-signed certs for LAN
        
        def create_protocol():
            global active_protocol
            active_protocol = VideoStreamProtocol(config)
            return active_protocol
        
        async with connect(
            peer_ip,
            port,
            configuration=config,
            create_protocol=create_protocol,
        ) as protocol:
            active_protocol = protocol
            print("✅ QUIC Connected")
            
            # Wait for handshake
            while running and not protocol.connected:
                await asyncio.sleep(0.1)
            
            # Start sender task
            sender = asyncio.create_task(sender_task(protocol))
            
            while running:
                await asyncio.sleep(0.1)
            
            sender.cancel()
            try:
                await sender
            except asyncio.CancelledError:
                pass
            
    except Exception as e:
        if running:
            print(f"❌ Connection error: {e}")
        running = False


async def display_frames():
    """Display local and received video frames."""
    global running
    
    print("\n🎥 QUIC Video streaming active! Press 'q' to end.\n")
    
    try:
        while running:
            # Display local camera
            try:
                local_frame = local_frames.get_nowait()
                cv2.imshow('Local Camera (QUIC)', local_frame)
            except Empty:
                pass
            
            # Display received
            try:
                recv_frame = received_frames.get_nowait()
                cv2.imshow('Peer Video (QUIC)', recv_frame)
            except Empty:
                pass
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("[Main] Quit requested")
                running = False
                break
            
            await asyncio.sleep(0.001)
                
    except KeyboardInterrupt:
        print("\n[Main] Interrupted")
    finally:
        running = False
        cv2.destroyAllWindows()
        print("🎥 QUIC Video call ended")


async def main():
    global running
    
    is_server = sys.argv[1].lower() == 'true' if len(sys.argv) > 1 else False
    peer_ip = sys.argv[2] if len(sys.argv) > 2 else ""
    port = 9995
    
    try:
        # Start display task
        display_task = asyncio.create_task(display_frames())
        
        if is_server:
            # Server mode: Listen for incoming connection
            quic_task = asyncio.create_task(run_quic_server(port))
            await quic_task
        else:
            # Client mode: Connect to peer
            if not peer_ip:
                print("❌ No peer IP provided")
                print("Usage:")
                print("  Server: python3 live_video_quic.py true")
                print("  Client: python3 live_video_quic.py false <server-ip>")
                running = False
            else:
                quic_task = asyncio.create_task(run_quic_client(peer_ip, port))
                await quic_task
        
        await display_task
        
    except KeyboardInterrupt:
        print("\n[Main] Interrupted")
    finally:
        running = False
        await asyncio.sleep(0.5)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete")
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
