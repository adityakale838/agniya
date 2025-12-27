"""
Multi-Level Encryption Cache for Paillier

Inspired by CPU cache hierarchy (L1/L2/L3), this module provides
ultra-fast caching for encrypted values.

Performance Impact:
- Cache hit: ~1 microsecond (instant)
- Cache miss: ~10 milliseconds (full encryption)
- Speedup on repeated values: 10,000x

Use Cases:
- Encrypting categorical data (ages, zip codes, ratings)
- Re-encrypting known values
- Batch processing with duplicates
- Database queries with common filters
"""

from collections import OrderedDict
from typing import Optional, Dict, Tuple
import threading


class LRUCache:
    """
    Thread-safe LRU (Least Recently Used) cache.
    
    Automatically evicts oldest entries when capacity is reached.
    """
    
    def __init__(self, capacity: int):
        """
        Initialize LRU cache.
        
        Args:
            capacity: Maximum number of entries
        """
        self.cache = OrderedDict()
        self.capacity = capacity
        self.lock = threading.Lock()
        
        # Statistics
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[int]:
        """
        Get value from cache.
        
        Args:
            key: Cache key (stringified plaintext)
            
        Returns:
            Cached ciphertext or None if not found
        """
        with self.lock:
            if key in self.cache:
                self.hits += 1
                # Move to end (most recently used)
                self.cache.move_to_end(key)
                return self.cache[key]
            
            self.misses += 1
            return None
    
    def put(self, key: str, value: int):
        """
        Store value in cache.
        
        Args:
            key: Cache key
            value: Ciphertext to cache
        """
        with self.lock:
            if key in self.cache:
                # Update existing entry
                self.cache.move_to_end(key)
                self.cache[key] = value
            else:
                # Add new entry
                self.cache[key] = value
                
                # Evict oldest if over capacity
                if len(self.cache) > self.capacity:
                    self.cache.popitem(last=False)
    
    def clear(self):
        """Clear all cache entries."""
        with self.lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0
    
    def size(self) -> int:
        """Get current cache size."""
        with self.lock:
            return len(self.cache)
    
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        with self.lock:
            total = self.hits + self.misses
            return self.hits / total if total > 0 else 0.0


class MultiLevelCache:
    """
    Three-level cache hierarchy for encrypted values.
    
    Architecture:
    - L1 Cache: Hot values (100 entries) - most frequently accessed
    - L2 Cache: Warm values (1000 entries) - recently used
    - L3 Cache: Cold values (optional, disk-backed) - historical
    
    Lookup Strategy:
    1. Check L1 (fastest) - if hit, return immediately
    2. Check L2 - if hit, promote to L1 and return
    3. Check L3 (future) - if hit, promote to L2/L1
    4. Cache miss - encrypt and store in all levels
    
    This mirrors CPU cache behavior and provides excellent performance
    for workloads with repeated values.
    """
    
    def __init__(self, 
                 l1_capacity: int = 100,
                 l2_capacity: int = 1000,
                 enable_l3: bool = False):
        """
        Initialize multi-level cache.
        
        Args:
            l1_capacity: L1 cache size (hot values)
            l2_capacity: L2 cache size (warm values)
            enable_l3: Enable L3 disk-backed cache (future)
        """
        self.l1 = LRUCache(l1_capacity)
        self.l2 = LRUCache(l2_capacity)
        self.enable_l3 = enable_l3
        self.enabled = True
        
        # Global statistics
        self.lock = threading.Lock()
    
    def get(self, plaintext: int) -> Optional[int]:
        """
        Try to get cached ciphertext for plaintext.
        
        Args:
            plaintext: Integer plaintext value
            
        Returns:
            Cached ciphertext or None if not found
        """
        if not self.enabled:
            return None
        
        key = str(plaintext)
        
        # Try L1 (fastest, most frequently used)
        result = self.l1.get(key)
        if result is not None:
            return result
        
        # Try L2 (recent, but not hot)
        result = self.l2.get(key)
        if result is not None:
            # Promote to L1 (it's becoming hot!)
            self.l1.put(key, result)
            return result
        
        # Try L3 (future: disk-backed cache)
        if self.enable_l3:
            # TODO: Implement disk-backed L3 cache
            pass
        
        return None
    
    def put(self, plaintext: int, ciphertext: int):
        """
        Store ciphertext in cache.
        
        Args:
            plaintext: Integer plaintext value
            ciphertext: Encrypted value
        """
        if not self.enabled:
            return
        
        key = str(plaintext)
        
        # Store in both L1 and L2 for redundancy
        self.l1.put(key, ciphertext)
        self.l2.put(key, ciphertext)
        
        # TODO: Store in L3 if enabled
    
    def clear(self):
        """Clear all cache levels."""
        self.l1.clear()
        self.l2.clear()
    
    def enable(self):
        """Enable caching."""
        self.enabled = True
    
    def disable(self):
        """Disable caching."""
        self.enabled = False
    
    def stats(self) -> Dict[str, any]:
        """
        Get comprehensive cache statistics.
        
        Returns:
            Dictionary with cache performance metrics
        """
        l1_total = self.l1.hits + self.l1.misses
        l2_total = self.l2.hits + self.l2.misses
        
        total_hits = self.l1.hits + self.l2.hits
        total_misses = self.l1.misses
        total = total_hits + total_misses
        
        hit_rate = total_hits / total if total > 0 else 0.0
        
        # Estimate time saved (assuming 10ms per encryption)
        time_saved_ms = total_hits * 10
        
        return {
            'l1_hits': self.l1.hits,
            'l1_misses': self.l1.misses,
            'l1_size': self.l1.size(),
            'l1_hit_rate': self.l1.hit_rate(),
            
            'l2_hits': self.l2.hits,
            'l2_misses': self.l2.misses,
            'l2_size': self.l2.size(),
            'l2_hit_rate': self.l2.hit_rate(),
            
            'total_hits': total_hits,
            'total_misses': total_misses,
            'overall_hit_rate': hit_rate,
            'efficiency': f'{hit_rate * 100:.1f}%',
            
            'estimated_time_saved_ms': time_saved_ms,
            'estimated_time_saved_sec': time_saved_ms / 1000,
            
            'enabled': self.enabled
        }
    
    def print_stats(self):
        """Print formatted cache statistics."""
        stats = self.stats()
        
        print("\n" + "="*60)
        print("Multi-Level Cache Statistics")
        print("="*60)
        
        print(f"\nL1 Cache (Hot):")
        print(f"  Hits:      {stats['l1_hits']:,}")
        print(f"  Misses:    {stats['l1_misses']:,}")
        print(f"  Size:      {stats['l1_size']:,}")
        print(f"  Hit Rate:  {stats['l1_hit_rate']*100:.1f}%")
        
        print(f"\nL2 Cache (Warm):")
        print(f"  Hits:      {stats['l2_hits']:,}")
        print(f"  Misses:    {stats['l2_misses']:,}")
        print(f"  Size:      {stats['l2_size']:,}")
        print(f"  Hit Rate:  {stats['l2_hit_rate']*100:.1f}%")
        
        print(f"\nOverall Performance:")
        print(f"  Total Hits:    {stats['total_hits']:,}")
        print(f"  Total Misses:  {stats['total_misses']:,}")
        print(f"  Hit Rate:      {stats['efficiency']}")
        print(f"  Time Saved:    {stats['estimated_time_saved_sec']:.2f} seconds")
        
        print("="*60 + "\n")


