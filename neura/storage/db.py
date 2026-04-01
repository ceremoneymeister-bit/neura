"""PostgreSQL connection management.

Single pool per application, injected into MemoryStore via DI.
DSN from DATABASE_URL env var or explicit parameter.
"""
import os
import logging
from pathlib import Path

import asyncpg

logger = logging.getLogger(__name__)


class Database:
    """Manages asyncpg connection pool and migrations."""

    def __init__(self):
        self._pool: asyncpg.Pool | None = None

    @property
    def pool(self) -> asyncpg.Pool:
        """Get the connection pool. Raises if not connected."""
        if self._pool is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._pool

    async def connect(self, dsn: str | None = None) -> None:
        """Create connection pool.

        Args:
            dsn: PostgreSQL DSN. If None, reads DATABASE_URL from env.
        """
        if dsn is None:
            dsn = os.environ.get("DATABASE_URL")
            if not dsn:
                raise ValueError("No DSN provided and DATABASE_URL not set")

        self._pool = await asyncpg.create_pool(dsn, min_size=2, max_size=10)
        logger.info("Database connected")

    async def disconnect(self) -> None:
        """Close the connection pool."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
            logger.info("Database disconnected")

    async def run_migrations(self, migrations_dir: str = "neura/storage/migrations") -> None:
        """Execute .sql migration files in alphabetical order."""
        pool = self.pool  # raises if not connected
        migrations_path = Path(migrations_dir)

        if not migrations_path.exists():
            logger.warning(f"Migrations directory not found: {migrations_path}")
            return

        for sql_file in sorted(migrations_path.glob("*.sql")):
            sql = sql_file.read_text(encoding="utf-8")
            try:
                await pool.execute(sql)
                logger.info(f"Migration applied: {sql_file.name}")
            except Exception as e:
                logger.error(f"Migration failed: {sql_file.name}: {e}")
                raise
