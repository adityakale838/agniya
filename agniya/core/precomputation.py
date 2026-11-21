"""
Offline randomness pool for Paillier encryption.

Paillier encryption is c = (1 + m*n) * r^n mod n^2. The r^n factor is the
expensive part and does not depend on m, so it can be computed ahead of time.
Online encryption is then one multiplication.

Each r^n is used for exactly ONE ciphertext, so ciphertexts stay randomized.

Methods:
- "djn" (default): fixed-base short-exponent r^n (agniya/core/djn.py), ~15x faster per
  value; relies on the DJN short-exponent assumption (see djn.py SECURITY NOTE).
- "standard": textbook r^n with uniform r in Z_n*; relies on DCR only.
"""

import os
from concurrent.futures import ProcessPoolExecutor
from typing import List

from agniya.core.paillier import PaillierPublicKey, random_rn, encrypt_with_rn
from agniya.core.djn import FixedBaseRN

DEFAULT_METHOD = os.environ.get("AGNIYA_RN_METHOD", "djn")
# below these counts, starting/feeding worker processes costs more than it saves
PARALLEL_THRESHOLD = {"standard": 64, "djn": 4096}  # djn: worker start-up + 17 MB table ~1 s

_worker_gen = None  # per-process r^n generator (set by _init_worker)


def _init_worker(public_key, method):
    global _worker_gen
    _worker_gen = FixedBaseRN(public_key) if method == "djn" else (lambda: random_rn(public_key))


def _worker_batch(count: int) -> List[int]:
    return [_worker_gen() for _ in range(count)]


class RandomnessPool:
    """Pool of precomputed one-time r^n values for a public key."""

    def __init__(self, public_key: PaillierPublicKey, size: int = 0, workers: int = None,
                 method: str = None):
        method = method or DEFAULT_METHOD
        if method not in PARALLEL_THRESHOLD:
            raise ValueError(f"unknown r^n method {method!r}")
        self.public_key = public_key
        self.method = method
        self.workers = workers or os.cpu_count() or 1
        self._gen = FixedBaseRN(public_key) if method == "djn" else (lambda: random_rn(public_key))
        self._executor = None
        self._pool: List[int] = []
        self.generated = 0  # r^n values computed
        self.used = 0       # ciphertexts produced (each consumed one r^n)
        if size:
            self.refill(size)

    def __len__(self):
        return len(self._pool)

    def refill(self, count: int):
        """Compute `count` fresh r^n values (all cores for large batches)."""
        if count <= 0:
            return
        if count < PARALLEL_THRESHOLD[self.method] or self.workers == 1:
            self._pool.extend(self._gen() for _ in range(count))
        else:
            if self._executor is None:  # persistent: Windows process start-up is ~1 s
                self._executor = ProcessPoolExecutor(self.workers, initializer=_init_worker,
                                                     initargs=(self.public_key, self.method))
            w = self.workers
            for part in self._executor.map(_worker_batch, [count // w + (i < count % w) for i in range(w)]):
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

    def close(self):
        if self._executor is not None:
            self._executor.shutdown()
            self._executor = None

    def get_stats(self) -> dict:
        return {'method': self.method, 'pool_remaining': len(self._pool),
                'generated': self.generated, 'used': self.used}


if __name__ == "__main__":
    import time
    from agniya.core.paillier import generate_keypair, decrypt_crt
    pub, priv = generate_keypair(2048)
    for method in ("standard", "djn"):
        pool = RandomnessPool(pub, method=method)
        t = time.perf_counter(); pool.refill(4096); t_off = time.perf_counter() - t
        cts = [pool.encrypt(42) for _ in range(4096)]
        assert len(set(cts)) == 4096 and all(decrypt_crt(pub, priv, c) == 42 for c in cts[:5])
        print(f"{method}: {t_off / 4096 * 1e3:.3f} ms per r^n on {pool.workers} workers, all distinct")
        pool.close()
