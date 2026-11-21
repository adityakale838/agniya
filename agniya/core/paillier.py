"""
Paillier cryptosystem (additively homomorphic, IND-CPA under DCR).

Textbook scheme with g = n + 1, CRT decryption and gmpy2 big-int arithmetic.
Every encryption uses fresh randomness r; two encryptions of the same value
are different ciphertexts. Never cache plaintext -> ciphertext.
"""

import secrets
from dataclasses import dataclass
from typing import Tuple
import json
from pathlib import Path

from agniya.core.number_theory import generate_prime, gcd, lcm, mod_inverse

try:
    import gmpy2

    def _powmod(base: int, exponent: int, modulus: int) -> int:
        return int(gmpy2.powmod(base, exponent, modulus))
    GMPY2_AVAILABLE = True
except ImportError:  # pragma: no cover - gmpy2 is a hard requirement in requirements.txt
    _powmod = pow
    GMPY2_AVAILABLE = False

MIN_KEY_BITS = 2048  # ~112-bit security; 1024-bit moduli are deprecated (NIST SP 800-131A)


@dataclass
class PaillierPublicKey:
    n: int
    g: int          # always n + 1
    n_squared: int
    bit_length: int

    def __repr__(self):
        return f"PaillierPublicKey(bit_length={self.bit_length})"


@dataclass
class PaillierPrivateKey:
    lambda_n: int   # lcm(p-1, q-1)
    mu: int         # L(g^lambda mod n^2)^-1 mod n
    p: int
    q: int
    p_squared: int
    q_squared: int
    hp: int         # L_p(g^(p-1) mod p^2)^-1 mod p
    hq: int
    q_inv_p: int = 0  # q^-1 mod p, for CRT recombination (computed on demand if 0)

    def __repr__(self):
        return "PaillierPrivateKey(<hidden>)"


def generate_keypair(bit_length: int = 2048) -> Tuple[PaillierPublicKey, PaillierPrivateKey]:
    """Generate a key pair whose modulus n has exactly `bit_length` bits."""
    half = bit_length // 2
    while True:
        p = generate_prime(half)
        q = generate_prime(half)
        n = p * q
        # top two bits of p, q are set, so n has exactly 2*half bits
        if p != q and n.bit_length() == bit_length and gcd(n, (p - 1) * (q - 1)) == 1:
            break
    return keypair_from_primes(p, q)


