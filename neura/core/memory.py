"""Memory CRUD — diary, long-term memory, learnings, corrections.

All data in PostgreSQL. Pool injected via DI (asyncpg.Pool or mock).
Provides build_context_parts() to bridge with context.py.
"""
import logging
from dataclasses import dataclass, field
from datetime import date, time, datetime, timezone, timedelta

from neura.core.context import ContextParts

logger = logging.getLogger(__name__)


@dataclass
class DiaryEntry:
    """Single diary record (one user↔bot interaction)."""
    capsule_id: str
    date: str
    time: str
    user_message: str
    bot_response: str
    model: str = "sonnet"
    duration_sec: float = 0
    tools_used: list[str] = field(default_factory=list)
    source: str = "telegram"


def _row_to_diary(row: dict) -> DiaryEntry:
    """Convert asyncpg Record to DiaryEntry."""
    d = row["date"]
    t = row["time"]
    return DiaryEntry(
        capsule_id=row["capsule_id"],
        date=d.isoformat() if isinstance(d, date) else str(d),
        time=t.isoformat() if isinstance(t, time) else str(t),
        user_message=row.get("user_message", ""),
        bot_response=row.get("bot_response", ""),
        model=row.get("model", "sonnet"),
        duration_sec=row.get("duration_sec", 0),
        tools_used=row.get("tools_used") or [],
        source=row.get("source", "telegram"),
    )


class MemoryStore:
    """CRUD for all capsule memory: diary, long-term, learnings."""

    def __init__(self, pool):
        if pool is None:
            raise ValueError("Database pool cannot be None")
        self._pool = pool

    # === Diary ===

    async def add_diary(self, entry: DiaryEntry) -> int:
        """Insert a diary entry, return its ID."""
        # asyncpg requires date/time objects, not strings
        d = date.fromisoformat(entry.date) if isinstance(entry.date, str) else entry.date
        t = time.fromisoformat(entry.time) if isinstance(entry.time, str) else entry.time
        return await self._pool.fetchval(
            """INSERT INTO diary (capsule_id, date, time, source,
               user_message, bot_response, model, duration_sec, tools_used)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
               RETURNING id""",
            entry.capsule_id, d, t, entry.source,
            entry.user_message, entry.bot_response, entry.model,
            entry.duration_sec, entry.tools_used,
        )

    async def get_today_diary(self, capsule_id: str, limit: int = 10) -> list[DiaryEntry]:
        """Get today's diary entries (most recent first)."""
        today = datetime.now(timezone.utc).date()
        rows = await self._pool.fetch(
            """SELECT * FROM diary
               WHERE capsule_id = $1 AND date = $2
               ORDER BY time DESC LIMIT $3""",
            capsule_id, today, limit,
        )
        return [_row_to_diary(r) for r in rows]

    async def get_recent_diary(self, capsule_id: str,
                               days: int = 3, per_day: int = 5) -> list[DiaryEntry]:
        """Get recent diary entries (excluding today)."""
        since = (datetime.now(timezone.utc) - timedelta(days=days)).date()
        today = datetime.now(timezone.utc).date()
        rows = await self._pool.fetch(
            """SELECT * FROM diary
               WHERE capsule_id = $1 AND date >= $2 AND date < $3
               ORDER BY date DESC, time DESC LIMIT $4""",
            capsule_id, since, today, days * per_day,
        )
        return [_row_to_diary(r) for r in rows]

    async def search_diary(self, capsule_id: str, query: str,
                           days: int = 14, limit: int = 5) -> list[DiaryEntry]:
        """Search diary by keyword (ILIKE)."""
        since = (datetime.now(timezone.utc) - timedelta(days=days)).date()
        rows = await self._pool.fetch(
            """SELECT * FROM diary
               WHERE capsule_id = $1 AND date >= $2
               AND (user_message ILIKE $3 OR bot_response ILIKE $3)
               ORDER BY date DESC, time DESC LIMIT $4""",
            capsule_id, since, f"%{query}%", limit,
        )
        return [_row_to_diary(r) for r in rows]

    # === Long-term memory ===

    async def add_memory(self, capsule_id: str, content: str,
                         source: str = "auto") -> int:
        """Add a long-term memory entry."""
        return await self._pool.fetchval(
            """INSERT INTO memory (capsule_id, content, source)
               VALUES ($1, $2, $3) RETURNING id""",
            capsule_id, content, source,
        )

    async def search_memory(self, capsule_id: str, query: str,
                            limit: int = 5) -> list[str]:
        """Search long-term memory by keyword."""
        rows = await self._pool.fetch(
            """SELECT content FROM memory
               WHERE capsule_id = $1 AND content ILIKE $2
               ORDER BY score DESC, created_at DESC LIMIT $3""",
            capsule_id, f"%{query}%", limit,
        )
        return [r["content"] for r in rows]

    # === Learnings & Corrections ===

    async def add_learning(self, capsule_id: str, content: str) -> int:
        """Add a learning entry."""
        return await self._pool.fetchval(
            """INSERT INTO learnings (capsule_id, type, content)
               VALUES ($1, 'learning', $2) RETURNING id""",
            capsule_id, content,
        )

    async def add_correction(self, capsule_id: str, content: str) -> int:
        """Add a correction entry."""
        return await self._pool.fetchval(
            """INSERT INTO learnings (capsule_id, type, content)
               VALUES ($1, 'correction', $2) RETURNING id""",
            capsule_id, content,
        )

    async def get_learnings(self, capsule_id: str, limit: int = 20) -> list[str]:
        """Get recent learnings."""
        rows = await self._pool.fetch(
            """SELECT content FROM learnings
               WHERE capsule_id = $1 AND type = 'learning'
               ORDER BY created_at DESC LIMIT $2""",
            capsule_id, limit,
        )
        return [r["content"] for r in rows]

    async def get_corrections(self, capsule_id: str, limit: int = 20) -> list[str]:
        """Get recent corrections."""
        rows = await self._pool.fetch(
            """SELECT content FROM learnings
               WHERE capsule_id = $1 AND type = 'correction'
               ORDER BY created_at DESC LIMIT $2""",
            capsule_id, limit,
        )
        return [r["content"] for r in rows]

    # === Bridge to context.py ===

    async def build_context_parts(self, capsule, user_prompt: str) -> ContextParts:
        """Gather all memory data into ContextParts for ContextBuilder."""
        capsule_id = capsule.config.id

        today = await self.get_today_diary(capsule_id)
        recent = await self.get_recent_diary(capsule_id)
        memory = await self.search_memory(capsule_id, user_prompt)
        learnings = await self.get_learnings(capsule_id)
        corrections = await self.get_corrections(capsule_id)

        today_text = "\n".join(
            f"{e.time} {e.user_message[:80]}" for e in today
        ) if today else ""

        recent_text = "\n".join(
            f"[{e.date}] {e.user_message[:80]}" for e in recent
        ) if recent else ""

        return ContextParts(
            system_prompt=capsule.get_system_prompt(),
            today_diary=today_text,
            recent_diary=recent_text,
            memory="\n".join(memory) if memory else "",
            learnings="\n".join(learnings) if learnings else "",
            corrections="\n".join(corrections) if corrections else "",
        )
