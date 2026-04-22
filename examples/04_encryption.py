#!/usr/bin/env python3
"""
Example 4: Encryption & Decryption
===================================
Demonstrates the cryptographic features of NeuralBook.

This example shows:
- Deriving encryption keys from seeds using scrypt (JS-compatible)
- Encrypting content with AES-256-GCM into the .nd blob format
- Integrity verification and tamper detection
- Unique IVs per message

Wire format: [IV:12 bytes][AuthTag:16 bytes][Ciphertext:N bytes]
Key derivation: scrypt(seed, salt='salt', n=16384, r=8, p=1, dklen=32)
  -- matches JS: crypto.scryptSync(seed, 'salt', 32)

Requirements:
  pip install neuralbook cryptography

Usage:
  python 04_encryption.py
"""

import secrets
import sys

from neuralbook.encryption import decrypt_content, derive_key, encrypt_content

IV_LENGTH = 12
AUTH_TAG_LENGTH = 16


def main():
    """Demonstrate encryption and decryption."""

    print("=" * 60)
    print("NeuralBook: Encryption Example")
    print("=" * 60)

    # 1. Generate seed (string form, as used in title-config.json)
    print("\n[1] Generating encryption seed...")
    seed = secrets.token_hex(32)  # 64 hex chars -> 32 bytes of entropy
    print(f"  seed: {seed[:32]}... ({len(seed)} chars)")

    # 2. Derive encryption key via scrypt (wire-compatible with JS pipeline)
    print("\n[2] Deriving AES-256 key from seed (scrypt)...")
    key = derive_key(seed)
    print(f"  key:  {key.hex()[:32]}... ({len(key)} bytes)")
    print( "  algo: scrypt(seed, salt='salt', n=16384, r=8, p=1, dklen=32)")
    print( "  ↔    JS: crypto.scryptSync(seed, 'salt', 32)")

    # 3. Prepare content
    print("\n[3] Preparing content...")
    original = b"""
This is a confidential chapter from a NeuralBook title.

It contains information protected by AES-256-GCM authenticated encryption.
The authentication tag detects any modification to the ciphertext.
""".strip()
    print(f"  plaintext: {len(original)} bytes")

    # 4. Encrypt -> .nd blob
    print("\n[4] Encrypting to .nd blob...")
    blob = encrypt_content(original, key)
    iv       = blob[:IV_LENGTH]
    auth_tag = blob[IV_LENGTH:IV_LENGTH + AUTH_TAG_LENGTH]
    ct       = blob[IV_LENGTH + AUTH_TAG_LENGTH:]
    print(f"  blob total: {len(blob)} bytes")
    print(f"  IV:         {iv.hex()} (12 bytes, random)")
    print(f"  AuthTag:    {auth_tag.hex()} (16 bytes)")
    print(f"  Ciphertext: {ct.hex()[:32]}... ({len(ct)} bytes)")

    # 5. Decrypt and verify
    print("\n[5] Decrypting blob...")
    try:
        recovered = decrypt_content(blob, key)
        print(f"  decrypted: {len(recovered)} bytes")
    except Exception as e:
        print(f"  FAIL: {e}")
        return 1

    assert recovered == original, "Round-trip mismatch!"
    print("  content matches original")

    # 6. Tamper detection
    print("\n[6] Testing tamper detection...")
    # Flip a byte in the ciphertext section of the blob
    tampered = bytearray(blob)
    tampered[IV_LENGTH + AUTH_TAG_LENGTH] ^= 0xFF
    try:
        decrypt_content(bytes(tampered), key)
        print("  ERROR: tampered blob should have raised InvalidTag!")
        return 1
    except Exception as e:
        print(f"  correctly rejected tampered blob: {type(e).__name__}")

    # 7. Multiple messages — each gets a unique IV
    print("\n[7] Unique IVs per message...")
    messages = [b"Chapter One", b"Chapter Two", b"Chapter Three"]
    blobs = [encrypt_content(m, key) for m in messages]
    ivs = [b[:IV_LENGTH].hex() for b in blobs]
    for i, (msg, iv_hex) in enumerate(zip(messages, ivs), 1):
        print(f"  msg {i} IV: {iv_hex}")
    assert len(set(ivs)) == 3, "IVs must be unique!"
    print("  all IVs are distinct")

    print("\n" + "=" * 60)
    print("Done.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
