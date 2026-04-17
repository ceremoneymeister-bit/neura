"""Capsule runtime — YAML config loader + runtime helpers.

One capsule = one AI agent (one client). Config lives in YAML,
system prompt in SYSTEM.md. This module loads, validates, and
provides runtime access to capsule configuration.
"""
import os
import re
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

from neura.core.engine import EngineConfig
from neura.core.engine_router import RouterConfig

logger = logging.getLogger(__name__)

_ENV_VAR_RE = re.compile(r"\$\{(\w+)\}")

DEFAULT_TOOLS = ["Read", "Glob", "Grep", "Write", "Edit", "WebSearch", "WebFetch"]
DEFAULT_MEMORY = {"diary_retention_days": 90, "max_long_term_entries": 100,
                  "context_window": {"today_diary": 10, "recent_days": 3}}
DEFAULT_RATE_LIMIT = {"max_per_day": 100, "warn_at": 50}

# Skills auto-injected into ALL capsules (platform-level, no YAML edit needed)
DEFAULT_GLOBAL_SKILLS = ["heartbeat", "smart-response"]
DEFAULT_HOMES_DIR = str(Path(__file__).resolve().parent.parent.parent / "homes")

REQUIRED_FIELDS = ["id", "name"]
REQUIRED_NESTED = {
    "owner": ["name", "telegram_id"],
    "telegram": ["bot_token"],
}


def _resolve_env_vars(value: str) -> str:
    """Replace ${VAR_NAME} with os.environ[VAR_NAME]."""
    def _replace(match):
        var = match.group(1)
        val = os.environ.get(var)
        if val is None:
            raise ValueError(f"Environment variable ${{{var}}} not set")
        return val
    return _ENV_VAR_RE.sub(_replace, value) if isinstance(value, str) else value


