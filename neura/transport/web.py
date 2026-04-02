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

import uvicorn
from fastapi import (
    Depends, FastAPI, HTTPException, Request, UploadFile, WebSocket,
    WebSocketDisconnect, status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, field_validator

from neura.transport.auth import (
    create_token, get_current_user, hash_password, verify_password,
)

logger = logging.getLogger(__name__)

# Upload directory
UPLOAD_DIR = Path(os.environ.get("NEURA_UPLOAD_DIR", "/tmp/neura-uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


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
    icon: str = "📁"


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    pinned: Optional[bool] = None
    icon: Optional[str] = None


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

    # CORS — allow frontend dev server
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
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
    # PROJECTS
    # ═══════════════════════════════════════════════════════════

    @app.get("/api/projects")
    async def list_projects(current_user: CurrentUser, request: Request):
        """List all projects for current user with conversation count."""
        p = request.app.state.db_pool
        if p is None:
            raise HTTPException(500, "Database not available")

        rows = await p.fetch(
            """SELECT pr.id, pr.name, pr.pinned, pr.icon, pr.sort_order, pr.created_at,
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
            """INSERT INTO projects (user_id, name, icon)
               VALUES ($1, $2, $3)
               RETURNING id, name, pinned, icon, sort_order, created_at""",
            current_user["user_id"], body.name, body.icon,
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

        if not updates:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "No fields to update")

        set_clause = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(updates))
        values = list(updates.values())
        row = await p.fetchrow(
            f"""UPDATE projects SET {set_clause}
                WHERE id = $1
                RETURNING id, name, pinned, icon, sort_order, created_at""",
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
            """SELECT c.id, c.title, c.project_id, c.pinned, c.created_at, c.updated_at,
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
               RETURNING id, title, project_id, pinned, created_at, updated_at""",
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
                RETURNING id, title, project_id, pinned, created_at, updated_at""",
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
        max_size = 10 * 1024 * 1024  # 10 MB
        content = await file.read()
        if len(content) > max_size:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File too large (max 10MB)")

        safe_name = Path(file.filename or "upload").name
        unique_name = f"{uuid.uuid4().hex}_{safe_name}"
        dest = UPLOAD_DIR / unique_name
        dest.write_bytes(content)

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
    # HEALTH
    # ═══════════════════════════════════════════════════════════

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

        return {
            "status": "online",
            "capsule": capsule_info,
            "uptime_sec": 0,  # filled by integration layer
        }

    # ═══════════════════════════════════════════════════════════
    # WEBSOCKET — STREAMING CHAT
    # ═══════════════════════════════════════════════════════════

    @app.websocket("/ws/chat/{conv_id}")
    async def ws_chat(websocket: WebSocket, conv_id: int):
        """WebSocket streaming chat endpoint.

        Auth: token in query param ?token=<JWT>
        Protocol:
          Client → {"text": "...", "files": [...]}
          Server ← {"type": "status", "content": "..."}
          Server ← {"type": "text", "content": "partial text"}
          Server ← {"type": "tool", "content": "🔧 Reading..."}
          Server ← {"type": "done", "content": "...", "model": "sonnet", "duration": 3.2}
          Server ← {"type": "error", "content": "..."}
        """
        # Extract token from query
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

        db_pool = websocket.app.state.db_pool
        engine = websocket.app.state.engine
        capsules = websocket.app.state.capsules

        # Verify conversation ownership
        if db_pool:
            conv = await db_pool.fetchrow(
                "SELECT id FROM conversations WHERE id = $1 AND user_id = $2",
                conv_id, user_id,
            )
            if not conv:
                await websocket.send_json({"type": "error", "content": "Conversation not found"})
                await websocket.close()
                return

        try:
            while True:
                raw = await websocket.receive_json()
                user_text = raw.get("text", "").strip()
                files = raw.get("files", [])

                if not user_text and not files:
                    continue

                # Resolve capsule
                capsule = None
                if capsule_id and capsules:
                    capsule = capsules.get(capsule_id)

                # Save user message
                if db_pool:
                    await db_pool.execute(
                        """INSERT INTO messages (conversation_id, role, content, files)
                           VALUES ($1, 'user', $2, $3::jsonb)""",
                        conv_id, user_text, __import__("json").dumps(files),
                    )

                # Status ping
                await websocket.send_json({"type": "status", "content": "⏳ Думаю..."})

                start_time = time.monotonic()
                accumulated = ""
                tools_used: list[str] = []

                if engine is None or capsule is None:
                    # No capsule/engine — send error, don't fake responses
                    await websocket.send_json({
                        "type": "error",
                        "content": "Агент не настроен. Обратитесь к администратору.",
                    })
                    continue
                else:
                    # Build context and stream
                    from neura.core.context import ContextBuilder
                    from neura.core.memory import MemoryStore
                    memory: MemoryStore = websocket.app.state.memory
                    from neura.transport.protocol import IncomingMessage, MessageType
                    incoming = IncomingMessage(
                        capsule_id=capsule_id or "",
                        user_id=user_id,
                        user_name="",
                        text=user_text,
                        message_type=MessageType.TEXT,
                    )
                    parts = await memory.build_context_parts(capsule, user_text)
                    builder = ContextBuilder(capsule)
                    prompt = builder.build(user_text, parts, is_first_message=True)

                    engine_cfg = capsule.get_engine_config()

                    async for chunk in engine.stream(prompt, engine_cfg):
                        if chunk.type == "text":
                            accumulated += chunk.text
                            await websocket.send_json({"type": "text", "content": accumulated})
                        elif chunk.type == "tool_start":
                            tools_used.append(chunk.tool)
                            await websocket.send_json({"type": "tool", "content": chunk.text})
                        elif chunk.type == "result":
                            accumulated = chunk.text or accumulated
                        elif chunk.type == "error":
                            await websocket.send_json({"type": "error", "content": chunk.text})

                duration = time.monotonic() - start_time

                # Auto-title: set first-message title
                if db_pool and user_text:
                    msg_count = await db_pool.fetchval(
                        "SELECT COUNT(*) FROM messages WHERE conversation_id = $1",
                        conv_id,
                    )
                    if msg_count <= 2:  # user + (about to add) assistant
                        auto_title = user_text[:60].strip()
                        if auto_title:
                            await db_pool.execute(
                                "UPDATE conversations SET title = $1 WHERE id = $2",
                                auto_title, conv_id,
                            )

                # Save assistant message
                if db_pool and accumulated:
                    model_name = getattr(capsule.config if capsule else None, "model", "sonnet") or "sonnet"
                    await db_pool.execute(
                        """INSERT INTO messages (conversation_id, role, content, model, duration_sec)
                           VALUES ($1, 'assistant', $2, $3, $4)""",
                        conv_id, accumulated, model_name, duration,
                    )

                await websocket.send_json({
                    "type": "done",
                    "content": accumulated,
                    "model": "sonnet",
                    "duration": round(duration, 2),
                })

        except WebSocketDisconnect:
            logger.info("WebSocket disconnected: conv_id=%d user_id=%d", conv_id, user_id)
        except Exception as exc:
            logger.error("WebSocket error: %s", exc, exc_info=True)
            try:
                await websocket.send_json({"type": "error", "content": str(exc)})
            except Exception:
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
        return {
            "id": row["id"],
            "name": row["name"],
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
        return {
            "id": row["id"],
            "role": row["role"],
            "content": row["content"],
            "files": files or [],
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
