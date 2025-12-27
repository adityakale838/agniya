"""
Maximum Cache Performance Test

Shows the full potential of the cache optimization by using
a dataset with high repetition (like real-world data).
"""

import time
import random
from collections import Counter

from agniya.core.paillier import generate_keypair
from agniya.core.optimized_paillier import OptimizedPaillier

print("\n" + "="*70)
print("Maximum Cache Performance Test")
print("="*70)

# Generate keys
print("\nGenerating 2048-bit keys...")
pub, priv = generate_keypair(2048)
print("✓ Keys ready")

# Create realistic dataset with heavy repetition
# Simulating real-world data (e.g., age distribution)
random.seed(42)

# Age distribution: 20-40 (common), 41-60 (very common), 61-80 (less common)
ages = (
    [random.randint(20, 40) for _ in range(1000)] +
    [random.randint(41, 60) for _ in range(5000)] +  # Heavy concentration
    [random.randint(61, 80) for _ in range(1000)]
)
random.shuffle(ages)

unique_count = len(set(ages))
most_common = Counter(ages).most_common(5)

print(f"\nDataset Statistics:")
print(f"  Total values: {len(ages):,}")
print(f"  Unique values: {unique_count}")
print(f"  Repetition factor: {len(ages)/unique_count:.1f}x")
print(f"  Most common values: {[v for v, _ in most_common]}")
print(f"  Expected SUM: {sum(ages):,}")

# Initialize without cache (baseline)
print("\n" + "="*70)
print("Baseline: No Cache")
print("="*70)

opt_no_cache = OptimizedPaillier(pub, priv,
                                enable_cache=False,
                                enable_precompute=True)

start = time.time()
encrypted = opt_no_cache.encrypt_batch(ages)
sum_ct = opt_no_cache.sum_encrypted(encrypted)
result = opt_no_cache.decrypt(sum_ct)
time_no_cache = time.time() - start

print(f"  Time: {time_no_cache:.3f} seconds")
print(f"  Result: {result:,}")
print(f"  Throughput: {len(ages)/time_no_cache:.1f} ops/sec")

# Initialize with cache
print("\n" + "="*70)
print("Optimized: With Multi-Level Cache")
print("="*70)

opt = OptimizedPaillier(pub, priv,
                       enable_cache=True,
                       enable_precompute=True,
                       cache_size_l1=100,  # Fits top 100 most common ages
                       cache_size_l2=500)  # Fits all unique values

# First pass: Fill cache
print("\nPass 1: Filling cache (cold start)...")
start = time.time()
encrypted = opt.encrypt_batch(ages)
sum_ct = opt.sum_encrypted(encrypted)
result = opt.decrypt(sum_ct)
time_pass1 = time.time() - start

stats = opt.get_stats()
print(f"  Time: {time_pass1:.3f} seconds")
print(f"  Result: {result:,}")
print(f"  Cache hits: {stats['cache_hits']:,}")
print(f"  Cache misses: {stats['encryptions_performed']:,}")

# Second pass: Hot cache
print("\nPass 2: Hot cache (all cached)...")
start = time.time()
encrypted = opt.encrypt_batch(ages)
sum_ct = opt.sum_encrypted(encrypted)
result = opt.decrypt(sum_ct)
time_pass2 = time.time() - start

stats = opt.get_stats()
total_ops = stats['cache_hits'] + stats['encryptions_performed']
hit_rate = stats['cache_hits'] / total_ops * 100

print(f"  Time: {time_pass2:.3f} seconds")
print(f"  Result: {result:,}")
print(f"  Cache hits: {stats['cache_hits']:,}")
print(f"  Hit rate: {hit_rate:.1f}%")
print(f"  Throughput: {len(ages)/time_pass2:.1f} ops/sec")

# Third pass: Maximum performance
print("\nPass 3: Maximum performance...")
start = time.time()
for _ in range(10):  # Process same data 10 times
    encrypted = opt.encrypt_batch(ages)
    sum_ct = opt.sum_encrypted(encrypted)
    result = opt.decrypt(sum_ct)
time_pass3 = (time.time() - start) / 10

print(f"  Time per query: {time_pass3:.3f} seconds")
print(f"  Throughput: {len(ages)/time_pass3:.1f} ops/sec")

# Calculate speedups
speedup_pass1 = time_no_cache / time_pass1
speedup_pass2 = time_no_cache / time_pass2
speedup_pass3 = time_no_cache / time_pass3

print("\n" + "="*70)
print("Performance Summary")
print("="*70)

opt.print_stats()

print("\n" + "="*70)
print("Speedup Analysis")
print("="*70)
print(f"\nNo cache:     {time_no_cache:.3f}s  ({len(ages)/time_no_cache:.1f} ops/sec) [BASELINE]")
print(f"Pass 1 (cold): {time_pass1:.3f}s  ({len(ages)/time_pass1:.1f} ops/sec) {speedup_pass1:.1f}x")
print(f"Pass 2 (warm): {time_pass2:.3f}s  ({len(ages)/time_pass2:.1f} ops/sec) {speedup_pass2:.1f}x ⭐")
print(f"Pass 3 (hot):  {time_pass3:.3f}s  ({len(ages)/time_pass3:.1f} ops/sec) {speedup_pass3:.1f}x 🚀")

print(f"\n🎯 Maximum Speedup: {speedup_pass3:.1f}x faster with cache!")
print(f"💾 Cache hit rate: {hit_rate:.1f}%")
print(f"⚡ Peak throughput: {len(ages)/time_pass3:,.0f} operations/second")

print(f"\n{'='*70}\n")
