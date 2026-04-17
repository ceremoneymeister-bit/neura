"""Memory CRUD — diary, long-term memory, learnings, corrections.

@arch scope=platform  affects=all_capsules(14)
@arch depends=core.context (ContextParts dataclass)
@arch risk=HIGH  restart=neura-v2
@arch role=All persistent data: diary writes, learning/correction saves, context retrieval.
@arch storage=PostgreSQL (asyncpg). Tables: diary, long_term_memory, learnings.
@arch sync=core.context (provides ContextParts), transport.telegram (calls build_context_parts)

All data in PostgreSQL. Pool injected via DI (asyncpg.Pool or mock).
Provides build_context_parts() to bridge with context.py.

Long-term memory uses pgvector cosine similarity (via embedding VECTOR(1024)
from intfloat/multilingual-e5-large, shared singleton with core.vectordb).
Falls back to ILIKE keyword search if the embedding model is unavailable.
"""
import asyncio
import logging
import time as _time_mod
from dataclasses import dataclass, field
from datetime import date, time, datetime, timezone, timedelta

from neura.core.context import ContextParts

logger = logging.getLogger(__name__)


async def _embed_text(text: str, *, is_query: bool) -> list[float] | None:
    """Compute a 1024-dim embedding for `text` using the e5-large singleton.

    Returns None if the model cannot be loaded (caller falls back to ILIKE).
    Offloaded to a thread so we don't block the event loop (~30ms CPU).
    """
    try:
        from neura.core.vectordb import _get_model, _IS_E5_MODEL
    except Exception as e:  # pragma: no cover
        logger.debug(f"vectordb import failed: {e}")
        return None

    model = _get_model()
    if model is None:
        return None

    prefix = ("query: " if is_query else "passage: ") if _IS_E5_MODEL else ""
    payload = f"{prefix}{text}"

    def _encode() -> list[float]:
        vec = model.encode([payload], show_progress_bar=False)
        return vec[0].tolist()

    try:
        return await asyncio.to_thread(_encode)
    except Exception as e:
        logger.warning(f"embed_text failed: {e}")
        return None


