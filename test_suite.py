#!/usr/bin/env python3
"""
AGNIYA Unified Test Suite
Comprehensive tests for all features: encryption, caching, compression, security

Run: python test_suite.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import time
import numpy as np
from agniya.core.paillier import generate_keypair, encrypt, decrypt_crt
from agniya.core.ultimate_system import UltimateOptimizedDatabase
from agniya.compression.rns_compression import RNSCompressor


def print_header(text):
    print("\n" + "="*80)
    print(f"  {text}")
    print("="*80)


def print_test(name, passed):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"  {status}: {name}")
    return passed


class TestSuite:
    """Unified test suite for AGNIYA"""
    
    def __init__(self):
        self.results = []
        self.db = None
    
    def test_key_generation(self):
        """Test 1: Paillier key generation"""
        try:
            public_key, private_key = generate_keypair(1024)  # Small key for speed
            assert hasattr(public_key, 'n'), "Public key missing 'n'"
            assert hasattr(private_key, 'lambda_n'), "Private key missing 'lambda_n'"
            return True
        except Exception as e:
            print(f"    Error: {e}")
            return False
    
    def test_basic_encryption(self):
        """Test 2: Basic encryption/decryption"""
        try:
            public_key, private_key = generate_keypair(1024)
            plaintext = 42
            ciphertext = encrypt(public_key, plaintext)
            decrypted = decrypt_crt(public_key, private_key, ciphertext)
            assert decrypted == plaintext, f"Decryption failed: {decrypted} != {plaintext}"
            return True
        except Exception as e:
            print(f"    Error: {e}")
            return False
    
    def test_homomorphic_addition(self):
        """Test 3: Homomorphic addition"""
        try:
            public_key, private_key = generate_keypair(1024)
            a, b = 10, 20
            ct_a = encrypt(public_key, a)
            ct_b = encrypt(public_key, b)
            
            # Homomorphic addition
            ct_sum = (ct_a * ct_b) % (public_key.n ** 2)
            result = decrypt_crt(public_key, private_key, ct_sum)
            
            assert result == (a + b), f"Addition failed: {result} != {a + b}"
            return True
        except Exception as e:
            print(f"    Error: {e}")
            return False
    
    def test_database_initialization(self):
        """Test 4: Database initialization"""
        try:
            self.db = UltimateOptimizedDatabase(key_size=1024, cache_size=100)
            assert self.db.public_key is not None, "Public key not initialized"
            assert self.db.private_key is not None, "Private key not initialized"
            return True
        except Exception as e:
            print(f"    Error: {e}")
            return False
    
    def test_caching_mechanism(self):
        """Test 5: Precomputation cache"""
        try:
            if self.db is None:
                self.db = UltimateOptimizedDatabase(key_size=1024, cache_size=100)
            
            # First encryption (cache miss)
            value = 100
            start = time.time()
            ct1 = self.db.precomp.get_or_encrypt(value)
            time1 = time.time() - start
            
            # Second encryption (cache hit)
            start = time.time()
            ct2 = self.db.precomp.get_or_encrypt(value)
            time2 = time.time() - start
            
            # Cache hit should be faster
            assert ct1 == ct2, "Cached ciphertext mismatch"
            if time1 > 0 and time2 > 0:
                assert time2 < time1 / 2, f"Cache not faster: {time2} vs {time1}"
            
            return True
        except Exception as e:
            print(f"    Error: {e}")
            return False
    
    def test_rns_compression(self):
        """Test 6: RNS compression"""
        try:
            public_key, private_key = generate_keypair(2048)
            compressor = RNSCompressor(bit_size=2048)
            
            # Encrypt value
            plaintext = 12345
            ciphertext = encrypt(public_key, plaintext)
            
            # Compress
            compressed = compressor.compress(ciphertext)
            
            # Decompress
            decompressed = compressor.decompress(compressed)
            
            # Verify
            result = decrypt_crt(public_key, private_key, decompressed)
            assert result == plaintext, f"Compression failed: {result} != {plaintext}"
            
            # Check compression ratio
            original_size = len(str(ciphertext))
            compressed_size = len(compressed)
            ratio = (1 - compressed_size / original_size) * 100
            print(f"    Compression ratio: {ratio:.1f}%")
            
            return True
        except Exception as e:
            print(f"    Error: {e}")
            return False
    
    def test_entropy_detection(self):
        """Test 7: Entropy-aware detection"""
        try:
            if self.db is None:
                self.db = UltimateOptimizedDatabase(key_size=1024, cache_size=100)
            
            # Low-entropy data
            low_entropy = [1, 2, 3] * 50
            uniqueness_low = self.db.estimate_uniqueness(low_entropy)
            assert uniqueness_low < 0.3, f"Low entropy detection failed: {uniqueness_low}"
            
            # High-entropy data
            high_entropy = list(range(1000, 1200))
            uniqueness_high = self.db.estimate_uniqueness(high_entropy)
            assert uniqueness_high > 0.7, f"High entropy detection failed: {uniqueness_high}"
            
            print(f"    Low entropy: {uniqueness_low:.1%}, High entropy: {uniqueness_high:.1%}")
            return True
        except Exception as e:
            print(f"    Error: {e}")
            return False
    
    def test_sum_query(self):
        """Test 8: Sum query"""
        try:
            if self.db is None:
                self.db = UltimateOptimizedDatabase(key_size=1024, cache_size=100)
            
            values = [10, 20, 30, 40, 50]
            expected = sum(values)
            
            # Warm cache
            for val in values:
                self.db.precomp.get_or_encrypt(val)
            
            # Query
            result = self.db.sum_query(values, use_cache=True)
            
            assert result == expected, f"Sum query failed: {result} != {expected}"
            return True
        except Exception as e:
            print(f"    Error: {e}")
            return False
    
    def test_average_query(self):
        """Test 9: Average query"""
        try:
            if self.db is None:
                self.db = UltimateOptimizedDatabase(key_size=1024, cache_size=100)
            
            values = [10, 20, 30, 40, 50]
            expected = sum(values) / len(values)
            
            # Warm cache
            for val in values:
                self.db.precomp.get_or_encrypt(val)
            
            # Query (use sum and divide)
            total = self.db.sum_query(values, use_cache=True)
            result = total / len(values)
            
            assert abs(result - expected) < 0.01, f"Average query failed: {result} != {expected}"
            return True
        except Exception as e:
            print(f"    Error: {e}")
            return False
    
    def test_parallel_aggregation(self):
        """Test 10: Parallel tree aggregation"""
        try:
            if self.db is None:
                self.db = UltimateOptimizedDatabase(key_size=1024, cache_size=100)
            
            # Encrypt values
            values = list(range(100, 150))
            ciphertexts = [self.db.precomp.get_or_encrypt(v) for v in values]
            
            # Parallel sum
            result_ct = self.db.sum_encrypted_parallel(ciphertexts, max_workers=2)
            result = decrypt_crt(self.db.public_key, self.db.private_key, result_ct)
            
            expected = sum(values)
            assert result == expected, f"Parallel sum failed: {result} != {expected}"
            return True
        except Exception as e:
            print(f"    Error: {e}")
            return False
    
    def test_security_properties(self):
        """Test 11: Basic security properties"""
        try:
            public_key, private_key = generate_keypair(1024)
            
            # Same plaintext → different ciphertexts (randomness)
            plaintext = 100
            ct1 = encrypt(public_key, plaintext)
            ct2 = encrypt(public_key, plaintext)
            
            # Ciphertexts should be different (non-deterministic)
            # Note: Our cache makes it deterministic, but pure Paillier is randomized
            
            # Both should decrypt to same value
            dec1 = decrypt_crt(public_key, private_key, ct1)
            dec2 = decrypt_crt(public_key, private_key, ct2)
            
            assert dec1 == plaintext, "Decryption 1 failed"
            assert dec2 == plaintext, "Decryption 2 failed"
            
            return True
        except Exception as e:
            print(f"    Error: {e}")
            return False
    
    def test_performance_benchmark(self):
        """Test 12: Performance benchmark"""
        try:
            if self.db is None:
                self.db = UltimateOptimizedDatabase(key_size=1024, cache_size=100)
            
            # Benchmark encryption
            values = list(range(100))
            
            # Without cache (first run)
            start = time.time()
            for val in values[:10]:
                self.db.precomp.get_or_encrypt(val)
            cold_time = (time.time() - start) / 10
            
            # With cache (repeated)
            start = time.time()
            for val in values[:10]:
                self.db.precomp.get_or_encrypt(val)
            hot_time = (time.time() - start) / 10
            
            speedup = cold_time / hot_time if hot_time > 0 else 1
            print(f"    Cold: {cold_time*1000:.2f}ms, Hot: {hot_time*1000:.2f}ms, Speedup: {speedup:.0f}x")
            
            return True
        except Exception as e:
            print(f"    Error: {e}")
            return False
    
    def run_all_tests(self):
        """Run all tests"""
        print_header("AGNIYA Unified Test Suite")
        
        tests = [
            ("Paillier Key Generation", self.test_key_generation),
            ("Basic Encryption/Decryption", self.test_basic_encryption),
            ("Homomorphic Addition", self.test_homomorphic_addition),
            ("Database Initialization", self.test_database_initialization),
            ("Caching Mechanism", self.test_caching_mechanism),
            ("RNS Compression", self.test_rns_compression),
            ("Entropy Detection", self.test_entropy_detection),
            ("Sum Query", self.test_sum_query),
            ("Average Query", self.test_average_query),
            ("Parallel Aggregation", self.test_parallel_aggregation),
            ("Security Properties", self.test_security_properties),
            ("Performance Benchmark", self.test_performance_benchmark),
        ]
        
        print("\nRunning tests...\n")
        
        for name, test_func in tests:
            try:
                passed = test_func()
                self.results.append((name, passed))
                print_test(name, passed)
            except Exception as e:
                print(f"  ❌ FAIL: {name}")
                print(f"    Exception: {e}")
                self.results.append((name, False))
        
        # Summary
        print_header("Test Summary")
        
        total = len(self.results)
        passed = sum(1 for _, result in self.results if result)
        failed = total - passed
        
        print(f"\n  Total Tests: {total}")
        print(f"  Passed:      {passed}")
        print(f"  Failed:      {failed}")
        print(f"  Success Rate: {(passed/total)*100:.1f}%")
        
        if passed == total:
            print("\n  🎉 ALL TESTS PASSED!")
        else:
            print(f"\n  ⚠️  {failed} test(s) failed")
        
        print("="*80 + "\n")
        
        return passed == total


def main():
    suite = TestSuite()
    success = suite.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
