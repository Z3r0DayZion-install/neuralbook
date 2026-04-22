"""Core data operations for the NeuralBook platform.

Manages projects, builds, artifacts, and email capture for any title
running on NeuralBook. Title-agnostic — MindUnset, Cognitive Leverage,
and any future title all use these same primitives.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@dataclass
class Store:
    path: Path

    def load(self) -> dict:
        if not self.path.exists():
            return {
                "users": [
                    {
                        "id": "u_local",
                        "email": "local@neuralbook",
                        "display_name": "Local User",
                    }
                ],
                "projects": [],
                "builds": [],
                "artifacts": [],
            }
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def list_projects(store: Store, owner_user_id: str = "u_local") -> list[dict]:
    data = store.load()
    return [p for p in data["projects"] if p["owner_user_id"] == owner_user_id]


def create_project(
    store: Store, title: str, slug: str, owner_user_id: str = "u_local", theme: str = "cyberpunk"
) -> dict:
    data = store.load()
    if any(p["slug"] == slug for p in data["projects"]):
        raise ValueError(f"slug already exists: {slug}")
    project = {
        "id": new_id("p"),
        "owner_user_id": owner_user_id,
        "slug": slug,
        "title": title,
        "theme": theme,
        "status": "draft",
        "content": {
            "metadata": {"title": title, "version": "1.0.0", "format": "MU-FMT-1.0"},
            "chapters": [],
            "case_studies": [],
            "testimonials": [],
        },
        "pricing": {
            "currency": "USD",
            "tiers": [
                {"id": 1, "name": "Free", "price": 0},
                {"id": 2, "name": "Basic", "price": 9},
                {"id": 3, "name": "Pro", "price": 29},
                {"id": 4, "name": "Elite", "price": 99},
            ],
        },
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    data["projects"].append(project)
    store.save(data)
    return project


def get_project(store: Store, project_id: str) -> dict | None:
    data = store.load()
    for p in data["projects"]:
        if p["id"] == project_id:
            return p
    return None


def update_project(store: Store, project_id: str, **fields) -> dict | None:
    data = store.load()
    for i, p in enumerate(data["projects"]):
        if p["id"] == project_id:
            updated = dict(p)
            for k, v in fields.items():
                if v is not None:
                    updated[k] = v
            updated["updated_at"] = now_iso()
            data["projects"][i] = updated
            store.save(data)
            return updated
    return None


def create_build(store: Store, project_id: str, trigger_source: str = "manual") -> dict:
    data = store.load()
    if not any(p["id"] == project_id for p in data["projects"]):
        raise ValueError(f"project not found: {project_id}")
    build = {
        "id": new_id("b"),
        "project_id": project_id,
        "status": "queued",
        "trigger_source": trigger_source,
        "started_at": "",
        "finished_at": "",
        "error_message": "",
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    data["builds"].append(build)
    store.save(data)
    return build


def get_build(store: Store, build_id: str) -> dict | None:
    data = store.load()
    for b in data["builds"]:
        if b["id"] == build_id:
            return b
    return None


def update_build(store: Store, build_id: str, **fields) -> dict:
    data = store.load()
    for i, b in enumerate(data["builds"]):
        if b["id"] == build_id:
            updated = dict(b)
            updated.update(fields)
            updated["updated_at"] = now_iso()
            data["builds"][i] = updated
            store.save(data)
            return updated
    raise ValueError(f"build not found: {build_id}")


def add_artifact(
    store: Store, build_id: str, kind: str, path: str, sha256: str, bytes_size: int
) -> dict:
    data = store.load()
    artifact = {
        "id": new_id("a"),
        "build_id": build_id,
        "kind": kind,
        "path": path,
        "sha256": sha256,
        "bytes": int(bytes_size),
        "created_at": now_iso(),
    }
    data["artifacts"].append(artifact)
    store.save(data)
    return artifact


def list_artifacts_for_build(store: Store, build_id: str) -> list[dict]:
    data = store.load()
    return [a for a in data["artifacts"] if a["build_id"] == build_id]


@dataclass
class EmailStore:
    path: Path

    def load(self) -> dict:
        if not self.path.exists():
            return {"emails": []}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"emails": []}

    def save(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def capture_email(email_path: Path, email: str, source: str) -> tuple[dict, bool]:
    """Store email. Returns (entry, already_existed)."""
    es = EmailStore(email_path)
    data = es.load()
    existing = next((e for e in data["emails"] if e["email"] == email), None)
    if existing:
        return existing, True
    entry = {
        "email": email,
        "source": source,
        "captured_at": now_iso(),
        "confirmed": False,
    }
    data["emails"].append(entry)
    es.save(data)
    return entry, False
