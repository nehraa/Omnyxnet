#!/usr/bin/env python3
"""
DEPRECATED: This file uses direct Python networking which violates the Golden Rule.

The Golden Rule:
  - Go: All networking (libp2p, TCP, UDP)
  - Rust: Files, memory, CES pipeline  
  - Python: AI and CLI management

This file is kept as a REFERENCE ONLY for understanding the UDP video streaming protocol.
For actual P2P video streaming, use the Go-based communication service:

    # Start Go node with libp2p (auto-discovers peers via mDNS)
    ./go/bin/go-node -node-id 1 -libp2p -local
    
    # Use Python CLI for high-level management
    python main.py video start
    python main.py video stop

This file shows legacy UDP-based video streaming for reference only.

See docs/COMMUNICATION.md for full documentation.
"""

import cv2
import asyncio
import struct
import numpy as np
import sys
import time
import socket
from queue import Queue, Empty

# Global state
received_frames = Queue(maxsize=30)
local_frames = Queue(maxsize=30)
running = True

# UDP settings
UDP_PORT = 9996
MAX_DGRAM_SIZE = 65000  # Max UDP payload (leave room for headers)
MAX_FRAME_SIZE = 10 * 1024 * 1024  # 10MB limit

# Target resolution
TARGET_WIDTH = 640
TARGET_HEIGHT = 480


class DynamicFrameRateAdapter:
    """Dynamically adjust frame rate and quality based on network conditions."""
    
    def __init__(self):
        self.jpeg_quality = 60
        self.frame_skip = 0
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
            print(f"[UDP Adapter] BW: {bandwidth_mbps:.2f} Mbps → Quality: {self.jpeg_quality} | Skip: {self.frame_skip}")
    
    def should_send_frame(self, frame_count):
        """Determine if this frame should be sent based on skip rate."""
        return (frame_count % (self.frame_skip + 1)) == 0
    
    def get_jpeg_quality(self):
        """Get current JPEG quality setting."""
        return self.jpeg_quality


async def receiver_task(sock, peer_addr=None):
    """Receive video frames via UDP."""
    global running
    frame_count = 0
    start_time = time.time()
    frame_buffer = {}  # Buffer for multi-packet frames
    
    print("📺 UDP Receiver started")
    
    loop = asyncio.get_event_loop()
    
    try:
        while running:
            try:
                # Non-blocking receive
                data, addr = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: sock.recvfrom(MAX_DGRAM_SIZE + 100)),
                    timeout=0.5
                )
                
                if len(data) < 16:
                    continue
                
                # Parse header: frame_id (4) + total_packets (4) + packet_num (4) + data_size (4)
                frame_id, total_packets, packet_num, data_size = struct.unpack('>IIII', data[:16])
                packet_data = data[16:]
                
                # Initialize frame buffer if new frame
                if frame_id not in frame_buffer:
                    frame_buffer[frame_id] = {
                        'packets': {},
                        'total': total_packets,
                        'timestamp': time.time()
                    }
                
                # Store packet
                frame_buffer[frame_id]['packets'][packet_num] = packet_data
                
                # Check if frame is complete
                if len(frame_buffer[frame_id]['packets']) == total_packets:
                    # Reassemble frame
                    frame_data = b''
                    for i in range(total_packets):
                        if i in frame_buffer[frame_id]['packets']:
                            frame_data += frame_buffer[frame_id]['packets'][i]
                    
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
                                print(f"[UDP Receiver] {frame_count} frames | FPS: {fps:.1f}")
                    except Exception as e:
                        pass
                    
                    # Remove completed frame
                    del frame_buffer[frame_id]
                
                # Clean old incomplete frames (older than 1 second)
                current_time = time.time()
                old_frames = [fid for fid, fdata in frame_buffer.items() 
                              if current_time - fdata['timestamp'] > 1.0]
                for fid in old_frames:
                    del frame_buffer[fid]
                    
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                if running:
                    await asyncio.sleep(0.01)
    
    except Exception as e:
        if running:
            print(f"[Receiver] Fatal: {e}")
    finally:
        elapsed = time.time() - start_time
        fps = frame_count / elapsed if elapsed > 0 else 0
        print(f"📺 UDP Receiver stopped. {frame_count} frames at {fps:.1f} FPS")


