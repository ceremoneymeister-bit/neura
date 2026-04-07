"""Skill loader + registry — scans SKILL.md files, provides skill info.

@arch scope=platform  affects=all_capsules(14), proactive_engine
@arch depends=filesystem (/opt/neura-v2/skills/*/SKILL.md)
@arch risk=MEDIUM  restart=neura-v2
@arch role=Parses SKILL.md frontmatter, caches metadata, provides lookup + proactive triggers.
@arch note=Default dir: /opt/neura-v2/skills/. Capsules symlink from homes/*/skills/.

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
    # Proactive config (flat format from frontmatter)
    proactive_enabled: bool = False
    proactive_triggers: list[dict] = field(default_factory=list)
    # Learning config
    learning_track_success: bool = False
    learning_track_corrections: bool = False
    learning_evolve_threshold: int = 5
    # Usage stats (populated at runtime)
    usage_count: int = 0
    maturity: str = "seed"


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
                # Parse proactive triggers from flat frontmatter
                proactive_triggers = []
                for i in range(1, 5):
                    t_type = meta.get(f"proactive_trigger_{i}_type")
                    t_cond = meta.get(f"proactive_trigger_{i}_condition")
                    t_act = meta.get(f"proactive_trigger_{i}_action")
                    if t_type and t_cond:
                        proactive_triggers.append({
                            "type": t_type, "condition": t_cond,
                            "action": t_act or "",
                        })

                self._skills[name] = SkillInfo(
                    name=name,
                    description=meta.get("description", ""),
                    path=str(skill_md.parent),
                    triggers=_extract_triggers(content),
                    version=meta.get("version", ""),
                    tags=meta.get("tags", []),
                    proactive_enabled=bool(meta.get("proactive_enabled", False)),
                    proactive_triggers=proactive_triggers,
                    learning_track_success=bool(meta.get("learning_track_success", False)),
                    learning_track_corrections=bool(meta.get("learning_track_corrections", False)),
                    learning_evolve_threshold=int(meta.get("learning_evolve_threshold", 5)),
                    usage_count=int(meta.get("usage_count", 0)),
                    maturity=meta.get("maturity", "seed"),
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

    def get_proactive_skills(self) -> list[SkillInfo]:
        """Get all skills with proactive triggers enabled."""
        return [s for s in self._skills.values() if s.proactive_enabled and s.proactive_triggers]

    def all_skill_names(self) -> list[str]:
        """Get all registered skill names."""
        return list(self._skills.keys())

    def format_table(self, skills: list[SkillInfo]) -> str:
        """Generate Markdown table for prompt injection."""
        if not skills:
            return ""
        lines = ["| Скилл | Описание |", "|-------|---------|"]
        for s in skills:
            desc = s.description.replace("|", "\\|")
            lines.append(f"| {s.name} | {desc} |")
        return "\n".join(lines)
