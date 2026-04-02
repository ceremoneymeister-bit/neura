"""Tests for neura/transport/web.py — Neura Web API.

Uses httpx.AsyncClient with FastAPI test transport (no real DB).
All DB operations are mocked via asyncpg-compatible mock pool.
"""
import json
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from fastapi import FastAPI

from neura.transport.auth import create_token, hash_password, verify_password, decode_token
from neura.transport.web import create_web_app


# ── Fixtures ─────────────────────────────────────────────────────

def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _make_user_row(user_id=1, email="test@example.com", name="Test User",
                   capsule_id=None, password_hash=None):
    """Create a fake asyncpg-like record dict for a user."""
    row = {
        "id": user_id,
        "email": email,
        "name": name,
        "capsule_id": capsule_id,
        "password_hash": password_hash or hash_password("password123"),
        "created_at": datetime.now(timezone.utc),
    }
    # Support dict-like and attribute-like access (asyncpg Record style)
    m = MagicMock()
    m.__getitem__ = lambda self, k: row[k]
    m.get = lambda k, d=None: row.get(k, d)
    m.__contains__ = lambda self, k: k in row
    for k, v in row.items():
        setattr(m, k, v)
    return m


def _make_project_row(project_id=1, name="My Project", user_id=1):
    row = {
        "id": project_id,
        "name": name,
        "pinned": False,
        "icon": "📁",
        "sort_order": 0,
        "chats_count": 0,
        "created_at": datetime.now(timezone.utc),
    }
    m = MagicMock()
    m.__getitem__ = lambda self, k: row[k]
    m.get = lambda k, d=None: row.get(k, d)
    for k, v in row.items():
        setattr(m, k, v)
    return m


def _make_conv_row(conv_id=1, title="Test Chat", user_id=1, project_id=None):
    row = {
        "id": conv_id,
        "title": title,
        "project_id": project_id,
        "pinned": False,
        "last_message": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    m = MagicMock()
    m.__getitem__ = lambda self, k: row[k]
    m.get = lambda k, d=None: row.get(k, d)
    for k, v in row.items():
        setattr(m, k, v)
    return m


def _make_message_row(msg_id=1, conv_id=1, role="user", content="Hello"):
    row = {
        "id": msg_id,
        "role": role,
        "content": content,
        "files": "[]",
        "model": None,
        "duration_sec": None,
        "tokens_used": None,
        "created_at": datetime.now(timezone.utc),
    }
    m = MagicMock()
    m.__getitem__ = lambda self, k: row[k]
    m.get = lambda k, d=None: row.get(k, d)
    for k, v in row.items():
        setattr(m, k, v)
    return m


def _make_pool(user_row=None, project_row=None, conv_row=None, msg_row=None,
               no_user=False, no_project=False, no_conv=False):
    """Create a minimal asyncpg pool mock."""
    pool = MagicMock()

    default_user = user_row or _make_user_row()
    default_project = project_row or _make_project_row()
    default_conv = conv_row or _make_conv_row()
    default_msg = msg_row or _make_message_row()

    async def fetchrow(query, *args, **kwargs):
        q = query.strip().upper()
        if "FROM USERS" in q or "INTO USERS" in q:
            if no_user:
                return None
            # Duplicate check: "SELECT id FROM users WHERE email" — selects only id
            # Login query: "SELECT id, email, name, password_hash..." — selects multiple columns
            if "SELECTIDFROMUSERS" in q.replace(" ", "").replace("\n", ""):
                return None  # not existing by default for duplicate check
            return default_user
        if "FROM PROJECTS" in q or "INTO PROJECTS" in q or "UPDATE PROJECTS" in q:
            if no_project:
                return None
            return default_project
        if "FROM CONVERSATIONS" in q or "INTO CONVERSATIONS" in q or "UPDATE CONVERSATIONS" in q:
            if no_conv:
                return None
            return default_conv
        return None

    async def fetch(query, *args, **kwargs):
        q = query.strip().upper()
        if "FROM PROJECTS" in q:
            return [default_project] if not no_project else []
        if "FROM CONVERSATIONS" in q:
            return [default_conv] if not no_conv else []
        if "FROM MESSAGES" in q:
            return [default_msg]
        return []

    async def execute(query, *args, **kwargs):
        return "DELETE 1"

    async def fetchval(query, *args, **kwargs):
        return 1  # row count or ID

    pool.fetchrow = fetchrow
    pool.fetch = fetch
    pool.execute = execute
    pool.fetchval = fetchval
    return pool


@pytest.fixture
def app_with_pool():
    """FastAPI app with mock DB pool."""
    pool = _make_pool()
    app = create_web_app(db_pool=pool)
    return app, pool


@pytest.fixture
def auth_token():
    """Valid JWT for user_id=1."""
    return create_token(1, "test@example.com", None)


# ── Auth tests ───────────────────────────────────────────────────

class TestAuthHelpers:
    def test_hash_and_verify(self):
        h = hash_password("secret123")
        assert verify_password("secret123", h)
        assert not verify_password("wrong", h)

    def test_hash_different_salts(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2  # different salts

    def test_create_decode_token(self):
        token = create_token(42, "alice@test.com", "dmitry")
        payload = decode_token(token)
        assert payload["sub"] == "42"
        assert payload["email"] == "alice@test.com"
        assert payload["capsule_id"] == "dmitry"

    def test_decode_invalid_token(self):
        import jwt
        with pytest.raises(jwt.InvalidTokenError):
            decode_token("not.a.token")


class TestRegister:
    @pytest.mark.asyncio
    async def test_register_success(self):
        pool = _make_pool()
        app = create_web_app(db_pool=pool)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/auth/register", json={
                "email": "new@example.com",
                "password": "password123",
                "name": "New User",
            })
        assert resp.status_code == 201
        data = resp.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == "test@example.com"  # from mock

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self):
        """Returns 409 when email already exists."""
        # Override fetchrow to return existing user on duplicate check
        pool = MagicMock()
        existing = _make_user_row()

        async def fetchrow(query, *args, **kwargs):
            q = query.strip().upper()
            if "SELECT ID" in q and "EMAIL" in q:
                return existing  # already exists
            return _make_user_row()

        pool.fetchrow = fetchrow
        app = create_web_app(db_pool=pool)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/auth/register", json={
                "email": "exists@example.com",
                "password": "password123",
                "name": "Dup User",
            })
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_register_short_password(self):
        pool = _make_pool()
        app = create_web_app(db_pool=pool)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/auth/register", json={
                "email": "x@x.com",
                "password": "123",
                "name": "X",
            })
        assert resp.status_code == 422


