#!/usr/bin/env python3
"""
Manual Peer Connection Utility - SIMPLIFIED VERSION

You ONLY need the IP and port - peer ID is auto-detected!

Usage:
    python examples/manual_connect.py 192.168.1.100:9081
    python examples/manual_connect.py 10.0.0.5:9081
    python examples/manual_connect.py  # Interactive mode

HOW TO GET PEER ADDRESS:
  1. Run on REMOTE machine: ./bin/go-node -node-id=2 -capnp-addr=:8081 -libp2p=true
  2. Look for output like: listening on /ip4/192.168.1.100/tcp/9081/...
  3. Copy the IP and port (192.168.1.100:9081)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from client.go_client import GoNodeClient

def main():
    # Get peer address from command line or prompt
    peer_address = None
    
    if len(sys.argv) > 1:
        peer_address = sys.argv[1]
    else:
        print("\n" + "=" * 60)
        print("  🔗 Manual Peer Connection")
        print("=" * 60)
        print("\n📋 You need the peer's IP and port (from its startup log)")
        print("\n   On REMOTE machine, run:")
        print("   ./bin/go-node -node-id=2 -capnp-addr=:8081 -libp2p=true")
        print("\n   Look for: /ip4/192.168.1.100/tcp/9081/...")
        print("   Copy: 192.168.1.100:9081\n")
        
        peer_address = input("Enter peer address (IP:port): ").strip()
        
        if not peer_address:
            print("Cancelled")
            return 1
    
    # Parse address
    if ":" not in peer_address:
        print(f"❌ Invalid format. Use IP:port")
        return 1
    
    try:
        peer_host, peer_port_str = peer_address.rsplit(":", 1)
        peer_port_num = int(peer_port_str)
    except ValueError:
        print(f"❌ Invalid port number")
        return 1
    
    print(f"\n🔍 Looking for peer at {peer_host}:{peer_port_num}...")
    
    # Connect to local Go node
    client = GoNodeClient(host="localhost", port=8080)
    
    if not client.connect():
        print("❌ Failed to connect to local Go node")
        print("   Make sure go-node is running:")
        print("   ./bin/go-node -node-id=1 -capnp-addr=:8080 -libp2p=true -local")
        return 1
    
    # Auto-detect peer ID by trying different IDs
    peer_id = None
    for candidate_id in range(2, 11):
        print(f"   Trying peer ID {candidate_id}...", end="", flush=True)
        success, quality = client.connect_to_peer(candidate_id, peer_host, peer_port_num)
        if success:
            peer_id = candidate_id
            print(f" ✅")
            break
        else:
            print(f" ✗", end="", flush=True)
    
    if peer_id is None:
        print(f"\n\n❌ Could not connect to {peer_host}:{peer_port_num}")
        print("\n🔧 Troubleshooting:")
        print(f"   • Remote node running? Check port {peer_port_num}")
        print(f"   • IP correct? Try: ping {peer_host}")
        print(f"   • Firewall open? Check both machines")
        print(f"   • Try different port? Maybe 9082, 9083, etc.")
        client.disconnect()
        return 1
    
    # Show success and connection quality
    print(f"\n✅ Connected to peer {peer_id}!")
    print(f"   Address: {peer_host}:{peer_port_num}")
    
    quality = client.get_connection_quality(peer_id)
    if quality:
        print(f"\n📊 Connection Quality:")
        print(f"   Latency: {quality['latencyMs']:.1f}ms")
        print(f"   Jitter: {quality['jitterMs']:.1f}ms")
        print(f"   Packet Loss: {quality['packetLoss']*100:.2f}%")
    
    # Send test message
    print(f"\n📤 Sending test message...")
    msg_success = client.send_message(peer_id, b"Hello from manual connection!")
    if msg_success:
        print("✅ Test message sent!")
    else:
        print("⚠️  Message send returned false")
    
    # Show connected peers
    peers = client.get_connected_peers()
    print(f"\n🔗 Connected peers: {peers}")
    
    print("\n" + "=" * 60)
    print("✅ Peer connected! Ready to use.")
    print("=" * 60)
    
    client.disconnect()
    return 0

if __name__ == "__main__":
    sys.exit(main())

