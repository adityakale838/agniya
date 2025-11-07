"""
GPU Utilities for AGNIYA

Provides GPU detection, CuPy initialization, and CPU fallback handling.
"""

import sys
import warnings
from typing import Tuple, Optional, Any

# Try to import CuPy (GPU-accelerated NumPy)
try:
    import cupy as cp
    CUPY_AVAILABLE = True
    GPU_AVAILABLE = True
    
    # Test if GPU is actually accessible
    try:
        _ = cp.array([1, 2, 3])
        cp.cuda.runtime.getDeviceCount()
    except Exception as e:
        GPU_AVAILABLE = False
        warnings.warn(f"CuPy installed but GPU not accessible: {e}")
except ImportError:
    CUPY_AVAILABLE = False
    GPU_AVAILABLE = False
    cp = None

# Fallback to NumPy if GPU not available
import numpy as np


class GPUContext:
    """
    Context manager for GPU operations with automatic CPU fallback.
    
    Usage:
        with GPUContext() as gpu:
            if gpu.available:
                # Use gpu.xp (CuPy)
                data = gpu.xp.array([1, 2, 3])
            else:
                # Use gpu.xp (NumPy)
                data = gpu.xp.array([1, 2, 3])
    """
    
    def __init__(self, device_id: int = 0):
        """
        Initialize GPU context.
        
        Args:
            device_id: CUDA device ID (default: 0)
        """
        self.device_id = device_id
        self.available = GPU_AVAILABLE
        self.xp = cp if GPU_AVAILABLE else np  # Array library (CuPy or NumPy)
        self._device_context = None
    
    def __enter__(self):
        """Enter GPU context."""
        if self.available and cp is not None:
            try:
                self._device_context = cp.cuda.Device(self.device_id)
                self._device_context.__enter__()
            except Exception as e:
                warnings.warn(f"Failed to enter GPU context: {e}, using CPU")
                self.available = False
                self.xp = np
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit GPU context."""
        if self._device_context is not None:
            self._device_context.__exit__(exc_type, exc_val, exc_tb)
    
    def to_cpu(self, array):
        """
        Move array from GPU to CPU.
        
        Args:
            array: CuPy or NumPy array
            
        Returns:
            NumPy array
        """
        if self.available and hasattr(array, 'get'):
            return array.get()  # CuPy → NumPy
        return np.asarray(array)  # Already NumPy
    
    def to_gpu(self, array):
        """
        Move array from CPU to GPU.
        
        Args:
            array: NumPy or CuPy array
            
        Returns:
            CuPy array (if GPU available) or NumPy array (fallback)
        """
        if self.available and cp is not None:
            return cp.asarray(array)  # NumPy → CuPy
        return np.asarray(array)  # Stay on CPU


def get_gpu_info() -> dict:
    """
    Get information about available GPUs.
    
    Returns:
        Dictionary with GPU information:
        - available: bool
        - device_count: int
        - devices: list of device info dicts
    """
    info = {
        'available': GPU_AVAILABLE,
        'cupy_installed': CUPY_AVAILABLE,
        'device_count': 0,
        'devices': []
    }
    
    if not GPU_AVAILABLE:
        return info
    
    try:
        info['device_count'] = cp.cuda.runtime.getDeviceCount()
        
        for i in range(info['device_count']):
            with cp.cuda.Device(i):
                props = cp.cuda.runtime.getDeviceProperties(i)
                device_info = {
                    'id': i,
                    'name': props['name'].decode('utf-8'),
                    'compute_capability': f"{props['major']}.{props['minor']}",
                    'total_memory_gb': props['totalGlobalMem'] / (1024**3),
                    'multiprocessor_count': props['multiProcessorCount'],
                }
                info['devices'].append(device_info)
    except Exception as e:
        warnings.warn(f"Failed to get GPU info: {e}")
    
    return info


def print_gpu_info():
    """Print GPU information in human-readable format."""
    info = get_gpu_info()
    
    print("\n" + "="*60)
    print("GPU INFORMATION")
    print("="*60)
    
    if not info['cupy_installed']:
        print("❌ CuPy not installed")
        print("   Install with: pip install cupy-cuda11x")
        print("   (or cupy-cuda12x for CUDA 12.x)")
    elif not info['available']:
        print("⚠️  CuPy installed but GPU not accessible")
        print("   Check NVIDIA drivers and CUDA installation")
    else:
        print(f"✅ GPU acceleration available")
        print(f"   Devices found: {info['device_count']}")
        
        for device in info['devices']:
            print(f"\n📊 Device {device['id']}: {device['name']}")
            print(f"   Compute Capability: {device['compute_capability']}")
            print(f"   Memory: {device['total_memory_gb']:.2f} GB")
            print(f"   Multiprocessors: {device['multiprocessor_count']}")
    
    print("="*60 + "\n")


def modular_pow_gpu(base, exponent, modulus, xp=None):
    """
    GPU-accelerated modular exponentiation: base^exponent mod modulus
    
    Uses square-and-multiply algorithm parallelized across array elements.
    
    Args:
        base: Base values (array or scalar)
        exponent: Exponent values (array or scalar)
        modulus: Modulus value (scalar)
        xp: Array library (cupy or numpy)
    
    Returns:
        Result array: base^exponent mod modulus
    """
    if xp is None:
        xp = cp if GPU_AVAILABLE else np
    
    # Convert to arrays
    base = xp.asarray(base)
    exponent = xp.asarray(exponent)
    
    # Handle scalar exponent
    if exponent.ndim == 0:
        exponent = xp.full(base.shape, exponent)
    
    # Result array
    result = xp.ones_like(base, dtype=xp.int64)
    
    # Square-and-multiply (not optimal for large exponents, but simple)
    # For production, use more sophisticated algorithms
    base_power = base % modulus
    exp_bits = exponent.copy()
    
    max_bits = int(xp.log2(xp.max(exp_bits)).get() if GPU_AVAILABLE else np.log2(np.max(exp_bits))) + 1
    
    for _ in range(max_bits):
        # If bit is set, multiply
        mask = (exp_bits & 1) == 1
        result = xp.where(mask, (result * base_power) % modulus, result)
        
        # Square the base
        base_power = (base_power * base_power) % modulus
        
        # Shift exponent right
        exp_bits >>= 1
    
    return result


def benchmark_gpu_vs_cpu(size: int = 1000, num_iterations: int = 10) -> dict:
    """
    Benchmark GPU vs CPU performance for array operations.
    
    Args:
        size: Array size to test
        num_iterations: Number of iterations
    
    Returns:
        Dictionary with benchmark results
    """
    import time
    
    results = {
        'size': size,
        'iterations': num_iterations,
        'gpu_available': GPU_AVAILABLE,
    }
    
    # Generate random data
    data_cpu = np.random.randint(1, 1000, size=size)
    
    # CPU benchmark
    start = time.time()
    for _ in range(num_iterations):
        result_cpu = np.power(data_cpu, 3) % 1000
    cpu_time = time.time() - start
    results['cpu_time_sec'] = cpu_time
    
    # GPU benchmark
    if GPU_AVAILABLE:
        data_gpu = cp.asarray(data_cpu)
        
        # Warmup
        _ = cp.power(data_gpu, 3) % 1000
        cp.cuda.Stream.null.synchronize()
        
        start = time.time()
        for _ in range(num_iterations):
            result_gpu = cp.power(data_gpu, 3) % 1000
            cp.cuda.Stream.null.synchronize()  # Wait for GPU to finish
        gpu_time = time.time() - start
        
        results['gpu_time_sec'] = gpu_time
        results['speedup'] = cpu_time / gpu_time
    else:
        results['gpu_time_sec'] = None
        results['speedup'] = None
    
    return results


if __name__ == "__main__":
    # Test GPU availability
    print_gpu_info()
    
    # Run benchmark
    if GPU_AVAILABLE:
        print("Running benchmark (GPU vs CPU)...")
        results = benchmark_gpu_vs_cpu(size=10000, num_iterations=100)
        print(f"\nBenchmark Results:")
        print(f"  Array size: {results['size']:,}")
        print(f"  Iterations: {results['iterations']}")
        print(f"  CPU time: {results['cpu_time_sec']:.3f}s")
        print(f"  GPU time: {results['gpu_time_sec']:.3f}s")
        print(f"  Speedup: {results['speedup']:.2f}x")
    else:
        print("\n⚠️  GPU not available - install CUDA and CuPy for acceleration")
