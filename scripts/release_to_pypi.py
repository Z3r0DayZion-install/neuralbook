#!/usr/bin/env python3
"""
NeuralBook Release Script
========================

Automates PyPI release process:
1. Validates package
2. Builds distribution
3. Tests installation
4. Publishes to PyPI

Usage:
  python scripts/release_to_pypi.py [--dry-run] [--skip-tests]

Requirements:
  pip install build twine wheel
"""

import argparse
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


def run_command(cmd: list, description: str = None) -> int:
    """Run a shell command and return exit code."""
    if description:
        print(f"\n{'='*60}")
        print(f">> {description}")
        print(f"{'='*60}")

    print(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
    return result.returncode


def main():
    """Execute release workflow."""
    parser = argparse.ArgumentParser(description="Release NeuralBook to PyPI")
    parser.add_argument("--dry-run", action="store_true", help="Test only, don't publish")
    parser.add_argument("--skip-tests", action="store_true", help="Skip test suite")
    parser.add_argument("--skip-validation", action="store_true", help="Skip twine validation")
    parser.add_argument(
        "--allow-upload",
        action="store_true",
        help="Allow upload step (disabled by default for dry-run safety)",
    )
    args = parser.parse_args()

    root_dir = Path(__file__).parent.parent
    dist_dir = root_dir / "dist"

    print("\n" + "=" * 60)
    print("NeuralBook PyPI Release Workflow")
    print("=" * 60)
    print(f"[PACKAGE] {root_dir.name}")
    print(f"[TIME] {datetime.now(UTC).isoformat()}")
    print(f"[MODE] {'DRY RUN' if args.dry_run else 'PRODUCTION'}")
    print("=" * 60)

    # Step 1: Clean previous builds
    print("\n[1/5] Cleaning previous distributions...")
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir(exist_ok=True)
    print("  [OK] Cleaned")

    # Step 2: Run tests
    if not args.skip_tests:
        print("\n[2/5] Running test suite...")
        if run_command(["python", "-m", "pytest", "tests/", "-v", "--cov"], "Running pytest") != 0:
            print("  [FAIL] Tests failed - aborting release")
            return 1
        print("  [OK] All tests passed")
    else:
        print("\n[2/5] Skipping tests")

    # Step 3: Build distributions
    print("\n[3/5] Building distributions...")
    if run_command(["python", "-m", "build"], "Building wheel and source distribution") != 0:
        print("  [FAIL] Build failed")
        return 1

    # List built files
    dist_files = list(dist_dir.glob("*"))
    print(f"  [OK] Built {len(dist_files)} distribution files:")
    for f in sorted(dist_files):
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"    - {f.name} ({size_mb:.2f} MB)")

    # Step 4: Validate with twine
    if not args.skip_validation:
        print("\n[4/5] Validating package...")
        dist_files = list(dist_dir.glob("*"))
        if (
            run_command(
                ["python", "-m", "twine", "check"] + [str(f) for f in dist_files],
                "Checking package validity",
            )
            != 0
        ):
            print("  [FAIL] Validation failed")
            return 1
        print("  [OK] Package valid for PyPI")
    else:
        print("\n[4/5] Skipping validation")

    # Step 5: Upload to PyPI
    print("\n[5/5] Publishing to PyPI...")

    dist_files = list(dist_dir.glob("*"))
    did_upload = False
    if not args.allow_upload:
        print("  [INFO] Upload skipped (safe default). Use --allow-upload to publish.")
    else:
        if args.dry_run:
            print("  [INFO] DRY RUN MODE - Uploading to test repository")
            cmd = (
                ["python", "-m", "twine", "upload"]
                + [str(f) for f in dist_files]
                + ["--repository-url", "https://test.pypi.org/legacy/", "--skip-existing"]
            )
        else:
            print("  [INFO] Uploading to production PyPI")
            cmd = (
                ["python", "-m", "twine", "upload"]
                + [str(f) for f in dist_files]
                + ["--skip-existing"]
            )

        if run_command(cmd, "Uploading distributions") != 0:
            print("  [FAIL] Upload failed")
            return 1
        did_upload = True

    # Success
    print("\n" + "=" * 60)
    print("SUCCESS: Release Complete!")
    print("=" * 60)

    if args.dry_run:
        print("\nTest Repository:")
        print("   https://test.pypi.org/project/neuralbook/")
        print("\nTest installation:")
        print("   pip install --index-url https://test.pypi.org/simple/ neuralbook")
    else:
        print("\nPyPI Package:")
        print("   https://pypi.org/project/neuralbook/")
        print("\nInstall:")
        print("   pip install neuralbook")

    if did_upload:
        print("\nPackage published successfully!")
    else:
        print("\nRelease checks completed successfully (no upload performed).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
