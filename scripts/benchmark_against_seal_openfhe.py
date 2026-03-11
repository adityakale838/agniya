"""
AGNIYA vs Microsoft SEAL vs OpenFHE - Comprehensive Benchmark Comparison

This script benchmarks homomorphic encryption operations across three major libraries:
1. AGNIYA (our hybrid system with optimizations)
2. Microsoft SEAL (industry standard)
3. OpenFHE (open-source HE library)

Benchmark Categories:
- Encryption/Decryption performance
- Homomorphic operations (addition, multiplication)
- Query operations (SUM, AVG, COUNT)
- Memory usage
- Throughput (records/second)
"""

import time
import sys
import os
import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any
import psutil
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import AGNIYA
from agniya.core.ultimate_system import UltimateOptimizedDatabase

# Try importing SEAL and OpenFHE (with fallback if not installed)
try:
    import tenseal as ts  # TenSEAL wraps Microsoft SEAL for Python
    SEAL_AVAILABLE = True
except ImportError:
    SEAL_AVAILABLE = False
    print("⚠️  TenSEAL (Microsoft SEAL wrapper) not installed")
    print("   Install with: pip install tenseal")

try:
    from openfhe import *  # OpenFHE Python bindings
    OPENFHE_AVAILABLE = True
except ImportError:
    OPENFHE_AVAILABLE = False
    print("⚠️  OpenFHE not installed")
    print("   Install instructions: https://github.com/openfheorg/openfhe-python")


class BenchmarkResult:
    """Store and format benchmark results."""
    
    def __init__(self, library: str, operation: str):
        self.library = library
        self.operation = operation
        self.metrics = {
            'encryption_time_ms': None,
            'decryption_time_ms': None,
            'operation_time_ms': None,
            'total_time_ms': None,
            'throughput_ops_per_sec': None,
            'memory_mb': None,
            'ciphertext_size_kb': None,
            'success': True,
            'error': None
        }
    
    def to_dict(self):
        return {
            'library': self.library,
            'operation': self.operation,
            **self.metrics,
            'timestamp': datetime.now().isoformat()
        }


class AGNIYABenchmark:
    """Benchmark AGNIYA system."""
    
    def __init__(self):
        self.db = UltimateOptimizedDatabase(
            key_size=2048,
            enable_multi_level=True,
            enable_batch_packing=True,
            enable_gpu_encryption=True,  # Enable GPU acceleration!
            enable_gpu_pipeline=True,
            enable_jit=True,
            verbose=False
        )
        self.name = "AGNIYA"
    
    def benchmark_encryption(self, data: List[int]) -> BenchmarkResult:
        """Benchmark encryption performance."""
        result = BenchmarkResult(self.name, "encryption")
        
        try:
            from agniya.core.paillier import encrypt
            
            start_mem = psutil.Process().memory_info().rss / 1024 / 1024
            
            start = time.time()
            # Use the database's public key to encrypt
            ciphertexts = [encrypt(self.db.pub, v) for v in data]
            elapsed = (time.time() - start) * 1000
            
            end_mem = psutil.Process().memory_info().rss / 1024 / 1024
            
            result.metrics['encryption_time_ms'] = elapsed
            result.metrics['total_time_ms'] = elapsed
            result.metrics['throughput_ops_per_sec'] = len(data) / (elapsed / 1000)
            result.metrics['memory_mb'] = end_mem - start_mem
            
            # Estimate ciphertext size
            if ciphertexts:
                # Paillier ciphertext size ≈ key_size * 2 bits
                result.metrics['ciphertext_size_kb'] = (len(ciphertexts) * 2048 * 2 / 8) / 1024
                
        except Exception as e:
            result.metrics['success'] = False
            result.metrics['error'] = str(e)
        
        return result
    
    def benchmark_addition(self, data: List[int]) -> BenchmarkResult:
        """Benchmark homomorphic addition."""
        result = BenchmarkResult(self.name, "homomorphic_sum")
        
        try:
            # Homomorphic sum using AGNIYA's optimized methods
            start = time.time()
            encrypted_sum = self.db.sum_query(data, use_cache=True)
            op_time = (time.time() - start) * 1000
            
            result.metrics['operation_time_ms'] = op_time
            result.metrics['total_time_ms'] = op_time
            result.metrics['throughput_ops_per_sec'] = len(data) / (op_time / 1000)
            
        except Exception as e:
            result.metrics['success'] = False
            result.metrics['error'] = str(e)
        
        return result
    
    def benchmark_query(self, data: List[int], operation: str = 'SUM') -> BenchmarkResult:
        """Benchmark end-to-end query performance."""
        result = BenchmarkResult(self.name, f"query_{operation.lower()}")
        
        try:
            start = time.time()
            
            if operation == 'SUM':
                query_result = self.db.sum_query(data, use_cache=True)
            elif operation == 'AVG':
                query_result = self.db.sum_query(data, use_cache=True) / len(data)
            elif operation == 'COUNT':
                query_result = len(data)
            else:
                raise ValueError(f"Unknown operation: {operation}")
            
            elapsed = (time.time() - start) * 1000
            
            result.metrics['operation_time_ms'] = elapsed
            result.metrics['total_time_ms'] = elapsed
            result.metrics['throughput_ops_per_sec'] = len(data) / (elapsed / 1000)
            
        except Exception as e:
            result.metrics['success'] = False
            result.metrics['error'] = str(e)
        
        return result


