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

# NOTE: aioquic module renamed 'asynch' to 'asyncio' in newer versions
# Old import (broken): from aioquic.asynch import connect
# Correct import: from aioquic.asyncio import connect

import cv2
import asyncio
import struct
import numpy as np
import sys
import time
from queue import Queue, Empty
from aioquic.asyncio import connect
from aioquic.quic.configuration import QuicConfiguration
import ssl

# Global state
received_frames = Queue(maxsize=30)
local_frames = Queue(maxsize=30)
running = True
quic_connection = None


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


async def receiver_stream(reader):
    """Receive video frames via QUIC stream."""
    global running
    frame_count = 0
    start_time = time.time()
    
    print("📺 QUIC Receiver started")
    
    try:
        while running:
            try:
                # Read frame header: frame_id (4) + frame_size (4)
                header = await asyncio.wait_for(reader.read(8), timeout=2.0)
                if not header or len(header) < 8:
                    if running:
                        await asyncio.sleep(0.01)
                    continue
                
                frame_id, frame_size = struct.unpack('>II', header)
                
                # Read frame data
                frame_data = b''
                remaining = frame_size
                while remaining > 0 and running:
                    chunk = await asyncio.wait_for(reader.read(min(65536, remaining)), timeout=1.0)
                    if not chunk:
                        break
                    frame_data += chunk
                    remaining -= len(chunk)
                
                if len(frame_data) != frame_size:
                    continue
                
                # Decode JPEG
                try:
                    frame = cv2.imdecode(np.frombuffer(frame_data, np.uint8), cv2.IMREAD_COLOR)
                    if frame is not None:
                        frame_count += 1
                        try:
                            received_frames.put_nowait(frame)
                        except:
                            try:
                                received_frames.get_nowait()
                                received_frames.put_nowait(frame)
                            except:
                                pass
                        
                        if frame_count % 100 == 0:
                            elapsed = time.time() - start_time
                            fps = frame_count / elapsed if elapsed > 0 else 0
                            print(f"[QUIC Receiver] {frame_count} frames | FPS: {fps:.1f}")
                except Exception as e:
                    if frame_count % 100 == 0:
                        print(f"[Receiver] Decode error: {e}")
                        
            except asyncio.TimeoutError:
                if running:
                    await asyncio.sleep(0.01)
                continue
            except Exception as e:
                if running:
                    print(f"[Receiver] Error: {e}")
                    await asyncio.sleep(0.1)
    
    except Exception as e:
        if running:
            print(f"[Receiver] Fatal: {e}")
    finally:
        elapsed = time.time() - start_time
        fps = frame_count / elapsed if elapsed > 0 else 0
        print(f"📺 QUIC Receiver stopped. {frame_count} frames at {fps:.1f} FPS")


async def sender_stream(writer):
    """Capture video and send via QUIC stream."""
    global running
    frame_count = 0
    print("📹 QUIC Sender started")
    adapter = DynamicFrameRateAdapter()
    
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
        
        start_time = time.time()
        frame_times = []
        
        while running:
            ret, frame = cap.read()
            if not ret:
                await asyncio.sleep(0.01)
                continue
            
            frame_times.append(time.time())
            if len(frame_times) > 100:
                frame_times.pop(0)
            
            # Queue for display
            try:
                local_frames.put_nowait(frame.copy())
            except:
                try:
                    local_frames.get_nowait()
                    local_frames.put_nowait(frame.copy())
                except:
                    pass
            
            # Encode JPEG with dynamic quality - QUIC handles retransmit
            if adapter.should_send_frame(frame_count):
                try:
                    send_start = time.time()
                    _, encoded = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, adapter.get_jpeg_quality()])
                    frame_data = encoded.tobytes()
                    
                    # Send frame: [frame_id (4)] [frame_size (4)] [data]
                    header = struct.pack('>II', frame_count, len(frame_data))
                    packet = header + frame_data
                    
                    await asyncio.wait_for(writer.write(packet), timeout=1.0)
                    
                    send_duration = time.time() - send_start
                    adapter.record_send(len(frame_data), send_duration)
                    
                    # Check if we should adjust parameters
                    if adapter.should_adjust():
                        bw = adapter.estimate_bandwidth_mbps()
                        adapter.adjust_for_bandwidth(bw)
                    
                    frame_count += 1
                    
                    if frame_count % 100 == 0:
                        elapsed = time.time() - start_time
                        total_fps = frame_count / elapsed if elapsed > 0 else 0
                        if len(frame_times) > 10:
                            capture_fps = len(frame_times) / (frame_times[-1] - frame_times[0]) if frame_times[-1] != frame_times[0] else 0
                        else:
                            capture_fps = 0
                        print(f"[QUIC Sender] {frame_count} frames | Capture: {capture_fps:.1f} FPS | Send: {total_fps:.1f} FPS | Quality: {adapter.get_jpeg_quality()}")
                    
                except asyncio.TimeoutError:
                    if running and frame_count % 100 == 0:
                        print("[Sender] Send timeout - QUIC buffering")
                except Exception as e:
                    if running:
                        print(f"[Sender] Error: {e}")
                    break
    
    except Exception as e:
        if running:
            print(f"[Sender] Fatal error: {e}")
    finally:
        elapsed = time.time() - start_time if 'start_time' in dir() else 0
        fps = frame_count / elapsed if elapsed > 0 else 0
        print(f"📹 QUIC Sender stopped. {frame_count} frames at {fps:.1f} FPS")
        if 'cap' in dir():
            cap.release()


