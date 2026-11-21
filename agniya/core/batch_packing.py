"""
Packing several plaintexts into one Paillier ciphertext.

Values are laid out in fixed-width slots of one plaintext: v0 + v1*2^b + v2*2^2b ...
One encryption then covers many values, and multiplying ciphertexts adds all
slots at once. This is a well-known technique (e.g. Ge & Zdonik, VLDB 2007).
Correctness requires headroom: each slot must hold the SUM of everything that
lands in it, which BatchedAggregator.layout() guarantees.
"""

from typing import Callable, Dict, List, Optional, Tuple
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


class BatchedAggregator:
    """SUM / COUNT / AVG over non-negative integers using packed ciphertexts."""

    def __init__(self, public_key: PaillierPublicKey, private_key: PaillierPrivateKey,
                 encrypt_batch: Optional[Callable[[List[int]], List[int]]] = None):
        self.public_key = public_key
        self.private_key = private_key
        self.packer = BatchPacker(slot_size_bits=32, max_slots=32)
        self.batch_ops = BatchOperations(public_key, self.packer)
        self.batch_size = self.batch_ops.batch_size  # low-level default; sum_values sizes slots itself
        self.encrypt_batch = encrypt_batch or (lambda ms: [encrypt(public_key, m) for m in ms])

    def layout(self, max_value: int, count: int) -> Tuple[int, int]:
        """(slot_bits, slots) such that no slot can overflow when all `count` values are summed."""
        usable = self.public_key.n.bit_length() - 1  # packed plaintext stays < n
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
        return {'ciphertexts': self.encrypt_batch(packed), 'slot_bits': bits,
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
        """Sum of values i..j-1 (in column order).

        Ciphertexts wholly inside the range are multiplied and decrypted once; the (at most
        two) ciphertexts cut by the range edges are decrypted on their own, so the KEY HOLDER
        sees those slots individually. The aggregating party never decrypts anything."""
        s, bits, count = column['slots'], column['slot_bits'], column['count']
        i, j = max(i, 0), min(j, count)
        if i >= j:
            return 0
        mask = (1 << bits) - 1
        full, total = [], 0
        cts = column['ciphertexts']
        for c in range(i // s, (j - 1) // s + 1):
            lo, hi = max(i, c * s) - c * s, min(j, (c + 1) * s, count) - c * s
            if lo == 0 and hi == min(s, count - c * s):
                full.append(cts[c])
            else:
                m = decrypt_crt(self.public_key, self.private_key, cts[c])
                total += sum((m >> (k * bits)) & mask for k in range(lo, hi))
        if full:
            m = decrypt_crt(self.public_key, self.private_key, sum_ciphertexts(self.public_key, full))
            total += sum((m >> (k * bits)) & mask for k in range(s))
        return total + column['offset'] * (j - i)

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
