"""
Part 1: Micro-Benchmarks - Individual Component Performance

Tests each optimization layer independently to measure isolated impact.
This generates data for:
- Graph 1.1: Performance Breakdown by Optimization Layer
- Graph 1.2: Latency Distribution

Critical Metrics:
- Baseline encryption: ops/sec
- Each layer's speedup multiplier
- Cumulative performance improvement
"""

import logging
import time
from typing import Dict, Any, List
import numpy as np

from agniya.core.paillier import generate_keypair, encrypt, decrypt
from agniya.core.optimized_paillier import OptimizedPaillier
from evaluation_suite.benchmarks.utils import (
    run_benchmark,
    BenchmarkResult,
    ProgressTracker,
    calculate_speedup,
    measure_memory_usage
)


logger = logging.getLogger(__name__)


def benchmark_baseline_encryption(key_size: int = 2048, repetitions: int = 10) -> BenchmarkResult:
    """
    Benchmark baseline Paillier encryption without any optimizations.
    
    Args:
        key_size: RSA modulus size in bits
        repetitions: Number of test runs
        
    Returns:
        BenchmarkResult with encryption performance
    """
    logger.info(f"Benchmarking baseline encryption ({key_size}-bit)")
    
    # Generate keys
    pub, priv = generate_keypair(bit_length=key_size)
    
    # Test data
    test_values = list(range(100))
    
    def encrypt_batch():
        return [encrypt(pub, val) for val in test_values]
    
    result = run_benchmark(
        encrypt_batch,
        repetitions=repetitions,
        warmup=2,
        unit='ops/sec'
    )
    
    result.name = f"baseline_encryption_{key_size}bit"
    result.category = "micro_benchmarks"
    result.metadata = {
        'key_size': key_size,
        'num_values': len(test_values),
        'optimization_level': 'none'
    }
    
    logger.info(f"[OK] Baseline: {result.mean:.2f} ops/sec")
    return result


def benchmark_gpu_only(key_size: int = 2048, repetitions: int = 10) -> BenchmarkResult:
    """
    Benchmark with GPU acceleration only (no cache, no other optimizations).
    
    Args:
        key_size: RSA modulus size in bits
        repetitions: Number of test runs
        
    Returns:
        BenchmarkResult with GPU performance
    """
    logger.info(f"Benchmarking GPU-only encryption ({key_size}-bit)")
    
    pub, priv = generate_keypair(bit_length=key_size)
    
    # GPU-enabled encryptor with all other optimizations disabled
    try:
        opt = OptimizedPaillier(
            pub, priv,
            enable_cache=False,
            enable_precompute=False,
            enable_query_cache=False,
            enable_gpu=True,
            enable_gpu_homomorphic=True
        )
        
        test_values = list(range(100))
        
        def encrypt_batch():
            return [opt.encrypt(val) for val in test_values]
        
        result = run_benchmark(
            encrypt_batch,
            repetitions=repetitions,
            warmup=2,
            unit='ops/sec'
        )
        
        result.name = f"gpu_only_{key_size}bit"
        result.category = "micro_benchmarks"
        result.metadata = {
            'key_size': key_size,
            'num_values': len(test_values),
            'optimization_level': 'gpu_only',
            'gpu_available': opt.gpu_available
        }
        
        logger.info(f"[OK] GPU-only: {result.mean:.2f} ops/sec")
        return result
        
    except Exception as e:
        logger.warning(f"GPU benchmark failed: {str(e)}")
        # Return baseline if GPU unavailable
        return benchmark_baseline_encryption(key_size, repetitions)


def benchmark_cache_l1_only(key_size: int = 2048, repetitions: int = 10) -> BenchmarkResult:
    """
    Benchmark with L1 cache only (100 most frequent values).
    
    Args:
        key_size: RSA modulus size in bits
        repetitions: Number of test runs
        
    Returns:
        BenchmarkResult with L1 cache performance
    """
    logger.info(f"Benchmarking L1 cache ({key_size}-bit)")
    
    pub, priv = generate_keypair(bit_length=key_size)
    
    opt = OptimizedPaillier(
        pub, priv,
        enable_cache=True,
        enable_precompute=False,
        enable_query_cache=False,
        enable_gpu=False,
        cache_size_l1=100,
        cache_size_l2=0  # Disable L2
    )
    
    # Warmup cache with values 0-99
    for i in range(100):
        opt.encrypt(i)
    
    # Test with cached values
    test_values = list(range(50)) * 2  # Repeat to ensure cache hits
    
    def encrypt_batch():
        return [opt.encrypt(val) for val in test_values]
    
    result = run_benchmark(
        encrypt_batch,
        repetitions=repetitions,
        warmup=1,  # Already warmed up
        unit='ops/sec'
    )
    
    # Get cache stats
    stats = opt.get_stats() if hasattr(opt, 'get_stats') else {}
    
    result.name = f"cache_l1_{key_size}bit"
    result.category = "micro_benchmarks"
    result.metadata = {
        'key_size': key_size,
        'num_values': len(test_values),
        'optimization_level': 'cache_l1',
        'cache_hit_rate': stats.get('cache_hit_rate', 'unknown')
    }
    
    logger.info(f"[OK] L1 Cache: {result.mean:.2f} ops/sec")
    return result


