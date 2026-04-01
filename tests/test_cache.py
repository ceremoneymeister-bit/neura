"""Tests for storage/cache.py — Redis connection management."""
import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestConnect:
    @pytest.mark.asyncio
    async def test_connect_creates_redis(self):
        from neura.storage.cache import Cache
        cache = Cache()
        mock_redis = AsyncMock()
        with patch("redis.asyncio.from_url", return_value=mock_redis) as mock_from:
            await cache.connect("redis://localhost:6379/0")
        mock_from.assert_called_once()
        assert cache.redis is mock_redis

    @pytest.mark.asyncio
    async def test_connect_from_env(self):
        from neura.storage.cache import Cache
        cache = Cache()
        mock_redis = AsyncMock()
        with patch.dict(os.environ, {"REDIS_URL": "redis://env:6379/0"}):
            with patch("redis.asyncio.from_url", return_value=mock_redis) as mock_from:
                await cache.connect()
        assert "env" in str(mock_from.call_args)


class TestDisconnect:
    @pytest.mark.asyncio
    async def test_disconnect_closes(self):
        from neura.storage.cache import Cache
        cache = Cache()
        mock_redis = AsyncMock()
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            await cache.connect("redis://localhost:6379/0")
        await cache.disconnect()
        mock_redis.aclose.assert_called_once()


class TestProperty:
    def test_raises_if_not_connected(self):
        from neura.storage.cache import Cache
        cache = Cache()
        with pytest.raises(RuntimeError, match="not connected"):
            _ = cache.redis