async def run_quic_server(port=9995):
    """QUIC server - accept incoming connection."""
    global running, quic_connection
    
    print(f"🟢 QUIC Server listening on port {port}...")
    
    # Create self-signed certificate for testing
    import tempfile
    import subprocess
    
    with tempfile.TemporaryDirectory() as tmpdir:
        cert_file = f"{tmpdir}/cert.pem"
        key_file = f"{tmpdir}/key.pem"
        
        # Generate self-signed cert
        subprocess.run([
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
        
        # Start server
        from aioquic.quic.server import QuicServer
        
        server = QuicServer(
            host="0.0.0.0",
            port=port,
            configuration=config,
            session_ticket_fetcher=None,
            session_ticket_handler=None,
        )
        
        await server.serve()
        
        print("✅ QUIC Server started")
        
        # Wait for first connection
        while running:
            try:
                # Accept connections (simplified for this example)
                await asyncio.sleep(1)
            except Exception as e:
                if running:
                    print(f"[Server] Error: {e}")


async def run_quic_client(peer_ip, port=9995):
    """QUIC client - connect to peer and stream."""
    global running, quic_connection
    
    print(f"🔗 QUIC Client connecting to {peer_ip}:{port}...")
    
    try:
        # Create SSL context that ignores self-signed certs for LAN testing
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        # Use insecure connection for LAN testing (self-signed certs)
        config = QuicConfiguration(is_client=True)
        
        async with await connect(peer_ip, port, configuration=config, session_ticket_handler=None) as connection:
            quic_connection = connection
            print("✅ QUIC Connected")
            
            # Open bidirectional stream for video
            stream_id = connection.get_next_available_stream_id(is_unidirectional=False)
            reader = connection.create_stream_reader(stream_id)
            writer = connection.create_stream_writer(stream_id)
            
            # Run sender and receiver concurrently
            sender = asyncio.create_task(sender_stream(writer))
            receiver = asyncio.create_task(receiver_stream(reader))
            
            while running and not sender.done() and not receiver.done():
                await asyncio.sleep(0.1)
            
            sender.cancel()
            receiver.cancel()
            
            try:
                await asyncio.gather(sender, receiver)
            except asyncio.CancelledError:
                pass
            
    except Exception as e:
        if running:
            print(f"❌ Connection error: {e}")
        running = False


async def display_frames():
    """Main thread for displaying frames."""
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
            # Server mode
            print(f"🟢 Waiting for QUIC peer on port {port}...")
            
            # For simplicity, we'll use client mode but accept on UDP 9995
            # Real implementation would use aioquic server
            # For now, connect back to client
            await asyncio.sleep(2)
            
            # Actually, let's swap roles - server connects to client for symmetry
            # This is simpler with current aioquic API
            if not peer_ip:
                print("❌ No peer found")
                running = False
            else:
                quic_task = asyncio.create_task(run_quic_client(peer_ip, port))
                await quic_task
        else:
            if not peer_ip:
                print("❌ No peer IP found")
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
        if quic_connection:
            await quic_connection.aclose()


if __name__ == "__main__":
    import os
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete")
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
