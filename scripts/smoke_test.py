"""Smoke test — end-to-end pipeline verification.

Tests the REAL pipeline: capsule → queue → memory → context → engine.
Requires: Docker (postgres + redis) running, Claude CLI installed.

Usage: python3 scripts/smoke_test.py [--capsule dmitry]
"""
import asyncio
import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ.setdefault("DATABASE_URL", "postgresql://neura:neura_v2_s3cure_2026@localhost:5432/neura")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

PASS = "✅"
FAIL = "❌"
SKIP = "⏭️"


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--capsule", default="dmitry")
    parser.add_argument("--skip-claude", action="store_true", help="Skip real Claude CLI call")
    args = parser.parse_args()

    results = []
    config_dir = str(Path(__file__).parent.parent / "config" / "capsules")
    skills_dir = "/root/Antigravity/.agent/skills"

    print(f"\n🧪 Neura v2 Smoke Test — capsule: {args.capsule}\n")

    # --- Test 1: Capsule loading ---
    try:
        from neura.core.capsule import Capsule
        capsule = Capsule.load(args.capsule, config_dir=config_dir)
        assert capsule.config.id == f"{args.capsule}_rostovcev" or capsule.config.id == args.capsule
        results.append((PASS, "Capsule loaded", f"id={capsule.config.id}, model={capsule.config.model}"))
    except Exception as e:
        results.append((FAIL, "Capsule loading", str(e)))
        print_results(results)
        return

    # --- Test 2: System prompt ---
    try:
        prompt = capsule.get_system_prompt()
        assert len(prompt) > 10, "System prompt too short"
        results.append((PASS, "System prompt", f"{len(prompt)} chars"))
    except Exception as e:
        results.append((FAIL, "System prompt", str(e)))

    # --- Test 3: Engine config ---
    try:
        from neura.core.engine import ClaudeEngine
        ecfg = capsule.get_engine_config()
        engine = ClaudeEngine()
        cmd = engine._build_cmd("test", ecfg)
        assert "claude" in cmd
        results.append((PASS, "Engine config", f"model={ecfg.model}, tools={len(ecfg.allowed_tools)}"))
    except Exception as e:
        results.append((FAIL, "Engine config", str(e)))

    # --- Test 4: PostgreSQL connection ---
    try:
        from neura.storage.db import Database
        db = Database()
        await db.connect()
        row = await db.pool.fetchval("SELECT 1")
        assert row == 1
        results.append((PASS, "PostgreSQL", "connected, SELECT 1 = OK"))
    except Exception as e:
        results.append((FAIL, "PostgreSQL", str(e)))
        print_results(results)
        return

    # --- Test 5: Register capsule in DB ---
    try:
        await db.pool.execute(
            """INSERT INTO capsules (id, name) VALUES ($1, $2)
               ON CONFLICT (id) DO UPDATE SET name = $2""",
            capsule.config.id, capsule.config.name,
        )
        results.append((PASS, "Capsule registered in DB", capsule.config.id))
    except Exception as e:
        results.append((FAIL, "Capsule DB registration", str(e)))

    # --- Test 6: Memory store ---
    try:
        from neura.core.memory import MemoryStore, DiaryEntry
        store = MemoryStore(db.pool)
        entry = DiaryEntry(
            capsule_id=capsule.config.id,
            date="2026-04-01", time="13:00",
            user_message="Smoke test message",
            bot_response="Smoke test response",
        )
        diary_id = await store.add_diary(entry)
        assert diary_id is not None
        today = await store.get_today_diary(capsule.config.id)
        assert len(today) >= 1
        results.append((PASS, "Memory store", f"diary_id={diary_id}, today={len(today)} entries"))
    except Exception as e:
        results.append((FAIL, "Memory store", str(e)))

    # --- Test 7: Redis connection ---
    try:
        from neura.storage.cache import Cache
        cache = Cache()
        await cache.connect()
        await cache.redis.set("neura:smoke_test", "ok", ex=60)
        val = await cache.redis.get("neura:smoke_test")
        assert val == "ok"
        results.append((PASS, "Redis", "connected, SET/GET = OK"))
    except Exception as e:
        results.append((FAIL, "Redis", str(e)))
        print_results(results)
        return

    # --- Test 8: Queue ---
    try:
        from neura.core.queue import RequestQueue
        queue = RequestQueue(cache.redis)
        assert await queue.is_processing(capsule.config.id) is False
        rate = await queue.check_rate_limit(capsule.config.id, 500)
        assert rate is None  # OK
        results.append((PASS, "Queue", "processing=false, rate=OK"))
    except Exception as e:
        results.append((FAIL, "Queue", str(e)))

    # --- Test 9: Context builder ---
    try:
        from neura.core.context import ContextBuilder
        parts = await store.build_context_parts(capsule, "smoke test query")
        builder = ContextBuilder(capsule)
        full_prompt = builder.build("smoke test query", parts, is_first_message=True)
        assert "smoke test query" in full_prompt
        assert len(full_prompt) > 100
        results.append((PASS, "Context builder", f"{len(full_prompt)} chars prompt"))
    except Exception as e:
        results.append((FAIL, "Context builder", str(e)))

    # --- Test 10: Skills ---
    try:
        from neura.core.skills import SkillRegistry
        reg = SkillRegistry(skills_dir=skills_dir)
        reg.scan()
        capsule_skills = reg.get_for_capsule(capsule.config.skills)
        results.append((PASS, "Skills", f"{len(reg._skills)} total, {len(capsule_skills)} for capsule"))
    except Exception as e:
        results.append((FAIL, "Skills", str(e)))

    # --- Test 11: Real Claude CLI call ---
    if args.skip_claude:
        results.append((SKIP, "Claude CLI", "skipped with --skip-claude"))
    else:
        try:
            start = time.monotonic()
            result = await engine.execute(
                "Ответь одним словом: работает?",
                ecfg,
            )
            duration = time.monotonic() - start
            assert result.success, f"Claude failed: {result.text}"
            assert len(result.text) > 0
            results.append((PASS, "Claude CLI", f"'{result.text[:50]}' ({duration:.1f}s)"))
        except Exception as e:
            results.append((FAIL, "Claude CLI", str(e)))

    # Cleanup
    await cache.disconnect()
    await db.disconnect()

    print_results(results)


def print_results(results):
    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТЫ SMOKE TEST")
    print("=" * 60)
    passed = sum(1 for r in results if r[0] == PASS)
    failed = sum(1 for r in results if r[0] == FAIL)
    for status, name, detail in results:
        print(f"  {status} {name}: {detail}")
    print("=" * 60)
    print(f"  {passed} passed, {failed} failed, {len(results)} total")
    if failed == 0:
        print("\n  🎉 ALL SYSTEMS GO — Phase 0.5 complete!\n")
    else:
        print(f"\n  ⚠️ {failed} FAILURES — fix before proceeding\n")


if __name__ == "__main__":
    asyncio.run(main())
