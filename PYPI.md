# PyPI Release Guide

Complete guide to publishing NeuralBook to PyPI and managing releases.

## Overview

NeuralBook is available on PyPI for easy installation across platforms.

**PyPI Package:** https://pypi.org/project/neuralbook/

## Installation

### From PyPI (Recommended)

```bash
# Latest version
pip install neuralbook

# Specific version
pip install neuralbook==1.0.0

# With optional dependencies
pip install neuralbook[server]      # FastAPI server
pip install neuralbook[dev]         # Development tools
pip install neuralbook[docker]      # Docker support
pip install neuralbook[all]         # Everything
```

### From Source

```bash
git clone https://github.com/neuralbook/neuralbook.git
cd neuralbook
pip install -e .
```

### Development Installation

```bash
git clone https://github.com/neuralbook/neuralbook.git
cd neuralbook
pip install -e ".[dev]"
```

## Version Management

### Current Version

View installed version:

```bash
python -c "import neuralbook; print(neuralbook.__version__)"
pip show neuralbook
```

### Update Version

1. Edit `pyproject.toml`:
   ```toml
   [project]
   version = "1.0.1"
   ```

2. Create git tag:
   ```bash
   git tag v1.0.1
   git push origin v1.0.1
   ```

3. GitHub Actions automatically publishes to PyPI

### Version Scheme