def keypair_from_primes(p: int, q: int) -> Tuple[PaillierPublicKey, PaillierPrivateKey]:
    """Rebuild the full key pair from the two primes (e.g. when loading a saved key)."""
    n = p * q
    if p == q or gcd(n, (p - 1) * (q - 1)) != 1:
        raise ValueError("p, q do not form a valid Paillier modulus")
    bit_length = n.bit_length()
    n_squared = n * n
    g = n + 1
    lambda_n = lcm(p - 1, q - 1)
    mu = mod_inverse((_powmod(g, lambda_n, n_squared) - 1) // n, n)

    p_squared, q_squared = p * p, q * q
    hp = mod_inverse((_powmod(g, p - 1, p_squared) - 1) // p, p)
    hq = mod_inverse((_powmod(g, q - 1, q_squared) - 1) // q, q)

    return (PaillierPublicKey(n=n, g=g, n_squared=n_squared, bit_length=bit_length),
            PaillierPrivateKey(lambda_n=lambda_n, mu=mu, p=p, q=q, p_squared=p_squared,
                               q_squared=q_squared, hp=hp, hq=hq, q_inv_p=mod_inverse(q, p)))


def random_rn(public_key: PaillierPublicKey) -> int:
    """Fresh r^n mod n^2 (the expensive, plaintext-independent half of encryption).

    Can be precomputed offline, but each value must be used for ONE ciphertext only.
    """
    n = public_key.n
    while True:
        r = secrets.randbelow(n)
        if r > 0 and gcd(r, n) == 1:
            return _powmod(r, n, public_key.n_squared)


def encrypt_with_rn(public_key: PaillierPublicKey, plaintext: int, rn: int) -> int:
    """c = g^m * r^n mod n^2, using g = n+1  =>  g^m = 1 + m*n (mod n^2)."""
    if not (0 <= plaintext < public_key.n):
        raise ValueError(f"Plaintext must be in range [0, n)")
    return (1 + plaintext * public_key.n) * rn % public_key.n_squared


def encrypt(public_key: PaillierPublicKey, plaintext: int) -> int:
    """Probabilistic Paillier encryption of an integer in [0, n)."""
    if not (0 <= plaintext < public_key.n):
        raise ValueError(f"Plaintext must be in range [0, n)")
    return encrypt_with_rn(public_key, plaintext, random_rn(public_key))


def decrypt(public_key: PaillierPublicKey, private_key: PaillierPrivateKey, ciphertext: int) -> int:
    """Standard decryption: L(c^lambda mod n^2) * mu mod n."""
    c_lambda = _powmod(ciphertext, private_key.lambda_n, public_key.n_squared)
    return (c_lambda - 1) // public_key.n * private_key.mu % public_key.n


def decrypt_crt(public_key: PaillierPublicKey, private_key: PaillierPrivateKey, ciphertext: int) -> int:
    """CRT decryption (~3x faster than decrypt)."""
    p, q = private_key.p, private_key.q
    m_p = (_powmod(ciphertext, p - 1, private_key.p_squared) - 1) // p * private_key.hp % p
    m_q = (_powmod(ciphertext, q - 1, private_key.q_squared) - 1) // q * private_key.hq % q
    if not private_key.q_inv_p:
        private_key.q_inv_p = mod_inverse(q, p)
    # Garner recombination: m = m_q + q * ((m_p - m_q) * q^-1 mod p)
    return m_q + q * ((m_p - m_q) * private_key.q_inv_p % p)


def homomorphic_add(public_key: PaillierPublicKey, ciphertext1: int, ciphertext2: int) -> int:
    """E(m1) * E(m2) = E(m1 + m2)."""
    return ciphertext1 * ciphertext2 % public_key.n_squared


def homomorphic_multiply(public_key: PaillierPublicKey, ciphertext: int, scalar: int) -> int:
    """E(m)^k = E(k * m)."""
    return _powmod(ciphertext, scalar, public_key.n_squared)


def sum_ciphertexts(public_key: PaillierPublicKey, ciphertexts) -> int:
    """Homomorphic sum of many ciphertexts (single-thread gmpy2 loop; faster than threaded trees)."""
    n2 = gmpy2.mpz(public_key.n_squared) if GMPY2_AVAILABLE else public_key.n_squared
    acc = 1
    for c in ciphertexts:
        acc = acc * c % n2
    return int(acc)


class PaillierCryptosystem:
    """Convenience wrapper holding a key pair."""

    def __init__(self, bit_length: int = 2048):
        if bit_length < MIN_KEY_BITS:
            raise ValueError(f"Key size must be >= {MIN_KEY_BITS} bits")
        self.public_key, self.private_key = generate_keypair(bit_length)
        self.bit_length = bit_length

    def encrypt(self, plaintext: int) -> int:
        return encrypt(self.public_key, plaintext)

    def decrypt(self, ciphertext: int, use_crt: bool = True) -> int:
        if use_crt:
            return decrypt_crt(self.public_key, self.private_key, ciphertext)
        return decrypt(self.public_key, self.private_key, ciphertext)

    def add(self, ciphertext1: int, ciphertext2: int) -> int:
        return homomorphic_add(self.public_key, ciphertext1, ciphertext2)

    def multiply(self, ciphertext: int, scalar: int) -> int:
        return homomorphic_multiply(self.public_key, ciphertext, scalar)

    def sum_encrypted(self, ciphertexts: list) -> int:
        if not ciphertexts:
            return self.encrypt(0)
        return sum_ciphertexts(self.public_key, ciphertexts)

    def save_keys(self, filepath: Path):
        """Save the PUBLIC key only."""
        with open(filepath, 'w') as f:
            json.dump({'bit_length': self.bit_length,
                       'public_key': {'n': str(self.public_key.n), 'g': str(self.public_key.g)}}, f, indent=2)


if __name__ == "__main__":
    crypto = PaillierCryptosystem(2048)
    values = [65, 72, 80, 98, 105, 120, 140]
    total = crypto.decrypt(crypto.sum_encrypted([crypto.encrypt(v) for v in values]))
    assert total == sum(values), total
    assert crypto.encrypt(5) != crypto.encrypt(5)
    print("ok", total)
