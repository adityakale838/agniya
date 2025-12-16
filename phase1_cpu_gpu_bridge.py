# phase1_cpu_gpu_bridge.py
"""
Phase 1: CPU-GPU Communication Bridge

Manages async data transfers between CPU and GPU with:
- Non-blocking transfers
- Prefetching strategy
- Transfer optimization
- Bandwidth monitoring
"""

import pycuda.driver as cuda
import numpy as np
from typing import Optional, Tuple
from collections import deque
import time


class CPUGPUBridge:
    """
    Optimized CPU-GPU data transfer bridge
    
    Features:
    - Asynchronous (non-blocking) transfers
    - Multiple transfer streams
    - Bandwidth monitoring
    - Prefetch pipeline
    """
    
    def __init__(self, gpu_mem_manager, num_streams=2, verbose=True):
        """
        Initialize CPU-GPU bridge
        
        Args:
            gpu_mem_manager: GPUMemoryManager instance
            num_streams: Number of concurrent transfer streams
            verbose: Print status information
        """
        self.gpu_mem = gpu_mem_manager
        self.verbose = verbose
        self.num_streams = num_streams
        
        # Create async streams
        self.streams = [cuda.Stream() for _ in range(num_streams)]
        self.current_stream_idx = 0
        
        # Statistics
        self.stats = {
            'bytes_h2d': 0,  # Host to Device
            'bytes_d2h': 0,  # Device to Host
            'transfers_h2d': 0,
            'transfers_d2h': 0,
            'total_time_ms': 0,
        }
        
        # Prefetch queue
        self.prefetch_queue = deque(maxlen=10)
        self.prefetch_cache = {}
        
        if self.verbose:
            print("\n" + "=" * 60)
            print("CPU-GPU BRIDGE INITIALIZED")
            print("=" * 60)
            print(f"Streams: {num_streams}")
            print(f"Max prefetch queue size: 10")
            print("=" * 60)
    
    def get_next_stream(self) -> cuda.Stream:
        """Get next available transfer stream (round-robin)"""
        stream = self.streams[self.current_stream_idx]
        self.current_stream_idx = (self.current_stream_idx + 1) % self.num_streams
        return stream
    
    def host_to_device_async(self, 
                            host_data: np.ndarray, 
                            pool_name: str,
                            offset: int = 0) -> Tuple[cuda.Stream, int]:
        """
        Asynchronous Host-to-Device transfer
        
        Args:
            host_data: NumPy array on CPU
            pool_name: GPU memory pool name
            offset: Offset within pool
        
        Returns:
            (stream, bytes_transferred)
        """
        pool = self.gpu_mem.get_pool(pool_name)
        stream = self.get_next_stream()
        
        # Check bounds
        if offset + host_data.nbytes > pool.size_bytes:
            raise MemoryError(
                f"Transfer would exceed pool bounds: "
                f"{offset + host_data.nbytes} > {pool.size_bytes}"
            )
        
        # Calculate actual GPU pointer with offset
        gpu_ptr = int(pool.gpu_pointer) + offset
        gpu_ptr_obj = cuda.DevicePointer(gpu_ptr)
        
        # Async transfer
        cuda.memcpy_htod_async(gpu_ptr_obj, host_data, stream)
        
        # Update stats
        self.stats['bytes_h2d'] += host_data.nbytes
        self.stats['transfers_h2d'] += 1
        
        if self.verbose:
            print(f"✓ H2D: {host_data.nbytes/1e6:.1f}MB → {pool_name} "
                  f"(stream {self.current_stream_idx - 1})")
        
        return stream, host_data.nbytes
    
    def device_to_host_async(self,
                            gpu_pointer: cuda.DeviceAllocation,
                            shape: Tuple,
                            dtype: np.dtype) -> Tuple[np.ndarray, cuda.Stream]:
        """
        Asynchronous Device-to-Host transfer
        
        Args:
            gpu_pointer: GPU memory pointer
            shape: Shape of output array
            dtype: Data type of output
        
        Returns:
            (host_array, stream)
        """
        stream = self.get_next_stream()
        host_data = np.empty(shape, dtype=dtype)
        
        # Async transfer
        cuda.memcpy_dtoh_async(host_data, gpu_pointer, stream)
        
        # Update stats
        self.stats['bytes_d2h'] += host_data.nbytes
        self.stats['transfers_d2h'] += 1
        
        if self.verbose:
            print(f"✓ D2H: {host_data.nbytes/1e6:.1f}MB ← GPU "
                  f"(stream {self.current_stream_idx - 1})")
        
        return host_data, stream
    
    def synchronize_all(self):
        """Wait for all pending transfers to complete"""
        for stream in self.streams:
            stream.synchronize()
    
    def synchronize_stream(self, stream: cuda.Stream):
        """Wait for specific stream to complete"""
        stream.synchronize()
    
    def prefetch(self, block_ids: list, prefetch_pool: str = 'batch_buffers'):
        """
        Prefetch blocks from CPU to GPU in background
        
        Args:
            block_ids: List of block IDs to prefetch
            prefetch_pool: GPU pool to prefetch into
        """
        for block_id in block_ids:
            if block_id not in self.prefetch_cache:
                # Simulate loading block from storage
                block_data = self._load_block_from_storage(block_id)
                
                # Transfer to GPU
                self.host_to_device_async(block_data, prefetch_pool)
                self.prefetch_cache[block_id] = True
    
    def _load_block_from_storage(self, block_id: int, block_size: int = 8192) -> np.ndarray:
        """Load block from storage (placeholder)"""
        # In real implementation, would load from disk or database
        return np.random.bytes(block_size)
    
    def get_bandwidth(self) -> Dict[str, float]:
        """Calculate average bandwidth statistics"""
        if self.stats['total_time_ms'] == 0:
            return {'h2d_gb_s': 0, 'd2h_gb_s': 0}
        
        time_s = self.stats['total_time_ms'] / 1000
        
        return {
            'h2d_gb_s': (self.stats['bytes_h2d'] / 1e9) / time_s,
            'd2h_gb_s': (self.stats['bytes_d2h'] / 1e9) / time_s,
            'total_transfers': self.stats['transfers_h2d'] + self.stats['transfers_d2h'],
        }
    
    def print_statistics(self):
        """Print transfer statistics"""
        print("\n" + "=" * 60)
        print("CPU-GPU BRIDGE STATISTICS")
        print("=" * 60)
        print(f"Host→Device: {self.stats['bytes_h2d']/1e9:.2f}GB in "
              f"{self.stats['transfers_h2d']} transfers")
        print(f"Device→Host: {self.stats['bytes_d2h']/1e9:.2f}GB in "
              f"{self.stats['transfers_d2h']} transfers")
        print(f"Total: {(self.stats['bytes_h2d'] + self.stats['bytes_d2h'])/1e9:.2f}GB")
        print("=" * 60)


