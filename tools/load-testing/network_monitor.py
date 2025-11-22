#!/usr/bin/env python3
"""
Real-time network monitor for Pangea Net.
Provides live monitoring of network performance and limits.
"""

import time
import json
import statistics
import threading
from datetime import datetime
from typing import Dict, List
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "python" / "src"))

from client.go_client import GoNodeClient


class NetworkMonitor:
    """Real-time network performance monitor."""
    
    def __init__(self, nodes: List[tuple]):
        self.nodes = nodes
        self.clients = []
        self.monitoring = False
        self.metrics = {
            'timestamps': [],
            'node_metrics': {},
            'network_metrics': {
                'total_connections': [],
                'avg_latency': [],
                'throughput': [],
                'error_rate': []
            }
        }
        
    def setup(self):
        """Setup monitoring clients."""
        print(f"🔧 Setting up monitoring for {len(self.nodes)} nodes...")
        
        for host, port in self.nodes:
            try:
                client = GoNodeClient(host, port)
                if client.connect():
                    self.clients.append(client)
                    self.metrics['node_metrics'][f"{host}:{port}"] = {
                        'latencies': [],
                        'response_times': [],
                        'success_rate': [],
                        'node_counts': []
                    }
                    print(f"✅ Connected to {host}:{port}")
                else:
                    print(f"❌ Failed to connect to {host}:{port}")
            except Exception as e:
                print(f"❌ Error connecting to {host}:{port}: {e}")
    
    def collect_metrics(self):
        """Collect metrics from all nodes."""
        timestamp = datetime.now().isoformat()
        self.metrics['timestamps'].append(timestamp)
        
        total_nodes = 0
        response_times = []
        success_count = 0
        total_attempts = len(self.clients)
        
        for client in self.clients:
            node_key = f"{client.host}:{client.port}"
            
            try:
                start_time = time.time()
                nodes = client.get_all_nodes()
                response_time = (time.time() - start_time) * 1000  # ms
                
                # Record metrics
                self.metrics['node_metrics'][node_key]['response_times'].append(response_time)
                self.metrics['node_metrics'][node_key]['node_counts'].append(len(nodes))
                
                response_times.append(response_time)
                total_nodes += len(nodes)
                success_count += 1
                
                # Test connection quality if available
                try:
                    for node in nodes:
                        quality = client.get_connection_quality(node['id'])
                        if quality:
                            self.metrics['node_metrics'][node_key]['latencies'].append(quality['latencyMs'])
                except:
                    pass
                    
            except Exception as e:
                self.metrics['node_metrics'][node_key]['response_times'].append(-1)
                print(f"❌ Error collecting from {node_key}: {e}")
        
        # Calculate network-wide metrics
        avg_latency = statistics.mean(response_times) if response_times else 0
        error_rate = (total_attempts - success_count) / total_attempts if total_attempts > 0 else 1
        
        self.metrics['network_metrics']['total_connections'].append(total_nodes)
        self.metrics['network_metrics']['avg_latency'].append(avg_latency)
        self.metrics['network_metrics']['error_rate'].append(error_rate)
        
        return {
            'timestamp': timestamp,
            'total_nodes': total_nodes,
            'avg_latency_ms': avg_latency,
            'success_rate': success_count / total_attempts if total_attempts > 0 else 0,
            'error_rate': error_rate
        }
    
    def start_monitoring(self, interval: float = 2.0, duration: int = 300):
        """Start real-time monitoring."""
        print(f"📊 Starting real-time monitoring (interval: {interval}s, duration: {duration}s)")
        print("=" * 80)
        
        self.monitoring = True
        start_time = time.time()
        
        # Header
        print(f"{'Time':<8} {'Nodes':<6} {'Latency(ms)':<12} {'Success%':<9} {'Error%':<8} {'Status'}")
        print("-" * 80)
        
        try:
            while self.monitoring and (time.time() - start_time) < duration:
                metrics = self.collect_metrics()
                
                # Display current metrics
                current_time = datetime.now().strftime("%H:%M:%S")
                print(f"{current_time:<8} "
                      f"{metrics['total_nodes']:<6} "
                      f"{metrics['avg_latency_ms']:<12.2f} "
                      f"{metrics['success_rate']*100:<8.1f}% "
                      f"{metrics['error_rate']*100:<7.1f}% "
                      f"{'🟢' if metrics['error_rate'] < 0.1 else '🟡' if metrics['error_rate'] < 0.3 else '🔴'}")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n⏹️  Monitoring stopped by user")
        
        self.monitoring = False
        self.analyze_results()
    
    def analyze_results(self):
        """Analyze collected metrics."""
        if not self.metrics['timestamps']:
            print("No metrics collected")
            return
        
        print("\n📈 Monitoring Analysis")
        print("=" * 50)
        
        # Network-wide analysis
        latencies = [l for l in self.metrics['network_metrics']['avg_latency'] if l > 0]
        error_rates = self.metrics['network_metrics']['error_rate']
        
        if latencies:
            print(f"Network Latency:")
            print(f"  Average: {statistics.mean(latencies):.2f}ms")
            print(f"  Min/Max: {min(latencies):.2f}ms / {max(latencies):.2f}ms")
            print(f"  Std Dev: {statistics.stdev(latencies):.2f}ms" if len(latencies) > 1 else "  Std Dev: N/A")
        
        if error_rates:
            avg_error_rate = statistics.mean(error_rates)
            print(f"\nError Rate:")
            print(f"  Average: {avg_error_rate*100:.2f}%")
            print(f"  Max: {max(error_rates)*100:.2f}%")
        
        # Per-node analysis
        print(f"\nPer-Node Analysis:")
        for node_key, metrics in self.metrics['node_metrics'].items():
            response_times = [rt for rt in metrics['response_times'] if rt > 0]
            if response_times:
                print(f"  {node_key}:")
                print(f"    Avg Response: {statistics.mean(response_times):.2f}ms")
                print(f"    Success Rate: {len(response_times)/len(metrics['response_times'])*100:.1f}%")
    
    def stress_test(self, max_load: int = 1000, step: int = 50):
        """Run progressive stress test to find limits."""
        print(f"💥 Running stress test (up to {max_load} req/s)")
        print("=" * 50)
        
        import concurrent.futures
        
        results = []
        
        for load in range(step, max_load + 1, step):
            print(f"\n🔥 Testing load: {load} requests/second")
            
            def make_request(client):
                try:
                    start = time.time()
                    client.get_all_nodes()
                    return time.time() - start
                except:
                    return -1
            
            # Run for 10 seconds at this load
            start_time = time.time()
            successful_requests = 0
            total_requests = 0
            response_times = []
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=load) as executor:
                while (time.time() - start_time) < 10:  # 10 second test
                    # Submit requests to maintain target load
                    futures = []
                    for _ in range(min(load, len(self.clients) * 10)):
                        client = self.clients[total_requests % len(self.clients)]
                        future = executor.submit(make_request, client)
                        futures.append(future)
                        total_requests += 1
                    
                    # Collect results
                    for future in concurrent.futures.as_completed(futures, timeout=1):
                        try:
                            response_time = future.result()
                            if response_time > 0:
                                successful_requests += 1
                                response_times.append(response_time)
                        except:
                            pass
                    
                    time.sleep(1.0 / load)  # Control rate
            
            # Calculate metrics
            success_rate = successful_requests / total_requests if total_requests > 0 else 0
            avg_response_time = statistics.mean(response_times) if response_times else 0
            actual_rps = successful_requests / 10  # 10 second test
            
            result = {
                'target_load': load,
                'actual_rps': actual_rps,
                'success_rate': success_rate,
                'avg_response_time_ms': avg_response_time * 1000,
                'total_requests': total_requests,
                'successful_requests': successful_requests
            }
            results.append(result)
            
            print(f"    Actual RPS: {actual_rps:.1f}")
            print(f"    Success Rate: {success_rate*100:.1f}%")
            print(f"    Avg Response: {avg_response_time*1000:.2f}ms")
            
            # Stop if performance degrades significantly
            if success_rate < 0.5:
                print(f"    💀 Performance degraded - stopping stress test")
                break
        
        print(f"\n📊 Stress Test Summary:")
        print(f"    Max sustainable load: {max([r['actual_rps'] for r in results if r['success_rate'] > 0.9]):.1f} RPS")
        print(f"    Max tested load: {max([r['actual_rps'] for r in results]):.1f} RPS")
        
        return results
    
    def save_metrics(self, filename: str = None):
        """Save collected metrics to file."""
        if filename is None:
            timestamp = int(time.time())
            filename = f"network_metrics_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.metrics, f, indent=2)
        
        print(f"📄 Metrics saved to {filename}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor Pangea Net network performance")
    parser.add_argument('--nodes', nargs='+', default=['localhost:8080', 'localhost:8081', 'localhost:8082'],
                       help='Node addresses in host:port format')
    parser.add_argument('--monitor', type=int, default=60, help='Monitor duration in seconds')
    parser.add_argument('--interval', type=float, default=2.0, help='Monitoring interval in seconds')
    parser.add_argument('--stress', action='store_true', help='Run stress test instead of monitoring')
    parser.add_argument('--save', help='Save metrics to file')
    
    args = parser.parse_args()
    
    # Parse nodes
    nodes = []
    for node_str in args.nodes:
        try:
            host, port = node_str.split(':')
            nodes.append((host, int(port)))
        except ValueError:
            print(f"Invalid node format: {node_str}")
            sys.exit(1)
    
    monitor = NetworkMonitor(nodes)
    monitor.setup()
    
    if not monitor.clients:
        print("❌ No nodes available for monitoring")
        sys.exit(1)
    
    if args.stress:
        monitor.stress_test()
    else:
        monitor.start_monitoring(interval=args.interval, duration=args.monitor)
    
    if args.save:
        monitor.save_metrics(args.save)


if __name__ == "__main__":
    main()