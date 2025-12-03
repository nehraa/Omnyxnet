#!/usr/bin/env python3
"""
DEPRECATED: This file uses direct Python networking which violates the Golden Rule.

The Golden Rule:
  - Go: All networking (libp2p, TCP, UDP)
  - Rust: Files, memory, CES pipeline  
  - Python: AI and CLI management

This file is kept as a REFERENCE ONLY for understanding the video streaming protocol.
For actual P2P video streaming, use the Go-based communication service:

    # Start Go node with libp2p (auto-discovers peers via mDNS)
    ./go/bin/go-node -node-id 1 -libp2p -local
    
    # Use Python CLI for high-level management
    python3 -m main streaming start --type video

The Go communication service (go/pkg/communication/communication.go) handles:
  - P2P video streaming over libp2p streams
  - P2P audio streaming over libp2p streams
  - P2P chat messaging with history persistence
  - Automatic peer discovery via mDNS

See docs/COMMUNICATION.md for complete documentation.
"""

import cv2
import socket
import threading
import struct
import numpy as np
import sys
import time
from queue import Queue, Empty

# Global queues for frames
received_frames = Queue(maxsize=30)
local_frames = Queue(maxsize=30)
running = True


class DynamicFrameRateAdapter:
    """Dynamically adjust frame rate and quality based on network conditions."""
    
    def __init__(self):
        self.jpeg_quality = 60  # 0-100
        self.frame_skip = 0  # Skip every Nth frame
        self.target_fps = 30
        self.send_times = []  # Track send times for bandwidth estimation
        self.last_adjustment = time.time()
        self.adjustment_interval = 2.0  # Adjust every 2 seconds
        
    def record_send(self, size_bytes, duration_sec):
        """Record a frame send operation."""
        self.send_times.append({
            'size': size_bytes,
            'time': time.time(),
            'duration': duration_sec
        })
        # Keep last 100 sends
        if len(self.send_times) > 100:
            self.send_times.pop(0)
    
    def estimate_bandwidth_mbps(self):
        """Estimate current bandwidth in Mbps."""
        if len(self.send_times) < 5:
            return None
        
        recent = self.send_times[-10:]  # Last 10 sends
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
        
        # Adapt to bandwidth
        if bandwidth_mbps > 5:  # >5 Mbps: high quality, no skipping
            self.jpeg_quality = 85
            self.frame_skip = 0
        elif bandwidth_mbps > 2:  # 2-5 Mbps: medium quality
            self.jpeg_quality = 70
            self.frame_skip = 0
        elif bandwidth_mbps > 1:  # 1-2 Mbps: lower quality
            self.jpeg_quality = 50
            self.frame_skip = 1  # Send every 2nd frame
        elif bandwidth_mbps > 0.5:  # 0.5-1 Mbps: low quality, skip more
            self.jpeg_quality = 40
            self.frame_skip = 2  # Send every 3rd frame
        else:  # <0.5 Mbps: minimal quality
            self.jpeg_quality = 30
            self.frame_skip = 3  # Send every 4th frame
        
        if old_quality != self.jpeg_quality or old_skip != self.frame_skip:
            print(f"[Adapter] BW: {bandwidth_mbps:.2f} Mbps → Quality: {self.jpeg_quality} | Skip: {self.frame_skip}")
    
    def should_send_frame(self, frame_count):
        """Determine if this frame should be sent based on skip rate."""
        return (frame_count % (self.frame_skip + 1)) == 0
    
    def get_jpeg_quality(self):
        """Get current JPEG quality setting."""
        return self.jpeg_quality


# Maximum frame size limit (10MB should handle even 4K frames)
MAX_FRAME_SIZE = 10 * 1024 * 1024