class TestLogin:
    @pytest.mark.asyncio
    async def test_login_success(self):
        pw_hash = hash_password("password123")
        pool = _make_pool(user_row=_make_user_row(password_hash=pw_hash))
        app = create_web_app(db_pool=pool)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/auth/login", json={
                "email": "test@example.com",
                "password": "password123",
            })
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert "user" in data

    @pytest.mark.asyncio
    async def test_login_wrong_password(self):
        pw_hash = hash_password("correct_pass")
        pool = _make_pool(user_row=_make_user_row(password_hash=pw_hash))
        app = create_web_app(db_pool=pool)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/auth/login", json={
                "email": "test@example.com",
                "password": "wrong_pass",
            })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_login_unknown_email(self):
        pool = _make_pool(no_user=True)
        # Make fetchrow return None for users query
        original = pool.fetchrow

        async def fetchrow(query, *args, **kwargs):
            if "FROM USERS" in query.upper():
                return None
            return await original(query, *args, **kwargs)

        pool.fetchrow = fetchrow
        app = create_web_app(db_pool=pool)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/auth/login", json={
                "email": "nobody@example.com",
                "password": "pass",
            })
        assert resp.status_code == 401


class TestGetMe:
    @pytest.mark.asyncio
    async def test_get_me_success(self):
        pool = _make_pool()
        app = create_web_app(db_pool=pool)
        token = create_token(1, "test@example.com", None)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert "user" in resp.json()

    @pytest.mark.asyncio
    async def test_get_me_no_token(self):
        pool = _make_pool()
        app = create_web_app(db_pool=pool)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/auth/me")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_invalid_token(self):
        pool = _make_pool()
        app = create_web_app(db_pool=pool)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/auth/me", headers={"Authorization": "Bearer bad.token.here"})
        assert resp.status_code == 401


# ── Projects tests ───────────────────────────────────────────────

