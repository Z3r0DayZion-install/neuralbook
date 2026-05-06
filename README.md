# NeuralBook™ Platform

**Modular, patchable, cryptographically sealed digital books.**

NeuralBook is an open book format and platform for **living documents** — books that are modular, patchable, sealed, and executable. Unlike static formats (EPUB, PDF), a NeuralBook file is an active interface: each section contains deployable protocols, and the file can receive patches without full replacement.

---

## Quick Start

```bash
pip install neuralbook

# Import a manuscript
neuralbook nb-import manuscript.txt --title "My Book" --author "Author Name"

# Validate
neuralbook nb-validate my-book.nbook --level full

# Cryptographically seal
neuralbook nb-seal my-book.nbook

# Export to EPUB or HTML
neuralbook nb-export my-book.nbook --format epub
neuralbook nb-export my-book.nbook --format html
```

---

## CLI Commands

| Command | Description |
|---------|-------------|
| `neuralbook keygen` | Generate encryption seed |
| `neuralbook init` | Scaffold a new project |
| `neuralbook build` | Encrypt content and generate manifest |
| `neuralbook verify` | Verify SHA-256 integrity |
| `neuralbook info` | Platform info and environment |
| `neuralbook nb-import` | Import TXT → .nbook format |
| `neuralbook nb-validate` | Validate .nbook (structure/integrity/format/full) |
| `neuralbook nb-seal` | Cryptographically seal a .nbook |
| `neuralbook nb-patch` | Apply a .nbook-patch |
| `neuralbook nb-info` | Display .nbook metadata and structure |
| `neuralbook nb-export` | Export .nbook → EPUB or HTML |

---

## Platform API

Production-ready FastAPI server with auth, rate limiting, and OpenAPI docs.

```bash
# Install server extras
pip install "neuralbook[server]"

# Configure
cp .env.example .env
# Edit .env with your API keys and settings

# Run
neuralbook-api
# Or with Docker
docker compose up api
```

### Endpoints

**Creator** (require API key when `NBOOK_API_KEYS` is set):
- `POST /v1/projects` — Create project
- `GET /v1/projects` — List projects
- `GET /v1/projects/{id}` — Get project
- `PUT /v1/projects/{id}` — Update project
- `POST /v1/projects/{id}/builds` — Trigger build
- `GET /v1/builds/{id}` — Get build status
- `POST /v1/emails` — Capture reader email

**Reader** (public):
- `GET /books` — List registered books
- `POST /books` — Register a book
- `GET /books/{slug}` — Get book metadata
- `GET /books/{slug}/patches` — List patches
- `POST /books/{slug}/patches` — Upload patch
- `GET /books/{slug}/patches/{id}` — Download patch
- `GET /books/{slug}/latest` — Latest patch info
- `POST /books/{slug}/verify` — Verify integrity

Interactive docs available at `/docs` (Swagger) and `/redoc`.

---

## Configuration

| Env Var | Default | Description |
|---------|---------|-------------|
| `NBOOK_API_KEYS` | (empty = no auth) | Comma-separated API keys for write endpoints |
| `NBOOK_DATA` | `./nbook_data` | Data directory for books, patches, store |
| `NBOOK_CORS_ORIGINS` | `*` | Comma-separated allowed origins |
| `NBOOK_HOST` | `0.0.0.0` | Server bind address |
| `NBOOK_PORT` | `8000` | Server bind port |
| `NBOOK_LOG_LEVEL` | `info` | Logging level |
| `NEURALBOOK_ENCRYPTION_SEED` | (required for build) | AES-256-GCM encryption seed |
| `NEURALBOOK_PROVENANCE_SIGNING_KEY_HEX` | (optional) | Ed25519 private key hex used to sign provenance |
| `NEURALBOOK_PROVENANCE_KEY_ID` | `default` | Key id recorded in provenance signature |
| `NEURALBOOK_PROVENANCE_SIGNERS_JSON` | (optional) | JSON list of multiple signers (`[{key_id,private_key_hex}, ...]`) |

---

## Trust + key rotation

- **Verify demo/internal**:
  - `neuralbook verify-attestation MANIFEST.json PROVENANCE.json ATTESTATION.json --allow-embedded-public-key`
- **Verify release/external (strict default)**:
  - `neuralbook verify-attestation MANIFEST.json PROVENANCE.json ATTESTATION.json --trusted-keys trusted-keys.json --revoked-keys revocations.json`
- **Manage key files**:
  - `neuralbook keys init trusted-keys.json revocations.json`
  - `neuralbook keys add trusted-keys.json --key-id primary-2026-04 --public-key-hex <hex>`
  - `neuralbook keys revoke revocations.json --key-id primary-2025-12`

More details in `SECURITY.md`.

## Project Structure

```
neuralbook-public/
├── src/neuralbook/          # Python SDK
│   ├── format.py            # NeuralBook format (read/write/patch/seal/validate)
│   ├── platform_api.py      # FastAPI server (creator + reader endpoints)
│   ├── cli.py               # Click CLI (11 commands)
│   ├── export.py            # EPUB + HTML export
│   ├── encryption.py        # AES-256-GCM encryption
│   ├── build.py             # Build pipeline
│   ├── manifest.py          # SHA-256 manifests
│   └── __init__.py          # Public API
├── tests/                   # 152 tests
│   ├── test_format.py       # Format SDK tests
│   ├── test_export.py       # Export tests
│   ├── test_platform_api.py # API endpoint tests
│   └── ...
├── docs/NB-SPEC-1.0.md     # Format specification
├── Dockerfile               # Production Docker image
├── docker-compose.yml       # Docker Compose config
├── .env.example             # Configuration template
└── pyproject.toml           # Package metadata
```

---

## Ecosystem

- **Python SDK** — `neuralbook` package (CLI + library)
- **JS/TS SDK** — `@neuralbook/nbook` npm package
- **Web Reader** — React SPA with drag-drop, sidebar, protocol execution
- **CI/CD** — GitHub Actions: test → validate → seal → export

---

## Development

```bash
pip install -e ".[all,server]"
pytest tests/ -v
black --check src/ tests/
isort --check-only src/ tests/
```

---

## License

MIT License. NeuralBook™ trademark reserved.
