"""Tests for core/queue.py — Request queue per capsule (Redis-backed)."""
import pytest
import json
import time
from unittest.mock import AsyncMock


def _mock_redis():
    r = AsyncMock()
    r.get = AsyncMock(return_value=None)
    r.set = AsyncMock()
    r.delete = AsyncMock()
    r.rpush = AsyncMock(return_value=1)
    r.lrange = AsyncMock(return_value=[])
    r.incr = AsyncMock(return_value=1)
    r.expire = AsyncMock()
    return r


class TestProcessingLock:
    @pytest.mark.asyncio
    async def test_not_processing_by_default(self):
        from neura.core.queue import RequestQueue
        q = RequestQueue(_mock_redis())
        assert await q.is_processing("marina") is False

    @pytest.mark.asyncio
    async def test_set_processing(self):
        from neura.core.queue import RequestQueue
        r = _mock_redis()
        q = RequestQueue(r)
        await q.set_processing("marina", True)
        r.set.assert_called_once()
        await q.set_processing("marina", False)
        r.delete.assert_called_once()


class TestBTWQueue:
    @pytest.mark.asyncio
    async def test_add_btw(self):
        from neura.core.queue import RequestQueue, QueuedMessage
        r = _mock_redis()
        r.rpush = AsyncMock(return_value=3)
        q = RequestQueue(r)
        msg = QueuedMessage(text="Also check email", timestamp=time.time())
        count = await q.add_btw("marina", msg)
        assert count == 3
        r.rpush.assert_called_once()

    @pytest.mark.asyncio
    async def test_flush_btw_returns_messages(self):
        from neura.core.queue import RequestQueue, QueuedMessage
        r = _mock_redis()
        stored = [
            json.dumps({"text": "msg1", "timestamp": 1.0, "source": "telegram"}),
            json.dumps({"text": "msg2", "timestamp": 2.0, "source": "telegram"}),
        ]
        # Mock pipeline context manager
        mock_pipe = AsyncMock()
        mock_pipe.execute = AsyncMock(return_value=[stored, 1])
        mock_pipe.__aenter__ = AsyncMock(return_value=mock_pipe)
        mock_pipe.__aexit__ = AsyncMock(return_value=False)
        r.pipeline = lambda transaction=True: mock_pipe
        q = RequestQueue(r)
        messages = await q.flush_btw("marina")
        assert len(messages) == 2
        assert messages[0].text == "msg1"
        assert messages[1].text == "msg2"

    @pytest.mark.asyncio
    async def test_flush_btw_empty(self):
        from neura.core.queue import RequestQueue
        r = _mock_redis()
        mock_pipe = AsyncMock()
        mock_pipe.execute = AsyncMock(return_value=[[], 0])
        mock_pipe.__aenter__ = AsyncMock(return_value=mock_pipe)
        mock_pipe.__aexit__ = AsyncMock(return_value=False)
        r.pipeline = lambda transaction=True: mock_pipe
        q = RequestQueue(r)
        messages = await q.flush_btw("marina")
        assert messages == []


class TestRateLimit:
    @pytest.mark.asyncio
    async def test_increment_rate(self):
        from neura.core.queue import RequestQueue
        r = _mock_redis()
        r.incr = AsyncMock(return_value=5)
        q = RequestQueue(r)
        count = await q.increment_rate("marina")
        assert count == 5
        r.expire.assert_called_once()  # TTL set

    @pytest.mark.asyncio
    async def test_check_rate_limit_ok(self):
        from neura.core.queue import RequestQueue
        r = _mock_redis()
        r.get = AsyncMock(return_value="10")
        q = RequestQueue(r)
        result = await q.check_rate_limit("marina", max_per_day=100)
        assert result is None  # OK

    @pytest.mark.asyncio
    async def test_check_rate_limit_warn(self):
        from neura.core.queue import RequestQueue
        r = _mock_redis()
        r.get = AsyncMock(return_value="85")
        q = RequestQueue(r)
        result = await q.check_rate_limit("marina", max_per_day=100)
        assert result == "warn"

    @pytest.mark.asyncio
    async def test_check_rate_limit_blocked(self):
        from neura.core.queue import RequestQueue
        r = _mock_redis()
        r.get = AsyncMock(return_value="101")
        q = RequestQueue(r)
        result = await q.check_rate_limit("marina", max_per_day=100)
        assert result == "blocked"
