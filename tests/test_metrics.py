"""Tests for monitoring/metrics.py — per-capsule metrics via Redis."""
import pytest
from unittest.mock import AsyncMock


class TestMetricsCollector:

    @pytest.mark.asyncio
    async def test_record_request_increments_counter(self):
        from neura.monitoring.metrics import MetricsCollector
        redis = AsyncMock()
        mc = MetricsCollector(redis)

        await mc.record_request("cap1", 1.5, success=True)

        # Should increment requests counter
        redis.incr.assert_called()
        key_args = [c[0][0] for c in redis.incr.call_args_list]
        assert any("cap1" in k and "requests" in k for k in key_args)

    @pytest.mark.asyncio
    async def test_record_request_updates_latency(self):
        from neura.monitoring.metrics import MetricsCollector
        redis = AsyncMock()
        mc = MetricsCollector(redis)

        await mc.record_request("cap1", 2.5, success=True)

        redis.incrbyfloat.assert_called_once()
        args = redis.incrbyfloat.call_args[0]
        assert "latency" in args[0]
        assert args[1] == 2.5

    @pytest.mark.asyncio
    async def test_record_error_increments_error_counter(self):
        from neura.monitoring.metrics import MetricsCollector
        redis = AsyncMock()
        mc = MetricsCollector(redis)

        await mc.record_request("cap1", 1.0, success=False)

        key_args = [c[0][0] for c in redis.incr.call_args_list]
        assert any("errors" in k for k in key_args)

    @pytest.mark.asyncio
    async def test_record_error_tracks_type(self):
        from neura.monitoring.metrics import MetricsCollector
        redis = AsyncMock()
        mc = MetricsCollector(redis)

        await mc.record_request("cap1", 1.0, success=False, error_type="TIMEOUT")

        redis.hincrby.assert_called_once()
        args = redis.hincrby.call_args[0]
        assert "error_types" in args[0]
        assert args[1] == "TIMEOUT"

    @pytest.mark.asyncio
    async def test_record_error_no_type_skips_hincrby(self):
        from neura.monitoring.metrics import MetricsCollector
        redis = AsyncMock()
        mc = MetricsCollector(redis)

        await mc.record_request("cap1", 1.0, success=False, error_type=None)

        redis.hincrby.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_capsule_stats_returns_dict(self):
        from neura.monitoring.metrics import MetricsCollector
        redis = AsyncMock()
        redis.get = AsyncMock(side_effect=lambda k: b"10" if "requests" in k
                              else b"2" if "errors" in k
                              else b"15.5" if "latency" in k else None)
        redis.hgetall = AsyncMock(return_value={b"TIMEOUT": b"1"})
        mc = MetricsCollector(redis)

        stats = await mc.get_capsule_stats("cap1")

        assert stats["requests"] == 10
        assert stats["errors"] == 2
        assert stats["avg_latency"] == 1.55  # 15.5 / 10

    @pytest.mark.asyncio
    async def test_get_capsule_stats_empty(self):
        from neura.monitoring.metrics import MetricsCollector
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.hgetall = AsyncMock(return_value={})
        mc = MetricsCollector(redis)

        stats = await mc.get_capsule_stats("new_cap")

        assert stats["requests"] == 0
        assert stats["errors"] == 0
        assert stats["avg_latency"] == 0.0

    @pytest.mark.asyncio
    async def test_keys_have_daily_ttl(self):
        from neura.monitoring.metrics import MetricsCollector
        redis = AsyncMock()
        mc = MetricsCollector(redis)

        await mc.record_request("cap1", 1.0, success=True)

        redis.expire.assert_called()
        ttl_args = [c[0][1] for c in redis.expire.call_args_list]
        assert all(t == 86400 for t in ttl_args)

    @pytest.mark.asyncio
    async def test_redis_error_no_crash(self):
        from neura.monitoring.metrics import MetricsCollector
        redis = AsyncMock()
        redis.incr = AsyncMock(side_effect=Exception("Redis down"))
        mc = MetricsCollector(redis)

        # Should not raise
        await mc.record_request("cap1", 1.0, success=True)

    def test_redis_key_pattern(self):
        from neura.monitoring.metrics import MetricsCollector
        redis = AsyncMock()
        mc = MetricsCollector(redis)
        keys = mc._keys("test_cap")
        assert all(k.startswith("neura:metrics:test_cap:") for k in keys.values())
