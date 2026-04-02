"""Tests for monitoring/alerts.py — AlertSender with dedup."""
import hashlib
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestAlertSender:

    @pytest.mark.asyncio
    async def test_send_calls_telegram_api(self):
        from neura.monitoring.alerts import AlertSender
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)  # not duplicate
        redis.set = AsyncMock()
        sender = AlertSender(redis, bot_token="123:ABC", group_id=-100, topic_id=8)

        with patch("neura.monitoring.alerts._call_telegram_api") as mock_api:
            mock_api.return_value = True
            result = await sender.send("Test alert", alert_type="TEST")

        assert result is True
        mock_api.assert_called_once()
        call_args = mock_api.call_args
        assert call_args[0][0] == "123:ABC"
        assert "-100" in str(call_args[0][1]) or call_args[0][1] == -100

    @pytest.mark.asyncio
    async def test_send_html_format(self):
        from neura.monitoring.alerts import AlertSender
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncMock()
        sender = AlertSender(redis, bot_token="123:ABC", group_id=-100, topic_id=8)

        with patch("neura.monitoring.alerts._call_telegram_api") as mock_api:
            mock_api.return_value = True
            await sender.send("DB down", alert_type="HEALTH_FAIL", capsule_id="test")

        text_sent = mock_api.call_args[0][3]
        assert "<b>" in text_sent  # HTML bold
        assert "HEALTH_FAIL" in text_sent or "DB down" in text_sent

    @pytest.mark.asyncio
    async def test_dedup_blocks_repeat(self):
        from neura.monitoring.alerts import AlertSender
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=b"1")  # already sent
        sender = AlertSender(redis, bot_token="123:ABC", group_id=-100, topic_id=8)

        with patch("neura.monitoring.alerts._call_telegram_api") as mock_api:
            result = await sender.send("Same error", alert_type="CAPSULE_ERROR")

        assert result is False
        mock_api.assert_not_called()

    @pytest.mark.asyncio
    async def test_dedup_different_alerts_pass(self):
        from neura.monitoring.alerts import AlertSender
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncMock()
        sender = AlertSender(redis, bot_token="123:ABC", group_id=-100, topic_id=8)

        with patch("neura.monitoring.alerts._call_telegram_api") as mock_api:
            mock_api.return_value = True
            r1 = await sender.send("Error A", alert_type="TYPE_A")
            r2 = await sender.send("Error B", alert_type="TYPE_B")

        assert r1 is True
        assert r2 is True
        assert mock_api.call_count == 2

    @pytest.mark.asyncio
    async def test_service_start_not_deduplicated(self):
        from neura.monitoring.alerts import AlertSender, SERVICE_START
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=b"1")  # dedup says duplicate
        redis.set = AsyncMock()
        sender = AlertSender(redis, bot_token="123:ABC", group_id=-100, topic_id=8)

        with patch("neura.monitoring.alerts._call_telegram_api") as mock_api:
            mock_api.return_value = True
            result = await sender.send("Started", alert_type=SERVICE_START, deduplicate=False)

        assert result is True
        mock_api.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_network_error_no_crash(self):
        from neura.monitoring.alerts import AlertSender
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncMock()
        sender = AlertSender(redis, bot_token="123:ABC", group_id=-100, topic_id=8)

        with patch("neura.monitoring.alerts._call_telegram_api") as mock_api:
            mock_api.side_effect = Exception("Network error")
            result = await sender.send("Alert", alert_type="TEST")

        assert result is False  # failed but no exception propagated

    @pytest.mark.asyncio
    async def test_send_returns_false_on_dedup(self):
        from neura.monitoring.alerts import AlertSender
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=b"1")
        sender = AlertSender(redis, bot_token="123:ABC", group_id=-100, topic_id=8)

        result = await sender.send("Dup", alert_type="SAME")
        assert result is False

    def test_dedup_key_deterministic(self):
        from neura.monitoring.alerts import AlertSender
        redis = AsyncMock()
        sender = AlertSender(redis, bot_token="t", group_id=-1, topic_id=8)
        k1 = sender._make_dedup_key("TYPE", "cap1", "error")
        k2 = sender._make_dedup_key("TYPE", "cap1", "error")
        assert k1 == k2

    def test_dedup_key_different_for_different_capsules(self):
        from neura.monitoring.alerts import AlertSender
        redis = AsyncMock()
        sender = AlertSender(redis, bot_token="t", group_id=-1, topic_id=8)
        k1 = sender._make_dedup_key("TYPE", "cap1", "error")
        k2 = sender._make_dedup_key("TYPE", "cap2", "error")
        assert k1 != k2

    def test_alert_type_constants_exist(self):
        from neura.monitoring.alerts import (
            SERVICE_START, SERVICE_STOP, HEALTH_FAIL,
            CAPSULE_ERROR, RATE_WARN,
        )
        assert all(isinstance(c, str) for c in [
            SERVICE_START, SERVICE_STOP, HEALTH_FAIL,
            CAPSULE_ERROR, RATE_WARN,
        ])

    @pytest.mark.asyncio
    async def test_dedup_sets_redis_key_with_ttl(self):
        from neura.monitoring.alerts import AlertSender
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncMock()
        sender = AlertSender(redis, bot_token="123:ABC", group_id=-100,
                             topic_id=8, dedup_ttl=600)

        with patch("neura.monitoring.alerts._call_telegram_api") as mock_api:
            mock_api.return_value = True
            await sender.send("Alert", alert_type="TEST")

        redis.set.assert_called_once()
        call_kwargs = redis.set.call_args
        # Check TTL is set (ex parameter)
        assert call_kwargs[1].get("ex") == 600 or call_kwargs[0][-1] == 600

    @pytest.mark.asyncio
    async def test_redis_down_still_sends_alert(self):
        from neura.monitoring.alerts import AlertSender
        redis = AsyncMock()
        redis.get = AsyncMock(side_effect=Exception("Redis down"))
        redis.set = AsyncMock()
        sender = AlertSender(redis, bot_token="123:ABC", group_id=-100, topic_id=8)

        with patch("neura.monitoring.alerts._call_telegram_api") as mock_api:
            mock_api.return_value = True
            result = await sender.send("Critical", alert_type="HEALTH_FAIL")

        # Should still send — better duplicate than missed alert
        assert result is True
        mock_api.assert_called_once()
