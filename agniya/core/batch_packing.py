"""
Packing several plaintexts into one Paillier ciphertext.

Values are laid out in fixed-width slots of one plaintext: v0 + v1*2^b + v2*2^2b ...
One encryption then covers many values, and multiplying ciphertexts adds all
slots at once. This is a well-known technique (e.g. Ge & Zdonik, VLDB 2007).
Correctness requires headroom: each slot must hold the SUM of everything that
lands in it, which BatchedAggregator.layout() guarantees.
"""

import math
from typing import Callable, Dict, List, Optional, Tuple
from agniya.core.integrity import RESERVE, ColumnMac, range_cuts
from agniya.core.paillier import (PaillierPublicKey, PaillierPrivateKey, encrypt, decrypt,
                                  decrypt_crt, sum_ciphertexts)


class BatchPacker:
    """
    Pack multiple small integers into a single large integer for batch encryption.
    
    This is inspired by SIMD (Single Instruction Multiple Data) in CPUs,
    but applied to homomorphic encryption.
    
    Key Innovation: Works at ANY key size (1024, 2048, 4096-bit)!
    """
    
    def __init__(self, slot_size_bits: int = 32, max_slots: int = 32):
        """
        Initialize batch packer.
        
        Args:
            slot_size_bits: Bits per slot (default 32 = 4 billion range)
            max_slots: Maximum slots per packed value
        """
        self.slot_size_bits = slot_size_bits
        self.slot_base = 2 ** slot_size_bits  # Base for slot encoding
        self.max_slots = max_slots
        self.slot_mask = self.slot_base - 1
    
    def pack(self, values: List[int]) -> int:
        """
        Pack multiple values into single integer.
        
        Encoding: packed = v₀ + v₁×B + v₂×B² + ... + vₙ×Bⁿ
        where B = 2^slot_size_bits
        
        Args:
            values: List of integers to pack (each must fit in slot)
            
        Returns:
            Single packed integer
            
        Example:
            values = [100, 200, 300]
            packed = 100 + 200×2^32 + 300×2^64
        """
        if len(values) > self.max_slots:
            raise ValueError(f"Too many values: {len(values)} > {self.max_slots}")
        
        # Check all values fit in slots
        for i, v in enumerate(values):
            if v < 0 or v >= self.slot_base:
                raise ValueError(
                    f"Value {v} at index {i} doesn't fit in {self.slot_size_bits}-bit slot"
                )
        
        # Pack: v₀ + v₁×B + v₂×B² + ...
        packed = 0
        for i, value in enumerate(values):
            packed += value * (self.slot_base ** i)
        
        return packed
    
    def unpack(self, packed: int, num_slots: int) -> List[int]:
        """
        Unpack single integer into multiple values.
        
        Args:
            packed: Packed integer
            num_slots: Number of values to extract
            
        Returns:
            List of unpacked values
        """
        values = []
        for i in range(num_slots):
            # Extract slot: (packed // B^i) mod B
            value = (packed // (self.slot_base ** i)) & self.slot_mask
            values.append(value)
        
        return values
    
    def supports_key_size(self, key_bit_length: int) -> int:
        """
        Calculate how many slots fit in given key size.
        
        Args:
            key_bit_length: Paillier key size (e.g., 2048)
            
        Returns:
            Maximum number of slots that fit
        """
        # Need some bits for carries/overflow in addition
        # Safe: use 75% of key size
        safe_bits = int(key_bit_length * 0.75)
        max_slots = safe_bits // self.slot_size_bits
        
        return min(max_slots, self.max_slots)


class BatchOperations:
    """
    Perform homomorphic operations on packed batches.
    
    This is where the magic happens: compute on multiple values at once!
    """
    
    def __init__(self, public_key: PaillierPublicKey, 
                 packer: BatchPacker):
        """
        Initialize batch operations.
        
        Args:
            public_key: Paillier public key
            packer: Batch packer instance
        """
        self.public_key = public_key
        self.packer = packer
        
        # Determine optimal batch size for this key
        self.batch_size = packer.supports_key_size(public_key.bit_length)
    
    def encrypt_batch(self, values: List[int]) -> int:
        """
        Encrypt multiple values as single ciphertext.
        
        Args:
            values: List of values to encrypt (max batch_size)
            
        Returns:
            Single ciphertext containing all values
        """
        if len(values) > self.batch_size:
            raise ValueError(f"Batch too large: {len(values)} > {self.batch_size}")
        
        # Pack values
        packed = self.packer.pack(values)
        
        # Encrypt packed value
        ciphertext = encrypt(self.public_key, packed)
        
        return ciphertext
    
    def decrypt_batch(self, private_key: PaillierPrivateKey, 
                     ciphertext: int, num_values: int) -> List[int]:
        """
        Decrypt batch ciphertext into multiple values.
        
        Args:
            private_key: Paillier private key
            ciphertext: Encrypted batch
            num_values: Number of values in batch
            
        Returns:
            List of decrypted values
        """
        # Decrypt packed value
        packed = decrypt(self.public_key, private_key, ciphertext)
        
        # Unpack values
        values = self.packer.unpack(packed, num_values)
        
        return values
    
    def batch_add(self, ct1: int, ct2: int) -> int:
        """
        Add two encrypted batches element-wise.
        
        E([a, b, c]) × E([d, e, f]) = E([a+d, b+e, c+f])
        
        Args:
            ct1: First encrypted batch
            ct2: Second encrypted batch
            
        Returns:
            Encrypted batch of sums
        """
        # Homomorphic addition: multiply ciphertexts
        return (ct1 * ct2) % self.public_key.n_squared
    
    def batch_scalar_multiply(self, ciphertext: int, scalars: List[int]) -> int:
        """
        Multiply batch by scalar vector.
        
        Note: This is a simplified version that raises the entire ciphertext
        to each scalar's power. For true element-wise multiplication, you need
        to separate slots, which requires decryption. This is mainly for demonstration.
        
        For practical use, encrypt scalars and use batch_add for element-wise operations.
        
        Args:
            ciphertext: Encrypted batch [a, b, c]
            scalars: List of scalar multipliers (must all be same for this version)
            
        Returns:
            Encrypted batch of products
        """
        # For simplicity: apply first scalar to entire batch
        # (Full implementation would require slot separation)
        scalar = scalars[0] if scalars else 1
        
        # Homomorphic scalar multiplication
        return pow(ciphertext, scalar, self.public_key.n_squared)
    
    def sum_batches(self, ciphertexts: List[int]) -> int:
        """
        Sum multiple encrypted batches.
        
        Args:
            ciphertexts: List of encrypted batches
            
        Returns:
            Encrypted batch of sums
        """
        if not ciphertexts:
            # Return encrypted zeros
            zeros = [0] * self.batch_size
            return self.encrypt_batch(zeros)
        
        result = ciphertexts[0]
        for ct in ciphertexts[1:]:
            result = self.batch_add(result, ct)
        
        return result


def quantile_rows(i: int, j: int, q: float) -> Tuple[int, int, float]:
    """Quantile q of sorted rows i..j-1 (i < j) as pandas computes it (linear interpolation):
    rows a <= b and frac, value = v[a] + (v[b] - v[a]) * frac. q = 0 is MIN, 0.5 MEDIAN, 1 MAX."""
    pos = q * (j - i - 1)
    return i + math.floor(pos), i + math.ceil(pos), pos - math.floor(pos)


def slot_value(plaintext: int, k: int, slot_bits: int) -> int:
    return (plaintext >> (k * slot_bits)) & ((1 << slot_bits) - 1)


def squares(ints: List[int]) -> Tuple[List[int], int]:
    """(x - c)^2 for each fixed-point x, and c (about the mean, so the squares stay small). Their sum next
    to SUM(x) gives VARIANCE and STDDEV (sample_variance); for any c, var(x) = var(x - c)."""
    c = sum(ints) // max(len(ints), 1)
    return [(x - c) ** 2 for x in ints], c


def sample_variance(n: int, s1: int, s2: int, c: int, scale: int) -> Optional[float]:
    """Sample variance (ddof=1, as pandas .var() and SQL VARIANCE) of n fixed-point values from their sum s1
    and s2 = sum((x - c)^2), computed exactly; None for fewer than 2 values."""
    if n < 2:
        return None
    d = s1 - n * c  # sum(x - c)
    num = n * s2 - d * d
    if num < 0:
        raise ValueError('sum of squares below the square of the sum: not sums of the same values')
    return num / (n * (n - 1) * scale * scale)  # int / int: correctly rounded


def range_plan(public_key: PaillierPublicKey, ciphertexts: List[int], slots: int, count: int,
               i: int, j: int) -> Tuple[Optional[int], List[Tuple[int, int, int]]]:
    """Public-key half of a range SUM over packed values i..j-1 (0 <= i < j <= count).

    Returns (product of the ciphertexts wholly inside the range, or None) and the (at most
    two) ciphertexts cut by the range edges as (ciphertext, first_slot, end_slot). The
    key holder decrypts the product once and each edge on its own, so it sees the edge
    slots individually; whoever runs this function sees no plaintext."""
    full, edges = range_cuts(slots, count, i, j)
    return ((sum_ciphertexts(public_key, [ciphertexts[c] for c in full]) if full else None),
            [(ciphertexts[c], lo, hi) for c, lo, hi in edges])


def decrypt_range(public_key: PaillierPublicKey, private_key: PaillierPrivateKey, product: Optional[int],
                  edges: List[Tuple[int, int, int]], slot_bits: int, slots: int, dec: Optional[Callable] = None) -> int:
    """Private-key half of range_plan: slot sums of the product plus the selected edge slots.
    dec(ciphertext) -> plaintext replaces decryption (for plaintexts already decrypted)."""
    dec = dec or (lambda c: decrypt_crt(public_key, private_key, c))
    mask = (1 << slot_bits) - 1
    total = 0
    for ct, lo, hi in ([(product, 0, slots)] if product is not None else []) + list(edges):
        m = dec(ct)
        total += sum((m >> (k * slot_bits)) & mask for k in range(lo, hi))
    return total


def group_layout(public_key: PaillierPublicKey, max_value: int, sizes: List[int],
                 decryptions_per_page: int = 1, reserve: int = 0) -> Tuple[int, int, int]:
    """(slot_bits, lanes, per_page) for GROUP BY packing: in every ciphertext each of up to per_page
    groups gets `lanes` value slots plus one count slot. Groups are split into pages of per_page;
    each page is its own run of ciphertexts, whose product holds the sum and count of every group
    on the page. One page (one decryption) whenever all groups fit; otherwise the layout with the
    fewest ciphertexts, counting each decryption a page adds to a query as 16 ciphertexts. `reserve`
    top bits stay free (integrity tags)."""
    usable = public_key.n.bit_length() - 1 - reserve
    k, biggest = max(len(sizes), 1), max(sizes, default=0)

    def fit(lanes):  # (slot bits, groups per plaintext, ciphertexts per page)
        m = max(1, -(-biggest // lanes))  # ciphertexts = rows of the biggest group / lanes
        bits = max(max_value * m, lanes * m, 1).bit_length()  # a slot's sum over all m ciphertexts fits
        return bits, usable // ((lanes + 1) * bits), m

    for lanes in range(max(1, usable // (max(max_value, 1).bit_length() + 1) // k - 1), 0, -1):
        bits, per, _ = fit(lanes)
        if per >= k:
            return bits, lanes, k
    best, lanes = None, 1
    while (f := fit(lanes))[1] >= 1:
        pages = -(-k // f[1])
        # ponytail: a decryption (3.2 ms, every query) ~ 16 ciphertexts (0.7 ms to encrypt once, 6 us per query)
        cost = pages * f[2] + 16 * decryptions_per_page * pages
        if best is None or cost < best[0]:
            best = (cost, f[0], lanes, f[1])
        lanes += 1
    if best is None:
        raise ValueError('Values too large for one plaintext; use a larger key')
    return best[1], best[2], best[3]


def group_pages(column: Dict) -> List[List[int]]:
    """A grouped column's ciphertexts split into its pages (one product and decryption each)."""
    cts, pages = column['ciphertexts'], column.get('pages', 1)
    m = len(cts) // pages
    return [cts[p * m:(p + 1) * m] for p in range(pages)]


def decrypt_groups(public_key: PaillierPublicKey, private_key: PaillierPrivateKey, products: List[int],
                   column: Dict, dec: Optional[Callable] = None) -> Dict:
    """{label: (sum, count)} from the products of a grouped column's pages (one decryption each)."""
    dec = dec or (lambda c: decrypt_crt(public_key, private_key, c))
    ms = [dec(p) for p in products]
    bits, lanes = column['slot_bits'], column['lanes']
    per, mask = column['slots'] // (lanes + 1), (1 << bits) - 1
    out = {}
    for gi, label in enumerate(column['labels']):
        page, base = divmod(gi, per)
        m, base = ms[page], base * (lanes + 1)
        slot = lambda s: (m >> (s * bits)) & mask  # noqa: E731
        count = slot(base + lanes)
        out[label] = (sum(slot(base + k) for k in range(lanes)) + column['offset'] * count, count)
    return out


def decrypt_sorted_groups(public_key: PaillierPublicKey, private_key: PaillierPrivateKey,
                          plans: List[Tuple[Optional[int], List[Tuple[int, int, int]]]], column: Dict,
                          dec: Optional[Callable] = None) -> Dict:
    """{label: (sum, count)} over a row range of a column from encrypt_sorted_groups: plans[p] is
    range_plan(group_pages(column)[p], slots=lanes, ...) = (product, edges) of page p, all for the
    same rows. Groups with no rows in the range are left out."""
    dec = dec or (lambda c: decrypt_crt(public_key, private_key, c))
    bits, lanes, labels = column['slot_bits'], column['lanes'], column['labels']
    per, mask = column['slots'] // (lanes + 1), (1 << bits) - 1
    sums, counts = [0] * len(labels), [0] * len(labels)
    for page, (product, edges) in enumerate(plans):
        own = range(page * per, min(len(labels), (page + 1) * per))
        if product is not None:
            m = dec(product)
            for gi in own:
                base = (gi - page * per) * (lanes + 1)
                c = (m >> ((base + lanes) * bits)) & mask
                counts[gi] += c
                sums[gi] += sum((m >> ((base + k) * bits)) & mask for k in range(lanes)) - c  # lanes held value - offset + 1
        for ct, lo, hi in edges:
            m = dec(ct)
            for gi in own:
                for k in range(lo, hi):
                    v = (m >> (((gi - page * per) * (lanes + 1) + k) * bits)) & mask
                    if v:  # 0 = this row is in another group
                        sums[gi], counts[gi] = sums[gi] + v - 1, counts[gi] + 1
    return {g: (s + column['offset'] * c, c) for g, s, c in zip(labels, sums, counts) if c}


class BatchedAggregator:
    """SUM / COUNT / AVG over non-negative integers using packed ciphertexts."""

    def __init__(self, public_key: PaillierPublicKey, private_key: PaillierPrivateKey,
                 encrypt_batch: Optional[Callable[[List[int]], List[int]]] = None, mac: Optional[ColumnMac] = None):
        """With mac, every plaintext also gets an integrity tag (see agniya.core.integrity)."""
        self.mac, self.reserve = mac, RESERVE if mac else 0
        self.public_key = public_key
        self.private_key = private_key
        self.packer = BatchPacker(slot_size_bits=32, max_slots=32)
        self.batch_ops = BatchOperations(public_key, self.packer)
        self.batch_size = self.batch_ops.batch_size  # low-level default; sum_values sizes slots itself
        self.encrypt_batch = encrypt_batch or (lambda ms: [encrypt(public_key, m) for m in ms])

    def _encrypt(self, plain: List[int], pages: int = 1) -> List[int]:
        return self.encrypt_batch(self.mac.tag(plain, pages) if self.mac else plain)

    def layout(self, max_value: int, count: int) -> Tuple[int, int]:
        """(slot_bits, slots) such that no slot can overflow when all `count` values are summed."""
        usable = self.public_key.n.bit_length() - 1 - self.reserve  # packed plaintext stays < n
        slots = max(1, usable // (max(max_value, 1).bit_length() + 1))
        while True:
            per_slot = -(-count // slots)  # ceil
            bits = max(max_value, 1).bit_length() + per_slot.bit_length()  # sum < 2^bits
            if slots * bits <= usable:
                return bits, slots
            if slots == 1:
                raise ValueError("Sum of values does not fit in one plaintext; use a larger key")
            slots -= 1

    def encrypt_column(self, values: List[int]) -> Dict:
        """Encrypt a column of ints into packed ciphertexts (negatives handled by a public offset)."""
        if any(not isinstance(v, int) for v in values):
            raise ValueError("Packed columns hold integers only (scale decimals first)")
        offset = min(0, min(values, default=0))
        shifted = [v - offset for v in values]
        bits, slots = self.layout(max(shifted, default=0), len(shifted))
        packed = []
        for i in range(0, len(shifted), slots):
            acc = 0
            for j, v in enumerate(shifted[i:i + slots]):
                acc |= v << (j * bits)
            packed.append(acc)
        return {'ciphertexts': self._encrypt(packed), 'slot_bits': bits,
                'slots': slots, 'count': len(values), 'offset': offset}

    def sum_column(self, column: Dict) -> int:
        """Homomorphic sum of a packed column: one ciphertext product, one decryption."""
        if not column['ciphertexts']:
            return 0
        ct = sum_ciphertexts(self.public_key, column['ciphertexts'])
        packed_sum = decrypt_crt(self.public_key, self.private_key, ct)
        bits, mask = column['slot_bits'], (1 << column['slot_bits']) - 1
        slot_total = sum((packed_sum >> (k * bits)) & mask for k in range(column['slots']))
        return slot_total + column['offset'] * column['count']

    def sum_range(self, column: Dict, i: int, j: int) -> int:
        """Sum of values i..j-1 (in column order). See range_plan for who sees what."""
        i, j = max(i, 0), min(j, column['count'])
        if i >= j:
            return 0
        product, edges = range_plan(self.public_key, column['ciphertexts'], column['slots'], column['count'], i, j)
        return decrypt_range(self.public_key, self.private_key, product, edges, column['slot_bits'],
                             column['slots']) + column['offset'] * (j - i)

    def encrypt_groups(self, values: List[int], groups: List) -> Dict:
        """Pack `values` for GROUP BY `groups` (one label per value, no missing ones): row r of group
        g goes to ciphertext r // lanes of g's page, lane r % lanes of g's block; each block also
        counts its rows. Every page has as many ciphertexts (the biggest group's rows / lanes), so
        whoever holds only the ciphertexts learns the slot layout, the number of pages and that
        size, not the labels or the other group sizes."""
        if any(not isinstance(v, int) for v in values):
            raise ValueError("Packed columns hold integers only (scale decimals first)")
        groups = [g.item() if hasattr(g, 'item') else g for g in groups]  # numpy scalars -> JSON-able
        if len(groups) != len(values):
            raise ValueError("One group label per value")
        labels = sorted(set(groups))
        offset = min(0, min(values, default=0))
        rows = {g: [] for g in labels}
        for v, g in zip(values, groups):
            rows[g].append(v - offset)
        bits, lanes, per = group_layout(self.public_key, max(values, default=0) - offset, [len(r) for r in rows.values()],
                                        reserve=self.reserve)
        m = max(1, -(-max((len(r) for r in rows.values()), default=0) // lanes))
        pages = max(1, -(-len(labels) // per))
        plain = [0] * (pages * m)
        for gi, g in enumerate(labels):
            page, base = divmod(gi, per)
            first, base = page * m, base * (lanes + 1)
            for r, v in enumerate(rows[g]):
                c, lane = divmod(r, lanes)
                plain[first + c] |= v << ((base + lane) * bits)
            for c in range(m):
                plain[first + c] |= min(lanes, max(0, len(rows[g]) - c * lanes)) << ((base + lanes) * bits)
        return {'ciphertexts': self._encrypt(plain, pages), 'slot_bits': bits, 'lanes': lanes, 'pages': pages,
                'slots': per * (lanes + 1), 'labels': labels, 'offset': offset}

    def encrypt_sorted_groups(self, values: List[int], groups: List) -> Dict:
        """GROUP BY packing that keeps the row order given (sorted by a filter column), so a range of
        rows is a run of ciphertexts, as in encrypt_column: row r goes to ciphertext r // lanes, lane
        r % lanes of its group's block, holding value - offset + 1 (0 marks a lane of another group).
        Each page of groups has its own len(values) / lanes ciphertexts (lanes of other pages' groups
        stay 0). Store a page with slots=lanes and count=len(values); range_plan cuts it like any column."""
        if any(not isinstance(v, int) for v in values):
            raise ValueError("Packed columns hold integers only (scale decimals first)")
        groups = [g.item() if hasattr(g, 'item') else g for g in groups]
        if len(groups) != len(values) or not values:
            raise ValueError("One group label per value, and at least one value")
        labels = sorted(set(groups))
        index = {g: i for i, g in enumerate(labels)}
        offset = min(0, min(values))
        bits, lanes, per = group_layout(self.public_key, max(values) - offset + 1, [len(values)] * len(labels),
                                       decryptions_per_page=3, reserve=self.reserve)  # the product and <=2 edges
        m = -(-len(values) // lanes)
        pages = -(-len(labels) // per)
        plain = [0] * (pages * m)
        for r, (v, g) in enumerate(zip(values, groups)):
            c, lane = divmod(r, lanes)
            page, base = divmod(index[g], per)
            base *= lanes + 1
            plain[page * m + c] += ((v - offset + 1) << ((base + lane) * bits)) + (1 << ((base + lanes) * bits))
        return {'ciphertexts': self._encrypt(plain, pages), 'slot_bits': bits, 'lanes': lanes, 'pages': pages,
                'slots': per * (lanes + 1), 'labels': labels, 'offset': offset, 'count': len(values)}

    def sum_groups(self, column: Dict) -> Dict:
        """{label: (sum, count)} for a column from encrypt_groups: one product and decryption per page."""
        if not column['labels']:
            return {}
        return decrypt_groups(self.public_key, self.private_key,
                              [sum_ciphertexts(self.public_key, cts) for cts in group_pages(column)], column)

    def sum_values(self, values: List[int]) -> int:
        if not values:
            return 0
        return self.sum_column(self.encrypt_column(list(values)))

    def count_matching(self, values: List[int], target: int) -> int:
        return self.sum_values([1 if v == target else 0 for v in values])

    def average_values(self, values: List[int]) -> float:
        return self.sum_values(values) / len(values) if values else 0.0


def demonstrate_batch_packing():
    """Demonstrate batch packing performance benefits."""
    from agniya.core.paillier import generate_keypair
    import time
    
    print("=" * 70)
    print("Batch Packing Demonstration (Patent Innovation)")
    print("=" * 70)
    
    # Generate keys
    print("\nGenerating 2048-bit keys...")
    pub, priv = generate_keypair(2048)
    
    # Create batch aggregator
    aggregator = BatchedAggregator(pub, priv)
    
    print(f"Key size: {pub.bit_length}-bit")
    print(f"Batch size: {aggregator.batch_size} values per ciphertext")
    
    # Test dataset: 1000 small values
    values = list(range(100, 1100))  # 100, 101, ..., 1099
    n = len(values)
    
    print(f"\nDataset: {n} values")
    print(f"Expected sum: {sum(values)}")
    
    # Traditional approach: encrypt each value separately
    print("\n" + "-" * 70)
    print("Traditional Approach (Individual Encryption)")
    print("-" * 70)
    
    start = time.time()
    encrypted_individual = [encrypt(pub, v) for v in values]
    
    # Sum homomorphically
    result_ct = encrypted_individual[0]
    for ct in encrypted_individual[1:]:
        result_ct = (result_ct * ct) % pub.n_squared
    
    result_trad = decrypt(pub, priv, result_ct)
    time_trad = time.time() - start
    
    print(f"Time: {time_trad*1000:.2f} ms")
    print(f"Result: {result_trad}")
    print(f"Correct: {result_trad == sum(values)}")
    
    # Batched approach
    print("\n" + "-" * 70)
    print("Batched Approach (Packed Encryption)")
    print("-" * 70)
    
    start = time.time()
    result_batch = aggregator.sum_values(values)
    time_batch = time.time() - start
    
    print(f"Time: {time_batch*1000:.2f} ms")
    print(f"Result: {result_batch}")
    print(f"Correct: {result_batch == sum(values)}")
    
    # Comparison
    print("\n" + "=" * 70)
    print("PERFORMANCE COMPARISON")
    print("=" * 70)
    print(f"Traditional: {time_trad*1000:.2f} ms")
    print(f"Batched:     {time_batch*1000:.2f} ms")
    print(f"Speedup:     {time_trad/time_batch:.2f}x ✅")
    print(f"")
    print(f"Encryptions saved: {n} → {(n + aggregator.batch_size - 1) // aggregator.batch_size}")
    print(f"Reduction factor:  {aggregator.batch_size}x")
    print("=" * 70)


if __name__ == "__main__":
    demonstrate_batch_packing()
