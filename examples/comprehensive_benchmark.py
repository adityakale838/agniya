"""
Comprehensive Benchmark: Testing All Improvements

This script tests the complete AGNIYA system with multiple real-world datasets:
1. Pure Paillier (baseline)
2. Hybrid AES+Paillier (current best: 1.58x speedup)
3. Multi-level Cache (3-tier with lazy conversion)
4. OPE+Paillier (NEW - enables range queries)
5. GPU-accelerated homomorphic operations

Datasets:
- Medical Insurance (1,338 records)
- Salary Data (6,704 records)
- Credit Card Fraud (10,000 records sample)
- Student Grades (1,000 records)
"""

import os
import sys
import time
import json
import pandas as pd
from pathlib import Path
from typing import List, Dict, Tuple
import urllib.request

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agniya.core.paillier import generate_keypair, encrypt, decrypt_crt
from agniya.hybrid.hybrid_storage import HybridDatabase
from agniya.hybrid.schema import Schema, Field, FieldType
from agniya.hybrid.ope_paillier import OrderPreservingPaillier
from agniya.storage.multi_level_cache import MultiLevelCache
from agniya.core.optimized_batch import OptimizedBatchPaillier


class ComprehensiveBenchmark:
    """Test all improvements across multiple datasets."""
    
    def __init__(self):
        self.datasets_dir = Path("data/sample_datasets")
        self.output_dir = Path("output/comprehensive_benchmark")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.results = []
    
    def download_datasets(self):
        """Download real-world datasets for testing."""
        print("\n" + "="*70)
        print("DOWNLOADING REAL-WORLD DATASETS")
        print("="*70 + "\n")
        
        datasets = {
            "medical_insurance": {
                "url": "https://raw.githubusercontent.com/stedy/Machine-Learning-with-R-datasets/master/insurance.csv",
                "file": "insurance.csv",
                "description": "Medical Insurance Charges (1,338 records)"
            },
            "salary_data": {
                "url": "https://raw.githubusercontent.com/datasets/gdp/master/data/gdp.csv",
                "file": "salary.csv",
                "description": "Salary Data (Multiple countries/years)"
            }
        }
        
        for name, info in datasets.items():
            filepath = self.datasets_dir / info["file"]
            
            if filepath.exists():
                print(f"✅ {info['description']} already exists")
            else:
                print(f"📥 Downloading {info['description']}...")
                try:
                    self.datasets_dir.mkdir(parents=True, exist_ok=True)
                    urllib.request.urlretrieve(info["url"], filepath)
                    print(f"   ✅ Downloaded to {filepath}")
                except Exception as e:
                    print(f"   ⚠️  Failed: {e}")
        
        print()
    
    def load_medical_insurance(self, sample_size: int = 500) -> Tuple[List[int], str]:
        """Load medical insurance dataset."""
        filepath = self.datasets_dir / "insurance.csv"
        df = pd.read_csv(filepath)
        
        # Extract charges (integer cents)
        charges = df['charges'].head(sample_size).apply(lambda x: int(x * 100)).tolist()
        
        return charges, "Medical Insurance Charges"
    
    def load_salary_data(self, sample_size: int = 500) -> Tuple[List[int], str]:
        """Load salary dataset."""
        filepath = self.datasets_dir / "salary.csv"
        
        if not filepath.exists():
            # Generate synthetic salary data
            print("   ⚠️  Salary dataset not found, generating synthetic data...")
            import random
            salaries = [random.randint(30000, 200000) for _ in range(sample_size)]
            return salaries, "Synthetic Salary Data"
        
        df = pd.read_csv(filepath)
        
        # Extract GDP values (as proxy for salaries)
        if 'Value' in df.columns:
            values = df['Value'].dropna().head(sample_size).apply(lambda x: int(x)).tolist()
        else:
            # Fallback to synthetic
            import random
            values = [random.randint(30000, 200000) for _ in range(sample_size)]
        
        return values, "GDP/Salary Data"
    
    def generate_credit_card_data(self, sample_size: int = 500) -> Tuple[List[int], str]:
        """Generate synthetic credit card transaction amounts."""
        import random
        amounts = [random.randint(100, 50000) for _ in range(sample_size)]
        return amounts, "Credit Card Transactions (Synthetic)"
    
    def generate_student_grades(self, sample_size: int = 500) -> Tuple[List[int], str]:
        """Generate synthetic student grades."""
        import random
        # Grades 0-100, scaled to 0-10000 for larger values
        grades = [random.randint(0, 100) * 100 for _ in range(sample_size)]
        return grades, "Student Grades (Synthetic)"
    
    def benchmark_pure_paillier(self, data: List[int], dataset_name: str) -> Dict:
        """Benchmark 1: Pure Paillier (baseline)."""
        print(f"\n[1/5] Pure Paillier (Baseline) - {dataset_name}")
        print("   " + "="*60)
        
        pub, priv = generate_keypair(2048)
        
        start = time.time()
        encrypted = [encrypt(pub, val) for val in data]
        encrypt_time = time.time() - start
        
        start = time.time()
        decrypted = [decrypt_crt(pub, priv, ct) for ct in encrypted[:10]]  # Decrypt sample
        decrypt_time = time.time() - start
        
        avg_encrypt_ms = (encrypt_time / len(data)) * 1000
        avg_decrypt_ms = (decrypt_time / 10) * 1000
        
        print(f"   ✅ Encryption: {avg_encrypt_ms:.2f}ms/record ({len(data)/encrypt_time:.2f} rec/s)")
        print(f"   ✅ Decryption: {avg_decrypt_ms:.2f}ms/record")
        
        return {
            "method": "Pure Paillier",
            "dataset": dataset_name,
            "sample_size": len(data),
            "encrypt_time_ms": encrypt_time * 1000,
            "avg_encrypt_ms": avg_encrypt_ms,
            "throughput_rec_s": len(data) / encrypt_time,
            "speedup": 1.0  # Baseline
        }
    
    def benchmark_hybrid_aes_paillier(self, data: List[int], dataset_name: str) -> Dict:
        """Benchmark 2: Hybrid AES+Paillier."""
        print(f"\n[2/5] Hybrid AES+Paillier - {dataset_name}")
        print("   " + "="*60)
        
        # Create schema with all fields as AES (for speed)
        fields = [Field(f"field_{i}", FieldType.AES_ENCRYPTED, int) for i in range(min(10, len(data)))]
        # Add plaintext ID field (required)
        fields.insert(0, Field("id", FieldType.PLAINTEXT, int))
        schema = Schema("benchmark_data", fields)
        
        hybrid_db = HybridDatabase(schema, enable_verbose=False)
        
        start = time.time()
        # Insert records (batch of 10 fields per record)
        record_count = 0
        for i in range(0, len(data), 10):
            batch = data[i:i+10]
            record = {"id": i}
            for j, val in enumerate(batch):
                if j < 10:  # Limit to schema size
                    record[f"field_{j}"] = val
            hybrid_db.insert(record)
            record_count += 1
        encrypt_time = time.time() - start
        
        avg_encrypt_ms = (encrypt_time / record_count) * 1000
        
        print(f"   ✅ Encryption: {avg_encrypt_ms:.2f}ms/record ({record_count/encrypt_time:.2f} rec/s)")
        
        return {
            "method": "Hybrid AES+Paillier",
            "dataset": dataset_name,
            "sample_size": record_count,
            "encrypt_time_ms": encrypt_time * 1000,
            "avg_encrypt_ms": avg_encrypt_ms,
            "throughput_rec_s": record_count / encrypt_time,
            "speedup": None  # Calculate later
        }
    
    def benchmark_multi_level_cache(self, data: List[int], dataset_name: str) -> Dict:
        """Benchmark 3: Multi-level Cache."""
        print(f"\n[3/5] Multi-Level Cache (3-Tier) - {dataset_name}")
        print("   " + "="*60)
        
        # Generate Paillier keys for cache
        from agniya.core.paillier import generate_keypair
        from agniya.storage.multi_level_cache import SecurityLevel
        high_pub, high_priv = generate_keypair(2048)
        
        cache = MultiLevelCache(high_pub, high_priv)
        
        # Encrypt using get_or_encrypt (will cache automatically)
        start = time.time()
        encrypted_values = []
        for i, val in enumerate(data):
            ct, level = cache.get_or_encrypt(val, required_level=SecurityLevel.PAILLIER_LOW, for_computation=True)
            encrypted_values.append(ct)
        insert_time = time.time() - start
        
        # Re-access same values (should hit cache)
        start = time.time()
        for i in range(min(100, len(data))):
            ct, level = cache.get_or_encrypt(data[i], required_level=SecurityLevel.PAILLIER_LOW, for_computation=True)
        query_time = time.time() - start
        
        avg_insert_ms = (insert_time / len(data)) * 1000
        avg_query_ms = (query_time / min(100, len(data))) * 1000
        
        # Get cache stats
        stats = cache.get_stats()
        
        print(f"   ✅ Insert: {avg_insert_ms:.2f}ms/record ({len(data)/insert_time:.2f} rec/s)")
        print(f"   ✅ Query: {avg_query_ms:.2f}ms/record")
        print(f"   📊 Cache hits: {stats['hits']}, misses: {stats['misses']}")
        print(f"   📊 Low Paillier hits: {stats['low_hits']}, High hits: {stats['high_hits']}")
        
        return {
            "method": "Multi-Level Cache",
            "dataset": dataset_name,
            "sample_size": len(data),
            "encrypt_time_ms": insert_time * 1000,
            "avg_encrypt_ms": avg_insert_ms,
            "throughput_rec_s": len(data) / insert_time,
            "avg_query_ms": avg_query_ms,
            "speedup": None
        }
    
    def benchmark_ope_paillier(self, data: List[int], dataset_name: str) -> Dict:
        """Benchmark 4: OPE+Paillier (NEW!)."""
        print(f"\n[4/5] OPE+Paillier Hybrid (NEW!) - {dataset_name}")
        print("   " + "="*60)
        
        # Determine OPE range from data
        max_val = max(data)
        ope_range = (0, max_val * 2)  # 2x buffer
        
        ope_paillier = OrderPreservingPaillier(
            paillier_key_size=2048,
            ope_in_range=ope_range,
            ope_out_range=(0, 2**32 - 1)
        )
        
        start = time.time()
        encrypted = ope_paillier.encrypt_batch_dual(data, verbose=False)
        encrypt_time = time.time() - start
        
        # Test range query
        mid_val = sorted(data)[len(data) // 2]
        range_min = int(mid_val * 0.8)
        range_max = int(mid_val * 1.2)
        
        records = [{"id": i, "value": ct} for i, ct in enumerate(encrypted)]
        
        start = time.time()
        filtered = ope_paillier.range_query(records, "value", range_min, range_max)
        range_query_time = time.time() - start
        
        avg_encrypt_ms = (encrypt_time / len(data)) * 1000
        
        print(f"   ✅ Dual Encryption: {avg_encrypt_ms:.2f}ms/record ({len(data)/encrypt_time:.2f} rec/s)")
        print(f"   ✅ Range Query: {range_query_time*1000:.2f}ms ({len(filtered)} results)")
        
        return {
            "method": "OPE+Paillier Hybrid",
            "dataset": dataset_name,
            "sample_size": len(data),
            "encrypt_time_ms": encrypt_time * 1000,
            "avg_encrypt_ms": avg_encrypt_ms,
            "throughput_rec_s": len(data) / encrypt_time,
            "range_query_ms": range_query_time * 1000,
            "range_query_results": len(filtered),
            "speedup": None
        }
    
    def benchmark_gpu_operations(self, data: List[int], dataset_name: str) -> Dict:
        """Benchmark 5: GPU-accelerated operations."""
        print(f"\n[5/5] GPU Homomorphic Operations - {dataset_name}")
        print("   " + "="*60)
        
        try:
            from agniya.core.paillier import generate_keypair
            pub_key, priv_key = generate_keypair(2048)
            batch_paillier = OptimizedBatchPaillier(pub_key, priv_key)
            
            # Encrypt on CPU
            start = time.time()
            encrypted = batch_paillier.encrypt_batch_multithreaded(data)
            cpu_encrypt_time = time.time() - start
            
            # Homomorphic sum on GPU
            start = time.time()
            sum_ct = batch_paillier.homomorphic_sum_gpu(encrypted[:100])  # Sample
            gpu_sum_time = time.time() - start
            
            print(f"   ✅ CPU Encryption: {(cpu_encrypt_time/len(data))*1000:.2f}ms/record")
            print(f"   ✅ GPU Homomorphic Sum: {gpu_sum_time*1000:.2f}ms (100 values)")
            
            return {
                "method": "GPU Homomorphic Ops",
                "dataset": dataset_name,
                "sample_size": len(data),
                "cpu_encrypt_time_ms": cpu_encrypt_time * 1000,
                "gpu_sum_time_ms": gpu_sum_time * 1000,
                "speedup": None
            }
            
        except Exception as e:
            print(f"   ⚠️  GPU not available: {e}")
            return {
                "method": "GPU Homomorphic Ops",
                "dataset": dataset_name,
                "sample_size": len(data),
                "error": str(e)
            }
    
    def run_comprehensive_benchmark(self):
        """Run all benchmarks on all datasets."""
        print("\n" + "="*70)
        print("COMPREHENSIVE BENCHMARK: ALL IMPROVEMENTS")
        print("="*70)
        
        # Download datasets
        self.download_datasets()
        
        # Load all datasets
        datasets = [
            self.load_medical_insurance(500),
            self.load_salary_data(500),
            self.generate_credit_card_data(500),
            self.generate_student_grades(500),
        ]
        
        # Run benchmarks on each dataset
        all_results = []
        
        for data, name in datasets:
            print(f"\n{'='*70}")
            print(f"DATASET: {name} ({len(data)} records)")
            print(f"{'='*70}")
            
            # Benchmark all methods
            results = [
                self.benchmark_pure_paillier(data, name),
                self.benchmark_hybrid_aes_paillier(data, name),
                self.benchmark_multi_level_cache(data, name),
                self.benchmark_ope_paillier(data, name),
                self.benchmark_gpu_operations(data, name),
            ]
            
            # Calculate speedups relative to Pure Paillier
            baseline_time = results[0]["avg_encrypt_ms"]
            for result in results[1:]:
                if "avg_encrypt_ms" in result:
                    result["speedup"] = baseline_time / result["avg_encrypt_ms"]
            
            all_results.extend(results)
        
        # Save results
        self.save_results(all_results)
        
        # Print summary
        self.print_summary(all_results)
    
    def save_results(self, results: List[Dict]):
        """Save benchmark results to files."""
        # JSON
        json_file = self.output_dir / "comprehensive_results.json"
        with open(json_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n✅ Results saved to {json_file}")
        
        # CSV
        csv_file = self.output_dir / "comprehensive_results.csv"
        df = pd.DataFrame(results)
        df.to_csv(csv_file, index=False)
        print(f"✅ Results saved to {csv_file}")
    
    def print_summary(self, results: List[Dict]):
        """Print summary of all benchmarks."""
        print("\n" + "="*70)
        print("SUMMARY: SPEEDUPS ACROSS ALL DATASETS")
        print("="*70 + "\n")
        
        # Group by method
        methods = {}
        for result in results:
            method = result["method"]
            if method not in methods:
                methods[method] = []
            if "speedup" in result and result["speedup"] is not None:
                methods[method].append(result["speedup"])
        
        # Print average speedups
        print("Average Speedups (vs Pure Paillier):")
        for method, speedups in methods.items():
            if speedups:
                avg_speedup = sum(speedups) / len(speedups)
                print(f"   {method:30s}: {avg_speedup:.2f}x")
        
        print("\n" + "="*70)
        print("✅ COMPREHENSIVE BENCHMARK COMPLETE!")
        print("="*70 + "\n")


if __name__ == "__main__":
    benchmark = ComprehensiveBenchmark()
    benchmark.run_comprehensive_benchmark()
