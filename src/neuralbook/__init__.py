"""
NeuralBook Platform - Encrypted digital book publishing system.

Create high-integrity, encrypted digital content with modern tooling.
"""

__version__ = "1.0.0"
__author__ = "NeuralBook Contributors"
__license__ = "MIT"

from .encryption import encrypt_content, decrypt_content
from .manifest import verify_manifest, generate_manifest
from .build import build_project
from .api import route_request

__all__ = [
    "encrypt_content",
    "decrypt_content", 
    "verify_manifest",
    "generate_manifest",
    "build_project",
    "route_request",
]
