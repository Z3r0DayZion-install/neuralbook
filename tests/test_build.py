"""Tests for NeuralBook build pipeline helpers."""

import json
from pathlib import Path

from neuralbook.build import ND_EXTENSION, build_project, discover_content, verify_trust_chain


def test_discover_content_filters_supported_files(tmp_path):
    content = tmp_path / "content"
    content.mkdir()
    (content / "chapter1.md").write_text("# chapter", encoding="utf-8")
    (content / "notes.txt").write_text("text", encoding="utf-8")
    (content / "ignore.exe").write_bytes(b"bin")

    results = discover_content(content)
    names = {item["relative_path"] for item in results}

    assert "chapter1.md" in names
    assert "notes.txt" in names
    assert "ignore.exe" not in names


def test_build_project_success_writes_manifest_and_encrypted_files(tmp_path):
    project = tmp_path / "title"
    content = project / "content"
    content.mkdir(parents=True)
    (content / "chapter-01.md").write_text("hello build", encoding="utf-8")

    cfg = {"title": "My Title", "encryptionSeed": "seed-abcdefghijklmnopqrstuvwxyz1234567890"}
    report = build_project(project, title_config=cfg, build_type="demo")

    assert report["status"] == "success"
    assert report["files_encrypted"] == 1
    assert report["files_failed"] == 0

    encrypted = project / "build" / "encrypted" / ("chapter-01.md" + ND_EXTENSION)
    assert encrypted.exists()

    manifest_path = project / "build" / "MANIFEST_MyTitle.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "chapter-01.md.nd" in manifest["files"]
    assert "root_hash" in manifest
    assert report["provenance_path"]
    assert report["attestation_path"]

    provenance_path = project / "build" / "PROVENANCE_MyTitle.json"
    assert provenance_path.exists()
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    assert provenance["title"] == "My Title"
    assert provenance["manifest_root_hash"] == manifest["root_hash"]
    assert len(provenance["source_entries"]) == 1
    assert provenance["source_entries"][0]["relative_path"] == "chapter-01.md"
    assert len(provenance["build_fingerprint"]) == 64

    attestation_path = project / "build" / "ATTESTATION_MyTitle.json"
    assert attestation_path.exists()
    attestation = json.loads(attestation_path.read_text(encoding="utf-8"))
    assert attestation["title"] == "My Title"
    assert attestation["manifest_root_hash"] == manifest["root_hash"]
    assert attestation["build_fingerprint"] == provenance["build_fingerprint"]


def test_build_project_errors_when_no_content_dir(tmp_path):
    project = tmp_path / "empty-title"
    project.mkdir()
    cfg = {"title": "Empty", "encryptionSeed": "seed-abcdefghijklmnopqrstuvwxyz1234567890"}

    report = build_project(project, title_config=cfg, build_type="demo")

    assert report["status"] == "error"
    assert any("No content directory found" in msg for msg in report["errors"])


def test_build_project_includes_signature_when_signing_key_set(tmp_path, monkeypatch):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    project = tmp_path / "signed-title"
    content = project / "content"
    content.mkdir(parents=True)
    (content / "chapter-01.md").write_text("signed build", encoding="utf-8")

    private_key = Ed25519PrivateKey.generate()
    raw_private = private_key.private_bytes_raw().hex()
    monkeypatch.setenv("NEURALBOOK_PROVENANCE_SIGNING_KEY_HEX", raw_private)
    monkeypatch.setenv("NEURALBOOK_PROVENANCE_KEY_ID", "unit-test-key")

    cfg = {"title": "Signed", "encryptionSeed": "seed-abcdefghijklmnopqrstuvwxyz1234567890"}
    report = build_project(project, title_config=cfg, build_type="demo")
    assert report["status"] == "success"

    provenance = json.loads(Path(report["provenance_path"]).read_text(encoding="utf-8"))
    assert "signature" in provenance
    assert provenance["signature"]["algorithm"] == "ed25519"
    assert provenance["signature"]["key_id"] == "unit-test-key"
    assert len(provenance["signature"]["public_key_hex"]) == 64
    assert len(provenance["signature"]["fingerprint_signature_hex"]) == 128


