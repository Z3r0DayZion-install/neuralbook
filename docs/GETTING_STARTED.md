# Getting Started with NeuralBook

Welcome! This guide will walk you through creating your first encrypted digital book with NeuralBook in about 30 minutes.

## Prerequisites

- Python 3.9+ 
- Node.js (for key generation, optional)
- Git

## Step 1: Clone and Install (5 minutes)

```bash
# Clone the repository
git clone https://github.com/yourusername/neuralbook.git
cd neuralbook

# Create a virtual environment
python -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Generate an Encryption Key (2 minutes)

NeuralBook uses AES-256-GCM for content encryption. Generate a strong random key:

**Option A: Using Node.js**
```bash
node -e "console.log(require('crypto').randomBytes(48).toString('base64'))"
```

**Option B: Using Python**
```bash
python -c "import os, base64; print(base64.b64encode(os.urandom(48)).decode())"
```

You'll see output like: `abc123XYZ...` — save this somewhere safe!

## Step 3: Create Your First Title (5 minutes)

```bash
# Set the encryption key in your shell
export NEURALBOOK_ENCRYPTION_SEED="abc123XYZ..."

# Initialize a new book project
python scripts/neuralbook_init.py \
  --title "My First Book" \
  --author "Your Name" \
  --output ./my-first-book
```

This creates a new directory structure:
```
my-first-book/
├── content/
│   ├── 01-chapter-one.md
│   ├── 02-chapter-two.md
│   └── README.md
├── config.yaml
├── metadata.json
└── build/
```

## Step 4: Add Your Content (10 minutes)

Edit the chapters in `my-first-book/content/`:

```markdown
# Chapter One: Getting Started

This is your first chapter. Write in Markdown.

## Section 1.1

You can use standard Markdown syntax:
- Bullet points
- **Bold text**
- *Italic text*
- [Links](https://example.com)

### Code Examples

\`\`\`python
def hello():
    print("Hello, NeuralBook!")
\`\`\`

> Blockquotes work too.

[Checkpoint: Did you understand this?]{data-challenge="q1"}
```

## Step 5: Build Your Book (5 minutes)

```bash
# Build the encrypted version
python scripts/neuralbook_build.py --project ./my-first-book

# This generates:
# - Encrypted HTML version
# - Encrypted EPUB (e-reader format)
# - Manifest (integrity verification)
# - Build report
```

## Step 6: Verify Integrity (1 minute)

Check that everything built correctly:

```bash
python scripts/neuralbook_verify.py --project ./my-first-book
```

You'll see output like:
```
[neuralbook] Verifying: my-first-book
[neuralbook] ✓ Manifest valid (SHA-256)
[neuralbook] ✓ All chapters encrypted
[neuralbook] ✓ Integrity check passed
[neuralbook] Build report: my-first-book/build/report.json
```

## Step 7: Distribute Your Book

Your encrypted book is now ready! Options:

### Option A: Direct Download
- Host `my-first-book/build/output.html` on a web server
- Readers download and extract offline
- Works on Windows, macOS, Linux, web browsers

### Option B: Package & Sign
```bash
python scripts/neuralbook_package.py --project ./my-first-book
python scripts/neuralbook_sign.py --package ./my-first-book/build/package.zip
```

This creates a signed package suitable for distribution.

### Option C: Gumroad Integration
```bash
# Prepare for Gumroad upload
python scripts/neuralbook_prepare_gumroad.py \
  --project ./my-first-book \
  --price 49.00 \
  --tier "standard"
```

## Next Steps

### Learn More
- **[Architecture](./ARCHITECTURE.md)** — How NeuralBook works under the hood
- **[API Reference](./API.md)** — Detailed command documentation
- **[Examples](../examples/)** — Full working examples

### Advanced Topics
- **Multiple titles** — Reuse the platform for new books
- **Encryption keys** — KMS integration, environment variables
- **Automation** — GitHub Actions for CI/CD
- **Custom branding** — White-label your distribution

### Get Help
- Issues: https://github.com/yourusername/neuralbook/issues
- Discussions: https://github.com/yourusername/neuralbook/discussions

---

**Happy writing! Build something remarkable.**
