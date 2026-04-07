"""Skill Learning — auto-collect usage data and evolve skills.

SkillUsageCollector: records every skill usage to PostgreSQL.
SkillEvolver: analyzes usage patterns and updates SKILL.md automatically.
"""
import logging
import re
import os
import shutil
import subprocess
from datetime import datetime, timezone
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

_BASE = os.environ.get("NEURA_BASE", str(Path(__file__).resolve().parent.parent.parent))
SKILLS_SOURCE = os.path.join(_BASE, "skills")  # same as deploy — self-contained
SKILLS_DEPLOY = os.path.join(_BASE, "skills")
SKILL_TRACKER = os.path.join(_BASE, "scripts", "skill-tracker.py")
EVOLVE_THRESHOLD = 5  # evolve after N new usages
CORRECTION_THRESHOLD = 3  # evolve after N corrections


@dataclass
class SkillUsageEntry:
    capsule_id: str
    skill_name: str
    success: bool = True
    duration_sec: float = 0.0
    user_intent: str = ""
    tools_used: list[str] = field(default_factory=list)
    correction: str = ""
    lesson: str = ""


class SkillUsageCollector:
    """Records skill usage to PostgreSQL after each request."""

    def __init__(self, pool):
        self._pool = pool

    def detect_skill(self, user_message: str, bot_response: str,
                     tools_used: list[str], capsule_skills: list[str]) -> str | None:
        """Detect which skill was used based on content analysis.

        Strategy: match user intent against known skill triggers.
        """
        msg_lower = user_message.lower()
        resp_lower = bot_response.lower() if bot_response else ""

        # Keyword-based detection (ordered by specificity)
        skill_keywords = {
            "word-docx": ["word", "docx", "документ word"],
            "excel-xlsx": ["excel", "xlsx", "таблиц"],
            "ppt-generator": ["презентаци", "слайд", "ppt", "powerpoint"],
            "notion-pdf": ["pdf", "экспорт", "документ"],
            "copywriting": ["копирайт", "текст лендинг", "заголов", "cta"],
            "headline-lab": ["заголовк", "подзаголов"],
            "smart-response": ["telegraph", "длинный ответ"],
            "carousel-creator": ["карусел", "слайды для", "instagram"],
            "social-content": ["пост", "соцсет", "instagram", "telegram контент"],
            "brand-voice-clone": ["brand voice", "стиль канала", "голос бренда"],
            "nano-banana-pro": ["картинк", "изображен", "сгенерируй", "нарисуй"],
            "image-processing": ["ресайз", "сжат", "webp", "favicon"],
            "seo-audit": ["seo", "индексац", "мета-тег"],
            "landing-audit": ["аудит", "проверь сайт", "lighthouse"],
            "landing-page": ["лендинг", "посадочн", "промо-страниц"],
            "systematic-debugging": ["баг", "ошибк", "не работает", "debug"],
            "brainstorming": ["мозговой штурм", "идеи", "спек"],
            "decision-lab": ["решени", "выбор", "вариант", "дилемм"],
            "market-research": ["исследован рынк", "конкурент", "ниш"],
            "auto-funnel": ["воронк", "funnel", "лид-магнит"],
            "webinar-script": ["вебинар", "сценарий вебинар"],
            "email-campaign": ["рассылк", "email", "письм"],
            "quiz-funnel": ["квиз", "опросник", "тест на сайт"],
            "product-ladder": ["тариф", "ценообразован", "продуктовая линейк"],
            "google-oauth": ["google", "sheets", "drive", "calendar"],
            "bitrix24-agent": ["битрикс", "bitrix", "crm"],
            "vk-community": ["вк", "вконтакт", "vk"],
            "russian-typography": ["типографик", "неразрывн", "предлог"],
            "warmup-constructor": ["прогрев", "warmup", "распаковк"],
            "content-creator": ["контент-план", "seo-стат"],
            "marketing-psychology": ["психолог", "убежден", "ментальн"],
            "course-platform-builder": ["обучающ платформ", "lms", "курс"],
        }

        for skill, keywords in skill_keywords.items():
            if skill not in capsule_skills:
                continue
            for kw in keywords:
                if kw in msg_lower or kw in resp_lower:
                    return skill

        # Tool-based detection
        tools_lower = [t.lower() for t in tools_used]
        if any("websearch" in t or "webfetch" in t for t in tools_lower):
            if "content-creator" in capsule_skills:
                return "content-creator"
        if any("write" in t or "edit" in t for t in tools_lower):
            if "copywriting" in capsule_skills:
                return "copywriting"

        return None

    async def record(self, entry: SkillUsageEntry) -> int | None:
        """Record a skill usage entry to PostgreSQL."""
        if not entry.skill_name:
            return None
        try:
            return await self._pool.fetchval(
                """INSERT INTO skill_usage
                   (capsule_id, skill_name, success, duration_sec,
                    user_intent, tools_used, correction, lesson)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                   RETURNING id""",
                entry.capsule_id, entry.skill_name, entry.success,
                entry.duration_sec, entry.user_intent,
                entry.tools_used, entry.correction, entry.lesson,
            )
        except Exception as e:
            logger.warning(f"Failed to record skill usage: {e}")
            return None

    async def get_usage_count(self, skill_name: str) -> int:
        """Get total usage count for a skill since last evolution."""
        try:
            return await self._pool.fetchval(
                "SELECT COUNT(*) FROM skill_usage WHERE skill_name = $1",
                skill_name,
            ) or 0
        except Exception:
            return 0

    async def get_recent_usages(self, skill_name: str, limit: int = 20) -> list[dict]:
        """Get recent usage entries for a skill."""
        try:
            rows = await self._pool.fetch(
                """SELECT capsule_id, user_intent, tools_used, success,
                          duration_sec, correction, lesson, used_at
                   FROM skill_usage
                   WHERE skill_name = $1
                   ORDER BY used_at DESC LIMIT $2""",
                skill_name, limit,
            )
            return [dict(r) for r in rows]
        except Exception:
            return []

    async def get_corrections(self, skill_name: str, limit: int = 10) -> list[str]:
        """Get recent corrections for a skill."""
        try:
            rows = await self._pool.fetch(
                """SELECT correction FROM skill_usage
                   WHERE skill_name = $1 AND correction IS NOT NULL
                   AND correction != ''
                   ORDER BY used_at DESC LIMIT $2""",
                skill_name, limit,
            )
            return [r["correction"] for r in rows]
        except Exception:
            return []

    async def get_skill_stats(self, skill_name: str) -> dict:
        """Get aggregated stats for a skill."""
        try:
            row = await self._pool.fetchrow(
                """SELECT
                     COUNT(*) as total,
                     COUNT(*) FILTER (WHERE success) as successes,
                     AVG(duration_sec) as avg_duration,
                     COUNT(*) FILTER (WHERE correction IS NOT NULL AND correction != '') as corrections,
                     MAX(used_at) as last_used
                   FROM skill_usage WHERE skill_name = $1""",
                skill_name,
            )
            if row:
                total = row["total"] or 0
                return {
                    "total": total,
                    "successes": row["successes"] or 0,
                    "success_rate": round((row["successes"] or 0) / total * 100, 1) if total else 0,
                    "avg_duration": round(row["avg_duration"] or 0, 1),
                    "corrections": row["corrections"] or 0,
                    "last_used": str(row["last_used"]) if row["last_used"] else None,
                }
        except Exception:
            pass
        return {"total": 0, "successes": 0, "success_rate": 0, "avg_duration": 0,
                "corrections": 0, "last_used": None}


