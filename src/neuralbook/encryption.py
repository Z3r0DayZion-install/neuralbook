"""
AES-256-GCM encryption for NeuralBook.

Wire format for .nd files: [IV:12 bytes][AuthTag:16 bytes][Ciphertext:N bytes]

Key derivation uses scrypt matching the JS pipeline (crypto.scryptSync(seed,'salt',32))
so Python and Electron can exchange encrypted files interchangeably.

Key discovery priority (mirrors key-discovery.js):
    1. NEURALBOOK_ENCRYPTION_SEED env var   (all build types)
    2. encryptionSeedFile in title config   (all build types)
    3. encryptionSeed in title config       (demo/internal only)
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import warnings
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

IV_LENGTH = 12
AUTH_TAG_LENGTH = 16
ND_EXTENSION = ".nd"
_SCRYPT_SALT = b"salt"  # matches JS: crypto.scryptSync(seed, 'salt', 32)


def derive_key(seed: Any) -> bytes:
    """Derive 32-byte AES-256 key from seed string/bytes using scrypt (matches JS pipeline)."""
    if isinstance(seed, str):
        seed = seed.encode("utf-8")
    return hashlib.scrypt(seed, salt=_SCRYPT_SALT, n=16384, r=8, p=1, dklen=32)


def encrypt_content(plaintext: bytes, key: bytes) -> bytes:
    """Encrypt bytes -> .nd blob: [IV:12][AuthTag:16][Ciphertext]."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    iv = secrets.token_bytes(IV_LENGTH)
    ct_tag = AESGCM(key).encrypt(iv, plaintext, None)
    ciphertext, auth_tag = ct_tag[:-AUTH_TAG_LENGTH], ct_tag[-AUTH_TAG_LENGTH:]
    return iv + auth_tag + ciphertext


def decrypt_content(blob: bytes, key: bytes) -> bytes:
    """Decrypt .nd blob -> plaintext bytes. Raises InvalidTag if tampered."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    if len(blob) < IV_LENGTH + AUTH_TAG_LENGTH:
        raise ValueError(f"Blob too short ({len(blob)}b) to be a valid .nd file")
    iv = blob[:IV_LENGTH]
    auth_tag = blob[IV_LENGTH: IV_LENGTH + AUTH_TAG_LENGTH]
    ciphertext = blob[IV_LENGTH + AUTH_TAG_LENGTH:]
    return AESGCM(key).decrypt(iv, ciphertext + auth_tag, None)


def encrypt_file(src: Any, dst: Any, key: bytes) -> int:
    """Encrypt src -> dst.nd. Returns encrypted byte count."""
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    blob = encrypt_content(Path(src).read_bytes(), key)
    dst.write_bytes(blob)
    return len(blob)


def decrypt_file(src: Any, dst: Any, key: bytes) -> int:
    """Decrypt src.nd -> dst plaintext. Returns plaintext byte count."""
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    plaintext = decrypt_content(Path(src).read_bytes(), key)
    dst.write_bytes(plaintext)
    return len(plaintext)


class KeySourceError(Exception):
    pass


def discover_key(
    title_config: Optional[Dict[str, Any]] = None,
    title_dir: Optional[Any] = None,
    build_type: str = "demo",
) -> Tuple[bytes, str]:
    """Discover encryption key from env -> seed file -> config (in priority order).

    Returns (key_bytes, source_label). Raises KeySourceError if nothing found.
    """
    cfg: Dict[str, Any] = title_config or {}

    # 1. Env var
    env_seed = os.environ.get("NEURALBOOK_ENCRYPTION_SEED", "").strip()
    if env_seed:
        _validate_seed(env_seed, "env var")
        return derive_key(env_seed), "environment"

    # 2. Seed file
    seed_file = str(cfg.get("encryptionSeedFile", "")).strip()
    if seed_file:
        base = Path(title_dir) if title_dir else Path.cwd()
        p = (base / seed_file).resolve()
        if not p.exists():
            raise KeySourceError(f"encryptionSeedFile not found: {p}")
        file_seed = p.read_text(encoding="utf-8").strip()
        _validate_seed(file_seed, f"file:{p.name}")
        return derive_key(file_seed), f"file:{p.name}"

    # 3. Plaintext config (demo/internal only)
    config_seed = str(cfg.get("encryptionSeed", "")).strip()
    if config_seed:
        if build_type in ("release", "external"):
            raise KeySourceError(
                f"Plaintext config seed not allowed for build_type='{build_type}'"
            )
        warnings.warn(
            "Using plaintext encryptionSeed from config - use env var for release builds.",
            stacklevel=2,
        )
        _validate_seed(config_seed, "title-config.json")
        return derive_key(config_seed), "config"

    raise KeySourceError(
        "No encryption seed found.\n"
        "  1. export NEURALBOOK_ENCRYPTION_SEED='$(openssl rand -base64 48)'\n"
        "  2. Set encryptionSeedFile in title-config.json\n"
        "  3. Set encryptionSeed in title-config.json  (demo only)"
    )


def key_from_config(config_path: Any, build_type: str = "demo") -> Tuple[bytes, str]:
    """Load title-config.json and return (key_bytes, source_label)."""
    cfg = json.loads(Path(config_path).read_text(encoding="utf-8"))
    return discover_key(cfg, Path(config_path).parent, build_type)


def _validate_seed(seed: str, source: str) -> None:
    if len(seed) < 32:
        raise KeySourceError(f"Seed from {source} too short ({len(seed)} chars, min 32)")
    for w in ("password", "123456", "qwerty", "admin", "test"):
        if seed.lower().startswith(w):
            raise KeySourceError(
                f"Seed from {source} matches weak pattern '{w}'. Use a random value."
            )
