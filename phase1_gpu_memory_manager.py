# phase1_gpu_memory_manager.py
"""
Phase 1: GPU Memory Manager for 8GB RTX 4070 Laptop

Core component: Smart allocation and management of limited VRAM
"""

import pycuda.driver as cuda
import pycuda.autoinit
import numpy as np
from dataclasses import dataclass
from typing import Dict, Tuple
import sys


@dataclass
class MemoryPool:
    """Represents an allocated GPU memory pool"""
    name: str
    size_bytes: int
    gpu_pointer: any
    used_bytes: int = 0
    
    def get_usage_percent(self) -> float:
        return (self.used_bytes / self.size_bytes) * 100 if self.size_bytes > 0 else 0


class GPUMemoryManager:
    """
    Smart GPU memory manager for 8GB RTX 4070 Laptop
    
    Memory Layout:
    ├─ ORAM Tree (2GB): Tree structure, persistent
    ├─ Position Map (128MB): Recursive position tracking
    ├─ Hot Cache (2GB): Recently accessed blocks
    ├─ Batch Buffers (1.5GB): Processing buffers
    ├─ Crypto Staging (1GB): AES encryption buffers
    ├─ Eviction Queue (500MB): Eviction operations
    └─ Free Margin (672MB): Safety buffer
    """
    
    # Memory allocation schema (in bytes)
    ALLOCATION_SCHEMA = {
        'oram_tree': int(2.0e9),           # 2GB
        'position_map': int(0.128e9),      # 128MB
        'hot_cache': int(2.0e9),           # 2GB
        'batch_buffers': int(1.5e9),       # 1.5GB
        'crypto_staging': int(1.0e9),      # 1GB
        'eviction_queue': int(0.5e9),      # 500MB
    }
    
    def __init__(self, safety_margin_mb=500, verbose=True):
        """
        Initialize GPU memory manager
        
        Args:
            safety_margin_mb: Safety margin to reserve (default 500MB)
            verbose: Print allocation details
        """
        self.verbose = verbose
        self.safety_margin = safety_margin_mb * 1e6
        
        # Get GPU device info
        self.device = cuda.Device(0)
        self.device_name = self.device.name().decode('utf-8')
        free_bytes, total_bytes = cuda.mem_get_info()
        
        self.total_memory = total_bytes
        self.available_memory = free_bytes - self.safety_margin
        
        if self.verbose:
            print("=" * 60)
            print("GPU MEMORY MANAGER - 8GB RTX 4070 LAPTOP")
            print("=" * 60)
            print(f"\nDevice: {self.device_name}")
            print(f"Total Memory: {total_bytes/1e9:.2f}GB")
            print(f"Free Memory: {free_bytes/1e9:.2f}GB")
            print(f"Safety Margin: {self.safety_margin/1e6:.0f}MB")
            print(f"Available for Allocation: {self.available_memory/1e9:.2f}GB")
            print("\n" + "=" * 60)
        
        # Allocate pools
        self.pools: Dict[str, MemoryPool] = {}
        self._allocate_pools()
        
        if self.verbose:
            self._print_allocation_summary()
    
    def _allocate_pools(self):
        """Allocate all memory pools"""
        if self.verbose:
            print("\nAllocating GPU Memory Pools:")
            print("-" * 60)
        
        total_requested = sum(self.ALLOCATION_SCHEMA.values()) / 1e9
        
        # Check if we have enough memory
        if total_requested > self.available_memory / 1e9:
            raise MemoryError(
                f"Requested {total_requested:.2f}GB exceeds available "
                f"{self.available_memory/1e9:.2f}GB"
            )
        
        # Allocate each pool
        for pool_name, size_bytes in self.ALLOCATION_SCHEMA.items():
            try:
                gpu_ptr = cuda.mem_alloc(size_bytes)
                self.pools[pool_name] = MemoryPool(
                    name=pool_name,
                    size_bytes=size_bytes,
                    gpu_pointer=gpu_ptr
                )
                
                if self.verbose:
                    print(f"✓ {pool_name:20s}: {size_bytes/1e9:5.3f}GB @ "
                          f"{int(gpu_ptr):20d}")
            
            except cuda.Error as e:
                print(f"✗ Failed to allocate {pool_name}: {e}")
                raise
    
    def get_pool(self, pool_name: str) -> MemoryPool:
        """Get a memory pool by name"""
        if pool_name not in self.pools:
            raise KeyError(f"Pool '{pool_name}' not found. "
                          f"Available: {list(self.pools.keys())}")
        return self.pools[pool_name]
    
    def get_pool_pointer(self, pool_name: str):
        """Get GPU pointer for a pool"""
        return self.get_pool(pool_name).gpu_pointer
    
    def get_memory_usage(self) -> Dict[str, float]:
        """Get memory usage for all pools (in MB)"""
        usage = {}
        for name, pool in self.pools.items():
            usage[f"{name}_mb"] = pool.used_bytes / 1e6
            usage[f"{name}_percent"] = pool.get_usage_percent()
        return usage
    
    def _print_allocation_summary(self):
        """Print memory allocation summary"""
        print("\n" + "=" * 60)
        print("ALLOCATION SUMMARY")
        print("=" * 60)
        
        total_allocated = sum(p.size_bytes for p in self.pools.values())
        
        print(f"\nTotal Allocated: {total_allocated/1e9:.2f}GB")
        print(f"Safety Margin: {self.safety_margin/1e6:.0f}MB")
        print(f"Total Used: {(total_allocated + self.safety_margin)/1e9:.2f}GB")
        print(f"Available Free: {(self.available_memory - total_allocated)/1e9:.2f}GB")
        print("\n" + "-" * 60)
        print("Pool Breakdown:")
        print("-" * 60)
        
        for name, pool in self.pools.items():
            pct = (pool.size_bytes / total_allocated) * 100
            print(f"{name:20s}: {pool.size_bytes/1e9:5.3f}GB ({pct:5.1f}%)")
        
        print("\n" + "=" * 60)
        print("✓ GPU Memory Manager Initialized Successfully")
        print("=" * 60)
    
    def cleanup(self):
        """Free all GPU memory"""
        if self.verbose:
            print("\nCleaning up GPU memory...")
        
        for pool_name, pool in self.pools.items():
            try:
                pool.gpu_pointer.free()
                if self.verbose:
                    print(f"✓ Freed {pool_name}")
            except Exception as e:
                print(f"✗ Error freeing {pool_name}: {e}")
        
        if self.verbose:
            print("\n✓ GPU Memory Cleanup Complete")
    
    def __enter__(self):
        """Context manager support"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup"""
        self.cleanup()


