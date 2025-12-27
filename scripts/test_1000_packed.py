"""Test packed encoding with exactly 1000 records"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from agniya.core.paillier import generate_keypair, encrypt, decrypt_crt

# Same as agniya_turbo
pack_size = 50
base = 1000000  # Must be > max value

def pack(values):
    """Encode multiple values as: v0 + v1*B + v2*B^2 + ..."""
    packed = 0
    for i, v in enumerate(values[:pack_size]):
        packed += v * (base ** i)
    return packed

def unpack(packed, n):
    """Decode packed value back to list"""
    values = []
    for _ in range(n):
        values.append(packed % base)
        packed //= base
    return values

def test_1000():
    print("Generating keys...")
    pub, priv = generate_keypair(2048)
    
    print("Generating dataset (1000 records)...")
    np.random.seed(42)
    data = np.random.randint(1, 1000, size=1000).tolist()
    expected_sum = sum(data)
    
    print(f"Expected sum: {expected_sum}")
    print()
    
    # Pack
    print(f"Packing with pack_size={pack_size}, base={base}...")
    packs = []
    for i in range(0, len(data), pack_size):
        chunk = data[i:i + pack_size]
        packs.append(pack(chunk))
    
    print(f"Created {len(packs)} packs")
    
    # Encrypt
    print("Encrypting packs...")
    encrypted_packs = [encrypt(pub, p) for p in packs]
    
    # Homomorphic sum
    print("Homomorphic sum...")
    result_ct = encrypted_packs[0]
    for ct in encrypted_packs[1:]:
        result_ct = (result_ct * ct) % pub.n_squared
    
    # Decrypt
    print("Decrypting...")
    packed_result = decrypt_crt(pub, priv, result_ct)
    print(f"Packed result: {packed_result}")
    
    # Unpack
    print(f"Unpacking {pack_size} values (not {len(packs)})...")
    unpacked = unpack(packed_result, pack_size)
    print(f"Unpacked: {unpacked[:10]}... (showing first 10)")
    
    result_sum = sum(unpacked)
    print()
    print(f"Sum of unpacked: {result_sum}")
    print(f"Expected: {expected_sum}")
    print(f"Match: {result_sum == expected_sum}")
    
if __name__ == "__main__":
    test_1000()
