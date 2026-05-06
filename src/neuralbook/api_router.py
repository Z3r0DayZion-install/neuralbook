"""Request router for the NeuralBook platform API."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, cast

from .core import (
    Store,
    capture_email,
    create_build,
    create_project,
    get_build,
    get_project,
    list_artifacts_for_build,
    list_projects,
    update_project,
)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

VERSION = "1.0.0"


def _json_body(raw: bytes) -> Dict[str, Any]:
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
    store_path: Path,
) -> Tuple[int, Dict[str, Any]]:
    """Route an HTTP request to the appropriate handler.

    Args:
        method: HTTP verb (GET, POST, PUT, …)
        path: URL path, may include query string
        body: Raw request body bytes
        store_path: Filesystem path to the JSON data store

    Returns:
        (http_status_code, response_body_dict)
    """
    store = Store(store_path)
    email_path = store_path.parent / "captured_emails.json"

    # Strip query string for routing
    path = path.split("?")[0]

    # Root
    if path == "/" and method == "GET":
        return 200, {
            "message": "NeuralBook Platform API",
            "version": VERSION,
            "docs": "/docs",
        }

    # Health checks
    if path in ("/health", "/healthz") and method == "GET":
        return 200, {"status": "healthy", "service": "creator-platform-api"}

    # Projects collection
    if path == "/v1/projects":
        if method == "GET":
            return 200, list_projects(store)  # type: ignore[return-value]
        if method == "POST":
            data = _json_body(body)
            title = str(data.get("title", "")).strip()
            slug = str(data.get("slug", "")).strip()
            if not title or not slug:
                return 400, {"error": "title and slug are required"}
            theme = str(data.get("theme", "cyberpunk")).strip()
            try:
                project = create_project(store, title=title, slug=slug, theme=theme)
            except ValueError as exc:
                return 409, {"error": str(exc)}
            return 201, project
        return 405, {"error": "method not allowed"}

    # Projects resource
    if path.startswith("/v1/projects/"):
        # ['v1', 'projects', <id>] or ['v1', 'projects', <id>, 'build']
        parts = [p for p in path.split("/") if p]
        project_id = parts[2] if len(parts) > 2 else ""

        # /v1/projects/:id
        if len(parts) == 3:
            if method == "GET":
                proj_get: Optional[Dict[str, Any]] = get_project(store, project_id)
                if not proj_get:
                    return 404, {"error": "project not found"}
                return 200, proj_get
            if method == "PUT":
                maybe_proj: Optional[Dict[str, Any]] = get_project(store, project_id)
                if not maybe_proj:
                    return 404, {"error": "project not found"}
                data = _json_body(body)
                updated = update_project(
                    store,
                    project_id,
                    title=data.get("title"),
                    theme=data.get("theme"),
                    status=data.get("status"),
                    content=data.get("content"),
                    pricing=data.get("pricing"),
                )
                return 200, updated if updated is not None else {}
            return 405, {"error": "method not allowed"}

        # /v1/projects/:id/build  or  /v1/projects/:id/builds
        if len(parts) == 4 and parts[3] in ("build", "builds") and method == "POST":
            data = _json_body(body)
            trigger_source = str(data.get("trigger_source", "manual"))
            try:
                build = create_build(store, project_id=project_id, trigger_source=trigger_source)
            except ValueError as exc:
                return 404, {"error": str(exc)}
            return 202, build

        return 404, {"error": "not found"}

    # Builds resource
    if path.startswith("/v1/builds/"):
        parts = [p for p in path.split("/") if p]
        if len(parts) != 3 or method != "GET":
            return (
                404 if method == "GET" else 405,
                {"error": "not found" if method == "GET" else "method not allowed"},
            )
        build_id = parts[2]
        maybe_build: Optional[Dict[str, Any]] = get_build(store, build_id)
        if not maybe_build:
            return 404, {"error": "build not found"}
        return 200, {
            "build": maybe_build,
            "artifacts": list_artifacts_for_build(store, build_id),
        }

    # Email capture
    if path == "/v1/emails":
        if method == "POST":
            data = _json_body(body)
            email_val = str(data.get("email", "")).strip()
            source_val = str(data.get("source", "")).strip()
            if not email_val or not _EMAIL_RE.match(email_val):
                return 422, {"error": "invalid email address"}
            entry, existed = capture_email(email_path, email_val, source_val)
            if existed:
                return 201, {
                    "success": True,
                    "email": email_val,
                    "message": "email already captured",
                    "already_exists": True,
                }
            return 201, {
                "success": True,
                "email": email_val,
                "message": "email captured successfully",
            }
        return 405, {"error": "method not allowed"}

    return 404, {"error": "not found"}
