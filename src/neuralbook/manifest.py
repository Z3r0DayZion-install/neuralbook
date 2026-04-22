"""
SHA-256 manifest generation and verification for integrity checking.
"""

import hashlib
import json
from pathlib import Path
from typing import Dict, List


def generate_manifest(directory: Path, recursive: bool = True) -> Dict:
    """
    Generate SHA-256 manifest for all files in directory.

    Args:
        directory: Root directory to manifest
        recursive: Include subdirectories

    Returns:
        Manifest dict with file hashes
    """
    manifest = {
        "version": "1.0",
        "generated": None,  # will be filled by caller
        "files": {},
    }

    pattern = "**/*" if recursive else "*"
    for file_path in sorted(directory.glob(pattern)):
        if file_path.is_file():
            rel_path = file_path.relative_to(directory)
            manifest["files"][str(rel_path)] = {
                "sha256": compute_hash(file_path),
                "size": file_path.stat().st_size,
            }

    return manifest


def compute_hash(file_path: Path, algorithm: str = "sha256") -> str:
    """
    Compute hash of a file.

    Args:
        file_path: Path to file
        algorithm: hash algorithm (sha256 supported)

    Returns:
        Hex-encoded hash string
    """
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_manifest(directory: Path, manifest: Dict) -> bool:
    """
    Verify that files match manifest hashes.

    Args:
        directory: Root directory to check
        manifest: Manifest dict from generate_manifest()

    Returns:
        True if all files match, False otherwise
    """
    for rel_path, expected in manifest["files"].items():
        file_path = directory / rel_path
        if not file_path.exists():
            print(f"Missing: {rel_path}")
            return False

        actual_hash = compute_hash(file_path)
        if actual_hash != expected["sha256"]:
            print(f"Hash mismatch: {rel_path}")
            return False

    return True


def compute_root_hash(manifest: Dict) -> str:
    """
    Compute root integrity hash for entire manifest.

    Args:
        manifest: Manifest dict

    Returns:
        Hex-encoded root hash
    """
    manifest_json = json.dumps(manifest["files"], sort_keys=True)
    return hashlib.sha256(manifest_json.encode()).hexdigest()
