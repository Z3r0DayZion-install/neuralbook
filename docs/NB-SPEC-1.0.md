# NeuralBook™ Format Specification v1.0

**Status:** Draft  
**Date:** 2026-04-21  
**Author:** NeuralBook Project  
**License:** MIT (specification); NeuralBook™ trademark reserved

---

## 1. Overview

NeuralBook™ is an open book format designed for **living documents** — books that are modular, patchable, cryptographically sealed, and executable. Unlike static formats (EPUB, PDF), a NeuralBook file is an active interface: each section contains deployable protocols, and the file can receive patches without full replacement.

### 1.1 Design Goals

- **Modular**: Each section is self-contained and independently addressable
- **Patchable**: Updates delivered as diffs, not full replacements
- **Sealed**: Cryptographic integrity verification on every read
- **Executable**: Sections contain operational instructions, not just prose
- **Upgradeable**: Format versioning allows forward-compatible extensions
- **Encrypted**: AES-256-GCM encryption of content at rest (`.nd` wire format)

### 1.2 Comparison with Existing Formats

| Feature | EPUB | PDF | NeuralBook |
|---------|------|-----|-----------|
| Static content | ✅ | ✅ | ❌ (living) |
| Modular sections | Partial | ❌ | ✅ |
| Patch-based updates | ❌ | ❌ | ✅ |
| Cryptographic seal | ❌ | ✅ (signing) | ✅ (per-section) |
| Encryption at rest | ❌ | ✅ (password) | ✅ (AES-256-GCM) |
| Executable protocols | ❌ | ❌ | ✅ |
| Version tracking | ✅ (metadata) | ❌ | ✅ (per-section) |
| Integrity verification | ❌ | ❌ | ✅ (SHA-256) |

---

## 2. File Format

### 2.1 File Extension

- **Recommended**: `.nbook`
- **Encrypted wire format**: `.nd` (existing NeuralBook encrypted format)
- **MIME type**: `application/x-nbook+json` (plaintext) / `application/x-nbook-encrypted` (`.nd`)

### 2.2 Plaintext Structure

A NeuralBook file is a JSON document with the following top-level structure:

```json
{
  "neuralbook": {
    "version": "1.0",
    "format": "NB-FMT-1.0",
    "sealed": false,
    "created": "2026-04-21T00:00:00Z",
    "modified": "2026-04-21T00:00:00Z"
  },
  "meta": {
    "title": "",
    "author": "",
    "slug": "",
    "edition": "1.0.0",
    "language": "en",
    "license": "",
    "tags": [],
    "word_count": 0,
    "section_count": 0
  },
  "toc": [
    {
      "id": "sec-I",
      "type": "section",
      "number": "I",
      "title": "The Scales of Speech",
      "weight_class": "Pro-Ton",
      "word_count": 0,
      "hash": "sha256:...",
      "version": "1.0.0"
    }
  ],
  "content": [
    {
      "id": "sec-I",
      "type": "section",
      "number": "I",
      "title": "The Scales of Speech",
      "weight_class": "Pro-Ton",
      "version": "1.0.0",
      "body": "...",
      "protocols": [],
      "hash": "sha256:..."
    }
  ],
  "patches": [],
  "seal": {
    "algorithm": "sha256",
    "root_hash": "...",
    "section_hashes": {},
    "sealed_at": null
  }
}
```

### 2.3 Section Types

| Type | Description | Required Fields |
|------|-------------|----------------|
| `section` | Major doctrinal division | `id`, `number`, `title`, `body` |
| `part` | Operational protocol | `id`, `number`, `title`, `body`, `protocols` |
| `interlude` | Transitional content | `id`, `title`, `body` |
| `appendix` | Reference material | `id`, `title`, `body` |

### 2.4 Protocol Objects

Sections may contain `protocols` — executable instructions embedded in the content:

```json
{
  "id": "proto-drift-audit",
  "name": "The Drift Audit",
  "type": "audit",
  "steps": [
    "List every belief you acted on today",
    "Mark each: inherited (I) or chosen (C)",
    "For every (I): write the override",
    "Execute the override tomorrow"
  ],
  "frequency": "weekly",
  "tier_required": 2
}
```

