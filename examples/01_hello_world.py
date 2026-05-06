#!/usr/bin/env python3
"""
Example 1: Hello World
======================
The simplest NeuralBook example.

This creates a minimal encrypted book with two chapters and demonstrates:
- Project creation
- Content management
- Encryption
- Build output

Requirements:
  pip install neuralbook

Usage:
  python 01_hello_world.py [--output-dir ./build]
"""

import sys
from datetime import datetime
from pathlib import Path

from neuralbook import Store, create_build, create_project


def main() -> int:
    """Create and build a simple encrypted book."""

    # Setup
    output_dir = Path("./hello-world-build")
    output_dir.mkdir(exist_ok=True)

    store_path = output_dir / "store.json"

    print("=" * 60)
    print("NeuralBook: Hello World Example")
    print("=" * 60)

    # 1. Create a project
    print("\n[1/4] Creating project...")
    store = Store(store_path)

    # Use unique slug to avoid conflicts on repeated runs
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_slug = f"hello-world-{timestamp}"

    project = create_project(
        store,
        title="Hello World",
        slug=unique_slug,
        theme="cyberpunk",
    )
    print(f"  Project created: {project['id']}")
    print(f"    Title: {project['title']}")
    print(f"    Slug:  {project['slug']}")

    # 2. Describe chapters (content would be encrypted in a real pipeline)
    print("\n[2/4] Defining chapters...")
    print("  Chapter 1: Introduction")
    print("  Chapter 2: Next Steps")

    # 3. Trigger a build
    print("\n[3/4] Triggering build...")
    build = create_build(store, project_id=project["id"], trigger_source="example")
    print(f"  Build queued: {build['id']}")
    print(f"    Status:  {build['status']}")
    print(f"    Created: {build['created_at']}")

    # 4. Output results
    print("\n[4/4] Build complete!")
    print(f"  Output directory: {output_dir.resolve()}")
    print(f"  Store location:   {store_path.resolve()}")

    print("\n" + "=" * 60)
    print("Success! Your book is ready.")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Review the project store: cat hello-world-build/store.json")
    print("  2. Check example 02_api_server.py for API usage")
    print("  3. See example 03_batch_build.py for building multiple projects")

    return 0


if __name__ == "__main__":
    sys.exit(main())
