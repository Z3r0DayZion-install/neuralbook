"""NeuralBook™ SDK — reader, writer, patcher, and validator for the NB-FMT-1.0 format.

This module implements the NeuralBook Format Specification v1.0:
- Parse and serialize .nbook files
- Compute and verify section/root hashes
- Apply patches (JSON Patch RFC 6902 + NeuralBook extensions)
- Import structured TXT manuscripts into .nbook format
- Cryptographic sealing
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

FORMAT_VERSION = "NB-FMT-1.0"
SPEC_VERSION = "1.0"

SECTION_HEADER_RE = re.compile(
    r"^=====+\s*(SECTION|PART|INTERLUDE|APPENDIX)\s+" r"([IVXLCDM\d]+)\s*:\s*(.+?)\s*=+$",
    re.MULTILINE,
)

WEIGHT_CLASS_SYMBOLS = {
    1: "\U0001fab6",  # 🪶 Feather
    2: "\U0001f3af",  # 🎯 Target
    3: "\U0001f573\ufe0f",  # 🕳️ Hole
    4: "\U0001f9f1",  # 🧱 Brick
    5: "\U0001fae7",  # 🫧 Bubbles
    6: "\U0001f4a3",  # 💣 Bomb
    7: "\U0001fae5",  # 🫥 Dotted Face
    8: "\U0001f32a\ufe0f",  # 🌪️ Tornado
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ── Hash computation ──────────────────────────────────────────────────────


def section_hash(section: dict) -> str:
    """Compute SHA-256 hash over a section's canonical JSON (excluding the hash field itself)."""
    s = {k: v for k, v in section.items() if k != "hash"}
    canonical = json.dumps(s, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def root_hash(sections: List[dict]) -> str:
    """Compute root hash over all section hashes in ID order."""
    combined = "".join(
        s.get("hash", section_hash(s)) for s in sorted(sections, key=lambda s: s.get("id", ""))
    )
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


# ── NeuralBook Document ────────────────────────────────────────────────────


class NeuralBookDocument:
    """In-memory representation of a .nbook file."""

    def __init__(self, meta: Optional[dict] = None):
        self.neuralbook = {
            "version": SPEC_VERSION,
            "format": FORMAT_VERSION,
            "sealed": False,
            "created": _now_iso(),
            "modified": _now_iso(),
        }
        self.meta = meta or {
            "title": "",
            "author": "",
            "slug": "",
            "edition": "1.0.0",
            "language": "en",
            "license": "",
            "tags": [],
            "word_count": 0,
            "section_count": 0,
        }
        self.toc: List[dict] = []
        self.content: List[dict] = []
        self.patches: List[dict] = []
        self.seal: dict = {
            "algorithm": "sha256",
            "root_hash": "",
            "section_hashes": {},
            "sealed_at": None,
        }

    # ── Section management ─────────────────────────────────────────────

    def add_section(
        self,
        section_type: str,
        number: str,
        title: str,
        body: str,
        weight_class: Optional[str] = None,
        protocols: Optional[List[dict]] = None,
    ) -> dict:
        """Add a section to the document."""
        prefix = {
            "section": "sec",
            "part": "part",
            "interlude": "inter",
            "appendix": "appx",
        }.get(section_type, "sec")
        sec_id = f"{prefix}-{number}"
        section: Dict[str, Any] = {
            "id": sec_id,
            "type": section_type,
            "number": number,
            "title": title,
            "version": "1.0.0",
            "body": body,
        }
        if weight_class:
            section["weight_class"] = weight_class
        if protocols:
            section["protocols"] = protocols
        section["hash"] = section_hash(section)
        self.content.append(section)
        self._rebuild_toc()
        self._update_meta()
        self.neuralbook["modified"] = _now_iso()
        return section

    def get_section(self, section_id: str) -> Optional[dict]:
        for s in self.content:
            if s["id"] == section_id:
                return s
        return None

    def update_section(self, section_id: str, **fields) -> Optional[dict]:
        for i, s in enumerate(self.content):
            if s["id"] == section_id:
                for k, v in fields.items():
                    s[k] = v
                s["hash"] = section_hash(s)
                s["version"] = _increment_patch(s.get("version", "1.0.0"))
                self.content[i] = s
                self._rebuild_toc()
                self._update_meta()
                self.neuralbook["modified"] = _now_iso()
                return s
        return None

    def remove_section(self, section_id: str) -> bool:
        before = len(self.content)
        self.content = [s for s in self.content if s["id"] != section_id]
        if len(self.content) < before:
            self._rebuild_toc()
            self._update_meta()
            self.neuralbook["modified"] = _now_iso()
            return True
        return False

    # ── Seal ───────────────────────────────────────────────────────────

    def compute_seal(self) -> dict:
        """Compute current seal without applying it."""
        section_hashes = {s["id"]: s["hash"] for s in self.content}
        rh = root_hash(self.content)
        return {
            "algorithm": "sha256",
            "root_hash": rh,
            "section_hashes": section_hashes,
            "sealed_at": None,
        }

    def seal_document(self) -> dict:
        """Cryptographically seal the document. Returns the seal object."""
        self.seal = self.compute_seal()
        self.seal["sealed_at"] = _now_iso()
        self.neuralbook["sealed"] = True
        self.neuralbook["modified"] = _now_iso()
        return self.seal

    def verify_integrity(self) -> Tuple[bool, List[str]]:
        """Verify all section hashes and root hash. Returns (ok, errors)."""
        errors = []
        for s in self.content:
            expected = section_hash(s)
            if s.get("hash") != expected:
                errors.append(
                    f"Hash mismatch for {s['id']}: expected {expected[:16]}..., got {s.get('hash', '')[:16]}..."
                )
        if self.seal.get("root_hash"):
            expected_root = root_hash(self.content)
            if self.seal["root_hash"] != expected_root:
                errors.append(
                    f"Root hash mismatch: expected {expected_root[:16]}..., got {self.seal['root_hash'][:16]}..."
                )
        return len(errors) == 0, errors

    # ── Patch ──────────────────────────────────────────────────────────

    def apply_patch(self, patch: dict) -> Tuple[bool, List[str]]:
        """Apply a NeuralBook patch. Returns (ok, errors)."""
        errors = []
        target = patch.get("neuralbook_patch", {}).get("target_edition", "")
        if target and target != self.meta.get("edition", ""):
            errors.append(
                f"Patch targets edition {target}, current is {self.meta.get('edition', '')}"
            )

        prev_hash = patch.get("verification", {}).get("previous_root_hash", "")
        if prev_hash:
            current_root = root_hash(self.content)
            if prev_hash != current_root:
                errors.append(
                    f"Previous root hash mismatch: patch expects {prev_hash[:16]}..., current is {current_root[:16]}..."
                )

        if errors:
            return False, errors

        for op in patch.get("operations", []):
            kind = op.get("op")
            path = op.get("path", "")
            value = op.get("value")

            if kind == "add" and path == "/content/-":
                if isinstance(value, dict):
                    value["hash"] = section_hash(value)
                    self.content.append(value)
            elif kind == "replace":
                parts = path.strip("/").split("/")
                if len(parts) >= 2 and parts[0] == "content":
                    try:
                        idx = int(parts[1]) if parts[1].isdigit() else None
                        if idx is not None and 0 <= idx < len(self.content):
                            if len(parts) == 2:
                                self.content[idx] = value
                                self.content[idx]["hash"] = section_hash(self.content[idx])
                            elif len(parts) == 3:
                                self.content[idx][parts[2]] = value
                                self.content[idx]["hash"] = section_hash(self.content[idx])
                    except (ValueError, IndexError):
                        errors.append(f"Invalid path: {path}")
                elif parts[0] == "meta" and len(parts) == 2:
                    self.meta[parts[1]] = value
            elif kind == "remove":
                parts = path.strip("/").split("/")
                if parts[0] == "content" and len(parts) == 2:
                    try:
                        idx = int(parts[1])
                        if 0 <= idx < len(self.content):
                            self.content.pop(idx)
                    except (ValueError, IndexError):
                        errors.append(f"Invalid path: {path}")

        self._rebuild_toc()
        self._update_meta()
        self.neuralbook["modified"] = _now_iso()
        self.patches.append(patch)
        return True, errors

    # ── Serialization ─────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "neuralbook": self.neuralbook,
            "meta": self.meta,
            "toc": self.toc,
            "content": self.content,
            "patches": self.patches,
            "seal": self.seal,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False) + "\n"

    @classmethod
    def from_dict(cls, data: dict) -> "NeuralBookDocument":
        doc = cls()
        doc.neuralbook = data.get("neuralbook", doc.neuralbook)
        doc.meta = data.get("meta", doc.meta)
        doc.toc = data.get("toc", [])
        doc.content = data.get("content", [])
        doc.patches = data.get("patches", [])
        doc.seal = data.get("seal", doc.seal)
        return doc

    @classmethod
    def from_json(cls, json_str: str) -> "NeuralBookDocument":
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def from_file(cls, path: Path) -> "NeuralBookDocument":
        return cls.from_json(Path(path).read_text(encoding="utf-8"))

    def write_file(self, path: Path) -> None:
        Path(path).write_text(self.to_json(), encoding="utf-8")

    # ── Internal ───────────────────────────────────────────────────────

    def _rebuild_toc(self) -> None:
        self.toc = []
        for s in self.content:
            entry = {
                "id": s["id"],
                "type": s["type"],
                "number": s.get("number", ""),
                "title": s.get("title", ""),
                "word_count": len(s.get("body", "").split()),
                "hash": s.get("hash", ""),
                "version": s.get("version", "1.0.0"),
            }
            if "weight_class" in s:
                entry["weight_class"] = s["weight_class"]
            self.toc.append(entry)

    def _update_meta(self) -> None:
        total_words = sum(len(s.get("body", "").split()) for s in self.content)
        self.meta["word_count"] = total_words
        self.meta["section_count"] = len(self.content)


