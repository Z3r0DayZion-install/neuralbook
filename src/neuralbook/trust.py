"""Trust utilities: key registry, revocation, and signature verification.

This module is intentionally standalone so trust policy can evolve
without changing build or runtime behavior.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class TrustedKey:
    key_id: str
    public_key_hex: str


def load_trusted_keys(path: Path) -> dict[str, TrustedKey]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    keys = payload.get("keys", [])
    out: dict[str, TrustedKey] = {}
    for item in keys:
        key_id = str(item.get("key_id", "")).strip()
        public_key_hex = str(item.get("public_key_hex", "")).strip()
        if not key_id or not public_key_hex:
            continue
        out[key_id] = TrustedKey(key_id=key_id, public_key_hex=public_key_hex)
    return out


def load_revoked_key_ids(path: Path) -> set[str]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    revoked = payload.get("revoked_key_ids", [])
    return {str(v).strip() for v in revoked if str(v).strip()}


def verify_ed25519_signature(
    *,
    public_key_hex: str,
    signature_hex: str,
    message: bytes,
) -> None:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    public_key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
    public_key.verify(bytes.fromhex(signature_hex), message)


def select_trusted_public_key_hex(
    signature_block: dict,
    trusted_keys: Optional[dict[str, TrustedKey]],
) -> str:
    """Return which public key hex should be used to verify signature.

    - If trusted_keys is provided, require signature's key_id to exist in it.
    - Otherwise fall back to embedded public_key_hex (legacy/unsigned-trust mode).
    """

    key_id = str(signature_block.get("key_id", "")).strip()
    embedded = str(signature_block.get("public_key_hex", "")).strip()

    if trusted_keys is None:
        return embedded

    if not key_id:
        raise ValueError("signature.key_id missing but trusted key registry was provided")
    if key_id not in trusted_keys:
        raise ValueError(f"signature key_id '{key_id}' not in trusted key registry")
    return trusted_keys[key_id].public_key_hex
