"""Health monitor — periodic background checks with transition alerts.

Checks PostgreSQL, Redis, Claude CLI, and each bot's Telegram token.
Sends alerts on state transitions (healthy→unhealthy, unhealthy→healthy).
"""
import asyncio
import logging
import shutil
import time
from dataclasses import dataclass, field

from neura.monitoring.alerts import AlertSender, HEALTH_FAIL, HEALTH_RECOVER

logger = logging.getLogger(__name__)


@dataclass
class HealthStatus:
    """Result of a single health check."""
    name: str
    healthy: bool
    detail: str = ""
    checked_at: float = 0.0


class HealthMonitor:
    """Background health checker with transition-based alerting."""

    def __init__(self, db_pool, redis_client, capsules: dict,
                 alert_sender: AlertSender, interval: int = 30):
        self._pool = db_pool
        self._redis = redis_client
        self._capsules = capsules
        self._alert = alert_sender
        self._interval = interval
        self._prev_state: dict[str, bool] = {}
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start background health check loop."""
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"Health monitor started (interval={self._interval}s)")

    async def stop(self) -> None:
        """Cancel background task."""
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Health monitor stopped")

    async def check_all(self) -> list[HealthStatus]:
        """Run all checks once."""
        results = [
            await self._check_postgres(),
            await self._check_redis(),
            await self._check_claude_cli(),
        ]
        for cap_id, capsule in self._capsules.items():
            results.append(await self._check_bot(cap_id, capsule))
        return results

    async def _run_loop(self) -> None:
        """Main loop — runs checks every interval seconds."""
        while True:
            try:
                await self._run_checks_once()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
            await asyncio.sleep(self._interval)

    async def _run_checks_once(self) -> None:
        """Run all checks and handle state transitions."""
        results = await self.check_all()
        for status in results:
            prev = self._prev_state.get(status.name)
            if prev is None:
                # First check — alert if unhealthy
                self._prev_state[status.name] = status.healthy
                if not status.healthy:
                    await self._alert.send(
                        f"{status.name}: {status.detail}",
                        alert_type=HEALTH_FAIL,
                        capsule_id=status.name,
                    )
            elif prev is True and not status.healthy:
                # Transition: healthy → unhealthy
                await self._alert.send(
                    f"{status.name}: {status.detail}",
                    alert_type=HEALTH_FAIL,
                    capsule_id=status.name,
                )
                self._prev_state[status.name] = False
            elif prev is False and status.healthy:
                # Transition: unhealthy → healthy
                await self._alert.send(
                    f"{status.name}: recovered",
                    alert_type=HEALTH_RECOVER,
                    capsule_id=status.name,
                    deduplicate=False,
                )
                self._prev_state[status.name] = True

    async def _check_postgres(self) -> HealthStatus:
        """Check PostgreSQL connectivity."""
        try:
            await asyncio.wait_for(self._pool.fetchval("SELECT 1"), timeout=5)
            return HealthStatus("postgres", True, "OK", time.monotonic())
        except Exception as e:
            return HealthStatus("postgres", False, str(e), time.monotonic())

    async def _check_redis(self) -> HealthStatus:
        """Check Redis connectivity."""
        try:
            await asyncio.wait_for(self._redis.ping(), timeout=5)
            return HealthStatus("redis", True, "OK", time.monotonic())
        except Exception as e:
            return HealthStatus("redis", False, str(e), time.monotonic())

    async def _check_claude_cli(self) -> HealthStatus:
        """Check Claude CLI is available."""
        path = shutil.which("claude")
        if path:
            return HealthStatus("claude_cli", True, path, time.monotonic())
        return HealthStatus("claude_cli", False, "not found", time.monotonic())

    async def _check_bot(self, capsule_id: str, capsule) -> HealthStatus:
        """Check Telegram bot token validity via getMe."""
        import urllib.request
        import json

        name = f"bot:{capsule_id}"
        try:
            token = capsule.config.bot_token
            url = f"https://api.telegram.org/bot{token}/getMe"
            loop = asyncio.get_running_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: urllib.request.urlopen(url, timeout=10).read()),
                timeout=15,
            )
            data = json.loads(result)
            if data.get("ok"):
                return HealthStatus(name, True, "OK", time.monotonic())
            return HealthStatus(name, False, "getMe not ok", time.monotonic())
        except Exception as e:
            return HealthStatus(name, False, str(e), time.monotonic())