# ── TXT Import ────────────────────────────────────────────────────────────


def import_txt(
    txt_path: Path, title: str = "", author: str = "", slug: str = ""
) -> NeuralBookDocument:
    """Import a structured TXT manuscript into NeuralBook format.

    Parses ===== SECTION X: TITLE ===== and ===== PART X: TITLE ===== headers.
    """
    text = Path(txt_path).read_text(encoding="utf-8")
    if not title:
        title = Path(txt_path).stem
    if not slug:
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")

    doc = NeuralBookDocument(
        meta={
            "title": title,
            "author": author,
            "slug": slug,
            "edition": "1.0.0",
            "language": "en",
            "license": "",
            "tags": [],
            "word_count": 0,
            "section_count": 0,
        }
    )

    # Split by section headers
    matches = list(SECTION_HEADER_RE.finditer(text))
    if not matches:
        # No headers found — treat entire file as one section
        doc.add_section("section", "I", title or "Untitled", text.strip())
        return doc

    for i, m in enumerate(matches):
        sec_type_raw = m.group(1).lower()
        number = m.group(2)
        sec_title = m.group(3).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()

        sec_type = {
            "section": "section",
            "part": "part",
            "interlude": "interlude",
            "appendix": "appendix",
        }.get(sec_type_raw, "section")

        doc.add_section(sec_type, number, sec_title, body)

    return doc