def benchmark_all_optimizations(key_size: int = 2048, repetitions: int = 10) -> BenchmarkResult:
    """
    Benchmark with ALL optimizations enabled (full stack).
    
    Args:
        key_size: RSA modulus size in bits
        repetitions: Number of test runs
        
    Returns:
        BenchmarkResult with full-stack performance
    """
    logger.info(f"Benchmarking full optimization stack ({key_size}-bit)")
    
    pub, priv = generate_keypair(bit_length=key_size)
    
    opt = OptimizedPaillier(
        pub, priv,
        enable_cache=True,
        enable_precompute=True,
        enable_query_cache=True,
        enable_gpu=True,
        enable_gpu_homomorphic=True,
        cache_size_l1=100,
        cache_size_l2=1000
    )
    
    # Warmup
    for i in range(100):
        opt.encrypt(i)
    
    test_values = list(range(50)) * 2
    
    def encrypt_batch():
        return [opt.encrypt(val) for val in test_values]
    
    result = run_benchmark(
        encrypt_batch,
        repetitions=repetitions,
        warmup=1,
        unit='ops/sec'
    )
    
    stats = opt.get_stats() if hasattr(opt, 'get_stats') else {}
    
    result.name = f"full_stack_{key_size}bit"
    result.category = "micro_benchmarks"
    result.metadata = {
        'key_size': key_size,
        'num_values': len(test_values),
        'optimization_level': 'full_stack',
        'cache_hit_rate': stats.get('cache_hit_rate', 'unknown'),
        'gpu_available': opt.gpu_available
    }
    
    logger.info(f"[OK] Full Stack: {result.mean:.2f} ops/sec")
    return result


def benchmark_homomorphic_operations(key_size: int = 2048, repetitions: int = 10) -> Dict[str, BenchmarkResult]:
    """
    Benchmark homomorphic addition and multiplication operations.
    
    Args:
        key_size: RSA modulus size in bits
        repetitions: Number of test runs
        
    Returns:
        Dictionary of BenchmarkResults for different operations
    """
    logger.info(f"Benchmarking homomorphic operations ({key_size}-bit)")
    
    pub, priv = generate_keypair(bit_length=key_size)
    
    # Encrypt test values
    enc1 = encrypt(pub, 100)
    enc2 = encrypt(pub, 200)
    
    results = {}
    
    # Homomorphic addition
    def homo_add():
        return [(enc1 + enc2) for _ in range(1000)]
    
    result_add = run_benchmark(
        homo_add,
        repetitions=repetitions,
        warmup=2,
        unit='ops/sec'
    )
    result_add.name = f"homomorphic_add_{key_size}bit"
    result_add.category = "micro_benchmarks"
    result_add.metadata = {'key_size': key_size, 'operation': 'addition'}
    
    results['homomorphic_add'] = result_add
    logger.info(f"[OK] Homomorphic Add: {result_add.mean:.2f} ops/sec")
    
    # Scalar multiplication
    def homo_mult():
        return [(enc1 * 5) for _ in range(1000)]
    
    result_mult = run_benchmark(
        homo_mult,
        repetitions=repetitions,
        warmup=2,
        unit='ops/sec'
    )
    result_mult.name = f"homomorphic_mult_{key_size}bit"
    result_mult.category = "micro_benchmarks"
    result_mult.metadata = {'key_size': key_size, 'operation': 'scalar_multiplication'}
    
    results['homomorphic_mult'] = result_mult
    logger.info(f"[OK] Homomorphic Mult: {result_mult.mean:.2f} ops/sec")
    
    return results


def benchmark_decryption(key_size: int = 2048, repetitions: int = 10) -> BenchmarkResult:
    """
    Benchmark decryption performance (with CRT optimization).
    
    Args:
        key_size: RSA modulus size in bits
        repetitions: Number of test runs
        
    Returns:
        BenchmarkResult with decryption performance
    """
    logger.info(f"Benchmarking decryption ({key_size}-bit)")
    
    pub, priv = generate_keypair(bit_length=key_size)
    
    # Pre-encrypt test values
    encrypted_values = [encrypt(pub, i) for i in range(100)]
    
    def decrypt_batch():
        from agniya.core.paillier import decrypt_crt
        return [decrypt_crt(pub, priv, ct) for ct in encrypted_values]
    
    result = run_benchmark(
        decrypt_batch,
        repetitions=repetitions,
        warmup=2,
        unit='ops/sec'
    )
    
    result.name = f"decryption_crt_{key_size}bit"
    result.category = "micro_benchmarks"
    result.metadata = {
        'key_size': key_size,
        'num_values': len(encrypted_values),
        'uses_crt': True
    }
    
    logger.info(f"[OK] Decryption (CRT): {result.mean:.2f} ops/sec")
    return result


