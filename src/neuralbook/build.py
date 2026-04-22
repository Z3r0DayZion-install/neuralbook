"""NeuralBook build pipeline: discover -> encrypt -> manifest."""
from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from .encryption import ND_EXTENSION, discover_key, encrypt_file
from .manifest import compute_hash

CONTENT_EXTENSIONS = {".txt",".md",".html",".json",".js",".css",".jpg",".jpeg",".png",".gif",".svg",".webp",".mp3",".mp4",".webm"}
IGNORE_PATTERNS = {"node_modules",".git","__pycache__",".DS_Store","build","dist"}

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

def build_project(project_dir: Path, output_dir: Optional[Path] = None, build_type: str = "demo", title_config: Optional[dict] = None, verbose: bool = False) -> Dict:
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
    report: Dict = {"status":"pending","build_type":build_type,"project_dir":str(project_dir),"started_at":started_at,"finished_at":"","title":"","key_source":"","files_encrypted":0,"files_failed":0,"total_plaintext_bytes":0,"total_encrypted_bytes":0,"manifest_path":"","errors":[]}

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
        report["errors"].append("No content directory found. Expected content/, plaintext-content/, or book/")
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
            encrypted_entries.append({"relative_path":rel,"sha256":sha256,"plaintext_size":f["size"],"encrypted_size":enc_size})
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
    manifest = {"title":title_name,"version":"1.0","generated":started_at,"files":{e["relative_path"]+ND_EXTENSION:{"sha256":e["sha256"],"plaintext_size":e["plaintext_size"],"encrypted_size":e["encrypted_size"]} for e in encrypted_entries},"root_hash":_root_hash(encrypted_entries)}
    mp = output_dir.parent / f"MANIFEST_{safe}.json"
    mp.write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    report["manifest_path"] = str(mp)
    report["status"] = "success" if report["files_failed"] == 0 else "partial"
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    if verbose:
        print(f"\nDone: {report['files_encrypted']} files. Manifest: {mp}")
    return report

def _root_hash(entries: List[Dict]) -> str:
    combined = json.dumps({e["relative_path"]:e["sha256"] for e in sorted(entries, key=lambda x: x["relative_path"])}, sort_keys=True)
    return hashlib.sha256(combined.encode()).hexdigest()