def receiver_thread(sock):
    """Receive video frames from peer and put them in queue."""
    global running
    frame_count = 0
    start_time = time.time()
    failed_decodes = 0
    print("📺 Receiver thread started")
    
    try:
        while running:
            # Read frame size header (4 bytes)
            header = b''
            header_start = time.time()
            while len(header) < 4 and running:
                try:
                    chunk = sock.recv(4 - len(header))
                    if not chunk:
                        print("[Receiver] Connection closed by peer")
                        return
                    header += chunk
                except socket.timeout:
                    # Check if we've been waiting too long for header
                    if time.time() - header_start > 5.0:
                        print("[Receiver] Timeout waiting for frame header")
                        continue
                    continue
                except Exception as e:
                    if running:
                        print(f"[Receiver] Recv error: {e}")
                    return
            
            if not running:
                break
            
            try:
                length = struct.unpack('>I', header)[0]
            except:
                print("[Receiver] Invalid header")
                break
            
            # Validate frame size - prevent memory issues with corrupted headers
            if length == 0:
                print("[Receiver] Empty frame, skipping")
                continue
            if length > MAX_FRAME_SIZE:
                print(f"[Receiver] Frame too large ({length / 1024 / 1024:.1f}MB), max is {MAX_FRAME_SIZE / 1024 / 1024:.0f}MB - skipping")
                # Try to drain the socket to resync
                try:
                    sock.settimeout(0.1)
                    sock.recv(min(length, 65536))
                    sock.settimeout(1.0)
                except:
                    pass
                continue
            
            # Read frame data with larger buffer for high-quality frames
            data = b''
            recv_start = time.time()
            # Use larger buffer for better performance with large frames
            buffer_size = min(262144, length)  # 256KB chunks for large frames
            
            while len(data) < length and running:
                try:
                    remaining = length - len(data)
                    chunk = sock.recv(min(buffer_size, remaining))
                    if not chunk:
                        print(f"[Receiver] Connection closed mid-frame ({len(data)}/{length} bytes)")
                        return
                    data += chunk
                except socket.timeout:
                    # Check for stalled transfer
                    if time.time() - recv_start > 10.0:
                        print(f"[Receiver] Timeout receiving frame data ({len(data)}/{length} bytes)")
                        break
                    continue
                except Exception as e:
                    if running:
                        print(f"[Receiver] Recv error: {e}")
                    return
            
            if len(data) != length:
                print(f"[Receiver] Incomplete frame: got {len(data)}/{length} bytes")
                continue
            
            if not running:
                break
            
            # Decode frame
            try:
                frame = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
                if frame is not None:
                    frame_count += 1
                    failed_decodes = 0  # Reset on success
                    
                    # Resize very large frames for display to avoid memory issues
                    h, w = frame.shape[:2]
                    if w > 1920 or h > 1080:
                        scale = min(1920 / w, 1080 / h)
                        new_w, new_h = int(w * scale), int(h * scale)
                        frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
                    
                    # Put in queue (drop if full to avoid lag)
                    try:
                        received_frames.put_nowait(frame)
                    except:
                        # Queue full, drop oldest frame
                        try:
                            received_frames.get_nowait()
                            received_frames.put_nowait(frame)
                        except:
                            pass
                    
                    # Print stats every 100 frames
                    if frame_count % 100 == 0:
                        elapsed = time.time() - start_time
                        fps = frame_count / elapsed if elapsed > 0 else 0
                        print(f"[Receiver] {frame_count} frames at {fps:.1f} FPS | Last frame: {len(data)/1024:.1f}KB, {w}x{h}")
                else:
                    failed_decodes += 1
                    if failed_decodes % 10 == 1:
                        print(f"[Receiver] Failed to decode frame (size: {len(data)} bytes)")
            except Exception as e:
                failed_decodes += 1
                if failed_decodes % 10 == 1:
                    print(f"[Receiver] Decode error: {e}")
    except Exception as e:
        if running:
            print(f"[Receiver] Error: {e}")
    finally:
        elapsed = time.time() - start_time
        fps = frame_count / elapsed if elapsed > 0 else 0
        print(f"📺 Receiver stopped. {frame_count} frames at {fps:.1f} FPS")