async def sender_task(sock, peer_addr):
    """Capture video and send via UDP."""
    global running
    frame_count = 0
    print("📹 UDP Sender started")
    adapter = DynamicFrameRateAdapter()
    cap = None
    start_time = time.time()
    
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ Could not open webcam")
            running = False
            return
        
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, TARGET_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, TARGET_HEIGHT)
        cap.set(cv2.CAP_PROP_FPS, 30)
        cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
        
        actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        needs_resize = (actual_width != TARGET_WIDTH or actual_height != TARGET_HEIGHT)
        
        if needs_resize:
            print(f"📷 Camera provides {actual_width}x{actual_height}, will resize to {TARGET_WIDTH}x{TARGET_HEIGHT}")
        
        frame_times = []
        
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
                display_frame = frame.copy()
                h, w = display_frame.shape[:2]
                if w > 1280 or h > 720:
                    scale = min(1280 / w, 720 / h)
                    display_frame = cv2.resize(display_frame, (int(w * scale), int(h * scale)))
                local_frames.put_nowait(display_frame)
            except:
                try:
                    local_frames.get_nowait()
                    local_frames.put_nowait(display_frame)
                except:
                    pass
            
            # Resize for sending if needed
            if needs_resize:
                send_frame = cv2.resize(frame, (TARGET_WIDTH, TARGET_HEIGHT))
            else:
                send_frame = frame
            
            # Encode and send
            if adapter.should_send_frame(frame_count):
                try:
                    send_start = time.time()
                    _, encoded = cv2.imencode('.jpg', send_frame, [cv2.IMWRITE_JPEG_QUALITY, adapter.get_jpeg_quality()])
                    frame_data = encoded.tobytes()
                    
                    # Split into UDP packets
                    total_packets = (len(frame_data) + MAX_DGRAM_SIZE - 1) // MAX_DGRAM_SIZE
                    
                    for packet_num in range(total_packets):
                        start_idx = packet_num * MAX_DGRAM_SIZE
                        end_idx = min(start_idx + MAX_DGRAM_SIZE, len(frame_data))
                        packet_data = frame_data[start_idx:end_idx]
                        
                        # Header: frame_id (4) + total_packets (4) + packet_num (4) + data_size (4)
                        header = struct.pack('>IIII', frame_count, total_packets, packet_num, len(packet_data))
                        packet = header + packet_data
                        
                        sock.sendto(packet, peer_addr)
                    
                    send_duration = time.time() - send_start
                    adapter.record_send(len(frame_data), send_duration)
                    
                    if adapter.should_adjust():
                        bw = adapter.estimate_bandwidth_mbps()
                        adapter.adjust_for_bandwidth(bw)
                    
                    frame_count += 1
                    
                    if frame_count % 100 == 0:
                        elapsed = time.time() - start_time
                        total_fps = frame_count / elapsed if elapsed > 0 else 0
                        print(f"[UDP Sender] {frame_count} frames | FPS: {total_fps:.1f} | Quality: {adapter.get_jpeg_quality()}")
                    
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
        print(f"📹 UDP Sender stopped. {frame_count} frames at {fps:.1f} FPS")
        if cap:
            cap.release()


async def display_frames():
    """Display local and received video frames."""
    global running
    
    print("\n🎥 UDP Video streaming active! Press 'q' to end.\n")
    
    try:
        while running:
            # Display local camera
            try:
                local_frame = local_frames.get_nowait()
                cv2.imshow('Local Camera (UDP)', local_frame)
            except Empty:
                pass
            
            # Display received
            try:
                recv_frame = received_frames.get_nowait()
                cv2.imshow('Peer Video (UDP)', recv_frame)
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
        print("🎥 UDP Video call ended")


async def main():
    global running
    
    is_server = sys.argv[1].lower() == 'true' if len(sys.argv) > 1 else False
    peer_ip = sys.argv[2] if len(sys.argv) > 2 else ""
    port = UDP_PORT
    
    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setblocking(False)
    
    try:
        if is_server:
            # Server mode: Bind and wait for first packet to get peer address
            sock.bind(('0.0.0.0', port))
            print(f"🟢 UDP Server listening on port {port}...")
            print("   Waiting for peer to connect...")
            
            # Start display task
            display_task = asyncio.create_task(display_frames())
            
            # Wait for first packet to discover peer
            loop = asyncio.get_event_loop()
            peer_addr = None
            while running and peer_addr is None:
                try:
                    data, peer_addr = await asyncio.wait_for(
                        loop.run_in_executor(None, lambda: sock.recvfrom(MAX_DGRAM_SIZE + 100)),
                        timeout=1.0
                    )
                    print(f"✅ Peer connected from {peer_addr[0]}:{peer_addr[1]}")
                except asyncio.TimeoutError:
                    continue
            
            if peer_addr:
                # Start sender and receiver
                sender = asyncio.create_task(sender_task(sock, peer_addr))
                receiver = asyncio.create_task(receiver_task(sock, peer_addr))
                
                await asyncio.gather(sender, receiver, display_task, return_exceptions=True)
            
        else:
            # Client mode: Connect to peer
            if not peer_ip:
                print("❌ No peer IP provided")
                print("Usage:")
                print("  Server: python3 live_video_udp.py true")
                print("  Client: python3 live_video_udp.py false <server-ip>")
                running = False
                return
            
            sock.bind(('0.0.0.0', 0))  # Bind to any available port
            peer_addr = (peer_ip, port)
            
            print(f"🔗 UDP Client connecting to {peer_ip}:{port}...")
            
            # Send initial packet to establish connection
            sock.sendto(b'HELLO', peer_addr)
            print("✅ UDP Connected")
            
            # Start display task
            display_task = asyncio.create_task(display_frames())
            
            # Start sender and receiver
            sender = asyncio.create_task(sender_task(sock, peer_addr))
            receiver = asyncio.create_task(receiver_task(sock, peer_addr))
            
            await asyncio.gather(sender, receiver, display_task, return_exceptions=True)
        
    except KeyboardInterrupt:
        print("\n[Main] Interrupted")
    finally:
        running = False
        sock.close()
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
