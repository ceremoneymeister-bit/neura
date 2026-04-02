"""Tests for monitoring/health.py — background health checker."""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestHealthStatus:

    def test_dataclass_fields(self):
        from neura.monitoring.health import HealthStatus
        s = HealthStatus(name="test", healthy=True, detail="ok")
        assert s.name == "test"
        assert s.healthy is True
        assert s.detail == "ok"
        assert s.checked_at == 0.0


class TestHealthMonitor:

    def _make_monitor(self, **overrides):
        from neura.monitoring.health import HealthMonitor
        pool = overrides.pop("db_pool", None)
        if pool is None:
            pool = AsyncMock()
            pool.fetchval = AsyncMock(return_value=1)
        redis = overrides.pop("redis_client", None)
        if redis is None:
            redis = AsyncMock()
            redis.ping = AsyncMock(return_value=True)
        defaults = {
            "db_pool": pool,
            "redis_client": redis,
            "capsules": {},
            "alert_sender": AsyncMock(),
            "interval": 30,
        }
        defaults.update(overrides)
        return HealthMonitor(**defaults)

    @pytest.mark.asyncio
    async def test_check_postgres_success(self):
        pool = AsyncMock()
        pool.fetchval = AsyncMock(return_value=1)
        mon = self._make_monitor(db_pool=pool)

        result = await mon._check_postgres()
        assert result.healthy is True
        assert result.name == "postgres"

    @pytest.mark.asyncio
    async def test_check_postgres_failure(self):
        pool = AsyncMock()
        pool.fetchval = AsyncMock(side_effect=Exception("Connection refused"))
        mon = self._make_monitor(db_pool=pool)

        result = await mon._check_postgres()
        assert result.healthy is False
        assert "Connection refused" in result.detail

    @pytest.mark.asyncio
    async def test_check_redis_success(self):
        redis = AsyncMock()
        redis.ping = AsyncMock(return_value=True)
        mon = self._make_monitor(redis_client=redis)

        result = await mon._check_redis()
        assert result.healthy is True

    @pytest.mark.asyncio
    async def test_check_redis_failure(self):
        redis = AsyncMock()
        redis.ping = AsyncMock(side_effect=Exception("Redis down"))
        mon = self._make_monitor(redis_client=redis)

        result = await mon._check_redis()
        assert result.healthy is False

    @pytest.mark.asyncio
    async def test_check_claude_cli_found(self):
        mon = self._make_monitor()
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            result = await mon._check_claude_cli()
        assert result.healthy is True

    @pytest.mark.asyncio
    async def test_check_claude_cli_missing(self):
        mon = self._make_monitor()
        with patch("shutil.which", return_value=None):
            result = await mon._check_claude_cli()
        assert result.healthy is False

    @pytest.mark.asyncio
    async def test_check_all_returns_list(self):
        mon = self._make_monitor()
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            results = await mon.check_all()
        assert isinstance(results, list)
        assert len(results) >= 3  # postgres, redis, claude_cli
        assert all(hasattr(r, "healthy") for r in results)

    @pytest.mark.asyncio
    async def test_alert_on_transition_to_unhealthy(self):
        alert = AsyncMock()
        alert.send = AsyncMock(return_value=True)
        pool = AsyncMock()
        pool.fetchval = AsyncMock(side_effect=Exception("DB down"))
        redis = AsyncMock()
        redis.ping = AsyncMock(return_value=True)
        mon = self._make_monitor(db_pool=pool, redis_client=redis, alert_sender=alert)

        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            await mon._run_checks_once()

        # Should have sent HEALTH_FAIL alert
        alert.send.assert_called()
        call_args = [c[1] for c in alert.send.call_args_list]
        assert any(ca.get("alert_type") == "HEALTH_FAIL" for ca in call_args)

    @pytest.mark.asyncio
    async def test_no_alert_when_still_healthy(self):
        alert = AsyncMock()
        alert.send = AsyncMock(return_value=True)
        mon = self._make_monitor(alert_sender=alert)

        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            await mon._run_checks_once()

        # No alerts — everything healthy
        alert.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_recovery_alert(self):
        alert = AsyncMock()
        alert.send = AsyncMock(return_value=True)
        pool = AsyncMock()
        redis = AsyncMock()
        redis.ping = AsyncMock(return_value=True)
        mon = self._make_monitor(db_pool=pool, redis_client=redis, alert_sender=alert)

        # First: postgres fails
        pool.fetchval = AsyncMock(side_effect=Exception("down"))
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            await mon._run_checks_once()

        # Then: postgres recovers
        pool.fetchval = AsyncMock(return_value=1)
        alert.send.reset_mock()
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            await mon._run_checks_once()

        call_args = [c[1] for c in alert.send.call_args_list]
        assert any(ca.get("alert_type") == "HEALTH_RECOVER" for ca in call_args)

    @pytest.mark.asyncio
    async def test_start_creates_task(self):
        mon = self._make_monitor()
        assert mon._task is None
        await mon.start()
        assert mon._task is not None
        await mon.stop()

    @pytest.mark.asyncio
    async def test_stop_cancels_task(self):
        mon = self._make_monitor()
        await mon.start()
        task = mon._task
        await mon.stop()
        assert task.cancelled() or task.done()
