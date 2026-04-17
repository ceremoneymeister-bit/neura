"""Per-capsule metrics collector — Redis counters with daily TTL.

Tracks request count, error count, latency, engine usage, and token costs per capsule.
"""
import logging
from datetime import date

logger = logging.getLogger(__name__)

DAY_TTL = 86400  # 24 hours
MONTH_TTL = 86400 * 31  # 31 days


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
            # Engine tracking
            "engine_usage": f"{prefix}:engine:{d}",  # hash: engine_name -> count
            "tokens_in": f"{prefix}:tokens_in:{d}",
            "tokens_out": f"{prefix}:tokens_out:{d}",
            "cost_usd": f"{prefix}:cost_usd:{d}",
        }

    def _month_keys(self, capsule_id: str) -> dict[str, str]:
        """Monthly aggregate keys."""
        m = date.today().strftime("%Y-%m")
        prefix = f"neura:metrics:{capsule_id}"
        return {
            "tokens_in": f"{prefix}:tokens_in_m:{m}",
            "tokens_out": f"{prefix}:tokens_out_m:{m}",
            "cost_usd": f"{prefix}:cost_usd_m:{m}",
            "requests": f"{prefix}:requests_m:{m}",
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

    async def record_engine_usage(self, capsule_id: str, engine_name: str,
                                  tokens_in: int = 0, tokens_out: int = 0,
                                  cost_usd: float = 0.0) -> None:
        """Record which engine was used and token consumption."""
        keys = self._keys(capsule_id)
        mkeys = self._month_keys(capsule_id)
        try:
            # Daily engine counter
            await self._redis.hincrby(keys["engine_usage"], engine_name, 1)
            await self._redis.expire(keys["engine_usage"], DAY_TTL)

            # Daily tokens
            if tokens_in:
                await self._redis.incrbyfloat(keys["tokens_in"], tokens_in)
                await self._redis.expire(keys["tokens_in"], DAY_TTL)
                await self._redis.incrbyfloat(mkeys["tokens_in"], tokens_in)
                await self._redis.expire(mkeys["tokens_in"], MONTH_TTL)
            if tokens_out:
                await self._redis.incrbyfloat(keys["tokens_out"], tokens_out)
                await self._redis.expire(keys["tokens_out"], DAY_TTL)
                await self._redis.incrbyfloat(mkeys["tokens_out"], tokens_out)
                await self._redis.expire(mkeys["tokens_out"], MONTH_TTL)

            # Cost
            if cost_usd:
                await self._redis.incrbyfloat(keys["cost_usd"], cost_usd)
                await self._redis.expire(keys["cost_usd"], DAY_TTL)
                await self._redis.incrbyfloat(mkeys["cost_usd"], cost_usd)
                await self._redis.expire(mkeys["cost_usd"], MONTH_TTL)

            # Monthly request count
            await self._redis.incr(mkeys["requests"])
            await self._redis.expire(mkeys["requests"], MONTH_TTL)

            logger.info(
                f"[{capsule_id}] engine={engine_name} "
                f"tokens={tokens_in}in/{tokens_out}out cost=${cost_usd:.4f}"
            )
        except Exception as e:
            logger.warning(f"Engine metrics record failed: {e}")

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

            # Engine/token stats
            raw_engines = await self._redis.hgetall(keys["engine_usage"])
            raw_tin = await self._redis.get(keys["tokens_in"])
            raw_tout = await self._redis.get(keys["tokens_out"])
            raw_cost = await self._redis.get(keys["cost_usd"])

            engine_usage = {
                (k.decode() if isinstance(k, bytes) else k): int(v)
                for k, v in raw_engines.items()
            } if raw_engines else {}

            # Monthly stats
            mkeys = self._month_keys(capsule_id)
            raw_mcost = await self._redis.get(mkeys["cost_usd"])
            raw_mreq = await self._redis.get(mkeys["requests"])

            return {
                "requests": requests,
                "errors": errors,
                "avg_latency": round(latency_sum / requests, 2) if requests else 0.0,
                "error_types": error_types,
                "engine_usage": engine_usage,
                "tokens_in": int(float(raw_tin)) if raw_tin else 0,
                "tokens_out": int(float(raw_tout)) if raw_tout else 0,
                "cost_usd_today": round(float(raw_cost), 4) if raw_cost else 0.0,
                "cost_usd_month": round(float(raw_mcost), 4) if raw_mcost else 0.0,
                "requests_month": int(raw_mreq) if raw_mreq else 0,
            }
        except Exception as e:
            logger.warning(f"Metrics get failed: {e}")
            return {"requests": 0, "errors": 0, "avg_latency": 0.0, "error_types": {},
                    "engine_usage": {}, "tokens_in": 0, "tokens_out": 0,
                    "cost_usd_today": 0.0, "cost_usd_month": 0.0, "requests_month": 0}

    async def get_all_stats(self, capsule_ids: list[str]) -> dict[str, dict]:
        """Get stats for all capsules."""
        return {cid: await self.get_capsule_stats(cid) for cid in capsule_ids}
