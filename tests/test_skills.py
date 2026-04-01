"""Tests for core/skills.py — Skill loader + registry.

TDD Red Phase.
"""
import pytest
from pathlib import Path

FIXTURES = str(Path(__file__).parent / "fixtures" / "skills")


class TestScan:
    def test_scan_finds_skills(self):
        from neura.core.skills import SkillRegistry
        reg = SkillRegistry(skills_dir=FIXTURES)
        reg.scan()
        # Should find copywriting and smart-response (empty-skill has no SKILL.md)
        assert len(reg._skills) >= 2


class TestGet:
    def test_get_existing(self):
        from neura.core.skills import SkillRegistry, SkillInfo
        reg = SkillRegistry(skills_dir=FIXTURES)
        reg.scan()
        skill = reg.get("copywriting")
        assert skill is not None
        assert isinstance(skill, SkillInfo)
        assert skill.name == "copywriting"
        assert "Marketing" in skill.description or "copy" in skill.description

    def test_get_nonexistent(self):
        from neura.core.skills import SkillRegistry
        reg = SkillRegistry(skills_dir=FIXTURES)
        reg.scan()
        assert reg.get("nonexistent-skill") is None


class TestGetForCapsule:
    def test_filters_by_list(self):
        from neura.core.skills import SkillRegistry
        reg = SkillRegistry(skills_dir=FIXTURES)
        reg.scan()
        skills = reg.get_for_capsule(["copywriting", "smart-response"])
        assert len(skills) == 2
        names = [s.name for s in skills]
        assert "copywriting" in names
        assert "smart-response" in names

    def test_skips_missing_with_warning(self):
        from neura.core.skills import SkillRegistry
        reg = SkillRegistry(skills_dir=FIXTURES)
        reg.scan()
        # "nonexistent" should be skipped, not raise
        skills = reg.get_for_capsule(["copywriting", "nonexistent"])
        assert len(skills) == 1
        assert skills[0].name == "copywriting"


class TestFormatTable:
    def test_generates_markdown(self):
        from neura.core.skills import SkillRegistry
        reg = SkillRegistry(skills_dir=FIXTURES)
        reg.scan()
        skills = reg.get_for_capsule(["copywriting", "smart-response"])
        table = reg.format_table(skills)
        assert "copywriting" in table
        assert "smart-response" in table
        assert "|" in table  # markdown table


class TestParseFrontmatter:
    def test_parses_yaml_metadata(self):
        from neura.core.skills import SkillRegistry
        reg = SkillRegistry(skills_dir=FIXTURES)
        reg.scan()
        skill = reg.get("copywriting")
        assert skill is not None
        assert skill.version == "1.2.0"
        assert "content" in skill.tags
        assert "marketing" in skill.tags
