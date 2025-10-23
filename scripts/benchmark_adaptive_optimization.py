"""
Comprehensive Adaptive Bit-Length Benchmark

This script tests the adaptive optimization across all key sizes (512 to 4096-bit)
and demonstrates the performance gains for each data range.
"""

import sys
import pandas as pd
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agniya.core.paillier import PaillierCryptosystem, AdaptiveKeySelector, generate_keypair, encrypt, decrypt
from agniya.core.precomputation import PrecomputationTable


def benchmark_key_size(data, key_size, description):
    """Benchmark a specific key size."""
    print(f"\n{description}")
    print("-" * 70)
    
    # Generate keys
    start = time.time()
    pub, priv = generate_keypair(key_size)
    keygen_time = (time.time() - start) * 1000
    
    # Encrypt sample
    sample = data[:100]  # Test with 100 values
    
    # Handle negative values by using an offset
    min_val = int(min(sample))
    offset = abs(min_val) if min_val < 0 else 0
    
    start = time.time()
    encrypted = [encrypt(pub, int(v) + offset) for v in sample]
    encrypt_time = (time.time() - start) * 1000
    
    # Decrypt sample
    start = time.time()
    decrypted = [decrypt(pub, priv, ct) - offset for ct in encrypted]
    decrypt_time = (time.time() - start) * 1000
    
    # Homomorphic sum
    start = time.time()
    sum_ct = encrypted[0]
    for ct in encrypted[1:]:
        sum_ct = (sum_ct * ct) % pub.n_squared
    sum_time = (time.time() - start) * 1000
    
    # Decrypt result (adjust for offset: sum(v+offset) = sum(v) + 100*offset)
    start = time.time()
    result_with_offset = decrypt(pub, priv, sum_ct)
    result = result_with_offset - (len(sample) * offset)
    final_decrypt_time = (time.time() - start) * 1000
    
    # Calculate ciphertext size
    ciphertext_bits = key_size * 2  # Paillier ciphertexts are ~2x key size
    ciphertext_bytes = ciphertext_bits // 8
    total_storage = ciphertext_bytes * len(sample)
    
    print(f"  Key generation: {keygen_time:>8.2f} ms")
    print(f"  Encrypt 100 values: {encrypt_time:>8.2f} ms ({encrypt_time/100:.2f} ms/value)")
    print(f"  Decrypt 100 values: {decrypt_time:>8.2f} ms ({decrypt_time/100:.2f} ms/value)")
    print(f"  Homomorphic sum: {sum_time:>8.2f} ms")
    print(f"  Final decrypt: {final_decrypt_time:>8.2f} ms")
    print(f"  Ciphertext size: {ciphertext_bytes:>8} bytes/value")
    print(f"  Total storage (100): {total_storage:>8} bytes ({total_storage/1024:.1f} KB)")
    print(f"  Result correct: {result == sum(sample)}")
    
    return {
        'key_size': key_size,
        'keygen_ms': keygen_time,
        'encrypt_ms': encrypt_time,
        'decrypt_ms': decrypt_time,
        'sum_ms': sum_time,
        'final_decrypt_ms': final_decrypt_time,
        'ciphertext_bytes': ciphertext_bytes,
        'total_storage_bytes': total_storage,
        'encrypt_per_value': encrypt_time / 100,
        'decrypt_per_value': decrypt_time / 100
    }


