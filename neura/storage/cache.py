"""Redis connection management.

Single client per application, injected into RequestQueue via DI.
URL from REDIS_URL env var or explicit parameter.
"""
import os
import logging

import redis.asyncio

logger = logging.getLogger(__name__)


class Cache:
    """Manages Redis async connection."""

    def __init__(self):
        self._redis: redis.asyncio.Redis | None = None

    @property
    def redis(self) -> redis.asyncio.Redis:
        """Get Redis client. Raises if not connected."""
        if self._redis is None:
            raise RuntimeError("Cache not connected. Call connect() first.")
        return self._redis

    async def connect(self, url: str | None = None) -> None:
        """Connect to Redis."""
        if url is None:
            url = os.environ.get("REDIS_URL")
            if not url:
                raise ValueError("No URL provided and REDIS_URL not set")

        self._redis = redis.asyncio.from_url(url, decode_responses=True)
        logger.info("Cache connected")

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None
            logger.info("Cache disconnected")
