"""
NeuralBook HTTP API - Production routing and handlers.

Provides REST endpoints for:
- Project CRUD operations
- Build triggering and status
- Content management
- Email capture
"""

import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, cast

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
VERSION = "1.0.0"


def now_iso() -> str:
    """ISO8601 timestamp."""
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    """Generate unique ID with prefix."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@dataclass
class Project:
    id: str
    title: str
    slug: str
    description: str = ""
    status: str = "draft"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self) -> None:
        if self.created_at is None:
            self.created_at = now_iso()
        if self.updated_at is None:
            self.updated_at = now_iso()


@dataclass
class Build:
    id: str
    project_id: str
    status: str = "pending"  # pending, building, success, failed
    created_at: Optional[str] = None
    completed_at: Optional[str] = None

    def __post_init__(self) -> None:
        if self.created_at is None:
            self.created_at = now_iso()


class Store:
    """JSON-based data store for projects and builds."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def load(self) -> Dict[str, Any]:
        """Load store from disk."""
        if not self.path.exists():
            return {"projects": [], "builds": []}
        try:
            return cast(Dict[str, Any], json.loads(self.path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, FileNotFoundError):
            return {"projects": [], "builds": []}

    def save(self, data: Dict[str, Any]) -> None:
        """Save store to disk."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _json_body(raw: bytes) -> Dict[str, Any]:
    """Parse JSON from request body."""
    if not raw:
        return {}
    try:
        return cast(Dict[str, Any], json.loads(raw.decode("utf-8")))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def route_request(
    method: str,
    path: str,
    body: bytes,
    store_path: Optional[Path] = None,
) -> Tuple[int, Dict[str, Any]]:
    """Route HTTP request to appropriate handler.

    Args:
        method: HTTP method (GET, POST, PUT, DELETE)
        path: Request path (with optional query string)
        body: Request body bytes
        store_path: Path to data store JSON

    Returns:
        (status_code, response_dict)
    """
    if store_path is None:
        store_path = Path("./data/platform_store.json")

    store = Store(store_path)

    # Strip query string for routing
    path = path.split("?")[0]

    # Root
    if path == "/" and method == "GET":
        return 200, {
            "message": "NeuralBook Platform API",
            "version": VERSION,
            "docs": "https://docs.neuralbook.dev/api",
        }

    # Health checks
    if path in ("/health", "/healthz") and method == "GET":
        return 200, {"status": "healthy", "service": "neuralbook-api"}

    # Projects collection
    if path == "/v1/projects":
        if method == "GET":
            data = store.load()
            return 200, {"projects": data.get("projects", [])}
        if method == "POST":
            data = _json_body(body)
            title = str(data.get("title", "")).strip()
            slug = str(data.get("slug", "")).strip()
            if not title or not slug:
                return 400, {"error": "title and slug are required"}

            store_data = store.load()
            if any(p.get("slug") == slug for p in store_data.get("projects", [])):
                return 409, {"error": "slug already exists"}

            project: Dict[str, Any] = {
                "id": new_id("proj"),
                "title": title,
                "slug": slug,
                "description": data.get("description", ""),
                "status": "draft",
                "created_at": now_iso(),
                "updated_at": now_iso(),
            }
            store_data.get("projects", []).append(project)
            store.save(store_data)
            return 201, project

        return 405, {"error": "method not allowed"}

    # Projects resource
    if path.startswith("/v1/projects/"):
        parts = [p for p in path.split("/") if p]
        if len(parts) < 3:
            return 404, {"error": "not found"}

        project_id = parts[2]

        # GET /v1/projects/:id
        if len(parts) == 3 and method == "GET":
            store_data = store.load()
            for proj in store_data.get("projects", []):
                if proj.get("id") == project_id:
                    return 200, cast(Dict[str, Any], proj)
            return 404, {"error": "project not found"}

        # POST /v1/projects/:id/builds
        if len(parts) == 4 and parts[3] == "builds" and method == "POST":
            store_data = store.load()
            if not any(p.get("id") == project_id for p in store_data.get("projects", [])):
                return 404, {"error": "project not found"}

            build: Dict[str, Any] = {
                "id": new_id("build"),
                "project_id": project_id,
                "status": "pending",
                "created_at": now_iso(),
            }
            store_data.setdefault("builds", []).append(build)
            store.save(store_data)
            return 202, build

        return 404, {"error": "not found"}

    # Builds resource
    if path.startswith("/v1/builds/"):
        parts = [p for p in path.split("/") if p]
        if len(parts) != 3 or method != "GET":
            return 404, {"error": "not found"}

        build_id = parts[2]
        store_data = store.load()
        for b in store_data.get("builds", []):
            if b.get("id") == build_id:
                return 200, cast(Dict[str, Any], b)
        return 404, {"error": "build not found"}

    # Email capture
    if path == "/v1/emails":
        if method == "POST":
            req_data = _json_body(body)
            email = str(req_data.get("email", "")).strip()
            if not email or not _EMAIL_RE.match(email):
                return 422, {"error": "invalid email address"}

            return 201, {
                "success": True,
                "email": email,
                "message": "email captured successfully",
            }
        return 405, {"error": "method not allowed"}

    return 404, {"error": "not found"}
