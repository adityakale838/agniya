"""
Tests for Batch Packing optimization.
"""

import pytest
from agniya.core.paillier import generate_keypair
from agniya.core.batch_packing import (
    BatchPacker, BatchOperations, BatchedAggregator
)


class TestBatchPacker:
    """Test basic batch packing/unpacking."""
    
    def test_pack_unpack_single(self):
        """Test packing and unpacking single value."""
        packer = BatchPacker(slot_size_bits=32, max_slots=32)
        
        values = [42]
        packed = packer.pack(values)
        unpacked = packer.unpack(packed, len(values))
        
        assert unpacked == values
    
    def test_pack_unpack_multiple(self):
        """Test packing multiple values."""
        packer = BatchPacker(slot_size_bits=32, max_slots=32)
        
        values = [100, 200, 300, 400]
        packed = packer.pack(values)
        unpacked = packer.unpack(packed, len(values))
        
        assert unpacked == values
    
    def test_pack_max_slots(self):
        """Test packing maximum number of slots."""
        packer = BatchPacker(slot_size_bits=32, max_slots=32)
        
        # Pack 32 values
        values = list(range(32))
        packed = packer.pack(values)
        unpacked = packer.unpack(packed, len(values))
        
        assert unpacked == values
    
    def test_pack_too_many_values(self):
        """Test error when too many values."""
        packer = BatchPacker(slot_size_bits=32, max_slots=32)
        
        values = list(range(33))  # One too many
        
        with pytest.raises(ValueError, match="Too many values"):
            packer.pack(values)
    
    def test_pack_value_too_large(self):
        """Test error when value doesn't fit in slot."""
        packer = BatchPacker(slot_size_bits=32, max_slots=32)
        
        values = [2**32]  # Too large for 32-bit slot
        
        with pytest.raises(ValueError, match="doesn't fit"):
            packer.pack(values)
    
    def test_pack_negative_value(self):
        """Test error on negative values."""
        packer = BatchPacker(slot_size_bits=32, max_slots=32)
        
        values = [-1]
        
        with pytest.raises(ValueError, match="doesn't fit"):
            packer.pack(values)
    
    def test_supports_key_size(self):
        """Test batch size calculation for different key sizes."""
        packer = BatchPacker(slot_size_bits=32, max_slots=32)
        
        # 1024-bit key: 768 safe bits / 32 = 24 slots
        assert packer.supports_key_size(1024) == 24
        
        # 2048-bit key: 1536 safe bits / 32 = 48 slots (capped at max_slots=32)
        assert packer.supports_key_size(2048) == 32
        
        # 4096-bit key: capped at max_slots
        assert packer.supports_key_size(4096) == 32


