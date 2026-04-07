"""Memory CRUD — diary, long-term memory, learnings, corrections.

@arch scope=platform  affects=all_capsules(14)
@arch depends=core.context (ContextParts dataclass)
@arch risk=HIGH  restart=neura-v2
@arch role=All persistent data: diary writes, learning/correction saves, context retrieval.
@arch storage=PostgreSQL (asyncpg). Tables: diary, long_term_memory, learnings.
@arch sync=core.context (provides ContextParts), transport.telegram (calls build_context_parts)

All data in PostgreSQL. Pool injected via DI (asyncpg.Pool or mock).
Provides build_context_parts() to bridge with context.py.
"""
import logging
from dataclasses import dataclass, field
from datetime import date, time, datetime, timezone, timedelta

from neura.core.context import ContextParts

logger = logging.getLogger(__name__)


def _truncate_word(text: str, max_chars: int) -> str:
    """Truncate text at word boundary (last space before max_chars)."""
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    last_space = cut.rfind(" ")
    if last_space > max_chars // 2:
        return cut[:last_space] + "…"
    return cut + "…"


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
    thread_id: int | None = None


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
        thread_id=row.get("thread_id"),
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
               user_message, bot_response, model, duration_sec, tools_used, thread_id)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
               RETURNING id""",
            entry.capsule_id, d, t, entry.source,
            entry.user_message, entry.bot_response, entry.model,
            entry.duration_sec, entry.tools_used, entry.thread_id,
        )

    async def get_today_diary(self, capsule_id: str, limit: int = 10,
                              thread_id: int | None = None) -> list[DiaryEntry]:
        """Get today's diary entries (most recent first).

        If thread_id is set, only return entries from that topic.
        """
        today = datetime.now(timezone.utc).date()
        if thread_id is not None:
            rows = await self._pool.fetch(
                """SELECT * FROM diary
                   WHERE capsule_id = $1 AND date = $2 AND thread_id = $3
                   ORDER BY time DESC LIMIT $4""",
                capsule_id, today, thread_id, limit,
            )
        else:
            rows = await self._pool.fetch(
                """SELECT * FROM diary
                   WHERE capsule_id = $1 AND date = $2
                   ORDER BY time DESC LIMIT $3""",
                capsule_id, today, limit,
            )
        return [_row_to_diary(r) for r in rows]

    async def get_recent_diary(self, capsule_id: str,
                               days: int = 3, per_day: int = 5,
                               thread_id: int | None = None) -> list[DiaryEntry]:
        """Get recent diary entries (excluding today), chronological order.

        Uses per-day windowing: takes last `per_day` entries from EACH day,
        so recent days are never pushed out by older high-volume days.

        If thread_id is set, only return entries from that topic.
        """
        since = (datetime.now(timezone.utc) - timedelta(days=days)).date()
        today = datetime.now(timezone.utc).date()
        if thread_id is not None:
            rows = await self._pool.fetch(
                """SELECT * FROM (
                       SELECT *, ROW_NUMBER() OVER (
                           PARTITION BY date ORDER BY time DESC
                       ) AS rn
                       FROM diary
                       WHERE capsule_id = $1 AND date >= $2 AND date < $3 AND thread_id = $4
                   ) sub
                   WHERE rn <= $5
                   ORDER BY date ASC, time ASC""",
                capsule_id, since, today, thread_id, per_day,
            )
        else:
            rows = await self._pool.fetch(
                """SELECT * FROM (
                       SELECT *, ROW_NUMBER() OVER (
                           PARTITION BY date ORDER BY time DESC
                       ) AS rn
                       FROM diary
                       WHERE capsule_id = $1 AND date >= $2 AND date < $3
                   ) sub
                   WHERE rn <= $4
                   ORDER BY date ASC, time ASC""",
                capsule_id, since, today, per_day,
            )
        return [_row_to_diary(r) for r in rows]

    async def search_diary(self, capsule_id: str, query: str,
                           days: int = 90, limit: int = 10) -> list[DiaryEntry]:
        """Search diary by keyword (ILIKE) across full retention window."""
        since = (datetime.now(timezone.utc) - timedelta(days=days)).date()
        rows = await self._pool.fetch(
            """SELECT * FROM diary
               WHERE capsule_id = $1 AND date >= $2
               AND (user_message ILIKE $3 OR bot_response ILIKE $3)
               ORDER BY date DESC, time DESC LIMIT $4""",
            capsule_id, since, f"%{query}%", limit,
        )
        return [_row_to_diary(r) for r in rows]

    async def cleanup_old_diary(self, capsule_id: str, retention_days: int = 30) -> int:
        """Delete diary entries older than retention_days. Returns count deleted."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).date()
        result = await self._pool.execute(
            "DELETE FROM diary WHERE capsule_id = $1 AND date < $2",
            capsule_id, cutoff,
        )
        # result is like "DELETE 42"
        try:
            return int(result.split()[-1])
        except (IndexError, ValueError):
            return 0

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
               ORDER BY created_at DESC LIMIT $3""",
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

    # === Vector search ===

    def _vector_search(self, capsule, user_prompt: str) -> str:
        """Search capsule's vector index for relevant context.

        Returns formatted string or empty string.
        Non-async: chromadb is sync, runs fast (~50ms).
        """
        try:
            from neura.core.vectordb import search_capsule
            home = capsule.config.home_dir
            if not home:
                return ""
            results = search_capsule(capsule.config.id, home, user_prompt, top_k=3)
            if not results:
                return ""
            parts = []
            for r in results:
                if r["score"] >= 0.4:
                    source = r["source"]
                    text = r["text"][:500]
                    parts.append(f"[{source}] {text}")
            if not parts:
                return ""
            return "🔍 Найдено в базе знаний:\n" + "\n---\n".join(parts)
        except Exception as e:
            logger.debug(f"Vector search failed for {capsule.config.id}: {e}")
            return ""

    # === Bridge to context.py ===

    async def build_context_parts(self, capsule, user_prompt: str,
                                   thread_id: int | None = None) -> ContextParts:
        """Gather all memory data into ContextParts for ContextBuilder.

        If thread_id is set, diary entries are filtered by topic (thread).
        Memory, learnings, corrections, and vector search are shared across topics.
        """
        capsule_id = capsule.config.id
        ctx_cfg = capsule.config.memory.get("context_window", {})

        today = await self.get_today_diary(
            capsule_id, limit=ctx_cfg.get("today_diary", 10),
            thread_id=thread_id)
        recent = await self.get_recent_diary(
            capsule_id, days=ctx_cfg.get("recent_days", 3),
            per_day=ctx_cfg.get("recent_per_day", 5),
            thread_id=thread_id)
        memory = await self.search_memory(capsule_id, user_prompt)
        learnings = await self.get_learnings(capsule_id)
        corrections = await self.get_corrections(capsule_id)

        # Vector search — find relevant files in capsule's own index
        vector_context = self._vector_search(capsule, user_prompt)
        if vector_context:
            memory.append(vector_context)

        # Diary truncation — configurable per capsule
        user_chars = ctx_cfg.get("diary_user_chars", 300)
        bot_chars = ctx_cfg.get("diary_bot_chars", 500)

        today_text = "\n".join(
            f"{e.time} Пользователь: {_truncate_word(e.user_message, user_chars)}\nАгент: {_truncate_word(e.bot_response, bot_chars)}"
            for e in today
        ) if today else ""

        recent_text = "\n".join(
            f"[{e.date}] Пользователь: {_truncate_word(e.user_message, user_chars)}\nАгент: {_truncate_word(e.bot_response, bot_chars)}"
            for e in recent
        ) if recent else ""

        # Search diary beyond recent window for relevant past work
        diary_search = await self._search_diary_for_context(
            capsule_id, user_prompt, user_chars, bot_chars,
            recent_days=ctx_cfg.get("recent_days", 3))
        if diary_search and recent_text:
            recent_text += "\n\n🔍 Из архива (найдено по запросу):\n" + diary_search
        elif diary_search:
            recent_text = "🔍 Из архива (найдено по запросу):\n" + diary_search

        return ContextParts(
            system_prompt=capsule.get_system_prompt(),
            today_diary=today_text,
            recent_diary=recent_text,
            memory="\n".join(memory) if memory else "",
            learnings="\n".join(learnings) if learnings else "",
            corrections="\n".join(corrections) if corrections else "",
        )

    async def _search_diary_for_context(self, capsule_id: str, user_prompt: str,
                                         user_chars: int, bot_chars: int,
                                         recent_days: int = 3) -> str:
        """Search diary beyond recent window for relevant past conversations.

        Extracts keywords from user prompt and searches across full retention.
        Only returns results OLDER than recent_days to avoid duplicates.
        """
        # Extract meaningful words (>3 chars) from user prompt
        words = [w for w in user_prompt.lower().split() if len(w) > 3]
        if not words:
            return ""

        # Search for top 3 keywords
        seen_ids = set()
        results = []
        for word in words[:3]:
            entries = await self.search_diary(capsule_id, word, days=90, limit=5)
            since = (datetime.now(timezone.utc) - timedelta(days=recent_days)).date()
            for e in entries:
                entry_date = date.fromisoformat(e.date) if isinstance(e.date, str) else e.date
                entry_key = f"{e.date}_{e.time}"
                if entry_date < since and entry_key not in seen_ids:
                    seen_ids.add(entry_key)
                    results.append(e)

        if not results:
            return ""

        # Sort by date desc, limit to 5
        results.sort(key=lambda e: (e.date, e.time), reverse=True)
        results = results[:5]

        return "\n".join(
            f"[{e.date}] Пользователь: {_truncate_word(e.user_message, user_chars)}\nАгент: {_truncate_word(e.bot_response, bot_chars)}"
            for e in results
        )
