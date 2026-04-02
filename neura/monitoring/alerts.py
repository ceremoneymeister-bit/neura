"""Alert sender — sends Telegram alerts to HQ group with deduplication.

Sends to HQ group topic 8 (infra) via Telegram Bot API.
Deduplication via Redis keys with configurable TTL.
"""
import asyncio
import hashlib
import json
import logging
import urllib.parse
import urllib.request
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Alert type constants
SERVICE_START = "SERVICE_START"
SERVICE_STOP = "SERVICE_STOP"
HEALTH_FAIL = "HEALTH_FAIL"
HEALTH_RECOVER = "HEALTH_RECOVER"
CAPSULE_ERROR = "CAPSULE_ERROR"
RATE_WARN = "RATE_WARN"

_EMOJI = {
    SERVICE_START: "🟢",
    SERVICE_STOP: "🔴",
    HEALTH_FAIL: "🚨",
    HEALTH_RECOVER: "✅",
    CAPSULE_ERROR: "⚠️",
    RATE_WARN: "📊",
}


def _call_telegram_api(bot_token: str, group_id: int, topic_id: int,
                        text: str) -> bool:
    """Synchronous Telegram Bot API call (sendMessage). Runs in executor."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": group_id,
        "message_thread_id": topic_id,
        "text": text,
        "parse_mode": "HTML",
    }).encode()

    req = urllib.request.Request(url, data=data)
    resp = urllib.request.urlopen(req, timeout=10)
    result = json.loads(resp.read())
    return bool(result.get("ok"))


class AlertSender:
    """Send alerts to HQ Telegram group with Redis-based deduplication."""

    def __init__(self, redis_client, bot_token: str, group_id: int,
                 topic_id: int = 8, dedup_ttl: int = 300):
        self._redis = redis_client
        self._bot_token = bot_token
        self._group_id = group_id
        self._topic_id = topic_id
        self._dedup_ttl = dedup_ttl

    async def send(self, text: str, alert_type: str = "",
                   capsule_id: str = "", deduplicate: bool = True) -> bool:
        """Send alert to HQ. Returns True if sent, False if deduplicated or failed."""
        # Dedup check
        if deduplicate:
            dedup_key = self._make_dedup_key(alert_type, capsule_id, text)
            try:
                existing = await self._redis.get(dedup_key)
                if existing:
                    return False
            except Exception:
                pass  # Redis down — send anyway (better dup than missed)

        # Format message
        emoji = _EMOJI.get(alert_type, "ℹ️")
        now = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
        cap_label = f" [{capsule_id}]" if capsule_id else ""
        html = f"<b>[NEURA-V2]</b> {emoji} {alert_type}{cap_label}\n{text}\n<i>{now}</i>"

        # Send
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None, _call_telegram_api,
                self._bot_token, self._group_id, self._topic_id, html,
            )
        except Exception as e:
            logger.error(f"Alert send failed: {e}")
            return False

        # Set dedup key
        if deduplicate:
            try:
                await self._redis.set(dedup_key, "1", ex=self._dedup_ttl)
            except Exception:
                pass

        logger.info(f"Alert sent: {alert_type} {capsule_id}")
        return True

    def _make_dedup_key(self, alert_type: str, capsule_id: str,
                        text: str) -> str:
        """Deterministic hash for deduplication."""
        raw = f"{alert_type}:{capsule_id}:{text}"
        h = hashlib.md5(raw.encode()).hexdigest()[:12]
        return f"neura:alert:dedup:{h}"
