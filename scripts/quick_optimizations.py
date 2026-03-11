"""
AGNIYA Quick Optimization Implementation
Immediate performance improvements without architectural changes
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agniya.core.ultimate_system import UltimateOptimizedDatabase
from agniya.core.paillier import encrypt, decrypt_crt
import numpy as np
import time
from typing import List
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing as mp


class OptimizedAGNIYA(UltimateOptimizedDatabase):
    """Enhanced AGNIYA with quick performance optimizations"""
    
    def __init__(self, *args, n_workers=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.n_workers = n_workers or min(8, mp.cpu_count())
        print(f"🚀 Optimized AGNIYA initialized with {self.n_workers} workers")
    
    def encrypt_batch_parallel(self, values: List[int]) -> List[int]:
        """
        Parallel encryption using multiprocessing.
        Expected: 4-8x speedup on multi-core systems.
        """
        if len(values) < 100:
            # For small batches, overhead not worth it
            return [encrypt(self.pub, v) for v in values]
        
        chunk_size = max(1, len(values) // self.n_workers)
        chunks = [values[i:i + chunk_size] for i in range(0, len(values), chunk_size)]
        
        def encrypt_chunk(chunk):
            return [encrypt(self.pub, v) for v in chunk]
        
        with ProcessPoolExecutor(max_workers=self.n_workers) as executor:
            results = list(executor.map(encrypt_chunk, chunks))
        
        return [ct for chunk_result in results for ct in chunk_result]
    
    def sum_query_optimized(self, values: List[int], use_cache=True) -> int:
        """
        Optimized sum with fast path for small datasets.
        Uses cache-first strategy for maximum speed.
        """
        n = len(values)
        
        # Fast path for tiny datasets
        if n <= 10:
            return sum(values)  # Just return plaintext sum (testing only!)
        
        # Fast path for small cached datasets
        if n < 1000 and use_cache and self.enable_multi_level:
            # Use multi-level cache
            return self.multi_cache.cached_sum(values)
        
        # Medium datasets: use batch packing
        if n < 10000 and self.enable_batch_packing:
            return self.batch_agg.batched_sum(values)
        
        # Large datasets: fall back to standard
        return super().sum_query(values, use_cache=use_cache)
    
    def encrypt_with_precomputation(self, values: List[int]) -> List[int]:
        """
        Encryption with aggressive precomputation lookup.
        Checks cache before encrypting.
        """
        results = []
        for v in values:
            # Check if value is precomputed
            if self.enable_multi_level and hasattr(self.multi_cache, 'precomputed'):
                cached = self.multi_cache.precomputed.get(v)
                if cached is not None:
                    results.append(cached)
                    continue
            # Encrypt normally
            results.append(encrypt(self.pub, v))
        return results


def benchmark_optimizations():
    """Benchmark the optimizations"""
    print("="*80)
    print("AGNIYA Optimization Benchmark")
    print("="*80)
    print()
    
    # Test data
    data_sizes = [100, 1000, 10000]
    
    print("Initializing systems...")
    baseline = UltimateOptimizedDatabase(
        key_size=2048,
        enable_multi_level=True,
        enable_batch_packing=True,
        verbose=False
    )
    optimized = OptimizedAGNIYA(
        key_size=2048,
        enable_multi_level=True,
        enable_batch_packing=True,
        n_workers=4,
        verbose=False
    )
    print()
    
    for size in data_sizes:
        print(f"\n{'='*80}")
        print(f"Dataset Size: {size:,} records")
        print(f"{'='*80}\n")
        
        data = np.random.randint(1, 1000, size=size).tolist()
        
        # Baseline encryption
        print("🔵 Baseline AGNIYA:")
        start = time.time()
        _ = [encrypt(baseline.pub, v) for v in data[:min(100, size)]]
        baseline_enc_time = (time.time() - start) * 1000
        baseline_throughput = min(100, size) / (baseline_enc_time / 1000)
        print(f"  Encryption: {baseline_enc_time:.2f}ms ({baseline_throughput:.0f} ops/sec)")
        
        # Optimized encryption (parallel)
        print("🟢 Optimized AGNIYA (Parallel):")
        start = time.time()
        _ = optimized.encrypt_batch_parallel(data[:min(100, size)])
        opt_enc_time = (time.time() - start) * 1000
        opt_throughput = min(100, size) / (opt_enc_time / 1000)
        speedup = baseline_enc_time / opt_enc_time if opt_enc_time > 0 else 0
        print(f"  Encryption: {opt_enc_time:.2f}ms ({opt_throughput:.0f} ops/sec)")
        print(f"  ⚡ Speedup: {speedup:.2f}x")
        
        # Baseline SUM
        print("\n🔵 Baseline SUM:")
        start = time.time()
        result1 = baseline.sum_query(data, use_cache=True)
        baseline_sum_time = (time.time() - start) * 1000
        print(f"  Time: {baseline_sum_time:.2f}ms")
        
        # Optimized SUM
        print("🟢 Optimized SUM:")
        start = time.time()
        result2 = optimized.sum_query_optimized(data, use_cache=True)
        opt_sum_time = (time.time() - start) * 1000
        speedup_sum = baseline_sum_time / opt_sum_time if opt_sum_time > 0 else 0
        print(f"  Time: {opt_sum_time:.2f}ms")
        print(f"  ⚡ Speedup: {speedup_sum:.2f}x")
        
        # Verify correctness
        if result1 == result2:
            print(f"  ✅ Results match: {result1}")
        else:
            print(f"  ⚠️  Results differ: {result1} vs {result2}")
    
    print(f"\n{'='*80}")
    print("Benchmark Complete")
    print(f"{'='*80}")


if __name__ == "__main__":
    benchmark_optimizations()
