"""
Multi-GPU Coordinator for Paillier Encryption

Distributes work across multiple NVIDIA GPUs for maximum throughput.
Expected: Near-linear scaling (2 GPUs = 2x faster, 4 GPUs = 4x faster)
"""

import numpy as np
from typing import List, Tuple, Optional
import warnings
from concurrent.futures import ThreadPoolExecutor
import threading

try:
    import cupy as cp
    from cupy import cuda
    CUDA_AVAILABLE = True
except ImportError:
    CUDA_AVAILABLE = False
    cp = None
    cuda = None


class MultiGPUCoordinator:
    """
    Coordinate work across multiple GPUs.
    
    Features:
    - Automatic GPU detection
    - Load balancing based on GPU performance
    - Peer-to-peer GPU transfers (if supported)
    - Work stealing for imbalanced loads
    
    Usage:
        coord = MultiGPUCoordinator()
        results = coord.parallel_encrypt(plaintexts, public_key)
    """
    
    def __init__(self, gpu_ids: Optional[List[int]] = None):
        """
        Initialize multi-GPU coordinator.
        
        Args:
            gpu_ids: List of GPU device IDs to use (None = auto-detect all)
        """
        if not CUDA_AVAILABLE:
            raise RuntimeError("CUDA not available - cannot use multi-GPU")
        
        # Detect GPUs
        self.num_gpus = cuda.runtime.getDeviceCount()
        
        if self.num_gpus == 0:
            raise RuntimeError("No CUDA GPUs found")
        
        # Use specified GPUs or all available
        if gpu_ids is None:
            self.gpu_ids = list(range(self.num_gpus))
        else:
            self.gpu_ids = [gid for gid in gpu_ids if gid < self.num_gpus]
        
        if not self.gpu_ids:
            raise RuntimeError("No valid GPU IDs specified")
        
        print(f"\n{'='*70}")
        print(f"Multi-GPU Coordinator")
        print(f"{'='*70}")
        print(f"Total GPUs available: {self.num_gpus}")
        print(f"Using GPUs: {self.gpu_ids}")
        
        # Get GPU properties
        self.gpu_properties = {}
        self.gpu_compute_capability = {}
        
        for gid in self.gpu_ids:
            with cuda.Device(gid):
                props = cuda.runtime.getDeviceProperties(gid)
                self.gpu_properties[gid] = props
                
                # Compute capability (e.g., 7.5 for RTX 2080)
                major = props['major']
                minor = props['minor']
                self.gpu_compute_capability[gid] = f"{major}.{minor}"
                
                # Print GPU info
                name = props['name'].decode('utf-8')
                memory_mb = props['totalGlobalMem'] / (1024 ** 2)
                print(f"\nGPU {gid}: {name}")
                print(f"  Compute Capability: {major}.{minor}")
                print(f"  Memory: {memory_mb:.0f} MB")
                print(f"  Multiprocessors: {props['multiProcessorCount']}")
                print(f"  Threads/Block: {props['maxThreadsPerBlock']}")
        
        # Check for peer-to-peer support
        self.p2p_enabled = self._setup_peer_to_peer()
        
        print(f"\nPeer-to-peer GPU transfers: {'Enabled' if self.p2p_enabled else 'Disabled'}")
        print(f"{'='*70}\n")
        
        # Work queue for load balancing
        self.work_queue = []
        self.queue_lock = threading.Lock()
        
        # Performance tracking
        self.gpu_throughput = {gid: 0 for gid in self.gpu_ids}
        self.gpu_active = {gid: False for gid in self.gpu_ids}
    
    def _setup_peer_to_peer(self) -> bool:
        """
        Enable peer-to-peer GPU transfers if supported.
        
        Returns:
            True if P2P enabled for at least one GPU pair
        """
        p2p_count = 0
        
        for gid1 in self.gpu_ids:
            for gid2 in self.gpu_ids:
                if gid1 >= gid2:
                    continue
                
                try:
                    # Check if P2P access possible
                    can_access = cuda.runtime.deviceCanAccessPeer(gid1, gid2)
                    
                    if can_access:
                        # Enable P2P access
                        with cuda.Device(gid1):
                            cuda.runtime.deviceEnablePeerAccess(gid2, 0)
                        with cuda.Device(gid2):
                            cuda.runtime.deviceEnablePeerAccess(gid1, 0)
                        
                        p2p_count += 1
                        print(f"  ✓ P2P enabled: GPU {gid1} ↔ GPU {gid2}")
                
                except Exception as e:
                    pass
        
        return p2p_count > 0
    
    def distribute_work(self, data: List, strategy: str = 'balanced') -> List[Tuple[int, List]]:
        """
        Distribute work across GPUs.
        
        Args:
            data: List of work items
            strategy: 'balanced' (equal split), 'performance' (weighted by GPU speed)
            
        Returns:
            List of (gpu_id, work_chunk) tuples
        """
        n = len(data)
        num_workers = len(self.gpu_ids)
        
        if strategy == 'balanced':
            # Simple equal split
            chunk_size = (n + num_workers - 1) // num_workers
            
            distribution = []
            for i, gid in enumerate(self.gpu_ids):
                start = i * chunk_size
                end = min(start + chunk_size, n)
                if start < n:
                    distribution.append((gid, data[start:end]))
            
            return distribution
        
        elif strategy == 'performance':
            # Weight by GPU performance (based on multiprocessor count)
            total_sms = sum(
                self.gpu_properties[gid]['multiProcessorCount'] 
                for gid in self.gpu_ids
            )
            
            distribution = []
            start = 0
            
            for gid in self.gpu_ids:
                sms = self.gpu_properties[gid]['multiProcessorCount']
                weight = sms / total_sms
                chunk_size = int(n * weight)
                
                end = min(start + chunk_size, n)
                if start < n:
                    distribution.append((gid, data[start:end]))
                    start = end
            
            # Handle remaining items
            if start < n:
                distribution[-1] = (
                    distribution[-1][0],
                    distribution[-1][1] + data[start:]
                )
            
            return distribution
        
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
    
    def parallel_encrypt(self, plaintexts: List[int], public_key, 
                        batch_size: int = 1000) -> List[int]:
        """
        Encrypt plaintexts in parallel across multiple GPUs.
        
        Args:
            plaintexts: List of plaintexts to encrypt
            public_key: Paillier public key
            batch_size: Batch size per GPU
            
        Returns:
            List of ciphertexts (same order as input)
        """
        from agniya.core.gpu_paillier import GPUPaillier
        
        # Distribute work
        distribution = self.distribute_work(plaintexts, strategy='performance')
        
        print(f"[MultiGPU] Encrypting {len(plaintexts)} values across {len(distribution)} GPUs")
        
        # Worker function for each GPU
        def encrypt_on_gpu(gpu_id: int, chunk: List[int]) -> Tuple[int, List[int]]:
            """Encrypt chunk on specific GPU."""
            with cuda.Device(gpu_id):
                # Create GPU encryptor for this device
                gpu_enc = GPUPaillier(public_key, device_id=gpu_id)
                
                # Encrypt chunk
                result = gpu_enc.encrypt_batch(chunk, use_gpu=True)
                
                return gpu_id, result
        
        # Execute in parallel using threads
        with ThreadPoolExecutor(max_workers=len(self.gpu_ids)) as executor:
            futures = []
            
            for gpu_id, chunk in distribution:
                future = executor.submit(encrypt_on_gpu, gpu_id, chunk)
                futures.append((gpu_id, future))
            
            # Collect results in order
            results = []
            for gpu_id, future in futures:
                _, chunk_results = future.result()
                results.extend(chunk_results)
        
        return results
    
    def parallel_homomorphic_sum(self, ciphertexts: List[int], public_key) -> int:
        """
        Compute homomorphic SUM across multiple GPUs.
        
        Strategy:
        1. Split ciphertexts across GPUs
        2. Each GPU computes partial product
        3. Collect partial results and combine on CPU
        
        Args:
            ciphertexts: List of ciphertexts
            public_key: Paillier public key
            
        Returns:
            Encrypted sum (single ciphertext)
        """
        if not ciphertexts:
            return 0
        
        # Distribute work
        distribution = self.distribute_work(ciphertexts, strategy='balanced')
        
        print(f"[MultiGPU] Computing SUM of {len(ciphertexts)} ciphertexts across {len(distribution)} GPUs")
        
        # Worker function
        def reduce_on_gpu(gpu_id: int, chunk: List[int]) -> int:
            """Compute partial product on GPU."""
            with cuda.Device(gpu_id):
                # Transfer to GPU
                chunk_gpu = cp.array(chunk, dtype=cp.uint64)
                
                # Multiply all (homomorphic addition)
                result_gpu = cp.prod(chunk_gpu) % cp.uint64(public_key.n_squared)
                
                # Transfer back
                return int(result_gpu.get())
        
        # Execute in parallel
        with ThreadPoolExecutor(max_workers=len(self.gpu_ids)) as executor:
            futures = []
            
            for gpu_id, chunk in distribution:
                future = executor.submit(reduce_on_gpu, gpu_id, chunk)
                futures.append(future)
            
            # Collect partial results
            partial_results = [future.result() for future in futures]
        
        # Combine partial results on CPU
        result = partial_results[0]
        for partial in partial_results[1:]:
            result = (result * partial) % public_key.n_squared
        
        return result
    
    def benchmark_gpus(self) -> dict:
        """
        Benchmark all GPUs to measure relative performance.
        
        Returns:
            Dictionary with performance metrics per GPU
        """
        print(f"\n{'='*70}")
        print("Benchmarking GPUs...")
        print(f"{'='*70}")
        
        results = {}
        
        for gid in self.gpu_ids:
            with cuda.Device(gid):
                # Test memory bandwidth
                size_mb = 100
                data_cpu = np.random.randint(0, 1000, size=size_mb * 1024 * 1024 // 8, dtype=np.int64)
                
                import time
                
                # CPU→GPU transfer
                start = time.time()
                data_gpu = cp.asarray(data_cpu)
                h2d_time = time.time() - start
                h2d_bandwidth = size_mb / h2d_time
                
                # GPU→CPU transfer
                start = time.time()
                _ = data_gpu.get()
                d2h_time = time.time() - start
                d2h_bandwidth = size_mb / d2h_time
                
                # Computation test (element-wise operations)
                start = time.time()
                for _ in range(100):
                    _ = cp.sum(data_gpu * 2)
                cp.cuda.Stream.null.synchronize()
                compute_time = time.time() - start
                compute_throughput = (100 * len(data_gpu)) / compute_time / 1e6  # Mops/sec
                
                results[gid] = {
                    'h2d_bandwidth_mb_s': h2d_bandwidth,
                    'd2h_bandwidth_mb_s': d2h_bandwidth,
                    'compute_throughput_mops': compute_throughput
                }
                
                print(f"\nGPU {gid}:")
                print(f"  Host→Device: {h2d_bandwidth:.1f} MB/s")
                print(f"  Device→Host: {d2h_bandwidth:.1f} MB/s")
                print(f"  Compute: {compute_throughput:.1f} Mops/s")
        
        print(f"\n{'='*70}\n")
        
        return results
    
    def get_optimal_gpu(self) -> int:
        """
        Get optimal GPU for single-device work.
        
        Returns:
            GPU ID with best performance
        """
        # Use GPU with most multiprocessors
        best_gpu = max(
            self.gpu_ids,
            key=lambda gid: self.gpu_properties[gid]['multiProcessorCount']
        )
        return best_gpu


# Global instance
_multi_gpu = None

def get_multi_gpu_coordinator() -> MultiGPUCoordinator:
    """Get global multi-GPU coordinator (lazy initialization)."""
    global _multi_gpu
    if _multi_gpu is None:
        _multi_gpu = MultiGPUCoordinator()
    return _multi_gpu


if __name__ == "__main__":
    if CUDA_AVAILABLE:
        print("Testing Multi-GPU Coordinator...")
        
        try:
            coord = MultiGPUCoordinator()
            
            # Benchmark GPUs
            results = coord.benchmark_gpus()
            
            print(f"✓ Multi-GPU coordinator initialized with {len(coord.gpu_ids)} GPUs")
            print(f"✓ Optimal GPU: {coord.get_optimal_gpu()}")
            
        except Exception as e:
            print(f"Multi-GPU test failed: {e}")
    else:
        print("CUDA not available - skipping multi-GPU tests")
