"""
NeuralBook CLI.

Commands: keygen, init, build, verify, info,
          nb-import, nb-validate, nb-seal, nb-patch, nb-info, nb-export
"""

import json
import os
import re
import sys
from pathlib import Path

try:
    import click
except ImportError:
    print("click not installed. Run: pip install click", file=sys.stderr)
    sys.exit(1)

from .build import build_project, verify_trust_chain
from .export import export_epub, export_html
from .format import (
    NeuralBookDocument,
    import_txt,
    validate_format,
    validate_full,
    validate_integrity,
    validate_structure,
)
from .manifest import compute_hash

VERSION = "1.0.0"


@click.group()
@click.version_option(VERSION, prog_name="neuralbook")
def main():
    """NeuralBook — encrypted digital book platform."""
    pass


@main.command()
@click.option("--length", default=64, show_default=True, help="Seed character length")
def keygen(length):
    """Generate a cryptographically random encryption seed."""
    import base64
    import secrets

    raw = secrets.token_bytes((length * 3) // 4 + 1)
    seed = base64.urlsafe_b64encode(raw).decode()[:length]
    click.echo(seed)
    click.echo("", err=True)
    click.echo("# Set in your shell:", err=True)
    click.echo(f"export NEURALBOOK_ENCRYPTION_SEED='{seed}'", err=True)


@main.command()
@click.argument("project_dir", type=click.Path())
@click.option("--title", prompt="Title", help="Book title")
@click.option("--slug", default=None, help="URL slug (derived from title if omitted)")
def init(project_dir, title, slug):
    """Scaffold a new NeuralBook title at PROJECT_DIR."""
    proj = Path(project_dir)
    if proj.exists() and any(proj.iterdir()):
        raise click.ClickException(f"{proj} already exists and is not empty")

    if not slug:
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")

    for d in ("content", "secrets", "build"):
        (proj / d).mkdir(parents=True, exist_ok=True)

    cfg = {
        "title": title,
        "slug": slug,
        "version": "1.0.0",
        "platform": "neuralbook",
        "encryptionSeedFile": "../secrets/encryption-seed.txt",
    }
    (proj / "title-config.json").write_text(json.dumps(cfg, indent=2) + "\n")
    (proj / "content" / "chapter-01.md").write_text(f"# {title}\n\nYour first chapter.\n")
    (proj / ".gitignore").write_text("secrets/\nbuild/\n*.nd\n__pycache__/\n.env\n")
    (proj / "README.md").write_text(
        f"# {title}\n\nA NeuralBook title.\n\n"
        "## Build\n\n```bash\n"
        "export NEURALBOOK_ENCRYPTION_SEED=$(neuralbook keygen)\n"
        f"neuralbook build {project_dir}\n```\n"
    )

    click.secho(f"\n  Initialized: {proj.resolve()}", fg="green")
    click.echo(f"  Title: {title}  |  Slug: {slug}")
    click.echo("\nNext steps:")
    click.echo(f"  1. Add content files to {proj}/content/")
    click.echo("  2. export NEURALBOOK_ENCRYPTION_SEED=$(neuralbook keygen)")
    click.echo(f"  3. neuralbook build {project_dir}")


@main.command()
@click.argument("project_dir", type=click.Path(exists=True))
@click.option(
    "--build-type",
    default="demo",
    show_default=True,
    type=click.Choice(["demo", "internal", "release", "external"]),
)
@click.option("--output-dir", default=None, type=click.Path())
@click.option("--verbose", "-v", is_flag=True)
def build(project_dir, build_type, output_dir, verbose):
    """Encrypt content and generate manifest for a title project."""
    proj = Path(project_dir)
    out = Path(output_dir) if output_dir else None
    click.secho(f"Building: {proj.resolve()}", bold=True)

    report = build_project(proj, output_dir=out, build_type=build_type, verbose=verbose)

    if report["status"] == "success":
        click.secho("\n  Build complete", fg="green")
        click.echo(f"  Files encrypted : {report['files_encrypted']}")
        click.echo(f"  Plaintext size  : {_human(report['total_plaintext_bytes'])}")
        click.echo(f"  Encrypted size  : {_human(report['total_encrypted_bytes'])}")
        click.echo(f"  Key source      : {report.get('key_source', '?')}")
        click.echo(f"  Manifest        : {report['manifest_path']}")
    else:
        click.secho(f"\n  Build failed ({report['status']})", fg="red", err=True)
        for e in report["errors"]:
            click.echo(f"  {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("manifest_path", type=click.Path(exists=True))
@click.argument("encrypted_dir", type=click.Path(exists=True))
def verify(manifest_path, encrypted_dir):
    """Verify SHA-256 integrity of an encrypted build against its manifest."""
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    enc_dir = Path(encrypted_dir)
    failures = []

    for rel_path, expected in manifest.get("files", {}).items():
        fpath = enc_dir / rel_path
        if not fpath.exists():
            failures.append(f"MISSING  {rel_path}")
        else:
            actual = compute_hash(fpath)
            if actual != expected["sha256"]:
                failures.append(f"MISMATCH {rel_path}")

    total = len(manifest.get("files", {}))
    if failures:
        click.secho(f"  FAIL — {len(failures)}/{total} integrity check(s) failed", fg="red")
        for f in failures:
            click.echo(f"    {f}")
        sys.exit(1)
    else:
        click.secho(f"  PASS — {total}/{total} files verified", fg="green")
        click.echo(f"  Root hash: {manifest.get('root_hash', '?')}")


@main.command("verify-attestation")
@click.argument("manifest_path", type=click.Path(exists=True))
@click.argument("provenance_path", type=click.Path(exists=True))
@click.argument("attestation_path", type=click.Path(exists=True))
@click.option("--require-signature", is_flag=True, help="Fail if provenance has no signature")
@click.option(
    "--allow-embedded-public-key",
    is_flag=True,
    help="Allow verifying signatures using embedded public_key_hex (no trusted registry).",
)
@click.option(
    "--trusted-keys",
    "trusted_keys_path",
    default=None,
    type=click.Path(exists=True),
    help="Path to trusted public keys registry (JSON).",
)
@click.option(
    "--revoked-keys",
    "revoked_keys_path",
    default=None,
    type=click.Path(exists=True),
    help="Path to revoked key IDs list (JSON).",
)
def verify_attestation(
    manifest_path,
    provenance_path,
    attestation_path,
    require_signature,
    allow_embedded_public_key,
    trusted_keys_path,
    revoked_keys_path,
):
    """Verify manifest, provenance, and attestation consistency."""
    att = json.loads(Path(attestation_path).read_text(encoding="utf-8"))
    build_type = str(att.get("build_type", "")).strip()
    strict_release = build_type in {"release", "external"}
    if strict_release:
        require_signature = True

    require_trusted_keys = strict_release and not allow_embedded_public_key

    ok, errors = verify_trust_chain(
        Path(manifest_path),
        Path(provenance_path),
        Path(attestation_path),
        require_signature=require_signature,
        trusted_keys_path=Path(trusted_keys_path) if trusted_keys_path else None,
        revoked_keys_path=Path(revoked_keys_path) if revoked_keys_path else None,
        require_trusted_keys=require_trusted_keys,
    )
    if ok:
        click.secho("  PASS — trust chain verified", fg="green")
        return
    click.secho(f"  FAIL — {len(errors)} trust chain issue(s)", fg="red")
    for item in errors:
        click.echo(f"    {item}")
    sys.exit(1)


@main.group("keys")
def keys_group():
    """Manage trusted keys and revocations JSON files."""
    pass


@keys_group.command("init")
@click.argument("trusted_keys_path", type=click.Path())
@click.argument("revocations_path", type=click.Path())
def keys_init(trusted_keys_path, revocations_path):
    tk = Path(trusted_keys_path)
    rv = Path(revocations_path)
    tk.write_text(json.dumps({"keys": []}, indent=2) + "\n", encoding="utf-8")
    rv.write_text(json.dumps({"revoked_key_ids": []}, indent=2) + "\n", encoding="utf-8")
    click.secho("Initialized keys files.", fg="green")
    click.echo(f"  Trusted:  {tk}")
    click.echo(f"  Revoked:  {rv}")


@keys_group.command("add")
@click.argument("trusted_keys_path", type=click.Path(exists=True))
@click.option("--key-id", required=True)
@click.option("--public-key-hex", required=True)
def keys_add(trusted_keys_path, key_id, public_key_hex):
    path = Path(trusted_keys_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    keys = payload.get("keys", [])
    keys = [k for k in keys if str(k.get("key_id", "")).strip() != key_id]
    keys.append({"key_id": key_id, "public_key_hex": public_key_hex})
    payload["keys"] = sorted(keys, key=lambda k: str(k.get("key_id", "")))
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    click.secho("Key added/updated.", fg="green")


@keys_group.command("revoke")
@click.argument("revocations_path", type=click.Path(exists=True))
@click.option("--key-id", "key_id", required=True)
def keys_revoke(revocations_path, key_id):
    path = Path(revocations_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    revoked = payload.get("revoked_key_ids", [])
    revoked_set = {str(v).strip() for v in revoked if str(v).strip()}
    revoked_set.add(key_id)
    payload["revoked_key_ids"] = sorted(revoked_set)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    click.secho("Key revoked.", fg="yellow")


@main.command()
def info():
    """Show NeuralBook platform info and environment status."""
    click.secho(f"NeuralBook Platform v{VERSION}", bold=True)
    click.echo(f"  Python   : {sys.version.split()[0]}")
    click.echo("  Cipher   : AES-256-GCM")
    click.echo("  KDF      : scrypt (JS-compatible)")
    click.echo("  Format   : .nd [IV:12][AuthTag:16][Ciphertext:N]")
    seed = os.environ.get("NEURALBOOK_ENCRYPTION_SEED", "")
    if seed:
        click.secho(f"  Key      : env var set ({len(seed)} chars)", fg="green")
    else:
        click.secho("  Key      : NOT SET — run: neuralbook keygen", fg="yellow")


def _human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


# ── NeuralBook Commands ────────────────────────────────────────────────────


@main.command("nb-import")
@click.argument("txt_file", type=click.Path(exists=True))
@click.option("--title", default="", help="Book title (derived from filename if omitted)")
@click.option("--author", default="", help="Author name")
@click.option("--slug", default="", help="URL slug (derived from title if omitted)")
@click.option("--output", "-o", default=None, type=click.Path(), help="Output .nbook file path")
def nb_import(txt_file, title, author, slug, output):
    """Import a structured TXT manuscript into NeuralBook (.nbook) format."""
    from pathlib import Path as P

    src = P(txt_file)
    if not title:
        title = src.stem
    if not slug:
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    if not output:
        output = str(src.with_suffix(".nbook"))

    click.secho(f"Importing: {src}", bold=True)
    doc = import_txt(src, title=title, author=author, slug=slug)
    doc.write_file(P(output))

    click.secho(f"\n  Imported: {output}", fg="green")
    click.echo(f"  Title  : {doc.meta['title']}")
    click.echo(f"  Sections: {doc.meta['section_count']}")
    click.echo(f"  Words  : {doc.meta['word_count']:,}")


@main.command("nb-validate")
@click.argument("nbook_file", type=click.Path(exists=True))
@click.option(
    "--level",
    default="full",
    show_default=True,
    type=click.Choice(["structure", "integrity", "format", "full"]),
)
def nb_validate(nbook_file, level):
    """Validate a NeuralBook (.nbook) file."""
    from pathlib import Path as P

    doc = NeuralBookDocument.from_file(P(nbook_file))

    validators = {
        "structure": validate_structure,
        "integrity": validate_integrity,
        "format": validate_format,
        "full": validate_full,
    }
    result = validators[level](doc)

    if result.ok:
        click.secho(f"  PASS — {level} validation", fg="green")
        if result.warnings:
            for w in result.warnings:
                click.secho(f"  WARN: {w}", fg="yellow")
    else:
        click.secho(f"  FAIL — {level} validation ({len(result.errors)} error(s))", fg="red")
        for e in result.errors:
            click.echo(f"    {e}")
        sys.exit(1)


@main.command("nb-seal")
@click.argument("nbook_file", type=click.Path(exists=True))
def nb_seal(nbook_file):
    """Cryptographically seal a NeuralBook (.nbook) file."""
    from pathlib import Path as P

    p = P(nbook_file)
    doc = NeuralBookDocument.from_file(p)

    if doc.neuralbook.get("sealed"):
        click.secho("  Document is already sealed. Re-sealing...", fg="yellow")

    seal = doc.seal_document()
    doc.write_file(p)

    click.secho(f"\n  Sealed: {p}", fg="green")
    click.echo(f"  Root hash : {seal['root_hash'][:32]}...")
    click.echo(f"  Sections  : {len(seal['section_hashes'])}")
    click.echo(f"  Sealed at : {seal['sealed_at']}")


@main.command("nb-patch")
@click.argument("nbook_file", type=click.Path(exists=True))
@click.argument("patch_file", type=click.Path(exists=True))
def nb_patch(nbook_file, patch_file):
    """Apply a patch (.nbook-patch) to a NeuralBook (.nbook) file."""
    from pathlib import Path as P

    p = P(nbook_file)
    doc = NeuralBookDocument.from_file(p)
    patch_data = json.loads(P(patch_file).read_text(encoding="utf-8"))

    click.secho(f"Patching: {p}", bold=True)
    ok, errors = doc.apply_patch(patch_data)

    if ok:
        doc.write_file(p)
        click.secho(f"\n  Patched: {p}", fg="green")
        click.echo(f"  Operations applied: {len(patch_data.get('operations', []))}")
        click.echo(f"  New section count: {doc.meta['section_count']}")
        click.echo(f"  New word count: {doc.meta['word_count']:,}")
    else:
        click.secho(f"\n  Patch failed ({len(errors)} error(s))", fg="red")
        for e in errors:
            click.echo(f"    {e}")
        sys.exit(1)


@main.command("nb-info")
@click.argument("nbook_file", type=click.Path(exists=True))
def nb_info(nbook_file):
    """Display metadata and structure of a NeuralBook (.nbook) file."""
    from pathlib import Path as P

    doc = NeuralBookDocument.from_file(P(nbook_file))

    click.secho("NeuralBook Document Info", bold=True)
    click.echo(f"  Format    : {doc.neuralbook.get('format', '?')}")
    click.echo(f"  Version   : {doc.neuralbook.get('version', '?')}")
    click.echo(f"  Sealed    : {'Yes' if doc.neuralbook.get('sealed') else 'No'}")
    click.echo(f"  Title     : {doc.meta.get('title', '?')}")
    click.echo(f"  Author    : {doc.meta.get('author', '?')}")
    click.echo(f"  Edition   : {doc.meta.get('edition', '?')}")
    click.echo(f"  Sections  : {doc.meta.get('section_count', 0)}")
    click.echo(f"  Words     : {doc.meta.get('word_count', 0):,}")
    click.echo(f"  Patches   : {len(doc.patches)}")
    click.echo(f"  Root hash : {doc.seal.get('root_hash', 'not computed')[:32]}...")

    if doc.toc:
        click.echo("\n  Table of Contents:")
        for entry in doc.toc:
            stype = entry.get("type", "?")[:3].upper()
            num = entry.get("number", "")
            title = entry.get("title", "")
            wc = entry.get("word_count", 0)
            click.echo(f"    [{stype}] {num:>4}: {title} ({wc:,} words)")


@main.command("nb-export")
@click.argument("nbook_file", type=click.Path(exists=True))
@click.option(
    "--format", "fmt", default="epub", show_default=True, type=click.Choice(["epub", "html"])
)
@click.option("--output", "-o", default=None, type=click.Path(), help="Output file path")
def nb_export(nbook_file, fmt, output):
    """Export a NeuralBook (.nbook) file to EPUB or HTML."""
    from pathlib import Path as P

    p = P(nbook_file)
    doc = NeuralBookDocument.from_file(p)

    if not output:
        stem = p.stem
        ext = ".epub" if fmt == "epub" else ".html"
        output = str(p.parent / f"{stem}{ext}")

    click.secho(f"Exporting: {p} → {output} ({fmt})", bold=True)

    if fmt == "epub":
        out = export_epub(doc, P(output))
    else:
        out = export_html(doc, P(output))

    click.secho(f"\n  Exported: {out}", fg="green")
    click.echo(f"  Format  : {fmt}")
    click.echo(f"  Sections: {doc.meta['section_count']}")
    click.echo(f"  Words   : {doc.meta['word_count']:,}")


if __name__ == "__main__":
    main()
