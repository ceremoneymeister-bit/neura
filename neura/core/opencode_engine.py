"""OpenCodeEngine — OpenCode CLI wrapper with streaming support.

@arch scope=platform  affects=all_capsules
@arch depends=none (standalone, receives config via EngineConfig)
@arch risk=HIGH  restart=neura-v2
@arch role=Alternative AI engine using OpenCode CLI with any provider (OpenRouter, etc.)
@arch note=Fallback engine when Claude CLI is unavailable or blocked.

Uses the same Chunk/EngineResult interface as ClaudeEngine for seamless switching.
"""
import asyncio
import json as _json
import logging
import os
import shutil
import signal
import tempfile
import time
from typing import AsyncIterator

from neura.core.engine import Chunk, EngineConfig, EngineResult, TOOL_LABELS, _tool_label

logger = logging.getLogger(__name__)

# OpenCode binary path
_OPENCODE_BIN = None


def _find_opencode() -> str | None:
    """Find opencode binary."""
    global _OPENCODE_BIN
    if _OPENCODE_BIN:
        return _OPENCODE_BIN
    # Check common locations
    for path in [
        shutil.which("opencode"),
        os.path.expanduser("~/.opencode/bin/opencode"),
        "/root/.opencode/bin/opencode",
    ]:
        if path and os.path.isfile(path):
            _OPENCODE_BIN = path
            return path
    return None


