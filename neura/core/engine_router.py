"""EngineRouter — multi-engine with automatic fallback.

@arch scope=platform  affects=all_capsules
@arch risk=HIGH  restart=neura-v2
@arch role=Routes requests between Claude, OpenCode, and YandexGPT engines with auto-fallback.

When primary engine fails (auth, rate limit, subscription revoked),
automatically switches to fallback engine. Seamless for users.
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import AsyncIterator

from neura.core.engine import Chunk, EngineConfig, EngineResult

logger = logging.getLogger(__name__)

# Error types that trigger fallback (transient errors worth retrying on different engine)
FALLBACK_ERRORS = {"AUTH", "RATE_LIMIT", "NO_BALANCE", "SIGTERM", "OOM"}

# Approximate token costs per 1M tokens (USD) for common models
MODEL_COSTS = {
    "openrouter/deepseek/deepseek-chat-v3.1": (0.27, 1.10),
    "openrouter/deepseek/deepseek-v3.2": (0.27, 1.10),
    "openrouter/google/gemini-2.5-flash": (0.15, 0.60),
    "openrouter/google/gemini-2.5-pro": (1.25, 10.0),
    "openrouter/anthropic/claude-sonnet-4": (3.0, 15.0),
    "openrouter/meta-llama/llama-3.3-70b-instruct:free": (0, 0),
    "yandexgpt-lite": (1.67, 1.67),
    "yandexgpt-pro": (6.70, 6.70),
    "yandexgpt-pro-5": (10.0, 10.0),
    "yandexgpt-pro-5.1": (6.70, 6.70),
}


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~1 token per 3.5 chars for mixed content."""
    return max(1, len(text) // 4)


def _estimate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    """Estimate cost in USD based on model pricing."""
    costs = MODEL_COSTS.get(model)
    if not costs:
        # Default to DeepSeek pricing for unknown models
        costs = (0.50, 2.0)
    cost_in = (tokens_in / 1_000_000) * costs[0]
    cost_out = (tokens_out / 1_000_000) * costs[1]
    return round(cost_in + cost_out, 6)


@dataclass
class EngineStatus:
    """Track engine health per capsule."""
    name: str
    healthy: bool = True
    last_error: str | None = None
    last_error_time: float = 0
    consecutive_failures: int = 0
    # Auto-recover after this many seconds
    recovery_timeout: float = 3600  # 1 hour


@dataclass
class RouterConfig:
    """Per-capsule engine routing config."""
    primary: str = "claude"          # "claude", "opencode", or "yandex"
    fallback: str | None = "opencode"  # fallback engine
    opencode_model: str = "openrouter/deepseek/deepseek-chat-v3.1"  # default cheap model
    opencode_model_premium: str = "openrouter/anthropic/claude-sonnet-4"  # premium fallback
    yandex_model: str = "yandexgpt-lite"  # yandexgpt-lite, yandexgpt-pro, yandexgpt-pro-5.1
    auto_switch: bool = True         # auto-fallback on error
    # Complexity-based routing (future)
    route_by_complexity: bool = False
    complexity_threshold: int = 500  # tokens in prompt — above = premium


class EngineRouter:
    """Routes between ClaudeEngine and OpenCodeEngine.

    Usage:
        router = EngineRouter(claude_engine, opencode_engine)
        result = await router.execute(prompt, config, router_config)
        async for chunk in router.stream(prompt, config, router_config):
            ...
    """

    def __init__(self, claude_engine=None, opencode_engine=None,
                 yandex_engine=None, metrics=None):
        self._claude = claude_engine
        self._opencode = opencode_engine
        self._yandex = yandex_engine
        self._metrics = metrics  # MetricsCollector for token/cost tracking
        # Per-capsule health tracking: capsule_id -> {engine_name: EngineStatus}
        self._status: dict[str, dict[str, EngineStatus]] = {}

    def _get_status(self, capsule_id: str, engine_name: str) -> EngineStatus:
        if capsule_id not in self._status:
            self._status[capsule_id] = {}
        if engine_name not in self._status[capsule_id]:
            self._status[capsule_id][engine_name] = EngineStatus(name=engine_name)
        return self._status[capsule_id][engine_name]

    def _get_engine(self, name: str):
        if name == "claude":
            return self._claude
        elif name == "opencode":
            return self._opencode
        elif name == "yandex":
            return self._yandex
        raise ValueError(f"Unknown engine: {name}")

    def _check_recovery(self, status: EngineStatus) -> bool:
        """Check if enough time has passed to retry a failed engine."""
        if status.healthy:
            return True
        elapsed = time.monotonic() - status.last_error_time
        if elapsed > status.recovery_timeout:
            logger.info(f"Engine {status.name} recovery timeout passed, retrying")
            status.healthy = True
            status.consecutive_failures = 0
            return True
        return False

    def _mark_failure(self, status: EngineStatus, error_type: str):
        status.healthy = False
        status.last_error = error_type
        status.last_error_time = time.monotonic()
        status.consecutive_failures += 1
        logger.warning(
            f"Engine {status.name} failed: {error_type} "
            f"(consecutive: {status.consecutive_failures})"
        )

    def _mark_success(self, status: EngineStatus):
        status.healthy = True
        status.consecutive_failures = 0

    def _select_engine(self, capsule_id: str, router_cfg: RouterConfig) -> tuple[str, object]:
        """Select which engine to use based on health and config."""
        primary = router_cfg.primary
        fallback = router_cfg.fallback

        primary_status = self._get_status(capsule_id, primary)
        self._check_recovery(primary_status)

        if primary_status.healthy:
            engine = self._get_engine(primary)
            if engine:
                return primary, engine

        # Primary unhealthy or unavailable — try fallback
        if fallback and router_cfg.auto_switch:
            fallback_status = self._get_status(capsule_id, fallback)
            self._check_recovery(fallback_status)
            if fallback_status.healthy:
                engine = self._get_engine(fallback)
                if engine:
                    logger.info(
                        f"Capsule {capsule_id}: switching to fallback engine {fallback} "
                        f"(primary {primary} unhealthy: {primary_status.last_error})"
                    )
                    return fallback, engine

        # Both unhealthy — force primary anyway
        engine = self._get_engine(primary)
        if engine:
            return primary, engine
        if fallback:
            engine = self._get_engine(fallback)
            if engine:
                return fallback, engine

        raise RuntimeError("No engine available")

    def _optimize_prompt_for_opencode(self, prompt: str) -> str:
        """Lighten prompt for OpenCode engines — save tokens, remove Claude-specific parts."""
        import re
        original_len = len(prompt)

        # Remove skill-check DNA rules (Claude-specific)
        prompt = re.sub(
            r'🔍 Скилл-чек.*?(?=\n###|\n##|\Z)', '', prompt, flags=re.DOTALL
        )
        # Remove session log DNA rules
        prompt = re.sub(
            r'💾 Фиксация.*?(?=\n###|\n##|\Z)', '', prompt, flags=re.DOTALL
        )
        # Remove skill update DNA rules
        prompt = re.sub(
            r'🔄 Обновление скиллов.*?(?=\n###|\n##|\Z)', '', prompt, flags=re.DOTALL
        )
        # Truncate diary sections more aggressively (keep last 3000 chars max)
        for marker in ['📋 Справка:', '📅 Справка:']:
            idx = prompt.find(marker)
            if idx >= 0:
                # Find end of section
                next_section = prompt.find('\n[', idx + 1)
                next_section2 = prompt.find('\n📚', idx + 1)
                next_section3 = prompt.find('\nСообщение пользователя:', idx + 1)
                ends = [e for e in [next_section, next_section2, next_section3] if e > 0]
                end = min(ends) if ends else len(prompt)
                section = prompt[idx:end]
                if len(section) > 3000:
                    prompt = prompt[:idx] + section[-3000:] + prompt[end:]

        # Clean up multiple blank lines
        prompt = re.sub(r'\n{3,}', '\n\n', prompt)

        saved = original_len - len(prompt)
        if saved > 100:
            logger.info(f"Prompt optimized for OpenCode: {original_len} → {len(prompt)} chars (saved {saved})")
        return prompt

    def _adjust_config(self, config: EngineConfig, engine_name: str,
                       router_cfg: RouterConfig) -> EngineConfig:
        """Adjust EngineConfig for the selected engine."""
        from dataclasses import replace
        if engine_name == "opencode":
            return replace(config, model=router_cfg.opencode_model)
        elif engine_name == "yandex":
            yandex_model = getattr(router_cfg, "yandex_model", "yandexgpt-lite")
            return replace(config, model=yandex_model)
        return config

    async def execute(self, prompt: str, config: EngineConfig,
                      router_cfg: RouterConfig | None = None,
                      capsule_id: str = "default") -> EngineResult:
        """Execute with automatic fallback."""
        rcfg = router_cfg or RouterConfig()
        engine_name, engine = self._select_engine(capsule_id, rcfg)
        adjusted_cfg = self._adjust_config(config, engine_name, rcfg)
        # Optimize prompt for non-Claude engines
        exec_prompt = self._optimize_prompt_for_opencode(prompt) if engine_name == "opencode" else prompt

        result = await engine.execute(exec_prompt, adjusted_cfg)

        # Track engine usage and estimated cost
        if self._metrics:
            tokens_in = _estimate_tokens(prompt)
            tokens_out = _estimate_tokens(result.text) if result.text else 0
            model = adjusted_cfg.model
            cost = _estimate_cost(model, tokens_in, tokens_out)
            import asyncio
            asyncio.ensure_future(
                self._metrics.record_engine_usage(
                    capsule_id, engine_name,
                    tokens_in=tokens_in, tokens_out=tokens_out,
                    cost_usd=cost,
                )
            )

        status = self._get_status(capsule_id, engine_name)
        if result.success:
            self._mark_success(status)
            return result

        # Check if error is fallback-worthy
        if result.error_type in FALLBACK_ERRORS and rcfg.fallback and rcfg.auto_switch:
            self._mark_failure(status, result.error_type)

            # Try fallback
            fb_name = rcfg.fallback if engine_name == rcfg.primary else rcfg.primary
            fb_engine = self._get_engine(fb_name)
            if fb_engine:
                fb_status = self._get_status(capsule_id, fb_name)
                if self._check_recovery(fb_status):
                    logger.info(f"Falling back to {fb_name} for capsule {capsule_id}")
                    fb_cfg = self._adjust_config(config, fb_name, rcfg)
                    fb_result = await fb_engine.execute(prompt, fb_cfg)
                    if fb_result.success:
                        self._mark_success(fb_status)
                    else:
                        self._mark_failure(fb_status, fb_result.error_type or "UNKNOWN")
                    return fb_result

        return result

    async def stream(self, prompt: str, config: EngineConfig,
                     router_cfg: RouterConfig | None = None,
                     capsule_id: str = "default") -> AsyncIterator[Chunk]:
        """Stream with automatic fallback on critical errors."""
        rcfg = router_cfg or RouterConfig()
        engine_name, engine = self._select_engine(capsule_id, rcfg)
        adjusted_cfg = self._adjust_config(config, engine_name, rcfg)
        # Optimize prompt for non-Claude engines
        stream_prompt = self._optimize_prompt_for_opencode(prompt) if engine_name == "opencode" else prompt

        status = self._get_status(capsule_id, engine_name)
        had_error = False
        error_type = None
        chunks_yielded = 0
        accumulated_text = ""

        try:
            async for chunk in engine.stream(stream_prompt, adjusted_cfg):
                if chunk.type == "error":
                    had_error = True
                    text_lower = chunk.text.lower()
                    if "auth" in text_lower or "unauthorized" in text_lower:
                        error_type = "AUTH"
                    elif "rate limit" in text_lower:
                        error_type = "RATE_LIMIT"
                    else:
                        error_type = "STREAM_ERROR"
                if chunk.type in ("text", "result") and chunk.text:
                    accumulated_text += chunk.text
                yield chunk
                chunks_yielded += 1
        except Exception as e:
            had_error = True
            error_type = "EXCEPTION"
            logger.error(f"Engine {engine_name} stream exception: {e}")

        # Track engine usage after stream completes
        if self._metrics and chunks_yielded > 0:
            tokens_in = _estimate_tokens(prompt)
            tokens_out = _estimate_tokens(accumulated_text)
            model = adjusted_cfg.model
            cost = _estimate_cost(model, tokens_in, tokens_out)
            import asyncio
            asyncio.ensure_future(
                self._metrics.record_engine_usage(
                    capsule_id, engine_name,
                    tokens_in=tokens_in, tokens_out=tokens_out,
                    cost_usd=cost,
                )
            )

        if had_error and error_type in FALLBACK_ERRORS:
            self._mark_failure(status, error_type)
            # If we haven't yielded much, try fallback
            if chunks_yielded < 3 and rcfg.fallback and rcfg.auto_switch:
                fb_name = rcfg.fallback if engine_name == rcfg.primary else rcfg.primary
                fb_engine = self._get_engine(fb_name)
                if fb_engine:
                    logger.info(f"Stream fallback to {fb_name}")
                    fb_cfg = self._adjust_config(config, fb_name, rcfg)
                    yield Chunk(type="status", text="🔄 Переключаю движок...")
                    async for chunk in fb_engine.stream(prompt, fb_cfg):
                        yield chunk
        elif not had_error:
            self._mark_success(status)

    def get_engine_info(self, capsule_id: str = "default") -> dict:
        """Get current engine status for monitoring/UI."""
        info = {}
        for engine_name, status in self._status.get(capsule_id, {}).items():
            info[engine_name] = {
                "healthy": status.healthy,
                "last_error": status.last_error,
                "consecutive_failures": status.consecutive_failures,
            }
        return info
