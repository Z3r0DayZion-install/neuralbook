# NeuralBook Examples

Complete, runnable examples demonstrating the NeuralBook platform.

## Quick Start

### Install

```bash
cd .. && pip install -e . && cd examples
```

### Run Examples

Each example is a standalone Python script that can be executed directly.

## Examples

### 1. Hello World (5 min)
**File:** `01_hello_world.py`

The simplest NeuralBook example. Creates a minimal encrypted book with two chapters.

**What it demonstrates:**
- Project creation
- Content management
- Build triggering
- Output structure

**Run it:**
```bash
python 01_hello_world.py
```

**Expected output:**
```
============================================================
NeuralBook: Hello World Example
============================================================

[1/4] Creating project...
  ✓ Project created: p_<id>
    Title: Hello World
    Slug: hello-world

[2/4] Adding chapters...
  ✓ Chapter 1: Introduction
  ✓ Chapter 2: Next Steps

[3/4] Triggering build...
  ✓ Build queued: b_<id>
    Status: queued
    Created: 2026-04-20T...

[4/4] Build complete!
  📦 Output directory: .../hello-world-build
  📄 Store location: .../hello-world-build/store.json

Success! Your book is ready.
============================================================
```

---

### 2. HTTP API Server (10 min)
**File:** `02_api_server.py`

Runs a local HTTP server implementing the NeuralBook API. Demonstrates server-side project management.

**What it demonstrates:**
- HTTP request routing
- REST API for CRUD operations
- JSON responses
- Real-time project management

**Run it:**
```bash
# Terminal 1: Start server
python 02_api_server.py

# Terminal 2: Make requests
curl http://localhost:8000/health

# Create a project
curl -X POST http://localhost:8000/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"title": "My Book", "slug": "my-book"}'

# List projects
curl http://localhost:8000/v1/projects

# Trigger a build
curl -X POST http://localhost:8000/v1/projects/<project-id>/build \
  -H "Content-Type: application/json" \
  -d '{"trigger_source": "manual"}'
```

**API Endpoints:**
```
GET    /health                 Health check
GET    /v1/projects            List all projects
POST   /v1/projects            Create new project
GET    /v1/projects/{id}       Get project details
PUT    /v1/projects/{id}       Update project
POST   /v1/projects/{id}/build Trigger build
```

---

### 3. Batch Project Builder (10 min)
**File:** `03_batch_build.py`

Creates and builds multiple projects in one run. Demonstrates scalable project management.

**What it demonstrates:**
- Creating multiple projects programmatically
- Triggering batch builds
- Generating project manifests
- Bulk operations

**Run it:**
```bash
python 03_batch_build.py
```

**Expected output:**
```
============================================================
NeuralBook: Batch Project Builder
============================================================

[1] Creating 4 projects...

  [1/4] ✓ Python Best Practices
         ID: p_<id>
  [2/4] ✓ Web Security Handbook
         ID: p_<id>
  ...

[2] Triggering builds for 4 projects...

  [1/4] ✓ Build queued for Python Best Practices
         Build ID: b_<id>
         Status: queued
  ...

[3] Generating project manifest...

  ✓ Manifest written to: .../batch-build/manifest.json

============================================================
Batch Build Complete!
============================================================

📊 Summary:
  Projects created: 4
  Builds triggered: 4
  Total in store: 4

📂 Output:
  Store: .../batch-build/projects.json
  Manifest: .../batch-build/manifest.json
```

View the manifest:
```bash
cat batch-build/manifest.json
```

---

### 4. Encryption & Decryption (10 min)
**File:** `04_encryption.py`

Demonstrates the cryptographic features of NeuralBook. Shows encryption, decryption, integrity verification, and tamper detection.

**What it demonstrates:**
- AES-256-GCM encryption
- Key derivation from seeds
- Unique IVs per message
- Authentication tags and integrity verification
- Tamper detection

**Run it:**
```bash
python 04_encryption.py
```

**Expected output:**
```
============================================================
NeuralBook: Encryption Example
============================================================

[1] Generating encryption seed...
  ✓ Seed generated: a1b2c3d4... (48 bytes)

[2] Deriving AES-256 key from seed...
  ✓ Key derived: 5e6f7a8b... (32 bytes)
    Algorithm: AES-256-GCM
    Iterations: 100,000 (NIST recommended minimum)

[3] Preparing content for encryption...
  ✓ Content prepared: 218 bytes

[4] Encrypting content...
  ✓ Encryption complete:
    Ciphertext: c9d0e1f2... (218 bytes)
    IV: a1b2c3d4... (96 bits, random)
    Tag: 5e6f7a8b... (128 bits, authentication tag)

[5] Testing integrity verification...
  ✓ Successfully decrypted with valid tag
    Length: 218 bytes
  ✓ Decrypted content matches original

  Testing with corrupted authentication tag...
  ✓ Integrity check failed as expected: InvalidTag
    This proves the content has not been tampered with.

[6] Encrypting multiple messages with same key...
  ✓ Message 1: IV=a1b2c3d4... (unique for each message)
  ✓ Message 2: IV=5e6f7a8b... (unique for each message)
  ✓ Message 3: IV=c9d0e1f2... (unique for each message)

============================================================
Encryption Demo Complete!
============================================================
```

---

## Architecture

All examples use the same core NeuralBook modules:

- **`neuralbook.Store`** — Persistent project storage (JSON-based)
- **`neuralbook.create_project()`** — Create new projects
- **`neuralbook.create_build()`** — Trigger builds
- **`neuralbook.list_projects()`** — Query projects
- **`neuralbook.encrypt_content()`** — Encrypt with AES-256-GCM
- **`neuralbook.decrypt_content()`** — Decrypt with integrity verification
- **`neuralbook.api_router.route_request()`** — HTTP API routing

## Next Steps

### Try Combining Examples

1. **Start the API server** (Example 2)
2. **Make requests to create projects** (using curl or Python requests)
3. **Run batch builds** (Example 3) to populate the server
4. **Verify encryption** (Example 4) on the content

### Add Your Own Content

Extend the examples with:
- Real chapter content
- Custom metadata
- Theme customization
- Build pipeline integration

### Deploy to Production

When ready, use these examples as templates to:
- Build your own book publishing platform
- Integrate into existing workflows
- Deploy to cloud infrastructure
- Scale to thousands of projects

## Architecture Diagram

```
Examples
├─ 01_hello_world.py      Create → Build → Output
├─ 02_api_server.py        HTTP API Server (RESTful)
├─ 03_batch_build.py       Batch Processing (Multi-project)
└─ 04_encryption.py        Cryptography (AES-256-GCM)

All use:
└─ neuralbook (imported from src/)
   ├─ Store              (JSON persistence)
   ├─ create_project()   (project creation)
   ├─ create_build()     (build triggering)
   ├─ encrypt_content()  (encryption)
   └─ route_request()    (HTTP API)
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'neuralbook'"

Install the package first:
```bash
cd .. && pip install -e . && cd examples
```

### "Address already in use" (Example 2)

Another process is using port 8000. Try a different port:
```bash
python 02_api_server.py --port 8001
```

### "Permission denied" when running scripts

Make them executable:
```bash
chmod +x *.py
python 01_hello_world.py  # Still works without chmod
```

## Support

For more information, see:
- [`../README.md`](../README.md) — Main platform documentation
- [`../docs/GETTING_STARTED.md`](../docs/GETTING_STARTED.md) — Detailed walkthrough
- [`../src/neuralbook/`](../src/neuralbook/) — Source code and docstrings

---

**Happy building! 🚀**

