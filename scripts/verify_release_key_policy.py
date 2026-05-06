"""CI gate to enforce release key policy and provenance signing."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from neuralbook.build import build_project
from neuralbook.encryption import KeySourceError, discover_key


def _assert_release_seed_policy() -> None:
    os.environ.pop("NEURALBOOK_ENCRYPTION_SEED", None)
    cfg = {"encryptionSeed": "seed-abcdefghijklmnopqrstuvwxyz1234567890"}
    try:
        discover_key(cfg, build_type="release")
    except KeySourceError:
        return
    raise RuntimeError("Release build accepted plaintext config seed; policy violation.")


def _assert_provenance_signature() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir) / "release-policy-title"
        content = root / "content"
        content.mkdir(parents=True, exist_ok=True)
        (content / "chapter-01.md").write_text("Release policy gate content.\n", encoding="utf-8")

        key = Ed25519PrivateKey.generate()
        os.environ["NEURALBOOK_PROVENANCE_SIGNING_KEY_HEX"] = key.private_bytes_raw().hex()
        os.environ["NEURALBOOK_PROVENANCE_KEY_ID"] = "ci-ephemeral"
        os.environ["NEURALBOOK_ENCRYPTION_SEED"] = "seed-abcdefghijklmnopqrstuvwxyz1234567890"
        cfg = {"title": "ReleasePolicy"}
        report = build_project(root, title_config=cfg, build_type="release")
        if report["status"] != "success":
            raise RuntimeError(f"Build failed while testing provenance signature: {report}")

        provenance = json.loads(Path(report["provenance_path"]).read_text(encoding="utf-8"))
        signature = provenance.get("signature")
        if not signature:
            raise RuntimeError("Provenance signature missing.")
        if signature.get("algorithm") != "ed25519":
            raise RuntimeError("Unexpected provenance signature algorithm.")

        public_key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(signature["public_key_hex"]))
        public_key.verify(
            bytes.fromhex(signature["fingerprint_signature_hex"]),
            provenance["build_fingerprint"].encode("utf-8"),
        )


def main() -> int:
    _assert_release_seed_policy()
    _assert_provenance_signature()
    print("Release key policy gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
