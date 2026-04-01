"""Tests for scripts/migrate_data.py — v1 → v2 data migration.

TDD Red Phase.
"""
import sys
import pytest
from unittest.mock import AsyncMock
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

V1_FIXTURE = str(Path(__file__).parent / "fixtures" / "v1_capsule")


class TestParseDiary:
    def test_parses_markdown_diary(self):
        from migrate_data import DataMigrator
        migrator = DataMigrator(pool=None)
        diary_file = f"{V1_FIXTURE}/memory/diary/2026-04-01.md"
        entries = migrator.parse_diary_file(diary_file, "test_capsule")
        assert len(entries) == 2
        assert entries[0].time == "14:57"
        assert "Привет" in entries[0].user_message
        assert "отлично" in entries[0].bot_response
        assert entries[0].source == "telegram"
        assert entries[1].source == "web"
        assert entries[1].time == "15:30"

    def test_empty_file(self, tmp_path):
        from migrate_data import DataMigrator
        migrator = DataMigrator(pool=None)
        empty = tmp_path / "empty.md"
        empty.write_text("")
        entries = migrator.parse_diary_file(str(empty), "test")
        assert entries == []


class TestParseLongTerm:
    def test_json_array(self):
        from migrate_data import DataMigrator
        migrator = DataMigrator(pool=None)
        lt_file = f"{V1_FIXTURE}/memory/long_term.json"
        entries = migrator.parse_long_term(lt_file)
        assert len(entries) == 2
        assert "контентом" in entries[0]["text"]

    def test_facts_format(self, tmp_path):
        from migrate_data import DataMigrator
        migrator = DataMigrator(pool=None)
        f = tmp_path / "lt.json"
        f.write_text('{"facts": []}')
        entries = migrator.parse_long_term(str(f))
        assert entries == []


class TestParseLearnings:
    def test_markdown_list(self):
        from migrate_data import DataMigrator
        migrator = DataMigrator(pool=None)
        entries = migrator.parse_learnings(f"{V1_FIXTURE}/memory/learnings.md")
        assert len(entries) == 2
        assert entries[0][0] == "2026-03-24"  # date
        assert "Google Drive" in entries[0][1]  # content


class TestMigrateCapsule:
    @pytest.mark.asyncio
    async def test_full_migration_flow(self):
        from migrate_data import DataMigrator
        pool = AsyncMock()
        # fetchval: None (not exists) for diary checks, then 1 (id) for inserts
        pool.fetchval = AsyncMock(side_effect=[
            None, 1,  # diary entry 1: exists? no → insert
            None, 1,  # diary entry 2: exists? no → insert
            1,        # memory entry 1
            1,        # memory entry 2
            1,        # learning 1
            1,        # learning 2
            1,        # correction 1
            1,        # correction 2
        ])
        pool.execute = AsyncMock()
        migrator = DataMigrator(pool=pool)
        result = await migrator.migrate_capsule("test_capsule", V1_FIXTURE)
        assert isinstance(result, dict)
        assert result["diary"] == 2
        assert result["memory"] == 2
        assert result["learnings"] == 2
        assert result["corrections"] == 2
