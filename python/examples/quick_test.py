#!/usr/bin/env python3
"""
Quick Test for Pangea Net - Communication & Compute

Run with:
    cd python
    source .venv/bin/activate
    python examples/quick_test.py

Requires: Go node running on localhost:8080
    cd go && make build
    ./bin/go-node -node-id=1 -capnp-addr=:8080 -libp2p=true -local
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from client.go_client import GoNodeClient


def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def print_success(text):
    print(f"  ✅ {text}")


def print_fail(text):
    print(f"  ❌ {text}")


def print_info(text):
    print(f"  ℹ️  {text}")


def test_connection(client):
    """Test basic connection to Go node."""
    print_header("Test 1: Connection to Go Node")

    if not client.connect():
        print_fail("Failed to connect to Go node")
        print_info("Make sure go-node is running on localhost:8080")
        return False

    print_success("Connected to Go node!")
    return True


def test_communication(client):
    """Test P2P communication features."""
    print_header("Test 2: P2P Communication")

    # Get nodes
    nodes = client.get_all_nodes()
    print_success(f"Found {len(nodes)} node(s)")
    for node in nodes:
        print_info(f"Node {node['id']}: latency={node['latencyMs']:.1f}ms")

    # Get peers
    peers = client.get_connected_peers()
    print_success(f"Connected peers: {peers}")

    # Network metrics
    metrics = client.get_network_metrics()
    if metrics:
        print_success("Network metrics:")
        print_info(f"  Avg RTT: {metrics.get('avgRttMs', 0):.1f}ms")
        print_info(f"  Bandwidth: {metrics.get('bandwidthMbps', 0):.1f} Mbps")

    return True


def test_compute(client):
    """Test CES compute pipeline."""
    print_header("Test 3: Compute (CES Pipeline)")

    # Test data
    test_data = b"Hello, World! This is test data for CES pipeline. " * 100
    print_info(f"Original data size: {len(test_data)} bytes")

    # CES process
    print_info("Running CES process (compress → encrypt → shard)...")
    shards = client.ces_process(test_data, compression_level=3)

    if shards is None:
        print_fail("CES process failed")
        return False

    print_success(f"Created {len(shards)} shards")
    total_size = sum(len(s) for s in shards)
    ratio = len(test_data) / total_size if total_size > 0 else 0
    print_info(f"Total shard size: {total_size} bytes (ratio: {ratio:.2f}x)")

    # Reconstruct
    print_info("Reconstructing data...")
    shard_present = [True] * len(shards)
    reconstructed = client.ces_reconstruct(shards, shard_present, compression_level=3)

    if reconstructed is None:
        print_fail("CES reconstruct failed")
        return False

    if reconstructed == test_data:
        print_success("Data integrity verified!")
    else:
        print_fail(
            f"Data mismatch! Original: {len(test_data)}, Reconstructed: {len(reconstructed)}"
        )
        return False

    return True


def test_messaging(client):
    """Test P2P messaging."""
    print_header("Test 4: P2P Messaging")

    nodes = client.get_all_nodes()
    if not nodes:
        print_info("No nodes found, skipping")
        return True

    target = nodes[0]["id"]
    message = b"Test message from Python!"

    print_info(f"Sending message to node {target}...")
    success = client.send_message(target, message)

    if success:
        print_success("Message sent successfully")
    else:
        print_info("Message send returned false (peer may not be connected)")

    return True


def main():
    print("\n" + "=" * 60)
    print("  🚀 Pangea Net Quick Test")
    print("=" * 60)

    # Parse args
    host = "localhost"
    port = 8080

    if len(sys.argv) >= 2:
        parts = sys.argv[1].split(":")
        host = parts[0]
        if len(parts) > 1:
            port = int(parts[1])

    print(f"\n  Connecting to {host}:{port}")

    client = GoNodeClient(host=host, port=port)

    try:
        # Run tests
        if not test_connection(client):
            return 1

        passed = 0
        total = 3

        if test_communication(client):
            passed += 1

        if test_compute(client):
            passed += 1

        if test_messaging(client):
            passed += 1

        # Summary
        print_header("Results")
        if passed == total:
            print_success(f"All {total} tests passed!")
            return 0
        else:
            print_fail(f"{passed}/{total} tests passed")
            return 1

    finally:
        client.disconnect()


if __name__ == "__main__":
    sys.exit(main())
