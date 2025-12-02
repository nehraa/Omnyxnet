#!/usr/bin/env python3
"""Live video streaming with webcam."""

import cv2
import socket
import threading
import struct
import numpy as np
import sys
import time

def video_receiver(sock):
    """Receive and display video from peer."""
    print("📺 Video receiver started")

    try:
        while True:
            header = sock.recv(4)
            if not header:
                break
            length = struct.unpack('>I', header)[0]
            data = b''
            while len(data) < length:
                chunk = sock.recv(min(65536, length - len(data)))
                if not chunk:
                    break
                data += chunk

            frame = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
            if frame is not None:
                cv2.imshow('Peer Video', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
    except Exception as e:
        print(f"Receiver stopped: {e}")

def video_sender(sock):
    """Capture and send video to peer."""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Could not open webcam")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    print("📹 Webcam started")
    frame_count = 0
    start_time = time.time()

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            cv2.imshow('Local Camera', frame)

            _, encoded = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            data = encoded.tobytes()

            try:
                sock.send(struct.pack('>I', len(data)) + data)
                frame_count += 1
            except:
                break

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    except Exception as e:
        print(f"Sender stopped: {e}")
    finally:
        elapsed = time.time() - start_time
        fps = frame_count / elapsed if elapsed > 0 else 0
        print(f"📊 Sent {frame_count} frames at {fps:.1f} FPS")
        cap.release()

def main():
    is_server = sys.argv[1].lower() == 'true' if len(sys.argv) > 1 else False
    peer_ip = sys.argv[2] if len(sys.argv) > 2 else ""
    port = 9997

    # Connect
    if is_server:
        print(f"🟢 Waiting for video peer on port {port}...")
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', port))
        server.listen(1)
        sock, addr = server.accept()
        print(f"🔗 Video peer connected from {addr}")
    else:
        if not peer_ip:
            print("❌ No peer IP found")
            sys.exit(1)
        print(f"🔗 Connecting to video peer at {peer_ip}:{port}...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((peer_ip, port))
        print("🔗 Connected!")

    # Start threads
    sender_thread = threading.Thread(target=video_sender, args=(sock,), daemon=True)
    receiver_thread = threading.Thread(target=video_receiver, args=(sock,), daemon=True)

    sender_thread.start()
    receiver_thread.start()

    print("\n🎥 Video call active! Press 'q' in video window to end.\n")

    try:
        while True:
            time.sleep(0.1)
            try:
                if cv2.getWindowProperty('Local Camera', cv2.WND_PROP_VISIBLE) < 1:
                    break
            except:
                pass
    except KeyboardInterrupt:
        print("\n[Video call ended]")
    finally:
        cv2.destroyAllWindows()
        sock.close()
        if is_server:
            server.close()

if __name__ == "__main__":
    main()