Protocol types: `audit`, `ritual`, `drill`, `command`, `protocol`, `override`

---

## 3. Encryption Layer

### 3.1 Wire Format (`.nd` files)

The encrypted wire format is identical to the existing NeuralBook `.nd` format:

```
[IV: 12 bytes][AuthTag: 16 bytes][Ciphertext: N bytes]
```

- **Algorithm**: AES-256-GCM
- **Key derivation**: scrypt (seed, 'salt', 32) — matching JS pipeline
- **Key discovery priority**:
  1. `NEUROBOOK_ENCRYPTION_SEED` environment variable
  2. `encryptionSeedFile` in title config
  3. `encryptionSeed` in title config (demo/internal builds only)

### 3.2 Per-Section Encryption

For granular access control, sections can be individually encrypted:

```json
{
  "id": "sec-XV",
  "encrypted": true,
  "encryption_tier": 3,
  "body_ref": "encrypted/sec-XV.nd",
  "body": null
}
```

Readers with the appropriate key tier decrypt the section on demand.

---

## 4. Patch Protocol

### 4.1 Patch Format

Patches are JSON documents that describe changes to a NeuralBook file without containing the full file:

```json
{
  "neuralbook_patch": {
    "version": "1.0",
    "target_edition": "1.0.0",
    "patch_id": "patch-001",
    "created": "2026-05-01T00:00:00Z",
    "description": "Added Signal Laws section"
  },
  "operations": [
    {
      "op": "add",
      "path": "/content/-",
      "value": { "id": "sec-XV", "type": "section", ... }
    },
    {
      "op": "replace",
      "path": "/content/3/body",
      "value": "Updated body text..."
    },
    {
      "op": "replace",
      "path": "/meta/word_count",
      "value": 36839
    }
  ],
  "verification": {
    "previous_root_hash": "sha256:abc...",
    "new_root_hash": "sha256:def...",
    "sections_affected": ["sec-XV", "sec-IV"]
  }
}
```

### 4.2 Patch Operations

Based on JSON Patch (RFC 6902) with NeuralBook extensions:

| Operation | Description |
|-----------|-------------|
| `add` | Add a new section or field |
| `replace` | Replace content of an existing section |
| `remove` | Remove a section (mark as deprecated) |
| `seal` | Re-seal the document after patching |
| `tier_update` | Update tier progression requirements |

### 4.3 Patch Application

```bash
neuralbook patch manuscript.nbook patch-001.nbook-patch
```

The CLI:
1. Verifies the patch targets the correct edition
2. Validates the `previous_root_hash` matches the current file
3. Applies operations in order
4. Recomputes section hashes and root hash
5. Updates `seal.new_root_hash`
6. Increments `meta.edition` patch version

---

## 5. Integrity Verification

### 5.1 Hash Computation

Each section's hash is computed over its canonical JSON representation:

```python
import json, hashlib

def section_hash(section: dict) -> str:
    canonical = json.dumps(section, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()
```

### 5.2 Root Hash

The root hash is computed over all section hashes in order:

```python
def root_hash(sections: list[dict]) -> str:
    combined = ''.join(s['hash'] for s in sorted(sections, key=lambda s: s['id']))
    return hashlib.sha256(combined.encode('utf-8')).hexdigest()
```

### 5.3 Seal

A sealed document has its `seal.sealed_at` timestamp set and all hashes verified. Once sealed, any modification invalidates the root hash, detecting tampering.

---

## 6. Validation

### 6.1 Validation Levels

| Level | Checks |
|-------|--------|
| `structure` | Required fields present, valid types, valid JSON |
| `integrity` | All section hashes match, root hash matches |
| `format` | Weight class symbols renderable, section numbering sequential |
| `encryption` | Encrypted sections decryptable with provided key |
| `full` | All of the above |

### 6.2 CLI Validation