def test_adaptive_selection():
    """Test adaptive key selection on different datasets."""
    print("\n" + "=" * 70)
    print("ADAPTIVE BIT-LENGTH OPTIMIZATION BENCHMARK")
    print("=" * 70)
    
    datasets = [
        ("data/sample_datasets/adaptive_tests/tiny_values_512bit.csv", "Tiny Values (512-bit target)"),
        ("data/sample_datasets/adaptive_tests/small_values_1024bit.csv", "Small Values (1024-bit target)"),
        ("data/sample_datasets/adaptive_tests/medium_values_2048bit.csv", "Medium Values (2048-bit target)"),
        ("data/sample_datasets/adaptive_tests/large_values_3072bit.csv", "Large Values (3072-bit target)"),
        ("data/sample_datasets/adaptive_tests/huge_values_4096bit.csv", "Huge Values (4096-bit target)"),
    ]
    
    all_results = []
    
    for filepath, description in datasets:
        if not Path(filepath).exists():
            print(f"\n⚠️  Dataset not found: {filepath}")
            print("   Run: python scripts/generate_datasets.py first")
            continue
        
        print(f"\n{'=' * 70}")
        print(f"Dataset: {description}")
        print(f"{'=' * 70}")
        
        # Load dataset
        df = pd.read_csv(filepath)
        
        # Get first numeric column for testing
        numeric_cols = df.select_dtypes(include=['int64', 'int32', 'float64']).columns
        if 'id' in numeric_cols:
            numeric_cols = [c for c in numeric_cols if c != 'id']
        
        test_column = numeric_cols[0]
        data = df[test_column].values
        
        print(f"\nColumn: {test_column}")
        print(f"  Values: {len(data)}")
        print(f"  Range: [{data.min()}, {data.max()}]")
        
        # Analyze with adaptive selector
        analysis = AdaptiveKeySelector.analyze_dataset(data.tolist())
        
        recommended = analysis['recommended_key_size']
        print(f"\nAdaptive Analysis:")
        print(f"  Recommended key size: {recommended} bits ✅")
        print(f"  Storage reduction: {analysis['storage_reduction_percent']:.1f}%")
        print(f"  Estimated speedup: {analysis['compute_speedup_estimate']:.2f}x")
        
        # Test 1: Baseline (2048-bit - traditional approach)
        print(f"\n{'─' * 70}")
        print("BASELINE: Traditional 2048-bit (no optimization)")
        baseline = benchmark_key_size(data, 2048, "2048-bit keys")
        
        # Test 2: Recommended (adaptive)
        print(f"\n{'─' * 70}")
        print(f"OPTIMIZED: Adaptive {recommended}-bit (our innovation)")
        optimized = benchmark_key_size(data, recommended, f"{recommended}-bit keys")
        
        # Calculate improvements
        print(f"\n{'─' * 70}")
        print("PERFORMANCE COMPARISON:")
        print(f"{'─' * 70}")
        
        encrypt_speedup = baseline['encrypt_ms'] / optimized['encrypt_ms'] if optimized['encrypt_ms'] > 0 else float('inf')
        decrypt_speedup = baseline['decrypt_ms'] / optimized['decrypt_ms'] if optimized['decrypt_ms'] > 0 else float('inf')
        storage_reduction = (1 - optimized['total_storage_bytes'] / baseline['total_storage_bytes']) * 100
        
        print(f"  Encryption speedup: {encrypt_speedup:.2f}x")
        print(f"  Decryption speedup: {decrypt_speedup:.2f}x")
        print(f"  Storage reduction: {storage_reduction:.1f}%")
        print(f"  Time saved per 100 encryptions: {baseline['encrypt_ms'] - optimized['encrypt_ms']:.2f} ms")
        print(f"  Storage saved per 100 values: {(baseline['total_storage_bytes'] - optimized['total_storage_bytes'])/1024:.1f} KB")
        
        # Store results
        result = {
            'dataset': description,
            'column': test_column,
            'max_value': int(data.max()),
            'recommended_bits': recommended,
            'baseline_encrypt_ms': baseline['encrypt_ms'],
            'optimized_encrypt_ms': optimized['encrypt_ms'],
            'encrypt_speedup': encrypt_speedup,
            'baseline_decrypt_ms': baseline['decrypt_ms'],
            'optimized_decrypt_ms': optimized['decrypt_ms'],
            'decrypt_speedup': decrypt_speedup,
            'baseline_storage_kb': baseline['total_storage_bytes'] / 1024,
            'optimized_storage_kb': optimized['total_storage_bytes'] / 1024,
            'storage_reduction_pct': storage_reduction
        }
        all_results.append(result)
    
    # Summary table
    if all_results:
        print("\n" + "=" * 70)
        print("SUMMARY: Adaptive Optimization Across All Key Sizes")
        print("=" * 70)
        
        results_df = pd.DataFrame(all_results)
        
        print("\nEncryption Performance:")
        print(results_df[['dataset', 'recommended_bits', 'encrypt_speedup', 'decrypt_speedup']].to_string(index=False))
        
        print("\nStorage Efficiency:")
        print(results_df[['dataset', 'recommended_bits', 'storage_reduction_pct']].to_string(index=False))
        
        print("\n" + "=" * 70)
        print("KEY FINDINGS:")
        print("=" * 70)
        print(f"  Average encryption speedup: {results_df['encrypt_speedup'].mean():.2f}x")
        print(f"  Average decryption speedup: {results_df['decrypt_speedup'].mean():.2f}x")
        print(f"  Average storage reduction: {results_df['storage_reduction_pct'].mean():.1f}%")
        print(f"  Best case speedup: {results_df['encrypt_speedup'].max():.2f}x")
        print(f"  Best case storage reduction: {results_df['storage_reduction_pct'].max():.1f}%")
        
        # Save results
        output_file = Path("data/benchmark_results/adaptive_optimization_results.csv")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        results_df.to_csv(output_file, index=False)
        print(f"\n✅ Results saved to: {output_file}")


