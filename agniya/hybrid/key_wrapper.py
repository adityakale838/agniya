"""
Paillier Key Wrapper for AES Keys

Encrypts AES symmetric keys using Paillier public key encryption.
This enables secure key storage where the server can store encrypted
AES keys without being able to decrypt them.

Architecture:
1. Client generates AES key for record encryption
2. AES key is encrypted with Paillier public key
3. Server stores encrypted AES key (can't decrypt without private key)
4. Client can unwrap AES key using Paillier private key when needed

Security Benefits:
- Server never sees plaintext AES keys
- Keys are as secure as Paillier encryption (2048-bit RSA-equivalent)
- Supports key rotation without re-encrypting all data
- Client holds Paillier private key (air-gapped key management)

Use Cases:
- Cloud storage: Server can't decrypt user data
- Multi-user systems: Each user's data encrypted with unique AES key
- Compliance: HIPAA/GDPR key escrow requirements
"""

from typing import Tuple
import struct

from agniya.core.paillier import (
    PaillierPublicKey,
    PaillierPrivateKey,
    generate_keypair,
    encrypt,
    decrypt_crt
)


class KeyWrapper:
    """
    Wraps (encrypts) AES keys using Paillier encryption.
    
    This provides a secure way to store encryption keys where the
    storage server cannot access the plaintext keys.
    """
    
    def __init__(self, 
                 public_key: PaillierPublicKey,
                 private_key: PaillierPrivateKey = None):
        """
        Initialize key wrapper.
        
        Args:
            public_key: Paillier public key (for wrapping keys)
            private_key: Paillier private key (for unwrapping keys, optional)
        """
        self.public_key = public_key
        self.private_key = private_key
        
        # Calculate max bytes we can encrypt (based on key size)
        # Paillier can encrypt values up to n-1
        # For 2048-bit key: ~256 bytes
        self.max_plaintext_bytes = (public_key.n.bit_length() // 8) - 1
    
    def wrap_key(self, aes_key: bytes) -> int:
        """
        Wrap (encrypt) AES key using Paillier encryption.
        
        The AES key is converted to an integer and encrypted.
        Server can store this encrypted key without being able to decrypt it.
        
        Args:
            aes_key: 256-bit (32-byte) AES key
            
        Returns:
            Paillier ciphertext (encrypted key)
            
        Raises:
            ValueError: If key is too large for Paillier encryption
        """
        if len(aes_key) > self.max_plaintext_bytes:
            raise ValueError(
                f"AES key too large: {len(aes_key)} bytes, "
                f"max {self.max_plaintext_bytes} bytes for this Paillier key"
            )
        
        # Convert bytes to integer (big-endian)
        key_as_int = int.from_bytes(aes_key, byteorder='big')
        
        # Encrypt with Paillier
        wrapped_key = encrypt(self.public_key, key_as_int)
        
        return wrapped_key
    
    def unwrap_key(self, wrapped_key: int) -> bytes:
        """
        Unwrap (decrypt) AES key using Paillier private key.
        
        Requires private key. Typically only client (not server) can do this.
        
        Args:
            wrapped_key: Paillier ciphertext (encrypted AES key)
            
        Returns:
            Original 32-byte AES key
            
        Raises:
            ValueError: If private key not available
        """
        if self.private_key is None:
            raise ValueError(
                "Cannot unwrap key: Paillier private key not available. "
                "This operation requires the private key (client-side only)."
            )
        
        # Decrypt with Paillier
        key_as_int = decrypt_crt(self.public_key, self.private_key, wrapped_key)
        
        # Convert integer back to bytes (32 bytes for AES-256)
        # Handle case where leading zeros were lost in integer conversion
        aes_key = key_as_int.to_bytes(32, byteorder='big')
        
        return aes_key
    
    def wrap_multiple_keys(self, aes_keys: list[bytes]) -> list[int]:
        """
        Wrap multiple AES keys (batch operation).
        
        Args:
            aes_keys: List of 32-byte AES keys
            
        Returns:
            List of Paillier ciphertexts
        """
        return [self.wrap_key(key) for key in aes_keys]
    
    def unwrap_multiple_keys(self, wrapped_keys: list[int]) -> list[bytes]:
        """
        Unwrap multiple AES keys (batch operation).
        
        Args:
            wrapped_keys: List of Paillier ciphertexts
            
        Returns:
            List of original AES keys
        """
        return [self.unwrap_key(key) for key in wrapped_keys]
    
    def get_wrapped_key_size(self) -> int:
        """
        Get storage size for a wrapped key.
        
        Returns:
            Size in bytes (typically 512 bytes for Paillier-2048)
        """
        # Paillier ciphertext is approximately n_squared size
        return (self.public_key.n_squared.bit_length() + 7) // 8
    
    def __repr__(self) -> str:
        has_private = "with private key" if self.private_key else "public key only"
        return (f"KeyWrapper(key_size={self.public_key.n.bit_length()} bits, "
                f"{has_private})")


class HybridKeyManager:
    """
    Manages key generation and wrapping for hybrid encryption system.
    
    Combines:
    - Paillier key pair generation (for key wrapping)
    - AES key generation (for data encryption)
    - Automatic key wrapping
    """
    
    def __init__(self, paillier_key_size: int = 2048):
        """
        Initialize hybrid key manager.
        
        Args:
            paillier_key_size: Size of Paillier keys in bits (default 2048)
        """
        print(f"Generating {paillier_key_size}-bit Paillier key pair...")
        self.paillier_pub, self.paillier_priv = generate_keypair(paillier_key_size)
        
        self.wrapper = KeyWrapper(self.paillier_pub, self.paillier_priv)
        print(f"✅ Key manager initialized")
    
    def create_wrapped_aes_key(self) -> Tuple[bytes, int]:
        """
        Generate new AES key and wrap it with Paillier.
        
        Returns:
            Tuple of (plaintext_aes_key, wrapped_aes_key)
            - Client keeps plaintext_aes_key (for encryption/decryption)
            - Server stores wrapped_aes_key (can't decrypt it)
        """
        from agniya.hybrid.aes_cipher import AESCipher
        
        # Generate random AES key
        aes_key = AESCipher.generate_key()
        
        # Wrap it with Paillier
        wrapped_key = self.wrapper.wrap_key(aes_key)
        
        return aes_key, wrapped_key
    
    def get_public_key_only_wrapper(self) -> KeyWrapper:
        """
        Create wrapper with public key only (for server-side).
        
        Server can wrap new keys but cannot unwrap existing keys.
        
        Returns:
            KeyWrapper with only public key
        """
        return KeyWrapper(self.paillier_pub, private_key=None)


# Demo
if __name__ == "__main__":
    from agniya.hybrid.aes_cipher import AESCipher
    import time
    
    print("="*70)
    print("Paillier Key Wrapper Demo")
    print("="*70)
    
    # Initialize key manager
    print("\nInitializing key manager...")
    manager = HybridKeyManager(paillier_key_size=2048)
    
    # Test 1: Generate and wrap AES key
    print("\n" + "="*70)
    print("Test 1: Generate and Wrap AES Key")
    print("="*70)
    
    aes_key, wrapped_key = manager.create_wrapped_aes_key()
    print(f"Generated AES key: {aes_key.hex()[:40]}...")
    print(f"Wrapped key size: {len(str(wrapped_key))} digits")
    print(f"Wrapped key (truncated): {str(wrapped_key)[:50]}...")
    
    # Test 2: Unwrap key
    print("\n" + "="*70)
    print("Test 2: Unwrap AES Key")
    print("="*70)
    
    unwrapped_key = manager.wrapper.unwrap_key(wrapped_key)
    print(f"Unwrapped key: {unwrapped_key.hex()[:40]}...")
    print(f"✅ Keys match: {aes_key == unwrapped_key}")
    
    # Test 3: Use wrapped key for encryption
    print("\n" + "="*70)
    print("Test 3: End-to-End Encryption Flow")
    print("="*70)
    
    # Scenario: Client encrypts data, server stores encrypted data + wrapped key
    
    # Client side: Encrypt sensitive data
    cipher = AESCipher(key=aes_key)
    sensitive_data = "Patient SSN: 123-45-6789, Diagnosis: Confidential"
    encrypted = cipher.encrypt_string(sensitive_data)
    
    print(f"Original data: {sensitive_data}")
    print(f"Encrypted: {encrypted['ciphertext'][:50]}...")
    
    # Server stores: encrypted data + wrapped AES key
    # Server CANNOT decrypt because it doesn't have Paillier private key
    print(f"\n📦 Server stores:")
    print(f"  - Encrypted data: {len(encrypted['ciphertext'])} bytes")
    print(f"  - Wrapped AES key: {len(str(wrapped_key))} digits")
    print(f"  ⚠️  Server CANNOT decrypt (no Paillier private key)")
    
    # Client retrieves: unwraps key, decrypts data
    print(f"\n🔓 Client retrieves:")
    retrieved_aes_key = manager.wrapper.unwrap_key(wrapped_key)
    cipher2 = AESCipher(key=retrieved_aes_key)
    decrypted = cipher2.decrypt_string(
        encrypted['ciphertext'],
        encrypted['nonce'],
        encrypted['tag']
    )
    
    print(f"  - Unwrapped AES key: {retrieved_aes_key.hex()[:40]}...")
    print(f"  - Decrypted data: {decrypted}")
    print(f"  ✅ Match: {sensitive_data == decrypted}")
    
    # Test 4: Server cannot unwrap
    print("\n" + "="*70)
    print("Test 4: Server Cannot Unwrap Keys")
    print("="*70)
    
    server_wrapper = manager.get_public_key_only_wrapper()
    print(f"Server wrapper: {server_wrapper}")
    
    try:
        server_wrapper.unwrap_key(wrapped_key)
        print("❌ Server was able to unwrap key (SECURITY BREACH!)")
    except ValueError as e:
        print(f"✅ Server correctly blocked from unwrapping: {e}")
    
    # Test 5: Performance
    print("\n" + "="*70)
    print("Test 5: Performance Benchmark")
    print("="*70)
    
    print("Wrapping 10 AES keys...")
    start = time.time()
    keys = [AESCipher.generate_key() for _ in range(10)]
    wrapped = manager.wrapper.wrap_multiple_keys(keys)
    wrap_time = time.time() - start
    print(f"  Wrap time: {wrap_time*1000:.1f}ms ({wrap_time*100:.1f}ms per key)")
    
    print("Unwrapping 10 AES keys...")
    start = time.time()
    unwrapped = manager.wrapper.unwrap_multiple_keys(wrapped)
    unwrap_time = time.time() - start
    print(f"  Unwrap time: {unwrap_time*1000:.1f}ms ({unwrap_time*100:.1f}ms per key)")
    
    print(f"✅ All keys match: {keys == unwrapped}")
    
    # Storage comparison
    print("\n" + "="*70)
    print("Storage Size Analysis")
    print("="*70)
    
    print(f"Plaintext AES key: 32 bytes")
    print(f"Wrapped AES key: {manager.wrapper.get_wrapped_key_size()} bytes")
    print(f"Overhead: {manager.wrapper.get_wrapped_key_size() / 32:.1f}x")
    print(f"\n⚠️  Note: This overhead is PER DATABASE, not per record!")
    print(f"Each record uses same AES key, so amortized cost is minimal.")
    
    print("\n" + "="*70)
    print("✅ Key Wrapping System Complete!")
    print("="*70)
