"""NeuralBook build pipeline: discover -> encrypt -> manifest."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from .encryption import ND_EXTENSION, discover_key, encrypt_file
from .manifest import compute_hash

CONTENT_EXTENSIONS = {
    ".txt",
    ".md",
    ".html",
    ".json",
    ".js",
    ".css",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".svg",
    ".webp",
    ".mp3",
    ".mp4",
    ".webm",
}
IGNORE_PATTERNS = {"node_modules", ".git", "__pycache__", ".DS_Store", "build", "dist"}


def discover_content(content_dir: Path, verbose: bool = False) -> List[Dict]:
    """Walk content_dir and return all encryptable files."""
    files = []
    for p in sorted(content_dir.rglob("*")):
        if not p.is_file():
            continue
        if any(part in IGNORE_PATTERNS for part in p.parts):
            continue
        if p.suffix.lower() not in CONTENT_EXTENSIONS:
            continue
        rel = p.relative_to(content_dir)
        files.append({"source_path": p, "relative_path": str(rel), "size": p.stat().st_size})
        if verbose:
            print(f"  found: {rel}")
    return files


def build_project(
    project_dir: Path,
    output_dir: Optional[Path] = None,
    build_type: str = "demo",
    title_config: Optional[dict] = None,
    verbose: bool = False,
) -> Dict:
    """Full NeuralBook content pipeline: discover -> encrypt -> manifest.

    Looks for plaintext content in content/, plaintext-content/, or book/.
    Writes encrypted .nd files to output_dir and a MANIFEST_<Title>.json beside it.

    Args:
        project_dir: Title project root (contains title-config.json)
        output_dir: Destination for .nd files (default: project_dir/build/encrypted/)
        build_type: 'demo' | 'internal' | 'release' | 'external'
        title_config: Pre-loaded config dict; loaded from title-config.json if None
        verbose: Print progress

    Returns:
        Build report dict.
    """
    project_dir = Path(project_dir)
    started_at = datetime.now(timezone.utc).isoformat()
    report: Dict = {
        "status": "pending",
        "build_type": build_type,
        "project_dir": str(project_dir),
        "started_at": started_at,
        "finished_at": "",
        "title": "",
        "key_source": "",
        "files_encrypted": 0,
        "files_failed": 0,
        "total_plaintext_bytes": 0,
        "total_encrypted_bytes": 0,
        "manifest_path": "",
        "provenance_path": "",
        "attestation_path": "",
        "errors": [],
    }

    if title_config is None:
        cfg_path = project_dir / "title-config.json"
        title_config = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}

    title_name = title_config.get("title", project_dir.name)
    report["title"] = title_name

    if output_dir is None:
        output_dir = project_dir / "build" / "encrypted"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    content_dir = None
    for name in ("content", "plaintext-content", "book"):
        c = project_dir / name
        if c.is_dir():
            content_dir = c
            break

    if content_dir is None:
        report["status"] = "error"
        report["errors"].append(
            "No content directory found. Expected content/, plaintext-content/, or book/"
        )
        return report

    content_files = discover_content(content_dir, verbose=verbose)
    if not content_files:
        report["status"] = "error"
        report["errors"].append(f"No encryptable files found in {content_dir}")
        return report

    if verbose:
        print(f"[2/4] Deriving key ({build_type})...")
    try:
        key, key_source = discover_key(title_config, project_dir, build_type)
    except Exception as exc:
        report["status"] = "error"
        report["errors"].append(f"Key discovery failed: {exc}")
        return report

    report["key_source"] = key_source
    if verbose:
        print(f"      source: {key_source}")
        print(f"[3/4] Encrypting {len(content_files)} files...")

    encrypted_entries = []
    for f in content_files:
        src = Path(f["source_path"])
        rel = f["relative_path"]
        dst = output_dir / (rel + ND_EXTENSION)
        try:
            enc_size = encrypt_file(src, dst, key)
            sha256 = compute_hash(dst)
            encrypted_entries.append(
                {
                    "relative_path": rel,
                    "sha256": sha256,
                    "plaintext_size": f["size"],
                    "encrypted_size": enc_size,
                }
            )
            report["files_encrypted"] += 1
            report["total_plaintext_bytes"] += f["size"]
            report["total_encrypted_bytes"] += enc_size
            if verbose:
                print(f"  ok  {rel}")
        except Exception as exc:
            report["files_failed"] += 1
            report["errors"].append(f"Failed {rel}: {exc}")
            if verbose:
                print(f"  ERR {rel}: {exc}")

    if verbose:
        print("[4/4] Writing manifest...")
    safe = title_name.replace(" ", "")
    manifest = {
        "title": title_name,
        "version": "1.0",
        "generated": started_at,
        "files": {
            e["relative_path"]
            + ND_EXTENSION: {
                "sha256": e["sha256"],
                "plaintext_size": e["plaintext_size"],
                "encrypted_size": e["encrypted_size"],
            }
            for e in encrypted_entries
        },
        "root_hash": _root_hash(encrypted_entries),
    }
    mp = output_dir.parent / f"MANIFEST_{safe}.json"
    mp.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    report["manifest_path"] = str(mp)

    provenance_path = output_dir.parent / f"PROVENANCE_{safe}.json"
    provenance = _write_provenance(
        provenance_path=provenance_path,
        title_name=title_name,
        project_dir=project_dir,
        content_dir=content_dir,
        build_type=build_type,
        key_source=key_source,
        started_at=started_at,
        encrypted_entries=encrypted_entries,
        manifest=manifest,
    )
    if build_type in {"release", "external"} and not (
        provenance.get("signature") or provenance.get("signatures")
    ):
        report["status"] = "error"
        report["errors"].append(
            "Release/external builds require provenance signature. "
            "Set NEURALBOOK_PROVENANCE_SIGNING_KEY_HEX or NEURALBOOK_PROVENANCE_SIGNERS_JSON."
        )
        return report

    report["provenance_path"] = str(provenance_path)
    attestation_path = output_dir.parent / f"ATTESTATION_{safe}.json"
    _write_attestation(attestation_path, manifest, provenance, report)
    report["attestation_path"] = str(attestation_path)

    report["status"] = "success" if report["files_failed"] == 0 else "partial"
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    if verbose:
        print(f"\nDone: {report['files_encrypted']} files. Manifest: {mp}")
    return report


def _root_hash(entries: List[Dict]) -> str:
    combined = json.dumps(
        {
            e["relative_path"]: e["sha256"]
            for e in sorted(entries, key=lambda x: x["relative_path"])
        },
        sort_keys=True,
    )
    return hashlib.sha256(combined.encode()).hexdigest()


def _write_provenance(
    provenance_path: Path,
    title_name: str,
    project_dir: Path,
    content_dir: Path,
    build_type: str,
    key_source: str,
    started_at: str,
    encrypted_entries: List[Dict],
    manifest: Dict,
) -> Dict:
    source_entries = []
    for entry in encrypted_entries:
        source_path = content_dir / entry["relative_path"]
        source_entries.append(
            {
                "relative_path": entry["relative_path"],
                "plaintext_sha256": compute_hash(source_path),
                "plaintext_size": entry["plaintext_size"],
                "encrypted_sha256": entry["sha256"],
                "encrypted_size": entry["encrypted_size"],
            }
        )

    source_entries = sorted(source_entries, key=lambda item: item["relative_path"])
    provenance = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "build_started_at": started_at,
        "title": title_name,
        "build_type": build_type,
        "key_source": key_source,
        "project_dir": str(project_dir),
        "content_dir": str(content_dir),
        "manifest_root_hash": manifest["root_hash"],
        "manifest_sha256": hashlib.sha256(
            json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "source_entries": source_entries,
    }
    provenance["build_fingerprint"] = _provenance_fingerprint(provenance)
    _attach_signature_if_configured(provenance)
    provenance_path.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    return provenance


def _provenance_fingerprint(provenance: Dict) -> str:
    material = {
        "title": provenance["title"],
        "build_type": provenance["build_type"],
        "manifest_root_hash": provenance["manifest_root_hash"],
        "manifest_sha256": provenance["manifest_sha256"],
        "source_entries": provenance["source_entries"],
    }
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _attach_signature_if_configured(provenance: Dict) -> None:
    """Attach one or more Ed25519 signatures to provenance.

    Supported env vars:
      - NEURALBOOK_PROVENANCE_SIGNING_KEY_HEX (+ optional NEURALBOOK_PROVENANCE_KEY_ID)
      - NEURALBOOK_PROVENANCE_SIGNERS_JSON: JSON list of {"key_id","private_key_hex"}
    """

    signers: list[dict[str, str]] = []
    signers_json = os.environ.get("NEURALBOOK_PROVENANCE_SIGNERS_JSON", "").strip()
    if signers_json:
        try:
            data = json.loads(signers_json)
            if isinstance(data, list):
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    key_id = str(item.get("key_id", "")).strip()
                    priv = str(item.get("private_key_hex", "")).strip()
                    if key_id and priv:
                        signers.append({"key_id": key_id, "private_key_hex": priv})
        except Exception as exc:
            raise ValueError("Invalid NEURALBOOK_PROVENANCE_SIGNERS_JSON value") from exc

    key_hex = os.environ.get("NEURALBOOK_PROVENANCE_SIGNING_KEY_HEX", "").strip()
    if key_hex:
        key_id = os.environ.get("NEURALBOOK_PROVENANCE_KEY_ID", "").strip() or "default"
        signers.append({"key_id": key_id, "private_key_hex": key_hex})

    if not signers:
        return

    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    except ImportError as exc:
        raise RuntimeError("cryptography package required for provenance signing") from exc

    fingerprint_bytes = provenance["build_fingerprint"].encode("utf-8")
    signatures: list[dict[str, str]] = []
    for signer in signers:
        try:
            private_key = Ed25519PrivateKey.from_private_bytes(
                bytes.fromhex(signer["private_key_hex"])
            )
        except ValueError as exc:
            raise ValueError(
                f"Invalid provenance signing private key for key_id={signer['key_id']!r}"
            ) from exc
        sig = private_key.sign(fingerprint_bytes)
        public_key = private_key.public_key().public_bytes_raw()
        signatures.append(
            {
                "algorithm": "ed25519",
                "key_id": signer["key_id"],
                "fingerprint_signature_hex": sig.hex(),
                "public_key_hex": public_key.hex(),
            }
        )

    provenance["signatures"] = signatures
    provenance["signature"] = signatures[0]


def _write_attestation(
    attestation_path: Path,
    manifest: Dict,
    provenance: Dict,
    report: Dict,
) -> None:
    attestation = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "title": report["title"],
        "build_type": report["build_type"],
        "build_status": report["status"],
        "manifest_root_hash": manifest["root_hash"],
        "manifest_sha256": provenance["manifest_sha256"],
        "build_fingerprint": provenance["build_fingerprint"],
        "provenance_signature": provenance.get("signature"),
        "provenance_signatures": provenance.get("signatures", []),
        "source_file_count": len(provenance["source_entries"]),
        "encrypted_file_count": report["files_encrypted"],
        "ci_context": {
            "git_sha": os.environ.get("GITHUB_SHA", ""),
            "git_ref": os.environ.get("GITHUB_REF", ""),
            "workflow": os.environ.get("GITHUB_WORKFLOW", ""),
            "run_id": os.environ.get("GITHUB_RUN_ID", ""),
        },
    }
    attestation_path.write_text(json.dumps(attestation, indent=2) + "\n", encoding="utf-8")


def verify_trust_chain(
    manifest_path: Path,
    provenance_path: Path,
    attestation_path: Path,
    require_signature: bool = False,
    trusted_keys_path: Path | None = None,
    revoked_keys_path: Path | None = None,
    require_trusted_keys: bool = False,
) -> tuple[bool, list[str]]:
    """Verify consistency of manifest, provenance, and attestation artifacts."""
    errors: list[str] = []
    manifest_path = Path(manifest_path)
    provenance_path = Path(provenance_path)
    attestation_path = Path(attestation_path)

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, [f"Failed to read manifest: {exc}"]
    try:
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, [f"Failed to read provenance: {exc}"]
    try:
        attestation = json.loads(attestation_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, [f"Failed to read attestation: {exc}"]

    if provenance.get("manifest_root_hash") != manifest.get("root_hash"):
        errors.append("Provenance manifest_root_hash mismatch.")
    if attestation.get("manifest_root_hash") != manifest.get("root_hash"):
        errors.append("Attestation manifest_root_hash mismatch.")

    expected_manifest_sha = hashlib.sha256(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if provenance.get("manifest_sha256") != expected_manifest_sha:
        errors.append("Provenance manifest_sha256 mismatch.")
    if attestation.get("manifest_sha256") != expected_manifest_sha:
        errors.append("Attestation manifest_sha256 mismatch.")

    expected_fingerprint = _provenance_fingerprint(provenance)
    if provenance.get("build_fingerprint") != expected_fingerprint:
        errors.append("Provenance build_fingerprint mismatch.")
    if attestation.get("build_fingerprint") != expected_fingerprint:
        errors.append("Attestation build_fingerprint mismatch.")

    signature_blocks: list[dict] = []
    if isinstance(provenance.get("signatures"), list) and provenance.get("signatures"):
        signature_blocks = list(provenance["signatures"])
    elif isinstance(provenance.get("signature"), dict):
        signature_blocks = [provenance["signature"]]

    if require_signature and not signature_blocks:
        errors.append("Provenance signature is required but missing.")

    if require_trusted_keys and not trusted_keys_path:
        errors.append("Trusted keys registry is required but missing.")

    if signature_blocks:
        try:
            from neuralbook.trust import (
                load_revoked_key_ids,
                load_trusted_keys,
                select_trusted_public_key_hex,
                verify_ed25519_signature,
            )

            trusted_keys = load_trusted_keys(trusted_keys_path) if trusted_keys_path else None
            revoked = load_revoked_key_ids(revoked_keys_path) if revoked_keys_path else set()

            if require_trusted_keys and trusted_keys is None:
                raise ValueError("Trusted key registry required for signature verification")

            for sig in signature_blocks:
                key_id = str(sig.get("key_id", "")).strip()
                if revoked_keys_path and key_id in revoked:
                    raise ValueError(f"signature key_id '{key_id}' is revoked")

                public_key_hex = select_trusted_public_key_hex(sig, trusted_keys)
                verify_ed25519_signature(
                    public_key_hex=public_key_hex,
                    signature_hex=sig["fingerprint_signature_hex"],
                    message=provenance["build_fingerprint"].encode("utf-8"),
                )
        except Exception as exc:
            errors.append(f"Invalid provenance signature: {exc}")

    return len(errors) == 0, errors
