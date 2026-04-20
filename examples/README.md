# Hello World Example

This is the simplest NeuralBook example.

## Structure

```
hello-world/
├── config.yaml
├── metadata.json
├── content/
│   ├── 01-intro.md
│   └── 02-conclusion.md
└── build/  (generated)
```

## Usage

```bash
cd hello-world
export NEURALBOOK_ENCRYPTION_SEED="..."
python ../scripts/neuralbook_build.py --project .
```

## Files

- **config.yaml** — Project configuration
- **metadata.json** — Book metadata
- **content/01-intro.md** — First chapter (plaintext, will be encrypted)
- **content/02-conclusion.md** — Second chapter

After building, output files are in `build/`.

---

See [../docs/GETTING_STARTED.md](../docs/GETTING_STARTED.md) for a walkthrough.
