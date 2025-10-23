"""
Tests for Paillier cryptosystem with adaptive bit-length optimization.
"""

import pytest
import numpy as np
from agniya.core.paillier import (
    generate_keypair, encrypt, decrypt, decrypt_crt,
    homomorphic_add, homomorphic_multiply,
    PaillierCryptosystem, AdaptiveKeySelector
)


class TestKeyGeneration:
    """Test key generation functionality."""
    
    def test_generate_keypair_1024(self):
        """Test 1024-bit key generation."""
        pub, priv = generate_keypair(1024)
        
        assert pub.bit_length == 1024
        assert pub.n.bit_length() >= 1020  # Allow small deviation
        assert pub.n.bit_length() <= 1030
        assert pub.g == pub.n + 1
        assert pub.n_squared == pub.n * pub.n
    
    def test_generate_keypair_2048(self):
        """Test 2048-bit key generation."""
        pub, priv = generate_keypair(2048)
        
        assert pub.bit_length == 2048
        assert pub.n.bit_length() >= 2045
        assert pub.n.bit_length() <= 2055
    
    def test_keypair_components(self):
        """Test that keypair has all required components."""
        pub, priv = generate_keypair(1024)
        
        # Public key
        assert pub.n > 0
        assert pub.g > 0
        assert pub.n_squared > 0
        
        # Private key
        assert priv.lambda_n > 0
        assert priv.mu > 0
        assert priv.p > 0
        assert priv.q > 0
        assert priv.p != priv.q
        assert priv.p * priv.q == pub.n


class TestEncryptionDecryption:
    """Test basic encryption and decryption."""
    
    @pytest.fixture
    def keypair(self):
        """Generate a keypair for testing."""
        return generate_keypair(1024)
    
    def test_encrypt_decrypt_zero(self, keypair):
        """Test encrypting and decrypting zero."""
        pub, priv = keypair
        
        plaintext = 0
        ciphertext = encrypt(pub, plaintext)
        decrypted = decrypt(pub, priv, ciphertext)
        
        assert decrypted == plaintext
    
    def test_encrypt_decrypt_small_number(self, keypair):
        """Test encrypting and decrypting small number."""
        pub, priv = keypair
        
        plaintext = 42
        ciphertext = encrypt(pub, plaintext)
        decrypted = decrypt(pub, priv, ciphertext)
        
        assert decrypted == plaintext
    
    def test_encrypt_decrypt_large_number(self, keypair):
        """Test encrypting and decrypting large number."""
        pub, priv = keypair
        
        plaintext = 123456789012345
        ciphertext = encrypt(pub, plaintext)
        decrypted = decrypt(pub, priv, ciphertext)
        
        assert decrypted == plaintext
    
    def test_encrypt_different_ciphertexts(self, keypair):
        """Test that same plaintext produces different ciphertexts (probabilistic)."""
        pub, priv = keypair
        
        plaintext = 100
        ct1 = encrypt(pub, plaintext)
        ct2 = encrypt(pub, plaintext)
        
        # Ciphertexts should differ (probabilistic encryption)
        assert ct1 != ct2
        
        # But both should decrypt to same value
        assert decrypt(pub, priv, ct1) == plaintext
        assert decrypt(pub, priv, ct2) == plaintext
    
    def test_encrypt_invalid_range(self, keypair):
        """Test that encrypting out-of-range value raises error."""
        pub, priv = keypair
        
        with pytest.raises(ValueError):
            encrypt(pub, -1)  # Negative number
        
        with pytest.raises(ValueError):
            encrypt(pub, pub.n)  # >= n


class TestCRTDecryption:
    """Test CRT-optimized decryption."""
    
    @pytest.fixture
    def keypair(self):
        return generate_keypair(1024)
    
    def test_crt_decrypt_matches_standard(self, keypair):
        """Test that CRT decryption matches standard decryption."""
        pub, priv = keypair
        
        for plaintext in [0, 1, 42, 999, 123456]:
            ciphertext = encrypt(pub, plaintext)
            
            standard = decrypt(pub, priv, ciphertext)
            crt = decrypt_crt(pub, priv, ciphertext)
            
            assert standard == crt == plaintext
    
    def test_crt_decrypt_multiple_values(self, keypair):
        """Test CRT decryption on multiple values."""
        pub, priv = keypair
        
        plaintexts = [10, 20, 30, 40, 50]
        
        for pt in plaintexts:
            ct = encrypt(pub, pt)
            assert decrypt_crt(pub, priv, ct) == pt


