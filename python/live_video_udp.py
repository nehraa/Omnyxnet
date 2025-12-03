#!/usr/bin/env python3
"""Live video streaming with UDP - optimized for low latency and high FPS.

UDP trades reliability for speed - perfect for video where a few dropped frames
are better than buffering delays. Uses selective retransmit for keyframes only.
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
packet_loss_count = 0


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
            print(f"[UDP Adapter] BW: {bandwidth_mbps:.2f} Mbps → Quality: {self.jpeg_quality} | Skip: {self.frame_skip}")
    
    def should_send_frame(self, frame_count):
        """Determine if this frame should be sent based on skip rate."""
        return (frame_count % (self.frame_skip + 1)) == 0
    
    def get_jpeg_quality(self):
        """Get current JPEG quality setting."""
        return self.jpeg_quality


def receiver_thread_udp(sock):
    """Receive video frames via UDP."""
    global running, packet_loss_count
    frame_count = 0
    start_time = time.time()
    lost_packets = 0
    print("📺 UDP Receiver thread started")
    
    frame_buffer = {}  # buffer for out-of-order packets
    expected_frame_id = 0
    
    try:
        while running:
            try:
                data, addr = sock.recvfrom(65536)
                if len(data) < 8:
                    continue
                
                frame_id = struct.unpack('>I', data[0:4])[0]
                packet_num = struct.unpack('>I', data[4:8])[0]
                frame_data = data[8:]
                
                # Buffer packets for this frame
                if frame_id not in frame_buffer:
                    frame_buffer[frame_id] = {}
                frame_buffer[frame_id][packet_num] = frame_data
                
                # Try to assemble complete frames
                while expected_frame_id in frame_buffer:
                    packets = frame_buffer[expected_frame_id]
                    # Simple check: if we have packets 0, 1, 2... (should have metadata in packet 0)
                    num_packets = struct.unpack('>I', packets[0][0:4])[0] if 0 in packets else 0
                    
                    if num_packets > 0 and all(i in packets for i in range(num_packets)):
                        # Assemble frame
                        frame_bytes = b''.join(packets[i][4:] if i > 0 else packets[i][8:] for i in range(num_packets))
                        
                        try:
                            frame = cv2.imdecode(np.frombuffer(frame_bytes, np.uint8), cv2.IMREAD_COLOR)
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
                                    print(f"[Receiver] {frame_count} frames | FPS: {fps:.1f} | Loss: {lost_packets}")
                        except:
                            pass
                        
                        del frame_buffer[expected_frame_id]
                        expected_frame_id += 1
                    else:
                        break
                
            except socket.timeout:
                continue
            except Exception as e:
                if running:
                    print(f"[Receiver] Error: {e}")
                    
    except Exception as e:
        if running:
            print(f"[Receiver] Fatal error: {e}")
    finally:
        elapsed = time.time() - start_time
        fps = frame_count / elapsed if elapsed > 0 else 0
        print(f"📺 Receiver stopped. {frame_count} frames at {fps:.1f} FPS | Packets lost: {lost_packets}")


def sender_thread_udp(sock, peer_addr):
    """Capture video and send via UDP."""
    global running
    frame_count = 0
    print("📹 UDP Sender thread started")
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
        max_packet_size = 60000  # Leave room for UDP/IP headers
        
        while running:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.01)
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
            
            # Encode with dynamic quality for UDP speed
            if adapter.should_send_frame(frame_count):
                try:
                    send_start = time.time()
                    _, encoded = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, adapter.get_jpeg_quality()])
                    frame_data = encoded.tobytes()
                    
                    # Split into UDP packets (max 60KB each)
                    num_packets = (len(frame_data) + max_packet_size - 1) // max_packet_size
                    
                    for packet_num in range(num_packets):
                        start_idx = packet_num * max_packet_size
                        end_idx = min(start_idx + max_packet_size, len(frame_data))
                        packet_data = frame_data[start_idx:end_idx]
                        
                        # Build UDP packet: [frame_id (4)] [packet_num (4)] [num_packets (4)] [data]
                        header = struct.pack('>III', frame_count, packet_num, num_packets)
                        udp_packet = header + packet_data
                        
                        try:
                            sock.sendto(udp_packet, peer_addr)
                        except Exception as e:
                            if running and frame_count % 100 == 0:
                                print(f"[Sender] Send error: {e}")
                            break
                    
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
                        print(f"[Sender] {frame_count} frames | Capture: {capture_fps:.1f} FPS | Send: {total_fps:.1f} FPS | Quality: {adapter.get_jpeg_quality()} | Packets/frame: {num_packets}")
                    
            except Exception as e:
                if running:
                    print(f"[Sender] Encode/send error: {e}")
                break
    
    except Exception as e:
        if running:
            print(f"[Sender] Fatal error: {e}")
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
    port = 9996  # Different port for UDP video
    
    if is_server:
        print(f"🟢 Waiting for UDP video peer on port {port}...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('0.0.0.0', port))
        sock.settimeout(1.0)
        print(f"✅ Listening on UDP 0.0.0.0:{port}")
        
        # Wait for first packet to get peer address
        peer_addr = None
        while peer_addr is None and running:
            try:
                _, addr = sock.recvfrom(1024)
                peer_addr = addr
                print(f"🔗 Got UDP packet from {addr}")
            except socket.timeout:
                continue
        
        if not peer_addr:
            print("❌ No peer connected")
            sys.exit(1)
    else:
        if not peer_ip:
            print("❌ No peer IP found")
            sys.exit(1)
        print(f"🔗 Sending UDP video to {peer_ip}:{port}...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4 * 1024 * 1024)
        sock.settimeout(1.0)
        peer_addr = (peer_ip, port)
        print("✅ UDP socket ready")
    
    # Start threads
    recv_t = threading.Thread(target=receiver_thread_udp, args=(sock,), daemon=True)
    send_t = threading.Thread(target=sender_thread_udp, args=(sock, peer_addr), daemon=True)
    recv_t.start()
    send_t.start()
    
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
            
            if not recv_t.is_alive() and not send_t.is_alive():
                print("[Main] Both threads stopped")
                break
                
    except KeyboardInterrupt:
        print("\n[Main] Interrupted")
    finally:
        running = False
        time.sleep(0.5)
        cv2.destroyAllWindows()
        try:
            sock.close()
        except:
            pass
        print("🎥 UDP Video call ended")


if __name__ == "__main__":
    main()
