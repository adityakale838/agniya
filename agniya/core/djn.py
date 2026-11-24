"""
Fast r^n for Paillier: fixed-base, short-exponent variant (Damgard-Jurik-Nielsen 2010).

Standard Paillier randomness is r^n mod n^2 with r uniform in Z_n*: one modexp with a
2048-bit exponent (~14 ms). DJN instead fixes a public base hs = h^n mod n^2, where
h = -x^2 mod n for a random x, and uses hs^alpha with a random alpha of |n|/2 bits.
hs^alpha = (h^alpha)^n is still an n-th residue, so ciphertexts decrypt normally and
the decryptor needs nothing new.

Because the base is fixed, hs^alpha is computed with a precomputed comb table
(alpha split into w-bit digits, one table row per digit): about |n|/(2w) modular
multiplications instead of a full exponentiation.

SECURITY NOTE (checked against Damgard, Jurik, Nielsen 2010, section 4.1, "An Alternative
Encryption Function"): for an admissible modulus (p = q = 3 mod 4, gcd(p-1, q-1) = 2, a random
square generates the squares) and h = -x^2 mod n, h^a with a uniform in [0, 2^ceil(k/2)) is
computationally indistinguishable from uniform in Z_n*[+1] assuming factoring is hard, which DCR
implies ([13, Thm 3.2] in that paper). So the scheme stays IND-CPA under DCR alone. generate_keypair
makes admissible keys (safe primes); paillier.is_djn_admissible checks a key. Keys that are not
admissible (e.g. made by the browser client) should use method="standard".
"""

import secrets

import gmpy2
from gmpy2 import mpz

from agniya.core.paillier import PaillierPublicKey


class FixedBaseRN:
    """Callable producing fresh hs^alpha values (drop-in replacement for random_rn)."""

    def __init__(self, public_key: PaillierPublicKey, window: int = 8, exponent_bits: int = None):
        n, n2 = mpz(public_key.n), mpz(public_key.n_squared)
        while True:
            x = mpz(secrets.randbelow(public_key.n - 2) + 2)
            if gmpy2.gcd(x, n) == 1:
                break
        h = (-x * x) % n
        self.hs = gmpy2.powmod(h, n, n2)
        self.n_squared = n2
        self.window = window
        self.exponent_bits = exponent_bits or (public_key.n.bit_length() + 1) // 2
        self._mask = (1 << window) - 1
        digits = -(-self.exponent_bits // window)
        # table[i][d] = hs^(d * 2^(window*i)) mod n^2
        self.table = []
        base = self.hs
        for _ in range(digits):
            row = [mpz(1)]
            for _ in range(self._mask):
                row.append(row[-1] * base % n2)
            self.table.append(row)
            base = row[-1] * base % n2  # base^(2^window)

    def rn_for(self, alpha: int) -> int:
        acc = mpz(1)
        n2, w, mask = self.n_squared, self.window, self._mask
        for i, row in enumerate(self.table):
            d = (alpha >> (i * w)) & mask
            if d:
                acc = acc * row[d] % n2
        return int(acc)

    def __call__(self) -> int:
        return self.rn_for(secrets.randbits(self.exponent_bits))

    def table_bytes(self) -> int:
        return len(self.table) * len(self.table[0]) * (int(self.n_squared).bit_length() // 8)
