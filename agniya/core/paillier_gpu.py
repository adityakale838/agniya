"""
GPU-Accelerated Paillier Encryption

This module provides GPU-accelerated encryption for Paillier cryptosystem
using CuPy for parallel operations on NVIDIA GPUs.

Expected Impact: 5-10x speedup on encryption operations
OPTIMIZED: Adaptive batch sizing based on GPU memory and workload
"""

import time
import numpy as np
from typing import List, Tuple, Optional
import secrets

try:
    import cupy as cp
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False
    cp = None


def calculate_optimal_batch_size(num_values: int, gpu_memory_gb: float = None) -> int:
    """
    Calculate optimal batch size based on workload and GPU memory
    
    Args:
        num_values: Total number of values to process
        gpu_memory_gb: Available GPU memory in GB (auto-detect if None)
        
    Returns:
        Optimal batch size for GPU operations
    """
    if not GPU_AVAILABLE:
        return 512  # Fallback
    
    # Auto-detect GPU memory if not provided
    if gpu_memory_gb is None:
        try:
            mempool = cp.get_default_memory_pool()
            free_memory = mempool.free_bytes()
            gpu_memory_gb = free_memory / (1024**3)
        except:
            gpu_memory_gb = 4.0  # Conservative default
    
    # Heuristic: Use 50% of available memory, assume 8 bytes per value
    # Each encryption needs: plaintext (8) + random (8) + ciphertext (8) = 24 bytes
    max_batch_from_memory = int((gpu_memory_gb * 0.5 * 1024**3) / 24)
    
    # Performance heuristics based on workload size
    if num_values < 100:
        optimal_size = 64  # Small workload, minimize overhead
    elif num_values < 1000:
        optimal_size = 256  # Medium workload
    elif num_values < 10000:
        optimal_size = 1024  # Large workload, maximize GPU utilization
    else:
        optimal_size = 4096  # Very large workload, full GPU saturation
    
    # Don't exceed memory limits or workload size
    return min(optimal_size, max_batch_from_memory, num_values)


class GPUPaillierEncryptor:
    """GPU-accelerated Paillier encryption using CuPy with adaptive batch sizing"""
    
    def __init__(self, public_key, adaptive_batching: bool = True):
        """
        Initialize GPU encryptor with public key
        
        Args:
            public_key: Paillier public key
            adaptive_batching: Enable adaptive batch size optimization
        """
        if not GPU_AVAILABLE:
            raise RuntimeError("CuPy not available - cannot use GPU encryption")
        
        self.n = public_key.n
        self.g = public_key.g
        self.nsquare = public_key.n_squared  # FIX: use n_squared not nsquare
        self.adaptive_batching = adaptive_batching
        
        # Transfer constants to GPU (one-time cost)
        self.n_gpu = cp.int64(self.n)
        self.g_gpu = cp.int64(self.g)
        self.nsquare_gpu = cp.int64(self.nsquare)
        
        # Create CUDA stream for async operations
        self.stream = cp.cuda.Stream(non_blocking=True)
        
        # Cache for repeated values
        self.gpu_cache = {}
        
        # Detect GPU memory
        try:
            mempool = cp.get_default_memory_pool()
            self.gpu_memory_gb = mempool.free_bytes() / (1024**3)
        except:
            self.gpu_memory_gb = 4.0  # Conservative default
    
    def batch_encrypt_gpu(self, plaintexts: List[int], batch_size: int = None) -> List[int]:
        """
        Encrypt multiple plaintexts in parallel on GPU
        
        Args:
            plaintexts: List of integers to encrypt
            batch_size: Number of values per GPU batch (auto if None)
            
        Returns:
            List of ciphertexts (as Python ints)
        """
        if not plaintexts:
            return []
        
        # Adaptive batch sizing
        if batch_size is None and self.adaptive_batching:
            batch_size = calculate_optimal_batch_size(len(plaintexts), self.gpu_memory_gb)
        elif batch_size is None:
            batch_size = 512  # Default fallback
        
        all_ciphertexts = []
        
        # Process in batches to manage GPU memory
        for i in range(0, len(plaintexts), batch_size):
            batch = plaintexts[i:i+batch_size]
            
            with self.stream:
                # Convert to numpy then GPU
                plaintexts_np = np.array(batch, dtype=np.int64)
                m_gpu = cp.asarray(plaintexts_np)
                
                # Generate random values on GPU
                r_gpu = cp.random.randint(1, self.n_gpu, size=len(batch), dtype=cp.int64)
                
                # Parallel modular exponentiation
                # c = (g^m * r^n) mod n^2
                g_m = self._modular_exp_gpu(self.g_gpu, m_gpu, self.nsquare_gpu)
                r_n = self._modular_exp_gpu(r_gpu, self.n_gpu, self.nsquare_gpu)
                
                # Multiply and mod
                ciphertexts_gpu = (g_m * r_n) % self.nsquare_gpu
                
                # Transfer back to CPU
                ciphertexts_np = cp.asnumpy(ciphertexts_gpu)
                all_ciphertexts.extend([int(c) for c in ciphertexts_np])
        
        return all_ciphertexts
    
    def _modular_exp_gpu(self, base, exponents, modulus):
        """Parallel modular exponentiation on GPU"""
        # For small exponents, direct computation
        if isinstance(exponents, cp.ndarray):
            max_exp = int(cp.max(exponents))
        else:
            max_exp = int(exponents) if hasattr(exponents, '__int__') else exponents
        
        if max_exp < 1000:
            return cp.power(base, exponents, dtype=cp.int64) % modulus
        
        # Binary exponentiation for large exponents
        result = cp.ones_like(exponents, dtype=cp.int64)
        base_power = cp.full_like(exponents, base, dtype=cp.int64) if isinstance(exponents, cp.ndarray) else base
        exp_copy = exponents.copy() if isinstance(exponents, cp.ndarray) else exponents
        
        max_bits = 64  # Safety limit
        for _ in range(max_bits):
            if isinstance(exp_copy, cp.ndarray):
                if cp.all(exp_copy == 0):
                    break
                mask = (exp_copy % 2) == 1
                result = cp.where(mask, (result * base_power) % modulus, result)
                base_power = (base_power * base_power) % modulus
                exp_copy = exp_copy // 2
            else:
                if exp_copy == 0:
                    break
                if exp_copy % 2 == 1:
                    result = (result * base_power) % modulus
                base_power = (base_power * base_power) % modulus
                exp_copy //= 2
        
        return result
    
    def encrypt_single(self, plaintext: int) -> int:
        """Encrypt single value (uses batch internally)"""
        return self.batch_encrypt_gpu([plaintext])[0]


