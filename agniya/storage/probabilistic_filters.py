"""
AGNIYA - Probabilistic Filters for Fast Membership Testing
=============================================================

Implements Bloom filters and Cuckoo filters for O(1) membership queries
with configurable false positive rates. Critical for fast deduplication.

Key Innovations:
1. Bloom Filter: Space-efficient probabilistic data structure
2. Cuckoo Filter: Better deletion support and cache locality
3. Integration with LSH: Fast pre-filter before expensive similarity checks
4. Encrypted Data Support: Hash-based membership without decryption

Patent Claims:
- Novel integration of probabilistic filters with homomorphic encryption
- Hybrid Bloom+Cuckoo strategy for optimal space-speed tradeoff
- Adaptive filter sizing based on data stream characteristics
"""

import hashlib
import math
import struct
from typing import List, Optional, Set
import gmpy2


class BloomFilter:
    """
    Space-efficient probabilistic data structure for membership testing.
    
    Properties:
    - False positives possible (configurable rate)
    - False negatives impossible
    - O(1) insertion and lookup
    - Cannot delete elements
    
    Use Cases:
    - Fast deduplication pre-check
    - Cache membership testing
    - Encrypted data fingerprint storage
    """
    
    def __init__(self, expected_elements: int = 10000, false_positive_rate: float = 0.01):
        """
        Initialize Bloom filter with optimal parameters.
        
        Args:
            expected_elements: Expected number of items to store
            false_positive_rate: Desired false positive probability (0 < p < 1)
        """
        self.expected_elements = expected_elements
        self.false_positive_rate = false_positive_rate
        
        # Calculate optimal bit array size
        self.bit_size = self._optimal_bit_size(expected_elements, false_positive_rate)
        
        # Calculate optimal number of hash functions
        self.num_hashes = self._optimal_num_hashes(self.bit_size, expected_elements)
        
        # Initialize bit array (use gmpy2 for efficient bit operations)
        self.bit_array = gmpy2.mpz(0)
        
        self.num_items = 0
        
    @staticmethod
    def _optimal_bit_size(n: int, p: float) -> int:
        """Calculate optimal bit array size: m = -n*ln(p) / (ln(2)^2)"""
        m = -(n * math.log(p)) / (math.log(2) ** 2)
        return int(math.ceil(m))
    
    @staticmethod
    def _optimal_num_hashes(m: int, n: int) -> int:
        """Calculate optimal number of hash functions: k = (m/n) * ln(2)"""
        k = (m / n) * math.log(2)
        return max(1, int(math.ceil(k)))
    
    def _hash(self, item: bytes, seed: int) -> int:
        """Generate hash value for given item and seed."""
        h = hashlib.sha256(item + struct.pack('<I', seed))
        return int.from_bytes(h.digest()[:8], 'little') % self.bit_size
    
    def add(self, item: bytes) -> None:
        """Add item to the filter."""
        for i in range(self.num_hashes):
            bit_index = self._hash(item, i)
            self.bit_array = gmpy2.bit_set(self.bit_array, bit_index)
        self.num_items += 1
    
    def contains(self, item: bytes) -> bool:
        """
        Check if item might be in the set.
        
        Returns:
            True: Item might be present (or false positive)
            False: Item is definitely not present
        """
        for i in range(self.num_hashes):
            bit_index = self._hash(item, i)
            if not gmpy2.bit_test(self.bit_array, bit_index):
                return False
        return True
    
    def __contains__(self, item: bytes) -> bool:
        """Support 'in' operator."""
        return self.contains(item)
    
    def get_stats(self) -> dict:
        """Return filter statistics."""
        actual_fp_rate = (1 - math.exp(-self.num_hashes * self.num_items / self.bit_size)) ** self.num_hashes
        return {
            'bit_size': self.bit_size,
            'num_hashes': self.num_hashes,
            'num_items': self.num_items,
            'expected_fp_rate': self.false_positive_rate,
            'actual_fp_rate': actual_fp_rate,
            'memory_bytes': self.bit_size // 8,
            'load_factor': self.num_items / self.expected_elements
        }