class TestBatchOperations:
    """Test homomorphic operations on batches."""
    
    @pytest.fixture
    def setup(self):
        """Generate keys and create batch operations."""
        pub, priv = generate_keypair(1024)
        packer = BatchPacker(slot_size_bits=32, max_slots=32)
        batch_ops = BatchOperations(pub, packer)
        
        return pub, priv, packer, batch_ops
    
    def test_encrypt_decrypt_batch(self, setup):
        """Test encrypting and decrypting batch."""
        pub, priv, packer, batch_ops = setup
        
        values = [10, 20, 30]
        
        # Encrypt
        ct = batch_ops.encrypt_batch(values)
        
        # Decrypt
        decrypted = batch_ops.decrypt_batch(priv, ct, len(values))
        
        assert decrypted == values
    
    def test_batch_add(self, setup):
        """Test homomorphic addition of batches."""
        pub, priv, packer, batch_ops = setup
        
        values1 = [10, 20, 30]
        values2 = [5, 15, 25]
        
        # Encrypt both batches
        ct1 = batch_ops.encrypt_batch(values1)
        ct2 = batch_ops.encrypt_batch(values2)
        
        # Homomorphic addition
        ct_sum = batch_ops.batch_add(ct1, ct2)
        
        # Decrypt result
        result = batch_ops.decrypt_batch(priv, ct_sum, len(values1))
        
        expected = [v1 + v2 for v1, v2 in zip(values1, values2)]
        assert result == expected
    
    def test_batch_scalar_multiply(self, setup):
        """Test homomorphic scalar multiplication."""
        pub, priv, packer, batch_ops = setup
        
        values = [10, 20, 30]
        scalar = 3  # Apply same scalar to all values
        
        # Encrypt batch
        ct = batch_ops.encrypt_batch(values)
        
        # Homomorphic scalar multiplication
        ct_mult = batch_ops.batch_scalar_multiply(ct, [scalar])
        
        # Decrypt result
        result = batch_ops.decrypt_batch(priv, ct_mult, len(values))
        
        expected = [v * scalar for v in values]
        assert result == expected
    
    def test_sum_batches(self, setup):
        """Test summing multiple batches."""
        pub, priv, packer, batch_ops = setup
        
        batches_values = [
            [10, 20, 30],
            [5, 10, 15],
            [1, 2, 3]
        ]
        
        # Encrypt all batches
        cts = [batch_ops.encrypt_batch(vals) for vals in batches_values]
        
        # Sum homomorphically
        ct_sum = batch_ops.sum_batches(cts)
        
        # Decrypt result
        result = batch_ops.decrypt_batch(priv, ct_sum, len(batches_values[0]))
        
        expected = [sum(vals[i] for vals in batches_values) 
                   for i in range(len(batches_values[0]))]
        assert result == expected


class TestBatchedAggregator:
    """Test high-level aggregation functions."""
    
    @pytest.fixture
    def setup(self):
        """Generate keys and create aggregator."""
        pub, priv = generate_keypair(1024)
        aggregator = BatchedAggregator(pub, priv)
        return aggregator
    
    def test_sum_values_small(self, setup):
        """Test sum with few values."""
        aggregator = setup
        
        values = [10, 20, 30, 40, 50]
        result = aggregator.sum_values(values)
        
        assert result == sum(values)
    
    def test_sum_values_large(self, setup):
        """Test sum with many values (multiple batches)."""
        aggregator = setup
        
        values = list(range(1, 101))  # 1 to 100
        result = aggregator.sum_values(values)
        
        assert result == sum(values)
    
    def test_sum_values_exact_batch(self, setup):
        """Test sum with values fitting exactly in one batch."""
        aggregator = setup
        
        # Use exactly batch_size values
        values = list(range(aggregator.batch_size))
        result = aggregator.sum_values(values)
        
        assert result == sum(values)
    
    def test_sum_values_empty(self, setup):
        """Test sum of empty list."""
        aggregator = setup
        
        result = aggregator.sum_values([])
        assert result == 0
    
    def test_count_matching(self, setup):
        """Test counting matching values."""
        aggregator = setup
        
        values = [1, 2, 3, 2, 4, 2, 5]
        count = aggregator.count_matching(values, 2)
        
        assert count == 3
    
    def test_count_matching_none(self, setup):
        """Test counting when no matches."""
        aggregator = setup
        
        values = [1, 3, 4, 5]
        count = aggregator.count_matching(values, 2)
        
        assert count == 0
    
    def test_average_values(self, setup):
        """Test computing average."""
        aggregator = setup
        
        values = [10, 20, 30, 40, 50]
        avg = aggregator.average_values(values)
        
        expected = sum(values) / len(values)
        assert avg == expected
    
    def test_average_values_empty(self, setup):
        """Test average of empty list."""
        aggregator = setup
        
        avg = aggregator.average_values([])
        assert avg == 0.0


