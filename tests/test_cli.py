"""Tests for NeuralBook CLI commands."""

import json
from pathlib import Path

from click.testing import CliRunner

import neuralbook.cli as cli_mod
from neuralbook.build import build_project


def test_keygen_outputs_requested_length():
    runner = CliRunner()
    result = runner.invoke(cli_mod.main, ["keygen", "--length", "32"])

    assert result.exit_code == 0
    lines = [line for line in result.output.splitlines() if line.strip()]
    assert len(lines[0]) == 32
    assert "NEURALBOOK_ENCRYPTION_SEED" in result.output


def test_info_reports_env_key_status(monkeypatch):
    runner = CliRunner()
    monkeypatch.setenv("NEURALBOOK_ENCRYPTION_SEED", "abc123")

    result = runner.invoke(cli_mod.main, ["info"])

    assert result.exit_code == 0
    assert "NeuralBook Platform v1.0.0" in result.output
    assert "env var set (6 chars)" in result.output


def test_init_creates_project_structure(tmp_path):
    runner = CliRunner()
    project_dir = tmp_path / "demo-title"

    result = runner.invoke(
        cli_mod.main,
        ["init", str(project_dir), "--title", "Demo Title", "--slug", "demo-title"],
    )

    assert result.exit_code == 0
    assert (project_dir / "content" / "chapter-01.md").exists()
    assert (project_dir / "secrets").exists()
    assert (project_dir / "build").exists()

    cfg = json.loads((project_dir / "title-config.json").read_text(encoding="utf-8"))
    assert cfg["title"] == "Demo Title"
    assert cfg["slug"] == "demo-title"


def test_build_command_success(monkeypatch, tmp_path):
    runner = CliRunner()
    project_dir = tmp_path / "p"
    project_dir.mkdir()

    def fake_build_project(proj, output_dir=None, build_type="demo", verbose=False):
        return {
            "status": "success",
            "files_encrypted": 2,
            "total_plaintext_bytes": 1024,
            "total_encrypted_bytes": 2048,
            "key_source": "env",
            "manifest_path": "manifest.json",
        }

    monkeypatch.setattr(cli_mod, "build_project", fake_build_project)
    result = runner.invoke(cli_mod.main, ["build", str(project_dir)])

    assert result.exit_code == 0
    assert "Build complete" in result.output
    assert "Files encrypted : 2" in result.output
    assert "Key source      : env" in result.output


def test_build_command_failure(monkeypatch, tmp_path):
    runner = CliRunner()
    project_dir = tmp_path / "p"
    project_dir.mkdir()

    def fake_build_project(proj, output_dir=None, build_type="demo", verbose=False):
        return {"status": "error", "errors": ["boom"]}

    monkeypatch.setattr(cli_mod, "build_project", fake_build_project)
    result = runner.invoke(cli_mod.main, ["build", str(project_dir)])

    assert result.exit_code != 0
    assert "Build failed (error)" in result.output
    assert "boom" in result.output


