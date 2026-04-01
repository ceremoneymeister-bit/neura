"""Unified Claude CLI wrapper — single entry point for all capsules.

Stateless: every call = new session (no --resume).
Based on: neura-capsule/bot/engine/claude.py (v1, 591 lines).
"""
import asyncio
import os
import logging
import shutil
import time
import json as _json
import subprocess
from dataclasses import dataclass, field
from typing import AsyncIterator

logger = logging.getLogger(__name__)

# Humanized tool labels for streaming progress
TOOL_LABELS: dict[str, str] = {
    "Read": "📖 Читаю", "Glob": "🔍 Ищу файлы", "Grep": "🔍 Ищу в коде",
    "Write": "✍️ Пишу", "Edit": "✏️ Редактирую", "Bash": "⚙️ Выполняю",
    "WebSearch": "🌐 Ищу в интернете", "WebFetch": "🌐 Загружаю страницу",
}

DEFAULT_TOOLS = ["Read", "Glob", "Grep", "Write", "Edit", "WebSearch", "WebFetch",
                 "Bash(python3|ls|mkdir|cat)"]


@dataclass
class EngineConfig:
    """Configuration for a Claude CLI call (from capsule YAML → claude section)."""
    model: str = "sonnet"
    effort: str = "standard"  # low / standard / high
    allowed_tools: list[str] = field(default_factory=lambda: list(DEFAULT_TOOLS))
    home_dir: str | None = None  # Isolated ~/.claude per capsule
    timeout: int = 600  # seconds
    append_system_prompt: str = ""


@dataclass
class Chunk:
    """Single streaming unit."""
    type: str  # "text" | "tool_start" | "tool_end" | "error" | "result"
    text: str = ""
    tool: str = ""
    session_id: str = ""


@dataclass
class EngineResult:
    """Final result of a Claude CLI call."""
    success: bool
    text: str
    tools_used: list[str]
    duration_sec: float
    session_id: str
    error_type: str | None = None  # SESSION_LOCK, RATE_LIMIT, TIMEOUT, SIGTERM, UNKNOWN