```bash
neuralbook validate manuscript.nbook --level full
```

Returns exit code 0 on pass, 1 on failure with detailed error report.

---

## 7. Build Pipeline

### 7.1 Transformation Chain

```
Source (.txt/.md) → NeuralBook (.nbook) → Encrypted (.nd)
                                              ↓
                                    HTML / DOCX / PWA
```

### 7.2 Build Types

| Type | Encryption | Audience | Key Source |
|------|-----------|----------|------------|
| `demo` | Optional | Preview | Config seed |
| `internal` | Required | Team | Seed file |
| `release` | Required | Public | Env var |
| `external` | Required | Third-party | Env var + per-section |

---

## 8. CLI Reference

### 8.1 Commands

```
neuralbook init <dir>          Scaffold a new NeuralBook project
neuralbook build <dir>         Build .nbook from source + encrypt to .nd
neuralbook validate <file>     Validate a .nbook file
neuralbook patch <file> <patch> Apply a patch to a .nbook file
neuralbook seal <file>         Cryptographically seal a .nbook file
neuralbook info <file>         Display metadata and structure
neuralbook extract <file.nd>   Decrypt .nd to .nbook
neuralbook keygen              Generate an encryption seed
```

### 8.2 Global Options

```
--verbose, -v     Verbose output
--quiet, -q       Suppress non-error output
--version         Show version
--help            Show help
```

---

## 9. Conformance

### 9.1 Reader Conformance

A conforming NeuralBook reader MUST:
- Parse the JSON structure per §2
- Verify section hashes per §5
- Support at least `structure` and `integrity` validation per §6
- Decrypt `.nd` files per §3
- Render all section types per §2.3

A conforming reader MAY:
- Support patch application per §4
- Support protocol execution per §2.4
- Support per-section encryption per §3.2

### 9.2 Writer Conformance

A conforming NeuralBook writer MUST:
- Produce valid JSON per §2
- Compute correct hashes per §5
- Support encryption per §3
- Generate valid patches per §4

### 9.3 Validator Conformance

A conforming NeuralBook validator MUST:
- Implement all validation levels per §6
- Return structured error reports
- Support both `.nbook` and `.nd` inputs

---

## 10. Versioning

Format versions follow semantic versioning:

- **Major** (2.0): Breaking structural changes
- **Minor** (1.1): New section types, protocol types, or operations
- **Patch** (1.0.1): Clarifications, no format changes

Current format version: **NB-FMT-1.0**

---

## Appendix A: Reserved Section IDs

| Pattern | Usage |
|---------|-------|
| `sec-*` | Sections |
| `part-*` | Parts |
| `inter-*` | Interludes |
| `appx-*` | Appendices |
| `proto-*` | Protocols |
| `patch-*` | Patches |

## Appendix B: Weight Class Symbol Registry

| Level | Symbol | Name | Unicode |
|-------|--------|------|---------|
| 1 | 🪶 | Anti-Ounce / Feather | U+1FAB6 |
| 2 | 🎯 | Pro-Ounce / Target | U+1F3AF |
| 3 | 🕳️ | Anti-Gram / Hole | U+1F573 U+FE0F |
| 4 | 🧱 | Pro-Gram / Brick | U+1F9F1 |
| 5 | 🫧 | Anti-Pound / Bubbles | U+1FAE7 |
| 6 | 💣 | Pro-Pound / Bomb | U+1F4A3 |
| 7 | 🫥 | Anti-Ton / Dotted Face | U+1FAE5 |
| 8 | 🌪️ | Pro-Ton / Tornado | U+1F32A U+FE0F |

## Appendix C: Migration from TXT

The `neuralbook import` command converts a structured TXT manuscript to `.nbook` format by:

1. Parsing `===== SECTION X: TITLE =====` and `===== PART X: TITLE =====` headers
2. Creating section objects with auto-generated IDs
3. Computing section hashes
4. Building the TOC from detected headers
5. Populating `meta.word_count` and `meta.section_count`
6. Setting `neuralbook.sealed = false` (requires explicit seal)
