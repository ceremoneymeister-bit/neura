"""SessionTracker — maps (capsule_id, user_id) → Claude CLI session_id.

Keeps one active session per user per capsule.  Stale sessions (older than
TTL) are automatically evicted so Claude starts fresh.

Thread-safe: uses a simple dict + asyncio lock.
"""
import asyncio
import logging
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)

DEFAULT_SESSION_TTL = 10800  # 3 hours — after this, start a new session
MAX_SESSIONS = 500  # prevent unbounded growth


@dataclass
class SessionEntry:
    session_id: str
    created_at: float
    last_used: float
    message_count: int = 1


class SessionTracker:
    """In-memory store for active Claude CLI session IDs."""

    def __init__(self, ttl: int = DEFAULT_SESSION_TTL):
        self._sessions: dict[str, SessionEntry] = {}
        self._ttl = ttl
        self._lock = asyncio.Lock()

    @staticmethod
    def _key(capsule_id: str, user_id: int) -> str:
        return f"{capsule_id}:{user_id}"

    async def get(self, capsule_id: str, user_id: int) -> str | None:
        """Get active session_id, or None if expired/missing."""
        key = self._key(capsule_id, user_id)
        async with self._lock:
            entry = self._sessions.get(key)
            if entry is None:
                return None
            # Check TTL
            if time.monotonic() - entry.last_used > self._ttl:
                logger.info(f"Session expired for {key} (idle {time.monotonic() - entry.last_used:.0f}s)")
                del self._sessions[key]
                return None
            return entry.session_id

    async def set(self, capsule_id: str, user_id: int, session_id: str) -> None:
        """Store or update session_id for a user."""
        if not session_id:
            return
        key = self._key(capsule_id, user_id)
        now = time.monotonic()
        async with self._lock:
            existing = self._sessions.get(key)
            if existing and existing.session_id == session_id:
                existing.last_used = now
                existing.message_count += 1
            else:
                self._sessions[key] = SessionEntry(
                    session_id=session_id,
                    created_at=now,
                    last_used=now,
                )
            # Evict oldest if too many
            if len(self._sessions) > MAX_SESSIONS:
                self._evict_oldest()

    async def invalidate(self, capsule_id: str, user_id: int) -> None:
        """Remove session (e.g. after error that requires fresh start)."""
        key = self._key(capsule_id, user_id)
        async with self._lock:
            self._sessions.pop(key, None)

    async def invalidate_capsule(self, capsule_id: str) -> None:
        """Remove all sessions for a capsule (e.g. after config change)."""
        async with self._lock:
            keys_to_remove = [k for k in self._sessions if k.startswith(f"{capsule_id}:")]
            for k in keys_to_remove:
                del self._sessions[k]
            if keys_to_remove:
                logger.info(f"Invalidated {len(keys_to_remove)} sessions for {capsule_id}")

    def _evict_oldest(self) -> None:
        """Remove oldest entries to stay within MAX_SESSIONS."""
        sorted_keys = sorted(
            self._sessions, key=lambda k: self._sessions[k].last_used
        )
        to_remove = len(self._sessions) - MAX_SESSIONS
        for key in sorted_keys[:to_remove]:
            del self._sessions[key]

    async def stats(self) -> dict:
        """Return stats for monitoring."""
        async with self._lock:
            now = time.monotonic()
            active = sum(
                1 for e in self._sessions.values()
                if now - e.last_used <= self._ttl
            )
            return {
                "total": len(self._sessions),
                "active": active,
                "ttl": self._ttl,
            }