class ClaudeEngine:
    """Unified Claude CLI wrapper. One instance per platform."""

    def __init__(self, config: EngineConfig | None = None):
        if not shutil.which("claude"):
            raise RuntimeError("Claude CLI not found in PATH. Install: https://docs.anthropic.com/claude-code")
        self._default_config = config or EngineConfig()

    def _build_cmd(self, prompt: str, config: EngineConfig) -> list[str]:
        """Build CLI command. Stateless — no --resume."""
        cmd = [
            "claude", "-p", prompt,
            "--model", config.model,
            "--output-format", "stream-json",
            "--verbose",
        ]

        if config.effort != "standard":
            cmd.extend(["--effort", config.effort])

        if config.allowed_tools:
            cmd.extend(["--allowedTools", ",".join(config.allowed_tools)])

        if config.append_system_prompt:
            cmd.extend(["--append-system-prompt", config.append_system_prompt])

        return cmd

    def _build_env(self, config: EngineConfig) -> dict[str, str]:
        """Build environment variables for subprocess isolation."""
        env = os.environ.copy()
        env.pop("CLAUDECODE", None)
        env["CLAUDE_NONINTERACTIVE"] = "1"
        env["NEURA_CAPSULE"] = "1"

        if config.home_dir:
            os.makedirs(config.home_dir, exist_ok=True)
            env["CLAUDE_CONFIG_DIR"] = config.home_dir

        return env

    def _classify_error(self, stdout: str, stderr: str, rc: int) -> str | None:
        """Classify error type from CLI output. Returns None if no error."""
        combined = stdout + stderr

        if rc in (143, -15, 137, -9):
            return "SIGTERM"

        if "is already in use" in combined:
            return "SESSION_LOCK"

        lower = combined.lower()
        if "rate limit" in lower:
            return "RATE_LIMIT"

        if "auth" in lower and ("expired" in lower or "unauthorized" in lower or "invalid" in lower):
            return "AUTH"

        if rc != 0 and not stdout.strip():
            return "UNKNOWN"

        return None

    def _parse_event(self, event: dict) -> list[Chunk]:
        """Parse a single stream-json event into Chunks."""
        chunks = []
        etype = event.get("type", "")

        if etype == "assistant":
            for block in event.get("message", {}).get("content", []):
                block_type = block.get("type", "")
                if block_type == "text":
                    text = block.get("text", "")
                    if text:
                        chunks.append(Chunk(type="text", text=text))
                elif block_type == "tool_use":
                    tool_name = block.get("name", "")
                    label = TOOL_LABELS.get(tool_name, f"⚙️ {tool_name}")
                    chunks.append(Chunk(type="tool_start", tool=tool_name, text=label))

        elif etype == "result":
            chunks.append(Chunk(
                type="result",
                text=event.get("result", ""),
                session_id=event.get("session_id", ""),
            ))

        return chunks

    async def execute(self, prompt: str, config: EngineConfig | None = None) -> EngineResult:
        """Non-streaming: full response in one call."""
        cfg = config or self._default_config
        start = time.monotonic()

        cmd = self._build_cmd(prompt, cfg)
        # Override output format for non-streaming
        idx = cmd.index("stream-json")
        cmd[idx] = "text"

        env = self._build_env(cfg)

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=cfg.timeout
            )
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except Exception:
                pass
            return EngineResult(
                success=False, text="⏱ Таймаут. Попробуй разбить задачу на части.",
                tools_used=[], duration_sec=time.monotonic() - start,
                session_id="", error_type="TIMEOUT",
            )

        stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
        stderr = stderr_bytes.decode("utf-8", errors="replace").strip()
        duration = time.monotonic() - start

        error_type = self._classify_error(stdout, stderr, proc.returncode or 0)

        if error_type == "SESSION_LOCK":
            retry = await self._retry_with_new_session(prompt, cfg)
            if retry.success:
                return retry

        if error_type and error_type != "SESSION_LOCK":
            return EngineResult(
                success=False, text=stdout or stderr or "Техническая ошибка.",
                tools_used=[], duration_sec=duration,
                session_id="", error_type=error_type,
            )

        text = stdout or "Пустой ответ от Claude."
        return EngineResult(
            success=True, text=text, tools_used=[],
            duration_sec=duration, session_id="",
        )

    async def stream(self, prompt: str, config: EngineConfig | None = None) -> AsyncIterator[Chunk]:
        """Streaming: yield Chunks as they arrive from CLI."""
        cfg = config or self._default_config
        env = self._build_env(cfg)
        cmd = self._build_cmd(prompt, cfg)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        try:
            assert proc.stdout is not None
            while True:
                line = await asyncio.wait_for(
                    proc.stdout.readline(), timeout=cfg.timeout
                )
                if not line:
                    break
                line_str = line.decode("utf-8", errors="replace").strip()
                if not line_str:
                    continue
                try:
                    event = _json.loads(line_str)
                except _json.JSONDecodeError:
                    continue
                for chunk in self._parse_event(event):
                    yield chunk
        except asyncio.TimeoutError:
            proc.kill()
            yield Chunk(type="error", text="⏱ Таймаут.")
        finally:
            try:
                await proc.wait()
            except Exception:
                pass

    async def _retry_with_new_session(self, prompt: str, config: EngineConfig) -> EngineResult:
        """Self-healing: kill orphaned processes, retry with fresh session."""
        _kill_orphaned_claude()
        await asyncio.sleep(1)
        return await self.execute(prompt, config)


def _kill_orphaned_claude():
    """Kill hanging claude processes."""
    try:
        result = subprocess.run(
            ["pgrep", "-af", "claude.*-p"],
            capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            pid = line.split()[0]
            try:
                os.kill(int(pid), 9)
                logger.info(f"Killed orphaned claude process {pid}")
            except (ProcessLookupError, ValueError):
                pass
    except Exception:
        pass
