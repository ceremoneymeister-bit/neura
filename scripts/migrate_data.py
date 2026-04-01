"""v1 → v2 data migration — reads capsule files, writes to PostgreSQL.

Usage:
    python3 scripts/migrate_data.py --capsule nikita --source /srv/capsules/nikita_maltsev
    python3 scripts/migrate_data.py --all --source-dir /srv/capsules

Only READS from v1 files. Never modifies production data.
"""
import argparse
import asyncio
import json
import logging
import os
import re
import sys
from datetime import date, time
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from neura.core.memory import DiaryEntry

logger = logging.getLogger(__name__)

# Regex patterns for v1 formats
DIARY_ENTRY_RE = re.compile(
    r"^###\s+(\d{2}:\d{2})\s+\[(\w+)(?::\w*)?\]",
)
LEARNING_RE = re.compile(
    r"^-\s+\[(\d{4}-\d{2}-\d{2})\s+\d{2}:\d{2}\]\s+(.+)",
)


class DataMigrator:
    """Migrates v1 capsule data (files) to v2 (PostgreSQL)."""

    def __init__(self, pool):
        self._pool = pool

    def parse_diary_file(self, filepath: str, capsule_id: str) -> list[DiaryEntry]:
        """Parse a v1 diary markdown file into DiaryEntry list."""
        path = Path(filepath)
        if not path.exists():
            return []

        content = path.read_text(encoding="utf-8").strip()
        if not content:
            return []

        # Extract date from filename (YYYY-MM-DD.md)
        file_date = path.stem  # "2026-04-01"

        entries = []
        current_time = ""
        current_source = "telegram"
        current_user = ""
        current_bot = ""
        state = "idle"  # idle → user → bot

        for line in content.split("\n"):
            header = DIARY_ENTRY_RE.match(line)
            if header:
                # Save previous entry if exists
                if current_time and (current_user or current_bot):
                    entries.append(DiaryEntry(
                        capsule_id=capsule_id,
                        date=file_date,
                        time=current_time,
                        user_message=current_user.strip(),
                        bot_response=current_bot.strip(),
                        source=current_source,
                    ))
                current_time = header.group(1)
                current_source = header.group(2)
                current_user = ""
                current_bot = ""
                state = "idle"
            elif line.startswith("**Пользователь:**"):
                current_user = line.replace("**Пользователь:**", "").strip()
                state = "user"
            elif line.startswith("**Ассистент:**"):
                current_bot = line.replace("**Ассистент:**", "").strip()
                state = "bot"
            elif state == "user" and line.strip():
                current_user += " " + line.strip()
            elif state == "bot" and line.strip():
                current_bot += " " + line.strip()

        # Last entry
        if current_time and (current_user or current_bot):
            entries.append(DiaryEntry(
                capsule_id=capsule_id,
                date=file_date,
                time=current_time,
                user_message=current_user.strip(),
                bot_response=current_bot.strip(),
                source=current_source,
            ))

        return entries

    def parse_long_term(self, filepath: str) -> list[dict]:
        """Parse v1 long_term.json."""
        path = Path(filepath)
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "facts" in data:
                return data["facts"]
            return []
        except (json.JSONDecodeError, KeyError):
            return []

    def parse_learnings(self, filepath: str) -> list[tuple[str, str]]:
        """Parse v1 learnings.md or corrections.md. Returns [(date, content)]."""
        path = Path(filepath)
        if not path.exists():
            return []
        entries = []
        for line in path.read_text(encoding="utf-8").split("\n"):
            match = LEARNING_RE.match(line.strip())
            if match:
                entries.append((match.group(1), match.group(2)))
        return entries

    async def migrate_capsule(self, capsule_id: str, source_dir: str) -> dict:
        """Migrate all data for one capsule. Returns counts."""
        source = Path(source_dir)
        counts = {"diary": 0, "memory": 0, "learnings": 0, "corrections": 0}

        # Diary
        diary_dir = source / "memory" / "diary"
        if diary_dir.exists():
            for md_file in sorted(diary_dir.glob("*.md")):
                entries = self.parse_diary_file(str(md_file), capsule_id)
                for entry in entries:
                    d = date.fromisoformat(entry.date) if isinstance(entry.date, str) else entry.date
                    t = time.fromisoformat(entry.time) if isinstance(entry.time, str) else entry.time
                    # Check for duplicate before insert (idempotent)
                    exists = await self._pool.fetchval(
                        """SELECT id FROM diary WHERE capsule_id = $1
                           AND date = $2 AND time = $3 AND user_message = $4""",
                        capsule_id, d, t, entry.user_message,
                    )
                    if exists:
                        continue
                    await self._pool.fetchval(
                        """INSERT INTO diary (capsule_id, date, time, source,
                           user_message, bot_response, model, duration_sec, tools_used)
                           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                           RETURNING id""",
                        capsule_id, d, t, entry.source,
                        entry.user_message, entry.bot_response, "sonnet", 0, [],
                    )
                    counts["diary"] += 1

        # Long-term memory
        lt_file = source / "memory" / "long_term.json"
        if lt_file.exists():
            entries = self.parse_long_term(str(lt_file))
            for entry in entries:
                text = entry.get("text", "")
                if not text:
                    logger.warning(f"Skipping long_term entry without 'text': {entry.get('ts', '?')}")
                    continue
                if text:
                    await self._pool.fetchval(
                        """INSERT INTO memory (capsule_id, content, source)
                           VALUES ($1, $2, $3) RETURNING id""",
                        capsule_id, text, "v1_migration",
                    )
                    counts["memory"] += 1

        # Learnings
        learn_file = source / "memory" / "learnings.md"
        if learn_file.exists():
            for dt, content in self.parse_learnings(str(learn_file)):
                await self._pool.fetchval(
                    """INSERT INTO learnings (capsule_id, type, content)
                       VALUES ($1, 'learning', $2) RETURNING id""",
                    capsule_id, content,
                )
                counts["learnings"] += 1

        # Corrections
        corr_file = source / "memory" / "corrections.md"
        if corr_file.exists():
            for dt, content in self.parse_learnings(str(corr_file)):
                await self._pool.fetchval(
                    """INSERT INTO learnings (capsule_id, type, content)
                       VALUES ($1, 'correction', $2) RETURNING id""",
                    capsule_id, content,
                )
                counts["corrections"] += 1

        logger.info(f"Migrated {capsule_id}: {counts}")
        return counts


async def main():
    parser = argparse.ArgumentParser(description="Migrate v1 capsule data to v2 PostgreSQL")
    parser.add_argument("--capsule", help="Capsule ID to migrate")
    parser.add_argument("--source", help="Path to v1 capsule directory")
    args = parser.parse_args()

    if not args.capsule or not args.source:
        parser.error("--capsule and --source are required")

    import asyncpg
    dsn = os.environ.get("DATABASE_URL", "postgresql://neura:neura@localhost:5432/neura")
    pool = await asyncpg.create_pool(dsn)

    migrator = DataMigrator(pool)
    result = await migrator.migrate_capsule(args.capsule, args.source)
    print(f"Migration complete: {result}")

    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
