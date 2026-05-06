"""
NeuralBook Platform - Encrypted digital book publishing system.

Create high-integrity, encrypted digital content with modern tooling.
"""

__version__ = "1.0.0"
__author__ = "NeuralBook Contributors"
__license__ = "MIT"

from .api import route_request
from .build import build_project
from .core import (
    Store,
    create_build,
    create_project,
    get_build,
    get_project,
    list_artifacts_for_build,
    list_projects,
    update_project,
)
from .encryption import (
    decrypt_content,
    decrypt_file,
    derive_key,
    discover_key,
    encrypt_content,
    encrypt_file,
)
from .export import export_epub, export_html
from .format import (
    NeuralBookDocument,
    import_txt,
    validate_format,
    validate_full,
    validate_integrity,
    validate_structure,
)
from .manifest import generate_manifest, verify_manifest

__all__ = [
    # Encryption
    "encrypt_content",
    "decrypt_content",
    "encrypt_file",
    "decrypt_file",
    "derive_key",
    "discover_key",
    # Manifest
    "verify_manifest",
    "generate_manifest",
    # Build pipeline
    "build_project",
    # API
    "route_request",
    # Data layer
    "Store",
    "create_project",
    "create_build",
    "get_project",
    "get_build",
    "list_projects",
    "update_project",
    "list_artifacts_for_build",
    # NeuralBook Format SDK
    "NeuralBookDocument",
    "import_txt",
    "validate_full",
    "validate_format",
    "validate_integrity",
    "validate_structure",
    # Export
    "export_epub",
    "export_html",
]