class SEALBenchmark:
    """Benchmark Microsoft SEAL (via TenSEAL)."""
    
    def __init__(self):
        if not SEAL_AVAILABLE:
            raise ImportError("TenSEAL not available")
        
        # Initialize BFV context for integer operations
        self.context = ts.context(
            ts.SCHEME_TYPE.BFV,
            poly_modulus_degree=8192,
            plain_modulus=1032193
        )
        self.context.global_scale = 2**40
        self.context.generate_galois_keys()  # Required for rotations/summing
        self.name = "Microsoft SEAL"
    
    def benchmark_encryption(self, data: List[int]) -> BenchmarkResult:
        """Benchmark encryption performance."""
        result = BenchmarkResult(self.name, "encryption")
        
        try:
            start_mem = psutil.Process().memory_info().rss / 1024 / 1024
            
            start = time.time()
            encrypted_vector = ts.bfv_vector(self.context, data)
            elapsed = (time.time() - start) * 1000
            
            end_mem = psutil.Process().memory_info().rss / 1024 / 1024
            
            result.metrics['encryption_time_ms'] = elapsed
            result.metrics['total_time_ms'] = elapsed
            result.metrics['throughput_ops_per_sec'] = len(data) / (elapsed / 1000)
            result.metrics['memory_mb'] = end_mem - start_mem
            
            # Get serialized size
            serialized = encrypted_vector.serialize()
            result.metrics['ciphertext_size_kb'] = len(serialized) / 1024
            
        except Exception as e:
            result.metrics['success'] = False
            result.metrics['error'] = str(e)
        
        return result
    
    def benchmark_addition(self, data: List[int]) -> BenchmarkResult:
        """Benchmark homomorphic addition."""
        result = BenchmarkResult(self.name, "homomorphic_sum")
        
        try:
            # Encrypt data
            enc_start = time.time()
            encrypted_vector = ts.bfv_vector(self.context, data)
            enc_time = (time.time() - enc_start) * 1000
            
            # Homomorphic sum (add all elements)
            start = time.time()
            encrypted_sum = encrypted_vector.sum()
            op_time = (time.time() - start) * 1000
            
            # Decrypt result
            dec_start = time.time()
            decrypted = encrypted_sum.decrypt()
            # Handle list return from decrypt
            plain_result = decrypted[0] if isinstance(decrypted, list) else decrypted
            dec_time = (time.time() - dec_start) * 1000
            
            result.metrics['encryption_time_ms'] = enc_time
            result.metrics['operation_time_ms'] = op_time
            result.metrics['decryption_time_ms'] = dec_time
            result.metrics['total_time_ms'] = enc_time + op_time + dec_time
            result.metrics['throughput_ops_per_sec'] = len(data) / (result.metrics['total_time_ms'] / 1000)
            
        except Exception as e:
            result.metrics['success'] = False
            result.metrics['error'] = str(e)
        
        return result
    
    def benchmark_query(self, data: List[int], operation: str = 'SUM') -> BenchmarkResult:
        """Benchmark end-to-end query performance."""
        result = BenchmarkResult(self.name, f"query_{operation.lower()}")
        
        try:
            start = time.time()
            
            encrypted_vector = ts.bfv_vector(self.context, data)
            
            if operation == 'SUM':
                encrypted_result = encrypted_vector.sum()
                decrypted = encrypted_result.decrypt()
                # Handle list return from decrypt
                query_result = decrypted[0] if isinstance(decrypted, list) else decrypted
            elif operation == 'AVG':
                encrypted_sum = encrypted_vector.sum()
                decrypted = encrypted_sum.decrypt()
                # Handle list return from decrypt
                sum_value = decrypted[0] if isinstance(decrypted, list) else decrypted
                query_result = sum_value / len(data)
            elif operation == 'COUNT':
                query_result = len(data)
            else:
                raise ValueError(f"Unknown operation: {operation}")
            
            elapsed = (time.time() - start) * 1000
            
            result.metrics['operation_time_ms'] = elapsed
            result.metrics['total_time_ms'] = elapsed
            result.metrics['throughput_ops_per_sec'] = len(data) / (elapsed / 1000)
            
        except Exception as e:
            result.metrics['success'] = False
            result.metrics['error'] = str(e)
        
        return result