def _vec_to_pg_literal(vec: list[float]) -> str:
    """Format a Python list as a pgvector literal: '[0.1,0.2,...]'."""
    return "[" + ",".join(f"{x:.7f}" for x in vec) + "]"


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
        """Insert a diary entry, return its ID.

        Uses ON CONFLICT upsert to survive sequence-out-of-sync scenarios
        (duplicate key on diary_pkey). If the auto-generated id collides with
        an existing row, the sequence is reset to max(id)+1 and the insert is
        retried (up to 3 times).
        """
        # asyncpg requires date/time objects, not strings
        d = date.fromisoformat(entry.date) if isinstance(entry.date, str) else entry.date
        t = time.fromisoformat(entry.time) if isinstance(entry.time, str) else entry.time

        insert_sql = """INSERT INTO diary (capsule_id, date, time, source,
               user_message, bot_response, model, duration_sec, tools_used, thread_id)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
               ON CONFLICT (id) DO UPDATE SET
                   user_message = EXCLUDED.user_message,
                   bot_response = EXCLUDED.bot_response,
                   model = EXCLUDED.model,
                   duration_sec = EXCLUDED.duration_sec,
                   tools_used = EXCLUDED.tools_used,
                   source = EXCLUDED.source,
                   thread_id = EXCLUDED.thread_id
               RETURNING id"""
        params = (
            entry.capsule_id, d, t, entry.source,
            entry.user_message, entry.bot_response, entry.model,
            entry.duration_sec, entry.tools_used, entry.thread_id,
        )

        for attempt in range(3):
            try:
                return await self._pool.fetchval(insert_sql, *params)
            except Exception as exc:
                if "diary_pkey" in str(exc) or "duplicate key" in str(exc).lower():
                    logger.warning(
                        "Diary insert hit duplicate PK (attempt %d/3), "
                        "resetting sequence diary_id_seq",
                        attempt + 1,
                    )
                    try:
                        await self._pool.execute(
                            "SELECT setval('diary_id_seq', "
                            "COALESCE((SELECT MAX(id) FROM diary), 0) + 1, false)"
                        )
                    except Exception as seq_err:
                        logger.error("Failed to reset diary_id_seq: %s", seq_err)
                    continue
                raise
        # Final attempt without catching — let error propagate
        return await self._pool.fetchval(insert_sql, *params)

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
                               days: int = 3, per_day: int = 10,
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
        """Add a long-term memory entry with e5-large embedding.

        Embedding is computed off the event loop. If the model is unavailable
        (first boot, ML deps missing), the row is still inserted with
        embedding=NULL and will be picked up by the next backfill run.
        """
        embedding = await _embed_text(content, is_query=False)
        if embedding is None:
            return await self._pool.fetchval(
                """INSERT INTO memory (capsule_id, content, source)
                   VALUES ($1, $2, $3) RETURNING id""",
                capsule_id, content, source,
            )
        return await self._pool.fetchval(
            """INSERT INTO memory (capsule_id, content, source, embedding)
               VALUES ($1, $2, $3, $4::vector) RETURNING id""",
            capsule_id, content, source, _vec_to_pg_literal(embedding),
        )

    async def search_memory(self, capsule_id: str, query: str,
                            limit: int = 5) -> list[str]:
        """Search long-term memory by cosine similarity (pgvector).

        Falls back to ILIKE keyword search if the embedding model is
        unavailable. Logs latency for the `search_memory_latency_ms` metric.
        """
        t0 = _time_mod.perf_counter()
        query_vec = await _embed_text(query, is_query=True)

        if query_vec is None:
            rows = await self._pool.fetch(
                """SELECT content FROM memory
                   WHERE capsule_id = $1 AND content ILIKE $2
                   ORDER BY created_at DESC LIMIT $3""",
                capsule_id, f"%{query}%", limit,
            )
            dt_ms = (_time_mod.perf_counter() - t0) * 1000
            logger.info(
                f"search_memory_latency_ms={dt_ms:.1f} mode=ilike "
                f"capsule={capsule_id} hits={len(rows)}"
            )
            results = [r["content"] for r in rows]
            for c in results:
                asyncio.create_task(self._bump_memory_hit(capsule_id, c))
            return results

        # pgvector cosine: rows with NULL embedding are excluded automatically
        rows = await self._pool.fetch(
            """SELECT content FROM memory
               WHERE capsule_id = $1 AND embedding IS NOT NULL
               ORDER BY embedding <=> $2::vector LIMIT $3""",
            capsule_id, _vec_to_pg_literal(query_vec), limit,
        )
        dt_ms = (_time_mod.perf_counter() - t0) * 1000
        logger.info(
            f"search_memory_latency_ms={dt_ms:.1f} mode=cosine "
            f"capsule={capsule_id} hits={len(rows)}"
        )
        results = [r["content"] for r in rows]
        for c in results:
            asyncio.create_task(self._bump_memory_hit(capsule_id, c))
        return results

    # === Learnings & Corrections ===

    async def add_learning(self, capsule_id: str, content: str) -> int:
        """Add a learning entry with embedding for wisdom graduation (with dedup)."""
        embedding = await _embed_text(content, is_query=False)
        if embedding:
            existing = await self._pool.fetchval(
                """SELECT id FROM learnings
                   WHERE capsule_id = $1 AND type = 'learning'
                   AND embedding IS NOT NULL
                   AND (embedding <=> $2::vector) < 0.25
                   LIMIT 1""",
                capsule_id, _vec_to_pg_literal(embedding),
            )
            if existing:
                logger.info(f"Skip duplicate learning for {capsule_id}: {content[:60]}")
                return existing
            return await self._pool.fetchval(
                """INSERT INTO learnings (capsule_id, type, content, embedding)
                   VALUES ($1, 'learning', $2, $3::vector) RETURNING id""",
                capsule_id, content, _vec_to_pg_literal(embedding),
            )
        # Fallback: exact text match
        existing = await self._pool.fetchval(
            "SELECT id FROM learnings WHERE capsule_id = $1 AND type = 'learning' AND content = $2",
            capsule_id, content,
        )
        if existing:
            return existing
        return await self._pool.fetchval(
            """INSERT INTO learnings (capsule_id, type, content)
               VALUES ($1, 'learning', $2) RETURNING id""",
            capsule_id, content,
        )

    async def add_correction(self, capsule_id: str, content: str) -> int:
        """Add a correction entry (with dedup)."""
        embedding = await _embed_text(content, is_query=False)
        if embedding:
            existing = await self._pool.fetchval(
                """SELECT id FROM learnings
                   WHERE capsule_id = $1 AND type = 'correction'
                   AND embedding IS NOT NULL
                   AND (embedding <=> $2::vector) < 0.25
                   LIMIT 1""",
                capsule_id, _vec_to_pg_literal(embedding),
            )
            if existing:
                logger.info(f"Skip duplicate correction for {capsule_id}: {content[:60]}")
                return existing
            return await self._pool.fetchval(
                """INSERT INTO learnings (capsule_id, type, content, embedding)
                   VALUES ($1, 'correction', $2, $3::vector) RETURNING id""",
                capsule_id, content, _vec_to_pg_literal(embedding),
            )
        # Fallback: exact text match
        existing = await self._pool.fetchval(
            "SELECT id FROM learnings WHERE capsule_id = $1 AND type = 'correction' AND content = $2",
            capsule_id, content,
        )
        if existing:
            return existing
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

    # === Behavioral Rules (L1 — graduated wisdom) ===

    async def get_behavioral_rules(self, capsule_id: str,
                                    limit: int = 10) -> list[str]:
        """Get active behavioral rules (graduated from recurring learnings)."""
        rows = await self._pool.fetch(
            """SELECT rule FROM behavioral_rules
               WHERE capsule_id = $1 AND active = true
               ORDER BY occurrence_count DESC LIMIT $2""",
            capsule_id, limit,
        )
        return [r["rule"] for r in rows]

    # === Knowledge Graph ===

    async def add_triple(self, capsule_id: str, subject: str,
                         predicate: str, object_: str,
                         source: str | None = None) -> int:
        """Add a temporal triple to the knowledge graph."""
        return await self._pool.fetchval(
            """INSERT INTO knowledge_graph
               (capsule_id, subject, predicate, object, source)
               VALUES ($1, $2, $3, $4, $5) RETURNING id""",
            capsule_id, subject, predicate, object_, source,
        )

    async def invalidate_triple(self, capsule_id: str, fact_id: int) -> None:
        """Soft-delete a fact by setting valid_to = NOW()."""
        await self._pool.execute(
            """UPDATE knowledge_graph SET valid_to = NOW()
               WHERE id = $1 AND capsule_id = $2""",
            fact_id, capsule_id,
        )

    async def search_knowledge_graph(self, capsule_id: str, query: str,
                                      limit: int = 5) -> list[dict]:
        """Search active knowledge graph triples by subject/object keyword."""
        words = [w for w in query.lower().split() if len(w) > 3]
        if not words:
            return []
        # Search across top-3 keywords
        results = []
        seen = set()
        for word in words[:3]:
            pattern = f"%{word}%"
            rows = await self._pool.fetch(
                """SELECT id, subject, predicate, object, valid_from
                   FROM knowledge_graph
                   WHERE capsule_id = $1 AND valid_to IS NULL
                   AND (LOWER(subject) LIKE $2 OR LOWER(object) LIKE $2)
                   ORDER BY created_at DESC LIMIT $3""",
                capsule_id, pattern, limit,
            )
            for r in rows:
                if r["id"] not in seen:
                    seen.add(r["id"])
                    results.append({
                        "subject": r["subject"],
                        "predicate": r["predicate"],
                        "object": r["object"],
                        "since": r["valid_from"].isoformat() if r["valid_from"] else "",
                    })
        return results[:limit]

    # === Wisdom Graduation ===

    async def graduate_wisdom(self, capsule_id: str) -> list[str]:
        """Graduate recurring learnings (2+ days) to behavioral rules.

        Finds learnings with similar content that appeared on different days,
        and promotes them to permanent behavioral rules.
        """
        # Get all learnings with embeddings
        rows = await self._pool.fetch(
            """SELECT id, content, created_at, embedding
               FROM learnings
               WHERE capsule_id = $1 AND type = 'learning'
               AND embedding IS NOT NULL
               ORDER BY created_at DESC""",
            capsule_id,
        )
        if len(rows) < 2:
            return []

        # Group similar learnings by cosine similarity
        # Use SQL for pairwise comparison (more efficient for small sets)
        candidates = await self._pool.fetch(
            """SELECT l1.content, COUNT(DISTINCT DATE(l1.created_at)) as days,
                      MIN(l1.created_at) as first_seen
               FROM learnings l1
               JOIN learnings l2 ON l1.capsule_id = l2.capsule_id
                   AND l1.id != l2.id
                   AND l1.embedding IS NOT NULL AND l2.embedding IS NOT NULL
                   AND (l1.embedding <=> l2.embedding) < 0.35
               WHERE l1.capsule_id = $1 AND l1.type = 'learning'
               GROUP BY l1.content
               HAVING COUNT(DISTINCT DATE(l1.created_at)) >= 2""",
            capsule_id,
        )

        graduated = []
        for row in candidates:
            content = row["content"]
            # Check if already graduated
            existing = await self._pool.fetchval(
                """SELECT COUNT(*) FROM behavioral_rules
                   WHERE capsule_id = $1 AND rule = $2""",
                capsule_id, content,
            )
            if existing > 0:
                continue

            embedding = await _embed_text(content, is_query=False)
            if embedding:
                await self._pool.execute(
                    """INSERT INTO behavioral_rules
                       (capsule_id, rule, source_pattern, occurrence_count,
                        first_seen, embedding)
                       VALUES ($1, $2, $3, $4, $5, $6::vector)""",
                    capsule_id, content, content, row["days"],
                    row["first_seen"],
                    _vec_to_pg_literal(embedding),
                )
            else:
                await self._pool.execute(
                    """INSERT INTO behavioral_rules
                       (capsule_id, rule, source_pattern, occurrence_count,
                        first_seen)
                       VALUES ($1, $2, $3, $4, $5)""",
                    capsule_id, content, content, row["days"],
                    row["first_seen"],
                )
            graduated.append(content)
            logger.info(f"Graduated wisdom for {capsule_id}: {content[:80]}...")

        return graduated

    async def graduate_corrections(self, capsule_id: str) -> list[str]:
        """Graduate recurring corrections to behavioral rules.

        Two pathways:
        1. Similar corrections (cosine distance < 0.40) appearing 2+ times
        2. Strong signal corrections (НИКОГДА/ВСЕГДА/ЗАПРЕЩЕНО) — promote after 1 occurrence
        """
        import re
        STRONG_MARKERS = re.compile(
            r'(?i)\b(НИКОГДА|ВСЕГДА|ЗАПРЕЩЕНО|НЕ делай|НЕ использовать|ОБЯЗАТЕЛЬНО)\b')

        # Pathway 1: recurring similar corrections (2+ occurrences)
        candidates = await self._pool.fetch(
            """SELECT l1.content, COUNT(*) as cnt,
                      MIN(l1.created_at) as first_seen
               FROM learnings l1
               JOIN learnings l2 ON l1.capsule_id = l2.capsule_id
                   AND l1.id != l2.id
                   AND l1.embedding IS NOT NULL AND l2.embedding IS NOT NULL
                   AND (l1.embedding <=> l2.embedding) < 0.40
               WHERE l1.capsule_id = $1 AND l1.type = 'correction'
               GROUP BY l1.content
               HAVING COUNT(*) >= 2""",
            capsule_id,
        )

        graduated = []
        for row in candidates:
            content = row["content"]
            # Check if already graduated (exact or similar)
            existing = await self._pool.fetchval(
                """SELECT COUNT(*) FROM behavioral_rules
                   WHERE capsule_id = $1 AND rule = $2""",
                capsule_id, content,
            )
            if existing > 0:
                continue

            embedding = await _embed_text(content, is_query=False)
            if embedding:
                # Also check cosine similarity against existing rules
                similar_rule = await self._pool.fetchval(
                    """SELECT id FROM behavioral_rules
                       WHERE capsule_id = $1 AND embedding IS NOT NULL
                       AND (embedding <=> $2::vector) < 0.30
                       LIMIT 1""",
                    capsule_id, _vec_to_pg_literal(embedding),
                )
                if similar_rule:
                    continue

                await self._pool.execute(
                    """INSERT INTO behavioral_rules
                       (capsule_id, rule, source_pattern, occurrence_count,
                        first_seen, embedding)
                       VALUES ($1, $2, 'correction:recurring', $3, $4, $5::vector)""",
                    capsule_id, content, row["cnt"],
                    row["first_seen"], _vec_to_pg_literal(embedding),
                )
            else:
                await self._pool.execute(
                    """INSERT INTO behavioral_rules
                       (capsule_id, rule, source_pattern, occurrence_count, first_seen)
                       VALUES ($1, $2, 'correction:recurring', $3, $4)""",
                    capsule_id, content, row["cnt"], row["first_seen"],
                )
            graduated.append(content)
            logger.info(f"Graduated correction for {capsule_id}: {content[:80]}...")

        # Pathway 2: strong signal corrections (single occurrence)
        strong = await self._pool.fetch(
            """SELECT id, content, created_at FROM learnings
               WHERE capsule_id = $1 AND type = 'correction'
               AND embedding IS NOT NULL
               ORDER BY created_at DESC""",
            capsule_id,
        )
        for row in strong:
            content = row["content"]
            if not STRONG_MARKERS.search(content):
                continue
            # Check not already graduated
            existing = await self._pool.fetchval(
                """SELECT COUNT(*) FROM behavioral_rules
                   WHERE capsule_id = $1 AND rule = $2""",
                capsule_id, content,
            )
            if existing > 0:
                continue
            embedding = await _embed_text(content, is_query=False)
            if embedding:
                similar_rule = await self._pool.fetchval(
                    """SELECT id FROM behavioral_rules
                       WHERE capsule_id = $1 AND embedding IS NOT NULL
                       AND (embedding <=> $2::vector) < 0.30
                       LIMIT 1""",
                    capsule_id, _vec_to_pg_literal(embedding),
                )
                if similar_rule:
                    continue
                await self._pool.execute(
                    """INSERT INTO behavioral_rules
                       (capsule_id, rule, source_pattern, occurrence_count,
                        first_seen, embedding)
                       VALUES ($1, $2, 'correction:strong', 1, $3, $4::vector)""",
                    capsule_id, content, row["created_at"],
                    _vec_to_pg_literal(embedding),
                )
            else:
                await self._pool.execute(
                    """INSERT INTO behavioral_rules
                       (capsule_id, rule, source_pattern, occurrence_count, first_seen)
                       VALUES ($1, $2, 'correction:strong', 1, $3)""",
                    capsule_id, content, row["created_at"],
                )
            graduated.append(content)
            logger.info(f"Promoted strong correction for {capsule_id}: {content[:80]}...")

        return graduated

    # === Layered memory (L1) ===

    async def get_l1_memory(self, capsule_id: str) -> list[str]:
        """Get L1 (critical) memory entries — always loaded."""
        rows = await self._pool.fetch(
            """SELECT content FROM memory
               WHERE capsule_id = $1 AND layer = 'L1'
               ORDER BY hit_count DESC""",
            capsule_id,
        )
        return [r["content"] for r in rows]

    async def _bump_memory_hit(self, capsule_id: str, content: str) -> None:
        """Increment hit_count and update last_hit for matched memory."""
        await self._pool.execute(
            """UPDATE memory SET hit_count = hit_count + 1, last_hit = NOW()
               WHERE capsule_id = $1 AND content = $2""",
            capsule_id, content,
        )

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
            per_day=ctx_cfg.get("recent_per_day", 10),
            thread_id=thread_id)
        memory = await self.search_memory(capsule_id, user_prompt)
        learnings = await self.get_learnings(
            capsule_id, limit=ctx_cfg.get("max_learnings", 50))
        corrections = await self.get_corrections(
            capsule_id, limit=ctx_cfg.get("max_corrections", 100))

        # Layered loading (if enabled in capsule config)
        layered = capsule.config.memory.get("layered_loading", False)
        behavioral_rules_text = ""
        knowledge_graph_text = ""

        if layered:
            # L1: behavioral rules + critical memory
            rules = await self.get_behavioral_rules(capsule_id)
            l1_mem = await self.get_l1_memory(capsule_id)
            all_l1 = rules + l1_mem
            if all_l1:
                behavioral_rules_text = "\n".join(f"• {r}" for r in all_l1)

            # L3: knowledge graph (on-demand, query-driven)
            if capsule.config.memory.get("knowledge_graph", False):
                kg_triples = await self.search_knowledge_graph(
                    capsule_id, user_prompt)
                if kg_triples:
                    knowledge_graph_text = "\n".join(
                        f"• {t['subject']} → {t['predicate']} → {t['object']}"
                        + (f" (с {t['since'][:10]})" if t.get('since') else "")
                        for t in kg_triples
                    )

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
            behavioral_rules=behavioral_rules_text,
            today_diary=today_text,
            recent_diary=recent_text,
            memory="\n".join(memory) if memory else "",
            learnings="\n".join(learnings) if learnings else "",
            corrections="\n".join(corrections) if corrections else "",
            knowledge_graph=knowledge_graph_text,
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
