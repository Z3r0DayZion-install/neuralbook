"""NeuralBook Platform API — unified FastAPI service for creators and readers.

Creator endpoints:
- POST /v1/projects              Create a new book project
- GET  /v1/projects              List all projects
- GET  /v1/projects/{id}         Get project details
- PUT  /v1/projects/{id}         Update project
- POST /v1/projects/{id}/builds  Trigger a new build
- GET  /v1/builds/{id}           Get build status + artifacts
- POST /v1/emails                Capture reader email

Reader/Book endpoints:
- GET  /books                    List registered books
- POST /books                    Register a new book
- GET  /books/{slug}             Get book metadata
- GET  /books/{slug}/patches     List available patches
- POST /books/{slug}/patches     Upload a new patch
- GET  /books/{slug}/patches/{id} Download a specific patch
- GET  /books/{slug}/latest      Get latest patch info
- POST /books/{slug}/verify      Verify a book's integrity against registry
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    from fastapi import (
        Depends,
        FastAPI,
        File,
        Header,
        HTTPException,
        Query,
        Request,
        UploadFile,
        status,
    )
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from fastapi.security import APIKeyHeader
    from pydantic import BaseModel, Field
    from slowapi import Limiter
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address
except ImportError:
    raise ImportError("platform_api requires fastapi+slowapi: pip install 'neuralbook[server]'")

logger = logging.getLogger("neuralbook.platform")

# ── Auth ─────────────────────────────────────────────────────────────────
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)
_raw_keys = os.environ.get("NBOOK_API_KEYS", "").strip()
VALID_API_KEYS = set(_raw_keys.split(",")) if _raw_keys else set()


async def verify_api_key(key: Optional[str] = Header(None, alias=API_KEY_NAME)):
    """Require API key for write operations. Empty NBOOK_API_KEYS = no auth."""
    if not VALID_API_KEYS:
        return True  # Auth disabled if no keys configured
    if not key or key not in VALID_API_KEYS:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or missing API key")
    return True


# ── App ──────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(_: FastAPI):
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    logger.info(f"NeuralBook Platform API starting — data dir: {DATA_DIR}")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _pg_init()
    try:
        yield
    finally:
        logger.info("NeuralBook Platform API shutting down")


app = FastAPI(
    title="NeuralBook Platform API",
    version="1.0.0",
    description="Unified API for NeuralBook creators and readers.\n\n"
    "Creator endpoints require an API key when NBOOK_API_KEYS is set. "
    "Reader endpoints are public.",
    openapi_tags=[
        {
            "name": "creator",
            "description": "Creator operations — project management, builds, email capture",
        },
        {
            "name": "reader",
            "description": "Reader operations — book discovery, patch delivery, integrity verification",
        },
    ],
    lifespan=lifespan,
)
# ── CORS ─────────────────────────────────────────────────────────────────
_allowed_origins = os.environ.get("NBOOK_CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,  # type: ignore[arg-type]
    allow_origins=_allowed_origins,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["X-API-Key", "Content-Type", "Authorization"],
    max_age=3600,
)

# ── Style presets ───────────────────────────────────────────────────────────

_STYLE_PRESETS = {
    "minimal": {
        "body": {
            "font-family": "system-ui, -apple-system, sans-serif",
            "background": "#ffffff",
            "color": "#1a1a1a",
        },
        "h1": {"font-size": "2.5rem", "font-weight": "600", "margin-bottom": "1rem"},
        "h2": {"font-size": "2rem", "font-weight": "600", "margin-bottom": "0.8rem"},
        "p": {"line-height": "1.7", "margin-bottom": "1rem"},
        "code": {"font-family": "monospace", "background": "#f5f5f5", "padding": "0.2rem 0.4rem"},
    },
    "cyberpunk": {
        "body": {
            "font-family": "'Courier New', monospace",
            "background": "#0a0a0a",
            "color": "#00ff00",
        },
        "h1": {
            "font-size": "3rem",
            "font-weight": "700",
            "color": "#ff00ff",
            "text-shadow": "0 0 10px #ff00ff",
        },
        "h2": {
            "font-size": "2rem",
            "font-weight": "700",
            "color": "#00ffff",
            "text-shadow": "0 0 8px #00ffff",
        },
        "p": {"line-height": "1.6", "margin-bottom": "1rem", "color": "#00ff00"},
        "code": {
            "font-family": "monospace",
            "background": "#1a1a1a",
            "color": "#ffff00",
            "border": "1px solid #00ff00",
        },
    },
    "academic": {
        "body": {"font-family": "Georgia, serif", "background": "#fffef8", "color": "#2c2c2c"},
        "h1": {
            "font-size": "2.2rem",
            "font-weight": "600",
            "color": "#2c2c2c",
            "border-bottom": "2px solid #2c2c2c",
        },
        "h2": {"font-size": "1.8rem", "font-weight": "600", "color": "#2c2c2c"},
        "p": {"line-height": "1.8", "margin-bottom": "1.2rem", "text-align": "justify"},
        "code": {"font-family": "Times New Roman, serif", "font-style": "italic", "color": "#444"},
    },
    "dark": {
        "body": {
            "font-family": "system-ui, sans-serif",
            "background": "#1a1a1a",
            "color": "#e0e0e0",
        },
        "h1": {"font-size": "2.5rem", "font-weight": "600", "color": "#ffffff"},
        "h2": {"font-size": "2rem", "font-weight": "600", "color": "#ffffff"},
        "p": {"line-height": "1.7", "margin-bottom": "1rem", "color": "#e0e0e0"},
        "code": {"font-family": "monospace", "background": "#2a2a2a", "color": "#a0ffa0"},
    },
    "serif": {
        "body": {
            "font-family": "Georgia, 'Times New Roman', serif",
            "background": "#faf9f5",
            "color": "#333",
        },
        "h1": {"font-size": "2.5rem", "font-weight": "600", "color": "#222"},
        "h2": {"font-size": "2rem", "font-weight": "600", "color": "#333"},
        "p": {"line-height": "1.8", "margin-bottom": "1.2rem"},
        "code": {"font-family": "Courier New, monospace", "background": "#eee", "color": "#555"},
    },
}


def _get_style_css(style_name: str) -> str:
    """Get CSS for a style preset."""
    preset = _STYLE_PRESETS.get(style_name, _STYLE_PRESETS["minimal"])
    css_parts = []
    for selector, props in preset.items():
        prop_str = "; ".join(f"{k.replace('_', '-')}: {v}" for k, v in props.items())
        css_parts.append(f"{selector} {{ {prop_str}; }}")
    return "\n".join(css_parts)


# ── Rate limiting ─────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429, content={"error": "rate_limit_exceeded", "detail": str(exc)}
    )


# ── Global error handler ──────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception on {request.method} {request.url.path}")
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "detail": "An unexpected error occurred"},
    )


DATA_DIR = Path(os.environ.get("NBOOK_DATA", "./nbook_data"))
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# ── Postgres email storage (optional; falls back to JSON if no DATABASE_URL) ──
_DATABASE_URL: Optional[str] = os.environ.get("DATABASE_URL")


def _pg_init() -> None:
    """Create the emails table if DATABASE_URL is set."""
    if not _DATABASE_URL:
        return
    try:
        import psycopg2  # type: ignore

        with psycopg2.connect(_DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS emails (
                        email       TEXT PRIMARY KEY,
                        source      TEXT NOT NULL DEFAULT 'landing',
                        captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                        confirmed   BOOLEAN NOT NULL DEFAULT false
                    );
                    """
                )
            conn.commit()
        logger.info("Postgres email table ready")
    except Exception as exc:  # pragma: no cover
        logger.error(f"Postgres init failed (falling back to JSON): {exc}")