def _deep_resolve(obj):
    """Recursively resolve env vars in nested dicts/lists."""
    if isinstance(obj, str):
        return _resolve_env_vars(obj)
    if isinstance(obj, dict):
        return {k: _deep_resolve(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_deep_resolve(i) for i in obj]
    return obj


def _merge_global_skills(capsule_skills: list[str]) -> list[str]:
    """Merge DEFAULT_GLOBAL_SKILLS into capsule's skill list (deduplicated)."""
    merged = list(capsule_skills)
    for skill in DEFAULT_GLOBAL_SKILLS:
        if skill not in merged:
            merged.append(skill)
    return merged


@dataclass
class CapsuleConfig:
    """All configuration for a single capsule."""
    id: str
    name: str
    owner_name: str
    owner_telegram_id: int
    bot_token: str
    model: str = "sonnet"
    effort: str = "standard"
    allowed_tools: list[str] = field(default_factory=lambda: [
        "Read", "Glob", "Grep", "Write", "Edit", "WebSearch", "WebFetch",
    ])
    system_prompt_path: str = ""
    skills: list[str] = field(default_factory=list)
    employees: list[dict] = field(default_factory=list)
    features: dict = field(default_factory=dict)
    memory: dict = field(default_factory=lambda: {
        "diary_retention_days": 90,
        "max_long_term_entries": 100,
        "context_window": {"today_diary": 10, "recent_days": 3},
    })
    rate_limit: dict = field(default_factory=lambda: {"max_per_day": 100, "warn_at": 50})
    trial: dict = field(default_factory=lambda: {"enabled": False})
    home_dir: str | None = None
    internal_groups: list[int] = field(default_factory=list)
    mention_required_groups: list[int] = field(default_factory=list)
    heartbeat: list[dict] = field(default_factory=list)
    # Engine routing: primary/fallback engine selection
    engine: dict = field(default_factory=lambda: {
        "primary": "claude",
        "fallback": "opencode",
        "opencode_model": "openrouter/openai/gpt-oss-120b:free",
        "auto_switch": True,
    })


class Capsule:
    """Runtime representation of a single AI agent capsule."""

    def __init__(self, config: CapsuleConfig, config_dir: str):
        self.config = config
        self._config_dir = Path(config_dir)

    @classmethod
    def load(cls, capsule_id: str, config_dir: str = "config/capsules") -> "Capsule":
        """Load a capsule from YAML config file."""
        config_path = Path(config_dir) / f"{capsule_id}.yaml"
        if not config_path.exists():
            raise FileNotFoundError(f"Capsule config not found: {config_path}")

        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        data = _deep_resolve(raw)

        # Validate required fields
        for f in REQUIRED_FIELDS:
            if f not in data or not data[f]:
                raise ValueError(f"Required field '{f}' missing in {config_path}")
        for section, fields in REQUIRED_NESTED.items():
            if section not in data:
                raise ValueError(f"Required section '{section}' missing in {config_path}")
            for f in fields:
                if f not in data[section]:
                    raise ValueError(f"Required field '{section}.{f}' missing in {config_path}")

        owner = data.get("owner", {})
        telegram = data.get("telegram", {})
        claude = data.get("claude", {})

        cfg = CapsuleConfig(
            id=data["id"],
            name=data["name"],
            owner_name=owner["name"],
            owner_telegram_id=int(owner["telegram_id"]),
            bot_token=telegram["bot_token"],
            model=claude.get("model", "sonnet"),
            effort=claude.get("effort", "standard"),
            allowed_tools=claude.get("allowed_tools", list(DEFAULT_TOOLS)),
            system_prompt_path=claude.get("system_prompt", ""),
            skills=_merge_global_skills(data.get("skills", [])),
            employees=data.get("employees", []),
            features=telegram.get("features", {}),
            memory=data.get("memory", dict(DEFAULT_MEMORY)),
            rate_limit=data.get("rate_limit", dict(DEFAULT_RATE_LIMIT)),
            trial=data.get("trial", {"enabled": False}),
            home_dir=str(Path(os.environ.get("NEURA_HOMES_DIR", DEFAULT_HOMES_DIR)) / data["id"]),
            internal_groups=[int(g) for g in data.get("internal_groups", [])],
            mention_required_groups=[int(g) for g in data.get("mention_required_groups", [])],
            heartbeat=data.get("heartbeat", []),
            engine=data.get("engine", {
                "primary": "claude",
                "fallback": "opencode",
                "opencode_model": "openrouter/openai/gpt-oss-120b:free",
                "auto_switch": True,
            }),
        )

        logger.info(f"Loaded capsule: {cfg.id} ({cfg.name})")
        return cls(cfg, config_dir)

    @classmethod
    def load_all(cls, config_dir: str = "config/capsules") -> dict[str, "Capsule"]:
        """Load all capsules from a directory."""
        capsules = {}
        config_path = Path(config_dir)
        for yaml_file in sorted(config_path.glob("*.yaml")):
            try:
                cap = cls.load(yaml_file.stem, config_dir=config_dir)
                capsules[cap.config.id] = cap
            except Exception as e:
                logger.error(f"Failed to load capsule {yaml_file.name}: {e}")
        return capsules

    def get_engine_config(self) -> EngineConfig:
        """Convert capsule config to EngineConfig for ClaudeEngine."""
        # Skills table is attached by app.py after loading
        skills_prompt = getattr(self, "_skills_table", "")
        return EngineConfig(
            model=self.config.model,
            effort=self.config.effort,
            allowed_tools=list(self.config.allowed_tools),
            home_dir=self.config.home_dir,
            append_system_prompt=skills_prompt,
        )

    def get_router_config(self) -> RouterConfig:
        """Convert capsule engine config to RouterConfig."""
        eng = self.config.engine
        return RouterConfig(
            primary=eng.get("primary", "claude"),
            fallback=eng.get("fallback", "opencode"),
            opencode_model=eng.get("opencode_model", "openrouter/openai/gpt-oss-120b:free"),
            opencode_model_premium=eng.get("opencode_model_premium", "openrouter/anthropic/claude-sonnet-4"),
            auto_switch=eng.get("auto_switch", True),
        )

    def is_employee(self, telegram_id: int) -> bool:
        """Check if telegram_id belongs to owner or staff."""
        if telegram_id == self.config.owner_telegram_id:
            return True
        return any(
            emp.get("telegram_id") == telegram_id
            for emp in self.config.employees
        )

    def get_system_prompt(self) -> str:
        """Read SYSTEM.md file for this capsule.

        Replaces ${NEURA_BASE} with the actual project root path,
        making SYSTEM.md portable across servers.
        """
        if not self.config.system_prompt_path:
            return ""
        prompt_path = self._config_dir / self.config.system_prompt_path
        if prompt_path.exists():
            base_dir = str(Path(__file__).resolve().parent.parent.parent)
            text = prompt_path.read_text(encoding="utf-8").strip()
            return text.replace("${NEURA_BASE}", base_dir)
        logger.warning(f"System prompt not found: {prompt_path}")
        return ""

    def is_trial_expired(self) -> bool:
        """Check if trial period has expired."""
        trial = self.config.trial
        if not trial.get("enabled", False):
            return False
        started_at = trial.get("started_at")
        days = trial.get("days", 5)
        if not started_at:
            return False
        if isinstance(started_at, str):
            started_at = datetime.fromisoformat(started_at)
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return bool((now - started_at).days > days)