def test_cpu_gpu_bridge(gpu_mem):
    """Test CPU-GPU bridge functionality"""
    
    print("\n\n")
    print("╔" + "=" * 58 + "╗")
    print("║ " + "CPU-GPU BRIDGE TEST".center(56) + " ║")
    print("╚" + "=" * 58 + "╝")
    
    bridge = CPUGPUBridge(gpu_mem, num_streams=2, verbose=True)
    
    # Test 1: Single transfer
    print("\n\nTest 1: Single H2D Transfer")
    print("-" * 60)
    data = np.random.randint(0, 256, (1024, 1024), dtype=np.uint32)
    stream, bytes_xfr = bridge.host_to_device_async(data, 'batch_buffers')
    bridge.synchronize_stream(stream)
    print(f"✓ Transferred {bytes_xfr/1e6:.1f}MB successfully")
    
    # Test 2: Multiple concurrent transfers
    print("\n\nTest 2: Multiple Concurrent Transfers")
    print("-" * 60)
    streams = []
    for i in range(3):
        data = np.random.randint(0, 256, (512, 512), dtype=np.uint32)
        stream, _ = bridge.host_to_device_async(data, 'batch_buffers', offset=i*1e6)
        streams.append(stream)
    
    for stream in streams:
        bridge.synchronize_stream(stream)
    print("✓ All 3 concurrent transfers completed")
    
    # Test 3: D2H transfer
    print("\n\nTest 3: Device-to-Host Transfer")
    print("-" * 60)
    pool = gpu_mem.get_pool('batch_buffers')
    output_data, stream = bridge.device_to_host_async(
        pool.gpu_pointer,
        (256, 256),
        np.uint32
    )
    bridge.synchronize_stream(stream)
    print(f"✓ Retrieved {output_data.nbytes/1e6:.1f}MB from GPU")
    
    # Print statistics
    bridge.print_statistics()
    
    print("\n" + "=" * 60)
    print("✓ CPU-GPU Bridge Test Passed")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    from phase1_gpu_memory_manager import GPUMemoryManager
    
    try:
        with GPUMemoryManager(verbose=False) as gpu_mem:
            test_cpu_gpu_bridge(gpu_mem)
        print("\n✓ All tests passed!")
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