def _kill_process_tree(proc) -> None:
    """Kill process and all its children via process group."""
    try:
        pgid = os.getpgid(proc.pid)
        if pgid == os.getpgrp():
            proc.kill()
        else:
            os.killpg(pgid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    except OSError:
        try:
            proc.kill()
        except Exception:
            pass


class OpenCodeEngine:
    """OpenCode CLI wrapper — same interface as ClaudeEngine.

    Supports any model via OpenRouter or other providers.
    Config model format: "openrouter/openai/gpt-oss-120b:free"
    """

    def __init__(self, default_config: EngineConfig | None = None):
        self._opencode_bin = _find_opencode()
        if not self._opencode_bin:
            raise RuntimeError(
                "OpenCode CLI not found. Install: curl -fsSL https://opencode.ai/install | bash"
            )
        self._default_config = default_config or EngineConfig()

    def _build_cmd(self, prompt: str, config: EngineConfig) -> list[str]:
        """Build opencode run command."""
        if not self._opencode_bin:
            self._opencode_bin = _find_opencode()
        if not self._opencode_bin:
            raise FileNotFoundError("opencode CLI not found")

        prompt = prompt.replace("\x00", "")

        # Ensure model has openrouter/ prefix for OpenRouter models
        model = config.model
        if not model.startswith("openrouter/") and not model.startswith("opencode/"):
            model = f"openrouter/{model}"

        cmd = [
            self._opencode_bin, "run",
            "-m", model,
            prompt,
        ]
        return cmd

    def _build_env(self, config: EngineConfig) -> dict[str, str]:
        """Build environment variables."""
        env = os.environ.copy()
        # Ensure OpenRouter key is available
        if "OPENROUTER_API_KEY" not in env:
            logger.warning("OPENROUTER_API_KEY not set in environment")
        # Set HOME for isolation if needed
        if config.home_dir:
            os.makedirs(config.home_dir, exist_ok=True)
        return env

    def _classify_error(self, stdout: str, stderr: str, rc: int) -> str | None:
        """Classify error type from CLI output."""
        combined = stdout + stderr
        lower = combined.lower()

        if rc in (143, -15, 137, -9):
            return "SIGTERM"
        if "timeout" in lower or "timed out" in lower:
            return "TIMEOUT"
        if "rate limit" in lower or "429" in combined:
            return "RATE_LIMIT"
        if "out of memory" in lower or rc == 137:
            return "OOM"
        if "auth" in lower and ("expired" in lower or "invalid" in lower):
            return "AUTH"
        if "401" in combined or "402" in combined:
            return "AUTH"
        if "insufficient" in lower and "balance" in lower:
            return "NO_BALANCE"
        if rc != 0:
            return f"EXIT_{rc}"
        return None

    async def execute(self, prompt: str, config: EngineConfig | None = None) -> EngineResult:
        """Non-streaming: full response in one call."""
        cfg = config or self._default_config
        start = time.monotonic()

        cmd = self._build_cmd(prompt, cfg)
        env = self._build_env(cfg)

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=cfg.home_dir if cfg.home_dir else None,
                start_new_session=True,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=cfg.timeout
            )
        except asyncio.TimeoutError:
            _kill_process_tree(proc)
            duration = time.monotonic() - start
            return EngineResult(
                success=False, text="Превышено время ожидания.",
                tools_used=[], duration_sec=duration,
                session_id="", error_type="TIMEOUT",
            )

        duration = time.monotonic() - start
        stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
        stderr = stderr_bytes.decode("utf-8", errors="replace").strip()
        rc = proc.returncode or 0

        # Clean ANSI escape codes from output
        import re
        stdout = re.sub(r'\x1b\[[0-9;]*m', '', stdout)
        # Remove the "build · model" header line
        lines = stdout.split('\n')
        clean_lines = [l for l in lines if not l.strip().startswith('> build')]
        stdout = '\n'.join(clean_lines).strip()

        error_type = self._classify_error(stdout, stderr, rc)
        if error_type:
            logger.warning(f"opencode error: {error_type} (rc={rc}) — {stderr[:200]}")
            return EngineResult(
                success=False, text=stdout or stderr or "Техническая ошибка.",
                tools_used=[], duration_sec=duration,
                session_id="", error_type=error_type,
            )

        return EngineResult(
            success=True, text=stdout or "Пустой ответ.",
            tools_used=[], duration_sec=duration, session_id="",
        )

    async def stream(self, prompt: str, config: EngineConfig | None = None) -> AsyncIterator[Chunk]:
        """Streaming: yield Chunks as they arrive.

        OpenCode doesn't have stream-json like Claude CLI,
        so we read output line by line and emit text chunks.
        For tool usage, we parse the output markers.
        """
        cfg = config or self._default_config
        env = self._build_env(cfg)
        cmd = self._build_cmd(prompt, cfg)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            cwd=cfg.home_dir if cfg.home_dir else None,
            start_new_session=True,
        )

        import re
        text_buffer = []
        try:
            assert proc.stdout is not None
            while True:
                line = await asyncio.wait_for(
                    proc.stdout.readline(),
                    timeout=min(cfg.timeout, 360),
                )
                if not line:
                    break
                line_str = line.decode("utf-8", errors="replace").rstrip()

                # Clean ANSI codes
                clean = re.sub(r'\x1b\[[0-9;]*m', '', line_str)

                # Skip header line
                if clean.strip().startswith('> build'):
                    yield Chunk(type="status", text="⏳ Думаю...")
                    continue

                # Detect tool usage markers from OpenCode output
                if clean.startswith('→ '):
                    # Tool start: "→ Read file.txt"
                    tool_info = clean[2:].strip()
                    tool_name = tool_info.split(' ')[0] if ' ' in tool_info else tool_info
                    label = TOOL_LABELS.get(tool_name, f"🔧 {tool_name}")
                    detail = ' '.join(tool_info.split(' ')[1:])
                    if detail:
                        label = f"{label} · {detail}"
                    yield Chunk(type="tool_start", text=label, tool=tool_name)
                    continue

                if clean.startswith('$ '):
                    # Bash command
                    cmd_text = clean[2:]
                    yield Chunk(type="tool_start", text=f"⚡ Выполняю · {cmd_text[:60]}", tool="Bash")
                    continue

                # Regular text
                if clean.strip():
                    yield Chunk(type="text", text=clean)
                    text_buffer.append(clean)

        except asyncio.TimeoutError:
            logger.warning("opencode stream timeout")
            _kill_process_tree(proc)
            yield Chunk(type="error", text="Превышено время ожидания.")
        except asyncio.CancelledError:
            _kill_process_tree(proc)
            raise
        finally:
            try:
                if proc.returncode is None:
                    proc.terminate()
                    await asyncio.wait_for(proc.wait(), timeout=5)
            except Exception:
                _kill_process_tree(proc)

        # Emit final result
        full_text = '\n'.join(text_buffer)
        if full_text:
            yield Chunk(type="result", text=full_text)
