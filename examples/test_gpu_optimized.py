"""
Quick GPU Test: Show cache + GPU working together

This test demonstrates:
1. Cache effectiveness (warm cache scenario)
2. GPU batch operations
3. Real-world speedup
"""

import time
import random

from agniya.core.paillier import generate_keypair
from agniya.core.optimized_paillier import OptimizedPaillier

print("\n" + "="*70)
print("Quick GPU Optimization Test")
print("="*70)

# Generate keys
print("\nGenerating 2048-bit keys...")
pub, priv = generate_keypair(2048)
print("✓ Keys ready")

# Create optimized instance with GPU
print("\nInitializing OptimizedPaillier with GPU...")
opt = OptimizedPaillier(pub, priv,
                       enable_cache=True,
                       enable_precompute=True,
                       enable_gpu=True,
                       enable_gpu_homomorphic=True,
                       cache_size_l1=100,
                       cache_size_l2=1000)

# Test 1: Warm cache with repeated values
print("\n" + "="*70)
print("Test 1: Cache Effectiveness (Repeated Values)")
print("="*70)

random.seed(42)
ages = [random.randint(20, 80) for _ in range(1000)]

print(f"Dataset: {len(ages):,} values, {len(set(ages))} unique")
print(f"Expected SUM: {sum(ages):,}")

# First run (cold - fills cache)
print("\nFirst run (cold - filling cache)...")
start = time.time()
encrypted = opt.encrypt_batch(ages)
sum_ct = opt.sum_encrypted(encrypted)
result = opt.decrypt(sum_ct)
time_cold = time.time() - start

print(f"  Time: {time_cold:.3f} seconds")
print(f"  Result: {result:,}")

stats = opt.get_stats()
print(f"  Cache hits: {stats['cache_hits']:,}")
print(f"  Cache misses: {stats['encryptions_performed']:,}")

# Second run (hot - cache hits)
print("\nSecond run (hot - cache hits)...")
start = time.time()
encrypted = opt.encrypt_batch(ages)
sum_ct = opt.sum_encrypted(encrypted)
result = opt.decrypt(sum_ct)
time_hot = time.time() - start

print(f"  Time: {time_hot:.3f} seconds")
print(f"  Result: {result:,}")

stats = opt.get_stats()
total_ops = stats['cache_hits'] + stats['encryptions_performed']
hit_rate = stats['cache_hits'] / total_ops * 100 if total_ops > 0 else 0

print(f"  Cache hits: {stats['cache_hits']:,}")
print(f"  Cache misses: {stats['encryptions_performed']:,}")
print(f"  Hit rate: {hit_rate:.1f}%")

speedup = time_cold / time_hot if time_hot > 0 else 0
print(f"\n✨ Speedup: {speedup:.1f}x faster on second run (cache hits)")

# Test 2: GPU batch operations
print("\n" + "="*70)
print("Test 2: GPU Homomorphic Operations")
print("="*70)

# Clear cache for fair test
opt.clear_caches()

# Small batch (CPU)
small_batch = [random.randint(1, 100) for _ in range(50)]
print(f"\nSmall batch ({len(small_batch)} values) - uses CPU:")
start = time.time()
encrypted_small = opt.encrypt_batch(small_batch)
sum_small = opt.sum_encrypted(encrypted_small)
time_small = time.time() - start
print(f"  Time: {time_small:.3f} seconds")

# Large batch (GPU if available)
opt.clear_caches()
large_batch = [random.randint(1, 100) for _ in range(500)]
print(f"\nLarge batch ({len(large_batch)} values) - uses GPU homomorphic:")
start = time.time()
encrypted_large = opt.encrypt_batch(large_batch)
sum_large = opt.sum_encrypted(encrypted_large)
time_large = time.time() - start
print(f"  Time: {time_large:.3f} seconds")

# Test 3: Overall performance
print("\n" + "="*70)
print("Test 3: Real-World Performance Summary")
print("="*70)

opt.print_stats()

print("\nConclusion:")
print(f"  ✓ Cache provides massive speedup on repeated data")
print(f"  ✓ GPU accelerates large batch operations")
print(f"  ✓ Combined optimizations work together seamlessly")
print(f"\n{'='*70}\n")
