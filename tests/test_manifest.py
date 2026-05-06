"""Tests for NeuralBook manifest helpers."""

import json

from neuralbook.manifest import compute_hash, compute_root_hash, generate_manifest, verify_manifest


def test_generate_manifest_and_verify_round_trip(tmp_path):
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    sub = tmp_path / "nested"
    sub.mkdir()
    (sub / "b.txt").write_text("world", encoding="utf-8")

    manifest = generate_manifest(tmp_path)
    normalized_keys = {key.replace("\\", "/") for key in manifest["files"]}

    assert manifest["version"] == "1.0"
    assert "a.txt" in normalized_keys
    assert "nested/b.txt" in normalized_keys
    assert verify_manifest(tmp_path, manifest) is True


def test_verify_manifest_detects_tamper(tmp_path):
    file_path = tmp_path / "chapter.md"
    file_path.write_text("original", encoding="utf-8")
    manifest = generate_manifest(tmp_path)

    file_path.write_text("tampered", encoding="utf-8")

    assert verify_manifest(tmp_path, manifest) is False


def test_compute_hash_matches_sha256_hex_length(tmp_path):
    file_path = tmp_path / "data.bin"
    file_path.write_bytes(b"abc123")

    digest = compute_hash(file_path)

    assert isinstance(digest, str)
    assert len(digest) == 64


def test_compute_root_hash_is_deterministic():
    files = {
        "z.txt": {"sha256": "z" * 64, "size": 1},
        "a.txt": {"sha256": "a" * 64, "size": 2},
    }
    manifest = {"files": files}

    first = compute_root_hash(manifest)
    second = compute_root_hash({"files": json.loads(json.dumps(files))})

    assert first == second
