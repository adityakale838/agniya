"""
AGNIYA Usage Examples
Demonstrates how to use AGNIYA like numpy/pandas

Run: python examples_library_usage.py
"""

import agniya as ag
import time

def print_section(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60 + "\n")


def example_1_basic_usage():
    """Example 1: Basic encryption and decryption"""
    print_section("Example 1: Basic Encryption/Decryption")
    
    # Initialize database (like creating a numpy array or pandas dataframe)
    db = ag.Database(key_size=2048)
    
    # Encrypt a single value
    encrypted = db.encrypt(42)
    print(f"Original value: 42")
    print(f"Encrypted: {str(encrypted)[:50]}...")
    
    # Decrypt
    decrypted = db.decrypt(encrypted)
    print(f"Decrypted: {decrypted}")
    
    # Encrypt a list
    data = [10, 20, 30, 40, 50]
    encrypted_list = db.encrypt(data)
    print(f"\nOriginal list: {data}")
    print(f"Encrypted {len(encrypted_list)} values")
    
    # Decrypt list
    decrypted_list = db.decrypt(encrypted_list)
    print(f"Decrypted list: {decrypted_list}")


def example_2_aggregations():
    """Example 2: Aggregations on encrypted data"""
    print_section("Example 2: Aggregations (Sum, Average)")
    
    db = ag.Database(key_size=2048)
    
    # Sample data
    salaries = [50000, 60000, 70000, 80000, 90000]
    print(f"Employee salaries: {salaries}")
    
    # Compute sum on encrypted data
    total = db.sum(salaries)
    print(f"\nTotal payroll: ${total:,}")
    
    # Compute average
    avg_salary = db.average(salaries)
    print(f"Average salary: ${avg_salary:,.2f}")
    
    # Count
    count = db.count(salaries)
    print(f"Number of employees: {count}")


def example_3_caching():
    """Example 3: Intelligent caching for performance"""
    print_section("Example 3: Intelligent Caching")
    
    db = ag.Database(key_size=2048)
    
    # E-commerce scenario: Most sales are for popular prices
    common_prices = [9.99, 19.99, 29.99, 49.99, 99.99]
    
    # Warm cache with common values (like creating an index in database)
    print("Warming cache with common prices...")
    db.warm_cache(common_prices)
    print(f"Cached {len(common_prices)} values")
    
    # Simulate 1000 sales (80% are common prices)
    sales = (common_prices * 160) + list(range(100, 300))  # 800 + 200 = 1000
    
    print(f"\nProcessing {len(sales)} sales...")
    start = time.time()
    total_revenue = db.sum(sales)
    elapsed = time.time() - start
    
    print(f"Total revenue: ${total_revenue:,.2f}")
    print(f"Processing time: {elapsed:.3f}s")
    print(f"Throughput: {len(sales)/elapsed:.0f} transactions/sec")
    
    # Show cache stats
    stats = db.stats()
    print(f"\nCache statistics:")
    print(f"  Cache size: {stats['cache_size']}")
    print(f"  Key size: {stats['key_size']} bits")


def example_4_compression():
    """Example 4: RNS compression"""
    print_section("Example 4: RNS Compression")
    
    db = ag.Database(key_size=2048)
    
    # Encrypt a value
    value = 123456789
    encrypted = db.encrypt(value)
    
    # Compress
    compressed = db.compress(encrypted)
    
    # Compare sizes
    original_size = len(str(encrypted))
    compressed_size = len(compressed)
    compression_ratio = (1 - compressed_size / original_size) * 100
    
    print(f"Original value: {value}")
    print(f"Encrypted size: {original_size} bytes")
    print(f"Compressed size: {compressed_size} bytes")
    print(f"Compression ratio: {compression_ratio:.1f}%")
    
    # Decompress and verify
    decompressed = db.decompress(compressed)
    result = db.decrypt(decompressed)
    print(f"\nDecompressed and decrypted: {result}")
    print(f"Correct: {result == value}")


