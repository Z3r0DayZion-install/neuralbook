"""
Tests for encryption module.
"""

import pytest
from neuralbook.encryption import derive_key, encrypt_content, decrypt_content


def test_derive_key():
    """Test key derivation produces consistent results."""
    seed = b"test-seed-12345678901234567890123456789012"
    key1 = derive_key(seed)
    key2 = derive_key(seed)
    
    assert key1 == key2
    assert len(key1) == 32  # AES-256 key size


def test_encrypt_decrypt_roundtrip():
    """Test encryption and decryption."""
    plaintext = b"Hello, NeuralBook!"
    key = derive_key(b"test" * 12)
    
    iv, ciphertext = encrypt_content(plaintext, key)
    decrypted = decrypt_content(iv, ciphertext, key)
    
    assert decrypted == plaintext


def test_unique_ivs():
    """Test that each encryption produces unique IV."""
    plaintext = b"Same content"
    key = derive_key(b"test" * 12)
    
    iv1, ct1 = encrypt_content(plaintext, key)
    iv2, ct2 = encrypt_content(plaintext, key)
    
    assert iv1 != iv2  # Different IVs
    assert ct1 != ct2  # Different ciphertexts
