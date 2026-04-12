"""Neura Web API — standalone FastAPI application.

Provides REST + WebSocket endpoints for the Neura Web UI (Phase 3).
This is a STANDALONE app: do NOT import from transport/app.py.
Integration into the main process happens manually at startup.

Usage (standalone testing):
    python3 -m neura.transport.web

Usage (integrated):
    from neura.transport.web import create_web_app
    app = create_web_app(db_pool, engine, memory, queue, capsules)
"""
import asyncio
import logging
import os
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Optional

try:
    from neura.core.document_processor import build_file_context as build_doc_context
except ImportError:
    build_doc_context = None  # fallback to inline builder

import uvicorn
from fastapi import (
    Depends, FastAPI, HTTPException, Request, UploadFile, WebSocket,
    WebSocketDisconnect, status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, EmailStr, field_validator

from neura.core.engine import EngineConfig
from neura.transport.auth import (
    create_token, get_current_user, hash_password, refresh_token, verify_password,
)

logger = logging.getLogger(__name__)

# Upload directory
UPLOAD_DIR = Path(os.environ.get("NEURA_UPLOAD_DIR", "/tmp/neura-uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Generated files directory (where Claude writes images/docs via tools)
GENERATED_DIR = Path("/tmp")

# Max concurrent streams per user
MAX_CONCURRENT_STREAMS = 2


import re as _re
import yaml

_FILE_MARKER_RE = _re.compile(r'\[FILE:(.*?)\]')

# Retryable error patterns (network, rate limit, timeout — NOT auth or bad request)
_RETRYABLE_PATTERNS = ["timeout", "rate limit", "overloaded", "connection", "ECONNRESET", "529", "503", "502"]

def _is_retryable_error(error_text: str) -> bool:
    lower = error_text.lower()
    return any(p in lower for p in _RETRYABLE_PATTERNS)


# ── Theme config loader ─────────────────────────────────────────

_theme_cache: dict = {}
_theme_mapping: dict | None = None


def _load_theme(capsule_id: str | None) -> dict | None:
    """Load theme config for capsule. Returns None for default theme."""
    global _theme_cache, _theme_mapping

    themes_dir = Path("/opt/neura-v2/config/themes")

    # Load mapping if needed
    if _theme_mapping is None:
        mapping_file = themes_dir / "_mapping.yaml"
        if mapping_file.exists():
            with open(mapping_file) as f:
                _theme_mapping = yaml.safe_load(f) or {}
        else:
            _theme_mapping = {}

    # Get theme_id for this capsule
    theme_id = _theme_mapping.get(capsule_id, "default") if capsule_id else "default"

    if theme_id == "default":
        return None  # Frontend uses built-in defaults

    # Load theme config
    if theme_id not in _theme_cache:
        theme_file = themes_dir / f"{theme_id}.yaml"
        if theme_file.exists():
            with open(theme_file) as f:
                _theme_cache[theme_id] = yaml.safe_load(f)
        else:
            return None

    return _theme_cache.get(theme_id)


def _clear_theme_cache():
    """Clear cached theme data (call on reload/restart)."""
    global _theme_cache, _theme_mapping
    _theme_cache = {}
    _theme_mapping = None


def _process_file_markers(text: str) -> str:
    """Replace [FILE:/path/to/file] markers with web-accessible URLs.

    Images become markdown images, other files become download links.
    """
    IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'}

    def _replace(m):
        fpath = m.group(1).strip()
        p = Path(fpath)
        if not p.exists():
            return f"*(файл не найден: {p.name})*"
        # Copy to uploads dir with unique name so it's servable
        dest_name = f"{uuid.uuid4().hex}_{p.name}"
        dest = UPLOAD_DIR / dest_name
        import shutil
        shutil.copy2(fpath, dest)
        url = f"/api/files/serve/{dest_name}"
        if p.suffix.lower() in IMAGE_EXTS:
            return f"\n![{p.name}]({url})\n"
        return f"\n[{p.name}]({url})\n"

    return _FILE_MARKER_RE.sub(_replace, text)


class StreamSession:
    """A background streaming session, decoupled from WebSocket lifecycle.

    Chunks are kept in memory for replay on reconnect.
    Max 100 chunks retained (prevents memory leak on long streams).
    Sessions auto-expire after 3 minutes of being done.
    """

    _MAX_CHUNKS = 100

    def __init__(self, conv_id: int, user_id: int):
        self.conv_id = conv_id
        self.user_id = user_id
        self.task: asyncio.Task | None = None
        self.chunks: list[dict] = []
        self.done = False
        self.done_at: float = 0.0
        self.final_chunk: dict | None = None
        self.subscribers: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def broadcast(self, data: dict):
        """Send to all connected subscribers, remove dead ones."""
        if len(self.chunks) < self._MAX_CHUNKS:
            self.chunks.append(data)
        dead = set()
        for ws in self.subscribers:
            try:
                await ws.send_json(data)
            except Exception:
                dead.add(ws)
        self.subscribers -= dead

    def cancel(self):
        if self.task and not self.task.done():
            self.task.cancel()

    @property
    def expired(self) -> bool:
        """Session is expired if done for >5 minutes."""
        return self.done and self.done_at > 0 and (time.monotonic() - self.done_at) > 300


class StreamManager:
    """Manages background stream sessions per user."""

    def __init__(self):
        # user_id → {conv_id → StreamSession}
        self._sessions: dict[int, dict[int, StreamSession]] = defaultdict(dict)

    def get_session(self, user_id: int, conv_id: int) -> StreamSession | None:
        return self._sessions.get(user_id, {}).get(conv_id)

    def active_count(self, user_id: int) -> int:
        return sum(1 for s in self._sessions.get(user_id, {}).values() if not s.done)

    def active_sessions(self, user_id: int) -> list[StreamSession]:
        return [s for s in self._sessions.get(user_id, {}).values() if not s.done]

    def create_session(self, user_id: int, conv_id: int) -> StreamSession:
        # Cleanup expired sessions first
        self._cleanup()
        session = StreamSession(conv_id, user_id)
        self._sessions[user_id][conv_id] = session
        return session

    def _cleanup(self):
        """Remove expired sessions to free memory."""
        for uid in list(self._sessions):
            expired = [cid for cid, s in self._sessions[uid].items() if s.expired]
            for cid in expired:
                del self._sessions[uid][cid]
            if not self._sessions[uid]:
                del self._sessions[uid]

    def remove_session(self, user_id: int, conv_id: int):
        sessions = self._sessions.get(user_id, {})
        sessions.pop(conv_id, None)
        # Cleanup old done sessions (keep last 5)
        done_sessions = [(cid, s) for cid, s in sessions.items() if s.done]
        if len(done_sessions) > 5:
            for cid, _ in done_sessions[:-5]:
                sessions.pop(cid, None)

    async def periodic_cleanup(self, interval: int = 60):
        """Background task: periodically remove expired sessions."""
        while True:
            await asyncio.sleep(interval)
            try:
                self._cleanup()
            except Exception as exc:
                logger.warning("StreamManager cleanup error: %s", exc)


# ── Pydantic schemas ─────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str


class ProjectCreate(BaseModel):
    name: str
    icon: str = ""
    description: str = ""
    instructions: str = ""


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    pinned: Optional[bool] = None
    icon: Optional[str] = None
    description: Optional[str] = None
    instructions: Optional[str] = None
    links: Optional[list] = None


class ConversationCreate(BaseModel):
    title: Optional[str] = None
    project_id: Optional[int] = None


class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    project_id: Optional[int] = None
    pinned: Optional[bool] = None


class WSMessage(BaseModel):
    text: str
    files: list[str] = []


# ── Rate limiter (simple in-memory, per IP) ──────────────────────

_rate_store: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = 10      # requests per window for auth endpoints


def _check_rate_limit(ip: str) -> bool:
    """Return False if rate limit exceeded."""
    now = time.monotonic()
    history = _rate_store[ip]
    # Drop old entries
    cutoff = now - RATE_LIMIT_WINDOW
    _rate_store[ip] = [t for t in history if t > cutoff]
    if len(_rate_store[ip]) >= RATE_LIMIT_MAX:
        return False
    _rate_store[ip].append(now)
    return True


# ── Factory ──────────────────────────────────────────────────────

def create_web_app(
    db_pool=None,
    engine=None,
    memory=None,
    queue=None,
    capsules: dict | None = None,
) -> FastAPI:
    """Create and return a configured FastAPI application.

    All arguments are optional to allow standalone testing with mocks.
    """
    app = FastAPI(
        title="Neura Web API",
        version="2.0.0",
        docs_url="/api/docs",
        redoc_url=None,
    )

    # Rate limiter (per-capsule, 8 req/min)
    from neura.transport.rate_limit import RateLimiter
    _rate_limiter = RateLimiter(window_sec=60, max_requests=8)

    # Stream manager for background sessions
    stream_mgr = StreamManager()

    @app.on_event("startup")
    async def _start_stream_cleanup():
        asyncio.create_task(stream_mgr.periodic_cleanup())

    # Claude CLI session_id per conversation (conv_id → session_id)
    # Enables --resume: continue existing session instead of starting fresh
    _claude_sessions: dict[int, str] = {}
    _CLAUDE_SESSIONS_MAX = 200

    # CORS — whitelist production + local dev
    _cors_origins = os.environ.get("NEURA_CORS_ORIGINS", "").strip()
    _allowed_origins = (
        [o.strip() for o in _cors_origins.split(",") if o.strip()]
        if _cors_origins
        else ["https://app.ceremoneymeister.ru", "http://localhost:5173", "http://localhost:4173"]
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # ── Request logging middleware ───────────────────────────────

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            "%s %s → %d (%.0fms)",
            request.method, request.url.path,
            response.status_code, duration_ms,
        )
        return response

    # Store context in app.state for access inside routes
    app.state.db_pool = db_pool
    app.state.engine = engine
    app.state.memory = memory
    app.state.queue = queue
    app.state.capsules = capsules or {}

    # ── Auth shortcuts ───────────────────────────────────────────

    CurrentUser = Annotated[dict, Depends(get_current_user)]

    def pool(request: Request):
        p = request.app.state.db_pool
        if p is None:
            raise HTTPException(500, "Database not available")
        return p

    Pool = Annotated[object, Depends(pool)]

    # ═══════════════════════════════════════════════════════════
    # AUTH
    # ═══════════════════════════════════════════════════════════

    @app.post("/api/auth/register", status_code=201)
    async def register(body: RegisterRequest, request: Request):
        """Register a new user. Returns JWT token + user object."""
        ip = request.client.host if request.client else "unknown"
        if not _check_rate_limit(f"auth:{ip}"):
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Rate limit exceeded")

        p = request.app.state.db_pool
        if p is None:
            raise HTTPException(500, "Database not available")

        # Check duplicate
        existing = await p.fetchrow(
            "SELECT id FROM users WHERE email = $1", body.email.lower()
        )
        if existing:
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

        pw_hash = hash_password(body.password)

        # Auto-assign first available capsule (default for web users)
        default_capsule = await p.fetchval(
            "SELECT id FROM capsules ORDER BY id LIMIT 1"
        )

        row = await p.fetchrow(
            """INSERT INTO users (email, password_hash, name, capsule_id)
               VALUES ($1, $2, $3, $4) RETURNING id, email, name, capsule_id, created_at""",
            body.email.lower(), pw_hash, body.name, default_capsule,
        )
        token = create_token(row["id"], row["email"], row["capsule_id"])
        return {
            "token": token,
            "user": _user_to_dict(row),
        }

    @app.post("/api/auth/login")
    async def login(body: LoginRequest, request: Request):
        """Authenticate existing user. Returns JWT token + user object."""
        ip = request.client.host if request.client else "unknown"
        if not _check_rate_limit(f"auth:{ip}"):
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Rate limit exceeded")

        p = request.app.state.db_pool
        if p is None:
            raise HTTPException(500, "Database not available")

        row = await p.fetchrow(
            "SELECT id, email, name, password_hash, capsule_id, created_at FROM users WHERE email = $1",
            body.email.lower(),
        )
        if not row or not verify_password(body.password, row["password_hash"]):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

        token = create_token(row["id"], row["email"], row["capsule_id"])
        return {
            "token": token,
            "user": _user_to_dict(row),
        }

    @app.post("/api/auth/refresh")
    async def auth_refresh(request: Request):
        """Refresh a JWT token. Accepts expired tokens up to 7 days old."""
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed",
            )
        old_token = auth_header[len("Bearer "):]
        try:
            new_token = refresh_token(old_token)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed",
            )
        return {"token": new_token}

    @app.get("/api/auth/me")
    async def get_me(current_user: CurrentUser, request: Request):
        """Return current authenticated user info."""
        p = request.app.state.db_pool
        if p is None:
            raise HTTPException(500, "Database not available")

        row = await p.fetchrow(
            "SELECT id, email, name, capsule_id, created_at FROM users WHERE id = $1",
            current_user["user_id"],
        )
        if not row:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
        return {"user": _user_to_dict(row)}

    # ═══════════════════════════════════════════════════════════
    # THEME
    # ═══════════════════════════════════════════════════════════

    @app.get("/api/theme")
    async def get_theme(current_user: CurrentUser, request: Request):
        """Return theme config for current user's capsule."""
        capsule_id = current_user.get("capsule_id")
        theme = _load_theme(capsule_id)
        if theme is None:
            return JSONResponse({"theme_id": "default"})
        return JSONResponse(theme)

    # ═══════════════════════════════════════════════════════════
    # PROJECTS
    # ═══════════════════════════════════════════════════════════

    @app.get("/api/projects")
    async def list_projects(current_user: CurrentUser, request: Request):
        """List all projects for current user with conversation count."""
        p = request.app.state.db_pool
        if p is None:
            raise HTTPException(500, "Database not available")

        rows = await p.fetch(
            """SELECT pr.id, pr.name, pr.description, pr.instructions, pr.links, pr.pinned, pr.icon, pr.sort_order, pr.created_at,
                      COUNT(c.id)::int AS chats_count
               FROM projects pr
               LEFT JOIN conversations c ON c.project_id = pr.id
               WHERE pr.user_id = $1
               GROUP BY pr.id
               ORDER BY pr.pinned DESC, pr.sort_order, pr.created_at DESC""",
            current_user["user_id"],
        )
        return [_project_to_dict(r) for r in rows]

    @app.post("/api/projects", status_code=201)
    async def create_project(body: ProjectCreate, current_user: CurrentUser, request: Request):
        """Create a new project."""
        p = request.app.state.db_pool
        if p is None:
            raise HTTPException(500, "Database not available")

        row = await p.fetchrow(
            """INSERT INTO projects (user_id, name, icon, description, instructions)
               VALUES ($1, $2, $3, $4, $5)
               RETURNING id, name, description, instructions, links, pinned, icon, sort_order, created_at""",
            current_user["user_id"], body.name, body.icon, body.description, body.instructions,
        )
        return _project_to_dict(row)

    @app.patch("/api/projects/{project_id}")
    async def update_project(
        project_id: int, body: ProjectUpdate,
        current_user: CurrentUser, request: Request,
    ):
        """Update project name, pinned status, or icon."""
        p = request.app.state.db_pool
        if p is None:
            raise HTTPException(500, "Database not available")

        existing = await p.fetchrow(
            "SELECT id FROM projects WHERE id = $1 AND user_id = $2",
            project_id, current_user["user_id"],
        )
        if not existing:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")

        updates = {}
        if body.name is not None:
            updates["name"] = body.name
        if body.pinned is not None:
            updates["pinned"] = body.pinned
        if body.icon is not None:
            updates["icon"] = body.icon
        if body.description is not None:
            updates["description"] = body.description
        if body.instructions is not None:
            updates["instructions"] = body.instructions
        if body.links is not None:
            import json as _json
            updates["links"] = _json.dumps(body.links)

        if not updates:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "No fields to update")

        set_clause = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(updates))
        values = list(updates.values())
        row = await p.fetchrow(
            f"""UPDATE projects SET {set_clause}
                WHERE id = $1
                RETURNING id, name, description, instructions, links, pinned, icon, sort_order, created_at""",
            project_id, *values,
        )
        return _project_to_dict(row)

    @app.delete("/api/projects/{project_id}", status_code=204)
    async def delete_project(
        project_id: int, current_user: CurrentUser, request: Request,
    ):
        """Delete a project (conversations become unassigned)."""
        p = request.app.state.db_pool
        if p is None:
            raise HTTPException(500, "Database not available")

        result = await p.execute(
            "DELETE FROM projects WHERE id = $1 AND user_id = $2",
            project_id, current_user["user_id"],
        )
        if result == "DELETE 0":
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")

    @app.get("/api/projects/{project_id}")
    async def get_project(
        project_id: int, current_user: CurrentUser, request: Request,
    ):
        """Get a single project with conversation count."""
        p = request.app.state.db_pool
        if p is None:
            raise HTTPException(500, "Database not available")

        row = await p.fetchrow(
            """SELECT pr.id, pr.name, pr.description, pr.instructions, pr.links, pr.pinned, pr.icon, pr.sort_order, pr.created_at,
                      COUNT(c.id)::int AS chats_count
               FROM projects pr
               LEFT JOIN conversations c ON c.project_id = pr.id
               WHERE pr.id = $1 AND pr.user_id = $2
               GROUP BY pr.id""",
            project_id, current_user["user_id"],
        )
        if not row:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
        return _project_to_dict(row)

    @app.get("/api/projects/{project_id}/conversations")
    async def list_project_conversations(
        project_id: int, current_user: CurrentUser, request: Request,
    ):
        """List all conversations belonging to a project."""
        p = request.app.state.db_pool
        if p is None:
            raise HTTPException(500, "Database not available")

        proj = await p.fetchrow(
            "SELECT id FROM projects WHERE id = $1 AND user_id = $2",
            project_id, current_user["user_id"],
        )
        if not proj:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")

        rows = await p.fetch(
            """SELECT c.id, c.title, c.project_id, c.pinned, c.created_at, c.updated_at,
                      (SELECT content FROM messages m
                       WHERE m.conversation_id = c.id
                       ORDER BY m.created_at DESC LIMIT 1) AS last_message
               FROM conversations c
               WHERE c.project_id = $1 AND c.user_id = $2
               ORDER BY c.pinned DESC, c.updated_at DESC""",
            project_id, current_user["user_id"],
        )
        return [_conversation_to_dict(r) for r in rows]

    @app.get("/api/projects/{project_id}/auto-context")
    async def get_project_auto_context(
        project_id: int, current_user: CurrentUser, request: Request,
    ):
        """Generate auto-context from project chats: titles, message count, recent topics."""
        p = request.app.state.db_pool
        if p is None:
            raise HTTPException(500, "Database not available")

        proj = await p.fetchrow(
            "SELECT id FROM projects WHERE id = $1 AND user_id = $2",
            project_id, current_user["user_id"],
        )
        if not proj:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")

        # Chat summaries with message counts
        chats = await p.fetch(
            """SELECT c.id, c.title, c.updated_at,
                      COUNT(m.id)::int AS message_count,
                      (SELECT content FROM messages m2
                       WHERE m2.conversation_id = c.id AND m2.role = 'user'
                       ORDER BY m2.created_at DESC LIMIT 1) AS last_user_message
               FROM conversations c
               LEFT JOIN messages m ON m.conversation_id = c.id
               WHERE c.project_id = $1 AND c.user_id = $2
               GROUP BY c.id
               ORDER BY c.updated_at DESC
               LIMIT 20""",
            project_id, current_user["user_id"],
        )

        # Extract URLs from recent messages
        import re
        url_pattern = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+')
        urls: list[dict] = []
        seen_urls: set[str] = set()

        recent_msgs = await p.fetch(
            """SELECT m.content, m.created_at
               FROM messages m
               JOIN conversations c ON c.id = m.conversation_id
               WHERE c.project_id = $1 AND c.user_id = $2
               ORDER BY m.created_at DESC
               LIMIT 100""",
            project_id, current_user["user_id"],
        )

        for msg in recent_msgs:
            for url in url_pattern.findall(msg["content"] or ""):
                if url not in seen_urls and len(urls) < 20:
                    seen_urls.add(url)
                    urls.append({
                        "url": url,
                        "found_at": msg["created_at"].isoformat() if msg["created_at"] else None,
                    })

        return {
            "chats": [
                {
                    "id": c["id"],
                    "title": c["title"],
                    "message_count": c["message_count"],
                    "last_user_message": (c["last_user_message"] or "")[:200],
                    "updated_at": c["updated_at"].isoformat() if c["updated_at"] else None,
                }
                for c in chats
            ],
            "auto_links": urls,
            "total_messages": sum(c["message_count"] for c in chats),
            "total_chats": len(chats),
        }

    @app.get("/api/projects/{project_id}/members")
    async def list_project_members(
        project_id: int, current_user: CurrentUser, request: Request,
    ):
        """List members (capsules) of a project."""
        p = request.app.state.db_pool
        if p is None:
            raise HTTPException(500, "Database not available")

        proj = await p.fetchrow(
            "SELECT id FROM projects WHERE id = $1 AND user_id = $2",
            project_id, current_user["user_id"],
        )
        if not proj:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")

        rows = await p.fetch(
            "SELECT id, capsule_id, role, added_at FROM project_members WHERE project_id = $1 ORDER BY added_at",
            project_id,
        )
        return [
            {"id": r["id"], "capsule_id": r["capsule_id"], "role": r["role"],
             "added_at": r["added_at"].isoformat() if r["added_at"] else None}
            for r in rows
        ]

    @app.post("/api/projects/{project_id}/members", status_code=201)
    async def add_project_member(
        project_id: int, body: dict, current_user: CurrentUser, request: Request,
    ):
        """Add a capsule to a project."""
        p = request.app.state.db_pool
        if p is None:
            raise HTTPException(500, "Database not available")

        proj = await p.fetchrow(
            "SELECT id FROM projects WHERE id = $1 AND user_id = $2",
            project_id, current_user["user_id"],
        )
        if not proj:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")

        capsule_id = body.get("capsule_id", "").strip()
        role = body.get("role", "member")
        if not capsule_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "capsule_id required")

        row = await p.fetchrow(
            """INSERT INTO project_members (project_id, capsule_id, role)
               VALUES ($1, $2, $3)
               ON CONFLICT (project_id, capsule_id) DO UPDATE SET role = $3
               RETURNING id, capsule_id, role, added_at""",
            project_id, capsule_id, role,
        )
        return {"id": row["id"], "capsule_id": row["capsule_id"], "role": row["role"],
                "added_at": row["added_at"].isoformat() if row["added_at"] else None}

    @app.delete("/api/projects/{project_id}/members/{member_id}", status_code=204)
    async def remove_project_member(
        project_id: int, member_id: int, current_user: CurrentUser, request: Request,
    ):
        """Remove a capsule from a project."""
        p = request.app.state.db_pool
        if p is None:
            raise HTTPException(500, "Database not available")

        await p.execute(
            """DELETE FROM project_members
               WHERE id = $1 AND project_id = $2
               AND project_id IN (SELECT id FROM projects WHERE user_id = $3)""",
            member_id, project_id, current_user["user_id"],
        )

    # ═══════════════════════════════════════════════════════════
    # CONVERSATIONS
    # ═══════════════════════════════════════════════════════════

    @app.get("/api/conversations")
    async def list_conversations(current_user: CurrentUser, request: Request):
        """List conversations for current user, newest first, with last message preview."""
        p = request.app.state.db_pool
        if p is None:
            raise HTTPException(500, "Database not available")

        rows = await p.fetch(
            """SELECT c.id, c.title, c.project_id, c.pinned, c.model, c.created_at, c.updated_at,
                      (SELECT content FROM messages m
                       WHERE m.conversation_id = c.id
                       ORDER BY m.created_at DESC LIMIT 1) AS last_message
               FROM conversations c
               WHERE c.user_id = $1
               ORDER BY c.pinned DESC, c.updated_at DESC""",
            current_user["user_id"],
        )
        return [_conversation_to_dict(r) for r in rows]

    @app.post("/api/conversations", status_code=201)
    async def create_conversation(
        body: ConversationCreate, current_user: CurrentUser, request: Request,
    ):
        """Create a new conversation."""
        p = request.app.state.db_pool
        if p is None:
            raise HTTPException(500, "Database not available")

        title = body.title or "Новый чат"
        row = await p.fetchrow(
            """INSERT INTO conversations (user_id, project_id, title)
               VALUES ($1, $2, $3)
               RETURNING id, title, project_id, pinned, model, created_at, updated_at""",
            current_user["user_id"], body.project_id, title,
        )
        return _conversation_to_dict(row)

    @app.patch("/api/conversations/{conv_id}")
    async def update_conversation(
        conv_id: int, body: ConversationUpdate,
        current_user: CurrentUser, request: Request,
    ):
        """Update conversation title, project, or pinned status."""
        p = request.app.state.db_pool
        if p is None:
            raise HTTPException(500, "Database not available")

        existing = await p.fetchrow(
            "SELECT id FROM conversations WHERE id = $1 AND user_id = $2",
            conv_id, current_user["user_id"],
        )
        if not existing:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")

        updates = {}
        if body.title is not None:
            updates["title"] = body.title
        if body.project_id is not None:
            updates["project_id"] = body.project_id
        if body.pinned is not None:
            updates["pinned"] = body.pinned

        if not updates:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "No fields to update")

        set_clause = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(updates))
        values = list(updates.values())
        row = await p.fetchrow(
            f"""UPDATE conversations SET {set_clause}
                WHERE id = $1
                RETURNING id, title, project_id, pinned, model, created_at, updated_at""",
            conv_id, *values,
        )
        return _conversation_to_dict(row)

    @app.delete("/api/conversations/{conv_id}", status_code=204)
    async def delete_conversation(
        conv_id: int, current_user: CurrentUser, request: Request,
    ):
        """Delete a conversation and all its messages."""
        p = request.app.state.db_pool
        if p is None:
            raise HTTPException(500, "Database not available")

        result = await p.execute(
            "DELETE FROM conversations WHERE id = $1 AND user_id = $2",
            conv_id, current_user["user_id"],
        )
        if result == "DELETE 0":
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
        # Clean up Claude CLI session for this conversation
        _claude_sessions.pop(conv_id, None)

    @app.get("/api/conversations/{conv_id}/messages")
    async def get_messages(
        conv_id: int, current_user: CurrentUser, request: Request,
    ):
        """Get all messages for a conversation."""
        p = request.app.state.db_pool
        if p is None:
            raise HTTPException(500, "Database not available")

        # Verify ownership
        conv = await p.fetchrow(
            "SELECT id FROM conversations WHERE id = $1 AND user_id = $2",
            conv_id, current_user["user_id"],
        )
        if not conv:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")

        rows = await p.fetch(
            """SELECT id, role, content, files, model, duration_sec, tokens_used, created_at
               FROM messages WHERE conversation_id = $1
               ORDER BY created_at ASC""",
            conv_id,
        )
        return [_message_to_dict(r) for r in rows]

    # ═══════════════════════════════════════════════════════════
    # FILE UPLOAD
    # ═══════════════════════════════════════════════════════════

    @app.post("/api/files/upload")
    async def upload_file(
        file: UploadFile,
        current_user: CurrentUser,
        request: Request,
    ):
        """Upload a file. Returns path, filename, size."""
        max_size = 100 * 1024 * 1024  # 100 MB
        content = await file.read()
        if len(content) > max_size:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Файл слишком большой (макс. 100 МБ)")

        safe_name = Path(file.filename or "upload").name
        unique_name = f"{uuid.uuid4().hex}_{safe_name}"
        dest = UPLOAD_DIR / unique_name
        dest.write_bytes(content)
        dest.chmod(0o600)

        # Store in DB if pool available
        p = request.app.state.db_pool
        if p:
            await p.execute(
                """INSERT INTO web_files (user_id, filename, path, mime_type, size_bytes)
                   VALUES ($1, $2, $3, $4, $5)""",
                current_user["user_id"], safe_name, str(dest),
                file.content_type, len(content),
            )

        return {
            "path": str(dest),
            "filename": safe_name,
            "size": len(content),
        }

    # ═══════════════════════════════════════════════════════════
    # FILE SERVE (generated images, documents)
    # ═══════════════════════════════════════════════════════════

    @app.get("/api/files/serve/{filename}")
    async def serve_file(filename: str):
        """Serve an uploaded or generated file."""
        safe = Path(filename).name  # prevent path traversal
        fpath = UPLOAD_DIR / safe
        if not fpath.exists():
            raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found")
        return FileResponse(fpath, filename=safe)

    # ═══════════════════════════════════════════════════════════
    # HEALTH
    # ═══════════════════════════════════════════════════════════

    @app.get("/mobile")
    async def mobile_ui():
        """Serve the Neura mobile HTML interface."""
        mobile_path = Path("/opt/neura-v2/homes/maxim_belousov/neura-mobile.html")
        if not mobile_path.exists():
            raise HTTPException(404, "Mobile UI not found")
        return FileResponse(mobile_path, media_type="text/html")

    @app.get("/api/health")
    async def health_check(request: Request):
        """Health check endpoint for monitoring and load balancers."""
        caps = request.app.state.capsules
        return {
            "status": "ok",
            "version": "2.0.0",
            "capsules": len(caps) if caps else 0,
        }

    # ═══════════════════════════════════════════════════════════
    # METRICS
    # ═══════════════════════════════════════════════════════════

    @app.get("/api/metrics")
    async def get_metrics(current_user: CurrentUser, request: Request):
        """Return agent metrics for the sidebar AgentPanel."""
        capsules = request.app.state.capsules
        engine = request.app.state.engine
        capsule_id = current_user.get("capsule_id")

        # Collect basic info
        capsule_info = None
        if capsule_id and capsule_id in capsules:
            cap = capsules[capsule_id]
            capsule_info = {
                "id": capsule_id,
                "name": cap.config.name,
                "model": getattr(cap.config, "model", "sonnet"),
            }

        # Collect real metrics from DB
        requests_total = 0
        errors_total = 0
        avg_duration = 0.0
        skills_list: list[str] = []

        db_pool = request.app.state.db_pool
        if db_pool and capsule_id:
            try:
                row = await db_pool.fetchrow(
                    """SELECT
                        COUNT(*) FILTER (WHERE role = 'assistant') AS req_total,
                        COUNT(*) FILTER (WHERE role = 'assistant' AND content LIKE '%%ошибк%%') AS err_total,
                        COALESCE(AVG(duration_sec) FILTER (WHERE role = 'assistant' AND duration_sec > 0), 0) AS avg_dur
                    FROM messages m
                    JOIN conversations c ON c.id = m.conversation_id
                    WHERE c.user_id = (SELECT id FROM users WHERE capsule_id = $1 LIMIT 1)""",
                    capsule_id,
                )
                if row:
                    requests_total = row["req_total"] or 0
                    errors_total = row["err_total"] or 0
                    avg_duration = float(row["avg_dur"] or 0)
            except Exception:
                pass

        if capsule_id and capsule_id in capsules:
            cap = capsules[capsule_id]
            skills_list = list(getattr(cap.config, "skills", []) or [])

        # Calculate uptime
        import psutil
        try:
            proc = psutil.Process()
            uptime = time.monotonic() - proc.create_time() + time.time() - time.monotonic()
            uptime_sec = round(time.time() - proc.create_time())
        except Exception:
            uptime_sec = 0

        return {
            "status": "online",
            "capsule": capsule_info,
            "uptime_sec": uptime_sec,
            "requests_total": requests_total,
            "errors_total": errors_total,
            "avg_duration_sec": round(avg_duration, 1),
            "skills": skills_list,
        }

    # ═══════════════════════════════════════════════════════════
    # HEARTBEAT — CRUD for per-capsule reminders & tasks
    # ═══════════════════════════════════════════════════════════

    class HeartbeatCreate(BaseModel):
        name: str
        message: str
        schedule: str = "daily 10:00"
        type: str = "reminder"  # "reminder" | "task"
        enabled: bool = True
        display_name: Optional[str] = None

    class HeartbeatUpdate(BaseModel):
        name: Optional[str] = None
        message: Optional[str] = None
        schedule: Optional[str] = None
        type: Optional[str] = None
        enabled: Optional[bool] = None
        display_name: Optional[str] = None

    def _heartbeat_yaml_path(capsule_id: str) -> Path:
        return Path(f"/opt/neura-v2/homes/{capsule_id}/heartbeat.yaml")

    def _load_heartbeat_yaml(capsule_id: str) -> list[dict]:
        p = _heartbeat_yaml_path(capsule_id)
        if not p.exists():
            return []
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save_heartbeat_yaml(capsule_id: str, items: list[dict]) -> None:
        p = _heartbeat_yaml_path(capsule_id)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            yaml.dump(items, allow_unicode=True, default_flow_style=False),
            encoding="utf-8",
        )

    @app.get("/api/heartbeat")
    async def list_heartbeats(current_user: CurrentUser):
        """List all heartbeat tasks for the current user's capsule."""
        capsule_id = current_user.get("capsule_id")
        if not capsule_id:
            return []
        items = _load_heartbeat_yaml(capsule_id)
        return [
            {
                "name": it.get("name", ""),
                "display_name": it.get("display_name") or None,
                "message": it.get("message", ""),
                "schedule": it.get("schedule", "daily 10:00"),
                "type": it.get("type", "reminder"),
                "enabled": it.get("enabled", True),
            }
            for it in items
            if it.get("name")
        ]

    @app.post("/api/heartbeat", status_code=201)
    async def create_heartbeat(body: HeartbeatCreate, current_user: CurrentUser):
        """Create a new heartbeat task."""
        capsule_id = current_user.get("capsule_id")
        if not capsule_id:
            raise HTTPException(400, "No capsule linked to this account")
        items = _load_heartbeat_yaml(capsule_id)
        # Unique name check
        if any(it.get("name") == body.name for it in items):
            raise HTTPException(409, f"Heartbeat '{body.name}' already exists")
        new_item: dict = {
            "name": body.name,
            "message": body.message,
            "schedule": body.schedule,
            "type": body.type,
            "enabled": body.enabled,
        }
        if body.display_name:
            new_item["display_name"] = body.display_name
        items.append(new_item)
        _save_heartbeat_yaml(capsule_id, items)
        return {**new_item, "display_name": new_item.get("display_name") or None}

    @app.patch("/api/heartbeat/{task_name}")
    async def update_heartbeat(task_name: str, body: HeartbeatUpdate, current_user: CurrentUser):
        """Update an existing heartbeat task by name."""
        capsule_id = current_user.get("capsule_id")
        if not capsule_id:
            raise HTTPException(400, "No capsule linked")
        items = _load_heartbeat_yaml(capsule_id)
        found = None
        for it in items:
            if it.get("name") == task_name:
                found = it
                break
        if not found:
            raise HTTPException(404, f"Heartbeat '{task_name}' not found")
        update_data = body.model_dump(exclude_none=True)
        if "name" in update_data and update_data["name"] != task_name:
            # Rename — check uniqueness
            if any(it.get("name") == update_data["name"] for it in items):
                raise HTTPException(409, f"Name '{update_data['name']}' already taken")
        found.update(update_data)
        _save_heartbeat_yaml(capsule_id, items)
        return {
            "name": found.get("name", ""),
            "display_name": found.get("display_name") or None,
            "message": found.get("message", ""),
            "schedule": found.get("schedule", ""),
            "type": found.get("type", "reminder"),
            "enabled": found.get("enabled", True),
        }

    @app.delete("/api/heartbeat/{task_name}", status_code=204)
    async def delete_heartbeat(task_name: str, current_user: CurrentUser):
        """Delete a heartbeat task by name."""
        capsule_id = current_user.get("capsule_id")
        if not capsule_id:
            raise HTTPException(400, "No capsule linked")
        items = _load_heartbeat_yaml(capsule_id)
        new_items = [it for it in items if it.get("name") != task_name]
        if len(new_items) == len(items):
            raise HTTPException(404, f"Heartbeat '{task_name}' not found")
        _save_heartbeat_yaml(capsule_id, new_items)

    # ═══════════════════════════════════════════════════════════
    # DIARY
    # ═══════════════════════════════════════════════════════════

    @app.get("/api/diary")
    async def list_diary(
        current_user: CurrentUser, request: Request,
        date: str | None = None, limit: int = 50, offset: int = 0,
    ):
        """List diary entries for the current user's capsule.

        If date is provided (YYYY-MM-DD), return entries for that date.
        Otherwise return most recent entries.
        """
        p = request.app.state.db_pool
        if p is None:
            raise HTTPException(500, "Database not available")

        capsule_id = current_user.get("capsule_id")
        if not capsule_id:
            raise HTTPException(400, "No capsule linked")

        if date:
            try:
                from datetime import date as date_type
                filter_date = date_type.fromisoformat(date)
            except ValueError:
                raise HTTPException(400, "Invalid date format, expected YYYY-MM-DD")
            rows = await p.fetch(
                """SELECT id, date, time, source, user_message, bot_response,
                          model, duration_sec, tools_used, created_at
                   FROM diary
                   WHERE capsule_id = $1 AND date = $2
                   ORDER BY time DESC
                   LIMIT $3 OFFSET $4""",
                capsule_id, filter_date, limit, offset,
            )
        else:
            rows = await p.fetch(
                """SELECT id, date, time, source, user_message, bot_response,
                          model, duration_sec, tools_used, created_at
                   FROM diary
                   WHERE capsule_id = $1
                   ORDER BY date DESC, time DESC
                   LIMIT $2 OFFSET $3""",
                capsule_id, limit, offset,
            )

        return [
            {
                "id": r["id"],
                "date": r["date"].isoformat() if hasattr(r["date"], "isoformat") else str(r["date"]),
                "time": r["time"].isoformat() if hasattr(r["time"], "isoformat") else str(r["time"]),
                "source": r["source"],
                "user_message": r["user_message"],
                "bot_response": r["bot_response"],
                "model": r["model"],
                "duration_sec": r["duration_sec"],
                "tools_used": r["tools_used"] or [],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
            for r in rows
        ]

    @app.get("/api/diary/search")
    async def search_diary(
        current_user: CurrentUser, request: Request,
        q: str = "", limit: int = 20,
    ):
        """Search diary entries by keyword in user_message and bot_response."""
        p = request.app.state.db_pool
        if p is None:
            raise HTTPException(500, "Database not available")

        capsule_id = current_user.get("capsule_id")
        if not capsule_id:
            raise HTTPException(400, "No capsule linked")

        if not q.strip():
            raise HTTPException(400, "Search query 'q' is required")

        rows = await p.fetch(
            """SELECT id, date, time, source, user_message, bot_response,
                      model, duration_sec, tools_used, created_at
               FROM diary
               WHERE capsule_id = $1
                 AND (user_message ILIKE $2 OR bot_response ILIKE $2)
               ORDER BY date DESC, time DESC
               LIMIT $3""",
            capsule_id, f"%{q}%", limit,
        )

        return [
            {
                "id": r["id"],
                "date": r["date"].isoformat() if hasattr(r["date"], "isoformat") else str(r["date"]),
                "time": r["time"].isoformat() if hasattr(r["time"], "isoformat") else str(r["time"]),
                "source": r["source"],
                "user_message": r["user_message"],
                "bot_response": r["bot_response"],
                "model": r["model"],
                "duration_sec": r["duration_sec"],
                "tools_used": r["tools_used"] or [],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
            for r in rows
        ]

    # ═══════════════════════════════════════════════════════════
    # FULL-TEXT SEARCH (messages)
    # ═══════════════════════════════════════════════════════════

    @app.get("/api/search")
    async def search_messages(
        current_user: CurrentUser, request: Request,
        q: str = "", limit: int = 20,
    ):
        """Search across message content in user's conversations."""
        p = request.app.state.db_pool
        if p is None:
            raise HTTPException(500, "Database not available")

        if not q.strip():
            raise HTTPException(400, "Search query 'q' is required")

        rows = await p.fetch(
            """SELECT m.id AS message_id, m.conversation_id, c.title,
                      m.role, LEFT(m.content, 200) AS preview, m.created_at
               FROM messages m
               JOIN conversations c ON c.id = m.conversation_id
               WHERE c.user_id = $1 AND m.content ILIKE $2
               ORDER BY m.created_at DESC
               LIMIT $3""",
            current_user["user_id"], f"%{q}%", limit,
        )

        return [
            {
                "message_id": r["message_id"],
                "conversation_id": r["conversation_id"],
                "conversation_title": r["title"],
                "role": r["role"],
                "content_preview": r["preview"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
            for r in rows
        ]

    # ═══════════════════════════════════════════════════════════
    # MEMORY & LEARNINGS
    # ═══════════════════════════════════════════════════════════

    @app.get("/api/memory")
    async def list_memory(
        current_user: CurrentUser, request: Request,
        limit: int = 50, offset: int = 0,
    ):
        """List long-term memory entries for the user's capsule."""
        p = request.app.state.db_pool
        if p is None:
            raise HTTPException(500, "Database not available")

        capsule_id = current_user.get("capsule_id")
        if not capsule_id:
            raise HTTPException(400, "No capsule linked")

        rows = await p.fetch(
            """SELECT id, content, source, score, created_at
               FROM memory
               WHERE capsule_id = $1
               ORDER BY created_at DESC
               LIMIT $2 OFFSET $3""",
            capsule_id, limit, offset,
        )

        return [
            {
                "id": r["id"],
                "content": r["content"],
                "source": r.get("source", "auto"),
                "score": r.get("score"),
                "created_at": r["created_at"].isoformat() if r.get("created_at") else None,
            }
            for r in rows
        ]

    @app.get("/api/learnings")
    async def list_learnings(
        current_user: CurrentUser, request: Request,
        limit: int = 50,
    ):
        """List learnings and corrections for the user's capsule."""
        p = request.app.state.db_pool
        if p is None:
            raise HTTPException(500, "Database not available")

        capsule_id = current_user.get("capsule_id")
        if not capsule_id:
            raise HTTPException(400, "No capsule linked")

        rows = await p.fetch(
            """SELECT id, content, type, created_at
               FROM learnings
               WHERE capsule_id = $1
               ORDER BY created_at DESC
               LIMIT $2""",
            capsule_id, limit,
        )

        return [
            {
                "id": r["id"],
                "content": r["content"],
                "type": r.get("type", "learning"),
                "created_at": r["created_at"].isoformat() if r.get("created_at") else None,
            }
            for r in rows
        ]

    @app.delete("/api/memory/{memory_id}", status_code=204)
    async def delete_memory(
        memory_id: int, current_user: CurrentUser, request: Request,
    ):
        """Delete a memory entry (must belong to user's capsule)."""
        p = request.app.state.db_pool
        if p is None:
            raise HTTPException(500, "Database not available")

        capsule_id = current_user.get("capsule_id")
        if not capsule_id:
            raise HTTPException(400, "No capsule linked")

        result = await p.execute(
            "DELETE FROM memory WHERE id = $1 AND capsule_id = $2",
            memory_id, capsule_id,
        )
        if result == "DELETE 0":
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Memory entry not found")

    # ═══════════════════════════════════════════════════════════
    # WEBSOCKET — STREAMING CHAT
    # ═══════════════════════════════════════════════════════════

    async def _run_stream(
        session: StreamSession,
        engine_obj, capsule, capsule_id: str,
        user_text: str, engine_cfg, requested_model: str | None,
        db_pool_ref, memory_ref, conv_id: int,
        files: list[str] | None = None,
    ):
        """Background stream task — runs independently of WebSocket.

        Session resume: if we have an active Claude CLI session_id for this
        conversation, we --resume it instead of rebuilding full context.
        """
        import json as _json_mod
        start_time = time.monotonic()
        accumulated = ""
        tools_used: list[str] = []
        model_name = engine_cfg.model or "sonnet"
        result_session_id = ""
        had_error = False

        # Build file context: append file paths so Claude can Read them
        file_context = ""
        if files:
            file_lines = []
            for fpath in files:
                p = Path(fpath)
                if not p.exists():
                    continue
                try:
                    if build_doc_context is not None:
                        line = build_doc_context(fpath)
                    else:
                        raise RuntimeError("document_processor not available")
                    file_lines.append(line)
                except Exception:
                    # Fallback to simple context
                    ext = p.suffix.lower()
                    size_mb = p.stat().st_size / (1024 * 1024)
                    size_str = f"{size_mb:.1f} МБ" if size_mb >= 1 else f"{p.stat().st_size / 1024:.0f} КБ"
                    file_lines.append(f"[Файл: {p.name}, {size_str}] — прочитай через Read tool: {fpath}")
            if file_lines:
                file_context = "\n\nПользователь прикрепил файлы:\n" + "\n".join(file_lines)

        try:
            # Check for existing Claude CLI session for this conversation
            existing_session = _claude_sessions.get(conv_id)

            if existing_session:
                # RESUME: send user message + vector context for relevant knowledge
                vector_ctx = ""
                try:
                    vector_ctx = memory_ref._vector_search(capsule, user_text)
                except Exception as e:
                    logger.debug(f"[web] Resume vector search failed: {e}")
                if vector_ctx:
                    prompt = user_text + file_context + "\n\n" + vector_ctx
                else:
                    prompt = user_text + file_context
                engine_cfg.resume_session_id = existing_session
                logger.info(f"[web] Resuming session {existing_session[:12]}… for conv_id={conv_id} (vector: {'yes' if vector_ctx else 'no'})")
            else:
                # NEW SESSION: build full context
                from neura.core.context import ContextBuilder
                parts = await memory_ref.build_context_parts(capsule, user_text)

                # Load conversation history (THIS chat only, last 20 messages)
                if db_pool_ref and conv_id:
                    try:
                        history_rows = await db_pool_ref.fetch(
                            """SELECT role, content FROM messages
                               WHERE conversation_id = $1
                               ORDER BY created_at ASC
                               LIMIT 20""",
                            conv_id,
                        )
                        if history_rows:
                            history_lines = []
                            for row in history_rows:
                                prefix = "Пользователь" if row["role"] == "user" else "Агент"
                                content = (row["content"] or "")[:500]
                                history_lines.append(f"{prefix}: {content}")
                            parts.conversation_history = "\n".join(history_lines)
                    except Exception as e:
                        logger.warning("Failed to load conversation history: %s", e)

                # Cross-project context: recent messages from OTHER conversations
                if db_pool_ref and conv_id:
                    try:
                        cross_rows = await db_pool_ref.fetch(
                            """SELECT p.name AS project_name, c.title AS chat_title,
                                      m.role, m.content, m.created_at
                               FROM messages m
                               JOIN conversations c ON c.id = m.conversation_id
                               LEFT JOIN projects p ON p.id = c.project_id
                               WHERE c.user_id = $1
                                 AND c.id != $2
                                 AND m.created_at > NOW() - INTERVAL '24 hours'
                               ORDER BY m.created_at DESC
                               LIMIT 10""",
                            session.user_id, conv_id,
                        )
                        if cross_rows:
                            by_project: dict[str, list[str]] = {}
                            for row in reversed(cross_rows):  # chronological
                                proj = row["project_name"] or "Без проекта"
                                chat = row["chat_title"] or "Чат"
                                key = f"{proj} / {chat}"
                                if key not in by_project:
                                    by_project[key] = []
                                prefix = "Пользователь" if row["role"] == "user" else "Агент"
                                by_project[key].append(f"{prefix}: {(row['content'] or '')[:200]}")
                            lines: list[str] = []
                            for key, msgs in by_project.items():
                                lines.append(f"[{key}]")
                                lines.extend(msgs[-4:])  # last 4 per chat
                            parts.cross_project_context = "\n".join(lines)
                    except Exception as e:
                        logger.warning("Failed to load cross-project context: %s", e)

                builder = ContextBuilder(capsule)
                prompt = builder.build(user_text + file_context, parts, is_first_message=True)

            # Link understanding: enrich prompt with URL metadata
            from neura.core.link_understanding import enrich_with_links, extract_urls
            if extract_urls(user_text):
                try:
                    import redis.asyncio as _redis_mod
                    _redis_tmp = _redis_mod.from_url("redis://localhost:6379")
                    link_ctx = await enrich_with_links(user_text, _redis_tmp)
                    await _redis_tmp.aclose()
                    if link_ctx:
                        prompt += link_ctx
                        logger.info(f"[web] Link context added: {len(link_ctx)} chars")
                except Exception as e:
                    logger.warning(f"[web] Link understanding failed: {e}")

            # Retry loop with exponential backoff (max 3 attempts)
            import random
            max_retries = 3
            for attempt in range(max_retries):
                had_error = False
                accumulated = ""

                async for chunk in engine_obj.stream(prompt, engine_cfg):
                    if chunk.session_id and not result_session_id:
                        result_session_id = chunk.session_id
                    if chunk.type == "text":
                        accumulated += chunk.text
                        await session.broadcast({"type": "text", "content": accumulated})
                    elif chunk.type == "tool_start":
                        tools_used.append(chunk.tool)
                        await session.broadcast({"type": "tool", "content": chunk.text})
                    elif chunk.type == "result":
                        accumulated = chunk.text or accumulated
                        if chunk.session_id:
                            result_session_id = chunk.session_id
                    elif chunk.type == "error":
                        had_error = True
                        error_text = chunk.text or ""
                        # Don't broadcast retryable errors to user yet
                        if attempt < max_retries - 1 and _is_retryable_error(error_text):
                            break
                        await session.broadcast({"type": "error", "content": chunk.text})

                # If success or non-retryable error — stop
                if not had_error or accumulated:
                    break
                if attempt < max_retries - 1 and had_error:
                    delay = (2 ** attempt) + random.uniform(0, 1)  # 1-2s, 2-3s, 4-5s
                    logger.warning(f"[web] Retry {attempt+1}/{max_retries} for conv_id={conv_id}, waiting {delay:.1f}s")
                    await session.broadcast({"type": "status", "content": f"Повторная попытка ({attempt+2}/{max_retries})..."})
                    await asyncio.sleep(delay)

            # Save or invalidate Claude CLI session
            if had_error and existing_session:
                _claude_sessions.pop(conv_id, None)
                logger.info(f"[web] Session invalidated for conv_id={conv_id}")
            elif result_session_id:
                _claude_sessions[conv_id] = result_session_id
                logger.info(f"[web] Session saved: {result_session_id[:12]}… for conv_id={conv_id}")
                # Evict oldest if too many
                if len(_claude_sessions) > _CLAUDE_SESSIONS_MAX:
                    oldest_key = next(iter(_claude_sessions))
                    _claude_sessions.pop(oldest_key, None)

        except asyncio.CancelledError:
            logger.info("Stream cancelled by user for conv_id=%d", conv_id)
        except Exception as exc:
            logger.error("Stream error conv_id=%d: %s", conv_id, exc, exc_info=True)
            await session.broadcast({"type": "error", "content": "Ошибка обработки. Попробуйте снова."})

        duration = time.monotonic() - start_time

        # Process [FILE:] markers — replace with web-accessible URLs (only once, for final result)
        if accumulated and _FILE_MARKER_RE.search(accumulated):
            accumulated = _process_file_markers(accumulated)

        # Save results to DB (regardless of WS connection)
        try:
            if db_pool_ref and user_text:
                msg_count = await db_pool_ref.fetchval(
                    "SELECT COUNT(*) FROM messages WHERE conversation_id = $1", conv_id,
                )
                if msg_count <= 2:
                    auto_title = user_text[:60].strip()
                    if auto_title:
                        await db_pool_ref.execute(
                            "UPDATE conversations SET title = $1 WHERE id = $2",
                            auto_title, conv_id,
                        )

            if db_pool_ref and requested_model:
                await db_pool_ref.execute(
                    "UPDATE conversations SET model = $1 WHERE id = $2",
                    requested_model, conv_id,
                )

            if db_pool_ref and accumulated:
                await db_pool_ref.execute(
                    """INSERT INTO messages (conversation_id, role, content, model, duration_sec)
                       VALUES ($1, 'assistant', $2, $3, $4)""",
                    conv_id, accumulated, model_name, duration,
                )

            if memory_ref and capsule and accumulated:
                from neura.core.memory import DiaryEntry
                now = datetime.now(timezone.utc)
                entry = DiaryEntry(
                    capsule_id=capsule_id or "",
                    date=now.strftime("%Y-%m-%d"),
                    time=now.strftime("%H:%M:%S"),
                    user_message=user_text[:2000],
                    bot_response=accumulated[:2000],
                    model=model_name,
                    tools_used=tools_used,
                    source="web",
                )
                await memory_ref.add_diary(entry)
        except Exception as e:
            logger.error(f"Stream post-save error: {e}")

        final = {
            "type": "done",
            "content": accumulated,
            "model": model_name,
            "duration": round(duration, 2),
        }
        session.final_chunk = final
        session.done = True
        session.done_at = time.monotonic()
        await session.broadcast(final)

    WS_PING_INTERVAL = 30  # seconds between pings
    WS_PING_TIMEOUT = 10   # seconds to wait for pong

    @app.websocket("/ws/chat/{conv_id}")
    async def ws_chat(websocket: WebSocket, conv_id: int):
        """WebSocket streaming chat endpoint.

        Auth: token in query param ?token=<JWT>
        Protocol:
          Client → {"text": "...", "files": [...]}
          Client → {"type": "cancel"}
          Client → {"type": "pong"}
          Server ← {"type": "status", "content": "..."}
          Server ← {"type": "text", "content": "partial text"}
          Server ← {"type": "tool", "content": "🔧 Reading..."}
          Server ← {"type": "done", "content": "...", "model": "sonnet", "duration": 3.2}
          Server ← {"type": "error", "content": "..."}
          Server ← {"type": "busy", "content": "...", "active_chats": [...]}
          Server ← {"type": "ping"}
        """
        token = websocket.query_params.get("token", "")
        try:
            from neura.transport.auth import decode_token
            payload = decode_token(token)
            user_id = int(payload["sub"])
            capsule_id = payload.get("capsule_id")
        except Exception:
            await websocket.close(code=4001, reason="Unauthorized")
            return

        await websocket.accept()

        # Heartbeat: track last pong time for this connection
        last_pong = time.monotonic()
        ping_task: asyncio.Task | None = None

        async def _ping_loop():
            """Send periodic pings, close if no pong received."""
            nonlocal last_pong
            missed = 0
            while True:
                await asyncio.sleep(WS_PING_INTERVAL)
                try:
                    await websocket.send_json({"type": "ping"})
                    # Check if last pong was recent enough
                    if time.monotonic() - last_pong > WS_PING_INTERVAL + WS_PING_TIMEOUT:
                        missed += 1
                        logger.warning(
                            "WS heartbeat: %d missed pongs (conv=%d, user=%d)",
                            missed, conv_id, user_id,
                        )
                        if missed >= 2:
                            logger.info("WS heartbeat: closing stale connection (conv=%d)", conv_id)
                            await websocket.close(code=4002, reason="Heartbeat timeout")
                            return
                    else:
                        missed = 0
                except Exception:
                    return  # WebSocket already closed

        ping_task = asyncio.create_task(_ping_loop())

        db_pool = websocket.app.state.db_pool
        engine_obj = websocket.app.state.engine
        capsules_map = websocket.app.state.capsules

        # Verify conversation ownership
        if db_pool:
            conv = await db_pool.fetchrow(
                "SELECT id FROM conversations WHERE id = $1 AND user_id = $2",
                conv_id, user_id,
            )
            if not conv:
                await websocket.send_json({"type": "error", "content": "Conversation not found"})
                await websocket.close(code=4001, reason="Conversation not found")
                return

        # Subscribe to existing session (reconnect scenario)
        existing = stream_mgr.get_session(user_id, conv_id)
        if existing and not existing.done:
            existing.subscribers.add(websocket)
            # Replay accumulated chunks
            for chunk in existing.chunks:
                try:
                    await websocket.send_json(chunk)
                except Exception:
                    break

        try:
            while True:
                raw = await websocket.receive_json()

                # Handle pong (heartbeat response)
                if raw.get("type") == "pong":
                    last_pong = time.monotonic()
                    continue

                # Handle cancel
                if raw.get("type") == "cancel":
                    session = stream_mgr.get_session(user_id, conv_id)
                    if session and not session.done:
                        session.cancel()
                    continue

                user_text = raw.get("text", "").strip()
                files = raw.get("files", [])
                requested_model = raw.get("model", None)

                if not user_text and not files:
                    continue

                # Rate limit check (per-capsule, per-minute)
                rl_key = f"user:{user_id}"
                allowed, wait_sec = _rate_limiter.check(rl_key)
                if not allowed:
                    await websocket.send_json({
                        "type": "error",
                        "content": f"Слишком много запросов. Подождите {wait_sec:.0f} сек."
                    })
                    continue

                # Check concurrent stream limit
                active = stream_mgr.active_count(user_id)
                # Don't count this conv if it already has a done/no session
                current_session = stream_mgr.get_session(user_id, conv_id)
                if current_session and not current_session.done:
                    active -= 1  # this conv already counted

                if active >= MAX_CONCURRENT_STREAMS:
                    active_chats = [
                        s.conv_id for s in stream_mgr.active_sessions(user_id)
                        if s.conv_id != conv_id
                    ]
                    await websocket.send_json({
                        "type": "busy",
                        "content": f"Уже работают {active} агента в других чатах. Дождитесь завершения или остановите их.",
                        "active_chats": active_chats,
                    })
                    continue

                # Voice transcription — always transcribe voice files
                VOICE_EXTS = {".webm", ".ogg", ".wav", ".mp3", ".m4a", ".oga"}
                voice_files = [f for f in files if any(f.lower().endswith(ext) for ext in VOICE_EXTS)]
                if voice_files:
                    await websocket.send_json({"type": "status", "content": "Транскрибирую голос..."})
                    try:
                        from neura.transport.protocol import transcribe_voice
                        transcript = await transcribe_voice(voice_files[0])
                        if transcript and not transcript.startswith("\u274c"):
                            if user_text:
                                user_text = f"{user_text}\n\n[Голосовое сообщение]: {transcript}"
                            else:
                                user_text = transcript
                            files = [f for f in files if f not in voice_files]
                            logger.info(f"Voice transcribed: {len(transcript)} chars")
                        else:
                            logger.warning(f"Voice transcription empty or failed: {transcript}")
                    except Exception as e:
                        logger.error(f"Voice transcription error: {e}")
                        await websocket.send_json({"type": "error", "content": "Не удалось распознать голос"})
                        continue

                # Resolve capsule
                capsule = None
                if capsule_id and capsules_map:
                    capsule = capsules_map.get(capsule_id)

                # Save user message
                if db_pool:
                    await db_pool.execute(
                        """INSERT INTO messages (conversation_id, role, content, files)
                           VALUES ($1, 'user', $2, $3::jsonb)""",
                        conv_id, user_text, __import__("json").dumps(files),
                    )

                if engine_obj is None or capsule is None:
                    await websocket.send_json({
                        "type": "error",
                        "content": "Агент не настроен. Обратитесь к администратору.",
                    })
                    continue

                # Build engine config
                engine_cfg = capsule.get_engine_config()
                if requested_model:
                    MODEL_MAP = {
                        "sonnet-4-6": "sonnet",
                        "opus-4-6": "opus",
                        "haiku-4-5": "haiku",
                    }
                    mapped = MODEL_MAP.get(requested_model, requested_model)
                    engine_cfg = EngineConfig(
                        model=mapped,
                        effort=engine_cfg.effort,
                        allowed_tools=engine_cfg.allowed_tools,
                        home_dir=engine_cfg.home_dir,
                        append_system_prompt=engine_cfg.append_system_prompt,
                    )

                # Create background stream session
                session = stream_mgr.create_session(user_id, conv_id)
                session.subscribers.add(websocket)

                await session.broadcast({"type": "status", "content": "Думаю..."})

                session.task = asyncio.create_task(
                    _run_stream(
                        session, engine_obj, capsule, capsule_id,
                        user_text, engine_cfg, requested_model,
                        db_pool, websocket.app.state.memory, conv_id,
                        files,
                    )
                )

        except WebSocketDisconnect:
            logger.info("WebSocket disconnected: conv_id=%d user_id=%d (stream continues in background)", conv_id, user_id)
            # Remove from subscribers but DON'T cancel the stream
            session = stream_mgr.get_session(user_id, conv_id)
            if session:
                session.subscribers.discard(websocket)
        except Exception as exc:
            logger.error("WebSocket error: %s", exc, exc_info=True)
            try:
                await websocket.send_json({"type": "error", "content": str(exc)})
            except Exception:
                pass
        finally:
            # Stop heartbeat ping task
            if ping_task and not ping_task.done():
                ping_task.cancel()
                try:
                    await ping_task
                except asyncio.CancelledError:
                    pass

    # ── Helpers ──────────────────────────────────────────────────

    def _user_to_dict(row) -> dict:
        return {
            "id": row["id"],
            "email": row["email"],
            "name": row["name"],
            "capsule_id": row["capsule_id"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }

    def _project_to_dict(row) -> dict:
        import json as _json
        links_raw = row.get("links", "[]")
        if isinstance(links_raw, str):
            try:
                links_raw = _json.loads(links_raw)
            except Exception:
                links_raw = []
        return {
            "id": row["id"],
            "name": row["name"],
            "description": row.get("description", ""),
            "instructions": row.get("instructions", ""),
            "links": links_raw or [],
            "pinned": row["pinned"],
            "icon": row["icon"],
            "sort_order": row["sort_order"],
            "chats_count": row.get("chats_count", 0),
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }

    def _conversation_to_dict(row) -> dict:
        lm = row.get("last_message")
        return {
            "id": row["id"],
            "title": row["title"],
            "project_id": row["project_id"],
            "pinned": row["pinned"],
            "model": row.get("model"),
            "last_message": lm[:100] if lm else None,
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        }

    def _message_to_dict(row) -> dict:
        import json
        files = row["files"]
        if isinstance(files, str):
            try:
                files = json.loads(files)
            except Exception:
                files = []
        # Strip full paths — expose only web-accessible URLs
        safe_files = []
        for f in (files or []):
            if isinstance(f, str):
                safe_files.append(f"/api/files/serve/{Path(f).name}")
            elif isinstance(f, dict) and "path" in f:
                f = dict(f)
                f["path"] = f"/api/files/serve/{Path(f['path']).name}"
                safe_files.append(f)
            else:
                safe_files.append(f)
        return {
            "id": row["id"],
            "role": row["role"],
            "content": row["content"],
            "files": safe_files,
            "model": row["model"],
            "duration_sec": row["duration_sec"],
            "tokens_used": row["tokens_used"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }

    return app


# ── Standalone entry point ───────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    # Standalone mode: no DB, no engine — useful for smoke-testing routes
    app = create_web_app()
    uvicorn.run(app, host="0.0.0.0", port=8080, reload=False)
