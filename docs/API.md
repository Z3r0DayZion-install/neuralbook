# NeuralBook API Reference

## Command-Line Interface

All commands use the format: `python scripts/neuralbook_COMMAND.py [options]`

### neuralbook_init.py

Initialize a new book project.

```bash
python scripts/neuralbook_init.py \
  --title "My Book" \
  --author "Author Name" \
  --output ./my-book \
  [--language en] \
  [--version 1.0.0]
```

**Options:**
- `--title TEXT` (required) — Book title
- `--author TEXT` (required) — Author name
- `--output PATH` (required) — Output directory
- `--language TEXT` — Language code (default: en)
- `--version TEXT` — Initial version (default: 0.1.0)

**Output:** Creates directory structure with config.yaml, metadata.json, content/ folder

---

### neuralbook_build.py

Build and encrypt the project.

```bash
python scripts/neuralbook_build.py \
  --project ./my-book \
  [--format html|epub|pdf|all] \
  [--output-dir build/output] \
  [--deterministic] \
  [--parallel 4]
```

**Options:**
- `--project PATH` (required) — Project directory
- `--format {html,epub,pdf,all}` — Output format (default: all)
- `--output-dir PATH` — Build output directory
- `--deterministic` — Use deterministic build settings
- `--parallel N` — Worker threads (default: CPU count)

**Output:** 
- `build/output.html` — Encrypted web version
- `build/output.epub` — Encrypted e-reader version
- `build/manifest.json` — Integrity manifest
- `build/report.json` — Build report

---

### neuralbook_verify.py

Verify project integrity.

```bash
python scripts/neuralbook_verify.py \
  --project ./my-book \
  [--strict] \
  [--log report.json]
```

**Options:**
- `--project PATH` (required) — Project directory
- `--strict` — Fail on warnings (default: warnings only)
- `--log PATH` — Output report to file

**Output:**
```
✓ Manifest valid
✓ All chapters encrypted
✓ Accessibility checks passed
✓ Performance budget OK
⚠ Deprecation: Update to latest version
```

**Exit codes:**
- 0 — All checks passed
- 1 — Failures detected
- 2 — Warnings detected (non-strict mode)

---

### neuralbook_cert.py

Run full certification pipeline.

```bash
python scripts/neuralbook_cert.py \
  --project ./my-book \
  [--tag v1.0.0] \
  [--operator alice@example.com] \
  [--requirement accessibility:aa,performance:2mb]
```

**Options:**
- `--project PATH` (required) — Project directory
- `--tag TEXT` — Release tag (default: auto-generated)
- `--operator TEXT` — Operator identity
- `--requirement TEXT` — Comma-separated requirements

**Checks:**
1. Build determinism (2 builds, compare hash)
2. Accessibility (WCAG 2.1 AA)
3. Performance budget (per-file & aggregate)
4. Security audit (dependency CVEs)
5. API contract (route verification)
6. Audit chain integrity

**Output:** `build/certification-2026-04-20.json`

---

### neuralbook_package.py

Prepare distribution package.

```bash
python scripts/neuralbook_package.py \
  --project ./my-book \
  --output package.zip \
  [--include-source] \
  [--sign]
```

**Options:**
- `--project PATH` (required) — Project directory
- `--output PATH` — Package filename (default: book.zip)
- `--include-source` — Include source files (development only)
- `--sign` — Cryptographically sign package

**Output:** `package.zip` containing:
```
book.zip
├── index.html
├── manifest.json
├── signature.sig
└── chapters/
```

---

### neuralbook_sign.py

Add cryptographic signature to package.

```bash
python scripts/neuralbook_sign.py \
  --package package.zip \
  --key-file ~/.ssh/neuralbook_signing_key \
  [--algorithm ed25519|rsa4096]
```

**Options:**
- `--package PATH` (required) — Package to sign
- `--key-file PATH` (required) — Private key file
- `--algorithm {ed25519,rsa4096}` — Signature algorithm

**Output:** `package.zip.sig` containing signature metadata

---

### neuralbook_release.py

Full release automation (build → cert → package → sign → publish).

```bash
python scripts/neuralbook_release.py \
  --project ./my-book \
  --tag v1.0.0 \
  [--publish-url https://example.com/releases]
```