NeuralBook follows [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking API changes (1.0.0 → 2.0.0)
- **MINOR**: New features, backward compatible (1.0.0 → 1.1.0)
- **PATCH**: Bug fixes, backward compatible (1.0.0 → 1.0.1)

Examples:
- `1.0.0` — Initial release
- `1.1.0` — Added encryption features
- `1.0.1` — Bug fix release
- `1.1.0-beta` — Beta release

## Release Process

### Automated (Recommended)

1. **Create tag**:
   ```bash
   git tag v1.0.1
   git push origin v1.0.1
   ```

2. **GitHub Actions**:
   - Automatically runs tests
   - Builds distributions
   - Publishes to PyPI
   - Creates Docker image
   - Generates GitHub release

### Manual Release

#### Step 1: Prepare Environment

```bash
# Install build tools
pip install build twine wheel

# Verify you're in the project root
cd neuralbook/
```

#### Step 2: Build Distributions

```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info/

# Build wheel and source distribution
python -m build
```

Outputs:
- `dist/neuralbook-1.0.0-py3-none-any.whl` (wheel)
- `dist/neuralbook-1.0.0.tar.gz` (sdist)

#### Step 3: Validate Package

```bash
# Check package metadata
twine check dist/*

# Verify all files are included
tar tzf dist/neuralbook-1.0.0.tar.gz | head -20
```

#### Step 4: Test on TestPyPI

```bash
# Upload to test repository
twine upload dist/* --repository testpypi

# Install from TestPyPI to verify
pip install --index-url https://test.pypi.org/simple/ neuralbook

# Test functionality
python -c "from neuralbook import Store; print('✓ Import successful')"

# Uninstall
pip uninstall neuralbook
```

#### Step 5: Release to Production

```bash
# Upload to PyPI
twine upload dist/*

# Verify on PyPI
pip install neuralbook

# Check version
pip show neuralbook
```

### Using Release Script

```bash
# Safe dry-run checks only (build + optional tests/validation, no upload)
python scripts/release_to_pypi.py --dry-run

# Dry run with explicit upload to TestPyPI
python scripts/release_to_pypi.py --dry-run --allow-upload

# Full release to production PyPI (explicit upload)
python scripts/release_to_pypi.py --allow-upload

# Skip tests
python scripts/release_to_pypi.py --skip-tests
```

## PyPI Configuration

### Setup Authentication

#### Tokens (Recommended)

1. Generate token on PyPI:
   - Go to https://pypi.org/account/
   - Click "Add API token"
   - Save token securely

2. Configure `~/.pypirc`:
   ```ini
   [pypi]
   username = __token__
   password = pypi-AgEIcHlwaS5vyear...
   ```

#### Username/Password

```ini
[pypi]
username = your_username
password = your_password
```

### Environment Variables

```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-AgEIcHlwaS5vyear...

# Then release
twine upload dist/*
```

### GitHub Secrets

1. Go to repository Settings → Secrets
2. Add `PYPI_API_TOKEN`
3. GitHub Actions automatically uses it

## Package Contents

### What's Included

```
neuralbook/
├── __init__.py              # Package initialization
├── encryption.py            # Encryption module
├── manifest.py              # Manifest generation
├── build.py                 # Build system
├── api.py                   # API stubs
├── api_router.py            # API routing (production)
├── core.py                  # Core business logic
└── cli.py                   # Command-line interface
```

### Excluded (via `.dockerignore` and `MANIFEST.in`)

- Git history (`.git/`)
- Virtual environments (`venv/`, `.venv/`)
- Build artifacts (`build/`, `dist/`, `*.egg-info/`)
- Cache files (`__pycache__/`, `.pytest_cache/`)
- IDE files (`.vscode/`, `.idea/`)

### Dependencies

**Core** (always installed):
- `cryptography>=41.0.0` — Encryption
- `pyyaml>=6.0` — Configuration
- `click>=8.0` — CLI
- `markdown2>=2.4.0` — Markdown processing

**Optional** (install with `pip install neuralbook[extra]`):
- `[server]` — FastAPI, Uvicorn for API server
- `[dev]` — Testing, linting, formatting tools
- `[docker]` — Docker SDK for container management
- `[all]` — All optional dependencies

## Package Metadata

### README

The long description on PyPI is `README.md`:

```bash
# Verify rendering
pip install readme-renderer
python -m readme_renderer README.md
```

### Classifiers

Update in `pyproject.toml`:

```toml
classifiers = [
    "Development Status :: 4 - Beta",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.9",
    ...
]
```

[Full classifier list](https://pypi.org/classifiers/)

### Keywords

```toml
keywords = ["encryption", "publishing", "security", ...]
```

## Troubleshooting

### Build Fails

```bash
# Check Python version
python --version  # Should be 3.9+

# Rebuild cleanly
rm -rf dist/ build/ *.egg-info/
python -m build -v
```

### Upload Fails

```bash
# Check credentials
cat ~/.pypirc

# Verify token
pip install --index-url https://pypi.org/simple/ neuralbook

# Check package validity
twine check dist/*
```

### Import Fails After Installation

```bash
# Verify package installed
pip show neuralbook

# Check import path
python -c "import neuralbook; print(neuralbook.__file__)"

# Reinstall
pip install --force-reinstall --no-cache-dir neuralbook
```

## Best Practices

### Versioning

✅ **Good**:
- Increment patch for bug fixes: `1.0.0` → `1.0.1`
- Increment minor for features: `1.0.0` → `1.1.0`
- Increment major for breaking changes: `1.0.0` → `2.0.0`

❌ **Avoid**:
- Version on every single change
- Jumping versions arbitrarily
- Inconsistent version formats

### Testing Before Release

```bash
# Always test locally first
python -m pytest tests/ -v

# Test installation in clean environment
python -m venv /tmp/test-nb
source /tmp/test-nb/bin/activate
pip install dist/neuralbook-*.whl
python -c "import neuralbook; print(neuralbook.__version__)"
```

### Documentation

- Update `CHANGELOG.md` with release notes
- Link to GitHub release in PyPI description
- Include upgrade instructions for major versions

### Changelog Example

```markdown
# Changelog

## [1.0.1] - 2026-04-20

### Fixed
- Fixed encryption key derivation issue (~#42)
- Corrected API error responses

### Changed
- Updated dependencies for security

## [1.0.0] - 2026-04-15

### Added
- Initial release of NeuralBook
```

## References

- [PyPI Help](https://pypi.org/help/)
- [setuptools Documentation](https://setuptools.readthedocs.io/)
- [Twine Documentation](https://twine.readthedocs.io/)
- [Python Packaging Guide](https://packaging.python.org/)
- [PEP 440 - Version Identification](https://peps.python.org/pep-0440/)
- [PEP 517 - Build System Interface](https://peps.python.org/pep-0517/)

---

**Questions?** Email hello@neuralbook.dev or open an issue on GitHub.
