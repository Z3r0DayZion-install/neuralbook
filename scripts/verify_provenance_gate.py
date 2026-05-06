"""CI gate to enforce build provenance generation and integrity."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from neuralbook.build import build_project, verify_trust_chain


def main() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir) / "gate-title"
        content = root / "content"
        content.mkdir(parents=True, exist_ok=True)
        (content / "chapter-01.md").write_text("Provenance gate test content.\n", encoding="utf-8")

        cfg = {
            "title": "Gate Title",
            "encryptionSeed": "seed-abcdefghijklmnopqrstuvwxyz1234567890",
        }
        report = build_project(root, title_config=cfg, build_type="demo")
        if report["status"] != "success":
            raise RuntimeError(f"Build failed in provenance gate: {report}")

        manifest_path = Path(report["manifest_path"])
        provenance_path = Path(report["provenance_path"])
        attestation_path = Path(report["attestation_path"])
        if (
            not manifest_path.exists()
            or not provenance_path.exists()
            or not attestation_path.exists()
        ):
            raise RuntimeError(
                "Manifest, provenance, or attestation file missing from build output."
            )

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
        attestation = json.loads(attestation_path.read_text(encoding="utf-8"))

        required_keys = {
            "schema_version",
            "generated_at",
            "build_started_at",
            "title",
            "build_type",
            "key_source",
            "project_dir",
            "content_dir",
            "manifest_root_hash",
            "manifest_sha256",
            "source_entries",
            "build_fingerprint",
        }
        missing = required_keys.difference(provenance.keys())
        if missing:
            raise RuntimeError(f"Provenance missing required keys: {sorted(missing)}")

        if provenance["manifest_root_hash"] != manifest["root_hash"]:
            raise RuntimeError("Provenance manifest_root_hash does not match manifest root_hash.")

        if not provenance["source_entries"]:
            raise RuntimeError("Provenance source_entries must not be empty.")

        fingerprint = provenance["build_fingerprint"]
        if not isinstance(fingerprint, str) or len(fingerprint) != 64:
            raise RuntimeError(
                "Provenance build_fingerprint is not a valid sha256 hex string length."
            )

        if attestation.get("manifest_root_hash") != manifest["root_hash"]:
            raise RuntimeError("Attestation manifest_root_hash does not match manifest root_hash.")
        if attestation.get("build_fingerprint") != provenance["build_fingerprint"]:
            raise RuntimeError("Attestation build_fingerprint does not match provenance.")

        ok, errors = verify_trust_chain(manifest_path, provenance_path, attestation_path)
        if not ok:
            raise RuntimeError(f"Trust-chain verification failed: {errors}")

        print("Provenance gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