def test_gpu_memory_manager():
    """Test GPU memory manager"""
    print("\n\n")
    print("╔" + "=" * 58 + "╗")
    print("║ " + "GPU MEMORY MANAGER TEST".center(56) + " ║")
    print("╚" + "=" * 58 + "╝")
    
    try:
        # Initialize manager
        with GPUMemoryManager(verbose=True) as gpu_mem:
            
            # Test pool access
            print("\n\nTesting Pool Access:")
            print("-" * 60)
            
            oram_pool = gpu_mem.get_pool('oram_tree')
            print(f"✓ Accessed ORAM tree pool: {oram_pool.size_bytes/1e9:.2f}GB")
            
            crypto_pool = gpu_mem.get_pool('crypto_staging')
            print(f"✓ Accessed crypto staging pool: {crypto_pool.size_bytes/1e9:.2f}GB")
            
            # Test memory usage tracking
            print("\n\nMemory Usage Tracking:")
            print("-" * 60)
            usage = gpu_mem.get_memory_usage()
            for key, value in sorted(usage.items()):
                if 'percent' in key:
                    print(f"{key:25s}: {value:6.1f}%")
            
            print("\n" + "=" * 60)
            print("✓ GPU Memory Manager Test Passed")
            print("=" * 60)
    
    except Exception as e:
        print(f"\n✗ GPU Memory Manager Test Failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = test_gpu_memory_manager()
    sys.exit(0 if success else 1)