def test_release_build_requires_signature(tmp_path, monkeypatch):
    project = tmp_path / "release-no-sign"
    content = project / "content"
    content.mkdir(parents=True)
    (content / "chapter-01.md").write_text("release build", encoding="utf-8")

    monkeypatch.setenv("NEURALBOOK_ENCRYPTION_SEED", "seed-abcdefghijklmnopqrstuvwxyz1234567890")
    monkeypatch.delenv("NEURALBOOK_PROVENANCE_SIGNING_KEY_HEX", raising=False)
    cfg = {"title": "ReleaseNoSign"}
    report = build_project(project, title_config=cfg, build_type="release")

    assert report["status"] == "error"
    assert any("require provenance signature" in msg for msg in report["errors"])


def test_release_build_with_signature_succeeds(tmp_path, monkeypatch):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    project = tmp_path / "release-signed"
    content = project / "content"
    content.mkdir(parents=True)
    (content / "chapter-01.md").write_text("release signed", encoding="utf-8")

    private_key = Ed25519PrivateKey.generate()
    monkeypatch.setenv(
        "NEURALBOOK_PROVENANCE_SIGNING_KEY_HEX", private_key.private_bytes_raw().hex()
    )
    monkeypatch.setenv("NEURALBOOK_ENCRYPTION_SEED", "seed-abcdefghijklmnopqrstuvwxyz1234567890")

    cfg = {"title": "ReleaseSigned"}
    report = build_project(project, title_config=cfg, build_type="release")
    assert report["status"] == "success"
    provenance = json.loads(Path(report["provenance_path"]).read_text(encoding="utf-8"))
    assert "signature" in provenance


def test_multi_signer_env_json_writes_signatures_array(tmp_path, monkeypatch):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    project = tmp_path / "multi-sign"
    content = project / "content"
    content.mkdir(parents=True)
    (content / "chapter-01.md").write_text("multi signer", encoding="utf-8")

    k1 = Ed25519PrivateKey.generate().private_bytes_raw().hex()
    k2 = Ed25519PrivateKey.generate().private_bytes_raw().hex()
    monkeypatch.setenv(
        "NEURALBOOK_PROVENANCE_SIGNERS_JSON",
        json.dumps(
            [
                {"key_id": "primary", "private_key_hex": k1},
                {"key_id": "escrow", "private_key_hex": k2},
            ]
        ),
    )
    cfg = {"title": "Multi", "encryptionSeed": "seed-abcdefghijklmnopqrstuvwxyz1234567890"}
    report = build_project(project, title_config=cfg, build_type="demo")
    assert report["status"] == "success"
    prov = json.loads(Path(report["provenance_path"]).read_text(encoding="utf-8"))
    assert "signatures" in prov
    assert len(prov["signatures"]) == 2
    assert prov["signature"]["key_id"] == "primary"


def test_verify_trust_chain_pass_and_fail(tmp_path):
    project = tmp_path / "verify-chain-title"
    content = project / "content"
    content.mkdir(parents=True)
    (content / "chapter-01.md").write_text("chain test", encoding="utf-8")
    cfg = {"title": "Chain", "encryptionSeed": "seed-abcdefghijklmnopqrstuvwxyz1234567890"}
    report = build_project(project, title_config=cfg, build_type="demo")

    manifest_path = Path(report["manifest_path"])
    provenance_path = Path(report["provenance_path"])
    attestation_path = Path(report["attestation_path"])
    ok, errors = verify_trust_chain(manifest_path, provenance_path, attestation_path)
    assert ok is True
    assert errors == []

    attestation = json.loads(attestation_path.read_text(encoding="utf-8"))
    attestation["manifest_root_hash"] = "0" * 64
    attestation_path.write_text(json.dumps(attestation, indent=2) + "\n", encoding="utf-8")

    ok, errors = verify_trust_chain(manifest_path, provenance_path, attestation_path)
    assert ok is False
    assert any("Attestation manifest_root_hash mismatch." in e for e in errors)
