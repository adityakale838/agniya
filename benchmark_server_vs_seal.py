"""
Compare AGNIYA server_optimized.py performance against Microsoft SEAL

This script benchmarks:
1. AGNIYA Ultimate Optimized System (with all optimizations)
2. Microsoft SEAL (via TenSEAL)

Metrics:
- Encryption time
- Query time (SUM, AVG)
- Throughput (ops/sec)
- Total end-to-end time
"""

import time
import sys
import numpy as np
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import AGNIYA
from agniya.core.ultimate_system import UltimateOptimizedDatabase

# Try importing SEAL
try:
    import tenseal as ts
    SEAL_AVAILABLE = True
except ImportError:
    SEAL_AVAILABLE = False
    print("⚠️  TenSEAL (Microsoft SEAL wrapper) not installed")
    print("   Install with: pip install tenseal")
    print()


def benchmark_agniya(data, verbose=True):
    """Benchmark AGNIYA Ultimate Optimized System."""
    if verbose:
        print("\n" + "="*70)
        print("🚀 AGNIYA ULTIMATE OPTIMIZED SYSTEM")
        print("="*70)
    
    # Initialize with all optimizations
    init_start = time.time()
    db = UltimateOptimizedDatabase(
        key_size=2048,
        cache_size=500000,
        enable_multi_level=True,
        enable_batch_packing=True,
        enable_probabilistic=True,
        enable_gpu_encryption=True,
        enable_gpu_pipeline=True,
        enable_jit=True,
        verbose=False
    )
    init_time = time.time() - init_start
    
    if verbose:
        print(f"Initialization: {init_time:.2f}s")
    
    # Test SUM query (lazy encryption with cache)
    sum_start = time.time()
    result = db.sum_query(data)
    sum_time = time.time() - sum_start
    sum_throughput = len(data) / sum_time
    
    if verbose:
        print(f"\nSUM Query:")
        print(f"  Time: {sum_time*1000:.2f}ms")
        print(f"  Throughput: {sum_throughput:.0f} ops/sec")
        print(f"  Result: {result:,}")
    
    # Test AVG query
    avg_start = time.time()
    sum_val = db.sum_query(data)
    avg_result = sum_val / len(data)
    avg_time = time.time() - avg_start
    avg_throughput = len(data) / avg_time
    
    if verbose:
        print(f"\nAVG Query:")
        print(f"  Time: {avg_time*1000:.2f}ms")
        print(f"  Throughput: {avg_throughput:.0f} ops/sec")
        print(f"  Result: {avg_result:.2f}")
    
    total_time = init_time + sum_time + avg_time
    
    return {
        'init_time': init_time,
        'sum_time': sum_time,
        'sum_throughput': sum_throughput,
        'avg_time': avg_time,
        'avg_throughput': avg_throughput,
        'total_time': total_time
    }


def benchmark_seal(data, verbose=True):
    """Benchmark Microsoft SEAL (via TenSEAL)."""
    if not SEAL_AVAILABLE:
        return None
    
    if verbose:
        print("\n" + "="*70)
        print("🔐 MICROSOFT SEAL (via TenSEAL)")
        print("="*70)
    
    # Initialize SEAL context (BFV scheme for integers)
    init_start = time.time()
    context = ts.context(
        ts.SCHEME_TYPE.BFV,
        poly_modulus_degree=8192,  # Security parameter
        plain_modulus=1032193
    )
    context.generate_galois_keys()
    context.global_scale = 2**40
    init_time = time.time() - init_start
    
    if verbose:
        print(f"Initialization: {init_time:.2f}s")
    
    # Encrypt data
    encrypt_start = time.time()
    encrypted_data = [ts.bfv_vector(context, [int(x)]) for x in data]
    encrypt_time = time.time() - encrypt_start
    encrypt_throughput = len(data) / encrypt_time
    
    if verbose:
        print(f"\nEncryption:")
        print(f"  Time: {encrypt_time:.2f}s")
        print(f"  Throughput: {encrypt_throughput:.0f} ops/sec")
    
    # Test SUM (homomorphic addition)
    sum_start = time.time()
    result = encrypted_data[0]
    for enc_val in encrypted_data[1:]:
        result = result + enc_val
    sum_ct = result
    sum_result = sum_ct.decrypt()[0]
    sum_time = time.time() - sum_start
    sum_throughput = len(data) / sum_time
    
    if verbose:
        print(f"\nSUM Query:")
        print(f"  Time: {sum_time*1000:.2f}ms")
        print(f"  Throughput: {sum_throughput:.0f} ops/sec")
        print(f"  Result: {sum_result:,}")
    
    # Test AVG (need to decrypt sum and divide)
    avg_start = time.time()
    avg_result = sum_result / len(data)
    avg_time = time.time() - avg_start
    
    if verbose:
        print(f"\nAVG Query:")
        print(f"  Time: {avg_time*1000:.2f}ms (decrypt + divide)")
        print(f"  Result: {avg_result:.2f}")
    
    total_time = init_time + encrypt_time + sum_time + avg_time
    
    return {
        'init_time': init_time,
        'encrypt_time': encrypt_time,
        'encrypt_throughput': encrypt_throughput,
        'sum_time': sum_time,
        'sum_throughput': sum_throughput,
        'avg_time': avg_time,
        'total_time': total_time
    }


