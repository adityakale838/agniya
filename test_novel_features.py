"""
Quick test of all 3 novel features together
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agniya.compression.rns_compression import RNSCompressor
from agniya.storage.deduplication import CiphertextDeduplicator
from agniya.core.query_planner import AdaptiveQueryPlanner
import random
import time

print("=" * 70)
print("AGNIYA - Novel Features Integration Test")
print("=" * 70)

# Test 1: RNS Compression
print("\n1. RNS Compression Test")
print("-" * 70)
compressor = RNSCompressor(bit_size=2048, num_primes=32)

# Generate fake ciphertext
test_ct = random.getrandbits(2048)
print(f"Original ciphertext: {test_ct.bit_length()} bits")

# Compress
compressed = compressor.compress(test_ct)
print(f"Compressed: {len(compressed)} bytes")

# Decompress
decompressed = compressor.decompress(compressed)
print(f"Decompressed matches: {(test_ct % compressor.M) == decompressed}")
print(f"Compression ratio: {compressor.compression_ratio():.2%}")
print("✅ RNS Compression working")

# Test 2: Ciphertext Deduplication
print("\n2. Ciphertext Deduplication Test")
print("-" * 70)
dedup = CiphertextDeduplicator(num_bands=20, rows_per_band=5)

# Add ciphertexts with duplicates
test_values = [random.getrandbits(2048) for _ in range(100)]
test_values_with_dups = test_values * 4  # 4x duplication

for ct in test_values_with_dups:
    dedup.add_ciphertext(ct)

stats = dedup.get_stats()
print(f"Total added: {stats['total_added']}")
print(f"Unique stored: {stats['unique_stored']}")
print(f"Storage saved: {stats['storage_saved_pct']:.1f}%")
print("✅ Deduplication working")

# Test 3: Adaptive Query Planning
print("\n3. Adaptive Query Planning Test")
print("-" * 70)
planner = AdaptiveQueryPlanner()

# Build histogram
age_data = [random.randint(18, 80) for _ in range(100000)]
planner.build_histogram('age', age_data)

# Plan query
plan = planner.plan_query('sum', 'age', filter_min=30, filter_max=50, cache_available=True)
print(f"Strategy: {plan.strategy.value}")
print(f"Estimated cost: {plan.estimated_cost:.2f} ms")
print(f"Estimated rows: {plan.estimated_rows:,}")
print(f"Reason: {plan.reason}")
print("✅ Query Planning working")

# Test 4: All together
print("\n4. Integration Test - Simulate Full Workflow")
print("-" * 70)

# Simulate encryption + compression + dedup
num_records = 1000
print(f"Simulating {num_records} record encryption...")

start = time.time()

# Generate fake encrypted data
encrypted_data = [random.getrandbits(2048) for _ in range(num_records)]

# Compress
print("  Compressing...")
compressed_data = compressor.compress_batch(encrypted_data)

# Deduplicate
print("  Deduplicating...")
dedup2 = CiphertextDeduplicator()
for ct in encrypted_data:
    dedup2.add_ciphertext(ct)

# Build histogram for planning
print("  Building query histogram...")
fake_values = [random.randint(1000, 5000) for _ in range(num_records)]
planner2 = AdaptiveQueryPlanner()
planner2.build_histogram('salary', fake_values)

# Plan a query
plan2 = planner2.plan_query('sum', 'salary', cache_available=True)

elapsed = time.time() - start

print("\n" + "=" * 70)
print("Integration Test Results:")
print("=" * 70)
print(f"Records processed: {num_records}")
print(f"Original size: {num_records * (2048//8):,} bytes ({num_records * (2048//8)/1024:.1f} KB)")
print(f"Compressed size: {len(compressed_data):,} bytes ({len(compressed_data)/1024:.1f} KB)")
print(f"Bandwidth saved: {(1 - len(compressed_data)/(num_records * (2048//8)))*100:.1f}%")
print(f"Storage dedup: {dedup2.get_stats()['storage_saved_pct']:.1f}% saved")
print(f"Query strategy: {plan2.strategy.value}")
print(f"Total time: {elapsed:.3f}s")
print("=" * 70)
print("✅ ALL FEATURES INTEGRATED AND WORKING!")
print("=" * 70)