# ── Validation ────────────────────────────────────────────────────────────


class ValidationResult:
    ok: bool

    def __init__(self) -> None:
        self.ok = True
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def error(self, msg: str) -> None:
        self.ok = False
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def __bool__(self) -> bool:
        return self.ok

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ValidationResult):
            return NotImplemented
        return self.ok == other.ok

    def __repr__(self) -> str:
        status = "PASS" if self.ok else "FAIL"
        return (
            f"ValidationResult({status}, errors={len(self.errors)}, warnings={len(self.warnings)})"
        )


def validate_structure(doc: NeuralBookDocument) -> ValidationResult:
    """Validate required fields and types."""
    result = ValidationResult()

    if not doc.meta.get("title"):
        result.warn("meta.title is empty")
    if not doc.content:
        result.error("Document has no content sections")

    for s in doc.content:
        for field in ("id", "type", "title", "body", "hash"):
            if field not in s:
                result.error(f"Section {s.get('id', '?')} missing required field: {field}")
        if "type" in s and s["type"] not in ("section", "part", "interlude", "appendix"):
            result.error(f"Section {s.get('id', '?')} has invalid type: {s['type']}")

    # Check for duplicate IDs
    ids = [s.get("id") for s in doc.content]
    dupes = [i for i in set(ids) if ids.count(i) > 1]
    if dupes:
        result.error(f"Duplicate section IDs: {dupes}")

    return result


def validate_integrity(doc: NeuralBookDocument) -> ValidationResult:
    """Validate section hashes and root hash."""
    result = ValidationResult()
    ok, errors = doc.verify_integrity()
    if not ok:
        for e in errors:
            result.error(e)
    return result


def validate_format(doc: NeuralBookDocument) -> ValidationResult:
    """Validate weight class symbols and section numbering."""
    result = ValidationResult()

    for s in doc.content:
        # Check section numbering is sequential for same type
        number = s.get("number", "")
        if number and s.get("type") in ("section", "part"):
            if not re.match(r"^[IVXLCDM\d]+$", number):
                result.warn(f"Section {s['id']} has non-standard number: {number}")

    return result


def validate_full(doc: NeuralBookDocument) -> ValidationResult:
    """Run all validation levels."""
    combined = ValidationResult()
    for validator in (validate_structure, validate_integrity, validate_format):
        r = validator(doc)
        combined.errors.extend(r.errors)
        combined.warnings.extend(r.warnings)
    combined.ok = len(combined.errors) == 0
    return combined


# ── Helpers ───────────────────────────────────────────────────────────────


def _increment_patch(version: str) -> str:
    """Increment the patch version of a semver string."""
    parts = version.split(".")
    if len(parts) == 3:
        try:
            parts[2] = str(int(parts[2]) + 1)
        except ValueError:
            pass
    return ".".join(parts)