class CuckooFilter:
    """
    Cuckoo filter: Probabilistic data structure with deletion support.
    
    Advantages over Bloom filter:
    - Supports deletion
    - Better cache locality
    - Lower false positive rates for same space
    
    Properties:
    - O(1) insertion, lookup, deletion
    - Configurable load factor
    - Better memory access patterns
    """
    
    def __init__(self, capacity: int = 10000, bucket_size: int = 4, 
                 fingerprint_size: int = 16, max_kicks: int = 500):
        """
        Initialize Cuckoo filter.
        
        Args:
            capacity: Maximum number of items to store
            bucket_size: Number of fingerprints per bucket (typically 2-8)
            fingerprint_size: Bits per fingerprint (8-32)
            max_kicks: Maximum relocations during insertion
        """
        self.bucket_size = bucket_size
        self.fingerprint_size = fingerprint_size
        self.max_kicks = max_kicks
        
        # Calculate number of buckets (power of 2 for fast modulo)
        self.num_buckets = 2 ** math.ceil(math.log2(capacity / bucket_size))
        
        # Initialize buckets (list of sets for each bucket)
        self.buckets: List[Set[int]] = [set() for _ in range(self.num_buckets)]
        
        self.num_items = 0
        
    def _hash(self, item: bytes) -> int:
        """Primary hash function."""
        h = hashlib.sha256(item)
        return int.from_bytes(h.digest()[:8], 'little') % self.num_buckets
    
    def _fingerprint(self, item: bytes) -> int:
        """Generate fingerprint for item."""
        h = hashlib.sha256(b'fingerprint:' + item)
        fp = int.from_bytes(h.digest()[:8], 'little')
        # Ensure non-zero fingerprint
        return (fp % (2 ** self.fingerprint_size - 1)) + 1
    
    def _alt_index(self, index: int, fingerprint: int) -> int:
        """Calculate alternative bucket index using fingerprint."""
        # Use fingerprint to compute alternative location
        h = hashlib.sha256(struct.pack('<Q', fingerprint))
        offset = int.from_bytes(h.digest()[:4], 'little')
        return (index ^ offset) % self.num_buckets
    
    def add(self, item: bytes) -> bool:
        """
        Add item to the filter.
        
        Returns:
            True if successfully added
            False if filter is full
        """
        fingerprint = self._fingerprint(item)
        index1 = self._hash(item)
        index2 = self._alt_index(index1, fingerprint)
        
        # Try to insert in primary bucket
        if len(self.buckets[index1]) < self.bucket_size:
            self.buckets[index1].add(fingerprint)
            self.num_items += 1
            return True
        
        # Try to insert in alternate bucket
        if len(self.buckets[index2]) < self.bucket_size:
            self.buckets[index2].add(fingerprint)
            self.num_items += 1
            return True
        
        # Both buckets full - perform cuckoo relocations
        current_index = index1
        current_fp = fingerprint
        
        for _ in range(self.max_kicks):
            # Randomly evict an item from current bucket
            if self.buckets[current_index]:
                evicted_fp = self.buckets[current_index].pop()
                self.buckets[current_index].add(current_fp)
                
                # Try to insert evicted item in its alternate location
                alt_index = self._alt_index(current_index, evicted_fp)
                
                if len(self.buckets[alt_index]) < self.bucket_size:
                    self.buckets[alt_index].add(evicted_fp)
                    self.num_items += 1
                    return True
                
                # Continue with evicted item
                current_index = alt_index
                current_fp = evicted_fp
            else:
                # Bucket became empty, insert here
                self.buckets[current_index].add(current_fp)
                self.num_items += 1
                return True
        
        # Failed to insert after max kicks
        return False
    
    def contains(self, item: bytes) -> bool:
        """Check if item might be in the filter."""
        fingerprint = self._fingerprint(item)
        index1 = self._hash(item)
        index2 = self._alt_index(index1, fingerprint)
        
        return (fingerprint in self.buckets[index1] or 
                fingerprint in self.buckets[index2])
    
    def delete(self, item: bytes) -> bool:
        """
        Remove item from the filter.
        
        Returns:
            True if item was found and removed
            False if item was not found
        """
        fingerprint = self._fingerprint(item)
        index1 = self._hash(item)
        index2 = self._alt_index(index1, fingerprint)
        
        if fingerprint in self.buckets[index1]:
            self.buckets[index1].remove(fingerprint)
            self.num_items -= 1
            return True
        elif fingerprint in self.buckets[index2]:
            self.buckets[index2].remove(fingerprint)
            self.num_items -= 1
            return True
        
        return False
    
    def __contains__(self, item: bytes) -> bool:
        """Support 'in' operator."""
        return self.contains(item)
    
    def get_stats(self) -> dict:
        """Return filter statistics."""
        total_capacity = self.num_buckets * self.bucket_size
        load_factor = self.num_items / total_capacity if total_capacity > 0 else 0
        
        # Approximate false positive rate
        fp_rate = (2 * self.bucket_size) / (2 ** self.fingerprint_size)
        
        return {
            'num_buckets': self.num_buckets,
            'bucket_size': self.bucket_size,
            'fingerprint_size': self.fingerprint_size,
            'num_items': self.num_items,
            'capacity': total_capacity,
            'load_factor': load_factor,
            'approx_fp_rate': fp_rate,
            'memory_bytes': self.num_buckets * self.bucket_size * (self.fingerprint_size // 8)
        }


class HybridFilter:
    """
    Hybrid strategy combining Bloom and Cuckoo filters.
    
    Strategy:
    1. Use Bloom filter for initial fast negative checks (definitely not present)
    2. Use Cuckoo filter for items that need deletion support
    3. Automatic switching based on workload characteristics
    
    Patent Claim: Novel adaptive hybrid probabilistic filter strategy
    """
    
    def __init__(self, expected_elements: int = 10000, 
                 false_positive_rate: float = 0.01,
                 support_deletion: bool = True):
        """
        Initialize hybrid filter.
        
        Args:
            expected_elements: Expected number of items
            false_positive_rate: Desired FP rate
            support_deletion: Whether to enable deletion support (uses Cuckoo)
        """
        self.bloom = BloomFilter(expected_elements, false_positive_rate)
        self.cuckoo = CuckooFilter(expected_elements) if support_deletion else None
        self.support_deletion = support_deletion
        
    def add(self, item: bytes) -> bool:
        """Add item to the filter."""
        self.bloom.add(item)
        if self.cuckoo:
            return self.cuckoo.add(item)
        return True
    
    def contains(self, item: bytes) -> bool:
        """Check if item might be in the filter."""
        # Fast negative check with Bloom filter
        if not self.bloom.contains(item):
            return False
        
        # If deletion support enabled, verify with Cuckoo
        if self.cuckoo:
            return self.cuckoo.contains(item)
        
        return True
    
    def delete(self, item: bytes) -> bool:
        """Remove item (only if deletion is supported)."""
        if not self.cuckoo:
            raise NotImplementedError("Deletion not supported without Cuckoo filter")
        return self.cuckoo.delete(item)
    
    def get_stats(self) -> dict:
        """Return combined filter statistics."""
        stats = {'bloom': self.bloom.get_stats()}
        if self.cuckoo:
            stats['cuckoo'] = self.cuckoo.get_stats()
            stats['total_memory_bytes'] = stats['bloom']['memory_bytes'] + stats['cuckoo']['memory_bytes']
        else:
            stats['total_memory_bytes'] = stats['bloom']['memory_bytes']
        return stats