**Options:**
- `--project PATH` (required) — Project directory
- `--tag TEXT` — Release tag
- `--publish-url URL` — Publish destination

**Steps:**
1. Build project
2. Run certification
3. Create package
4. Sign package
5. Upload to publish URL (if provided)
6. Write release metadata

---

## Python SDK

Use NeuralBook programmatically:

```python
from neuralbook import Project, build, verify, certify

# Load project
project = Project("./my-book")

# Build
build(project, format="all")

# Verify
results = verify(project)
print(f"Status: {results.status}")  # "pass", "warn", "fail"

# Certify
cert_report = certify(project)
print(f"Score: {cert_report.score}/100")
```

### Project Class

```python
class Project:
    def __init__(self, path: str):
        self.path = Path(path)
        self.config = load_yaml(self.path / "config.yaml")
        self.metadata = load_json(self.path / "metadata.json")
    
    @property
    def title(self) -> str:
        return self.config["title"]
    
    @property
    def chapters(self) -> List[Chapter]:
        # Returns sorted chapters from content/ directory
```

### Key Functions

```python
def build(project: Project, 
          format: str = "all",
          parallel: int = None) -> BuildReport:
    """Build and encrypt project."""

def verify(project: Project, 
           strict: bool = False) -> VerifyReport:
    """Verify project integrity."""

def certify(project: Project, 
            requirements: Dict = None) -> CertReport:
    """Run full certification suite."""

def encrypt_content(plaintext: str, 
                    key: bytes, 
                    algorithm: str = "AES-256-GCM") -> bytes:
    """Encrypt content directly."""

def decrypt_content(ciphertext: bytes, 
                    key: bytes) -> str:
    """Decrypt content directly."""
```

---

## Environment Variables

### Required

- `NEURALBOOK_ENCRYPTION_SEED` — Base64-encoded 48-byte encryption key

### Optional

- `NEURALBOOK_OUTPUT_DIR` — Override default build output directory
- `NEURALBOOK_LOG_LEVEL` — {DEBUG, INFO, WARN, ERROR}
- `NEURALBOOK_OPERATOR` — Operator identity (for audit log)
- `NEURALBOOK_KMS_URL` — KMS endpoint for key management

---

## Exit Codes

```
0 = Success
1 = Build/verification failure
2 = Configuration error
3 = Missing required file
4 = Encryption/decryption error
5 = Network/external service error
```

---

## Configuration (config.yaml)

```yaml
title: "My Book"
author: "Author Name"
version: "1.0.0"
language: "en"

encryption:
  algorithm: "AES-256-GCM"
  key_derivation: "PBKDF2-SHA256"
  iterations: 100000

quality_gates:
  accessibility: "WCAG-AA"
  performance:
    per_file_mb: 0.5
    aggregate_mb: 50
  security_scan: true
  deterministic: true

publishing:
  tier: "standard"  # standard|premium|enterprise
  license: "MIT"
  update_check: false
```

---

## Error Handling

All commands return structured errors:

```json
{
  "error": "encryption_failed",
  "message": "IV generation failed: insufficient entropy",
  "file": "chapters/01.md",
  "line": 145,
  "suggestion": "Ensure /dev/urandom is available"
}
```

---

## Rate Limiting

No rate limiting for local CLI. API server (if deployed) implements:
- 100 requests/minute per IP
- 1000 requests/minute per API key

---

## Version Compatibility

Current version: **1.0.0**

Breaking changes indicated by major version bump (1.0 → 2.0).

See [CHANGELOG.md](./CHANGELOG.md) for migration guides.

---

## Examples

### Example 1: Simple Build

```bash
export NEURALBOOK_ENCRYPTION_SEED="$(python -c 'import os,base64; print(base64.b64encode(os.urandom(48)).decode())')"
python scripts/neuralbook_init.py --title "My Book" --output ./book
python scripts/neuralbook_build.py --project ./book
```

### Example 2: Full Release

```bash
python scripts/neuralbook_release.py \
  --project ./book \
  --tag v1.0.0 \
  --publish-url https://example.com/releases
```

### Example 3: Programmatic Build

```python
from neuralbook import Project, build, verify

project = Project("./book")
build(project)
results = verify(project)
if results.status == "pass":
    print("Ready to publish!")
```

---

**Need help?** See [GETTING_STARTED.md](./GETTING_STARTED.md) or open an issue.