class TestHomomorphicOperations:
    """Test homomorphic properties."""
    
    @pytest.fixture
    def keypair(self):
        return generate_keypair(1024)
    
    def test_homomorphic_addition(self, keypair):
        """Test E(m1) * E(m2) = E(m1 + m2)."""
        pub, priv = keypair
        
        m1, m2 = 15, 27
        
        ct1 = encrypt(pub, m1)
        ct2 = encrypt(pub, m2)
        
        ct_sum = homomorphic_add(pub, ct1, ct2)
        decrypted_sum = decrypt(pub, priv, ct_sum)
        
        assert decrypted_sum == m1 + m2
    
    def test_homomorphic_addition_multiple(self, keypair):
        """Test adding multiple encrypted values."""
        pub, priv = keypair
        
        values = [5, 10, 15, 20, 25]
        ciphertexts = [encrypt(pub, v) for v in values]
        
        # Sum all ciphertexts
        ct_sum = ciphertexts[0]
        for ct in ciphertexts[1:]:
            ct_sum = homomorphic_add(pub, ct_sum, ct)
        
        decrypted_sum = decrypt(pub, priv, ct_sum)
        
        assert decrypted_sum == sum(values)
    
    def test_homomorphic_scalar_multiplication(self, keypair):
        """Test E(m)^k = E(k * m)."""
        pub, priv = keypair
        
        m, k = 7, 5
        
        ct = encrypt(pub, m)
        ct_mult = homomorphic_multiply(pub, ct, k)
        decrypted = decrypt(pub, priv, ct_mult)
        
        assert decrypted == m * k
    
    def test_homomorphic_scalar_multiplication_zero(self, keypair):
        """Test multiplication by zero."""
        pub, priv = keypair
        
        m = 100
        ct = encrypt(pub, m)
        ct_zero = homomorphic_multiply(pub, ct, 0)
        decrypted = decrypt(pub, priv, ct_zero)
        
        assert decrypted == 0
    
    def test_homomorphic_scalar_multiplication_one(self, keypair):
        """Test multiplication by one."""
        pub, priv = keypair
        
        m = 42
        ct = encrypt(pub, m)
        ct_same = homomorphic_multiply(pub, ct, 1)
        decrypted = decrypt(pub, priv, ct_same)
        
        assert decrypted == m
    
    def test_combined_operations(self, keypair):
        """Test combination of addition and multiplication."""
        pub, priv = keypair
        
        # Compute: (5 * 3) + (10 * 2) = 15 + 20 = 35
        ct1 = encrypt(pub, 5)
        ct2 = encrypt(pub, 10)
        
        ct1_mult = homomorphic_multiply(pub, ct1, 3)
        ct2_mult = homomorphic_multiply(pub, ct2, 2)
        
        ct_sum = homomorphic_add(pub, ct1_mult, ct2_mult)
        result = decrypt(pub, priv, ct_sum)
        
        assert result == 35


class TestAdaptiveKeySelector:
    """Test adaptive key size selection."""
    
    def test_small_values_512bit(self):
        """Test that small values recommend 512-bit keys."""
        values = [10, 20, 30, 100, 255]  # All fit in 8-bit
        
        analysis = AdaptiveKeySelector.analyze_dataset(values)
        
        # Small values should recommend 512 or 1024-bit
        assert analysis['recommended_key_size'] <= 1024
        assert analysis['abs_max'] == 255
    
    def test_medium_values_1024bit(self):
        """Test that medium values recommend 1024-bit keys."""
        values = [10000, 50000, 100000, 1000000]  # Up to 1 million
        
        analysis = AdaptiveKeySelector.analyze_dataset(values)
        
        assert analysis['recommended_key_size'] == 1024
    
    def test_large_values_2048bit(self):
        """Test that large values recommend 2048-bit keys."""
        values = [2**40, 2**50, 2**60]  # Very large values
        
        analysis = AdaptiveKeySelector.analyze_dataset(values)
        
        assert analysis['recommended_key_size'] == 2048
    
    def test_min_security_override(self):
        """Test that min_security is respected."""
        values = [10, 20, 30]  # Would normally suggest 512-bit
        
        key_size = AdaptiveKeySelector.select_key_size(max(values), min_security=1024)
        
        assert key_size == 1024  # Enforced minimum
    
    def test_storage_reduction_calculation(self):
        """Test storage reduction calculation."""
        values = [100, 200, 300]  # Should recommend smaller key
        
        analysis = AdaptiveKeySelector.analyze_dataset(values)
        
        # Should show some storage reduction vs 2048-bit default
        assert analysis['storage_reduction_percent'] >= 0
        assert analysis['recommended_key_size'] < analysis['default_key_size']


