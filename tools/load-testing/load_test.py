#!/usr/bin/env python3
"""
Load testing script for Pangea Net decentralized network.
Tests network limits and performance under various loads.
"""

import time
import statistics
import concurrent.futures
import sys
import json
from typing import List, Dict, Tuple, Any, Optional
from pathlib import Path
import argparse

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "python" / "src"))

from client.go_client import GoNodeClient


class LoadTester:
    """Load tester for the decentralized network."""

    def __init__(self, nodes: List[Tuple[str, int]]):
        """
        Initialize load tester.

        Args:
            nodes: List of (host, port) tuples for Go nodes
        """
        self.nodes = nodes
        self.clients: List[Any] = []
        self.results: Dict[str, Any] = {
            "connection_tests": [],
            "latency_tests": [],
            "throughput_tests": [],
            "concurrent_tests": [],
            "stress_tests": [],
        }

    def setup_clients(self):
        """Set up clients for all nodes."""
        print(f"Setting up clients for {len(self.nodes)} nodes...")

        for host, port in self.nodes:
            try:
                client = GoNodeClient(host, port)
                if client.connect():
                    self.clients.append(client)
                    print(f"✅ Connected to {host}:{port}")
                else:
                    print(f"❌ Failed to connect to {host}:{port}")
            except Exception as e:
                print(f"❌ Error connecting to {host}:{port}: {e}")

    def test_basic_connectivity(self) -> Dict:
        """Test basic connectivity to all nodes."""
        print("\n🔗 Testing basic connectivity...")

        results: Dict[str, Any] = {
            "total_nodes": len(self.nodes),
            "connected_nodes": len(self.clients),
            "connection_success_rate": (
                len(self.clients) / len(self.nodes) if self.nodes else 0
            ),
            "node_data": [],
        }

        for client in self.clients:
            try:
                start_time = time.time()
                nodes = client.get_all_nodes()
                response_time = time.time() - start_time

                results["node_data"].append(
                    {
                        "host": client.host,
                        "port": client.port,
                        "response_time_ms": response_time * 1000,
                        "nodes_returned": len(nodes),
                        "status": "success",
                    }
                )
            except Exception as e:
                results["node_data"].append(
                    {
                        "host": client.host,
                        "port": client.port,
                        "response_time_ms": -1,
                        "nodes_returned": 0,
                        "status": f"error: {e}",
                    }
                )

        self.results["connection_tests"] = results
        return results

    def test_latency(self, iterations: int = 100) -> Dict:
        """Test latency across all connections."""
        print(f"\n⏱️  Testing latency ({iterations} iterations per node)...")

        results: Dict[str, Any] = {
            "iterations_per_node": iterations,
            "node_latencies": [],
        }

        for client in self.clients:
            latencies = []

            for i in range(iterations):
                try:
                    start_time = time.time()
                    client.get_all_nodes()
                    latency = (time.time() - start_time) * 1000  # ms
                    latencies.append(latency)

                    if (i + 1) % 20 == 0:
                        print(
                            f"    Node {client.host}:{client.port} - {i+1}/{iterations} iterations"
                        )

                except Exception as e:
                    print(f"    Error in iteration {i+1}: {e}")

            if latencies:
                node_result = {
                    "host": client.host,
                    "port": client.port,
                    "min_latency_ms": min(latencies),
                    "max_latency_ms": max(latencies),
                    "avg_latency_ms": statistics.mean(latencies),
                    "median_latency_ms": statistics.median(latencies),
                    "std_dev_ms": (
                        statistics.stdev(latencies) if len(latencies) > 1 else 0
                    ),
                    "success_count": len(latencies),
                    "total_attempts": iterations,
                }
                results["node_latencies"].append(node_result)

        self.results["latency_tests"] = results
        return results

    def test_concurrent_load(
        self, concurrent_requests: int = 50, duration_seconds: int = 30
    ) -> Dict:
        """Test concurrent load on the network."""
        print(
            f"\n🚀 Testing concurrent load ({concurrent_requests} concurrent requests for {duration_seconds}s)..."
        )

        results: Dict[str, Any] = {
            "concurrent_requests": concurrent_requests,
            "duration_seconds": duration_seconds,
            "node_results": [],
        }

        def make_request(client, request_id):
            try:
                start_time = time.time()
                nodes = client.get_all_nodes()
                response_time = time.time() - start_time
                return {
                    "request_id": request_id,
                    "host": client.host,
                    "port": client.port,
                    "response_time_ms": response_time * 1000,
                    "nodes_count": len(nodes),
                    "status": "success",
                }
            except Exception as e:
                return {
                    "request_id": request_id,
                    "host": client.host,
                    "port": client.port,
                    "response_time_ms": -1,
                    "nodes_count": 0,
                    "status": f"error: {e}",
                }

        for client in self.clients:
            print(f"    Testing node {client.host}:{client.port}...")

            start_time = time.time()
            request_results = []

            with concurrent.futures.ThreadPoolExecutor(
                max_workers=concurrent_requests
            ) as executor:
                request_id = 0

                while time.time() - start_time < duration_seconds:
                    # Submit batch of concurrent requests
                    futures = []
                    for _ in range(min(concurrent_requests, 10)):  # Batch size
                        future = executor.submit(make_request, client, request_id)
                        futures.append(future)
                        request_id += 1

                    # Collect results
                    for future in concurrent.futures.as_completed(futures, timeout=5):
                        try:
                            result = future.result()
                            request_results.append(result)
                        except Exception as e:
                            request_results.append(
                                {
                                    "request_id": request_id,
                                    "host": client.host,
                                    "port": client.port,
                                    "response_time_ms": -1,
                                    "status": f"timeout: {e}",
                                }
                            )

                    time.sleep(0.1)  # Small delay between batches

            # Analyze results for this node
            successful_requests = [
                r for r in request_results if r["status"] == "success"
            ]
            response_times = [r["response_time_ms"] for r in successful_requests]

            node_result = {
                "host": client.host,
                "port": client.port,
                "total_requests": len(request_results),
                "successful_requests": len(successful_requests),
                "success_rate": (
                    len(successful_requests) / len(request_results)
                    if request_results
                    else 0
                ),
                "avg_response_time_ms": (
                    statistics.mean(response_times) if response_times else -1
                ),
                "min_response_time_ms": min(response_times) if response_times else -1,
                "max_response_time_ms": max(response_times) if response_times else -1,
                "requests_per_second": len(successful_requests) / duration_seconds,
            }
            results["node_results"].append(node_result)

        self.results["concurrent_tests"] = results
        return results

    def test_stress_limits(self, max_connections: int = 1000) -> Dict:
        """Test network stress limits."""
        print(f"\n💥 Testing stress limits (up to {max_connections} connections)...")

        results: Dict[str, Any] = {
            "max_connections_tested": max_connections,
            "connection_results": [],
        }

        # Test increasing numbers of connections
        connection_counts = [1, 5, 10, 25, 50, 100, 200, 500]
        if max_connections > 500:
            connection_counts.extend([750, 1000])

        for conn_count in connection_counts:
            if conn_count > max_connections:
                break

            print(f"    Testing {conn_count} concurrent connections...")

            start_time = time.time()
            successful_connections = 0
            total_response_time = 0

            def test_connection(node_info):
                host, port = node_info
                try:
                    client = GoNodeClient(host, port)
                    conn_start = time.time()
                    if client.connect():
                        client.get_all_nodes()
                        response_time = time.time() - conn_start
                        client.disconnect()
                        return True, response_time
                    return False, 0
                except Exception:
                    return False, 0

            # Create connection pool
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=conn_count
            ) as executor:
                # Distribute connections across all nodes
                node_assignments = []
                for i in range(conn_count):
                    node_assignments.append(self.nodes[i % len(self.nodes)])

                futures = [
                    executor.submit(test_connection, node) for node in node_assignments
                ]

                for future in concurrent.futures.as_completed(futures, timeout=30):
                    try:
                        success, response_time = future.result()
                        if success:
                            successful_connections += 1
                            total_response_time += response_time
                    except Exception:
                        pass

            test_duration = time.time() - start_time

            result = {
                "concurrent_connections": conn_count,
                "successful_connections": successful_connections,
                "success_rate": successful_connections / conn_count,
                "avg_response_time_ms": (
                    (total_response_time / successful_connections * 1000)
                    if successful_connections > 0
                    else -1
                ),
                "test_duration_seconds": test_duration,
                "connections_per_second": (
                    successful_connections / test_duration if test_duration > 0 else 0
                ),
            }
            results["connection_results"].append(result)

            print(
                f"      {successful_connections}/{conn_count} successful ({result['success_rate']:.2%})"
            )

            # Stop if success rate drops below 50%
            if result["success_rate"] < 0.5:
                print("      Stopping stress test - success rate too low")
                break

        self.results["stress_tests"] = results
        return results

    def run_full_test_suite(self) -> Dict:
        """Run complete test suite."""
        print("🧪 Starting Pangea Net Load Testing Suite")
        print("=" * 50)

        start_time = time.time()

        # Setup
        self.setup_clients()

        if not self.clients:
            print("❌ No clients connected - aborting tests")
            return {"error": "No connections available"}

        # Run tests
        connectivity = self.test_basic_connectivity()
        latency = self.test_latency(iterations=50)
        concurrent = self.test_concurrent_load(
            concurrent_requests=20, duration_seconds=15
        )
        stress = self.test_stress_limits(max_connections=100)

        total_duration = time.time() - start_time

        # Summary
        summary = {
            "test_duration_seconds": total_duration,
            "nodes_tested": len(self.clients),
            "connectivity_success_rate": connectivity["connection_success_rate"],
            "avg_latency_ms": (
                statistics.mean(
                    [n["avg_latency_ms"] for n in latency["node_latencies"]]
                )
                if latency["node_latencies"]
                else -1
            ),
            "max_concurrent_success_rate": (
                max([n["success_rate"] for n in concurrent["node_results"]])
                if concurrent["node_results"]
                else 0
            ),
            "max_stress_connections": (
                max([r["successful_connections"] for r in stress["connection_results"]])
                if stress["connection_results"]
                else 0
            ),
        }

        self.results["summary"] = summary

        print("\n📊 Test Suite Complete!")
        print(f"Duration: {total_duration:.1f}s")
        print(f"Nodes tested: {len(self.clients)}")
        print(f"Connectivity success rate: {summary['connectivity_success_rate']:.2%}")
        print(f"Average latency: {summary['avg_latency_ms']:.2f}ms")
        print(
            f"Max concurrent success rate: {summary['max_concurrent_success_rate']:.2%}"
        )
        print(f"Max stress connections: {summary['max_stress_connections']}")

        return self.results

    def save_results(self, filename: Optional[str] = None):
        """Save test results to JSON file."""
        if filename is None:
            timestamp = int(time.time())
            filename = f"load_test_results_{timestamp}.json"

        with open(filename, "w") as f:
            json.dump(self.results, f, indent=2)

        print(f"📄 Results saved to {filename}")


def main():
    parser = argparse.ArgumentParser(
        description="Load test Pangea Net decentralized network"
    )
    parser.add_argument(
        "--nodes",
        nargs="+",
        default=["localhost:8080", "localhost:8081", "localhost:8082"],
        help="Node addresses in host:port format",
    )
    parser.add_argument("--save", help="Save results to file")
    parser.add_argument("--quick", action="store_true", help="Run quick test suite")

    args = parser.parse_args()

    # Parse node addresses
    nodes = []
    for node_str in args.nodes:
        try:
            host, port = node_str.split(":")
            nodes.append((host, int(port)))
        except ValueError:
            print(f"Invalid node format: {node_str} (expected host:port)")
            sys.exit(1)

    print(f"Testing nodes: {[f'{h}:{p}' for h, p in nodes]}")

    # Create and run load tester
    tester = LoadTester(nodes)

    if args.quick:
        tester.setup_clients()
        tester.test_basic_connectivity()
        tester.test_latency(iterations=20)
    else:
        tester.run_full_test_suite()

    if args.save:
        tester.save_results(args.save)


if __name__ == "__main__":
    main()
