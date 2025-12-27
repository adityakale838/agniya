"""
Quick AGNIYA Performance Benchmark
Runs AGNIYA benchmarks standalone (without SEAL/OpenFHE comparison)
"""

import time
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from agniya.hybrid.database import HybridEncryptedDatabase


def benchmark_agniya():
    """Quick benchmark of AGNIYA system."""
    
    print("=" * 80)
    print("AGNIYA Performance Benchmark")
    print("=" * 80)
    print()
    
    db = HybridEncryptedDatabase(
        key_size=2048,
        enable_cache=True,
        enable_batch=True,
        enable_precomputation=True
    )
    
    results = []
    data_sizes = [100, 500, 1000, 5000, 10000]
    
    for size in data_sizes:
        print(f"\n📊 Testing with {size:,} records...")
        data = np.random.randint(1, 1000, size=size).tolist()
        
        # Test encryption
        start = time.time()
        ciphertexts = db.encrypt(data[:100])
        enc_time = (time.time() - start) * 1000
        enc_throughput = 100 / (enc_time / 1000)
        print(f"  Encryption: {enc_time:.2f}ms ({enc_throughput:.0f} ops/sec)")
        
        # Test SUM
        start = time.time()
        result = db.sum(data)
        sum_time = (time.time() - start) * 1000
        sum_throughput = size / (sum_time / 1000)
        print(f"  SUM Query:  {sum_time:.2f}ms ({sum_throughput:.0f} records/sec)")
        
        # Test AVG
        start = time.time()
        result = db.sum(data) / len(data)
        avg_time = (time.time() - start) * 1000
        avg_throughput = size / (avg_time / 1000)
        print(f"  AVG Query:  {avg_time:.2f}ms ({avg_throughput:.0f} records/sec)")
        
        results.append({
            'size': size,
            'encryption_ms': enc_time,
            'sum_ms': sum_time,
            'avg_ms': avg_time,
            'encryption_throughput': enc_throughput,
            'sum_throughput': sum_throughput,
            'avg_throughput': avg_throughput
        })
    
    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)
    
    df = pd.DataFrame(results)
    print(df.to_string(index=False))
    
    # Save results
    output_dir = Path("data/benchmark_results")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file = output_dir / f"agniya_standalone_{timestamp}.csv"
    df.to_csv(csv_file, index=False)
    
    print(f"\n✅ Results saved to {csv_file}")
    print()


if __name__ == "__main__":
    benchmark_agniya()
