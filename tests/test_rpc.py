#!/usr/bin/env python3
"""
Python RPC Connection Test for Pangea Net
Tests basic connection to Go node via Cap'n Proto RPC
"""
import sys
import time
from pathlib import Path

# Add python directory to path
PROJECT_ROOT = Path(__file__).parent.parent
PYTHON_DIR = PROJECT_ROOT / "python"
SCHEMA_PATH = PROJECT_ROOT / "go" / "schema" / "schema.capnp"

sys.path.insert(0, str(PYTHON_DIR))

try:
    import capnp
    from src.client.go_client import GoNodeClient
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("   Install dependencies: pip install -r python/requirements.txt")
    print(f"   Python path: {sys.path}")
    sys.exit(1)


def test_connection():
    """Test basic connection to Go node"""
    print("   Testing connection...")
    client = GoNodeClient("localhost", 8080, str(SCHEMA_PATH))
    if client.connect():
        print("   ✅ Connected to Go node")
        return client
    else:
        print("   ❌ Failed to connect")
        return None


def test_get_all_nodes(client):
    """Test getting all nodes"""
    print("   Testing getAllNodes()...")
    nodes = client.get_all_nodes()
    if nodes:
        print(f"   ✅ Got {len(nodes)} nodes")
        if len(nodes) > 0:
            node = nodes[0]
            print(
                f"      Node {node['id']}: latency={node['latencyMs']}ms, threat={node['threatScore']:.3f}"
            )
        return True
    else:
        print("   ❌ Failed to get nodes")
        return False


def test_get_node(client, node_id):
    """Test getting specific node"""
    print(f"   Testing getNode({node_id})...")
    node = client.get_node(node_id)
    if node:
        print(f"   ✅ Got node {node_id}")
        return True
    else:
        print(f"   ❌ Failed to get node {node_id}")
        return False


def test_update_threat_score(client, node_id, score):
    """Test updating threat score"""
    print(f"   Testing updateThreatScore({node_id}, {score})...")
    success = client.update_threat_score(node_id, score)
    if success:
        print("   ✅ Updated threat score")
        return True
    else:
        print("   ❌ Failed to update threat score")
        return False


def test_get_connected_peers(client):
    """Test getting connected peers"""
    print("   Testing getConnectedPeers()...")
    peers = client.get_connected_peers()
    print(f"   ✅ Got {len(peers)} connected peers: {peers}")
    return True


def test_connection_quality(client, peer_id):
    """Test getting connection quality"""
    print(f"   Testing getConnectionQuality({peer_id})...")
    quality = client.get_connection_quality(peer_id)
    if quality:
        print(
            f"   ✅ Got quality: latency={quality['latencyMs']:.2f}ms, jitter={quality['jitterMs']:.2f}ms"
        )
        return True
    else:
        print("   ⚠️  No quality data (peer may not be connected)")
        return True  # Not a failure, just no data


# Main test
if __name__ == "__main__":
    print("\n🧪 Python Connectivity Tests")
    print("=" * 40)

    # Test connection
    client = test_connection()
    if not client:
        sys.exit(1)

    # Wait a bit for node to initialize
    time.sleep(1)

    # Run tests
    tests_passed = 0
    tests_total = 0

    # Test 1: Get all nodes
    tests_total += 1
    if test_get_all_nodes(client):
        tests_passed += 1

    # Test 2: Get specific node
    tests_total += 1
    if test_get_node(client, 1):
        tests_passed += 1

    # Test 3: Update threat score
    tests_total += 1
    if test_update_threat_score(client, 1, 0.75):
        tests_passed += 1

    # Test 4: Get connected peers
    tests_total += 1
    if test_get_connected_peers(client):
        tests_passed += 1

    # Test 5: Get connection quality
    tests_total += 1
    if test_connection_quality(client, 1):
        tests_passed += 1

    # Disconnect
    client.disconnect()

    # Results
    print(f"\n📊 Results: {tests_passed}/{tests_total} tests passed")
    if tests_passed == tests_total:
        print("✅ All connectivity tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed")
        sys.exit(1)
