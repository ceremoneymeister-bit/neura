"""Neura v2 — Application entry point.

@arch scope=platform  affects=all_capsules(14)
@arch depends=ALL core modules, ALL transport modules
@arch risk=CRITICAL  restart=neura-v2
@arch role=Single entry point. Initializes DB, Redis, Engine, Memory, Queue, Transport.
@arch note=SIGTERM/SIGINT graceful shutdown. Start order matters (DB→Redis→Engine→Transport).

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
from neura.core.opencode_engine import OpenCodeEngine
from neura.core.yandex_engine import YandexEngine
from neura.core.engine_router import EngineRouter
from neura.core.memory import MemoryStore
from neura.core.queue import RequestQueue
from neura.core.skills import SkillRegistry
from neura.core.skill_learning import SkillUsageCollector, SkillEvolver
from neura.core.heartbeat import HeartbeatEngine, parse_heartbeat_config
from neura.core.proactive import ProactiveEngine
from neura.monitoring import setup_monitoring, SERVICE_START, SERVICE_STOP, HEARTBEAT_FAIL
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

    # 3a. OpenCode engine (fallback)
    opencode_engine = None
    try:
        opencode_engine = OpenCodeEngine()
        logger.info("OpenCode engine initialized (fallback available)")
    except RuntimeError as e:
        logger.warning(f"OpenCode engine not available: {e}")

    # 3b. YandexGPT engine (optional third engine)
    yandex_engine = None
    try:
        ye = YandexEngine()
        if ye.is_available():
            yandex_engine = ye
            logger.info("YandexGPT engine initialized")
        else:
            logger.info("YandexGPT engine not configured (set YANDEX_API_KEY + YANDEX_FOLDER_ID)")
    except Exception as e:
        logger.warning(f"YandexGPT engine not available: {e}")

    # 3c. Engine router (multi-engine with auto-fallback)
    # Note: metrics attached later after monitoring init (step 6)
    engine_router = EngineRouter(
        claude_engine=engine,
        opencode_engine=opencode_engine,
        yandex_engine=yandex_engine,
    )

    memory = MemoryStore(db.pool)
    queue = RequestQueue(cache.redis)

    # 3b. Clear stale processing locks from previous run
    cleared = await queue.clear_all_processing_locks()
    if cleared:
        logger.info(f"Cleared {cleared} stale processing lock(s) from previous run")

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

    # 6a. Attach metrics to engine router for token/cost tracking
    engine_router._metrics = monitoring["metrics"]

    # 6b. Skill learning
    skill_collector = SkillUsageCollector(db.pool)
    skill_evolver = SkillEvolver(skill_collector)
    logger.info("Skill learning engine initialized")

    # 6c. Proactive engine
    proactive_engine = ProactiveEngine(
        skill_registry, db.pool, cache.redis,
        alert_sender=monitoring["alert_sender"],
        metrics_collector=monitoring["metrics"],
        capsules=capsules,
    )

    # 6d. Heartbeat engine (per-capsule periodic reminders)
    async def _heartbeat_send(capsule_id: str, telegram_id: int, message: str):
        """Send heartbeat message via capsule's bot."""
        cap = capsules.get(capsule_id)
        if not cap:
            return
        from telegram import Bot
        bot = Bot(token=cap.config.bot_token)
        try:
            await bot.send_message(chat_id=telegram_id, text=f"💓 {message}")
        except Exception as e:
            logger.warning(f"Heartbeat send failed {capsule_id}→{telegram_id}: {e}")
        finally:
            await bot.shutdown()

    async def _heartbeat_run_task(capsule_id: str, telegram_id: int, task_name: str, prompt: str):
        """Run a prompt through Claude engine and send result to user."""
        cap = capsules.get(capsule_id)
        if not cap:
            return
        from neura.core.context import ContextBuilder
        from neura.core.memory import DiaryEntry
        from datetime import datetime as _dt, timezone as _tz

        try:
            # Build context with diary/memory
            parts = await memory.build_context_parts(cap, prompt)
            builder = ContextBuilder(cap)
            full_prompt = builder.build(prompt, parts, is_first_message=True)

            cfg = cap.get_engine_config()
            # Collect streaming output into a single result
            result_parts = []
            async for chunk in engine.stream(full_prompt, cfg):
                if chunk.text:
                    result_parts.append(chunk.text)
            result = "".join(result_parts)

            # Send result via bot
            from telegram import Bot
            bot = Bot(token=cap.config.bot_token)
            try:
                text = result[:4000] if len(result) > 4000 else result
                await bot.send_message(chat_id=telegram_id, text=f"⚡ {text}")
            finally:
                await bot.shutdown()

            # Write diary
            now = _dt.now(_tz.utc)
            entry = DiaryEntry(
                capsule_id=capsule_id,
                date=now.strftime("%Y-%m-%d"),
                time=now.strftime("%H:%M:%S"),
                source="heartbeat",
                user_message=f"[Автозадача] {prompt[:300]}",
                bot_response=result[:500],
            )
            await memory.add_diary(entry)
            logger.info(f"Heartbeat task done: {capsule_id}/{task_name}, {len(result)} chars")
        except Exception as e:
            logger.error(f"Heartbeat task failed {capsule_id}/{task_name}: {e}", exc_info=True)
            # Alert Dmitry via HQ infra channel
            try:
                await monitoring["alert_sender"].send(
                    f"Задача: <code>{task_name}</code>\n"
                    f"Ошибка: <code>{str(e)[:300]}</code>",
                    alert_type=HEARTBEAT_FAIL,
                    capsule_id=capsule_id,
                    deduplicate=True,
                )
            except Exception:
                pass
            # Also notify the capsule user
            from telegram import Bot
            bot = Bot(token=cap.config.bot_token)
            try:
                await bot.send_message(
                    chat_id=telegram_id,
                    text=f"⚠️ Автозадача не выполнена: {str(e)[:200]}"
                )
            except Exception:
                pass
            finally:
                await bot.shutdown()

    heartbeat_engine = HeartbeatEngine(cache.redis, _heartbeat_send, _heartbeat_run_task)
    for cap in capsules.values():
        if cap.config.heartbeat:
            hb_tasks = parse_heartbeat_config(
                cap.config.id, cap.config.owner_telegram_id,
                cap.config.heartbeat,
            )
            heartbeat_engine.register_tasks(hb_tasks)

    # 7. Transport
    transport = TelegramTransport(
        capsules, engine, memory, queue,
        metrics=monitoring["metrics"],
        alert_sender=monitoring["alert_sender"],
        skill_collector=skill_collector,
        skill_evolver=skill_evolver,
        engine_router=engine_router,
    )
    transport.set_onboarding(cache.redis)

    # 8. Web API (FastAPI + uvicorn)
    web_app = create_web_app(db.pool, engine, memory, queue, capsules)

    return {
        "db": db,
        "cache": cache,
        "engine": engine,
        "opencode_engine": opencode_engine,
        "engine_router": engine_router,
        "memory": memory,
        "queue": queue,
        "capsules": capsules,
        "transport": transport,
        "monitoring": monitoring,
        "proactive": proactive_engine,
        "heartbeat": heartbeat_engine,
        "web_app": web_app,
    }


