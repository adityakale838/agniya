"""
Paillier Cryptosystem with Adaptive Bit-Length Optimization

This module implements the Paillier homomorphic encryption scheme with
an innovative adaptive bit-length selection mechanism that optimizes
performance based on data characteristics.

Patent Claim: Dynamic key size selection based on plaintext value ranges,
with automatic parameter adjustment for optimal performance.
"""

import secrets
from typing import Tuple, Optional
from dataclasses import dataclass
import json
from pathlib import Path

from agniya.core.number_theory import (
    generate_prime, gcd, lcm, mod_inverse, carmichael_lambda
)


@dataclass
class PaillierPublicKey:
    """Paillier public key."""
    n: int  # n = p * q
    g: int  # Generator (typically n + 1)
    n_squared: int  # n^2 (precomputed)
    bit_length: int  # Key size in bits
    
    def __repr__(self):
        return f"PaillierPublicKey(bit_length={self.bit_length})"


@dataclass
class PaillierPrivateKey:
    """Paillier private key with CRT optimization support."""
    lambda_n: int  # λ(n) = lcm(p-1, q-1)
    mu: int  # μ = (L(g^λ mod n^2))^(-1) mod n
    
    # CRT optimization parameters
    p: int  # First prime
    q: int  # Second prime
    p_squared: int  # p^2 (precomputed)
    q_squared: int  # q^2 (precomputed)
    hp: int  # h_p for CRT
    hq: int  # h_q for CRT
    
    def __repr__(self):
        return f"PaillierPrivateKey(lambda={self.lambda_n})"


class AdaptiveKeySelector:
    """
    Selects optimal Paillier key size based on data characteristics.
    
    This is a key patent innovation: dynamically choosing encryption
    parameters based on plaintext value ranges to minimize overhead.
    """
    
    # Key size thresholds (bit_length: max_value)
    KEY_THRESHOLDS = {
        512: 2**16,           # Up to 65K (16-bit values)
        1024: 2**48,          # Up to 48-bit values  
        2048: 2**96,          # Up to 96-bit values
        3072: 2**192,         # Very large values
        4096: float('inf')    # Maximum security
    }
    
    @classmethod
    def select_key_size(cls, max_value: int, min_security: int = 1024) -> int:
        """
        Select optimal key size based on maximum plaintext value.
        
        Args:
            max_value: Maximum value that will be encrypted
            min_security: Minimum key size for security (default 1024)
            
        Returns:
            Recommended key size in bits
        """
        for bit_length, threshold in sorted(cls.KEY_THRESHOLDS.items()):
            if bit_length >= min_security and max_value < threshold:
                return bit_length
        
        return 4096  # Maximum if value is very large
    
    @classmethod
    def analyze_dataset(cls, values: list) -> dict:
        """
        Analyze dataset to determine optimal encryption parameters.
        
        Args:
            values: List of integer values
            
        Returns:
            Dictionary with analysis results
        """
        if not values:
            return {'recommended_key_size': 2048, 'reason': 'default'}
        
        min_val = min(values)
        max_val = max(values)
        abs_max = max(abs(min_val), abs(max_val))
        
        recommended = cls.select_key_size(abs_max)
        
        # Calculate potential savings vs. 2048-bit default
        default_size = 2048
        storage_ratio = recommended / default_size
        compute_ratio = (recommended / default_size) ** 2  # Rough estimate
        
        return {
            'min_value': min_val,
            'max_value': max_val,
            'abs_max': abs_max,
            'recommended_key_size': recommended,
            'default_key_size': default_size,
            'storage_reduction_percent': (1 - storage_ratio) * 100,
            'compute_speedup_estimate': 1 / compute_ratio,
            'num_values': len(values)
        }


