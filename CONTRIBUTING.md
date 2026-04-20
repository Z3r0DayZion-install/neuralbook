# Contributing to NeuralBook

Thank you for your interest in contributing to NeuralBook! We welcome contributions of all kinds.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally: `git clone https://github.com/yourusername/neuralbook.git`
3. **Create a branch** for your feature: `git checkout -b feature/your-feature-name`
4. **Install dev dependencies**: `pip install -r requirements-dev.txt`
5. **Run tests**: `pytest tests/`

## Development Setup

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run formatter & linter
black .
isort .
flake8 .

# Run tests
pytest -v

# Build documentation
cd docs && make html
```

## Code Style

- **Python:** Black (line length 100)
- **Imports:** isort (3-line mode)
- **Linting:** flake8
- **Type hints:** Python 3.9+ style recommended
- **Docstrings:** Google/NumPy style

## Submitting Changes

### Before Opening a PR

- [ ] Tests pass: `pytest`
- [ ] Code formatted: `black . && isort .`
- [ ] No linter errors: `flake8`
- [ ] Updated documentation if needed
- [ ] Added tests for new features

### PR Title & Description

- **Title:** Descriptive, imperative mood (e.g., "Fix encryption key derivation for Windows")
- **Description:** 
  - What problem does this solve?
  - How does it work?
  - Any breaking changes?
  - Links to related issues

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add support for ECDSA key derivation
fix: correct CBC mode IV handling on macOS
docs: clarify encryption model in ARCHITECTURE.md
test: add edge-case tests for manifest parsing
chore: update dependencies
```

## Testing

All PRs require tests. We aim for >90% coverage.

```bash
# Run tests with coverage
pytest --cov=src/neuralbook tests/

# Run a specific test
pytest tests/test_encryption.py::test_aes_256_gcm_roundtrip
```

## Documentation

- Update [docs/](./docs/) if adding features
- Keep README.md current
- Examples should be self-contained and runnable

## Reporting Issues

### Bug Reports

Include:
- OS & Python version
- Steps to reproduce
- Expected vs actual behavior
- Error output / logs

### Feature Requests

Describe:
- Use case
- Proposed implementation (if you have one)
- Priority/impact
- Alternatives considered

## Code Review

- Reviews by core maintainers
- Address feedback constructively
- Feel free to ask questions
- No change is too small to improve

## Areas We Welcome

- **Bug fixes** — Always welcome
- **Performance improvements** — Profile first
- **Documentation** — Especially examples & runbooks
- **Tests** — Better coverage helps everyone
- **Dependencies** — Security updates & version bumps
- **Accessibility** — Help make NeuralBook inclusive
- **Translations** — i18n support

## Areas Under Active Development

These change frequently; coordinate with maintainers first:
- Core encryption implementation
- Build pipeline architecture
- Release automation

## Questions?

- Open a [GitHub Discussion](https://github.com/yourusername/neuralbook/discussions)
- Email: hello@neuralbook.dev

---

**Thank you for helping make NeuralBook better!**
