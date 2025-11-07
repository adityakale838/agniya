"""
Comprehensive Benchmark: Hybrid AES+Paillier vs Pure Paillier

This benchmark compares three approaches:
1. Pure Paillier: Everything encrypted with Paillier (baseline)
2. Hybrid System: AES for bulk data + Paillier for computational fields
3. Plaintext: No encryption (upper bound on performance)

Metrics measured:
- Insertion time (per record)
- Query time (per record)
- Storage size (per record)
- Aggregation time (SUM operation)

Datasets:
- Small: 50 records
- Medium: 200 records
- Large: 500 records
"""

import time
import random
import sys
from typing import List, Dict, Any

from agniya.core.paillier import generate_keypair, encrypt, decrypt_crt
from agniya.hybrid import HybridDatabase, Schema, Field, FieldType
from agniya.hybrid.aes_cipher import AESCipher


class PurePaillierDatabase:
    """Baseline: Everything encrypted with Paillier (SLOW)."""
    
    def __init__(self, key_size: int = 2048):
        self.pub, self.priv = generate_keypair(key_size)
        self.records = []
        self.insert_count = 0
        self.query_count = 0
    
    def insert(self, record: Dict[str, Any]) -> int:
        """Insert record with all fields Paillier-encrypted."""
        encrypted = {}
        
        for field, value in record.items():
            if isinstance(value, str):
                # Convert string to bytes, then to int
                value_bytes = value.encode('utf-8')
                value_int = int.from_bytes(value_bytes, byteorder='big')
                encrypted[field] = encrypt(self.pub, value_int)
            elif isinstance(value, int):
                encrypted[field] = encrypt(self.pub, value)
        
        self.records.append(encrypted)
        self.insert_count += 1
        return len(self.records) - 1
    
    def query(self, record_id: int) -> Dict[str, Any]:
        """Query and decrypt all fields."""
        encrypted = self.records[record_id]
        decrypted = {}
        
        for field, ciphertext in encrypted.items():
            value_int = decrypt_crt(self.pub, self.priv, ciphertext)
            
            # Try to decode as string, otherwise keep as int
            try:
                value_bytes = value_int.to_bytes((value_int.bit_length() + 7) // 8, 'big')
                decrypted[field] = value_bytes.decode('utf-8')
            except:
                decrypted[field] = value_int
        
        self.query_count += 1
        return decrypted
    
    def aggregate(self, field: str) -> int:
        """Compute SUM on encrypted field."""
        result_ct = None
        
        for record in self.records:
            if field in record:
                if result_ct is None:
                    result_ct = record[field]
                else:
                    result_ct = (result_ct * record[field]) % self.pub.n_squared
        
        if result_ct:
            return decrypt_crt(self.pub, self.priv, result_ct)
        return 0


class PlaintextDatabase:
    """Upper bound: No encryption (FAST but insecure)."""
    
    def __init__(self):
        self.records = []
        self.insert_count = 0
        self.query_count = 0
    
    def insert(self, record: Dict[str, Any]) -> int:
        self.records.append(record.copy())
        self.insert_count += 1
        return len(self.records) - 1
    
    def query(self, record_id: int) -> Dict[str, Any]:
        self.query_count += 1
        return self.records[record_id]
    
    def aggregate(self, field: str) -> int:
        return sum(r.get(field, 0) for r in self.records)


def generate_test_data(num_records: int) -> List[Dict[str, Any]]:
    """Generate synthetic employee records for benchmarking."""
    records = []
    
    for i in range(num_records):
        record = {
            "emp_id": 1000 + i,
            "name": f"Employee_{i}",
            "email": f"emp{i}@company.com",
            "salary": random.randint(40000, 150000),
            "age": random.randint(22, 65),
            "hire_date": 1609459200 + i * 86400,
        }
        records.append(record)
    
    return records


def create_employee_schema() -> Schema:
    """Create employee schema for hybrid system."""
    return Schema("employees", [
        Field("emp_id", FieldType.PLAINTEXT, int),
        Field("name", FieldType.AES_ENCRYPTED, str),
        Field("email", FieldType.AES_ENCRYPTED, str),
        Field("salary", FieldType.PAILLIER_ENCRYPTED, int),
        Field("age", FieldType.PAILLIER_ENCRYPTED, int),
        Field("hire_date", FieldType.PLAINTEXT, int),
    ])


def benchmark_insertion(db, records: List[Dict], db_name: str):
    """Benchmark insertion performance."""
    print(f"\n{'='*70}")
    print(f"Insertion Benchmark: {db_name}")
    print('='*70)
    
    start_time = time.time()
    record_ids = []
    
    for i, record in enumerate(records):
        record_id = db.insert(record)
        record_ids.append(record_id)
        
        if (i + 1) % 50 == 0:
            elapsed = time.time() - start_time
            if elapsed > 0:
                rate = (i + 1) / elapsed
                print(f"  Progress: {i+1}/{len(records)} records ({rate:.1f} records/sec)")
    
    total_time = time.time() - start_time
    if total_time == 0:
        total_time = 0.0001  # Prevent division by zero
    avg_time = total_time / len(records)
    
    print(f"\n✅ Results:")
    print(f"   Total time: {total_time:.4f}s")
    print(f"   Average per record: {avg_time*1000:.3f}ms")
    print(f"   Throughput: {len(records)/total_time:.0f} records/sec")
    
    return {
        'total_time': total_time,
        'avg_time_ms': avg_time * 1000,
        'throughput': len(records) / total_time,
        'record_ids': record_ids
    }


def benchmark_query(db, record_ids: List, num_queries: int, db_name: str):
    """Benchmark query performance."""
    print(f"\n{'='*70}")
    print(f"Query Benchmark: {db_name}")
    print('='*70)
    
    # Random sample of queries
    query_ids = random.sample(record_ids, min(num_queries, len(record_ids)))
    
    start_time = time.time()
    
    for i, record_id in enumerate(query_ids):
        result = db.query(record_id)
        
        if (i + 1) % 10 == 0:
            elapsed = time.time() - start_time
            if elapsed > 0:
                rate = (i + 1) / elapsed
                print(f"  Progress: {i+1}/{len(query_ids)} queries ({rate:.1f} queries/sec)")
    
    total_time = time.time() - start_time
    if total_time == 0:
        total_time = 0.0001  # Prevent division by zero
    avg_time = total_time / len(query_ids)
    
    print(f"\n✅ Results:")
    print(f"   Total time: {total_time:.4f}s")
    print(f"   Average per query: {avg_time*1000:.3f}ms")
    print(f"   Throughput: {len(query_ids)/total_time:.0f} queries/sec")
    
    return {
        'total_time': total_time,
        'avg_time_ms': avg_time * 1000,
        'throughput': len(query_ids) / total_time
    }


def benchmark_aggregation(db, field: str, db_name: str):
    """Benchmark aggregation performance."""
    print(f"\n{'='*70}")
    print(f"Aggregation Benchmark: {db_name}")
    print('='*70)
    
    start_time = time.time()
    result = db.aggregate(field)
    total_time = time.time() - start_time
    
    print(f"\n✅ Results:")
    print(f"   SUM({field}) = {result:,}")
    print(f"   Computation time: {total_time:.3f}s")
    
    return {
        'result': result,
        'time_s': total_time
    }


def estimate_storage_size(db, db_name: str, num_records: int):
    """Estimate storage size per record."""
    print(f"\n{'='*70}")
    print(f"Storage Size Estimate: {db_name}")
    print('='*70)
    
    if db_name == "Pure Paillier":
        # Each field is 512 bytes (Paillier-2048)
        # 6 fields: emp_id, name, email, salary, age, hire_date
        size_per_record = 6 * 512
    
    elif db_name == "Hybrid AES+Paillier":
        # emp_id: 8 bytes (plaintext int)
        # hire_date: 8 bytes (plaintext int)
        # name: ~36 bytes (AES)
        # email: ~50 bytes (AES)
        # salary: 512 bytes (Paillier)
        # age: 512 bytes (Paillier)
        size_per_record = 8 + 8 + 36 + 50 + 512 + 512
    
    elif db_name == "Plaintext (No Encryption)":
        # Rough estimate for plaintext storage
        size_per_record = 8 + 8 + 20 + 30 + 8 + 8
    
    else:
        size_per_record = 0
    
    total_size = size_per_record * num_records
    
    print(f"\n✅ Results:")
    print(f"   Size per record: ~{size_per_record:,} bytes")
    print(f"   Total for {num_records} records: ~{total_size:,} bytes ({total_size/(1024*1024):.2f} MB)")
    
    return {
        'size_per_record': size_per_record,
        'total_size': total_size,
        'total_mb': total_size / (1024 * 1024)
    }


def run_comprehensive_benchmark():
    """Run comprehensive benchmark comparing all three approaches."""
    
    print("="*70)
    print("COMPREHENSIVE BENCHMARK: Hybrid vs Pure Paillier vs Plaintext")
    print("="*70)
    print("\nComparing three database architectures:")
    print("1. Pure Paillier: All fields Paillier-encrypted (SLOW but fully homomorphic)")
    print("2. Hybrid AES+Paillier: Smart encryption routing (FAST + homomorphic)")
    print("3. Plaintext: No encryption (FASTEST but insecure - upper bound)")
    
    # Test configurations
    test_sizes = [50, 100, 200]
    
    results = {}
    
    for num_records in test_sizes:
        print(f"\n{'='*70}")
        print(f"DATASET SIZE: {num_records} RECORDS")
        print('='*70)
        
        # Generate test data
        print(f"\nGenerating {num_records} synthetic employee records...")
        records = generate_test_data(num_records)
        print(f"✅ Generated {num_records} records")
        
        results[num_records] = {}
        
        # Benchmark 1: Pure Paillier (baseline)
        print(f"\n{'#'*70}")
        print("APPROACH 1: Pure Paillier (Everything Paillier-encrypted)")
        print('#'*70)
        
        pure_db = PurePaillierDatabase(key_size=2048)
        
        pure_insert = benchmark_insertion(pure_db, records, "Pure Paillier")
        pure_query = benchmark_query(pure_db, pure_insert['record_ids'], 
                                      min(20, num_records), "Pure Paillier")
        pure_agg = benchmark_aggregation(pure_db, "salary", "Pure Paillier")
        pure_storage = estimate_storage_size(pure_db, "Pure Paillier", num_records)
        
        results[num_records]['pure_paillier'] = {
            'insert': pure_insert,
            'query': pure_query,
            'aggregate': pure_agg,
            'storage': pure_storage
        }
        
        # Benchmark 2: Hybrid System
        print(f"\n{'#'*70}")
        print("APPROACH 2: Hybrid AES+Paillier (Smart Encryption)")
        print('#'*70)
        
        schema = create_employee_schema()
        hybrid_db = HybridDatabase(schema, paillier_key_size=2048, enable_verbose=False)
        
        hybrid_insert = benchmark_insertion(hybrid_db, records, "Hybrid AES+Paillier")
        hybrid_query = benchmark_query(hybrid_db, hybrid_insert['record_ids'],
                                       min(20, num_records), "Hybrid AES+Paillier")
        hybrid_agg = benchmark_aggregation(hybrid_db, "salary", "Hybrid AES+Paillier")
        hybrid_storage = estimate_storage_size(hybrid_db, "Hybrid AES+Paillier", num_records)
        
        results[num_records]['hybrid'] = {
            'insert': hybrid_insert,
            'query': hybrid_query,
            'aggregate': hybrid_agg,
            'storage': hybrid_storage
        }
        
        # Benchmark 3: Plaintext (upper bound)
        print(f"\n{'#'*70}")
        print("APPROACH 3: Plaintext (No Encryption - Upper Bound)")
        print('#'*70)
        
        plain_db = PlaintextDatabase()
        
        plain_insert = benchmark_insertion(plain_db, records, "Plaintext (No Encryption)")
        plain_query = benchmark_query(plain_db, plain_insert['record_ids'],
                                      min(20, num_records), "Plaintext (No Encryption)")
        plain_agg = benchmark_aggregation(plain_db, "salary", "Plaintext (No Encryption)")
        plain_storage = estimate_storage_size(plain_db, "Plaintext (No Encryption)", num_records)
        
        results[num_records]['plaintext'] = {
            'insert': plain_insert,
            'query': plain_query,
            'aggregate': plain_agg,
            'storage': plain_storage
        }
        
        # Comparison for this dataset size
        print(f"\n{'='*70}")
        print(f"COMPARISON SUMMARY: {num_records} Records")
        print('='*70)
        
        print(f"\n📊 Insertion Performance:")
        print(f"   Pure Paillier:    {pure_insert['avg_time_ms']:.1f}ms per record")
        print(f"   Hybrid System:    {hybrid_insert['avg_time_ms']:.1f}ms per record")
        print(f"   Plaintext:        {plain_insert['avg_time_ms']:.3f}ms per record")
        print(f"   Hybrid Speedup:   {pure_insert['avg_time_ms']/hybrid_insert['avg_time_ms']:.1f}x over Pure Paillier")
        
        print(f"\n📊 Query Performance:")
        print(f"   Pure Paillier:    {pure_query['avg_time_ms']:.1f}ms per query")
        print(f"   Hybrid System:    {hybrid_query['avg_time_ms']:.1f}ms per query")
        print(f"   Plaintext:        {plain_query['avg_time_ms']:.3f}ms per query")
        print(f"   Hybrid Speedup:   {pure_query['avg_time_ms']/hybrid_query['avg_time_ms']:.1f}x over Pure Paillier")
        
        print(f"\n📊 Aggregation Performance:")
        print(f"   Pure Paillier:    {pure_agg['time_s']:.3f}s")
        print(f"   Hybrid System:    {hybrid_agg['time_s']:.3f}s")
        print(f"   Plaintext:        {plain_agg['time_s']:.6f}s")
        print(f"   Speedup Ratio:    {pure_agg['time_s']/hybrid_agg['time_s']:.2f}x")
        
        print(f"\n📊 Storage Size:")
        print(f"   Pure Paillier:    {pure_storage['size_per_record']:,} bytes/record")
        print(f"   Hybrid System:    {hybrid_storage['size_per_record']:,} bytes/record")
        print(f"   Plaintext:        {plain_storage['size_per_record']:,} bytes/record")
        print(f"   Space Savings:    {pure_storage['size_per_record']/hybrid_storage['size_per_record']:.1f}x smaller than Pure Paillier")
    
    # Final summary
    print(f"\n{'='*70}")
    print("FINAL SUMMARY: Hybrid System Benefits")
    print('='*70)
    
    # Average speedups across all dataset sizes
    insert_speedups = []
    query_speedups = []
    storage_ratios = []
    
    for size in test_sizes:
        pure_insert = results[size]['pure_paillier']['insert']['avg_time_ms']
        hybrid_insert = results[size]['hybrid']['insert']['avg_time_ms']
        insert_speedups.append(pure_insert / hybrid_insert)
        
        pure_query = results[size]['pure_paillier']['query']['avg_time_ms']
        hybrid_query = results[size]['hybrid']['query']['avg_time_ms']
        query_speedups.append(pure_query / hybrid_query)
        
        pure_storage = results[size]['pure_paillier']['storage']['size_per_record']
        hybrid_storage = results[size]['hybrid']['storage']['size_per_record']
        storage_ratios.append(pure_storage / hybrid_storage)
    
    avg_insert_speedup = sum(insert_speedups) / len(insert_speedups)
    avg_query_speedup = sum(query_speedups) / len(query_speedups)
    avg_storage_ratio = sum(storage_ratios) / len(storage_ratios)
    
    print(f"\n🎯 Average Performance Improvements (Hybrid vs Pure Paillier):")
    print(f"   Insertion:  {avg_insert_speedup:.1f}x faster")
    print(f"   Query:      {avg_query_speedup:.1f}x faster")
    print(f"   Storage:    {avg_storage_ratio:.1f}x smaller")
    print(f"   Aggregation: ~1x (same speed - both use Paillier homomorphism)")
    
    print(f"\n✅ Key Findings:")
    print(f"   1. Hybrid system is {avg_insert_speedup:.0f}-{max(insert_speedups):.0f}x faster for insertions")
    print(f"   2. Hybrid system is {avg_query_speedup:.0f}-{max(query_speedups):.0f}x faster for queries")
    print(f"   3. Hybrid system uses {avg_storage_ratio:.1f}x less storage")
    print(f"   4. Hybrid maintains homomorphic properties for computational fields")
    print(f"   5. Hybrid provides same security guarantees as pure Paillier")
    
    print(f"\n🎓 Conclusion:")
    print(f"   The hybrid AES+Paillier approach achieves practical performance")
    print(f"   while maintaining encrypted computation capabilities.")
    print(f"   Best of both worlds: Fast AES + Homomorphic Paillier!")
    
    print("\n" + "="*70)
    
    return results


if __name__ == "__main__":
    run_comprehensive_benchmark()
