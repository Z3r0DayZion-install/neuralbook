"""
Test fixtures and configuration for NeuralBook tests.
"""

import pytest
from pathlib import Path
import tempfile
import shutil


@pytest.fixture
def tmp_project():
    """Create temporary project directory."""
    tmpdir = Path(tempfile.mkdtemp())
    
    # Create basic structure
    (tmpdir / "content").mkdir()
    
    # Create minimal config
    (tmpdir / "config.yaml").write_text("""
title: Test Book
author: Test Author
version: 1.0.0
""")
    
    yield tmpdir
    
    # Cleanup
    shutil.rmtree(tmpdir)


@pytest.fixture
def encryption_key():
    """Generate test encryption key."""
    import os
    return os.urandom(48)
