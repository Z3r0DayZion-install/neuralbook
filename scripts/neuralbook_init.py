#!/usr/bin/env python3
"""
Initialize a new NeuralBook project.

Usage:
    python neuralbook_init.py --title "My Book" --author "Author" --output ./my-book
"""

import argparse
import json
from datetime import datetime
from pathlib import Path


def init_project(
    title: str, author: str, output: str, language: str = "en", version: str = "0.1.0"
):
    """Initialize new project structure."""
    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)

    # Create content directory
    content_dir = output_path / "content"
    content_dir.mkdir(exist_ok=True)

    # Create sample chapters
    (content_dir / "01-intro.md").write_text(
        """# Chapter 1: Introduction

This is your first chapter. Edit this file to replace it with your content.

You can use standard Markdown:
- Lists
- **Bold text**
- *Italic text*
- [Links](https://example.com)

## Subsection

Add as many subsections as you need.

> You can also include blockquotes.

```python
# Code blocks work too
print("Hello, NeuralBook!")
```
"""
    )

    (content_dir / "02-conclusion.md").write_text(
        """# Chapter 2: Conclusion

Add more chapters by creating new .md files in the content/ directory.

They will be encrypted and included in the final build.
"""
    )

    # Create config.yaml
    config = f"""title: "{title}"
author: "{author}"
version: "{version}"
language: "{language}"

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
"""
    (output_path / "config.yaml").write_text(config)

    # Create metadata.json
    metadata = {
        "title": title,
        "author": author,
        "version": version,
        "language": language,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    (output_path / "metadata.json").write_text(json.dumps(metadata, indent=2))

    print(f"[neuralbook] Created project: {output_path}")
    print(f"[neuralbook] Next step: python neuralbook_build.py --project {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize a new NeuralBook project")
    parser.add_argument("--title", required=True, help="Book title")
    parser.add_argument("--author", required=True, help="Author name")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--language", default="en", help="Language code")
    parser.add_argument("--version", default="0.1.0", help="Initial version")

    args = parser.parse_args()
    init_project(args.title, args.author, args.output, args.language, args.version)