async def shutdown(app: dict) -> None:
    """Graceful shutdown: monitoring → transport → cache → db."""
    logger.info("Shutting down...")

    # Stop heartbeat engine
    heartbeat = app.get("heartbeat")
    if heartbeat:
        await heartbeat.stop()

    # Stop proactive engine
    proactive = app.get("proactive")
    if proactive:
        await proactive.stop()

    # Stop monitoring
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

    # Preload vector search models in background thread
    # (so first user request doesn't wait 15+ seconds for model load)
    import threading
    def _preload_vector_models():
        try:
            from neura.core.vectordb import _get_model, _get_reranker
            _get_model()
            _get_reranker()
            logger.info("Vector models preloaded")
        except Exception as e:
            logger.warning(f"Vector model preload failed (will retry on first search): {e}")
    threading.Thread(target=_preload_vector_models, daemon=True).start()

    # Start proactive engine
    proactive = app["proactive"]
    await proactive.start()

    # Start heartbeat engine
    heartbeat = app["heartbeat"]
    await heartbeat.start()

    capsule_count = len(app["capsules"])
    await alert_sender.send(
        f"Запущено {capsule_count} капсул(а)",
        alert_type=SERVICE_START,
        deduplicate=True,  # Prevent spam during crash loops / rapid restarts
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