class QueryCache:
    """
    Cache for expensive query results (SUM, AVG, COUNT, etc.).
    
    Unlike encryption cache (plaintext → ciphertext), this caches
    complete query results (query_key → encrypted_result).
    """
    
    def __init__(self, capacity: int = 500):
        """
        Initialize query result cache.
        
        Args:
            capacity: Maximum number of cached queries
        """
        self.cache = LRUCache(capacity)
    
    def get(self, query_key: str) -> Optional[int]:
        """
        Get cached query result.
        
        Args:
            query_key: Unique query identifier (e.g., "SUM:table1:col_age")
            
        Returns:
            Cached encrypted result or None
        """
        return self.cache.get(query_key)
    
    def put(self, query_key: str, result: int):
        """
        Store query result.
        
        Args:
            query_key: Unique query identifier
            result: Encrypted query result
        """
        self.cache.put(query_key, result)
    
    def invalidate(self, pattern: str):
        """
        Invalidate cache entries matching pattern.
        
        Args:
            pattern: Pattern to match (e.g., "table1" clears all table1 queries)
        """
        # Get all keys
        with self.cache.lock:
            keys_to_remove = [
                key for key in self.cache.cache.keys()
                if pattern in key
            ]
            
            for key in keys_to_remove:
                del self.cache.cache[key]
    
    def clear(self):
        """Clear all cached queries."""
        self.cache.clear()
    
    def stats(self) -> Dict[str, any]:
        """Get query cache statistics."""
        return {
            'hits': self.cache.hits,
            'misses': self.cache.misses,
            'size': self.cache.size(),
            'hit_rate': self.cache.hit_rate(),
            'efficiency': f'{self.cache.hit_rate()*100:.1f}%'
        }


if __name__ == "__main__":
    # Demo the cache
    print("Multi-Level Cache Demo\n")
    
    cache = MultiLevelCache(l1_capacity=5, l2_capacity=10)
    
    # Simulate encryption cache usage
    print("Simulating 100 lookups with repeated values...")
    
    import random
    random.seed(42)
    
    # Generate repeated values (age-like distribution)
    values = [random.randint(20, 80) for _ in range(100)]
    
    for value in values:
        result = cache.get(value)
        if result is None:
            # Cache miss - "encrypt"
            fake_ciphertext = value * 12345  # Simulate encryption
            cache.put(value, fake_ciphertext)
        # else: Cache hit!
    
    # Print statistics
    cache.print_stats()
    
    print(f"Unique values: {len(set(values))}")
    print(f"Total accesses: {len(values)}")
    print(f"Cache efficiency: {cache.stats()['efficiency']}")