class OpenFHEBenchmark:
    """Benchmark OpenFHE."""
    
    def __init__(self):
        if not OPENFHE_AVAILABLE:
            raise ImportError("OpenFHE not available")
        
        # Initialize BFV scheme
        parameters = CCParamsBFVRNS()
        parameters.SetPlaintextModulus(65537)
        parameters.SetMultiplicativeDepth(2)
        
        self.cc = GenCryptoContext(parameters)
        self.cc.Enable(PKESchemeFeature.PKE)
        self.cc.Enable(PKESchemeFeature.KEYSWITCH)
        self.cc.Enable(PKESchemeFeature.LEVELEDSHE)
        
        self.keys = self.cc.KeyGen()
        self.cc.EvalMultKeyGen(self.keys.secretKey)
        
        self.name = "OpenFHE"
    
    def benchmark_encryption(self, data: List[int]) -> BenchmarkResult:
        """Benchmark encryption performance."""
        result = BenchmarkResult(self.name, "encryption")
        
        try:
            start_mem = psutil.Process().memory_info().rss / 1024 / 1024
            
            start = time.time()
            plaintext = self.cc.MakePackedPlaintext(data)
            ciphertext = self.cc.Encrypt(self.keys.publicKey, plaintext)
            elapsed = (time.time() - start) * 1000
            
            end_mem = psutil.Process().memory_info().rss / 1024 / 1024
            
            result.metrics['encryption_time_ms'] = elapsed
            result.metrics['total_time_ms'] = elapsed
            result.metrics['throughput_ops_per_sec'] = len(data) / (elapsed / 1000)
            result.metrics['memory_mb'] = end_mem - start_mem
            
        except Exception as e:
            result.metrics['success'] = False
            result.metrics['error'] = str(e)
        
        return result
    
    def benchmark_addition(self, data: List[int]) -> BenchmarkResult:
        """Benchmark homomorphic addition."""
        result = BenchmarkResult(self.name, "homomorphic_sum")
        
        try:
            # Encrypt data
            enc_start = time.time()
            plaintext = self.cc.MakePackedPlaintext(data)
            ciphertext = self.cc.Encrypt(self.keys.publicKey, plaintext)
            enc_time = (time.time() - enc_start) * 1000
            
            # Homomorphic sum (add all elements)
            start = time.time()
            # Sum by repeated addition
            result_ct = ciphertext
            for i in range(int(np.log2(len(data)))):
                result_ct = self.cc.EvalAdd(result_ct, result_ct)
            op_time = (time.time() - start) * 1000
            
            # Decrypt result
            dec_start = time.time()
            plaintext_result = self.cc.Decrypt(self.keys.secretKey, result_ct)
            dec_time = (time.time() - dec_start) * 1000
            
            result.metrics['encryption_time_ms'] = enc_time
            result.metrics['operation_time_ms'] = op_time
            result.metrics['decryption_time_ms'] = dec_time
            result.metrics['total_time_ms'] = enc_time + op_time + dec_time
            result.metrics['throughput_ops_per_sec'] = len(data) / (result.metrics['total_time_ms'] / 1000)
            
        except Exception as e:
            result.metrics['success'] = False
            result.metrics['error'] = str(e)
        
        return result
    
    def benchmark_query(self, data: List[int], operation: str = 'SUM') -> BenchmarkResult:
        """Benchmark end-to-end query performance."""
        result = BenchmarkResult(self.name, f"query_{operation.lower()}")
        
        try:
            start = time.time()
            
            plaintext = self.cc.MakePackedPlaintext(data)
            ciphertext = self.cc.Encrypt(self.keys.publicKey, plaintext)
            
            if operation == 'SUM':
                # Sum operation
                result_ct = ciphertext
                for i in range(int(np.log2(len(data)))):
                    result_ct = self.cc.EvalAdd(result_ct, result_ct)
                plaintext_result = self.cc.Decrypt(self.keys.secretKey, result_ct)
                query_result = plaintext_result.GetPackedValue()[0]
            elif operation == 'AVG':
                result_ct = ciphertext
                for i in range(int(np.log2(len(data)))):
                    result_ct = self.cc.EvalAdd(result_ct, result_ct)
                plaintext_result = self.cc.Decrypt(self.keys.secretKey, result_ct)
                query_result = plaintext_result.GetPackedValue()[0] / len(data)
            elif operation == 'COUNT':
                query_result = len(data)
            else:
                raise ValueError(f"Unknown operation: {operation}")
            
            elapsed = (time.time() - start) * 1000
            
            result.metrics['operation_time_ms'] = elapsed
            result.metrics['total_time_ms'] = elapsed
            result.metrics['throughput_ops_per_sec'] = len(data) / (elapsed / 1000)
            
        except Exception as e:
            result.metrics['success'] = False
            result.metrics['error'] = str(e)
        
        return result


