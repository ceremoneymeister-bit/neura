"""JWT authentication utilities for the Neura Web API.

Provides password hashing (bcrypt), JWT token creation/decoding,
and a FastAPI dependency for extracting the current user from the request.
"""
import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import bcrypt
import jwt
from fastapi import Request, HTTPException, status

logger = logging.getLogger(__name__)

# Secret key — read from env, fallback for tests only
JWT_SECRET = os.environ.get("JWT_SECRET", "neura-web-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_DAYS = 7


# ── Password ────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """Hash plaintext password with bcrypt. Returns str."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(plain.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain matches hashed (bcrypt)."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ── JWT ─────────────────────────────────────────────────────────

def create_token(user_id: int, email: str, capsule_id: Optional[str] = None) -> str:
    """Create a signed JWT with 7-day expiry."""
    payload = {
        "sub": str(user_id),
        "email": email,
        "capsule_id": capsule_id,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRE_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT. Returns payload dict.

    Raises jwt.ExpiredSignatureError or jwt.InvalidTokenError on failure.
    """
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


# ── FastAPI dependency ───────────────────────────────────────────

def get_current_user(request: Request) -> dict:
    """FastAPI dependency: extract and validate Bearer token.

    Returns dict with keys: user_id (int), email (str), capsule_id (str|None).
    Raises 401 if token is missing or invalid.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header[len("Bearer "):]
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "user_id": int(payload["sub"]),
        "email": payload.get("email", ""),
        "capsule_id": payload.get("capsule_id"),
    }