def test_verify_command_pass(tmp_path):
    runner = CliRunner()
    enc_dir = tmp_path / "enc"
    enc_dir.mkdir()
    encrypted_file = enc_dir / "a.nd"
    encrypted_file.write_bytes(b"hello")

    manifest = {
        "files": {"a.nd": {"sha256": cli_mod.compute_hash(encrypted_file)}},
        "root_hash": "abc",
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = runner.invoke(cli_mod.main, ["verify", str(manifest_path), str(enc_dir)])

    assert result.exit_code == 0
    assert "PASS" in result.output


def test_verify_command_fail_on_missing_file(tmp_path):
    runner = CliRunner()
    enc_dir = tmp_path / "enc"
    enc_dir.mkdir()

    manifest = {"files": {"missing.nd": {"sha256": "deadbeef"}}}
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = runner.invoke(cli_mod.main, ["verify", str(manifest_path), str(enc_dir)])

    assert result.exit_code != 0
    assert "FAIL" in result.output
    assert "MISSING  missing.nd" in result.output


def test_nb_import_creates_nbook_file(tmp_path):
    runner = CliRunner()
    txt = tmp_path / "book.txt"
    txt.write_text(
        "===== SECTION I: Start =====\n"
        "Hello section body.\n"
        "===== SECTION II: Next =====\n"
        "Another body.\n",
        encoding="utf-8",
    )
    out = tmp_path / "book.nbook"

    result = runner.invoke(
        cli_mod.main,
        ["nb-import", str(txt), "--title", "Book", "--author", "A", "-o", str(out)],
    )

    assert result.exit_code == 0
    assert out.exists()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["meta"]["title"] == "Book"


def test_nb_info_prints_document_metadata(tmp_path):
    runner = CliRunner()
    doc_path = tmp_path / "demo.nbook"
    doc = cli_mod.NeuralBookDocument(meta={"title": "Demo", "author": "Me"})
    doc.add_section("section", "I", "First", "Body")
    doc.write_file(Path(doc_path))

    result = runner.invoke(cli_mod.main, ["nb-info", str(doc_path)])

    assert result.exit_code == 0
    assert "NeuralBook Document Info" in result.output
    assert "Title     : Demo" in result.output


def test_verify_attestation_command_pass_and_fail(tmp_path):
    runner = CliRunner()
    project = tmp_path / "attest-title"
    content = project / "content"
    content.mkdir(parents=True)
    (content / "chapter-01.md").write_text("trust chain", encoding="utf-8")

    cfg = {"title": "Attest", "encryptionSeed": "seed-abcdefghijklmnopqrstuvwxyz1234567890"}
    report = build_project(project, title_config=cfg, build_type="demo")
    manifest_path = report["manifest_path"]
    provenance_path = report["provenance_path"]
    attestation_path = report["attestation_path"]

    ok_result = runner.invoke(
        cli_mod.main,
        ["verify-attestation", manifest_path, provenance_path, attestation_path],
    )
    assert ok_result.exit_code == 0
    assert "PASS — trust chain verified" in ok_result.output

    attestation = json.loads(Path(attestation_path).read_text(encoding="utf-8"))
    attestation["build_fingerprint"] = "0" * 64
    Path(attestation_path).write_text(json.dumps(attestation, indent=2) + "\n", encoding="utf-8")

    bad_result = runner.invoke(
        cli_mod.main,
        ["verify-attestation", manifest_path, provenance_path, attestation_path],
    )
    assert bad_result.exit_code != 0
    assert "FAIL" in bad_result.output


def test_verify_attestation_require_signature_fails_without_signature(tmp_path):
    runner = CliRunner()
    project = tmp_path / "attest-nosign"
    content = project / "content"
    content.mkdir(parents=True)
    (content / "chapter-01.md").write_text("trust chain nosign", encoding="utf-8")

    cfg = {"title": "AttestNoSign", "encryptionSeed": "seed-abcdefghijklmnopqrstuvwxyz1234567890"}
    report = build_project(project, title_config=cfg, build_type="demo")

    result = runner.invoke(
        cli_mod.main,
        [
            "verify-attestation",
            report["manifest_path"],
            report["provenance_path"],
            report["attestation_path"],
            "--require-signature",
        ],
    )
    assert result.exit_code != 0
    assert "required but missing" in result.output


def test_verify_attestation_with_trusted_keys_and_revocation(tmp_path, monkeypatch):
    import json

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    runner = CliRunner()
    project = tmp_path / "attest-trust"
    content = project / "content"
    content.mkdir(parents=True)
    (content / "chapter-01.md").write_text("trust chain signed", encoding="utf-8")

    key = Ed25519PrivateKey.generate()
    monkeypatch.setenv("NEURALBOOK_PROVENANCE_SIGNING_KEY_HEX", key.private_bytes_raw().hex())
    monkeypatch.setenv("NEURALBOOK_PROVENANCE_KEY_ID", "k1")
    cfg = {"title": "Trust", "encryptionSeed": "seed-abcdefghijklmnopqrstuvwxyz1234567890"}
    report = build_project(project, title_config=cfg, build_type="demo")

    prov = json.loads(Path(report["provenance_path"]).read_text(encoding="utf-8"))
    trusted_path = tmp_path / "trusted-keys.json"
    trusted_path.write_text(
        json.dumps(
            {
                "keys": [
                    {"key_id": "k1", "public_key_hex": prov["signature"]["public_key_hex"]},
                ]
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    ok = runner.invoke(
        cli_mod.main,
        [
            "verify-attestation",
            report["manifest_path"],
            report["provenance_path"],
            report["attestation_path"],
            "--trusted-keys",
            str(trusted_path),
        ],
    )
    assert ok.exit_code == 0

    revoked_path = tmp_path / "revoked.json"
    revoked_path.write_text(
        json.dumps({"revoked_key_ids": ["k1"]}, indent=2) + "\n", encoding="utf-8"
    )
    bad = runner.invoke(
        cli_mod.main,
        [
            "verify-attestation",
            report["manifest_path"],
            report["provenance_path"],
            report["attestation_path"],
            "--trusted-keys",
            str(trusted_path),
            "--revoked-keys",
            str(revoked_path),
        ],
    )
    assert bad.exit_code != 0
    assert "revoked" in bad.output


def test_verify_attestation_release_requires_trusted_keys_by_default(tmp_path, monkeypatch):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    runner = CliRunner()
    project = tmp_path / "attest-release"
    content = project / "content"
    content.mkdir(parents=True)
    (content / "chapter-01.md").write_text("release strict", encoding="utf-8")

    key = Ed25519PrivateKey.generate()
    monkeypatch.setenv("NEURALBOOK_PROVENANCE_SIGNING_KEY_HEX", key.private_bytes_raw().hex())
    monkeypatch.setenv("NEURALBOOK_PROVENANCE_KEY_ID", "krel")
    monkeypatch.setenv("NEURALBOOK_ENCRYPTION_SEED", "seed-abcdefghijklmnopqrstuvwxyz1234567890")

    cfg = {"title": "ReleaseStrict"}
    report = build_project(project, title_config=cfg, build_type="release")
    assert report["status"] == "success"

    # Should fail: release/external defaults require trusted registry (unless allow-embedded-public-key).
    bad = runner.invoke(
        cli_mod.main,
        [
            "verify-attestation",
            report["manifest_path"],
            report["provenance_path"],
            report["attestation_path"],
        ],
    )
    assert bad.exit_code != 0
    assert "Trusted keys registry is required" in bad.output

    # Should pass with allow-embedded-public-key.
    ok = runner.invoke(
        cli_mod.main,
        [
            "verify-attestation",
            report["manifest_path"],
            report["provenance_path"],
            report["attestation_path"],
            "--allow-embedded-public-key",
        ],
    )
    assert ok.exit_code == 0


def test_keys_init_add_revoke_round_trip(tmp_path):
    runner = CliRunner()
    trusted = tmp_path / "trusted.json"
    revoked = tmp_path / "revoked.json"

    res = runner.invoke(cli_mod.main, ["keys", "init", str(trusted), str(revoked)])
    assert res.exit_code == 0
    assert trusted.exists()
    assert revoked.exists()

    add = runner.invoke(
        cli_mod.main,
        [
            "keys",
            "add",
            str(trusted),
            "--key-id",
            "k1",
            "--public-key-hex",
            "0" * 64,
        ],
    )
    assert add.exit_code == 0
    payload = json.loads(trusted.read_text(encoding="utf-8"))
    assert payload["keys"][0]["key_id"] == "k1"

    rev = runner.invoke(cli_mod.main, ["keys", "revoke", str(revoked), "--key-id", "k1"])
    assert rev.exit_code == 0
    rpayload = json.loads(revoked.read_text(encoding="utf-8"))
    assert "k1" in rpayload["revoked_key_ids"]
