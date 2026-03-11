"""
Benchmarking Framework for Agniya Hybrid Encryption System

This module provides comprehensive benchmarking tools to measure and compare
performance across different encryption strategies.
"""

import time
import psutil
import json
from pathlib import Path
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, asdict
import numpy as np
import pandas as pd
from datetime import datetime


@dataclass
class BenchmarkResult:
    """Store results from a single benchmark run."""
    
    # Test identification
    test_name: str
    dataset_name: str
    dataset_size: int
    query_type: str
    
    # Performance metrics
    total_time_ms: float
    aes_decrypt_time_ms: Optional[float] = None
    paillier_encrypt_time_ms: Optional[float] = None
    homomorphic_compute_time_ms: Optional[float] = None
    result_decrypt_time_ms: Optional[float] = None
    
    # Throughput metrics
    records_per_second: Optional[float] = None
    operations_per_second: Optional[float] = None
    
    # Resource metrics
    peak_memory_mb: Optional[float] = None
    cpu_percent: Optional[float] = None
    
    # Storage metrics
    plaintext_size_bytes: Optional[int] = None
    aes_ciphertext_size_bytes: Optional[int] = None
    paillier_ciphertext_size_bytes: Optional[int] = None
    
    # Cache metrics (for Phase 1)
    cache_hits: Optional[int] = None
    cache_misses: Optional[int] = None
    cache_hit_rate: Optional[float] = None
    
    # Metadata
    timestamp: str = None
    system_info: Optional[Dict] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        
        # Calculate derived metrics
        if self.dataset_size and self.total_time_ms:
            self.records_per_second = (self.dataset_size / (self.total_time_ms / 1000))
        
        if self.cache_hits is not None and self.cache_misses is not None:
            total_requests = self.cache_hits + self.cache_misses
            if total_requests > 0:
                self.cache_hit_rate = self.cache_hits / total_requests