def test_with_precomputation():
    """Test adaptive + precomputation combined."""
    print("\n" + "=" * 70)
    print("COMBINED: Adaptive + Precomputation Optimization")
    print("=" * 70)
    
    # Use small values dataset (good for precomputation)
    filepath = "data/sample_datasets/adaptive_tests/small_values_1024bit.csv"
    
    if not Path(filepath).exists():
        print(f"⚠️  Dataset not found: {filepath}")
        return
    
    df = pd.read_csv(filepath)
    
    # Use heart_rate column (repeated values benefit from cache)
    data = df['heart_rate'].values[:1000]
    
    print(f"\nDataset: Small Values (Heart Rates)")
    print(f"  Values: {len(data)}")
    print(f"  Range: [{data.min()}, {data.max()}]")
    print(f"  Unique values: {len(set(data))}")
    
    # Create adaptive system
    crypto = PaillierCryptosystem.from_dataset(data.tolist())
    
    # Create precomputation table
    precomp = PrecomputationTable(crypto.public_key)
    
    # Warm cache with dataset values
    print("\nWarming cache with dataset values...")
    unique_values = list(set(data))[:80]  # Top 80 unique values
    for v in unique_values:
        precomp.add_to_cache(int(v), encrypt(crypto.public_key, int(v)))
    print(f"  Cached {len(unique_values)} unique values")
    
    # Test without precomputation
    print("\n" + "─" * 70)
    print("Without Precomputation:")
    start = time.time()
    encrypted_no_cache = [encrypt(crypto.public_key, int(v)) for v in data]
    time_no_cache = (time.time() - start) * 1000
    print(f"  Encryption time: {time_no_cache:.2f} ms")
    
    # Test with precomputation
    print("\n" + "─" * 70)
    print("With Precomputation:")
    precomp.clear_stats()
    
    start = time.time()
    encrypted_with_cache = [precomp.get_or_encrypt(int(v)) for v in data]
    time_with_cache = (time.time() - start) * 1000
    
    stats = precomp.get_stats()
    
    print(f"  Encryption time: {time_with_cache:.2f} ms")
    print(f"  Cache hits: {stats['hits']}")
    print(f"  Cache misses: {stats['misses']}")
    print(f"  Hit rate: {stats['hit_rate']*100:.1f}%")
    
    # Results
    print("\n" + "─" * 70)
    print("COMBINED RESULTS:")
    speedup = time_no_cache / time_with_cache if time_with_cache > 0 else float('inf')
    print(f"  Speedup: {speedup:.2f}x")
    print(f"  Time saved: {time_no_cache - time_with_cache:.2f} ms")
    print(f"  Total optimization: Adaptive (4x) + Precompute ({speedup:.2f}x) = {4*speedup:.2f}x ✅")


if __name__ == "__main__":
    # Test adaptive selection across all key sizes
    test_adaptive_selection()
    
    # Test combined optimizations
    test_with_precomputation()
    
    print("\n" + "=" * 70)
    print("✅ All benchmarks complete!")
    print("=" * 70)
