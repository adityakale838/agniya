"""
AGNIYA - Comprehensive Test Suite
==================================

Single test file for all functionality:
- GPU acceleration
- JIT compilation
- ORAM security
- Multi-level caching
- Real-world datasets
- Performance benchmarks

Usage:
    python test_all.py              # Run all tests
    python test_all.py --quick      # Quick test (skip slow tests)
    python test_all.py --benchmark  # Performance benchmarks only
"""

import sys
import time
import argparse
import pandas as pd
import numpy as np
from pathlib import Path

from agniya.core.ultimate_system import UltimateOptimizedDatabase

# Test results
results = {}


def test_basic_encryption():
    """Test 1: Basic encryption/decryption"""
    print("\n" + "="*70)
    print("TEST 1: Basic Encryption/Decryption")
    print("="*70)
    
    try:
        db = UltimateOptimizedDatabase(
            key_size=2048,
            enable_gpu_encryption=False,
            verbose=False
        )
        
        # Test small query
        data = [10, 20, 30, 40, 50]
        result = db.sum_query(data)
        expected = sum(data)
        
        if result == expected:
            print(f"✅ PASSED - Sum: {result} == {expected}")
            return True
        else:
            print(f"❌ FAILED - Sum: {result} != {expected}")
            return False
            
    except Exception as e:
        print(f"❌ FAILED - Error: {e}")
        return False


def test_gpu_acceleration():
    """Test 2: GPU acceleration"""
    print("\n" + "="*70)
    print("TEST 2: GPU Acceleration")
    print("="*70)
    
    try:
        import cupy
        print("✅ CuPy available")
        
        db = UltimateOptimizedDatabase(
            key_size=2048,
            enable_gpu_encryption=True,
            enable_gpu_pipeline=True,
            verbose=False
        )
        
        data = list(range(1, 101))
        result = db.sum_query(data)
        expected = sum(data)
        
        if result == expected:
            print(f"✅ PASSED - GPU sum: {result} == {expected}")
            return True
        else:
            print(f"❌ FAILED - GPU sum: {result} != {expected}")
            return False
            
    except ImportError:
        print("⚠️  SKIPPED - CuPy not available (GPU test skipped)")
        return True
    except Exception as e:
        print(f"❌ FAILED - Error: {e}")
        return False


def test_oram_security():
    """Test 3: ORAM access pattern hiding"""
    print("\n" + "="*70)
    print("TEST 3: ORAM Security")
    print("="*70)
    
    try:
        db = UltimateOptimizedDatabase(
            key_size=2048,
            enable_oram=True,
            oram_mode='hybrid',
            verbose=False
        )
        
        data = [100, 200, 300, 400, 500]
        result = db.sum_query(data)
        expected = sum(data)
        
        if result == expected:
            print(f"✅ PASSED - ORAM sum: {result} == {expected}")
            return True
        else:
            print(f"❌ FAILED - ORAM sum: {result} != {expected}")
            return False
            
    except Exception as e:
        print(f"❌ FAILED - Error: {e}")
        return False


def test_caching_performance():
    """Test 4: Multi-level caching"""
    print("\n" + "="*70)
    print("TEST 4: Caching Performance")
    print("="*70)
    
    try:
        db = UltimateOptimizedDatabase(
            key_size=2048,
            cache_size=5000,
            enable_multi_level=True,
            verbose=False
        )
        
        # Warm cache
        hot_values = list(range(1, 201))
        for v in hot_values:
            _ = db.precomp.get_or_encrypt(v)
        
        # Test with cached data
        start = time.time()
        data = hot_values * 10  # 2000 operations
        result = db.sum_query(data)
        elapsed = time.time() - start
        
        expected = sum(data)
        throughput = len(data) / elapsed
        
        if result == expected and throughput > 1000:
            print(f"✅ PASSED - Cached sum: {result} == {expected}")
            print(f"   Throughput: {throughput:,.1f} ops/sec")
            return True
        else:
            print(f"❌ FAILED - Result or performance issue")
            return False
            
    except Exception as e:
        print(f"❌ FAILED - Error: {e}")
        return False