def sender_thread(sock):
    """Capture video from webcam and send to peer."""
    global running
    frame_count = 0
    print("📹 Sender thread started")
    adapter = DynamicFrameRateAdapter()
    
    # Target resolution for sending (can be adjusted for quality vs bandwidth)
    TARGET_WIDTH = 640
    TARGET_HEIGHT = 480
    
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ Could not open webcam")
            running = False
            return
        
        # Request desired resolution (may not be honored by all cameras)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, TARGET_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, TARGET_HEIGHT)
        cap.set(cv2.CAP_PROP_FPS, 30)
        cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
        
        # Check actual resolution from camera
        actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        needs_resize = (actual_width != TARGET_WIDTH or actual_height != TARGET_HEIGHT)
        
        if needs_resize:
            print(f"📷 Camera provides {actual_width}x{actual_height}, will resize to {TARGET_WIDTH}x{TARGET_HEIGHT} for sending")
        else:
            print(f"📷 Camera set to {actual_width}x{actual_height}")
        
        start_time = time.time()
        frame_times = []
        
        while running:
            ret, frame = cap.read()
            if not ret:
                print("[Sender] Failed to read from webcam")
                time.sleep(0.01)
                continue
            
            # Track FPS
            frame_times.append(time.time())
            if len(frame_times) > 100:
                frame_times.pop(0)
            
            # Put original frame in queue for local display (show what camera sees)
            try:
                # For local display, resize if too large for display
                display_frame = frame.copy()
                h, w = display_frame.shape[:2]
                if w > 1280 or h > 720:
                    scale = min(1280 / w, 720 / h)
                    display_frame = cv2.resize(display_frame, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
                local_frames.put_nowait(display_frame)
            except:
                try:
                    local_frames.get_nowait()
                    local_frames.put_nowait(display_frame)
                except:
                    pass
            
            # Resize frame for sending if needed (important for high-quality cameras)
            if needs_resize:
                send_frame = cv2.resize(frame, (TARGET_WIDTH, TARGET_HEIGHT), interpolation=cv2.INTER_AREA)
            else:
                send_frame = frame
            
            # Encode and send with dynamic quality
            if adapter.should_send_frame(frame_count):
                try:
                    send_start = time.time()
                    _, encoded = cv2.imencode('.jpg', send_frame, [cv2.IMWRITE_JPEG_QUALITY, adapter.get_jpeg_quality()])
                    data = encoded.tobytes()
                    
                    # Sanity check on frame size
                    if len(data) > MAX_FRAME_SIZE:
                        print(f"[Sender] Frame too large ({len(data)/1024/1024:.1f}MB), reducing quality")
                        _, encoded = cv2.imencode('.jpg', send_frame, [cv2.IMWRITE_JPEG_QUALITY, 30])
                        data = encoded.tobytes()
                    
                    header = struct.pack('>I', len(data))
                    sock.sendall(header)
                    sock.sendall(data)
                    send_duration = time.time() - send_start
                    adapter.record_send(len(data), send_duration)
                    
                    # Check if we should adjust parameters
                    if adapter.should_adjust():
                        bw = adapter.estimate_bandwidth_mbps()
                        adapter.adjust_for_bandwidth(bw)
                    
                    frame_count += 1
                    
                    if frame_count % 100 == 0:
                        elapsed = time.time() - start_time
                        actual_fps = frame_count / elapsed if elapsed > 0 else 0
                        if len(frame_times) > 10:
                            capture_fps = len(frame_times) / (frame_times[-1] - frame_times[0]) if frame_times[-1] != frame_times[0] else 0
                        else:
                            capture_fps = 0
                        print(f"[Sender] {frame_count} frames | Capture: {capture_fps:.1f} FPS | Send: {actual_fps:.1f} FPS | Quality: {adapter.get_jpeg_quality()} | Size: {len(data)/1024:.1f}KB")
                except Exception as e:
                    if running:
                        print(f"[Sender] Send error: {e}")
                    break
            
    except Exception as e:
        if running:
            print(f"[Sender] Error: {e}")
    finally:
        elapsed = time.time() - start_time if 'start_time' in dir() else 0
        fps = frame_count / elapsed if elapsed > 0 else 0
        print(f"📹 Sender stopped. {frame_count} frames at {fps:.1f} FPS")
        if 'cap' in dir():
            cap.release()


def main():
    global running
    
    is_server = sys.argv[1].lower() == 'true' if len(sys.argv) > 1 else False
    peer_ip = sys.argv[2] if len(sys.argv) > 2 else ""
    port = 9997
    server = None
    
    # Connect
    if is_server:
        print(f"🟢 Waiting for video peer on port {port}...")
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(('0.0.0.0', port))
            server.listen(1)
            server.settimeout(60)
            print(f"✅ Listening on 0.0.0.0:{port}")
            sock, addr = server.accept()
            print(f"🔗 Video peer connected from {addr}")
        except socket.timeout:
            print("❌ Timeout waiting for peer")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Server error: {e}")
            sys.exit(1)
    else:
        if not peer_ip:
            print("❌ No peer IP found")
            sys.exit(1)
        print(f"🔗 Connecting to {peer_ip}:{port}...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        try:
            sock.connect((peer_ip, port))
            print("✅ Connected!")
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            sys.exit(1)
    
    # Configure socket for high-quality video streams
    # Larger buffers help with bursty high-resolution frame data
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4 * 1024 * 1024)  # 4MB send buffer
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)  # 4MB receive buffer
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    sock.settimeout(2.0)  # Longer timeout for large frames
    
    # Start worker threads
    recv_t = threading.Thread(target=receiver_thread, args=(sock,), daemon=True)
    send_t = threading.Thread(target=sender_thread, args=(sock,), daemon=True)
    recv_t.start()
    send_t.start()
    
    print("\n🎥 Video call active! Press 'q' to end.\n")
    
    # Main loop - handle display (must be in main thread on macOS)
    try:
        while running:
            # Display local camera frame
            try:
                local_frame = local_frames.get_nowait()
                cv2.imshow('Local Camera', local_frame)
            except Empty:
                pass
            
            # Display received frame
            try:
                recv_frame = received_frames.get_nowait()
                cv2.imshow('Peer Video', recv_frame)
            except Empty:
                pass
            
            # Check for quit key
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("[Main] Quit requested")
                running = False
                break
            
            # Check if threads died
            if not recv_t.is_alive() and not send_t.is_alive():
                print("[Main] Both threads stopped")
                break
                
    except KeyboardInterrupt:
        print("\n[Main] Interrupted")
    finally:
        running = False
        time.sleep(0.5)  # Let threads finish
        cv2.destroyAllWindows()
        try:
            sock.close()
        except:
            pass
        if server:
            try:
                server.close()
            except:
                pass
        print("🎥 Video call ended")


if __name__ == "__main__":
    main()