class TestPaillierCryptosystem:
    """Test high-level PaillierCryptosystem interface."""
    
    def test_init_default(self):
        """Test default initialization."""
        crypto = PaillierCryptosystem()
        
        assert crypto.bit_length == 2048
        assert crypto.public_key.bit_length == 2048
    
    def test_init_custom_size(self):
        """Test custom key size."""
        crypto = PaillierCryptosystem(bit_length=1024)
        
        assert crypto.bit_length == 1024
    
    def test_from_dataset_small_values(self):
        """Test creating system from small value dataset."""
        dataset = [65, 72, 80, 98, 105, 120]  # Heart rates
        
        crypto = PaillierCryptosystem.from_dataset(dataset, min_security=512)
        
        # Should select small key size for small values
        assert crypto.bit_length <= 1024
    
    def test_encrypt_decrypt_interface(self):
        """Test high-level encrypt/decrypt interface."""
        crypto = PaillierCryptosystem(1024)
        
        plaintext = 42
        ciphertext = crypto.encrypt(plaintext)
        decrypted = crypto.decrypt(ciphertext)
        
        assert decrypted == plaintext
    
    def test_decrypt_with_without_crt(self):
        """Test that both decryption methods work."""
        crypto = PaillierCryptosystem(1024)
        
        plaintext = 123
        ciphertext = crypto.encrypt(plaintext)
        
        decrypted_crt = crypto.decrypt(ciphertext, use_crt=True)
        decrypted_standard = crypto.decrypt(ciphertext, use_crt=False)
        
        assert decrypted_crt == plaintext
        assert decrypted_standard == plaintext
    
    def test_homomorphic_add_interface(self):
        """Test high-level homomorphic addition."""
        crypto = PaillierCryptosystem(1024)
        
        ct1 = crypto.encrypt(10)
        ct2 = crypto.encrypt(20)
        ct_sum = crypto.add(ct1, ct2)
        
        assert crypto.decrypt(ct_sum) == 30
    
    def test_homomorphic_multiply_interface(self):
        """Test high-level homomorphic multiplication."""
        crypto = PaillierCryptosystem(1024)
        
        ct = crypto.encrypt(7)
        ct_mult = crypto.multiply(ct, 6)
        
        assert crypto.decrypt(ct_mult) == 42
    
    def test_sum_encrypted_empty(self):
        """Test sum of empty list."""
        crypto = PaillierCryptosystem(1024)
        
        result = crypto.sum_encrypted([])
        assert crypto.decrypt(result) == 0
    
    def test_sum_encrypted_single(self):
        """Test sum of single value."""
        crypto = PaillierCryptosystem(1024)
        
        ct = crypto.encrypt(42)
        result = crypto.sum_encrypted([ct])
        
        assert crypto.decrypt(result) == 42
    
    def test_sum_encrypted_multiple(self):
        """Test sum of multiple values."""
        crypto = PaillierCryptosystem(1024)
        
        values = [10, 20, 30, 40, 50]
        ciphertexts = [crypto.encrypt(v) for v in values]
        
        ct_sum = crypto.sum_encrypted(ciphertexts)
        
        assert crypto.decrypt(ct_sum) == sum(values)


class TestRealWorldScenarios:
    """Test realistic use cases."""
    
    def test_healthcare_vital_signs(self):
        """Test with realistic healthcare data."""
        crypto = PaillierCryptosystem(1024)
        
        # Heart rates from multiple patients
        heart_rates = [65, 72, 80, 68, 95, 88, 76]
        
        encrypted = [crypto.encrypt(hr) for hr in heart_rates]
        encrypted_sum = crypto.sum_encrypted(encrypted)
        
        avg_encrypted = crypto.multiply(encrypted_sum, 1)  # Just for testing
        decrypted_sum = crypto.decrypt(encrypted_sum)
        
        assert decrypted_sum == sum(heart_rates)
    
    def test_financial_salaries(self):
        """Test with financial data (salaries in cents)."""
        crypto = PaillierCryptosystem(2048)
        
        # Salaries in cents: $50K, $75K, $100K
        salaries = [5000000, 7500000, 10000000]
        
        encrypted = [crypto.encrypt(s) for s in salaries]
        total_encrypted = crypto.sum_encrypted(encrypted)
        
        total = crypto.decrypt(total_encrypted)
        
        assert total == sum(salaries)
    
    def test_sensor_readings(self):
        """Test with IoT sensor data."""
        crypto = PaillierCryptosystem(1024)
        
        # Temperature readings in tenths of degrees
        temperatures = [200, 215, 225, 210, 205, 220]  # 20.0°C to 22.5°C
        
        encrypted = [crypto.encrypt(t) for t in temperatures]
        sum_encrypted = crypto.sum_encrypted(encrypted)
        
        total = crypto.decrypt(sum_encrypted)
        
        assert total == sum(temperatures)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
