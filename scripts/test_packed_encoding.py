"""
Simple test of packed encoding to debug the issue
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agniya.core.paillier import generate_keypair, encrypt, decrypt_crt

def test_pack_unpack():
    """Test basic pack/unpack"""
    base = 10000
    values = [10, 20, 30]
    
    # Pack
    packed = 0
    for i, v in enumerate(values):
        packed += v * (base ** i)
    
    print(f"Values: {values}")
    print(f"Packed: {packed}")
    
    # Unpack
    unpacked = []
    temp = packed
    for _ in range(len(values)):
        unpacked.append(temp % base)
        temp //= base
    
    print(f"Unpacked: {unpacked}")
    print(f"Match: {values == unpacked}")
    print()

def test_packed_sum():
    """Test packed homomorphic sum"""
    print("Generating keypair...")
    pub, priv = generate_keypair(bit_length=2048)
    
    base = 10000
    pack_size = 3
    
    # Test values: [10, 20, 30, 40, 50]
    # Expected sum: 150
    values = [10, 20, 30, 40, 50]
    print(f"Values: {values}")
    print(f"Expected sum: {sum(values)}")
    print()
    
    # Pack into chunks
    packs = []
    for i in range(0, len(values), pack_size):
        chunk = values[i:i+pack_size]
        packed = 0
        for j, v in enumerate(chunk):
            packed += v * (base ** j)
        packs.append(packed)
        print(f"Pack {len(packs)}: values={chunk}, packed={packed}")
    
    print(f"\nTotal packs: {len(packs)}")
    
    # Encrypt packs
    print("\nEncrypting packs...")
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
    print(f"\nUnpacking {len(packs)} values...")
    unpacked = []
    temp = packed_result
    for i in range(len(packs)):
        val = temp % base
        unpacked.append(val)
        temp //= base
        print(f"  Unpacked[{i}]: {val}")
    
    print(f"\nUnpacked: {unpacked}")
    print(f"Sum of unpacked: {sum(unpacked)}")
    print(f"Expected: {sum(values)}")
    print(f"Match: {sum(unpacked) == sum(values)}")
    
if __name__ == "__main__":
    print("="*70)
    print("TEST 1: Basic Pack/Unpack")
    print("="*70)
    test_pack_unpack()
    
    print("="*70)
    print("TEST 2: Packed Homomorphic Sum")
    print("="*70)
    test_packed_sum()
