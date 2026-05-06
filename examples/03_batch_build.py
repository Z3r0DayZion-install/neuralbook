#!/usr/bin/env python3
"""
Example 3: Batch Project Builder
==================================
Demonstrates building multiple projects at once.

This example shows how to:
- Create multiple projects from templates
- Track build status
- Export project metadata

Requirements:
  pip install neuralbook

Usage:
  python 03_batch_build.py
"""

import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from neuralbook import Store, create_build, create_project, list_projects


def main() -> int:
    """Create and build multiple projects."""

    output_dir = Path(tempfile.mkdtemp(prefix="neuralbook-batch-"))

    store_path = output_dir / "projects.json"
    store = Store(store_path)

    print("=" * 60)
    print("NeuralBook: Batch Project Builder")
    print("=" * 60)

    # Define multiple project templates
    projects_to_create = [
        {
            "title": "Python Best Practices",
            "slug": "python-best-practices",
            "theme": "cyberpunk",
            "description": "A comprehensive guide to Python coding standards",
        },
        {
            "title": "Web Security Handbook",
            "slug": "web-security-handbook",
            "theme": "minimal",
            "description": "Essential web application security principles",
        },
        {
            "title": "Team Playbook",
            "slug": "team-playbook",
            "theme": "classic",
            "description": "Internal processes and best practices",
        },
        {
            "title": "Product Roadmap 2026",
            "slug": "product-roadmap-2026",
            "theme": "cyberpunk",
            "description": "Public product strategy and vision",
        },
    ]

    # 1. Create projects
    print(f"\n[1] Creating {len(projects_to_create)} projects...\n")
    created_projects = []

    for i, project_spec in enumerate(projects_to_create, 1):
        project = create_project(
            store,
            title=project_spec["title"],
            slug=project_spec["slug"],
            theme=project_spec.get("theme", "cyberpunk"),
        )
        created_projects.append(project)
        print(f"  [{i}/{len(projects_to_create)}] {project['title']}")
        print(f"             ID: {project['id']}")

    # 2. Trigger builds for all projects
    print(f"\n[2] Triggering builds for {len(created_projects)} projects...\n")
    builds = []

    for i, project in enumerate(created_projects, 1):
        build = create_build(store, project_id=project["id"], trigger_source="batch-example")
        builds.append(build)
        print(f"  [{i}/{len(created_projects)}] Build queued for {project['title']}")
        print(f"             Build ID: {build['id']}")
        print(f"             Status:   {build['status']}")

    # 3. Generate project manifest
    print("\n[3] Generating project manifest...\n")

    all_projects = list_projects(store)
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_projects": len(all_projects),
        "projects": [
            {
                "id": p["id"],
                "title": p.get("title", "Untitled"),
                "slug": p.get("slug", ""),
                "status": p.get("status", "unknown"),
                "created_at": p.get("created_at", ""),
            }
            for p in all_projects
        ],
    }

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"  Manifest written to: {manifest_path}")

    # 4. Summary
    print("\n" + "=" * 60)
    print("Batch Build Complete!")
    print("=" * 60)
    print("\nSummary:")
    print(f"  Projects created: {len(created_projects)}")
    print(f"  Builds triggered: {len(builds)}")
    print(f"  Total in store:   {len(all_projects)}")
    print("\nOutput:")
    print(f"  Store:    {store_path.resolve()}")
    print(f"  Manifest: {manifest_path.resolve()}")
    print("\nNext steps:")
    print(f"  1. View the manifest: cat {manifest_path}")
    print("  2. Try the API server: python 02_api_server.py")
    print("  3. Query for a specific project through the API")

    return 0


if __name__ == "__main__":
    sys.exit(main())
