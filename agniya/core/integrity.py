"""
Integrity checks for client-held keys: the client can tell when the server returns a wrong answer.

Every packed plaintext m of page p, ciphertext c gets a tag t = (alpha * m + beta(p, c)) mod P in
bits above the data, under a key only the client has (alpha and every beta are AES-256-CTR
keystream). Products add tags like data, so the product of ciphertexts S of a page holds
M + T * 2^shift with T = alpha * M + sum(beta(p, c) for c in S) mod P. A server that multiplies
other ciphertexts, adds a constant, or returns anything but the honest product passes this with
probability about 2^-127, since it never sees alpha or beta.

Range queries also need the cut points: per ciphertext the client stores a MAC of the OPE tags of
its rows, and the server returns the tags around the cut (rows i-1, i, j-1, j) with their MACs, so
the client sees that rows i..j-1 are exactly those inside [lo_tag, hi_tag].
"""

import hashlib
import hmac
import secrets
from typing import Dict, List, Optional, Tuple

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

P = 2 ** 127 - 1
RESERVE = 159  # bits above the data: a 127-bit tag summed over up to 2^32 ciphertexts


class IntegrityError(Exception):
    """The server's answer does not match the data this client uploaded."""


class ColumnMac:
    def __init__(self, n: int, key: Optional[bytes] = None):
        self.key = key or secrets.token_bytes(32)  # stored in key files; tags and cut MACs use subkeys of it
        self._aes, self._hmac = (hmac.new(self.key, label, hashlib.sha256).digest() for label in (b'tags', b'cuts'))
        self.shift = n.bit_length() - 1 - RESERVE  # the data stays below 2^shift (layouts reserve RESERVE bits)
        self.alpha = self._blocks(1 << 127, 1)[0]

    def _blocks(self, start: int, n: int) -> List[int]:
        """n pseudorandom values < 2^127: AES-256-CTR keystream blocks start..start+n-1."""
        ks = Cipher(algorithms.AES(self._aes), modes.CTR(start.to_bytes(16, 'big'))).encryptor().update(bytes(16 * n))
        return [int.from_bytes(ks[k:k + 16], 'big') >> 1 for k in range(0, len(ks), 16)]

    def beta_sum(self, page: int, first: int, n: int) -> int:
        return sum(self._blocks((page << 64) + first, n)) if n else 0

    def tag(self, plain: List[int], pages: int = 1) -> List[int]:
        """Plaintexts (pages of equal length, page-major) with their tags above the data."""
        m = len(plain) // max(pages, 1)
        betas = [b for p in range(pages) for b in self._blocks(p << 64, m)] if m else []
        return [x + (((self.alpha * x + b) % P) << self.shift) for x, b in zip(plain, betas)]

    def check(self, plaintext: int, page: int, first: int, n: int) -> bool:
        """plaintext = product of ciphertexts first..first+n-1 of the page, decrypted."""
        low = plaintext & ((1 << self.shift) - 1)
        return (plaintext >> self.shift) % P == (self.alpha * low + self.beta_sum(page, first, n)) % P

    def tags_mac(self, page: int, c: int, tags: List) -> str:
        msg = f"{page}:{c}:{','.join(str(t) for t in tags)}".encode()
        return hmac.new(self._hmac, msg, hashlib.sha256).digest()[:16].hex()

    def tag_macs(self, page: int, tags: List[int], slots: int) -> List[str]:
        return [self.tags_mac(page, c, tags[k:k + slots]) for c, k in enumerate(range(0, len(tags), slots))]

    def check_cut(self, page: int, slots: int, count: int, i: int, j: int, witnesses: List[Dict],
                  lo_tag: int, hi_tag: int) -> bool:
        """Rows i..j-1 are exactly the rows with lo_tag <= tag <= hi_tag (tags are sorted)."""
        seen = {}
        for w in witnesses:
            if not hmac.compare_digest(self.tags_mac(page, w['index'], w['tags']), str(w['mac'])):
                return False
            seen.update({w['index'] * slots + k: int(t) for k, t in enumerate(w['tags'])})
        try:
            return (0 <= i <= j <= count and (i == 0 or seen[i - 1] < lo_tag) and (j == count or seen[j] > hi_tag)
                    and (i == j or (seen[i] >= lo_tag and seen[j - 1] <= hi_tag)))
        except KeyError:  # a needed row was not sent
            return False


def range_cuts(slots: int, count: int, i: int, j: int) -> Tuple[List[int], List[Tuple[int, int, int]]]:
    """Ciphertexts wholly inside rows i..j-1, and the (at most two) cut ones as (index, first_slot, end_slot)."""
    full, edges = [], []
    for c in (range(i // slots, (j - 1) // slots + 1) if i < j else ()):
        lo, hi = max(i, c * slots) - c * slots, min(j, (c + 1) * slots, count) - c * slots
        if lo == 0 and hi == min(slots, count - c * slots):
            full.append(c)
        else:
            edges.append((c, lo, hi))
    return full, edges
