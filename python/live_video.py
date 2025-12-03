#!/usr/bin/env python3
"""Live video streaming with webcam - macOS compatible.

On macOS, OpenCV's imshow() must be called from the main thread.
This version uses queues to pass frames between threads and the main loop.
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


def receiver_thread(sock):
    """Receive video frames from peer and put them in queue."""
    global running
    frame_count = 0
    start_time = time.time()
    print("📺 Receiver thread started")
    
    try:
        while running:
            # Read frame size header
            header = b''
            while len(header) < 4 and running:
                try:
                    chunk = sock.recv(4 - len(header))
                    if not chunk:
                        print("[Receiver] Connection closed by peer")
                        return
                    header += chunk
                except socket.timeout:
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
            
            # Read frame data
            data = b''
            while len(data) < length and running:
                try:
                    remaining = length - len(data)
                    chunk = sock.recv(min(65536, remaining))
                    if not chunk:
                        print(f"[Receiver] Connection closed mid-frame")
                        return
                    data += chunk
                except socket.timeout:
                    continue
                except Exception as e:
                    if running:
                        print(f"[Receiver] Recv error: {e}")
                    return
            
            if not running:
                break
            
            # Decode frame
            try:
                frame = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
                if frame is not None:
                    frame_count += 1
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
                        print(f"[Receiver] {frame_count} frames at {fps:.1f} FPS")
            except Exception as e:
                # Silent fail on decode - don't spam
                pass
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
                print("[Sender] Failed to read from webcam")
                time.sleep(0.01)
                continue
            
            # Track FPS
            frame_times.append(time.time())
            if len(frame_times) > 100:
                frame_times.pop(0)
            
            # Put frame in queue for local display
            try:
                local_frames.put_nowait(frame.copy())
            except:
                try:
                    local_frames.get_nowait()
                    local_frames.put_nowait(frame.copy())
                except:
                    pass
            
            # Encode and send with dynamic quality
            if adapter.should_send_frame(frame_count):
                try:
                    send_start = time.time()
                    _, encoded = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, adapter.get_jpeg_quality()])
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
                        print(f"[Sender] {frame_count} frames | Capture: {capture_fps:.1f} FPS | Send: {actual_fps:.1f} FPS | Quality: {adapter.get_jpeg_quality()}")
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
    
    # Configure socket
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024 * 1024)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024 * 1024)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    sock.settimeout(1.0)  # Short timeout for responsive shutdown
    
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
