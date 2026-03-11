"""
Parallel Query Executor

Executes multiple queries in parallel for increased throughput.
Expected: 3-4x throughput improvement.
"""

import time
from typing import List, Dict, Any, Callable
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import multiprocessing as mp


class ParallelQueryExecutor:
    """Execute multiple database queries in parallel"""
    
    def __init__(self, database, num_workers: int = None, use_processes: bool = False):
        """
        Initialize parallel executor
        
        Args:
            database: Database instance to execute queries on
            num_workers: Number of parallel workers (default: CPU count)
            use_processes: Use processes instead of threads (for CPU-bound work)
        """
        self.db = database
        self.num_workers = num_workers or mp.cpu_count()
        
        # Use ThreadPoolExecutor for I/O-bound, ProcessPoolExecutor for CPU-bound
        if use_processes:
            self.executor = ProcessPoolExecutor(max_workers=self.num_workers)
        else:
            self.executor = ThreadPoolExecutor(max_workers=self.num_workers)
        
        self.use_processes = use_processes
    
    def execute_batch(self, queries: List[Dict[str, Any]]) -> List[Any]:
        """
        Execute multiple queries in parallel
        
        Args:
            queries: List of query dicts with 'values' and optional 'sensitive'
            
        Returns:
            List of query results in same order as input
        """
        futures = []
        
        for query in queries:
            values = query['values']
            sensitive = query.get('sensitive', False)
            
            # Submit query to executor
            future = self.executor.submit(
                self.db.sum_query_oram,
                values,
                sensitive
            )
            futures.append(future)
        
        # Collect results in order
        results = []
        for future in futures:
            try:
                result = future.result(timeout=30)  # 30s timeout
                results.append(result)
            except Exception as e:
                results.append(None)
                print(f"Query failed: {e}")
        
        return results
    
    def execute_batch_unordered(self, queries: List[Dict[str, Any]]) -> List[Any]:
        """
        Execute queries and return results as they complete (faster)
        
        Args:
            queries: List of query dicts
            
        Returns:
            List of results in completion order
        """
        futures = []
        
        for query in queries:
            values = query['values']
            sensitive = query.get('sensitive', False)
            
            future = self.executor.submit(
                self.db.sum_query_oram,
                values,
                sensitive
            )
            futures.append(future)
        
        # Collect as completed
        results = []
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"Query failed: {e}")
        
        return results
    
    def benchmark_throughput(self, num_queries: int = 100, query_size: int = 1000):
        """
        Benchmark parallel vs sequential throughput
        
        Args:
            num_queries: Number of queries to execute
            query_size: Number of values per query
        """
        import random
        
        print(f"\n{'='*70}")
        print(f"PARALLEL THROUGHPUT BENCHMARK")
        print(f"Queries: {num_queries}, Values per query: {query_size}")
        print('='*70)
        
        # Generate test queries
        queries = []
        for _ in range(num_queries):
            values = [random.randint(1, 10000) for _ in range(query_size)]
            queries.append({'values': values, 'sensitive': True})
        
        # Sequential execution
        print(f"\n⏱️  Sequential execution...")
        seq_start = time.time()
        seq_results = []
        for query in queries[:10]:  # Only first 10 for speed
            result = self.db.sum_query_oram(query['values'], query['sensitive'])
            seq_results.append(result)
        seq_time = time.time() - seq_start
        seq_qps = 10 / seq_time
        
        print(f"   Time: {seq_time:.2f}s")
        print(f"   Throughput: {seq_qps:.2f} queries/sec")
        
        # Parallel execution
        print(f"\n⚡ Parallel execution ({self.num_workers} workers)...")
        par_start = time.time()
        par_results = self.execute_batch(queries[:10])
        par_time = time.time() - par_start
        par_qps = 10 / par_time
        
        print(f"   Time: {par_time:.2f}s")
        print(f"   Throughput: {par_qps:.2f} queries/sec")
        
        # Results
        speedup = seq_time / par_time
        throughput_improvement = par_qps / seq_qps
        
        print(f"\n{'='*70}")
        print(f"📊 RESULTS:")
        print(f"   Sequential: {seq_qps:.2f} qps")
        print(f"   Parallel: {par_qps:.2f} qps")
        print(f"   🚀 Speedup: {speedup:.2f}x")
        print(f"   📈 Throughput: {throughput_improvement:.2f}x better")
        print('='*70)
        
        return {
            'sequential_qps': seq_qps,
            'parallel_qps': par_qps,
            'speedup': speedup,
            'num_workers': self.num_workers
        }
    
    def shutdown(self):
        """Shutdown executor and cleanup resources"""
        self.executor.shutdown(wait=True)


class AdaptiveParallelExecutor:
    """Adaptive executor that adjusts parallelism based on query characteristics"""
    
    def __init__(self, database, max_workers: int = None):
        """Initialize adaptive executor"""
        self.db = database
        self.max_workers = max_workers or mp.cpu_count()
        self.executor = None
    
    def execute_adaptive(self, queries: List[Dict[str, Any]]) -> List[Any]:
        """
        Execute queries with adaptive parallelism
        
        Small queries: More parallelism
        Large queries: Less parallelism (avoid memory pressure)
        """
        # Analyze queries
        avg_size = sum(len(q['values']) for q in queries) / len(queries)
        
        # Adaptive worker count
        if avg_size < 100:
            num_workers = self.max_workers
        elif avg_size < 1000:
            num_workers = max(2, self.max_workers // 2)
        else:
            num_workers = 2
        
        print(f"Adaptive parallelism: {num_workers} workers (avg query size: {avg_size:.0f})")
        
        # Execute with adaptive workers
        executor = ParallelQueryExecutor(self.db, num_workers=num_workers)
        results = executor.execute_batch(queries)
        executor.shutdown()
        
        return results