class BenchmarkSuite:
    """Comprehensive benchmarking suite for encryption methods."""
    
    def __init__(self, results_dir: Path = Path("data/benchmark_results")):
        """
        Initialize benchmark suite.
        
        Args:
            results_dir: Directory to save benchmark results
        """
        self.results_dir = results_dir
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.results: List[BenchmarkResult] = []
        
        # System information
        self.system_info = {
            'cpu_count': psutil.cpu_count(logical=True),
            'cpu_freq_mhz': psutil.cpu_freq().current if psutil.cpu_freq() else 'unknown',
            'total_memory_gb': psutil.virtual_memory().total / (1024**3),
            'python_version': psutil.Process().exe()
        }
    
    def measure_time_and_memory(self, func: Callable, *args, **kwargs) -> tuple:
        """
        Measure execution time and memory usage of a function.
        
        Args:
            func: Function to benchmark
            *args: Arguments to pass to function
            **kwargs: Keyword arguments to pass to function
            
        Returns:
            Tuple of (result, execution_time_ms, peak_memory_mb)
        """
        process = psutil.Process()
        
        # Get initial memory
        initial_memory = process.memory_info().rss / (1024 * 1024)
        
        # Measure execution time
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        
        # Get peak memory
        peak_memory = process.memory_info().rss / (1024 * 1024)
        memory_used = peak_memory - initial_memory
        
        execution_time_ms = (end_time - start_time) * 1000
        
        return result, execution_time_ms, memory_used
    
    def benchmark_baseline_plaintext(self, data: np.ndarray, operation: str) -> BenchmarkResult:
        """
        Benchmark baseline plaintext operations (no encryption).
        
        Args:
            data: Plaintext data array
            operation: Operation to perform ('sum', 'avg', 'count')
            
        Returns:
            BenchmarkResult object
        """
        def compute():
            if operation == 'sum':
                return np.sum(data)
            elif operation == 'avg':
                return np.mean(data)
            elif operation == 'count':
                return len(data)
            else:
                raise ValueError(f"Unknown operation: {operation}")
        
        result, exec_time, memory = self.measure_time_and_memory(compute)
        
        return BenchmarkResult(
            test_name="baseline_plaintext",
            dataset_name="array",
            dataset_size=len(data),
            query_type=operation,
            total_time_ms=exec_time,
            peak_memory_mb=memory,
            records_per_second=len(data) / (exec_time / 1000) if exec_time > 0 else 0,
            plaintext_size_bytes=data.nbytes,
            system_info=self.system_info
        )
    
    def benchmark_pure_paillier(self, data: np.ndarray, operation: str, 
                                encrypt_func: Callable, decrypt_func: Callable,
                                homomorphic_func: Callable) -> BenchmarkResult:
        """
        Benchmark pure Paillier encryption (baseline homomorphic approach).
        
        Args:
            data: Plaintext data array
            operation: Operation to perform
            encrypt_func: Paillier encryption function
            decrypt_func: Paillier decryption function
            homomorphic_func: Homomorphic operation function
            
        Returns:
            BenchmarkResult object
        """
        # Encrypt all data
        encrypted_data, encrypt_time, _ = self.measure_time_and_memory(
            lambda: [encrypt_func(int(x)) for x in data]
        )
        
        # Perform homomorphic operation
        result_encrypted, compute_time, memory = self.measure_time_and_memory(
            lambda: homomorphic_func(encrypted_data)
        )
        
        # Decrypt result
        result, decrypt_time, _ = self.measure_time_and_memory(
            lambda: decrypt_func(result_encrypted)
        )
        
        total_time = encrypt_time + compute_time + decrypt_time
        
        # Estimate ciphertext size (Paillier ciphertexts are ~2x key size)
        paillier_size = len(data) * 512  # Assuming 2048-bit keys = 256 bytes per ciphertext
        
        return BenchmarkResult(
            test_name="pure_paillier",
            dataset_name="array",
            dataset_size=len(data),
            query_type=operation,
            total_time_ms=total_time,
            paillier_encrypt_time_ms=encrypt_time,
            homomorphic_compute_time_ms=compute_time,
            result_decrypt_time_ms=decrypt_time,
            peak_memory_mb=memory,
            plaintext_size_bytes=data.nbytes,
            paillier_ciphertext_size_bytes=paillier_size,
            system_info=self.system_info
        )
    
    def benchmark_hybrid_basic(self, data: np.ndarray, operation: str,
                               aes_decrypt_func: Callable,
                               paillier_encrypt_func: Callable,
                               paillier_decrypt_func: Callable,
                               homomorphic_func: Callable) -> BenchmarkResult:
        """
        Benchmark basic hybrid AES→Paillier approach (no optimizations).
        
        Args:
            data: AES-encrypted data
            operation: Operation to perform
            aes_decrypt_func: AES decryption function
            paillier_encrypt_func: Paillier encryption function
            paillier_decrypt_func: Paillier decryption function
            homomorphic_func: Homomorphic operation function
            
        Returns:
            BenchmarkResult object
        """
        # Step 1: AES decryption
        plaintext_data, aes_time, _ = self.measure_time_and_memory(
            lambda: aes_decrypt_func(data)
        )
        
        # Step 2: Paillier encryption
        encrypted_data, paillier_enc_time, _ = self.measure_time_and_memory(
            lambda: [paillier_encrypt_func(int(x)) for x in plaintext_data]
        )
        
        # Step 3: Homomorphic computation
        result_encrypted, compute_time, memory = self.measure_time_and_memory(
            lambda: homomorphic_func(encrypted_data)
        )
        
        # Step 4: Decrypt result
        result, decrypt_time, _ = self.measure_time_and_memory(
            lambda: paillier_decrypt_func(result_encrypted)
        )
        
        total_time = aes_time + paillier_enc_time + compute_time + decrypt_time
        
        return BenchmarkResult(
            test_name="hybrid_basic",
            dataset_name="array",
            dataset_size=len(plaintext_data),
            query_type=operation,
            total_time_ms=total_time,
            aes_decrypt_time_ms=aes_time,
            paillier_encrypt_time_ms=paillier_enc_time,
            homomorphic_compute_time_ms=compute_time,
            result_decrypt_time_ms=decrypt_time,
            peak_memory_mb=memory,
            aes_ciphertext_size_bytes=len(data) * 16,  # AES block size
            system_info=self.system_info
        )
    
    def add_result(self, result: BenchmarkResult):
        """Add a benchmark result to the suite."""
        self.results.append(result)
    
    def save_results(self, filename: str = "benchmark_results.json"):
        """Save all benchmark results to JSON file."""
        filepath = self.results_dir / filename
        
        results_dict = [asdict(r) for r in self.results]
        
        with open(filepath, 'w') as f:
            json.dump(results_dict, f, indent=2)
        
        print(f"Saved {len(self.results)} benchmark results to {filepath}")
    
    def generate_comparison_report(self) -> pd.DataFrame:
        """
        Generate a comparison report of all benchmark results.
        
        Returns:
            DataFrame with comparative analysis
        """
        if not self.results:
            return pd.DataFrame()
        
        # Convert results to DataFrame
        df = pd.DataFrame([asdict(r) for r in self.results])
        
        # Group by test_name and calculate statistics
        comparison = df.groupby('test_name').agg({
            'total_time_ms': ['mean', 'std', 'min', 'max'],
            'records_per_second': ['mean', 'std'],
            'peak_memory_mb': ['mean', 'max'],
            'cache_hit_rate': 'mean'
        }).round(2)
        
        return comparison
    
    def plot_comparison(self, metric: str = 'total_time_ms', save_path: Optional[Path] = None):
        """
        Plot comparison of different methods.
        
        Args:
            metric: Metric to plot
            save_path: Optional path to save plot
        """
        try:
            import matplotlib.pyplot as plt
            
            df = pd.DataFrame([asdict(r) for r in self.results])
            
            # Group by test method
            grouped = df.groupby('test_name')[metric].mean()
            
            plt.figure(figsize=(10, 6))
            grouped.plot(kind='bar')
            plt.title(f'Comparison of {metric}')
            plt.ylabel(metric)
            plt.xlabel('Method')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path)
                print(f"Saved plot to {save_path}")
            else:
                plt.show()
                
        except ImportError:
            print("matplotlib not installed. Install with: pip install matplotlib")


