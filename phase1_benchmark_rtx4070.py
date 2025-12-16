# phase1_benchmark_rtx4070.py
"""
Phase 1: RTX 4070 Laptop GPU Benchmarking

Comprehensive benchmarks to verify GPU capabilities and identify bottlenecks
"""

import pycuda.driver as cuda
import numpy as np
import time
from typing import Dict, List
import sys


class RTX4070Benchmarks:
    """Benchmark suite for RTX 4070 laptop GPU"""
    
    def __init__(self, verbose=True):
        self.verbose = verbose
        self.results = {}
        self.device = cuda.Device(0)
        
        if self.verbose:
            print("\n" + "=" * 70)
            print("RTX 4070 LAPTOP GPU BENCHMARK SUITE")
            print("=" * 70)
            
            # Get device properties
            props = self.device.get_attributes()
            device_name = self.device.name().decode('utf-8')
            
            print(f"\nDevice: {device_name}")
            print(f"Compute Capability: {self.device.compute_capability()}")
            
            free, total = cuda.mem_get_info()
            print(f"Total Memory: {total/1e9:.2f}GB")
            print(f"Free Memory: {free/1e9:.2f}GB")
            print("\n" + "=" * 70)
    
    def benchmark_memory_bandwidth(self, num_iterations=10) -> Dict[str, float]:
        """Benchmark GPU memory bandwidth"""
        
        if self.verbose:
            print("\n1. MEMORY BANDWIDTH TEST")
            print("-" * 70)
        
        results = {}
        sizes_mb = [10, 50, 100, 500, 1000]
        
        for size_mb in sizes_mb:
            size_bytes = int(size_mb * 1e6)
            
            # Allocate GPU memory
            gpu_data = cuda.mem_alloc(size_bytes)
            
            # Create test data
            host_data = np.random.bytes(size_bytes)
            
            # Warm-up
            cuda.memcpy_htod(gpu_data, host_data)
            cuda.Context.synchronize()
            
            # Host-to-Device bandwidth
            start = time.perf_counter()
            for _ in range(num_iterations):
                cuda.memcpy_htod(gpu_data, host_data)
            cuda.Context.synchronize()
            h2d_time = time.perf_counter() - start
            h2d_bw_gb_s = (size_mb * num_iterations) / (h2d_time * 1000)
            
            # Device-to-Host bandwidth
            result_data = np.empty(size_bytes // 4, dtype=np.uint32)
            
            start = time.perf_counter()
            for _ in range(num_iterations):
                cuda.memcpy_dtoh(result_data, gpu_data)
            cuda.Context.synchronize()
            d2h_time = time.perf_counter() - start
            d2h_bw_gb_s = (size_mb * num_iterations) / (d2h_time * 1000)
            
            results[f'{size_mb}mb'] = {
                'h2d_gb_s': h2d_bw_gb_s,
                'd2h_gb_s': d2h_bw_gb_s,
                'avg_gb_s': (h2d_bw_gb_s + d2h_bw_gb_s) / 2
            }
            
            if self.verbose:
                print(f"  {size_mb:4d}MB: H2D={h2d_bw_gb_s:6.1f} GB/s, "
                      f"D2H={d2h_bw_gb_s:6.1f} GB/s, "
                      f"AVG={results[f'{size_mb}mb']['avg_gb_s']:6.1f} GB/s")
            
            gpu_data.free()
        
        self.results['memory_bandwidth'] = results
        return results
    
    def benchmark_memory_latency(self, num_iterations=100) -> Dict[str, float]:
        """Benchmark GPU memory access latency"""
        
        if self.verbose:
            print("\n2. MEMORY LATENCY TEST")
            print("-" * 70)
        
        results = {}
        
        # Allocate small buffer for latency test
        buffer_size = int(1e6)  # 1MB
        gpu_buffer = cuda.mem_alloc(buffer_size)
        
        # Test 1: Allocation latency
        start = time.perf_counter()
        alloc_ptrs = []
        for _ in range(num_iterations):
            ptr = cuda.mem_alloc(100000)  # 100KB each
            alloc_ptrs.append(ptr)
        alloc_time_ms = (time.perf_counter() - start) * 1000
        alloc_latency_us = (alloc_time_ms * 1000) / num_iterations
        
        if self.verbose:
            print(f"  Allocation: {alloc_latency_us:.2f} µs per allocation")
        results['allocation_us'] = alloc_latency_us
        
        # Free allocations
        for ptr in alloc_ptrs:
            ptr.free()
        
        # Test 2: Synchronization latency
        sync_times = []
        for _ in range(num_iterations):
            start = time.perf_counter()
            cuda.Context.synchronize()
            sync_times.append((time.perf_counter() - start) * 1000)
        
        avg_sync_ms = np.mean(sync_times)
        max_sync_ms = np.max(sync_times)
        
        if self.verbose:
            print(f"  Synchronization: {avg_sync_ms:.3f} ms (avg), "
                  f"{max_sync_ms:.3f} ms (max)")
        
        results['sync_avg_ms'] = avg_sync_ms
        results['sync_max_ms'] = max_sync_ms
        
        # Test 3: Context switch latency (if multiple contexts)
        # Skip for single context
        
        gpu_buffer.free()
        self.results['memory_latency'] = results
        return results
    
    def benchmark_pci_express(self, num_iterations=20) -> Dict[str, float]:
        """Benchmark PCIe bandwidth (specific to laptop GPU)"""
        
        if self.verbose:
            print("\n3. PCIe BANDWIDTH TEST (CPU-GPU)")
            print("-" * 70)
        
        results = {}
        
        # PCIe bandwidth depends on CPU↔GPU connection
        # Laptop GPUs often have narrower paths than desktop
        
        sizes_mb = [1, 10, 100]
        
        for size_mb in sizes_mb:
            size_bytes = int(size_mb * 1e6)
            gpu_mem = cuda.mem_alloc(size_bytes)
            host_mem = np.random.bytes(size_bytes)
            
            # Measure PCIe H2D
            start = time.perf_counter()
            for _ in range(num_iterations):
                cuda.memcpy_htod(gpu_mem, host_mem)
            cuda.Context.synchronize()
            pcie_h2d_bw = (size_mb * num_iterations) / \
                         ((time.perf_counter() - start) * 1000)
            
            results[f'{size_mb}mb_pcie_h2d_gb_s'] = pcie_h2d_bw
            
            if self.verbose:
                print(f"  {size_mb}MB PCIe H2D: {pcie_h2d_bw:.1f} GB/s")
            
            gpu_mem.free()
        
        self.results['pcie'] = results
        return results
    
    def benchmark_memory_types(self) -> Dict[str, float]:
        """Benchmark different GPU memory types"""
        
        if self.verbose:
            print("\n4. GPU MEMORY TYPES PERFORMANCE")
            print("-" * 70)
        
        results = {}
        
        # Get GPU memory properties
        props = self.device.get_attributes()
        
        # Memory clock
        memory_clock = self.device.get_attribute(cuda.device_attribute.MEMORY_CLOCK_RATE)
        results['memory_clock_mhz'] = memory_clock / 1000
        
        # L2 cache size
        l2_cache = self.device.get_attribute(cuda.device_attribute.L2_CACHE_SIZE)
        results['l2_cache_mb'] = l2_cache / 1e6
        
        if self.verbose:
            print(f"  Memory Clock: {results['memory_clock_mhz']:.0f} MHz")
            print(f"  L2 Cache: {results['l2_cache_mb']:.1f} MB")
        
        self.results['memory_types'] = results
        return results
    
    def benchmark_stream_performance(self, num_streams=4) -> Dict[str, float]:
        """Benchmark concurrent stream performance"""
        
        if self.verbose:
            print("\n5. CONCURRENT STREAMS TEST")
            print("-" * 70)
        
        results = {}
        
        # Create multiple streams
        streams = [cuda.Stream() for _ in range(num_streams)]
        
        # Allocate memory for each stream
        buffers = [cuda.mem_alloc(10000000) for _ in range(num_streams)]  # 10MB each
        
        # Create host data
        host_data = np.random.bytes(10000000)
        
        # Concurrent transfers
        start = time.perf_counter()
        for i, (stream, buffer) in enumerate(zip(streams, buffers)):
            cuda.memcpy_htod_async(buffer, host_data, stream)
        
        for stream in streams:
            stream.synchronize()
        concurrent_time_ms = (time.perf_counter() - start) * 1000
        
        # Sequential transfers for comparison
        start = time.perf_counter()
        for buffer in buffers:
            cuda.memcpy_htod(buffer, host_data)
        cuda.Context.synchronize()
        sequential_time_ms = (time.perf_counter() - start) * 1000
        
        speedup = sequential_time_ms / concurrent_time_ms
        
        if self.verbose:
            print(f"  Sequential ({num_streams} transfers): {sequential_time_ms:.2f} ms")
            print(f"  Concurrent ({num_streams} streams): {concurrent_time_ms:.2f} ms")
            print(f"  Speedup: {speedup:.2f}×")
        
        results['num_streams'] = num_streams
        results['concurrent_speedup'] = speedup
        
        # Cleanup
        for buffer in buffers:
            buffer.free()
        
        self.results['streams'] = results
        return results
    
    def print_summary(self):
        """Print benchmark summary"""
        print("\n\n" + "=" * 70)
        print("BENCHMARK SUMMARY")
        print("=" * 70)
        
        if 'memory_bandwidth' in self.results:
            mb_results = self.results['memory_bandwidth']
            best_1gb = mb_results['1000mb']['avg_gb_s']
            print(f"✓ Max Memory Bandwidth (1GB): {best_1gb:.1f} GB/s")
        
        if 'memory_latency' in self.results:
            lat_results = self.results['memory_latency']
            print(f"✓ Sync Latency: {lat_results['sync_avg_ms']:.3f} ms avg")
        
        if 'streams' in self.results:
            stream_results = self.results['streams']
            print(f"✓ Concurrent Streams Speedup: {stream_results['concurrent_speedup']:.2f}×")
        
        if 'memory_types' in self.results:
            mem_results = self.results['memory_types']
            print(f"✓ Memory Clock: {mem_results['memory_clock_mhz']:.0f} MHz")
        
        print("\n" + "=" * 70)
        print("✓ All benchmarks completed successfully!")
        print("=" * 70 + "\n")


def run_benchmarks():
    """Run complete benchmark suite"""
    
    try:
        benchmarks = RTX4070Benchmarks(verbose=True)
        
        # Run all benchmarks
        benchmarks.benchmark_memory_bandwidth()
        benchmarks.benchmark_memory_latency()
        benchmarks.benchmark_pci_express()
        benchmarks.benchmark_memory_types()
        benchmarks.benchmark_stream_performance(num_streams=4)
        
        # Print summary
        benchmarks.print_summary()
        
        return True
    
    except Exception as e:
        print(f"\n✗ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_benchmarks()
    sys.exit(0 if success else 1)
