"""
AGNIYA: additively homomorphic (Paillier) aggregation for Python.

    import agniya as ag
    db = ag.Database()                 # 2048-bit key
    cts = db.encrypt([100, 200, 300])  # randomized ciphertexts
    db.sum(cts, encrypted=True)        # 600, computed on ciphertexts
    db.sum([1, 2, 3])                  # packs, encrypts, sums, decrypts
"""

__version__ = "2.0.0"
__license__ = "MIT"

from .core.paillier import generate_keypair, encrypt, decrypt, decrypt_crt
from .core.ultimate_system import UltimateOptimizedDatabase

Database = UltimateOptimizedDatabase

__all__ = ['Database', 'UltimateOptimizedDatabase', 'generate_keypair', 'encrypt',
           'decrypt', 'decrypt_crt', '__version__']
