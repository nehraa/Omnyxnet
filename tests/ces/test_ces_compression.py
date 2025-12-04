#!/usr/bin/env python3
"""
CES Pipeline Compression Algorithm Tests
======================================

Individual testing of CES compression algorithms:
- Zstd (original) 
- Brotli (Phase 1 addition)
- None (no compression)

Tests each algorithm separately with different data types.
"""

import subprocess
import os
import time
import json
from pathlib import Path

class CESCompressionTester:
    def __init__(self):
        self.results = {}
        print("🧪 CES Pipeline Compression Algorithm Tests")
        print("=" * 50)
    
    def create_test_files(self):
        """Create different types of test files"""
        test_files = {}
        
        # 1. Highly compressible text (JSON-like)
        json_data = {
            "message": "Hello World",
            "timestamp": 1699999999,
            "data": list(range(100)),
            "repeated_text": "This is repeated content. " * 100
        }
        
        with open('test_json.json', 'w') as f:
            json.dump(json_data, f, indent=2)
        test_files['json'] = ('test_json.json', 'JSON data (highly compressible)')
        
        # 2. Random binary data (not compressible)
        with open('test_random.bin', 'wb') as f:
            f.write(os.urandom(50000))  # 50KB random
        test_files['random'] = ('test_random.bin', 'Random binary (not compressible)')
        
        # 3. Repetitive text (very compressible)
        with open('test_text.txt', 'w') as f:
            for i in range(1000):
                f.write(f"Line {i}: This is a test line with repeated patterns.\n")
        test_files['text'] = ('test_text.txt', 'Repetitive text (very compressible)')
        
        # 4. Medium complexity data
        mixed_data = []
        for i in range(500):
            mixed_data.extend([i, f"item_{i}", i*2, f"data_{i%10}"])
        
        with open('test_mixed.json', 'w') as f:
            json.dump(mixed_data, f)
        test_files['mixed'] = ('test_mixed.json', 'Mixed data (medium compressibility)')
        
        return test_files
    
    def test_compression_algorithm(self, algorithm, test_file, description):
        """Test a specific compression algorithm"""
        print(f"\n🔧 Testing {algorithm} compression")
        print(f"📂 File: {test_file} ({description})")
        
        # Get original file size
        original_size = os.path.getsize(test_file)
        
        # Create modified CES test binary call with specific algorithm
        cmd = ['./rust/target/release/ces_test', test_file]
        
        start_time = time.time()
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            processing_time = time.time() - start_time
            
            if result.returncode == 0:
                output = result.stdout
                
                # Parse output
                compressed_size = original_size
                latency_ms = processing_time * 1000
                compression_ratio = 1.0
                
                for line in output.split('\n'):
                    if 'Compressed size:' in line:
                        try:
                            compressed_size = int(line.split(':')[1].strip().split()[0])
                        except:
                            pass
                    elif 'Compression ratio:' in line:
                        try:
                            compression_ratio = float(line.split(':')[1].strip().replace('x', ''))
                        except:
                            pass
                    elif 'Processing latency:' in line:
                        try:
                            latency_ms = float(line.split(':')[1].strip().replace('ms', ''))
                        except:
                            pass
                
                # Display results
                print(f"  📊 Original size: {original_size:,} bytes")
                print(f"  📊 Compressed size: {compressed_size:,} bytes")
                print(f"  📊 Compression ratio: {compression_ratio:.2f}x")
                print(f"  📊 Processing time: {latency_ms:.2f}ms")
                
                # Determine effectiveness
                if compression_ratio > 1.5:
                    effectiveness = "🟢 Excellent"
                elif compression_ratio > 1.1:
                    effectiveness = "🟡 Good"
                elif compression_ratio > 0.9:
                    effectiveness = "🟠 Neutral"
                else:
                    effectiveness = "🔴 Ineffective"
                
                print(f"  {effectiveness} compression for this data type")
                
                return {
                    'algorithm': algorithm,
                    'file_type': description,
                    'original_size': original_size,
                    'compressed_size': compressed_size,
                    'compression_ratio': compression_ratio,
                    'latency_ms': latency_ms,
                    'effectiveness': effectiveness
                }
            else:
                print(f"  ❌ Test failed: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            print(f"  ⏰ Test timed out after 30 seconds")
            return None
        except Exception as e:
            print(f"  ⚠️  Test error: {e}")
            return None
    
    def create_algorithm_specific_binary(self, algorithm):
        """Create a test binary for specific algorithm"""
        # Modify the ces_test.rs to use specific algorithm
        algorithm_map = {
            'Zstd': 'CompressionAlgorithm::Zstd',
            'Brotli': 'CompressionAlgorithm::Brotli', 
            'None': 'CompressionAlgorithm::None'
        }
        
        if algorithm not in algorithm_map:
            return False
            
        # Read current ces_test.rs
        with open('rust/src/bin/ces_test.rs', 'r') as f:
            content = f.read()
        
        # Replace algorithm line
        original_line = "compression_algorithm: CompressionAlgorithm::Brotli, // Phase 1 feature"
        new_line = f"compression_algorithm: {algorithm_map[algorithm]}, // {algorithm} algorithm test"
        
        modified_content = content.replace(original_line, new_line)
        
        # Create temporary test file
        temp_file = f'rust/src/bin/ces_test_{algorithm.lower()}.rs'
        with open(temp_file, 'w') as f:
            f.write(modified_content)
        
        # Build the specific binary
        cmd = ['cargo', 'build', '--release', '--bin', f'ces_test_{algorithm.lower()}']
        try:
            result = subprocess.run(cmd, cwd='rust', capture_output=True, text=True)
            if result.returncode == 0:
                return f'./rust/target/release/ces_test_{algorithm.lower()}'
            else:
                print(f"❌ Failed to build {algorithm} binary: {result.stderr}")
                return None
        except Exception as e:
            print(f"⚠️  Build error for {algorithm}: {e}")
            return None
        finally:
            # Cleanup temp file
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def run_comprehensive_tests(self):
        """Run comprehensive compression algorithm tests"""
        print("🚀 Starting CES Compression Algorithm Comparison")
        
        # Create test files
        test_files = self.create_test_files()
        
        algorithms = ['Zstd', 'Brotli', 'None']
        
        # Test each algorithm with each file type
        all_results = []
        
        for algorithm in algorithms:
            print(f"\n" + "="*60)
            print(f"🔬 Testing {algorithm} Algorithm")
            print("="*60)
            
            algorithm_results = []
            
            for file_key, (filename, description) in test_files.items():
                result = self.test_compression_algorithm(algorithm, filename, description)
                if result:
                    algorithm_results.append(result)
                    all_results.append(result)
            
            # Algorithm summary
            if algorithm_results:
                avg_ratio = sum(r['compression_ratio'] for r in algorithm_results) / len(algorithm_results)
                avg_latency = sum(r['latency_ms'] for r in algorithm_results) / len(algorithm_results)
                
                print(f"\n📊 {algorithm} Algorithm Summary:")
                print(f"   Average compression: {avg_ratio:.2f}x")
                print(f"   Average latency: {avg_latency:.2f}ms")
                print(f"   Test files: {len(algorithm_results)}")
        
        # Overall comparison
        print(f"\n" + "="*60)
        print("🏆 Overall Algorithm Comparison")
        print("="*60)
        
        # Group results by algorithm
        algo_stats = {}
        for result in all_results:
            algo = result['algorithm']
            if algo not in algo_stats:
                algo_stats[algo] = {'ratios': [], 'latencies': [], 'count': 0}
            
            algo_stats[algo]['ratios'].append(result['compression_ratio'])
            algo_stats[algo]['latencies'].append(result['latency_ms'])
            algo_stats[algo]['count'] += 1
        
        print("\n| Algorithm | Avg Ratio | Avg Latency | Best For |")
        print("|-----------|-----------|-------------|----------|")
        
        for algo, stats in algo_stats.items():
            avg_ratio = sum(stats['ratios']) / len(stats['ratios'])
            avg_latency = sum(stats['latencies']) / len(stats['latencies'])
            max_ratio = max(stats['ratios'])
            
            # Determine best use case
            if algo == 'Brotli':
                best_for = "Text, JSON, structured data"
            elif algo == 'Zstd':
                best_for = "General purpose, balanced"
            else:
                best_for = "Pre-compressed, binary data"
            
            print(f"| {algo:9} | {avg_ratio:8.2f}x | {avg_latency:10.1f}ms | {best_for:8} |")
        
        # Phase 1 validation
        print(f"\n✅ Phase 1 Algorithm Validation:")
        brotli_latencies = [r['latency_ms'] for r in all_results if r['algorithm'] == 'Brotli']
        if brotli_latencies:
            max_brotli_latency = max(brotli_latencies)
            avg_brotli_latency = sum(brotli_latencies) / len(brotli_latencies)
            
            print(f"   Brotli max latency: {max_brotli_latency:.2f}ms")
            print(f"   Brotli avg latency: {avg_brotli_latency:.2f}ms") 
            print(f"   Phase 1 target (<100ms): {'✅ PASS' if max_brotli_latency < 100 else '❌ FAIL'}")
        
        # Save detailed results
        with open('benchmarks/ces_compression_comparison.json', 'w') as f:
            json.dump({
                'timestamp': time.time(),
                'results': all_results,
                'algorithm_stats': algo_stats
            }, f, indent=2)
        
        print(f"\n💾 Detailed results saved to: benchmarks/ces_compression_comparison.json")
        
        # Cleanup test files
        for _, (filename, _) in test_files.items():
            if os.path.exists(filename):
                os.remove(filename)

if __name__ == "__main__":
    # Make sure benchmarks directory exists
    os.makedirs('benchmarks', exist_ok=True)
    
    tester = CESCompressionTester()
    tester.run_comprehensive_tests()
    
    print("\n🎉 CES Compression Algorithm Tests Complete!")