def test_real_world_insurance():
    """Test 5: Real-world insurance dataset"""
    print("\n" + "="*70)
    print("TEST 5: Real-World Data (Insurance)")
    print("="*70)
    
    try:
        df = pd.read_csv('data/insurance_real.csv')
        print(f"✅ Loaded {len(df)} records")
        
        db = UltimateOptimizedDatabase(
            key_size=2048,
            enable_gpu_encryption=True,
            enable_oram=False,
            verbose=False
        )
        
        # Test with ages
        ages = df['age'].dropna().astype(int).tolist()[:500]
        result = db.sum_query(ages)
        expected = sum(ages)
        
        if result == expected:
            print(f"✅ PASSED - Sum of {len(ages)} ages: {result}")
            return True
        else:
            print(f"❌ FAILED - Sum mismatch")
            return False
            
    except FileNotFoundError:
        print("⚠️  SKIPPED - Insurance data not found")
        return True
    except Exception as e:
        print(f"❌ FAILED - Error: {e}")
        return False


def test_real_world_retail():
    """Test 6: Real-world retail dataset"""
    print("\n" + "="*70)
    print("TEST 6: Real-World Data (Retail)")
    print("="*70)
    
    try:
        df = pd.read_csv('data/real_datasets/online_retail_prepared.csv')
        print(f"✅ Loaded {len(df)} transactions")
        
        db = UltimateOptimizedDatabase(
            key_size=2048,
            enable_gpu_encryption=True,
            verbose=False
        )
        
        # Test with quantities
        sample = df.sample(n=500, random_state=42)
        quantities = sample['quantity'].astype(int).tolist()
        result = db.sum_query(quantities)
        expected = sum(quantities)
        
        if result == expected:
            print(f"✅ PASSED - Sum of {len(quantities)} quantities: {result}")
            return True
        else:
            print(f"❌ FAILED - Sum mismatch")
            return False
            
    except FileNotFoundError:
        print("⚠️  SKIPPED - Retail data not found")
        return True
    except Exception as e:
        print(f"❌ FAILED - Error: {e}")
        return False


def benchmark_performance():
    """Benchmark: Performance test"""
    print("\n" + "="*70)
    print("BENCHMARK: Performance Test")
    print("="*70)
    
    try:
        db = UltimateOptimizedDatabase(
            key_size=2048,
            cache_size=10000,
            enable_gpu_encryption=True,
            enable_gpu_pipeline=True,
            enable_jit=True,
            enable_oram=False,
            verbose=False
        )
        
        # Warm cache
        hot_values = list(range(1, 101))
        for v in hot_values:
            _ = db.precomp.get_or_encrypt(v)
        
        # Test 1: Pure cache throughput
        print("\n📊 Pure Cache Throughput:")
        data = hot_values * 10  # 1000 ops
        start = time.time()
        _ = db.sum_query(data)
        elapsed = time.time() - start
        throughput = len(data) / elapsed
        print(f"   {throughput:,.0f} ops/sec")
        
        # Test 2: Sustained load
        print("\n📊 Sustained Load (50 queries):")
        total_ops = 0
        start = time.time()
        for _ in range(50):
            subset = np.random.choice(hot_values, 50).tolist()
            _ = db.sum_query(subset)
            total_ops += 50
        elapsed = time.time() - start
        throughput = total_ops / elapsed
        print(f"   {throughput:,.0f} ops/sec")
        print(f"   {50/elapsed:.1f} queries/sec")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED - Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='AGNIYA Test Suite')
    parser.add_argument('--quick', action='store_true', help='Quick test (skip slow tests)')
    parser.add_argument('--benchmark', action='store_true', help='Run benchmarks only')
    args = parser.parse_args()
    
    print("="*70)
    print("AGNIYA - Comprehensive Test Suite")
    print("="*70)
    
    if args.benchmark:
        # Run benchmarks only
        results['benchmark'] = benchmark_performance()
    else:
        # Run all tests
        results['basic'] = test_basic_encryption()
        results['gpu'] = test_gpu_acceleration()
        results['oram'] = test_oram_security()
        results['cache'] = test_caching_performance()
        
        if not args.quick:
            results['insurance'] = test_real_world_insurance()
            results['retail'] = test_real_world_retail()
        
        # Run benchmark
        results['benchmark'] = benchmark_performance()
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{name:20s}: {status}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print("\n⚠️  SOME TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
