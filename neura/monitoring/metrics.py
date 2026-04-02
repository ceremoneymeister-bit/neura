"""Per-capsule metrics collector — Redis counters with daily TTL.

Tracks request count, error count, latency, and error types per capsule.
"""
import logging
from datetime import date

logger = logging.getLogger(__name__)

DAY_TTL = 86400  # 24 hours


class MetricsCollector:
    """Collects per-capsule request metrics in Redis."""

    def __init__(self, redis_client):
        self._redis = redis_client

    def _keys(self, capsule_id: str) -> dict[str, str]:
        """Generate Redis key names for a capsule (today's date)."""
        d = date.today().isoformat()
        prefix = f"neura:metrics:{capsule_id}"
        return {
            "requests": f"{prefix}:requests:{d}",
            "errors": f"{prefix}:errors:{d}",
            "latency_sum": f"{prefix}:latency_sum:{d}",
            "error_types": f"{prefix}:error_types:{d}",
        }

    async def record_request(self, capsule_id: str, duration_sec: float,
                             success: bool,
                             error_type: str | None = None) -> None:
        """Record a completed request. Increments counters, updates latency."""
        keys = self._keys(capsule_id)
        try:
            await self._redis.incr(keys["requests"])
            await self._redis.incrbyfloat(keys["latency_sum"], duration_sec)
            await self._redis.expire(keys["requests"], DAY_TTL)
            await self._redis.expire(keys["latency_sum"], DAY_TTL)

            if not success:
                await self._redis.incr(keys["errors"])
                await self._redis.expire(keys["errors"], DAY_TTL)
                if error_type:
                    await self._redis.hincrby(keys["error_types"], error_type, 1)
                    await self._redis.expire(keys["error_types"], DAY_TTL)
        except Exception as e:
            logger.warning(f"Metrics record failed: {e}")

    async def get_capsule_stats(self, capsule_id: str) -> dict:
        """Get current stats for a capsule."""
        keys = self._keys(capsule_id)
        try:
            raw_req = await self._redis.get(keys["requests"])
            raw_err = await self._redis.get(keys["errors"])
            raw_lat = await self._redis.get(keys["latency_sum"])
            raw_types = await self._redis.hgetall(keys["error_types"])

            requests = int(raw_req) if raw_req else 0
            errors = int(raw_err) if raw_err else 0
            latency_sum = float(raw_lat) if raw_lat else 0.0
            error_types = {
                k.decode() if isinstance(k, bytes) else k:
                int(v) for k, v in raw_types.items()
            } if raw_types else {}

            return {
                "requests": requests,
                "errors": errors,
                "avg_latency": round(latency_sum / requests, 2) if requests else 0.0,
                "error_types": error_types,
            }
        except Exception as e:
            logger.warning(f"Metrics get failed: {e}")
            return {"requests": 0, "errors": 0, "avg_latency": 0.0, "error_types": {}}

    async def get_all_stats(self, capsule_ids: list[str]) -> dict[str, dict]:
        """Get stats for all capsules."""
        return {cid: await self.get_capsule_stats(cid) for cid in capsule_ids}
