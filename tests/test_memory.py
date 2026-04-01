"""Tests for core/memory.py — Memory CRUD (PostgreSQL).

TDD Red Phase. Pool is mocked via AsyncMock.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import date, time


def _mock_pool():
    """Create a mock asyncpg pool."""
    pool = AsyncMock()
    return pool


class TestInit:
    def test_pool_none_raises(self):
        from neura.core.memory import MemoryStore
        with pytest.raises(ValueError, match="pool"):
            MemoryStore(None)


class TestDiary:
    @pytest.mark.asyncio
    async def test_add_diary(self):
        from neura.core.memory import MemoryStore, DiaryEntry
        pool = _mock_pool()
        pool.fetchval = AsyncMock(return_value=1)
        store = MemoryStore(pool)
        entry = DiaryEntry(
            capsule_id="test", date="2026-04-01", time="14:30",
            user_message="Hello", bot_response="Hi there",
        )
        result = await store.add_diary(entry)
        assert result == 1
        pool.fetchval.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_today_diary(self):
        from neura.core.memory import MemoryStore, DiaryEntry
        pool = _mock_pool()
        pool.fetch = AsyncMock(return_value=[
            {"id": 1, "capsule_id": "test", "date": date(2026, 4, 1),
             "time": time(14, 30), "user_message": "Hello",
             "bot_response": "Hi", "model": "sonnet", "duration_sec": 2.0,
             "tools_used": [], "source": "telegram"},
        ])
        store = MemoryStore(pool)
        entries = await store.get_today_diary("test", limit=10)
        assert len(entries) == 1
        assert entries[0].user_message == "Hello"
        assert entries[0].capsule_id == "test"

    @pytest.mark.asyncio
    async def test_get_recent_diary(self):
        from neura.core.memory import MemoryStore
        pool = _mock_pool()
        pool.fetch = AsyncMock(return_value=[
            {"id": 2, "capsule_id": "test", "date": date(2026, 3, 31),
             "time": time(10, 0), "user_message": "Yesterday q",
             "bot_response": "Yesterday a", "model": "sonnet",
             "duration_sec": 1.0, "tools_used": [], "source": "telegram"},
        ])
        store = MemoryStore(pool)
        entries = await store.get_recent_diary("test", days=3, per_day=5)
        assert len(entries) >= 1

    @pytest.mark.asyncio
    async def test_search_diary(self):
        from neura.core.memory import MemoryStore
        pool = _mock_pool()
        pool.fetch = AsyncMock(return_value=[
            {"id": 3, "capsule_id": "test", "date": date(2026, 4, 1),
             "time": time(9, 0), "user_message": "weather forecast",
             "bot_response": "Sunny", "model": "sonnet",
             "duration_sec": 1.5, "tools_used": [], "source": "telegram"},
        ])
        store = MemoryStore(pool)
        entries = await store.search_diary("test", "weather")
        assert len(entries) >= 1


class TestLongTermMemory:
    @pytest.mark.asyncio
    async def test_add_memory(self):
        from neura.core.memory import MemoryStore
        pool = _mock_pool()
        pool.fetchval = AsyncMock(return_value=42)
        store = MemoryStore(pool)
        result = await store.add_memory("test", "User prefers concise answers")
        assert result == 42

    @pytest.mark.asyncio
    async def test_search_memory(self):
        from neura.core.memory import MemoryStore
        pool = _mock_pool()
        pool.fetch = AsyncMock(return_value=[
            {"content": "User prefers concise answers"},
            {"content": "User works in marketing"},
        ])
        store = MemoryStore(pool)
        results = await store.search_memory("test", "concise")
        assert len(results) == 2
        assert "concise" in results[0]


class TestLearnings:
    @pytest.mark.asyncio
    async def test_add_learning(self):
        from neura.core.memory import MemoryStore
        pool = _mock_pool()
        pool.fetchval = AsyncMock(return_value=10)
        store = MemoryStore(pool)
        result = await store.add_learning("test", "Check timezone always")
        assert result == 10

    @pytest.mark.asyncio
    async def test_add_correction(self):
        from neura.core.memory import MemoryStore
        pool = _mock_pool()
        pool.fetchval = AsyncMock(return_value=11)
        store = MemoryStore(pool)
        result = await store.add_correction("test", "Don't use emojis")
        assert result == 11

    @pytest.mark.asyncio
    async def test_get_learnings(self):
        from neura.core.memory import MemoryStore
        pool = _mock_pool()
        pool.fetch = AsyncMock(return_value=[
            {"content": "Learning 1"},
            {"content": "Learning 2"},
        ])
        store = MemoryStore(pool)
        results = await store.get_learnings("test")
        assert len(results) == 2
        assert results[0] == "Learning 1"


class TestBuildContextParts:
    @pytest.mark.asyncio
    async def test_builds_context_parts(self):
        import os
        from unittest.mock import patch
        from pathlib import Path
        from neura.core.memory import MemoryStore
        from neura.core.context import ContextParts
        from neura.core.capsule import Capsule

        fixtures = Path(__file__).parent / "fixtures" / "capsules"
        with patch.dict(os.environ, {"TEST_BOT_TOKEN": "tok"}):
            capsule = Capsule.load("test_capsule", config_dir=str(fixtures))

        pool = _mock_pool()
        # Mock all sub-calls
        pool.fetch = AsyncMock(return_value=[])
        store = MemoryStore(pool)
        parts = await store.build_context_parts(capsule, "test prompt")
        assert isinstance(parts, ContextParts)
