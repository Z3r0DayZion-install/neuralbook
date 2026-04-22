"""
NeuralBook CLI.

Commands: keygen, init, build, verify, info
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

from .build import build_project
from .encryption import discover_key
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
@click.option("--build-type", default="demo", show_default=True,
              type=click.Choice(["demo", "internal", "release", "external"]))
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


@main.command()
def info():
    """Show NeuralBook platform info and environment status."""
    click.secho(f"NeuralBook Platform v{VERSION}", bold=True)
    click.echo(f"  Python   : {sys.version.split()[0]}")
    click.echo(f"  Cipher   : AES-256-GCM")
    click.echo(f"  KDF      : scrypt (JS-compatible)")
    click.echo(f"  Format   : .nd [IV:12][AuthTag:16][Ciphertext:N]")
    seed = os.environ.get("NEURALBOOK_ENCRYPTION_SEED", "")
    if seed:
        click.secho(f"  Key      : env var set ({len(seed)} chars)", fg="green")
    else:
        click.secho(f"  Key      : NOT SET — run: neuralbook keygen", fg="yellow")


def _human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"
