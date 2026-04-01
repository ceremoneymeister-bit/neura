"""Tests for storage/db.py — PostgreSQL connection management.

TDD Red Phase. asyncpg mocked — no real DB needed.
"""
import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path


class TestConnect:
    @pytest.mark.asyncio
    async def test_connect_creates_pool(self):
        from neura.storage.db import Database
        db = Database()
        mock_pool = AsyncMock()
        with patch("asyncpg.create_pool", new_callable=AsyncMock, return_value=mock_pool):
            await db.connect("postgresql://test:test@localhost/test")
        assert db.pool is mock_pool

    @pytest.mark.asyncio
    async def test_connect_from_env(self):
        from neura.storage.db import Database
        db = Database()
        mock_pool = AsyncMock()
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://env:env@localhost/env"}):
            with patch("asyncpg.create_pool", new_callable=AsyncMock, return_value=mock_pool) as mock_create:
                await db.connect()
        mock_create.assert_called_once()
        assert "env" in str(mock_create.call_args)


class TestDisconnect:
    @pytest.mark.asyncio
    async def test_disconnect_closes_pool(self):
        from neura.storage.db import Database
        db = Database()
        mock_pool = AsyncMock()
        with patch("asyncpg.create_pool", new_callable=AsyncMock, return_value=mock_pool):
            await db.connect("postgresql://test:test@localhost/test")
        await db.disconnect()
        mock_pool.close.assert_called_once()


class TestPoolProperty:
    def test_raises_if_not_connected(self):
        from neura.storage.db import Database
        db = Database()
        with pytest.raises(RuntimeError, match="not connected"):
            _ = db.pool


class TestMigrations:
    @pytest.mark.asyncio
    async def test_run_migrations_executes_sql(self, tmp_path):
        from neura.storage.db import Database
        db = Database()
        mock_pool = AsyncMock()
        mock_pool.execute = AsyncMock()
        with patch("asyncpg.create_pool", new_callable=AsyncMock, return_value=mock_pool):
            await db.connect("postgresql://test:test@localhost/test")

        # Create test migration files
        (tmp_path / "001_initial.sql").write_text("CREATE TABLE test (id INT);")
        (tmp_path / "002_extra.sql").write_text("CREATE TABLE extra (id INT);")

        await db.run_migrations(str(tmp_path))
        assert mock_pool.execute.call_count == 2


class TestLifecycle:
    @pytest.mark.asyncio
    async def test_connect_disconnect_cycle(self):
        from neura.storage.db import Database
        db = Database()
        mock_pool = AsyncMock()
        with patch("asyncpg.create_pool", new_callable=AsyncMock, return_value=mock_pool):
            await db.connect("postgresql://test:test@localhost/test")
            assert db.pool is not None
            await db.disconnect()
        # After disconnect, pool access should raise
        with pytest.raises(RuntimeError):
            _ = db.pool
