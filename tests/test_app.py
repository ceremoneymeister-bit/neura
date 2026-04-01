"""Tests for transport/app.py — application entry point.

Written BEFORE implementation (TDD Red Phase).
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestMain:
    @pytest.mark.asyncio
    @patch("neura.transport.app.TelegramTransport")
    @patch("neura.transport.app.Capsule")
    @patch("neura.transport.app.Cache")
    @patch("neura.transport.app.Database")
    @patch("neura.transport.app.ClaudeEngine")
    async def test_initializes_all_services(self, mock_engine_cls, mock_db_cls,
                                            mock_cache_cls, mock_capsule_cls,
                                            mock_transport_cls):
        from neura.transport.app import create_app

        mock_db = AsyncMock()
        mock_pool = AsyncMock()
        mock_db.pool = mock_pool
        mock_db_cls.return_value = mock_db

        mock_cache = AsyncMock()
        mock_cache.redis = MagicMock()
        mock_cache_cls.return_value = mock_cache

        mock_engine = MagicMock()
        mock_engine_cls.return_value = mock_engine

        cap = MagicMock()
        cap.config.id = "t"
        cap.config.name = "T"
        mock_capsule_cls.load_all.return_value = {"t": cap}

        mock_transport = AsyncMock()
        mock_transport_cls.return_value = mock_transport

        app = await create_app(config_dir="/tmp/test_capsules")

        mock_db.connect.assert_called_once()
        mock_db.run_migrations.assert_called_once()
        mock_cache.connect.assert_called_once()
        assert app["transport"] is mock_transport
        assert app["db"] is mock_db
        assert app["cache"] is mock_cache

    @pytest.mark.asyncio
    @patch("neura.transport.app.Capsule")
    @patch("neura.transport.app.Cache")
    @patch("neura.transport.app.Database")
    @patch("neura.transport.app.ClaudeEngine")
    async def test_no_capsules_raises(self, mock_engine_cls, mock_db_cls,
                                      mock_cache_cls, mock_capsule_cls):
        from neura.transport.app import create_app

        mock_db = AsyncMock()
        mock_db.pool = MagicMock()
        mock_db_cls.return_value = mock_db

        mock_cache = AsyncMock()
        mock_cache.redis = MagicMock()
        mock_cache_cls.return_value = mock_cache

        mock_engine_cls.return_value = MagicMock()
        mock_capsule_cls.load_all.return_value = {}  # No capsules

        with pytest.raises(SystemExit):
            await create_app(config_dir="/tmp/empty")

    @pytest.mark.asyncio
    async def test_shutdown_order(self):
        """Shutdown must stop transport → cache → db."""
        from neura.transport.app import shutdown

        transport = AsyncMock()
        cache = AsyncMock()
        db = AsyncMock()

        app = {"transport": transport, "cache": cache, "db": db}
        await shutdown(app)

        transport.stop.assert_called_once()
        cache.disconnect.assert_called_once()
        db.disconnect.assert_called_once()

    @pytest.mark.asyncio
    @patch("neura.transport.app.TelegramTransport")
    @patch("neura.transport.app.Capsule")
    @patch("neura.transport.app.Cache")
    @patch("neura.transport.app.Database")
    @patch("neura.transport.app.ClaudeEngine")
    async def test_capsules_registered_in_db(self, mock_engine_cls, mock_db_cls,
                                             mock_cache_cls, mock_capsule_cls,
                                             mock_transport_cls):
        from neura.transport.app import create_app

        mock_db = AsyncMock()
        mock_pool = AsyncMock()
        mock_db.pool = mock_pool
        mock_db_cls.return_value = mock_db

        mock_cache = AsyncMock()
        mock_cache.redis = MagicMock()
        mock_cache_cls.return_value = mock_cache

        mock_engine_cls.return_value = MagicMock()

        cap = MagicMock()
        cap.config.id = "test_cap"
        cap.config.name = "Test"
        mock_capsule_cls.load_all.return_value = {"test_cap": cap}

        mock_transport_cls.return_value = AsyncMock()

        await create_app(config_dir="/tmp/test")

        # Pool.execute should be called for capsule upsert
        mock_pool.execute.assert_called()
