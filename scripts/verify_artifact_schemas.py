"""CI gate to validate manifest/provenance/attestation schema conformance."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from neuralbook.build import build_project


def _validate_schema(data, schema, path="$"):
    expected_type = schema.get("type")
    if isinstance(expected_type, list):
        if not any(_type_matches(data, t) for t in expected_type):
            raise RuntimeError(
                f"{path}: expected one of {expected_type}, got {type(data).__name__}"
            )
    elif expected_type and not _type_matches(data, expected_type):
        raise RuntimeError(f"{path}: expected {expected_type}, got {type(data).__name__}")

    required = schema.get("required", [])
    if isinstance(data, dict):
        for key in required:
            if key not in data:
                raise RuntimeError(f"{path}: missing required key '{key}'")

    if "const" in schema and data != schema["const"]:
        raise RuntimeError(f"{path}: expected const value {schema['const']!r}, got {data!r}")

    if isinstance(data, str):
        min_len = schema.get("minLength")
        max_len = schema.get("maxLength")
        if min_len is not None and len(data) < min_len:
            raise RuntimeError(f"{path}: string shorter than minLength {min_len}")
        if max_len is not None and len(data) > max_len:
            raise RuntimeError(f"{path}: string longer than maxLength {max_len}")
    if isinstance(data, int):
        minimum = schema.get("minimum")
        if minimum is not None and data < minimum:
            raise RuntimeError(f"{path}: integer smaller than minimum {minimum}")

    if isinstance(data, dict):
        properties = schema.get("properties", {})
        for key, subschema in properties.items():
            if key in data:
                _validate_schema(data[key], subschema, f"{path}.{key}")
        additional = schema.get("additionalProperties")
        if additional and isinstance(additional, dict):
            for key, value in data.items():
                if key not in properties:
                    _validate_schema(value, additional, f"{path}.{key}")

    if isinstance(data, list):
        min_items = schema.get("minItems")
        if min_items is not None and len(data) < min_items:
            raise RuntimeError(f"{path}: array shorter than minItems {min_items}")
        item_schema = schema.get("items")
        if item_schema:
            for idx, item in enumerate(data):
                _validate_schema(item, item_schema, f"{path}[{idx}]")


def _type_matches(value, schema_type: str) -> bool:
    mapping = {
        "object": dict,
        "array": list,
        "string": str,
        "integer": int,
        "null": type(None),
    }
    py_type = mapping.get(schema_type)
    return isinstance(value, py_type) if py_type else True


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    schema_dir = repo_root / "schemas"
    manifest_schema = json.loads((schema_dir / "manifest.schema.json").read_text(encoding="utf-8"))
    provenance_schema = json.loads(
        (schema_dir / "provenance.schema.json").read_text(encoding="utf-8")
    )
    attestation_schema = json.loads(
        (schema_dir / "attestation.schema.json").read_text(encoding="utf-8")
    )
    trusted_keys_schema = json.loads(
        (schema_dir / "trusted_keys.schema.json").read_text(encoding="utf-8")
    )
    revocations_schema = json.loads(
        (schema_dir / "revocations.schema.json").read_text(encoding="utf-8")
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir) / "schema-title"
        content = root / "content"
        content.mkdir(parents=True, exist_ok=True)
        (content / "chapter-01.md").write_text("Schema gate content.\n", encoding="utf-8")

        cfg = {
            "title": "SchemaTitle",
            "encryptionSeed": "seed-abcdefghijklmnopqrstuvwxyz1234567890",
        }
        report = build_project(root, title_config=cfg, build_type="demo")
        if report["status"] != "success":
            raise RuntimeError(f"Build failed in schema gate: {report}")

        manifest = json.loads(Path(report["manifest_path"]).read_text(encoding="utf-8"))
        provenance = json.loads(Path(report["provenance_path"]).read_text(encoding="utf-8"))
        attestation = json.loads(Path(report["attestation_path"]).read_text(encoding="utf-8"))

        _validate_schema(manifest, manifest_schema, "$manifest")
        _validate_schema(provenance, provenance_schema, "$provenance")
        _validate_schema(attestation, attestation_schema, "$attestation")

        # Validate trust artifacts (schemas only; content is example).
        _validate_schema(
            {"keys": [{"key_id": "primary", "public_key_hex": "0" * 64}]},
            trusted_keys_schema,
            "$trusted_keys",
        )
        _validate_schema({"revoked_key_ids": ["k1"]}, revocations_schema, "$revocations")

        print("Artifact schema gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
