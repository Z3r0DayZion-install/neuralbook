# NeuralBook Architecture

## Overview

NeuralBook is a content encryption and verification platform designed for authors, publishers, and enterprises who want to distribute high-integrity digital content.

## Core Principles

1. **Zero Platform Overhead** — Encryption is content-aware, not platform-aware
2. **Offline-First** — Content is decryptable without server contact
3. **Deterministic Builds** — Same input always produces identical output
4. **Tamper-Evident** — Audit chain makes tampering detectable
5. **Key Flexibility** — Support multiple key management strategies

## Encryption Model

### Algorithm Choice: AES-256-GCM

- **Why AES?** Industry-standard, hardware-accelerated, NIST-approved
- **Why GCM?** Provides both confidentiality and authenticity in one cipher
- **IV Management** — Unique random IV per content block (NIST SP 800-38D)
- **Authentication Tag** — Detects tampering automatically

### Key Derivation

```
Master Seed (48 bytes, user-supplied)
         ↓
    PBKDF2-SHA256
    (iterations=100000)
         ↓
   Derived Keys:
   - Content Key (32 bytes for AES-256)
   - IV Seed (32 bytes for random IVs)
   - MAC Key (32 bytes reserved)
```

### Per-Chapter Encryption

Each chapter gets:
1. **Unique IV** — 96-bit nonce generated from IV seed
2. **Content Encryption** — AES-256-GCM(key, IV, chapter_plaintext)
3. **Authentication Tag** — Embedded in ciphertext header
4. **Manifest Entry** — SHA-256(ciphertext) for integrity verification

```
[Version (1 byte)]
[Algorithm ID (1 byte)]
[IV (12 bytes)]
[Ciphertext (variable)]
[Auth Tag (16 bytes)]
[Metadata JSON (variable)]
```

## Manifest & Integrity

### SHA-256 Manifest Tree

Every content file produces a manifest entry:

```json
{
  "file": "chapters/01-intro.html",
  "sha256": "abc123...",
  "size": 12345,
  "encrypted": true,
  "algorithm": "AES-256-GCM",
  "chunks": [
    {"index": 0, "sha256": "def456...", "offset": 0},
    {"index": 1, "sha256": "ghi789...", "offset": 16384}
  ]
}
```

### Root Integrity Hash

All manifests are hashed together to create a root integrity hash:

```
Root Hash = SHA-256(sort & concat manifests)
```

Readers verify:
```
Downloaded Root Hash == SHA-256(downloaded manifests)
If different: Content tampered or corrupted
```

## Build Determinism

### Challenge: Non-Deterministic Outputs

Common sources of non-determinism:
- Timestamps (now, build date)
- File ordering (filesystem-dependent)
- Floating-point math
- Randomness in libraries

### Solution: Deterministic Build Process

1. **Sort** all inputs alphabetically
2. **Fix timestamps** to project-defined value
3. **Seed RNG** with project hash (not system randomness)
4. **Strip metadata** (build machine, environment)
5. **Use fixed dependency versions** (not "latest")

### Verification

```bash
# Build twice, compare hashes
python build.py project1 && HASH1=sha256(output)
python build.py project1 && HASH2=sha256(output)
assert HASH1 == HASH2  # ✓ Deterministic
```

## Audit Chain

### Immutable Mutation Log

Every operation (create, update, delete) is logged:

```json
{
  "timestamp": "2026-04-20T12:00:00Z",
  "operator": "alice@example.com",
  "action": "chapter_update",
  "file": "chapters/02.md",
  "hash_before": "abc123...",
  "hash_after": "def456...",
  "signature": "sig_xyz..."
}
```

### Hash Chain Integrity

Each log entry includes hash of the previous entry:

```
Entry 0: hash_prev = null
Entry 1: hash_prev = SHA-256(Entry 0)
Entry 2: hash_prev = SHA-256(Entry 1)
...
```

Tampering Entry N requires re-hashing all entries N+1 through end, which requires knowing all future operator signatures — cryptographically infeasible.

## Quality Gates

### Accessibility Checks

- WCAG 2.1 AA compliance
- Color contrast verification
- Alt text for images
- Heading hierarchy validation
- Keyboard navigation support

### Performance Budget

Per-file limits prevent bloat:
- Chapter < 500 KB
- Images < 2 MB each
- Total project < 50 MB

### Security Scans

- Dependency audits (CVE database)
- OWASP Top 10 static checks
- No embedded credentials
- No hardcoded API keys

## Distribution Formats

### Web Browser

```html
<script src="neuralbook-reader.js"></script>
<div id="reader" data-key="encrypted..."></div>
```

Advantages:
- No installation required
- Works on all platforms
- Can be served from GitHub Pages, CDN, etc.

### Downloadable Package

```
book.zip
├── index.html
├── manifest.json
├── chapters/
│   ├── 01.encrypted
│   ├── 02.encrypted
│   └── ...
└── reader-offline.js
```

Advantages:
- Offline-first (no network required after download)
- Air-gapped networks (no external dependencies)
- Subscriber verification (embedded in package)

### E-Reader (EPUB-compatible)

Encrypted EPUB3 with custom reader extension.

## API Surface

### Command-Line Interface

```bash
neuralbook init          # New project
neuralbook build         # Build & encrypt
neuralbook verify        # Check integrity
neuralbook cert          # Run quality gates
neuralbook package       # Prepare distribution
neuralbook sign          # Add cryptographic signature
neuralbook release       # Full CD pipeline
```

### Python SDK

```python
from neuralbook import Project, build, verify

project = Project("./book")
build(project)
verify(project)
```

### HTTP API (Optional Server)

```
POST /projects             # Create
GET  /projects/{id}/build  # Status
POST /projects/{id}/release  # Publish
```

## Key Management Strategies

### Strategy 1: Environment Variable (Dev)

```bash
export NEURALBOOK_ENCRYPTION_SEED="..."
python build.py project
```

### Strategy 2: JWKS Endpoint (Production)

```yaml
key_store:
  type: jwks
  url: https://keyserver.example.com/.well-known/jwks.json
  key_id: 2026-q1-primary
```

### Strategy 3: AWS KMS (Enterprise)

```yaml
key_store:
  type: aws-kms
  key_arn: arn:aws:kms:us-east-1:...
  region: us-east-1
```

## Threat Model

### What We Protect

✓ Content confidentiality (AES-256)
✓ Content integrity (GCM + manifests)
✓ Insider audit trails (immutable log)
✓ Offline-first (no phone-home)

### What We Don't Protect

✗ Reader tracking (no built-in analytics)
✗ Usage restrictions (DRM features)
✗ Hardware security (no TEE support)
✗ Zero-knowledge proofs

## Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| Encrypt 1 MB | 50 ms | Single-threaded Python |
| Verify 1 MB | 30 ms | Parallel verification possible |
| Build 100 chapters | 5 sec | Parallelized by default |
| First read (cached) | 1 ms | In-memory |

## References

- [NIST SP 800-38D](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38d.pdf) — GCM Mode
- [OWASP Top 10](https://owasp.org/www-project-top-ten/) — Security guidelines
- [WCAG 2.1](https://www.w3.org/WAI/WCAG21/quickref/) — Accessibility standards
- [RFC 3394](https://www.ietf.org/rfc/rfc3394.txt) — Key Wrap

---

**Questions?** Open an issue or discussion on GitHub.
