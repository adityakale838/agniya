"""
Hybrid AES + Paillier Encryption System

This module implements a hybrid encryption protocol combining:
- AES-256-GCM: Fast symmetric encryption for non-computational data
- Paillier: Homomorphic encryption for data requiring encrypted computation

Architecture:
1. AES Layer: Encrypts bulk data (names, emails, addresses)
2. Paillier Layer: Encrypts computational fields (salaries, ages) - supports SUM/AVG
3. Key Wrapper: Paillier-encrypts AES keys for secure key management
4. Schema System: Declarative field type annotations (plaintext/AES/Paillier)

Use Cases:
- Healthcare: Patient names (AES) + medical costs (Paillier for billing analytics)
- HR Systems: Employee names (AES) + salaries (Paillier for payroll analytics)
- Financial: Customer info (AES) + transaction amounts (Paillier for fraud detection)

Measured by scripts/benchmark_hybrid_vs_pure.py (50 records, versus Paillier on every field): inserts 2.4x
faster, queries 2.3x faster, storage 2.7x smaller. Paillier fields still support encrypted aggregation.
"""

from .aes_cipher import AESCipher
from .key_wrapper import KeyWrapper
from .schema import FieldType, Schema, Field

__all__ = [
    'AESCipher',
    'KeyWrapper', 
    'FieldType',
    'Schema',
    'Field',
]

# HybridDatabase will be imported after it's created
try:
    from .hybrid_storage import HybridDatabase
    __all__.append('HybridDatabase')
except ImportError:
    pass

__version__ = '1.0.0'