class SkillEvolver:
    """Analyzes skill usage patterns and updates SKILL.md automatically.

    Triggered after EVOLVE_THRESHOLD usages or CORRECTION_THRESHOLD corrections.
    """

    def __init__(self, collector: SkillUsageCollector):
        self._collector = collector

    async def should_evolve(self, skill_name: str) -> bool:
        """Check if skill has enough data to evolve."""
        stats = await self._collector.get_skill_stats(skill_name)
        # Evolve if enough usages OR enough corrections
        if stats["total"] >= EVOLVE_THRESHOLD:
            return True
        if stats["corrections"] >= CORRECTION_THRESHOLD:
            return True
        return False

    async def generate_evolution(self, skill_name: str) -> dict | None:
        """Analyze usage and generate SKILL.md updates.

        Returns dict with keys: changelog_entry, new_antipatterns, trigger_updates.
        Returns None if nothing meaningful to add.
        """
        stats = await self._collector.get_skill_stats(skill_name)
        usages = await self._collector.get_recent_usages(skill_name, limit=20)
        corrections = await self._collector.get_corrections(skill_name, limit=10)

        if not usages:
            return None

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        result = {"changelog_entry": "", "new_antipatterns": [], "trigger_insights": []}

        # Analyze corrections → new anti-patterns
        if corrections:
            result["new_antipatterns"] = corrections[:5]
            corrections_summary = "; ".join(c[:60] for c in corrections[:3])
            result["changelog_entry"] += f"- {now}: {stats['total']} использований, "
            result["changelog_entry"] += f"{stats['corrections']} corrections. "
            result["changelog_entry"] += f"Success rate: {stats['success_rate']}%. "
            result["changelog_entry"] += f"Corrections: {corrections_summary}"
        else:
            result["changelog_entry"] += f"- {now}: {stats['total']} использований, "
            result["changelog_entry"] += f"success rate {stats['success_rate']}%, "
            result["changelog_entry"] += f"avg latency {stats['avg_duration']}s"

        # Analyze user intents → trigger insights
        intents = [u.get("user_intent", "") for u in usages if u.get("user_intent")]
        if intents:
            # Find common words that appear in 50%+ of intents
            word_freq = {}
            for intent in intents:
                for word in intent.lower().split():
                    if len(word) > 3:
                        word_freq[word] = word_freq.get(word, 0) + 1
            threshold = max(len(intents) * 0.3, 2)
            common = [w for w, c in word_freq.items() if c >= threshold]
            if common:
                result["trigger_insights"] = common[:5]

        return result

    async def apply_evolution(self, skill_name: str) -> bool:
        """Apply evolution to SKILL.md file.

        1. Generate evolution data
        2. Edit SKILL.md changelog
        3. Sync to v2 deployment
        """
        evolution = await self.generate_evolution(skill_name)
        if not evolution or not evolution.get("changelog_entry"):
            logger.info(f"Skill {skill_name}: nothing to evolve")
            return False

        # Find SKILL.md in source
        skill_md = os.path.join(SKILLS_SOURCE, skill_name, "SKILL.md")
        if not os.path.exists(skill_md):
            logger.warning(f"SKILL.md not found: {skill_md}")
            return False

        try:
            content = open(skill_md, "r").read()

            # Append to ## Changelog section
            changelog_marker = "## Changelog"
            if changelog_marker in content:
                # Find the marker and insert after it (and any comment line)
                parts = content.split(changelog_marker, 1)
                after = parts[1]
                # Skip comment lines
                lines = after.split("\n")
                insert_idx = 0
                for i, line in enumerate(lines):
                    if line.strip() and not line.strip().startswith("<!--") and not line.strip().startswith("-->"):
                        insert_idx = i
                        break
                    insert_idx = i + 1

                lines.insert(insert_idx, "\n" + evolution["changelog_entry"])

                # Add anti-patterns if any
                if evolution.get("new_antipatterns"):
                    ap_text = "\n".join(f"  - ⚠️ {ap[:80]}" for ap in evolution["new_antipatterns"])
                    lines.insert(insert_idx + 1, f"  Auto-detected anti-patterns:\n{ap_text}")

                new_content = parts[0] + changelog_marker + "\n".join(lines)
            else:
                # No changelog section — append one
                new_content = content + f"\n\n## Changelog\n\n{evolution['changelog_entry']}\n"

            # Write updated SKILL.md
            with open(skill_md, "w") as f:
                f.write(new_content)

            # Sync to v2 deployment (skip if same directory)
            deploy_dir = os.path.join(SKILLS_DEPLOY, skill_name)
            deploy_md = os.path.join(deploy_dir, "SKILL.md")
            if os.path.exists(deploy_dir) and os.path.realpath(skill_md) != os.path.realpath(deploy_md):
                shutil.copy2(skill_md, deploy_md)
                logger.info(f"Skill {skill_name} synced to v2: {deploy_md}")

            logger.info(f"Skill {skill_name} evolved: {evolution['changelog_entry'][:80]}")
            return True

        except Exception as e:
            logger.error(f"Failed to evolve skill {skill_name}: {e}")
            return False

    async def check_and_evolve_all(self, skill_names: list[str]) -> list[str]:
        """Check all skills and evolve those that need it. Returns evolved skill names."""
        evolved = []
        for name in skill_names:
            try:
                if await self.should_evolve(name):
                    if await self.apply_evolution(name):
                        evolved.append(name)
            except Exception as e:
                logger.error(f"Evolution check failed for {name}: {e}")
        return evolved
