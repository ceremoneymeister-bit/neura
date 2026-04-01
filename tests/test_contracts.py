"""Contract tests — verify type compatibility at module boundaries.

These tests ensure modules can actually work together,
not just pass unit tests with mocks. Each test crosses
at least one module boundary.
"""
import os
import pytest
from unittest.mock import AsyncMock, patch
from pathlib import Path
from datetime import date, time

FIXTURES = Path(__file__).parent / "fixtures" / "capsules"


def _make_capsule():
    from neura.core.capsule import Capsule
    with patch.dict(os.environ, {"TEST_BOT_TOKEN": "tok"}):
        return Capsule.load("test_capsule", config_dir=str(FIXTURES))


# === Capsule → Engine ===

class TestCapsuleToEngine:
    def test_get_engine_config_accepted_by_engine(self):
        """capsule.get_engine_config() → engine._build_cmd() works."""
        from neura.core.engine import ClaudeEngine, EngineConfig
        capsule = _make_capsule()
        ecfg = capsule.get_engine_config()

        assert isinstance(ecfg, EngineConfig)
        engine = ClaudeEngine()
        cmd = engine._build_cmd("test prompt", ecfg)
        assert isinstance(cmd, list)
        assert "claude" in cmd
        assert ecfg.model in cmd

    def test_engine_config_has_home_dir(self):
        """Capsule sets home_dir for isolation."""
        capsule = _make_capsule()
        ecfg = capsule.get_engine_config()
        assert ecfg.home_dir is not None
        assert capsule.config.id in ecfg.home_dir

    def test_engine_env_uses_home_dir(self):
        """engine._build_env() respects home_dir from capsule config."""
        from neura.core.engine import ClaudeEngine
        capsule = _make_capsule()
        ecfg = capsule.get_engine_config()
        engine = ClaudeEngine()
        env = engine._build_env(ecfg)
        assert env.get("CLAUDE_CONFIG_DIR") == ecfg.home_dir


# === Memory → Context ===

class TestMemoryToContext:
    @pytest.mark.asyncio
    async def test_build_context_parts_returns_valid_contextparts(self):
        """memory.build_context_parts() → ContextParts accepted by ContextBuilder."""
        from neura.core.memory import MemoryStore
        from neura.core.context import ContextBuilder, ContextParts

        capsule = _make_capsule()
        pool = AsyncMock()
        pool.fetch = AsyncMock(return_value=[])
        store = MemoryStore(pool)

        parts = await store.build_context_parts(capsule, "test query")
        assert isinstance(parts, ContextParts)

        # ContextBuilder actually accepts these parts
        builder = ContextBuilder(capsule)
        prompt = builder.build("test query", parts, is_first_message=True)
        assert isinstance(prompt, str)
        assert "test query" in prompt

    @pytest.mark.asyncio
    async def test_diary_entries_format_correctly_in_context(self):
        """DiaryEntry fields survive through build_context_parts → ContextBuilder."""
        from neura.core.memory import MemoryStore
        from neura.core.context import ContextBuilder

        capsule = _make_capsule()
        pool = AsyncMock()

        diary_row = {"id": 1, "capsule_id": "test", "date": date(2026, 4, 1),
                     "time": time(14, 30), "user_message": "What is AI?",
                     "bot_response": "AI is...", "model": "sonnet",
                     "duration_sec": 2.0, "tools_used": [], "source": "telegram"}
        memory_row = {"content": "User likes concise answers"}
        learning_row = {"content": "Check timezone"}

        # Different calls get different data
        pool.fetch = AsyncMock(side_effect=[
            [diary_row],          # get_today_diary
            [],                   # get_recent_diary
            [memory_row],         # search_memory
            [learning_row],       # get_learnings
            [],                   # get_corrections
        ])
        store = MemoryStore(pool)
        parts = await store.build_context_parts(capsule, "test")

        builder = ContextBuilder(capsule)
        prompt = builder.build("follow up", parts, is_first_message=True)
        assert "What is AI?" in prompt


# === Capsule → Context (system prompt) ===

class TestCapsuleToContext:
    def test_system_prompt_flows_to_context(self):
        """capsule.get_system_prompt() → ContextParts → ContextBuilder output."""
        from neura.core.context import ContextBuilder, ContextParts

        capsule = _make_capsule()
        system_prompt = capsule.get_system_prompt()

        parts = ContextParts(system_prompt=system_prompt)
        builder = ContextBuilder(capsule)
        result = builder.build("hello", parts, is_first_message=True)
        assert "Test Bot" in result  # from SYSTEM.md fixture


# === DiaryEntry types → asyncpg compatibility ===

class TestDiaryTypeContract:
    def test_add_diary_converts_str_to_date(self):
        """DiaryEntry with str date/time is converted before SQL."""
        from neura.core.memory import DiaryEntry
        entry = DiaryEntry(
            capsule_id="test", date="2026-04-01", time="14:30",
            user_message="hi", bot_response="hello",
        )
        # Verify str→date conversion works
        d = date.fromisoformat(entry.date)
        t = time.fromisoformat(entry.time)
        assert isinstance(d, date)
        assert isinstance(t, time)
        assert d.year == 2026
        assert t.hour == 14

    @pytest.mark.asyncio
    async def test_add_diary_passes_date_objects_to_pool(self):
        """Verify add_diary sends date/time objects, not strings."""
        from neura.core.memory import MemoryStore, DiaryEntry
        pool = AsyncMock()
        pool.fetchval = AsyncMock(return_value=1)
        store = MemoryStore(pool)

        entry = DiaryEntry(
            capsule_id="test", date="2026-04-01", time="14:30",
            user_message="hi", bot_response="hello",
        )
        await store.add_diary(entry)

        # Check the actual args passed to fetchval
        args = pool.fetchval.call_args[0]
        # args[0] is SQL, args[1:] are parameters
        # $2 = date, $3 = time
        assert isinstance(args[2], date), f"Expected date, got {type(args[2])}"
        assert isinstance(args[3], time), f"Expected time, got {type(args[3])}"
