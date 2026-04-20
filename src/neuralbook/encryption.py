"""
AES-256-GCM encryption implementation for NeuralBook.
"""

from typing import Tuple
import secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2


def derive_key(seed: bytes, iterations: int = 100000) -> bytes:
    """
    Derive a 256-bit AES key from a seed using PBKDF2-SHA256.
    
    Args:
        seed: Base seed bytes (48 bytes recommended)
        iterations: PBKDF2 iterations (default: NIST recommended 100k+)
    
    Returns:
        32-byte AES-256 key
    """
    kdf = PBKDF2(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"neuralbook-aes",
        iterations=iterations,
    )
    return kdf.derive(seed)


def encrypt_content(plaintext: bytes, key: bytes) -> Tuple[bytes, bytes, bytes]:
    """
    Encrypt content using AES-256-GCM.
    
    Args:
        plaintext: Content to encrypt
        key: 32-byte AES key
    
    Returns:
        (iv, ciphertext, tag) where tag is authentication tag
    """
    iv = secrets.token_bytes(12)  # 96-bit nonce
    cipher = AESGCM(key)
    ciphertext = cipher.encrypt(iv, plaintext, None)
    # GCM returns ciphertext + tag concatenated
    return iv, ciphertext


def decrypt_content(iv: bytes, ciphertext: bytes, key: bytes) -> bytes:
    """
    Decrypt AES-256-GCM encrypted content.
    
    Args:
        iv: 12-byte nonce
        ciphertext: Encrypted content (includes auth tag)
        key: 32-byte AES key
    
    Returns:
        Decrypted plaintext
    
    Raises:
        InvalidTag: If authentication fails
    """
    cipher = AESGCM(key)
    plaintext = cipher.decrypt(iv, ciphertext, None)
    return plaintext