class QueryBenchmark:
    """Benchmark specific database queries."""
    
    def __init__(self, suite: BenchmarkSuite):
        self.suite = suite
    
    def benchmark_aggregation_query(self, df: pd.DataFrame, column: str, 
                                    operation: str, method: str) -> BenchmarkResult:
        """
        Benchmark an aggregation query on a DataFrame column.
        
        Args:
            df: Input DataFrame
            column: Column to aggregate
            operation: 'sum', 'avg', or 'count'
            method: Encryption method being tested
            
        Returns:
            BenchmarkResult object
        """
        data = df[column].dropna().values
        
        start_time = time.perf_counter()
        
        if operation == 'sum':
            result = np.sum(data)
        elif operation == 'avg':
            result = np.mean(data)
        elif operation == 'count':
            result = len(data)
        else:
            raise ValueError(f"Unknown operation: {operation}")
        
        end_time = time.perf_counter()
        exec_time_ms = (end_time - start_time) * 1000
        
        return BenchmarkResult(
            test_name=method,
            dataset_name=f"dataframe_{column}",
            dataset_size=len(data),
            query_type=f"{operation}_{column}",
            total_time_ms=exec_time_ms,
            system_info=self.suite.system_info
        )


def print_summary(results: List[BenchmarkResult]):
    """Print a summary of benchmark results."""
    print("\n" + "=" * 80)
    print("BENCHMARK SUMMARY")
    print("=" * 80)
    
    df = pd.DataFrame([asdict(r) for r in results])
    
    # Group by test method
    for test_name in df['test_name'].unique():
        test_results = df[df['test_name'] == test_name]
        
        print(f"\n{test_name.upper()}")
        print("-" * 80)
        print(f"  Average Time: {test_results['total_time_ms'].mean():.2f} ms")
        print(f"  Throughput: {test_results['records_per_second'].mean():.0f} records/sec")
        print(f"  Peak Memory: {test_results['peak_memory_mb'].mean():.2f} MB")
        
        if 'cache_hit_rate' in test_results and test_results['cache_hit_rate'].notna().any():
            print(f"  Cache Hit Rate: {test_results['cache_hit_rate'].mean()*100:.1f}%")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    # Example usage
    suite = BenchmarkSuite()
    
    # Generate sample data
    test_data = np.random.randint(1000, 100000, size=10000)
    
    # Benchmark plaintext baseline
    result = suite.benchmark_baseline_plaintext(test_data, 'sum')
    suite.add_result(result)
    
    print_summary(suite.results)