class TestProjects:
    def _headers(self):
        return {"Authorization": f"Bearer {create_token(1, 'test@example.com', None)}"}

    @pytest.mark.asyncio
    async def test_list_projects(self):
        pool = _make_pool()
        app = create_web_app(db_pool=pool)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/projects", headers=self._headers())
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_create_project(self):
        pool = _make_pool()
        app = create_web_app(db_pool=pool)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/projects",
                                     json={"name": "My Project"},
                                     headers=self._headers())
        assert resp.status_code == 201
        assert resp.json()["name"] == "My Project"

    @pytest.mark.asyncio
    async def test_update_project(self):
        pool = _make_pool()
        app = create_web_app(db_pool=pool)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.patch("/api/projects/1",
                                      json={"pinned": True},
                                      headers=self._headers())
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_project(self):
        pool = _make_pool()
        app = create_web_app(db_pool=pool)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.delete("/api/projects/1", headers=self._headers())
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_projects_require_auth(self):
        pool = _make_pool()
        app = create_web_app(db_pool=pool)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/projects")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_not_found(self):
        pool = _make_pool()
        # Override execute to return DELETE 0
        async def execute(query, *args, **kwargs):
            return "DELETE 0"
        pool.execute = execute
        app = create_web_app(db_pool=pool)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.delete("/api/projects/999", headers=self._headers())
        assert resp.status_code == 404


# ── Conversations tests ──────────────────────────────────────────

class TestConversations:
    def _headers(self):
        return {"Authorization": f"Bearer {create_token(1, 'test@example.com', None)}"}

    @pytest.mark.asyncio
    async def test_list_conversations(self):
        pool = _make_pool()
        app = create_web_app(db_pool=pool)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/conversations", headers=self._headers())
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_create_conversation(self):
        pool = _make_pool()
        app = create_web_app(db_pool=pool)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/conversations",
                                     json={"title": "My Chat"},
                                     headers=self._headers())
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert "title" in data

    @pytest.mark.asyncio
    async def test_create_conversation_no_title(self):
        """Empty title defaults to 'Новый чат'."""
        pool = _make_pool()
        app = create_web_app(db_pool=pool)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/conversations",
                                     json={},
                                     headers=self._headers())
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_get_messages(self):
        pool = _make_pool()
        app = create_web_app(db_pool=pool)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/conversations/1/messages", headers=self._headers())
        assert resp.status_code == 200
        messages = resp.json()
        assert isinstance(messages, list)
        assert messages[0]["role"] in ("user", "assistant")

    @pytest.mark.asyncio
    async def test_delete_conversation(self):
        pool = _make_pool()
        app = create_web_app(db_pool=pool)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.delete("/api/conversations/1", headers=self._headers())
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_conversations_require_auth(self):
        pool = _make_pool()
        app = create_web_app(db_pool=pool)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/conversations")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_get_messages_not_found(self):
        pool = _make_pool(no_conv=True)

        async def fetchrow(query, *args, **kwargs):
            return None  # conv not found

        pool.fetchrow = fetchrow
        app = create_web_app(db_pool=pool)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/conversations/999/messages",
                                    headers=self._headers())
        assert resp.status_code == 404


# ── 401 Unauthorized tests ───────────────────────────────────────

class TestUnauthorized:
    """All protected endpoints return 401 without token."""

    @pytest.mark.asyncio
    async def test_no_token_on_all_protected_endpoints(self):
        pool = _make_pool()
        app = create_web_app(db_pool=pool)
        endpoints = [
            ("GET", "/api/auth/me"),
            ("GET", "/api/projects"),
            ("POST", "/api/projects"),
            ("GET", "/api/conversations"),
            ("POST", "/api/conversations"),
        ]
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            for method, path in endpoints:
                if method == "GET":
                    resp = await client.get(path)
                else:
                    resp = await client.post(path, json={})
                assert resp.status_code == 401, f"{method} {path} → expected 401 got {resp.status_code}"


# ── Metrics tests ────────────────────────────────────────────────

class TestMetrics:
    @pytest.mark.asyncio
    async def test_metrics_returns_status(self):
        pool = _make_pool()
        app = create_web_app(db_pool=pool)
        token = create_token(1, "test@example.com", None)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/metrics", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "online"
