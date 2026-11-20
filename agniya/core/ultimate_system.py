"""
AGNIYA encrypted aggregation engine.

Honest building blocks only (each is measured by tools/verify_claims.py):
- Paillier with fresh randomness per ciphertext (IND-CPA)
- RandomnessPool: r^n precomputed offline, one use each, multi-process refill
- Packing with overflow headroom: many values per ciphertext
- gmpy2 single-thread aggregation and CRT decryption

Trust model of this class: it holds the private key, so it plays the DATA OWNER.
A server that aggregates for someone else should only ever receive the public key
and ciphertexts (see sum_encrypted / BatchedAggregator.sum_column).
"""

from typing import Callable, List, Optional, Union

from agniya.core.paillier import (MIN_KEY_BITS, PaillierPublicKey, PaillierPrivateKey,
                                  generate_keypair, decrypt_crt, sum_ciphertexts)
from agniya.core.precomputation import RandomnessPool
from agniya.core.batch_packing import BatchedAggregator


class UltimateOptimizedDatabase:
    """Encrypt, aggregate homomorphically, decrypt."""

    def __init__(self, key_size: int = 2048, pool_size: int = 0, verbose: bool = False):
        if key_size < MIN_KEY_BITS:
            raise ValueError(f"Key size must be >= {MIN_KEY_BITS} bits")
        self.verbose = verbose
        self.pub, self.priv = generate_keypair(key_size)
        self.pool = RandomnessPool(self.pub, size=pool_size)
        self.packer = BatchedAggregator(self.pub, self.priv, encrypt_batch=self.pool.encrypt_batch)
        if verbose:
            print(f"AGNIYA: {key_size}-bit Paillier key, r^n pool {pool_size}")

    @property
    def public_key(self) -> PaillierPublicKey:
        return self.pub

    @property
    def private_key(self) -> PaillierPrivateKey:
        return self.priv

    # ---- single-value ciphertexts -------------------------------------------------
    def encrypt(self, data: Union[int, List[int]]):
        if isinstance(data, (list, tuple)):
            return self.pool.encrypt_batch(list(data))
        return self.pool.encrypt(data)

    def decrypt(self, ciphertext):
        if isinstance(ciphertext, (list, tuple)):
            return [decrypt_crt(self.pub, self.priv, c) for c in ciphertext]
        return decrypt_crt(self.pub, self.priv, ciphertext)

    def sum_encrypted(self, ciphertexts: List[int]) -> int:
        """Encrypted sum of ciphertexts (needs only the public key)."""
        if not ciphertexts:
            raise ValueError("No ciphertexts provided")
        return sum_ciphertexts(self.pub, ciphertexts)

    # ---- packed columns (fast path for aggregation) -------------------------------
    def encrypt_column(self, values: List[int]) -> dict:
        return self.packer.encrypt_column(values)

    def sum_column(self, column: dict) -> int:
        return self.packer.sum_column(column)

    # ---- convenience queries --------------------------------------------------------
    def sum(self, data: List[int], encrypted: bool = False) -> int:
        """SUM. Plaintext input is packed+encrypted first; encrypted input is summed directly."""
        if encrypted:
            return self.decrypt(self.sum_encrypted(data))
        return self.packer.sum_values(list(data))

    sum_query = sum  # backwards-compatible name

    def average(self, data: List[int], encrypted: bool = False) -> float:
        return self.sum(data, encrypted) / len(data) if data else 0.0

    def count(self, data: List, condition: Optional[Callable] = None) -> int:
        return len(data) if condition is None else sum(1 for v in data if condition(v))

    def stats(self) -> dict:
        return {'key_size': self.pub.n.bit_length(), **self.pool.get_stats()}


if __name__ == "__main__":
    db = UltimateOptimizedDatabase(pool_size=0)
    vals = list(range(-50, 1000))
    assert db.sum(vals) == sum(vals)
    cts = db.encrypt([3, 4, 5])
    assert db.sum(cts, encrypted=True) == 12 and cts[0] != db.encrypt(3)
    print("ok", db.stats())
