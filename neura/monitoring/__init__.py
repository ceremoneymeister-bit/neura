"""Neura v2 Monitoring — health checks, metrics, alerts.

Usage in app.py:
    monitoring = await setup_monitoring(db.pool, cache.redis, capsules)
    await monitoring["health"].start()
"""
from neura.monitoring.alerts import AlertSender, SERVICE_START, SERVICE_STOP
from neura.monitoring.health import HealthMonitor, HealthStatus
from neura.monitoring.metrics import MetricsCollector

# HQ bot for system alerts
DEFAULT_HQ_BOT_TOKEN = "8674618358:AAHINXfvxnungqyUnmNwh8UEIPKjBaDnifY"
DEFAULT_HQ_GROUP_ID = -1003417427556


async def setup_monitoring(db_pool, redis_client, capsules: dict) -> dict:
    """Factory: create and wire all monitoring components."""
    alert_sender = AlertSender(
        redis_client,
        bot_token=DEFAULT_HQ_BOT_TOKEN,
        group_id=DEFAULT_HQ_GROUP_ID,
        topic_id=8,
    )
    metrics = MetricsCollector(redis_client)
    health = HealthMonitor(
        db_pool=db_pool,
        redis_client=redis_client,
        capsules=capsules,
        alert_sender=alert_sender,
    )
    return {
        "alert_sender": alert_sender,
        "metrics": metrics,
        "health": health,
    }
