"""
Number Theory utilities for the Paillier cryptosystem.

This module provides the mathematical primitives needed for
the hybrid AES + Paillier encryption system.
"""

import secrets
from typing import Tuple
import math


def gcd(a: int, b: int) -> int:
    """
    Calculate Greatest Common Divisor using Euclidean algorithm.
    
    Args:
        a: First integer
        b: Second integer
        
    Returns:
        Greatest common divisor of a and b
    """
    while b:
        a, b = b, a % b
    return abs(a)


def extended_gcd(a: int, b: int) -> Tuple[int, int, int]:
    """
    Extended Euclidean Algorithm (iterative implementation).
    
    Returns (gcd, x, y) where ax + by = gcd(a, b)
    
    Args:
        a: First integer
        b: Second integer
        
    Returns:
        Tuple of (gcd, x, y) satisfying ax + by = gcd(a, b)
    """
    # Iterative implementation to avoid stack overflow with large numbers
    old_r, r = a, b
    old_s, s = 1, 0
    old_t, t = 0, 1
    
    while r != 0:
        quotient = old_r // r
        old_r, r = r, old_r - quotient * r
        old_s, s = s, old_s - quotient * s
        old_t, t = t, old_t - quotient * t
    
    return old_r, old_s, old_t


def mod_inverse(a: int, m: int) -> int:
    """
    Calculate modular multiplicative inverse of a modulo m.
    
    Args:
        a: Integer to find inverse of
        m: Modulus
        
    Returns:
        Modular inverse of a modulo m
        
    Raises:
        ValueError: If gcd(a, m) != 1 (no inverse exists)
    """
    gcd_val, x, _ = extended_gcd(a, m)
    
    if gcd_val != 1:
        raise ValueError(f"Modular inverse of {a} mod {m} does not exist")
    
    return x % m


def is_prime(n: int, k: int = 20) -> bool:
    """
    Miller-Rabin primality test.
    
    Args:
        n: Number to test for primality
        k: Number of rounds (higher = more accurate)
        
    Returns:
        True if n is probably prime, False if composite
    """
    if n < 2:
        return False
    if n == 2 or n == 3:
        return True
    if n % 2 == 0:
        return False
    
    # Write n-1 as 2^r * d
    r = 0
    d = n - 1
    while d % 2 == 0:
        r += 1
        d //= 2
    
    # Perform k rounds of testing
    for _ in range(k):
        a = secrets.randbelow(n - 3) + 2  # [2, n-2]
        x = pow(a, d, n)
        
        if x == 1 or x == n - 1:
            continue
            
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    
    return True


_SMALL_PRIMES = [p for p in range(3, 2000, 2) if all(p % d for d in range(3, int(p ** 0.5) + 1, 2))]

try:
    from gmpy2 import is_prime as _gmp_is_prime
except ImportError:  # pragma: no cover
    _gmp_is_prime = None


def generate_prime(bit_length: int) -> int:
    """
    Random prime with exactly `bit_length` bits and its top TWO bits set,
    so the product of two such primes has exactly 2*bit_length bits.
    Candidates come from `secrets`; small factors are sieved before Miller-Rabin.
    """
    top2 = 3 << (bit_length - 2)
    while True:
        candidate = secrets.randbits(bit_length) | top2 | 1
        if any(candidate % sp == 0 for sp in _SMALL_PRIMES):
            continue
        if (_gmp_is_prime(candidate, 40) if _gmp_is_prime else is_prime(candidate)):
            return candidate


def lcm(a: int, b: int) -> int:
    """
    Calculate Least Common Multiple of two integers.
    
    Args:
        a: First integer
        b: Second integer
        
    Returns:
        Least common multiple of a and b
    """
    return abs(a * b) // gcd(a, b)


def carmichael_lambda(p: int, q: int) -> int:
    """
    Calculate Carmichael function λ(n) for n = p * q where p, q are primes.
    
    For RSA-like systems: λ(n) = lcm(p-1, q-1)
    
    Args:
        p: First prime
        q: Second prime
        
    Returns:
        Carmichael lambda of p * q
    """
    return lcm(p - 1, q - 1)
