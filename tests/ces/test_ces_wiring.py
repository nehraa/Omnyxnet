#!/usr/bin/env python3
"""
Test CES wiring - verifies that CES operations work end-to-end
through the Go → Rust FFI → Python chain.
"""

import sys
import time
from pathlib import Path

# Add Python src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "python"))

from src.client.go_client import GoNodeClient


def test_ces_process_reconstruct():
    """Test CES process and reconstruct operations."""
    print("🧪 Testing CES Process & Reconstruct...")
    
    # Connect to Go node
    client = GoNodeClient(host="localhost", port=8080)
    
    print("  Connecting to Go node...")
    if not client.connect():
        print("  ❌ Failed to connect to Go node")
        print("  Make sure Go node is running: cd go && ./go-node")
        return False
    
    time.sleep(0.5)
    
    try:
        # Test data
        test_data = b"Hello, CES Pipeline! This is a test of the Compression, Encryption, and Sharding system." * 10
        print(f"  Testing with {len(test_data)} bytes of data")
        
        # Process through CES
        print("  Processing through CES pipeline...")
        shards = client.ces_process(test_data, compression_level=3)
        
        if not shards:
            print("  ❌ CES process failed")
            return False
        
        print(f"  ✅ Created {len(shards)} shards")
        print(f"  Shard sizes: {[len(s) for s in shards[:5]]}...")
        
        # Reconstruct from shards
        print("  Reconstructing from shards...")
        shard_present = [True] * len(shards)
        reconstructed = client.ces_reconstruct(shards, shard_present, compression_level=3)
        
        if not reconstructed:
            print("  ❌ CES reconstruct failed")
            return False
        
        print(f"  ✅ Reconstructed {len(reconstructed)} bytes")
        
        # Verify data integrity
        if reconstructed == test_data:
            print("  ✅ Data integrity verified!")
            return True
        else:
            print(f"  ❌ Data mismatch: original={len(test_data)} reconstructed={len(reconstructed)}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        client.disconnect()


def test_get_network_metrics():
    """Test getting network metrics."""
    print("\n🧪 Testing Network Metrics...")
    
    client = GoNodeClient(host="localhost", port=8080)
    
    if not client.connect():
        print("  ❌ Failed to connect to Go node")
        return False
    
    time.sleep(0.5)
    
    try:
        metrics = client.get_network_metrics()
        
        if not metrics:
            print("  ❌ Failed to get network metrics")
            return False
        
        print(f"  ✅ Network Metrics:")
        print(f"    - Average RTT: {metrics['avgRttMs']} ms")
        print(f"    - Packet Loss: {metrics['packetLoss']*100:.2f}%")
        print(f"    - Bandwidth: {metrics['bandwidthMbps']} Mbps")
        print(f"    - Peer Count: {metrics['peerCount']}")
        print(f"    - CPU Usage: {metrics['cpuUsage']*100:.1f}%")
        print(f"    - I/O Capacity: {metrics['ioCapacity']*100:.1f}%")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
    finally:
        client.disconnect()


def main():
    """Run all CES wiring tests."""
    print("=" * 60)
    print("CES Wiring Integration Tests")
    print("=" * 60)
    
    results = []
    
    # Test 1: CES Process & Reconstruct
    results.append(("CES Process & Reconstruct", test_ces_process_reconstruct()))
    
    # Test 2: Network Metrics
    results.append(("Network Metrics", test_get_network_metrics()))
    
    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All CES wiring tests passed!")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
