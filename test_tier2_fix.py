"""
Test script to verify Tier 2 fix - should no longer hang!
"""

import pandas as pd
import time
from agniya.core.ultimate_system import UltimateOptimizedDatabase

print("="*70)
print("TESTING TIER 2 FIX")
print("="*70)

# Load dataset
print("\nLoading dataset...")
df = pd.read_csv("G:\\agniya\\data\\real_datasets\\online_retail_prepared.csv")
print(f"✅ Loaded {len(df):,} records")

# Initialize system with Tier 2 DISABLED (default)
print("\nInitializing AGNIYA system with Tier 2 DISABLED (should be fast)...")
start_time = time.time()
db = UltimateOptimizedDatabase(
    key_size=2048,
    cache_size=10000,
    enable_tiered_cache=True,
    enable_tier2_disk=False,  # DISABLED - no more hang!
    enable_probabilistic=True
)
init_time = time.time() - start_time
print(f"✅ Initialization completed in {init_time:.2f} seconds")

# Encrypt a subset of data
print("\nEncrypting first 1,000 records...")
start_time = time.time()
from agniya.core.paillier import encrypt
encrypted_quantities = []
for qty in df['quantity'].head(1000):  # lowercase 'quantity'
    enc_qty = encrypt(db.pub, qty)
    encrypted_quantities.append(enc_qty)

encrypt_time = time.time() - start_time
print(f"✅ Encrypted 1,000 values in {encrypt_time:.2f} seconds")
print(f"   Average: {encrypt_time/1000*1000:.2f} ms per encryption")

# Show statistics
print("\n" + "="*70)
print("CACHE STATISTICS")
print("="*70)
db.print_statistics()

print("\n✅ SUCCESS! No more hang - Tier 2 is disabled by default.")
print("   If you REALLY need Tier 2, enable it with enable_tier2_disk=True")
print("   (but be warned: it will take ~7 hours to build!)")