def benchmark_memory_usage(key_size: int = 2048) -> Dict[str, float]:
    """
    Measure memory footprint of encryption operations.
    
    Args:
        key_size: RSA modulus size in bits
        
    Returns:
        Dictionary of memory statistics
    """
    logger.info(f"Measuring memory usage ({key_size}-bit)")
    
    pub, priv = generate_keypair(bit_length=key_size)
    
    def encrypt_large_batch():
        return [encrypt(pub, i) for i in range(1000)]
    
    _, memory_stats = measure_memory_usage(encrypt_large_batch)
    
    memory_stats['key_size'] = key_size
    memory_stats['batch_size'] = 1000
    
    logger.info(f"[OK] Memory: {memory_stats['delta_mb']:.2f} MB for 1000 encryptions")
    return memory_stats


def run(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for micro-benchmarks.
    
    Args:
        config: Configuration dictionary from YAML
        
    Returns:
        Dictionary containing all benchmark results
    """
    logger.info("Starting Micro-Benchmarks")
    
    results = {
        'timestamp': time.time(),
        'config': config['micro_benchmarks'],
        'benchmarks': {}
    }
    
    key_sizes = config['micro_benchmarks']['key_sizes']
    repetitions = config['statistics']['repetitions']
    
    tracker = ProgressTracker(
        total_steps=len(key_sizes) * 7,  # 7 tests per key size
        description="Micro-benchmarks"
    )
    
    for key_size in key_sizes:
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing {key_size}-bit keys")
        logger.info(f"{'='*60}")
        
        key_results = {}
        
        # 1. Baseline
        tracker.update(description=f"Baseline {key_size}-bit")
        key_results['baseline'] = benchmark_baseline_encryption(key_size, repetitions).to_dict()
        
        # 2. GPU only
        tracker.update(description=f"GPU {key_size}-bit")
        key_results['gpu_only'] = benchmark_gpu_only(key_size, repetitions).to_dict()
        
        # 3. L1 cache
        tracker.update(description=f"L1 Cache {key_size}-bit")
        key_results['cache_l1'] = benchmark_cache_l1_only(key_size, repetitions).to_dict()
        
        # 4. Full stack
        tracker.update(description=f"Full Stack {key_size}-bit")
        key_results['full_stack'] = benchmark_all_optimizations(key_size, repetitions).to_dict()
        
        # 5. Homomorphic operations
        tracker.update(description=f"Homomorphic Ops {key_size}-bit")
        homo_results = benchmark_homomorphic_operations(key_size, repetitions)
        key_results['homomorphic'] = {k: v.to_dict() for k, v in homo_results.items()}
        
        # 6. Decryption
        tracker.update(description=f"Decryption {key_size}-bit")
        key_results['decryption'] = benchmark_decryption(key_size, repetitions).to_dict()
        
        # 7. Memory usage
        tracker.update(description=f"Memory {key_size}-bit")
        key_results['memory'] = benchmark_memory_usage(key_size)
        
        # Calculate speedups
        baseline_perf = key_results['baseline']['mean']
        key_results['speedups'] = {
            'gpu_vs_baseline': calculate_speedup(baseline_perf, key_results['gpu_only']['mean']),
            'cache_vs_baseline': calculate_speedup(baseline_perf, key_results['cache_l1']['mean']),
            'full_vs_baseline': calculate_speedup(baseline_perf, key_results['full_stack']['mean']),
        }
        
        results['benchmarks'][f'{key_size}bit'] = key_results
        
        logger.info(f"\nSpeedups for {key_size}-bit:")
        logger.info(f"  GPU only: {key_results['speedups']['gpu_vs_baseline']:.2f}x")
        logger.info(f"  L1 Cache: {key_results['speedups']['cache_vs_baseline']:.2f}x")
        logger.info(f"  Full Stack: {key_results['speedups']['full_vs_baseline']:.2f}x")
    
    tracker.complete()
    
    # Summary
    results['summary'] = {
        'max_speedup': max(
            kv['speedups']['full_vs_baseline'] 
            for kv in results['benchmarks'].values()
        ),
        'key_sizes_tested': key_sizes,
        'repetitions_per_test': repetitions
    }
    
    logger.info(f"\n[COMPLETE] Micro-benchmarks complete")
    logger.info(f"  Maximum speedup achieved: {results['summary']['max_speedup']:.2f}x")
    
    return results
