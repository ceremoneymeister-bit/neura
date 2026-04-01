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

from neura.core.capsule import Capsule
from neura.core.engine import ClaudeEngine
from neura.core.memory import MemoryStore
from neura.core.queue import RequestQueue
from neura.storage.cache import Cache
from neura.storage.db import Database
from neura.transport.telegram import TelegramTransport

logger = logging.getLogger(__name__)


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

    # 4. Load capsules
    capsules = Capsule.load_all(config_dir)
    if not capsules:
        logger.error(f"No capsules found in {config_dir}. Exiting.")
        sys.exit(1)
    logger.info(f"Loaded {len(capsules)} capsule(s): {', '.join(capsules.keys())}")

    # 5. Register capsules in DB (upsert)
    for cap in capsules.values():
        await db.pool.execute(
            """INSERT INTO capsules (id, name) VALUES ($1, $2)
               ON CONFLICT (id) DO UPDATE SET name = $2""",
            cap.config.id, cap.config.name,
        )

    # 6. Transport
    transport = TelegramTransport(capsules, engine, memory, queue)

    return {
        "db": db,
        "cache": cache,
        "engine": engine,
        "memory": memory,
        "queue": queue,
        "capsules": capsules,
        "transport": transport,
    }


async def shutdown(app: dict) -> None:
    """Graceful shutdown: transport → cache → db."""
    logger.info("Shutting down...")

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
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

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

    # Start
    await transport.start()
    logger.info("Neura v2 running. Press Ctrl+C to stop.")

    await stop_event.wait()

    # Shutdown
    await shutdown(app)


if __name__ == "__main__":
    asyncio.run(main())
