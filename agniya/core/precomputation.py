"""
Offline randomness pool for Paillier encryption.

Paillier encryption is c = (1 + m*n) * r^n mod n^2. The r^n factor is the
expensive part (one 2048-bit-exponent modexp) and does not depend on m, so it
can be computed ahead of time. Online encryption is then one multiplication.

Each r^n is used for exactly ONE ciphertext, so ciphertexts stay randomized
(IND-CPA). This replaces the old plaintext -> ciphertext cache, which returned
the same ciphertext for the same value and leaked equality/frequencies.
"""

import os
from concurrent.futures import ProcessPoolExecutor
from typing import List

from agniya.core.paillier import PaillierPublicKey, random_rn, encrypt_with_rn

PARALLEL_THRESHOLD = 64  # below this, process start-up costs more than it saves


def _rn_batch(args) -> List[int]:
    """Top-level so ProcessPoolExecutor can pickle it."""
    pub, count = args
    return [random_rn(pub) for _ in range(count)]


class RandomnessPool:
    """Pool of precomputed one-time r^n values for a public key."""

    def __init__(self, public_key: PaillierPublicKey, size: int = 0, workers: int = None):
        self.public_key = public_key
        self.workers = workers or os.cpu_count() or 1
        self._pool: List[int] = []
        self.generated = 0  # r^n values computed
        self.used = 0       # ciphertexts produced (each consumed one r^n)
        if size:
            self.refill(size)

    def __len__(self):
        return len(self._pool)

    def refill(self, count: int):
        """Compute `count` fresh r^n values (uses all cores for large batches)."""
        if count <= 0:
            return
        if count < PARALLEL_THRESHOLD or self.workers == 1:
            self._pool.extend(_rn_batch((self.public_key, count)))
        else:
            w = min(self.workers, count)
            chunks = [(self.public_key, count // w + (i < count % w)) for i in range(w)]
            with ProcessPoolExecutor(w) as ex:
                for part in ex.map(_rn_batch, chunks):
                    self._pool.extend(part)
        self.generated += count

    def encrypt(self, plaintext: int) -> int:
        if not self._pool:
            self.refill(1)
        self.used += 1
        return encrypt_with_rn(self.public_key, plaintext, self._pool.pop())

    def encrypt_batch(self, plaintexts: List[int]) -> List[int]:
        self.refill(len(plaintexts) - len(self._pool))
        return [self.encrypt(m) for m in plaintexts]

    def get_stats(self) -> dict:
        return {'pool_remaining': len(self._pool), 'generated': self.generated, 'used': self.used}


if __name__ == "__main__":
    import time
    from agniya.core.paillier import generate_keypair, decrypt_crt
    pub, priv = generate_keypair(2048)
    pool = RandomnessPool(pub)
    t = time.perf_counter(); pool.refill(256); t_off = time.perf_counter() - t
    t = time.perf_counter(); cts = [pool.encrypt(42) for _ in range(256)]; t_on = time.perf_counter() - t
    assert len(set(cts)) == 256 and all(decrypt_crt(pub, priv, c) == 42 for c in cts[:5])
    print(f"offline {t_off / 256 * 1e3:.2f} ms/value, online {t_on / 256 * 1e6:.1f} us/value, all distinct")
