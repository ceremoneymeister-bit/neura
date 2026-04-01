"""Per-capsule request queue — processing lock, BTW batching, rate limits.

All state in Redis. One capsule processes one request at a time.
Messages arriving during processing are queued (BTW pattern)
and flushed as additional context for the next response.
"""
import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

import redis.asyncio

logger = logging.getLogger(__name__)

KEY_PREFIX = "neura"
RATE_TTL_SECONDS = 48 * 3600  # 48h (covers timezone edge cases)


@dataclass
class QueuedMessage:
    """A message waiting in the BTW queue."""
    text: str
    timestamp: float
    source: str = "telegram"


class RequestQueue:
    """Per-capsule request queue backed by Redis."""

    def __init__(self, redis_client: redis.asyncio.Redis):
        self._r = redis_client

    # === Processing lock ===

    async def is_processing(self, capsule_id: str) -> bool:
        """Check if capsule is currently processing a request."""
        val = await self._r.get(f"{KEY_PREFIX}:processing:{capsule_id}")
        return val is not None

    async def set_processing(self, capsule_id: str, active: bool) -> None:
        """Set or clear processing flag."""
        key = f"{KEY_PREFIX}:processing:{capsule_id}"
        if active:
            await self._r.set(key, "1", ex=600)  # 10 min safety TTL
        else:
            await self._r.delete(key)

    # === BTW queue ===

    async def add_btw(self, capsule_id: str, message: QueuedMessage) -> int:
        """Add a message to BTW queue. Returns queue length."""
        key = f"{KEY_PREFIX}:btw:{capsule_id}"
        data = json.dumps(asdict(message))
        result = await self._r.rpush(key, data)  # type: ignore[misc]
        return int(result)

    async def flush_btw(self, capsule_id: str) -> list[QueuedMessage]:
        """Get all BTW messages and clear the queue atomically."""
        key = f"{KEY_PREFIX}:btw:{capsule_id}"
        # Atomic: get + delete in pipeline
        async with self._r.pipeline(transaction=True) as pipe:
            pipe.lrange(key, 0, -1)
            pipe.delete(key)
            results = await pipe.execute()
        raw_messages = results[0]
        if not raw_messages:
            return []
        messages = []
        for raw in raw_messages:
            try:
                data = json.loads(raw)
                messages.append(QueuedMessage(**data))
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Invalid BTW message in queue: {raw}")
        return messages

    # === Rate limiting ===

    async def increment_rate(self, capsule_id: str) -> int:
        """Increment today's request counter. Returns new count."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        key = f"{KEY_PREFIX}:rate:{capsule_id}:{today}"
        count = await self._r.incr(key)
        await self._r.expire(key, RATE_TTL_SECONDS)
        return count

    async def get_rate(self, capsule_id: str) -> int:
        """Get today's request count."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        key = f"{KEY_PREFIX}:rate:{capsule_id}:{today}"
        val = await self._r.get(key)
        try:
            return int(val) if val else 0
        except (ValueError, TypeError):
            return 0

    async def check_rate_limit(self, capsule_id: str, max_per_day: int) -> str | None:
        """Check rate limit status.

        Returns: None (OK), "warn" (>80%), "blocked" (exceeded).
        """
        if max_per_day <= 0:
            return "blocked"
        count = await self.get_rate(capsule_id)
        if count >= max_per_day:
            return "blocked"
        if count >= max_per_day * 0.8:
            return "warn"
        return None
