"""
Faster pyope: same scheme (Boldyreva et al. 2009), same key, bit-identical tags.

pyope spends most of its time turning the AES-CTR coin tape into bits one Python call
per byte, and walks the whole recursion tree again for every value. FastOPE
- generates the same coin tape with C-level iteration (table lookup per byte), and
- encrypt_many() walks the tree once for a whole batch: each node's hypergeometric
  split is sampled once and shared by every value below it.
tests/test_core/test_fast_ope.py checks the tags equal pyope's.
"""

import hashlib
import hmac
import math
from bisect import bisect_right
from itertools import chain
from typing import Dict, Iterable, List

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms
from cryptography.hazmat.primitives.ciphers.modes import CTR
from pyope import stat
from pyope.ope import OPE, ValueRange

_BITS = [tuple((b >> i) & 1 for i in range(7, -1, -1)) for b in range(256)]  # MSB first, as pyope
_ZEROS = bytes(64)


class FastOPE(OPE):
    def tape_gen(self, data):
        key = hmac.new(self.key, str(data).encode(), hashlib.sha256).digest()
        enc = Cipher(algorithms.AES(key), CTR(bytes(16))).encryptor()
        stream = chain.from_iterable(iter(lambda: enc.update(_ZEROS), None))  # infinite keystream bytes
        return chain.from_iterable(map(_BITS.__getitem__, stream))

    def encrypt_many(self, values: Iterable[int]) -> Dict[int, int]:
        """{value: tag} for every distinct value, one shared walk of the OPE tree."""
        vals = sorted(set(values))
        if vals and not (self.in_range.contains(vals[0]) and self.in_range.contains(vals[-1])):
            raise ValueError('Plaintext is not within the input range')
        tags: Dict[int, int] = {}

        def walk(lo: int, hi: int, in_range: ValueRange, out_range: ValueRange):
            # same arithmetic as OPE.encrypt_recursive, for vals[lo:hi] at once
            if lo == hi:
                return
            if in_range.size() == 1:
                tags[vals[lo]] = stat.sample_uniform(out_range, self.tape_gen(vals[lo]))
                return
            in_size, out_size = in_range.size(), out_range.size()
            in_edge, out_edge = in_range.start - 1, out_range.start - 1
            mid = out_edge + int(math.ceil(out_size / 2.0))
            x = stat.sample_hgd(in_range, out_range, mid, self.tape_gen(mid))
            k = bisect_right(vals, x, lo, hi)
            if lo < k:  # a side with no values may be an empty range: never build it
                walk(lo, k, ValueRange(in_edge + 1, x), ValueRange(out_edge + 1, mid))
            if k < hi:
                walk(k, hi, ValueRange(x + 1, in_edge + in_size), ValueRange(mid + 1, out_edge + out_size))

        walk(0, len(vals), self.in_range, self.out_range)
        return tags

    def encrypt_list(self, values: List[int]) -> List[int]:
        tags = self.encrypt_many(values)
        return [tags[v] for v in values]
