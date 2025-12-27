"""
AGNIYA - Homomorphic Encryption Library for Python

A high-performance library for privacy-preserving computations using Paillier encryption,
RNS compression, and intelligent caching.

Usage:
    import agniya as ag
    
    # Initialize database
    db = ag.Database(key_size=2048)
    
    # Encrypt data
    encrypted = db.encrypt([100, 200, 300])
    
    # Perform queries on encrypted data
    total = db.sum(encrypted)
    average = db.average(encrypted)
    
    # Decrypt results
    result = db.decrypt(total)
"""

__version__ = "1.0.0"
__author__ = "AGNIYA Team"
__license__ = "MIT"

# Core imports
from .core.paillier import generate_keypair, encrypt, decrypt, decrypt_crt
from .core.ultimate_system import UltimateOptimizedDatabase
from .compression.rns_compression import RNSCompressor

# High-level API
class Database:
    """
    High-level interface for homomorphic encryption operations.
    
    Examples:
        >>> import agniya as ag
        >>> db = ag.Database(key_size=2048)
        >>> encrypted = db.encrypt([10, 20, 30])
        >>> total = db.sum(encrypted)
        >>> result = db.decrypt(total)
        >>> print(result)  # 60
    """
    
    def __init__(self, key_size=2048, cache_size=10000, verbose=True):
        """
        Initialize AGNIYA database with encryption keys.
        
        Args:
            key_size (int): Size of Paillier key (1024, 2048, or 4096)
            cache_size (int): Size of precomputation cache
            verbose (bool): Enable detailed logging (disable for production performance)
        """
        self._db = UltimateOptimizedDatabase(key_size=key_size, cache_size=cache_size, verbose=verbose)
        self.public_key = self._db.public_key
        self.private_key = self._db.private_key
    
    def encrypt(self, data):
        """
        Encrypt data using Paillier encryption.
        
        Args:
            data: Single value or list of values to encrypt
        
        Returns:
            Encrypted value(s)
        
        Examples:
            >>> db = ag.Database()
            >>> encrypted = db.encrypt(42)
            >>> encrypted_list = db.encrypt([1, 2, 3, 4, 5])
        """
        if isinstance(data, (list, tuple)):
            return [self._db.precomp.get_or_encrypt(val) for val in data]
        else:
            return self._db.precomp.get_or_encrypt(data)
    
    def decrypt(self, ciphertext):
        """
        Decrypt ciphertext using private key.
        
        Args:
            ciphertext: Single or list of encrypted values
        
        Returns:
            Decrypted plaintext value(s)
        
        Examples:
            >>> db = ag.Database()
            >>> encrypted = db.encrypt(42)
            >>> plaintext = db.decrypt(encrypted)
            >>> print(plaintext)  # 42
        """
        if isinstance(ciphertext, (list, tuple)):
            return [decrypt_crt(self.public_key, self.private_key, ct) for ct in ciphertext]
        else:
            return decrypt_crt(self.public_key, self.private_key, ciphertext)
    
    def sum(self, data, encrypted=False):
        """
        Compute sum over encrypted data.
        
        Args:
            data: List of values (plaintext or encrypted)
            encrypted (bool): If False, encrypts data first
        
        Returns:
            Decrypted sum
        
        Examples:
            >>> db = ag.Database()
            >>> result = db.sum([10, 20, 30, 40, 50])
            >>> print(result)  # 150
        """
        if not encrypted:
            return self._db.sum_query(data, use_cache=True)
        else:
            ct_sum = self._db.sum_encrypted(data)
            return decrypt_crt(self.public_key, self.private_key, ct_sum)
    
    def average(self, data, encrypted=False):
        """
        Compute average over encrypted data.
        
        Args:
            data: List of values (plaintext or encrypted)
            encrypted (bool): If False, encrypts data first
        
        Returns:
            Decrypted average
        
        Examples:
            >>> db = ag.Database()
            >>> result = db.average([10, 20, 30, 40, 50])
            >>> print(result)  # 30.0
        """
        if not encrypted:
            return self._db.average_query(data, use_cache=True)
        else:
            total = self.sum(data, encrypted=True)
            return total / len(data)
    
    def count(self, data, condition=None):
        """
        Count records matching condition.
        
        Args:
            data: List of values
            condition: Optional lambda function for filtering
        
        Returns:
            Count of matching records
        
        Examples:
            >>> db = ag.Database()
            >>> count = db.count([10, 20, 30, 40, 50], lambda x: x > 25)
            >>> print(count)  # 3
        """
        if condition is None:
            return len(data)
        else:
            return sum(1 for val in data if condition(val))
    
    def compress(self, ciphertext):
        """
        Compress ciphertext using RNS compression.
        
        Args:
            ciphertext: Encrypted value to compress
        
        Returns:
            Compressed ciphertext (bytes)
        
        Examples:
            >>> db = ag.Database()
            >>> encrypted = db.encrypt(12345)
            >>> compressed = db.compress(encrypted)
            >>> print(f"Saved {(1 - len(compressed)/len(str(encrypted)))*100:.1f}% space")
        """
        compressor = RNSCompressor()
        return compressor.compress(ciphertext)
    
    def decompress(self, compressed_data):
        """
        Decompress RNS-compressed ciphertext.
        
        Args:
            compressed_data: Compressed bytes
        
        Returns:
            Original ciphertext
        
        Examples:
            >>> db = ag.Database()
            >>> encrypted = db.encrypt(12345)
            >>> compressed = db.compress(encrypted)
            >>> decompressed = db.decompress(compressed)
            >>> result = db.decrypt(decompressed)
            >>> print(result)  # 12345
        """
        compressor = RNSCompressor()
        return compressor.decompress(compressed_data)
    
    def warm_cache(self, values):
        """
        Pre-encrypt common values for faster queries.
        
        Args:
            values: List of values to pre-encrypt
        
        Examples:
            >>> db = ag.Database()
            >>> db.warm_cache([1, 2, 3, 4, 5])  # Pre-encrypt common values
            >>> result = db.sum([1, 2, 3, 4, 5])  # Now very fast!
        """
        self._db.warm_cache_with_dataset(values)
    
    def stats(self):
        """
        Get database statistics.
        
        Returns:
            Dictionary with cache statistics
        
        Examples:
            >>> db = ag.Database()
            >>> db.encrypt([1, 2, 3])
            >>> print(db.stats())
            {'cache_size': 3, 'key_size': 2048, ...}
        """
        return {
            'cache_size': len(self._db.precomp.cache),
            'key_size': self._db.public_key.n.bit_length(),
            'max_cache_size': self._db.precomp.max_size
        }


# Convenience functions
def encrypt_value(public_key, value):
    """
    Encrypt a single value.
    
    Args:
        public_key: Paillier public key
        value (int): Value to encrypt
    
    Returns:
        Encrypted ciphertext
    """
    return encrypt(public_key, value)


def decrypt_value(public_key, private_key, ciphertext):
    """
    Decrypt a single ciphertext.
    
    Args:
        public_key: Paillier public key
        private_key: Paillier private key
        ciphertext: Encrypted value
    
    Returns:
        Decrypted plaintext
    """
    return decrypt_crt(public_key, private_key, ciphertext)


# Export public API
__all__ = [
    'Database',
    'generate_keypair',
    'encrypt',
    'decrypt',
    'decrypt_crt',
    'encrypt_value',
    'decrypt_value',
    'RNSCompressor',
    '__version__',
]