def generate_keypair(bit_length: int = 2048) -> Tuple[PaillierPublicKey, PaillierPrivateKey]:
    """
    Generate Paillier public and private key pair.
    
    Args:
        bit_length: Bit length of the modulus n (default 2048)
        
    Returns:
        Tuple of (public_key, private_key)
    """
    # Generate two large primes of half the desired bit length
    p = generate_prime(bit_length // 2)
    q = generate_prime(bit_length // 2)
    
    # Ensure p != q
    while p == q:
        q = generate_prime(bit_length // 2)
    
    # Calculate n and n^2
    n = p * q
    n_squared = n * n
    
    # Generator (simplified: g = n + 1)
    g = n + 1
    
    # Calculate λ(n) = lcm(p-1, q-1)
    lambda_n = carmichael_lambda(p, q)
    
    # Calculate μ = (L(g^λ mod n^2))^(-1) mod n
    # where L(x) = (x - 1) / n
    g_lambda = pow(g, lambda_n, n_squared)
    L_value = (g_lambda - 1) // n
    mu = mod_inverse(L_value, n)
    
    # Precompute CRT parameters
    p_squared = p * p
    q_squared = q * q
    
    # h_p = L(g^(p-1) mod p^2)^(-1) mod p
    g_p = pow(g, p - 1, p_squared)
    L_p = (g_p - 1) // p
    hp = mod_inverse(L_p, p)
    
    # h_q = L(g^(q-1) mod q^2)^(-1) mod q
    g_q = pow(g, q - 1, q_squared)
    L_q = (g_q - 1) // q
    hq = mod_inverse(L_q, q)
    
    public_key = PaillierPublicKey(
        n=n,
        g=g,
        n_squared=n_squared,
        bit_length=bit_length
    )
    
    private_key = PaillierPrivateKey(
        lambda_n=lambda_n,
        mu=mu,
        p=p,
        q=q,
        p_squared=p_squared,
        q_squared=q_squared,
        hp=hp,
        hq=hq
    )
    
    return public_key, private_key


def encrypt(public_key: PaillierPublicKey, plaintext: int) -> int:
    """
    Encrypt a plaintext value using Paillier encryption.
    
    Args:
        public_key: Paillier public key
        plaintext: Integer plaintext to encrypt
        
    Returns:
        Integer ciphertext
    """
    # Ensure plaintext is in valid range [0, n)
    if not (0 <= plaintext < public_key.n):
        raise ValueError(f"Plaintext must be in range [0, {public_key.n})")
    
    # Select random r where gcd(r, n) = 1
    while True:
        r = secrets.randbelow(public_key.n)
        if r > 0 and gcd(r, public_key.n) == 1:
            break
    
    # Compute ciphertext: c = g^m * r^n mod n^2
    g_m = pow(public_key.g, plaintext, public_key.n_squared)
    r_n = pow(r, public_key.n, public_key.n_squared)
    ciphertext = (g_m * r_n) % public_key.n_squared
    
    return ciphertext


def decrypt(public_key: PaillierPublicKey, private_key: PaillierPrivateKey, 
           ciphertext: int) -> int:
    """
    Decrypt a ciphertext using standard Paillier decryption.
    
    Args:
        public_key: Paillier public key
        private_key: Paillier private key
        ciphertext: Integer ciphertext to decrypt
        
    Returns:
        Integer plaintext
    """
    # Compute L(c^λ mod n^2) * μ mod n
    # where L(x) = (x - 1) / n
    c_lambda = pow(ciphertext, private_key.lambda_n, public_key.n_squared)
    L_value = (c_lambda - 1) // public_key.n
    plaintext = (L_value * private_key.mu) % public_key.n
    
    return plaintext


def decrypt_crt(public_key: PaillierPublicKey, private_key: PaillierPrivateKey,
               ciphertext: int) -> int:
    """
    Decrypt using Chinese Remainder Theorem optimization.
    
    This provides significant speedup (2-4x) over standard decryption.
    
    Args:
        public_key: Paillier public key
        private_key: Paillier private key
        ciphertext: Integer ciphertext to decrypt
        
    Returns:
        Integer plaintext
    """
    p = private_key.p
    q = private_key.q
    p_squared = private_key.p_squared
    q_squared = private_key.q_squared
    
    # Compute m_p = L(c^(p-1) mod p^2) * h_p mod p
    c_p = pow(ciphertext, p - 1, p_squared)
    L_p = (c_p - 1) // p
    m_p = (L_p * private_key.hp) % p
    
    # Compute m_q = L(c^(q-1) mod q^2) * h_q mod q
    c_q = pow(ciphertext, q - 1, q_squared)
    L_q = (c_q - 1) // q
    m_q = (L_q * private_key.hq) % q
    
    # Use CRT to combine m_p and m_q
    # m = (m_p * q * (q^-1 mod p) + m_q * p * (p^-1 mod q)) mod n
    q_inv_p = mod_inverse(q, p)
    p_inv_q = mod_inverse(p, q)
    
    plaintext = (m_p * q * q_inv_p + m_q * p * p_inv_q) % public_key.n
    
    return plaintext


def homomorphic_add(public_key: PaillierPublicKey, ciphertext1: int, 
                   ciphertext2: int) -> int:
    """
    Homomorphically add two encrypted values.
    
    E(m1) * E(m2) = E(m1 + m2)
    
    Args:
        public_key: Paillier public key
        ciphertext1: First encrypted value
        ciphertext2: Second encrypted value
        
    Returns:
        Encryption of the sum
    """
    return (ciphertext1 * ciphertext2) % public_key.n_squared


def homomorphic_multiply(public_key: PaillierPublicKey, ciphertext: int,
                        scalar: int) -> int:
    """
    Homomorphically multiply encrypted value by plaintext scalar.
    
    E(m)^k = E(k * m)
    
    Args:
        public_key: Paillier public key
        ciphertext: Encrypted value
        scalar: Plaintext scalar multiplier
        
    Returns:
        Encryption of the product
    """
    return pow(ciphertext, scalar, public_key.n_squared)


class PaillierCryptosystem:
    """
    High-level interface for Paillier encryption with adaptive optimization.
    """
    
    def __init__(self, bit_length: int = 2048):
        """
        Initialize Paillier cryptosystem.
        
        Args:
            bit_length: Key size in bits
        """
        self.public_key, self.private_key = generate_keypair(bit_length)
        self.bit_length = bit_length
    
    @classmethod
    def from_dataset(cls, dataset: list, min_security: int = 1024):
        """
        Create Paillier system with optimal key size for dataset.
        
        Args:
            dataset: List of values to be encrypted
            min_security: Minimum acceptable key size
            
        Returns:
            PaillierCryptosystem instance
        """
        analysis = AdaptiveKeySelector.analyze_dataset(dataset)
        optimal_size = max(analysis['recommended_key_size'], min_security)
        
        print(f"Dataset analysis:")
        print(f"  Value range: [{analysis['min_value']}, {analysis['max_value']}]")
        print(f"  Recommended key size: {optimal_size} bits")
        print(f"  Storage reduction: {analysis['storage_reduction_percent']:.1f}%")
        print(f"  Estimated speedup: {analysis['compute_speedup_estimate']:.2f}x")
        
        return cls(bit_length=optimal_size)
    
    def encrypt(self, plaintext: int) -> int:
        """Encrypt a plaintext value."""
        return encrypt(self.public_key, plaintext)
    
    def decrypt(self, ciphertext: int, use_crt: bool = True) -> int:
        """
        Decrypt a ciphertext.
        
        Args:
            ciphertext: Encrypted value
            use_crt: Use CRT optimization (default True)
            
        Returns:
            Plaintext value
        """
        if use_crt:
            return decrypt_crt(self.public_key, self.private_key, ciphertext)
        else:
            return decrypt(self.public_key, self.private_key, ciphertext)
    
    def add(self, ciphertext1: int, ciphertext2: int) -> int:
        """Homomorphically add two encrypted values."""
        return homomorphic_add(self.public_key, ciphertext1, ciphertext2)
    
    def multiply(self, ciphertext: int, scalar: int) -> int:
        """Homomorphically multiply encrypted value by scalar."""
        return homomorphic_multiply(self.public_key, ciphertext, scalar)
    
    def sum_encrypted(self, ciphertexts: list) -> int:
        """
        Compute sum of encrypted values.
        
        Args:
            ciphertexts: List of encrypted values
            
        Returns:
            Encryption of the sum
        """
        if not ciphertexts:
            return self.encrypt(0)
        
        result = ciphertexts[0]
        for ct in ciphertexts[1:]:
            result = self.add(result, ct)
        
        return result
    
    def save_keys(self, filepath: Path):
        """Save keys to file (for testing purposes)."""
        data = {
            'bit_length': self.bit_length,
            'public_key': {
                'n': str(self.public_key.n),
                'g': str(self.public_key.g)
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)


if __name__ == "__main__":
    # Quick demonstration
    print("Paillier Cryptosystem with Adaptive Bit-Length")
    print("=" * 60)
    
    # Example: Small values (healthcare data)
    small_values = [65, 72, 80, 98, 105, 120, 140]  # Heart rates
    
    print("\nExample 1: Small values (heart rates)")
    crypto = PaillierCryptosystem.from_dataset(small_values)
    
    # Encrypt and compute
    encrypted = [crypto.encrypt(v) for v in small_values]
    encrypted_sum = crypto.sum_encrypted(encrypted)
    decrypted_sum = crypto.decrypt(encrypted_sum)
    
    print(f"Plaintext sum: {sum(small_values)}")
    print(f"Decrypted sum: {decrypted_sum}")
    print(f"Match: {sum(small_values) == decrypted_sum}")
    
    print("\n" + "=" * 60)