def example_5_privacy_preserving_analytics():
    """Example 5: Privacy-preserving analytics (real-world use case)"""
    print_section("Example 5: Privacy-Preserving Analytics")
    
    db = ag.Database(key_size=2048)
    
    # Scenario: Hospital wants to compute average patient age without revealing individual ages
    patient_ages = [25, 34, 45, 56, 67, 78, 23, 45, 56, 34]
    
    print("Hospital Data (sensitive!):")
    print(f"  Patient ages: {patient_ages}")
    
    # Encrypt ages (now secure!)
    print("\nEncrypting patient data...")
    encrypted_ages = db.encrypt(patient_ages)
    print(f"  ✅ {len(encrypted_ages)} ages encrypted")
    
    # Compute statistics on encrypted data
    print("\nComputing statistics on encrypted data...")
    
    # Average age
    avg_age = db.average(patient_ages)
    print(f"  Average age: {avg_age:.1f} years")
    
    # Total (for sum of ages)
    total = db.sum(patient_ages)
    print(f"  Sum of ages: {total}")
    
    # Count
    count = db.count(patient_ages)
    print(f"  Number of patients: {count}")
    
    print("\n✅ Statistics computed WITHOUT revealing individual ages!")


def example_6_numpy_pandas_style():
    """Example 6: NumPy/Pandas-style API"""
    print_section("Example 6: NumPy/Pandas-Style API")
    
    # AGNIYA works like numpy/pandas
    import numpy as np
    import pandas as pd
    
    # NumPy-style
    print("NumPy-style:")
    arr = np.array([1, 2, 3, 4, 5])
    print(f"  np.sum(arr) = {np.sum(arr)}")
    print(f"  np.mean(arr) = {np.mean(arr)}")
    
    # Pandas-style
    print("\nPandas-style:")
    df = pd.DataFrame({'values': [1, 2, 3, 4, 5]})
    print(f"  df['values'].sum() = {df['values'].sum()}")
    print(f"  df['values'].mean() = {df['values'].mean()}")
    
    # AGNIYA-style (encrypted!)
    print("\nAGNIYA-style (encrypted!):")
    db = ag.Database(key_size=2048)
    data = [1, 2, 3, 4, 5]
    print(f"  db.sum(data) = {db.sum(data)}")
    print(f"  db.average(data) = {db.average(data)}")
    
    print("\n✅ Same simple API, but with encryption!")


def example_7_performance_comparison():
    """Example 7: Performance comparison"""
    print_section("Example 7: Performance Comparison")
    
    db = ag.Database(key_size=2048)
    
    # Small dataset (benefits from caching)
    small_data = [1, 2, 3, 4, 5] * 20  # 100 values, 5 unique
    
    print("Small dataset (100 values, 5 unique):")
    print("First run (cold cache):")
    start = time.time()
    result1 = db.sum(small_data)
    time1 = time.time() - start
    print(f"  Time: {time1:.3f}s")
    print(f"  Result: {result1}")
    
    print("\nSecond run (warm cache):")
    start = time.time()
    result2 = db.sum(small_data)
    time2 = time.time() - start
    print(f"  Time: {time2:.3f}s")
    print(f"  Result: {result2}")
    
    speedup = time1 / time2 if time2 > 0 else 1
    print(f"\nSpeedup: {speedup:.0f}x faster!")


def main():
    """Run all examples"""
    print("\n" + "="*60)
    print("  AGNIYA Library Usage Examples")
    print("  Use AGNIYA like NumPy/Pandas for encrypted data")
    print("="*60)
    
    examples = [
        example_1_basic_usage,
        example_2_aggregations,
        example_3_caching,
        example_4_compression,
        example_5_privacy_preserving_analytics,
        example_6_numpy_pandas_style,
        example_7_performance_comparison,
    ]
    
    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"\n❌ Error in {example.__name__}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("  All examples complete!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