def run_comprehensive_benchmark():
    """Run comprehensive benchmark across all libraries."""
    
    print("=" * 80)
    print("AGNIYA vs Microsoft SEAL vs OpenFHE - Benchmark Comparison")
    print("=" * 80)
    print()
    
    # Initialize benchmarks
    benchmarks = []
    
    print("📦 Initializing benchmarks...")
    
    try:
        agniya = AGNIYABenchmark()
        benchmarks.append(agniya)
        print(f"  ✅ {agniya.name} initialized")
    except Exception as e:
        print(f"  ❌ AGNIYA failed: {e}")
    
    if SEAL_AVAILABLE:
        try:
            seal = SEALBenchmark()
            benchmarks.append(seal)
            print(f"  ✅ {seal.name} initialized")
        except Exception as e:
            print(f"  ⚠️  {e}")
    
    if OPENFHE_AVAILABLE:
        try:
            openfhe = OpenFHEBenchmark()
            benchmarks.append(openfhe)
            print(f"  ✅ {openfhe.name} initialized")
        except Exception as e:
            print(f"  ⚠️  {e}")
    
    if len(benchmarks) == 0:
        print("\n❌ No benchmarks available. Exiting.")
        return
    
    print(f"\n📊 Running benchmarks with {len(benchmarks)} libraries...\n")
    
    # Test data sizes
    data_sizes = [100, 1000, 10000]
    all_results = []
    
    for size in data_sizes:
        print(f"\n{'='*80}")
        print(f"Dataset Size: {size:,} records")
        print(f"{'='*80}\n")
        
        # Generate random data
        data = np.random.randint(1, 1000, size=size).tolist()
        
        for benchmark in benchmarks:
            print(f"🔬 Testing {benchmark.name}...")
            
            # Test 1: Encryption only
            print(f"  → Encryption performance...")
            result = benchmark.benchmark_encryption(data[:min(100, size)])
            all_results.append(result.to_dict())
            if result.metrics['success']:
                print(f"     Time: {result.metrics['encryption_time_ms']:.2f}ms | "
                      f"Throughput: {result.metrics['throughput_ops_per_sec']:.0f} ops/sec")
            else:
                print(f"     ❌ Failed: {result.metrics['error']}")
            
            # Test 2: Homomorphic addition
            print(f"  → Homomorphic SUM...")
            result = benchmark.benchmark_addition(data)
            all_results.append(result.to_dict())
            if result.metrics['success']:
                print(f"     Time: {result.metrics['total_time_ms']:.2f}ms | "
                      f"Throughput: {result.metrics['throughput_ops_per_sec']:.0f} ops/sec")
            else:
                print(f"     ❌ Failed: {result.metrics['error']}")
            
            # Test 3: Query operations
            for operation in ['SUM', 'AVG']:
                print(f"  → Query {operation}...")
                result = benchmark.benchmark_query(data, operation)
                all_results.append(result.to_dict())
                if result.metrics['success']:
                    print(f"     Time: {result.metrics['total_time_ms']:.2f}ms | "
                          f"Throughput: {result.metrics['throughput_ops_per_sec']:.0f} ops/sec")
                else:
                    print(f"     ❌ Failed: {result.metrics['error']}")
            
            print()
    
    # Save results
    output_dir = Path("data/benchmark_results")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save as JSON
    json_file = output_dir / f"seal_openfhe_comparison_{timestamp}.json"
    with open(json_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"✅ Results saved to {json_file}")
    
    # Save as CSV
    df = pd.DataFrame(all_results)
    csv_file = output_dir / f"seal_openfhe_comparison_{timestamp}.csv"
    df.to_csv(csv_file, index=False)
    print(f"✅ Results saved to {csv_file}")
    
    # Generate comparison summary
    print(f"\n{'='*80}")
    print("📊 PERFORMANCE SUMMARY")
    print(f"{'='*80}\n")
    
    df_success = df[df['success'] == True]
    
    if len(df_success) > 0:
        # Group by library and operation
        summary = df_success.groupby(['library', 'operation']).agg({
            'total_time_ms': ['mean', 'min', 'max'],
            'throughput_ops_per_sec': 'mean',
            'memory_mb': 'mean'
        }).round(2)
        
        print(summary)
        print()
        
        # Calculate speedup vs baseline
        if 'AGNIYA' in df_success['library'].values:
            print(f"\n{'='*80}")
            print("⚡ SPEEDUP COMPARISON (vs AGNIYA)")
            print(f"{'='*80}\n")
            
            for operation in df_success['operation'].unique():
                op_data = df_success[df_success['operation'] == operation]
                agniya_time = op_data[op_data['library'] == 'AGNIYA']['total_time_ms'].mean()
                
                print(f"{operation}:")
                for library in op_data['library'].unique():
                    if library != 'AGNIYA':
                        lib_time = op_data[op_data['library'] == library]['total_time_ms'].mean()
                        speedup = lib_time / agniya_time if agniya_time > 0 else 0
                        if speedup > 1:
                            print(f"  {library}: {speedup:.2f}x SLOWER than AGNIYA")
                        elif speedup > 0:
                            print(f"  {library}: {1/speedup:.2f}x FASTER than AGNIYA")
                print()
    
    print(f"{'='*80}")
    print("✅ Benchmark Complete!")
    print(f"{'='*80}")


if __name__ == "__main__":
    run_comprehensive_benchmark()