class HybridPaillierEncryptor:
    """
    Hybrid encryptor: GPU for batches, CPU for singles
    OPTIMIZED: Adaptive thresholds and batch sizing
    """
    
    def __init__(self, public_key, threshold: int = None, adaptive: bool = True):
        """
        Initialize hybrid encryptor
        
        Args:
            public_key: Paillier public key
            threshold: Minimum batch size to use GPU (auto if None)
            adaptive: Enable adaptive optimization
        """
        self.pub = public_key
        self.gpu_available = GPU_AVAILABLE
        self.adaptive = adaptive
        
        # Adaptive threshold: smaller for powerful GPUs, larger for weak ones
        if threshold is None and adaptive and GPU_AVAILABLE:
            try:
                # Try to detect GPU capability
                mempool = cp.get_default_memory_pool()
                gpu_memory_gb = mempool.free_bytes() / (1024**3)
                
                if gpu_memory_gb > 6:
                    self.threshold = 5  # Strong GPU, use for small batches
                elif gpu_memory_gb > 4:
                    self.threshold = 10  # Medium GPU
                else:
                    self.threshold = 20  # Weak GPU, only for larger batches
            except:
                self.threshold = 10  # Conservative default
        else:
            self.threshold = threshold if threshold is not None else 10
        
        if self.gpu_available:
            try:
                self.gpu_encryptor = GPUPaillierEncryptor(public_key, adaptive_batching=adaptive)
            except Exception as e:
                self.gpu_available = False
    
    def encrypt_batch(self, plaintexts: List[int], force_gpu: bool = False) -> List:
        """
        Smart encryption: GPU for large batches, CPU for small
        
        Args:
            plaintexts: List of integers to encrypt
            force_gpu: Force GPU usage regardless of batch size
            
        Returns:
            List of EncryptedNumber objects
        """
        use_gpu = (len(plaintexts) >= self.threshold or force_gpu) and self.gpu_available
        
        if use_gpu:
            # Use GPU for large batches
            from agniya.core.paillier import EncryptedNumber
            ct_ints = self.gpu_encryptor.batch_encrypt_gpu(plaintexts)
            return [EncryptedNumber(self.pub, ct) for ct in ct_ints]
        else:
            # Use CPU for small batches
            from agniya.core.paillier import encrypt
            return [encrypt(self.pub, v) for v in plaintexts]
    
    def encrypt_single(self, plaintext: int):
        """Encrypt single value (always uses CPU for efficiency)"""
        from agniya.core.paillier import encrypt
        return encrypt(self.pub, plaintext)
    
    def get_stats(self) -> dict:
        """Get performance statistics"""
        return {
            "gpu_available": self.gpu_available,
            "threshold": self.threshold,
            "adaptive": self.adaptive
        }