class TestBatchPerformance:
    """Performance validation tests."""
    
    def test_batch_size_at_different_key_sizes(self):
        """Verify batch sizes scale with key size."""
        packer = BatchPacker(slot_size_bits=32, max_slots=32)
        
        # 1024-bit → 24 slots
        pub1024, _ = generate_keypair(1024)
        batch_ops_1024 = BatchOperations(pub1024, packer)
        assert batch_ops_1024.batch_size == 24
        
        # 2048-bit → 32 slots (capped)
        pub2048, _ = generate_keypair(2048)
        batch_ops_2048 = BatchOperations(pub2048, packer)
        assert batch_ops_2048.batch_size == 32
    
    def test_speedup_calculation(self):
        """Verify theoretical speedup matches implementation."""
        pub, priv = generate_keypair(1024)
        aggregator = BatchedAggregator(pub, priv)
        
        num_values = 1000
        batch_size = aggregator.batch_size
        
        # Traditional: N encryptions
        traditional_ops = num_values
        
        # Batched: ceil(N / batch_size) encryptions
        batched_ops = (num_values + batch_size - 1) // batch_size
        
        speedup = traditional_ops / batched_ops
        
        # Should be close to batch_size
        assert speedup >= batch_size * 0.8  # Allow 20% variance
        
        print(f"\nBatch size: {batch_size}")
        print(f"Traditional ops: {traditional_ops}")
        print(f"Batched ops: {batched_ops}")
        print(f"Theoretical speedup: {speedup:.1f}x")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestPackingHeadroom:
    """Slot sums must never overflow into neighbouring slots."""

    @pytest.fixture(scope="class")
    @classmethod
    def aggregator(cls):
        pub, priv = generate_keypair(2048)
        return BatchedAggregator(pub, priv)

    def test_large_sums_exact(self, aggregator):
        import random
        rng = random.Random(7)
        values = [rng.randint(3_000_000, 15_000_000) for _ in range(5_000)]  # salaries in cents
        assert aggregator.sum_values(values) == sum(values)

    def test_max_values_exact(self, aggregator):
        values = [2**32 - 1] * 3_000  # every slot saturated
        assert aggregator.sum_values(values) == sum(values)

    def test_layout_has_headroom(self, aggregator):
        bits, slots = aggregator.layout(max_value=10**6, count=100_000)
        per_slot = -(-100_000 // slots)
        assert per_slot * 10**6 < 2**bits
        assert slots * bits < aggregator.public_key.n.bit_length()

    def test_negative_values_exact(self, aggregator):
        values = [5, -20, 300, -7, 0] * 50
        assert aggregator.sum_values(values) == sum(values)

    def test_rejects_floats(self, aggregator):
        with pytest.raises(ValueError):
            aggregator.sum_values([1.5, 2.0])

    @pytest.mark.parametrize("k,n,lo,hi", [(1, 50, 0, 10), (4, 1338, -5_000, 640_000_000), (6, 999, 0, 2**32 - 1),
                                           (30, 300, -3, 3), (3, 0, 0, 1)])
    def test_sum_groups_exact(self, aggregator, k, n, lo, hi):
        import random
        rng = random.Random(k * 1000 + n)
        groups = [rng.choice(range(k)) if rng.random() < 0.5 else 0 for _ in range(n)]  # skewed: group 0 is big
        values = [rng.randint(lo, hi) for _ in range(n)]
        col = aggregator.encrypt_groups(values, [f"g{g}" for g in groups])
        want = {}
        for v, g in zip(values, groups):
            s, c = want.get(f"g{g}", (0, 0))
            want[f"g{g}"] = (s + v, c + 1)
        assert aggregator.sum_groups(col) == want
        assert col['slots'] * col['slot_bits'] < aggregator.public_key.n.bit_length()

    def test_too_many_groups(self, aggregator):
        with pytest.raises(ValueError, match="groups do not fit"):
            aggregator.encrypt_groups([2**40] * 2000, list(range(2000)))

    def test_sum_range_exact(self, aggregator):
        import random
        rng = random.Random(11)
        values = sorted(rng.randint(-5_000, 10**9) for _ in range(500))
        col = aggregator.encrypt_column(values)
        s = col['slots']
        cuts = [0, 1, s - 1, s, s + 1, 2 * s, 250, 499, 500, 600]
        for i in cuts:
            for j in cuts:
                assert aggregator.sum_range(col, i, j) == sum(values[max(i, 0):j]), (i, j)