def _pg_capture_email(email: str, source: str) -> dict:
    """Insert or ignore duplicate email via Postgres. Returns result dict."""
    import psycopg2  # type: ignore

    with psycopg2.connect(_DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO emails (email, source)
                VALUES (%s, %s)
                ON CONFLICT (email) DO NOTHING
                RETURNING email;
                """,
                (email, source),
            )
            row = cur.fetchone()
        conn.commit()
    if row:
        return {"success": True, "email": email, "message": "email captured successfully"}
    return {"success": True, "email": email, "message": "email already captured", "already_exists": True}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _book_dir(slug: str) -> Path:
    return DATA_DIR / "books" / slug


def _patches_dir(slug: str) -> Path:
    d = _book_dir(slug) / "patches"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _store_path() -> Path:
    p = DATA_DIR / "platform_store.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


_store_lock = threading.Lock()


def _load_store() -> dict:
    p = _store_path()
    if not p.exists():
        return {"projects": [], "builds": [], "artifacts": [], "emails": []}
    try:
        return dict(json.loads(p.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Corrupted store file: {e}")
        return {"projects": [], "builds": [], "artifacts": [], "emails": []}


def _save_store(data: dict) -> None:
    p = _store_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with _store_lock:
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        tmp.replace(p)  # Atomic on most filesystems


# ── Models ───────────────────────────────────────────────────────────────


class ProjectCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: str = Field("", max_length=2000)
    theme: str = Field("cyberpunk", max_length=50)


class ProjectUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    theme: Optional[str] = Field(None, max_length=50)
    status: Optional[str] = Field(None, pattern=r"^(draft|published|archived)$")
    content: Optional[dict] = None
    pricing: Optional[list] = None


class BookRegistration(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    author: str = Field("", max_length=200)
    edition: str = Field("1.0.0", pattern=r"^\d+\.\d+\.\d+$")
    root_hash: str = Field("", max_length=128)
    format_version: str = Field("NB-FMT-1.0", max_length=20)
    style: str = Field("minimal", pattern=r"^(minimal|cyberpunk|academic|dark|serif)$")


class TierCreate(BaseModel):
    id: str = Field(..., min_length=1, max_length=50, pattern=r"^[a-z0-9_-]+$")
    name: str = Field(..., min_length=1, max_length=100)
    price: float = Field(..., ge=0)
    currency: str = Field("USD", max_length=3)
    features: list[str] = Field(default_factory=list)
    description: str = Field("", max_length=500)


class TierUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    price: Optional[float] = Field(None, ge=0)
    features: Optional[list[str]] = None
    description: Optional[str] = Field(None, max_length=500)
    active: Optional[bool] = None


class ReaderTierAssignment(BaseModel):
    email: str = Field(..., pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    tier_id: str = Field(..., min_length=1)
    book_slug: str = Field(..., min_length=1)
    expires_at: Optional[str] = None  # ISO datetime


class EmailCapture(BaseModel):
    email: str = Field(..., pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    source: str = Field("", max_length=100)


class VerifyRequest(BaseModel):
    root_hash: str = Field(..., min_length=64, max_length=64)


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None


class PaginatedResponse(BaseModel):
    items: list
    count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


# ── Root ──────────────────────────────────────────────────────────────────


@app.get("/")
async def root():
    return {
        "message": "NeuralBook Platform API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "creator": ["/v1/projects", "/v1/builds", "/v1/emails"],
            "reader": ["/books", "/books/{slug}/patches", "/books/{slug}/verify"],
        },
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "neuralbook-platform"}


@app.get("/metrics", tags=["reader"])
async def metrics():
    """System metrics for monitoring."""
    data = _load_store()
    books_dir = DATA_DIR / "books"
    book_count = len([d for d in books_dir.iterdir()]) if books_dir.exists() else 0
    return {
        "projects": len(data.get("projects", [])),
        "builds": len(data.get("builds", [])),
        "emails": len(data.get("emails", [])),
        "books": book_count,
        "data_dir": str(DATA_DIR),
        "version": "1.0.0",
    }


# ══════════════════════════════════════════════════════════════════════════
# CREATOR ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════


@app.post("/v1/projects", status_code=201, tags=["creator"], dependencies=[Depends(verify_api_key)])
async def create_project(proj: ProjectCreate):
    """Create a new book project."""
    data = _load_store()
    if any(p["slug"] == proj.slug for p in data["projects"]):
        raise HTTPException(409, f"slug '{proj.slug}' already exists")
    project = {
        "id": _new_id("proj"),
        "title": proj.title,
        "slug": proj.slug,
        "description": proj.description,
        "theme": proj.theme,
        "status": "draft",
        "content": {
            "metadata": {"title": proj.title, "version": "1.0.0", "format": "NB-FMT-1.0"},
            "chapters": [],
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
        "created_at": _now(),
        "updated_at": _now(),
    }
    data["projects"].append(project)
    _save_store(data)
    return project


@app.get("/v1/projects", tags=["creator"])
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, pattern=r"^(draft|published|archived)$"),
    search: Optional[str] = Query(None),
    sort_by: str = Query("created_at", pattern=r"^(created_at|updated_at|title)$"),
    sort_desc: bool = Query(False),
):
    """List projects with pagination, filtering, and sorting."""
    data = _load_store()
    projects = data.get("projects", [])

    # Filter
    if status:
        projects = [p for p in projects if p.get("status") == status]
    if search:
        projects = [p for p in projects if search.lower() in p.get("title", "").lower()]

    # Sort
    reverse = sort_desc
    projects = sorted(projects, key=lambda p: p.get(sort_by, ""), reverse=reverse)

    # Paginate
    total = len(projects)
    total_pages = (total + page_size - 1) // page_size
    start = (page - 1) * page_size
    end = start + page_size
    items = projects[start:end]

    return {
        "projects": items,
        "count": len(items),
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
    }


@app.get("/v1/projects/{project_id}", tags=["creator"])
async def get_project(project_id: str):
    """Get project details."""
    data = _load_store()
    for p in data["projects"]:
        if p["id"] == project_id:
            return p
    raise HTTPException(404, f"project '{project_id}' not found")


@app.put("/v1/projects/{project_id}", tags=["creator"], dependencies=[Depends(verify_api_key)])
async def update_project(project_id: str, updates: ProjectUpdate):
    """Update a project."""
    data = _load_store()
    for i, p in enumerate(data["projects"]):
        if p["id"] == project_id:
            for k, v in updates.model_dump(exclude_none=True).items():
                p[k] = v
            p["updated_at"] = _now()
            data["projects"][i] = p
            _save_store(data)
            return p
    raise HTTPException(404, f"project '{project_id}' not found")


@app.post(
    "/v1/projects/{project_id}/builds",
    status_code=202,
    tags=["creator"],
    dependencies=[Depends(verify_api_key)],
)
async def trigger_build(
    project_id: str, trigger_source: str = Query("manual", pattern=r"^(manual|api|webhook)$")
):
    """Trigger a new build for a project."""
    data = _load_store()
    if not any(p["id"] == project_id for p in data["projects"]):
        raise HTTPException(404, f"project '{project_id}' not found")
    build = {
        "id": _new_id("build"),
        "project_id": project_id,
        "status": "pending",
        "trigger_source": trigger_source,
        "started_at": "",
        "finished_at": "",
        "created_at": _now(),
        "updated_at": _now(),
    }
    data["builds"].append(build)
    _save_store(data)
    return build


@app.get("/v1/builds/{build_id}", tags=["creator"])
async def get_build(build_id: str):
    """Get build status and artifacts."""
    data = _load_store()
    for b in data["builds"]:
        if b["id"] == build_id:
            artifacts = [a for a in data.get("artifacts", []) if a.get("build_id") == build_id]
            return {"build": b, "artifacts": artifacts}
    raise HTTPException(404, f"build '{build_id}' not found")


@app.post("/v1/emails", status_code=201, tags=["creator"])
async def capture_email(email_data: EmailCapture):
    """Capture a reader email address."""
    email = email_data.email.strip()
    if not email or not _EMAIL_RE.match(email):
        raise HTTPException(422, "invalid email address")
    if _DATABASE_URL:
        try:
            result = _pg_capture_email(email, email_data.source or "landing")
            if result.get("already_exists"):
                return JSONResponse(status_code=200, content=result)
            return result
        except Exception as exc:
            logger.error(f"Postgres email capture failed: {exc}")
            raise HTTPException(503, "email service temporarily unavailable")
    # --- JSON fallback (no DATABASE_URL) ---
    data = _load_store()
    existing = next((e for e in data["emails"] if e["email"] == email), None)
    if existing:
        return JSONResponse(
            status_code=200,
            content={"success": True, "email": email, "message": "email already captured", "already_exists": True},
        )
    entry = {"email": email, "source": email_data.source, "captured_at": _now(), "confirmed": False}
    data["emails"].append(entry)
    _save_store(data)
    return {"success": True, "email": email, "message": "email captured successfully"}


# ══════════════════════════════════════════════════════════════════════════
# TIER MANAGEMENT ENDPOINTS (Book-specific, stored in book folders)
# ══════════════════════════════════════════════════════════════════════════


def _tiers_file(slug: str) -> Path:
    """Get path to tiers.yaml for a book."""
    return _book_dir(slug) / "tiers.yaml"


def _subscribers_file(slug: str) -> Path:
    """Get path to subscribers.yaml for a book."""
    return _book_dir(slug) / "subscribers.yaml"


def _load_tiers(slug: str) -> list:
    """Load tiers from book's tiers.yaml."""
    tf = _tiers_file(slug)
    if not tf.exists():
        return []
    try:
        import yaml

        return list(yaml.safe_load(tf.read_text(encoding="utf-8")) or [])
    except ImportError:
        # Fallback to JSON if no yaml
        tf_json = _book_dir(slug) / "tiers.json"
        if tf_json.exists():
            return list(json.loads(tf_json.read_text(encoding="utf-8")))
        return []


def _save_tiers(slug: str, tiers: list):
    """Save tiers to book's tiers.yaml."""
    tf = _tiers_file(slug)
    try:
        import yaml

        tf.write_text(yaml.dump(tiers, default_flow_style=False, sort_keys=False), encoding="utf-8")
    except ImportError:
        # Fallback to JSON
        tf_json = _book_dir(slug) / "tiers.json"
        tf_json.write_text(json.dumps(tiers, indent=2), encoding="utf-8")


def _load_subscribers(slug: str) -> list:
    """Load subscriber assignments from book's subscribers.yaml."""
    sf = _subscribers_file(slug)
    if not sf.exists():
        return []
    try:
        import yaml

        return list(yaml.safe_load(sf.read_text(encoding="utf-8")) or [])
    except ImportError:
        sf_json = _book_dir(slug) / "subscribers.json"
        if sf_json.exists():
            return list(json.loads(sf_json.read_text(encoding="utf-8")))
        return []


def _save_subscribers(slug: str, subscribers: list):
    """Save subscribers to book's subscribers.yaml."""
    sf = _subscribers_file(slug)
    try:
        import yaml

        sf.write_text(
            yaml.dump(subscribers, default_flow_style=False, sort_keys=False), encoding="utf-8"
        )
    except ImportError:
        sf_json = _book_dir(slug) / "subscribers.json"
        sf_json.write_text(json.dumps(subscribers, indent=2), encoding="utf-8")


@app.post(
    "/v1/books/{slug}/tiers",
    status_code=201,
    tags=["creator"],
    dependencies=[Depends(verify_api_key)],
)
async def create_book_tier(slug: str, tier: TierCreate):
    """Create a pricing tier for a specific book. Stored in book's tiers.yaml."""
    bd = _book_dir(slug)
    if not (bd / "meta.json").exists():
        raise HTTPException(404, f"Book '{slug}' not found")

    tiers = _load_tiers(slug)
    if any(t["id"] == tier.id for t in tiers):
        raise HTTPException(409, f"tier '{tier.id}' already exists for this book")

    tier_data = tier.model_dump()
    tier_data["created_at"] = _now()
    tier_data["updated_at"] = _now()
    tier_data["active"] = True
    tiers.append(tier_data)
    _save_tiers(slug, tiers)

    return {"status": "created", "tier": tier_data, "file": str(_tiers_file(slug))}


@app.get("/v1/books/{slug}/tiers", tags=["creator"])
async def list_book_tiers(slug: str, active_only: bool = False):
    """List all pricing tiers for a book."""
    bd = _book_dir(slug)
    if not (bd / "meta.json").exists():
        raise HTTPException(404, f"Book '{slug}' not found")

    tiers = _load_tiers(slug)
    if active_only:
        tiers = [t for t in tiers if t.get("active", True)]
    return {"tiers": tiers, "count": len(tiers), "file": str(_tiers_file(slug))}


@app.get("/v1/books/{slug}/tiers/{tier_id}", tags=["creator"])
async def get_book_tier(slug: str, tier_id: str):
    """Get tier details for a book."""
    bd = _book_dir(slug)
    if not (bd / "meta.json").exists():
        raise HTTPException(404, f"Book '{slug}' not found")

    tiers = _load_tiers(slug)
    for t in tiers:
        if t["id"] == tier_id:
            return t
    raise HTTPException(404, f"tier '{tier_id}' not found for book '{slug}'")


@app.put(
    "/v1/books/{slug}/tiers/{tier_id}", tags=["creator"], dependencies=[Depends(verify_api_key)]
)
async def update_book_tier(slug: str, tier_id: str, updates: TierUpdate):
    """Update a tier for a book."""
    bd = _book_dir(slug)
    if not (bd / "meta.json").exists():
        raise HTTPException(404, f"Book '{slug}' not found")

    tiers = _load_tiers(slug)
    for i, t in enumerate(tiers):
        if t["id"] == tier_id:
            for k, v in updates.model_dump(exclude_none=True).items():
                t[k] = v
            t["updated_at"] = _now()
            tiers[i] = t
            _save_tiers(slug, tiers)
            return {"status": "updated", "tier": t, "file": str(_tiers_file(slug))}
    raise HTTPException(404, f"tier '{tier_id}' not found for book '{slug}'")


@app.post(
    "/v1/books/{slug}/subscribers",
    status_code=201,
    tags=["creator"],
    dependencies=[Depends(verify_api_key)],
)
async def subscribe_reader(slug: str, assignment: ReaderTierAssignment):
    """Subscribe a reader to a tier for a book. Stored in book's subscribers.yaml."""
    bd = _book_dir(slug)
    if not (bd / "meta.json").exists():
        raise HTTPException(404, f"Book '{slug}' not found")

    # Check tier exists
    tiers = _load_tiers(slug)
    tier = next((t for t in tiers if t["id"] == assignment.tier_id), None)
    if not tier:
        raise HTTPException(404, f"Tier '{assignment.tier_id}' not found for book '{slug}'")

    # Record subscription
    subscribers = _load_subscribers(slug)

    # Check if already subscribed
    existing = next((s for s in subscribers if s["email"] == assignment.email), None)
    if existing:
        # Update existing subscription
        existing["tier_id"] = assignment.tier_id
        existing["updated_at"] = _now()
        existing["expires_at"] = assignment.expires_at
        existing["price_paid"] = tier["price"]
        existing["currency"] = tier["currency"]
    else:
        # New subscription
        subscription = {
            "email": assignment.email,
            "tier_id": assignment.tier_id,
            "book_slug": slug,
            "subscribed_at": _now(),
            "updated_at": _now(),
            "expires_at": assignment.expires_at,
            "price_paid": tier["price"],
            "currency": tier["currency"],
            "payments": [{"amount": tier["price"], "date": _now(), "currency": tier["currency"]}],
        }
        subscribers.append(subscription)

    _save_subscribers(slug, subscribers)

    return {
        "status": "subscribed" if not existing else "updated",
        "subscription": existing if existing else subscription,
        "file": str(_subscribers_file(slug)),
    }


@app.get("/v1/books/{slug}/subscribers", tags=["creator"])
async def list_subscribers(slug: str, tier_id: Optional[str] = None):
    """List all subscribers for a book."""
    bd = _book_dir(slug)
    if not (bd / "meta.json").exists():
        raise HTTPException(404, f"Book '{slug}' not found")

    subscribers = _load_subscribers(slug)
    if tier_id:
        subscribers = [s for s in subscribers if s["tier_id"] == tier_id]
    return {
        "subscribers": subscribers,
        "count": len(subscribers),
        "file": str(_subscribers_file(slug)),
    }


@app.get("/v1/books/{slug}/subscribers/{email}", tags=["creator"])
async def get_subscriber(slug: str, email: str):
    """Get subscription details for a reader."""
    bd = _book_dir(slug)
    if not (bd / "meta.json").exists():
        raise HTTPException(404, f"Book '{slug}' not found")

    subscribers = _load_subscribers(slug)
    for s in subscribers:
        if s["email"] == email:
            # Add tier details
            tiers = _load_tiers(slug)
            tier: dict = next((t for t in tiers if t["id"] == s["tier_id"]), {})
            s["tier_name"] = tier.get("name")
            s["features"] = tier.get("features", [])

            # Check expiration
            if s.get("expires_at"):
                expires = datetime.fromisoformat(s["expires_at"].replace("Z", "+00:00"))
                s["is_expired"] = datetime.now(timezone.utc) > expires
                s["has_access"] = not s["is_expired"]
            else:
                s["is_expired"] = False
                s["has_access"] = True

            return s
    raise HTTPException(404, f"subscriber '{email}' not found for book '{slug}'")


@app.get("/v1/books/{slug}/pricing", tags=["reader"])
async def get_book_pricing(slug: str):
    """Get public pricing info for a book (reader-facing)."""
    bd = _book_dir(slug)
    if not (bd / "meta.json").exists():
        raise HTTPException(404, f"Book '{slug}' not found")

    tiers = _load_tiers(slug)
    # Only return active tiers, filter out internal fields
    public_tiers = []
    for t in tiers:
        if t.get("active", True):
            public_tiers.append(
                {
                    "id": t["id"],
                    "name": t["name"],
                    "price": t["price"],
                    "currency": t.get("currency", "USD"),
                    "features": t.get("features", []),
                    "description": t.get("description", ""),
                }
            )
    return {"book_slug": slug, "tiers": public_tiers, "count": len(public_tiers)}


@app.get("/v1/books/{slug}/analytics", tags=["creator"])
async def get_book_analytics(slug: str):
    """Get tier analytics for a book (revenue, subscriber counts)."""
    bd = _book_dir(slug)
    if not (bd / "meta.json").exists():
        raise HTTPException(404, f"Book '{slug}' not found")

    tiers = _load_tiers(slug)
    subscribers = _load_subscribers(slug)

    # Calculate per-tier stats
    tier_stats = {}
    total_revenue = 0

    for tier in tiers:
        tier_id = tier["id"]
        tier_subs = [s for s in subscribers if s["tier_id"] == tier_id]
        tier_revenue = sum(s.get("price_paid", 0) for s in tier_subs)
        total_revenue += tier_revenue

        # Count active vs expired
        active_count = 0
        expired_count = 0
        for s in tier_subs:
            if s.get("expires_at"):
                expires = datetime.fromisoformat(s["expires_at"].replace("Z", "+00:00"))
                if datetime.now(timezone.utc) > expires:
                    expired_count += 1
                else:
                    active_count += 1
            else:
                active_count += 1

        tier_stats[tier_id] = {
            "tier_name": tier["name"],
            "price": tier["price"],
            "total_subscribers": len(tier_subs),
            "active_subscribers": active_count,
            "expired_subscribers": expired_count,
            "revenue": tier_revenue,
            "currency": tier.get("currency", "USD"),
        }

    return {
        "book_slug": slug,
        "total_subscribers": len(subscribers),
        "total_revenue": total_revenue,
        "by_tier": tier_stats,
        "files": {
            "tiers": str(_tiers_file(slug)),
            "subscribers": str(_subscribers_file(slug)),
        },
    }


def _check_reader_access(email: str, book_slug: str, required_feature: "Optional[str]" = None) -> dict:
    """Check if a reader has access to a book based on their tier (reads from book folder)."""
    bd = _book_dir(book_slug)
    if not (bd / "meta.json").exists():
        return {"has_access": False, "reason": "book not found"}

    subscribers = _load_subscribers(book_slug)
    subscription = next((s for s in subscribers if s["email"] == email), None)

    if not subscription:
        return {"has_access": False, "tier_id": None, "features": []}

    # Check expiration
    if subscription.get("expires_at"):
        expires = datetime.fromisoformat(subscription["expires_at"].replace("Z", "+00:00"))
        if datetime.now(timezone.utc) > expires:
            return {
                "has_access": False,
                "tier_id": subscription["tier_id"],
                "expired": True,
                "features": [],
            }

    # Get tier features
    tiers = _load_tiers(book_slug)
    tier: dict = next((t for t in tiers if t["id"] == subscription["tier_id"]), {})
    features = tier.get("features", [])

    # Check specific feature requirement
    if required_feature and required_feature not in features:
        return {
            "has_access": False,
            "tier_id": subscription["tier_id"],
            "reason": f"feature '{required_feature}' not available in your tier",
            "available_features": features,
        }

    return {
        "has_access": True,
        "tier_id": subscription["tier_id"],
        "tier_name": tier.get("name"),
        "features": features,
    }


# ══════════════════════════════════════════════════════════════════════════
# READER / BOOK ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════


@app.get("/books", tags=["reader"])
async def list_books(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    sort_by: str = Query("registered_at", pattern=r"^(registered_at|title|author)$"),
    sort_desc: bool = Query(False),
):
    """List registered books with pagination, filtering, and sorting."""
    from fastapi import Response

    books_dir = DATA_DIR / "books"
    if not books_dir.exists():
        return {
            "books": [],
            "count": 0,
            "page": 1,
            "page_size": page_size,
            "total": 0,
            "total_pages": 0,
            "has_next": False,
            "has_prev": False,
        }
    books = []
    for d in sorted(books_dir.iterdir()):
        if d.is_dir():
            meta_path = d / "meta.json"
            if meta_path.exists():
                books.append(json.loads(meta_path.read_text(encoding="utf-8")))

    # Filter
    if search:
        books = [
            b
            for b in books
            if search.lower() in b.get("title", "").lower()
            or search.lower() in b.get("author", "").lower()
        ]

    # Sort
    reverse = sort_desc
    books = sorted(books, key=lambda b: b.get(sort_by, ""), reverse=reverse)

    # Paginate
    total = len(books)
    total_pages = (total + page_size - 1) // page_size
    start = (page - 1) * page_size
    end = start + page_size
    items = books[start:end]

    response = {
        "books": items,
        "count": len(items),
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
    }
    headers = {"Cache-Control": "public, max-age=60"}
    return Response(content=json.dumps(response), media_type="application/json", headers=headers)


@app.post("/books", status_code=201, tags=["reader"], dependencies=[Depends(verify_api_key)])
async def register_book(reg: BookRegistration):
    """Register a new book in the platform."""
    bd = _book_dir(reg.slug)
    if (bd / "meta.json").exists():
        raise HTTPException(409, f"Book '{reg.slug}' already registered")
    bd.mkdir(parents=True, exist_ok=True)
    meta = {
        "title": reg.title,
        "slug": reg.slug,
        "author": reg.author,
        "edition": reg.edition,
        "root_hash": reg.root_hash,
        "format_version": reg.format_version,
        "style": reg.style,
        "registered_at": _now(),
        "updated_at": _now(),
        "patch_count": 0,
    }
    (bd / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return {"status": "registered", "book": meta}


@app.get("/books/{slug}", tags=["reader"])
async def get_book(slug: str):
    """Get book metadata."""
    meta_path = _book_dir(slug) / "meta.json"
    if not meta_path.exists():
        raise HTTPException(404, f"Book '{slug}' not found")
    return json.loads(meta_path.read_text(encoding="utf-8"))


@app.get("/books/{slug}/patches", tags=["reader"])
async def list_patches(slug: str):
    """List all available patches for a book."""
    pd = _patches_dir(slug)
    if not pd.exists():
        return {"patches": [], "count": 0}
    patches = []
    for f in sorted(pd.glob("*.nbook-patch.json")):
        patches.append(json.loads(f.read_text(encoding="utf-8")))
    return {"patches": patches, "count": len(patches)}


@app.post("/books/{slug}/patches", tags=["reader"], dependencies=[Depends(verify_api_key)])
async def upload_patch(slug: str, file: UploadFile = File(...)):
    """Upload a new patch for a book."""
    bd = _book_dir(slug)
    if not (bd / "meta.json").exists():
        raise HTTPException(404, f"Book '{slug}' not found")
    content = await file.read()
    try:
        patch_data = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON patch file")
    patch_id = patch_data.get("neuralbook_patch", {}).get("patch_id", uuid.uuid4().hex[:8])
    pd = _patches_dir(slug)
    patch_path = pd / f"{patch_id}.nbook-patch.json"
    patch_path.write_text(json.dumps(patch_data, indent=2) + "\n", encoding="utf-8")
    # Update book meta
    meta_path = bd / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["patch_count"] = meta.get("patch_count", 0) + 1
    meta["updated_at"] = _now()
    new_hash = patch_data.get("verification", {}).get("new_root_hash", "")
    if new_hash:
        meta["root_hash"] = new_hash
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return {"status": "uploaded", "patch_id": patch_id}


@app.get("/books/{slug}/patches/{patch_id}", tags=["reader"])
async def get_patch(slug: str, patch_id: str):
    """Download a specific patch."""
    patch_path = _patches_dir(slug) / f"{patch_id}.nbook-patch.json"
    if not patch_path.exists():
        raise HTTPException(404, f"Patch '{patch_id}' not found")
    return json.loads(patch_path.read_text(encoding="utf-8"))


@app.get("/books/{slug}/latest", tags=["reader"])
async def latest_patch(slug: str):
    """Get the latest patch info for a book."""
    pd = _patches_dir(slug)
    if not pd.exists():
        return {"latest": None, "patch_count": 0}
    patches = sorted(pd.glob("*.nbook-patch.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not patches:
        return {"latest": None, "patch_count": 0}
    latest = json.loads(patches[0].read_text(encoding="utf-8"))
    return {"latest": latest, "patch_count": len(patches)}


@app.post("/books/{slug}/verify", tags=["reader"])
async def verify_book(slug: str, body: VerifyRequest):
    """Verify a book's root hash against the registry."""
    meta_path = _book_dir(slug) / "meta.json"
    if not meta_path.exists():
        raise HTTPException(404, f"Book '{slug}' not found")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    expected = meta.get("root_hash", "")
    if not expected:
        return {"status": "no_reference", "message": "No root hash on file for this book"}
    match = body.root_hash == expected
    return {
        "status": "match" if match else "mismatch",
        "expected": expected[:32] + "...",
        "provided": body.root_hash[:32] + "...",
    }


@app.get("/books/{slug}/export", tags=["reader"])
async def export_book(slug: str, format: str = Query(..., pattern=r"^(epub|html)$")):
    """Export a registered book to EPUB or HTML with custom style."""
    from fastapi.responses import FileResponse

    from neuralbook.export import export_epub, export_html
    from neuralbook.format import NeuralBookDocument

    bd = _book_dir(slug)
    meta_path = bd / "meta.json"
    if not meta_path.exists():
        raise HTTPException(404, f"Book '{slug}' not found")

    # Get book metadata for style
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    style_name = meta.get("style", "minimal")

    # Look for the actual .nbook file in the book directory
    nbook_files = list(bd.glob("*.nbook"))
    if not nbook_files:
        # Try parent directory
        parent_files = list(bd.parent.glob("*.nbook"))
        if not parent_files:
            raise HTTPException(404, f"No .nbook file found for book '{slug}'")
        nbook_path = parent_files[0]
    else:
        nbook_path = nbook_files[0]

    doc = NeuralBookDocument.from_file(nbook_path)
    export_path = DATA_DIR / "exports" / f"{slug}.{format}"
    export_path.parent.mkdir(parents=True, exist_ok=True)

    if format == "epub":
        export_epub(doc, export_path)
        media_type = "application/epub+zip"
    else:
        export_html(doc, export_path)
        # Inject custom style into HTML
        html_content = export_path.read_text(encoding="utf-8")
        style_css = _get_style_css(style_name)
        style_tag = f"<style>\n{style_css}\n</style>"
        # Insert style tag after <head>
        html_content = html_content.replace("<head>", f"<head>\n{style_tag}")
        export_path.write_text(html_content, encoding="utf-8")
        media_type = "text/html"

    return FileResponse(
        export_path,
        media_type=media_type,
        filename=f"{slug}.{format}",
        headers={"Cache-Control": "public, max-age=3600"},
    )


# ── Server entrypoint ─────────────────────────────────────────────────────


def start_server():
    """Start the NeuralBook Platform API server (configured via env vars)."""
    import uvicorn

    host = os.environ.get("NBOOK_HOST", "0.0.0.0")
    port = int(os.environ.get("NBOOK_PORT") or os.environ.get("PORT", "8000"))
    log_level = os.environ.get("NBOOK_LOG_LEVEL", "info").lower()
    uvicorn.run(app, host=host, port=port, log_level=log_level)
