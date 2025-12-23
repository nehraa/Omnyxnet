#!/usr/bin/env python3
"""
DEPRECATED: This file uses direct Python networking which violates the Golden Rule.

The Golden Rule:
  - Go: All networking (libp2p, TCP, UDP)
  - Rust: Files, memory, CES pipeline
  - Python: AI and CLI management

This file is kept as a REFERENCE ONLY for understanding the chat protocol.
For actual P2P chat, use the Go-based communication service:

    # Start Go node with libp2p (auto-discovers peers via mDNS)
    ./go/bin/go-node -node-id 1 -libp2p -local

    # Use Python CLI for high-level management
    python main.py chat send <peer_id> "Hello!"
    python main.py chat history

See docs/COMMUNICATION.md for full documentation.
"""

import socket
import threading
import sys


def receive_messages(sock):
    while True:
        try:
            data = sock.recv(1024)
            if not data:
                print("\n[Peer disconnected]")
                break
            print(f"\n📨 Peer: {data.decode('utf-8')}")
            print("You: ", end="", flush=True)
        except Exception:
            break


def main():
    is_server = sys.argv[1].lower() == "true" if len(sys.argv) > 1 else False
    peer_ip = sys.argv[2] if len(sys.argv) > 2 else ""
    port = 9999

    if is_server:
        print("🟢 Waiting for peer to connect on port", port, "...")
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("0.0.0.0", port))
        server.listen(1)
        conn, addr = server.accept()
        print(f"🔗 Peer connected from {addr}")
        sock = conn
    else:
        if not peer_ip:
            print("❌ No peer IP found. Make sure you pasted the peer address.")
            sys.exit(1)
        print(f"🔗 Connecting to {peer_ip}:{port}...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((peer_ip, port))
            print("🔗 Connected!")
        except Exception as e:
            print(f"❌ Could not connect: {e}")
            print("Make sure the other device started first!")
            sys.exit(1)

    # Start receiver thread
    receiver = threading.Thread(target=receive_messages, args=(sock,), daemon=True)
    receiver.start()

    print("\n💬 Chat started! Type messages and press Enter.\n")

    try:
        while True:
            try:
                msg = input("You: ")
            except EOFError:
                print("\n[Connection closed]")
                break
            if msg.lower() == "quit":
                break
            sock.send(msg.encode("utf-8"))
    except KeyboardInterrupt:
        print("\n[Chat ended]")
    finally:
        sock.close()
        if is_server:
            server.close()


if __name__ == "__main__":
    main()
