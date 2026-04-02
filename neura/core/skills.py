"""Skill loader + registry — scans SKILL.md files, provides skill info.

Skills are directories containing SKILL.md with YAML frontmatter.
Each capsule references skills by name in its YAML config.
"""
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_SKILLS_DIR = str(Path(__file__).resolve().parent.parent.parent / "skills")

import yaml

logger = logging.getLogger(__name__)

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)


@dataclass
class SkillInfo:
    """Metadata for a single skill."""
    name: str
    description: str
    path: str
    triggers: str = ""
    version: str = ""
    tags: list[str] = field(default_factory=list)


def _parse_frontmatter(text: str) -> dict:
    """Extract YAML frontmatter from SKILL.md content."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}
    try:
        return yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return {}


def _extract_triggers(text: str) -> str:
    """Extract 'When to Use' section from SKILL.md body."""
    lines = text.split("\n")
    capture = False
    result = []
    for line in lines:
        if re.match(r"^##\s*(When|Когда)", line, re.IGNORECASE):
            capture = True
            continue
        if capture:
            if line.startswith("##"):
                break
            if line.strip():
                result.append(line.strip())
    return " ".join(result)


class SkillRegistry:
    """Scans skill directories, caches metadata, provides lookup."""

    def __init__(self, skills_dir: str | None = None):
        self._skills_dir = Path(
            skills_dir or os.environ.get("NEURA_SKILLS_DIR", DEFAULT_SKILLS_DIR)
        )
        self._skills: dict[str, SkillInfo] = {}

    def scan(self) -> None:
        """Scan skills directory and cache all SKILL.md metadata."""
        self._skills.clear()
        if not self._skills_dir.exists():
            logger.warning(f"Skills directory not found: {self._skills_dir}")
            return

        for skill_md in sorted(self._skills_dir.glob("*/SKILL.md")):
            try:
                content = skill_md.read_text(encoding="utf-8")
                meta = _parse_frontmatter(content)
                name = meta.get("name", skill_md.parent.name)
                self._skills[name] = SkillInfo(
                    name=name,
                    description=meta.get("description", ""),
                    path=str(skill_md.parent),
                    triggers=_extract_triggers(content),
                    version=meta.get("version", ""),
                    tags=meta.get("tags", []),
                )
            except Exception as e:
                logger.error(f"Failed to parse skill {skill_md}: {e}")

        logger.info(f"Scanned {len(self._skills)} skills")

    def get(self, name: str) -> SkillInfo | None:
        """Get skill by name. Returns None if not found."""
        return self._skills.get(name)

    def get_for_capsule(self, skill_names: list[str]) -> list[SkillInfo]:
        """Get skills matching capsule config list. Skips missing."""
        result = []
        for name in skill_names:
            skill = self._skills.get(name)
            if skill:
                result.append(skill)
            else:
                logger.warning(f"Skill '{name}' not found in registry")
        return result

    def format_table(self, skills: list[SkillInfo]) -> str:
        """Generate Markdown table for prompt injection."""
        if not skills:
            return ""
        lines = ["| Скилл | Описание |", "|-------|---------|"]
        for s in skills:
            desc = s.description.replace("|", "\\|")
            lines.append(f"| {s.name} | {desc} |")
        return "\n".join(lines)
