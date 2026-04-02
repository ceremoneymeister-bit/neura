"""Neura v2 — Application entry point.

Init: DB pool + Redis + Engine + MemoryStore + Queue.
Load capsules from YAML. Start TelegramTransport.
Graceful shutdown on SIGTERM/SIGINT.
"""
import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

from neura.core.capsule import Capsule
from neura.core.engine import ClaudeEngine
from neura.core.memory import MemoryStore
from neura.core.queue import RequestQueue
from neura.core.skills import SkillRegistry
from neura.monitoring import setup_monitoring, SERVICE_START, SERVICE_STOP
from neura.storage.cache import Cache
from neura.storage.db import Database
from neura.transport.telegram import TelegramTransport
from neura.transport.web import create_web_app

logger = logging.getLogger(__name__)


def _load_dotenv() -> None:
    """Load .env file from project root if it exists."""
    env_file = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


async def create_app(config_dir: str = "config/capsules") -> dict:
    """Initialize all services and return app context dict."""

    # 1. Database
    db = Database()
    await db.connect()
    await db.run_migrations()

    # 2. Redis
    cache = Cache()
    await cache.connect()

    # 3. Core services
    engine = ClaudeEngine()
    memory = MemoryStore(db.pool)
    queue = RequestQueue(cache.redis)

    # 4. Load capsules + skills
    capsules = Capsule.load_all(config_dir)
    if not capsules:
        logger.error(f"No capsules found in {config_dir}. Exiting.")
        sys.exit(1)
    logger.info(f"Loaded {len(capsules)} capsule(s): {', '.join(capsules.keys())}")

    # 4b. Load skills and attach to capsules
    skill_registry = SkillRegistry()
    skill_registry.scan()
    for cap in capsules.values():
        cap_skills = skill_registry.get_for_capsule(cap.config.skills)
        cap._skills_table = skill_registry.format_table(cap_skills)
        logger.info(f"  {cap.config.id}: {len(cap_skills)} skills loaded")

    # 5. Register capsules in DB (upsert)
    for cap in capsules.values():
        await db.pool.execute(
            """INSERT INTO capsules (id, name) VALUES ($1, $2)
               ON CONFLICT (id) DO UPDATE SET name = $2""",
            cap.config.id, cap.config.name,
        )

    # 6. Monitoring
    monitoring = await setup_monitoring(db.pool, cache.redis, capsules)

    # 7. Transport
    transport = TelegramTransport(
        capsules, engine, memory, queue,
        metrics=monitoring["metrics"],
        alert_sender=monitoring["alert_sender"],
    )

    # 8. Web API (FastAPI + uvicorn)
    web_app = create_web_app(db.pool, engine, memory, queue, capsules)

    return {
        "db": db,
        "cache": cache,
        "engine": engine,
        "memory": memory,
        "queue": queue,
        "capsules": capsules,
        "transport": transport,
        "monitoring": monitoring,
        "web_app": web_app,
    }


async def shutdown(app: dict) -> None:
    """Graceful shutdown: monitoring → transport → cache → db."""
    logger.info("Shutting down...")

    # Stop monitoring first
    monitoring = app.get("monitoring")
    if monitoring:
        await monitoring["health"].stop()
        try:
            await monitoring["alert_sender"].send(
                "Graceful shutdown",
                alert_type=SERVICE_STOP,
                deduplicate=False,
            )
        except Exception:
            pass

    transport = app.get("transport")
    if transport:
        await transport.stop()

    cache = app.get("cache")
    if cache:
        await cache.disconnect()

    db = app.get("db")
    if db:
        await db.disconnect()

    logger.info("Neura v2 stopped.")


async def main() -> None:
    """Application lifecycle: init → run → shutdown."""
    import uvicorn

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    _load_dotenv()
    app = await create_app()
    transport: TelegramTransport = app["transport"]

    # Signal handling
    stop_event = asyncio.Event()

    def _signal_handler():
        logger.info("Shutdown signal received")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _signal_handler)

    # Start monitoring
    monitoring = app["monitoring"]
    health = monitoring["health"]
    alert_sender = monitoring["alert_sender"]

    await health.start()
    capsule_count = len(app["capsules"])
    await alert_sender.send(
        f"Запущено {capsule_count} капсул(а)",
        alert_type=SERVICE_START,
        deduplicate=False,
    )

    # Start Web API (uvicorn)
    web_port = int(os.environ.get("WEB_PORT", "8080"))
    web_app = app["web_app"]
    uvicorn_config = uvicorn.Config(
        web_app, host="0.0.0.0", port=web_port,
        log_level="info", access_log=False,
    )
    uvicorn_server = uvicorn.Server(uvicorn_config)
    app["uvicorn_server"] = uvicorn_server
    web_task = asyncio.create_task(uvicorn_server.serve())
    logger.info(f"Web API started on port {web_port}")

    # Start Telegram transport
    await transport.start()
    logger.info("Neura v2 running (Telegram + Web). Press Ctrl+C to stop.")

    await stop_event.wait()

    # Shutdown
    uvicorn_server.should_exit = True
    await web_task
    await shutdown(app)


if __name__ == "__main__":
    asyncio.run(main())
