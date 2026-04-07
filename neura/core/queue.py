"""Per-capsule request queue — processing lock, BTW batching, rate limits.

@arch scope=platform  affects=all_capsules(14)
@arch depends=redis (async)
@arch risk=HIGH  restart=neura-v2
@arch role=Concurrency control. Processing lock per capsule, BTW queue per user_id.
@arch note=Lock TTL=5min safety. BTW queue TTL=1h. Per-user to prevent cross-contamination.

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

    async def get_processing_user(self, capsule_id: str) -> int | None:
        """Return user_id of who's currently processing, or None."""
        val = await self._r.get(f"{KEY_PREFIX}:processing:{capsule_id}")
        if val is None:
            return None
        try:
            return int(val)
        except (ValueError, TypeError):
            return -1  # legacy "1" value

    async def set_processing(self, capsule_id: str, active: bool,
                             user_id: int = 0) -> None:
        """Set or clear processing flag. Stores user_id for multi-employee."""
        key = f"{KEY_PREFIX}:processing:{capsule_id}"
        if active:
            await self._r.set(key, str(user_id), ex=300)  # 5 min safety TTL
        else:
            await self._r.delete(key)

    async def cancel_processing(self, capsule_id: str) -> bool:
        """Cancel current processing for a capsule.

        Sets a cancel flag that the engine loop can check.
        Returns True if there was an active processing to cancel.
        """
        key = f"{KEY_PREFIX}:processing:{capsule_id}"
        was_active = await self._r.exists(key)
        if was_active:
            # Set cancel flag (checked by transport layer)
            await self._r.set(
                f"{KEY_PREFIX}:cancel:{capsule_id}", "1", ex=60
            )
            # Clear the processing lock
            await self._r.delete(key)
            logger.info(f"Processing cancelled for {capsule_id}")
        return bool(was_active)

    async def is_cancelled(self, capsule_id: str) -> bool:
        """Check if processing was cancelled. Consumes the flag."""
        key = f"{KEY_PREFIX}:cancel:{capsule_id}"
        val = await self._r.getdel(key)
        return val is not None

    async def get_processing_age(self, capsule_id: str) -> float | None:
        """Get how long the current processing has been running (seconds).

        Returns None if not processing. Uses Redis TTL to calculate.
        """
        key = f"{KEY_PREFIX}:processing:{capsule_id}"
        ttl = await self._r.ttl(key)
        if ttl < 0:
            return None
        # Processing lock was set with ex=300 (5 min)
        return 300 - ttl

    async def clear_all_processing_locks(self) -> int:
        """Clear all stale processing locks on startup. Returns count cleared."""
        keys = []
        async for key in self._r.scan_iter(f"{KEY_PREFIX}:processing:*"):
            keys.append(key)
        for key in keys:
            await self._r.delete(key)
        # Also clear any stale cancel flags
        cancel_keys = []
        async for key in self._r.scan_iter(f"{KEY_PREFIX}:cancel:*"):
            cancel_keys.append(key)
        for key in cancel_keys:
            await self._r.delete(key)
        return len(keys)

    # === BTW queue (per capsule+user to prevent cross-contamination) ===

    async def add_btw(self, capsule_id: str, message: QueuedMessage,
                      user_id: int = 0, max_size: int = 10) -> int:
        """Add a message to per-user BTW queue. Returns queue length.

        Enforces max_size (drops oldest) and 1h TTL to prevent unbounded growth.
        """
        key = f"{KEY_PREFIX}:btw:{capsule_id}:{user_id}"
        data = json.dumps(asdict(message))
        result = await self._r.rpush(key, data)  # type: ignore[misc]
        queue_len = int(result)
        # Enforce max size — drop oldest
        if queue_len > max_size:
            await self._r.ltrim(key, queue_len - max_size, -1)
            queue_len = max_size
        # Set TTL so stale queues auto-expire
        await self._r.expire(key, 3600)  # 1 hour
        return queue_len

    async def flush_btw(self, capsule_id: str, user_id: int = 0) -> list[QueuedMessage]:
        """Get all BTW messages for a specific user and clear atomically."""
        key = f"{KEY_PREFIX}:btw:{capsule_id}:{user_id}"
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