def run_comparison(data_sizes=[100, 1000, 10000]):
    """Run comparison across multiple data sizes."""
    
    print("\n" + "="*70)
    print("AGNIYA vs MICROSOFT SEAL - Performance Comparison")
    print("="*70)
    print(f"\nTest Configuration:")
    print(f"  - Data sizes: {data_sizes}")
    print(f"  - Value range: 1-1000")
    print(f"  - Operations: SUM, AVG")
    print(f"  - Security: 2048-bit keys")
    
    all_results = []
    
    for size in data_sizes:
        print(f"\n\n{'#'*70}")
        print(f"DATASET SIZE: {size:,} records")
        print(f"{'#'*70}")
        
        # Generate random data
        data = np.random.randint(1, 1000, size=size).tolist()
        
        # Benchmark AGNIYA
        agniya_results = benchmark_agniya(data, verbose=True)
        
        # Benchmark SEAL
        seal_results = benchmark_seal(data, verbose=True) if SEAL_AVAILABLE else None
        
        # Store results
        all_results.append({
            'size': size,
            'agniya': agniya_results,
            'seal': seal_results
        })
        
        # Print comparison
        if seal_results:
            print(f"\n{'='*70}")
            print(f"COMPARISON SUMMARY - {size:,} records")
            print(f"{'='*70}")
            
            print(f"\n📊 Initialization Time:")
            print(f"  AGNIYA: {agniya_results['init_time']:.2f}s")
            print(f"  SEAL:   {seal_results['init_time']:.2f}s")
            speedup = seal_results['init_time'] / agniya_results['init_time']
            print(f"  {'🚀 AGNIYA faster' if speedup > 1 else '⚠️  SEAL faster'}: {speedup:.2f}x")
            
            print(f"\n📊 SUM Query:")
            print(f"  AGNIYA: {agniya_results['sum_time']*1000:.2f}ms ({agniya_results['sum_throughput']:.0f} ops/sec)")
            print(f"  SEAL:   {seal_results['sum_time']*1000:.2f}ms ({seal_results['sum_throughput']:.0f} ops/sec)")
            speedup = seal_results['sum_time'] / agniya_results['sum_time']
            print(f"  {'🚀 AGNIYA faster' if speedup > 1 else '⚠️  SEAL faster'}: {speedup:.2f}x")
            
            print(f"\n📊 AVG Query:")
            print(f"  AGNIYA: {agniya_results['avg_time']*1000:.2f}ms ({agniya_results['avg_throughput']:.0f} ops/sec)")
            print(f"  SEAL:   {seal_results['avg_time']*1000:.2f}ms")
            speedup = seal_results['avg_time'] / agniya_results['avg_time']
            print(f"  {'🚀 AGNIYA faster' if speedup > 1 else '⚠️  SEAL faster'}: {speedup:.2f}x")
            
            print(f"\n📊 Total Time:")
            print(f"  AGNIYA: {agniya_results['total_time']:.2f}s")
            print(f"  SEAL:   {seal_results['total_time']:.2f}s")
            speedup = seal_results['total_time'] / agniya_results['total_time']
            print(f"  {'🚀 AGNIYA faster' if speedup > 1 else '⚠️  SEAL faster'}: {speedup:.2f}x")
    
    # Final summary
    print(f"\n\n{'#'*70}")
    print("FINAL SUMMARY")
    print(f"{'#'*70}")
    
    if all_results and all_results[0]['seal']:
        for result in all_results:
            size = result['size']
            agniya = result['agniya']
            seal = result['seal']
            
            sum_speedup = seal['sum_time'] / agniya['sum_time']
            avg_speedup = seal['avg_time'] / agniya['avg_time']
            total_speedup = seal['total_time'] / agniya['total_time']
            
            print(f"\n{size:,} records:")
            print(f"  SUM speedup:   {sum_speedup:.2f}x")
            print(f"  AVG speedup:   {avg_speedup:.2f}x")
            print(f"  Total speedup: {total_speedup:.2f}x")
    else:
        print("\nSEAL not available for comparison.")
        print("Install with: pip install tenseal")


if __name__ == '__main__':
    # Run with multiple dataset sizes
    run_comparison(data_sizes=[100, 1000, 10000])
    
    print("\n" + "="*70)
    print("✅ Benchmark complete!")
    print("="*70)
