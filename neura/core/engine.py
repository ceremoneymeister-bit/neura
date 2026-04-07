"""ClaudeEngine — Claude CLI wrapper with streaming support.

@arch scope=platform  affects=all_capsules(14)
@arch depends=none (standalone, receives config via EngineConfig)
@arch risk=CRITICAL  restart=neura-v2
@arch role=Executes Claude CLI subprocess. All AI responses go through here.
@arch note=MemoryMax=4G in systemd. Temp files cleaned via atexit.

Supports session resume: pass resume_session_id to continue an existing
conversation instead of starting fresh.  Thread-safe: no shared mutable state.
"""
import asyncio
import atexit
import glob
import json as _json
import logging
import os
import signal
import time
import tempfile
from dataclasses import dataclass, field
from typing import AsyncIterator

logger = logging.getLogger(__name__)

# Track temp files for cleanup on exit
_temp_files: list[str] = []


def _cleanup_temp_files():
    """Remove any leftover temp files on process exit."""
    for f in _temp_files:
        try:
            os.unlink(f)
        except OSError:
            pass
    # Also clean stale files from previous runs
    for f in glob.glob("/tmp/neura_prompt_*.txt"):
        try:
            os.unlink(f)
        except OSError:
            pass


atexit.register(_cleanup_temp_files)

DEFAULT_TOOLS = ["Read", "Glob", "Grep", "Write", "Edit", "Bash(python3|ls|mkdir|cat)"]


@dataclass
class Chunk:
    """One streaming event from Claude CLI."""
    type: str  # "text", "tool_use", "tool_result", "status", "error"
    text: str = ""
    tool: str = ""
    session_id: str = ""


@dataclass
class EngineResult:
    """Final result after a full Claude CLI session."""
    success: bool
    text: str
    tools_used: list[str]
    duration_sec: float
    session_id: str
    error_type: str | None = None


@dataclass
class EngineConfig:
    model: str = "sonnet"
    effort: str = "standard"
    allowed_tools: list[str] = field(default_factory=lambda: list(DEFAULT_TOOLS))
    home_dir: str | None = None
    timeout: int = 600
    append_system_prompt: str | None = None
    resume_session_id: str | None = None  # Pass to --resume existing session


TOOL_LABELS = {
    "Read": "📖 Читаю",
    "Glob": "🔍 Ищу файлы",
    "Grep": "🔎 Ищу в коде",
    "Write": "✏️ Пишу",
    "Edit": "📝 Редактирую",
    "Bash": "⚡ Выполняю",
    "WebSearch": "🌐 Ищу в интернете",
    "WebFetch": "🌐 Загружаю",
}


def _kill_process_tree(proc) -> None:
    """Kill process and all its children via process group."""
    try:
        pgid = os.getpgid(proc.pid)
        os.killpg(pgid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    except OSError:
        # Fallback: kill just the process
        try:
            proc.kill()
        except Exception:
            pass


class ClaudeEngine:
    """Claude CLI wrapper with session resume support."""

    def __init__(self, default_config: EngineConfig | None = None):
        import shutil
        if not shutil.which("claude"):
            raise RuntimeError("Claude CLI not found. Install: npm install -g @anthropic-ai/claude-code")
        self._default_config = default_config or EngineConfig()

    def _build_cmd(self, prompt: str, config: EngineConfig) -> tuple[list[str], str | None]:
        """Build CLI command. Returns (cmd, prompt_file_path_or_None).

        When resume_session_id is set, uses --resume to continue an existing
        session instead of starting fresh.  The prompt becomes just the new
        user message (no system context needed — it's already in session).

        For prompts >120KB: writes to temp file, pipes via stdin.
        For smaller prompts: direct -p argument (safe up to 128KB).
        """
        prompt_bytes = len(prompt.encode("utf-8"))
        prompt_file = None

        if prompt_bytes > 120_000:
            fd, prompt_file = tempfile.mkstemp(suffix=".txt", prefix="neura_prompt_")
            _temp_files.append(prompt_file)
            with os.fdopen(fd, "w") as f:
                f.write(prompt)
            logger.info(f"Prompt >120KB ({prompt_bytes}B), will use stdin pipe from: {prompt_file}")
            cmd = [
                "claude", "-p", "-",
                "--model", config.model,
                "--output-format", "stream-json",
                "--verbose",
            ]
        else:
            cmd = [
                "claude", "-p", prompt,
                "--model", config.model,
                "--output-format", "stream-json",
                "--verbose",
            ]

        # Resume existing session instead of starting a new one
        if config.resume_session_id:
            cmd.extend(["--resume", config.resume_session_id])

        if config.effort != "standard":
            cmd.extend(["--effort", config.effort])

        if config.allowed_tools:
            cmd.extend(["--allowedTools", ",".join(config.allowed_tools)])

        if config.append_system_prompt:
            cmd.extend(["--append-system-prompt", config.append_system_prompt])

        return cmd, prompt_file

    def _build_env(self, config: EngineConfig) -> dict[str, str]:
        """Build environment variables for subprocess isolation."""
        env = os.environ.copy()
        env.pop("CLAUDECODE", None)
        env["CLAUDE_NONINTERACTIVE"] = "1"
        env["NEURA_CAPSULE"] = "1"

        if config.home_dir:
            os.makedirs(config.home_dir, exist_ok=True)
            # Use .bot-config/ subdirectory if it exists (isolates bot creds from user's Claude Code)
            bot_config_dir = os.path.join(config.home_dir, ".bot-config")
            if os.path.isdir(bot_config_dir):
                env["CLAUDE_CONFIG_DIR"] = bot_config_dir
            else:
                env["CLAUDE_CONFIG_DIR"] = config.home_dir

        return env

    def _classify_error(self, stdout: str, stderr: str, rc: int) -> str | None:
        """Classify error type from CLI output. Returns None if no error."""
        combined = stdout + stderr
        lower = combined.lower()

        if rc in (143, -15, 137, -9):
            return "SIGTERM"
        if "SIGTERM" in combined or "signal: terminated" in combined:
            return "SIGTERM"
        if "argument list too long" in lower or "errno 7" in lower:
            return "ARG_MAX"
        if "syntax error" in lower and "unexpected token" in lower:
            return "SHELL_SYNTAX"
        if "session is already in use" in lower or "session lock" in lower:
            return "SESSION_LOCK"
        if "timeout" in lower or "timed out" in lower:
            return "TIMEOUT"
        if "rate limit" in lower or "429" in combined:
            return "RATE_LIMIT"
        if "out of memory" in lower or "oom" in lower or rc == 137:
            return "OOM"
        if "auth" in lower and ("expired" in lower or "invalid" in lower or "unauthorized" in lower):
            return "AUTH"
        if "401" in combined or "Unauthorized" in combined:
            return "AUTH"
        if rc != 0:
            return f"EXIT_{rc}"
        return None

    async def collect(self, prompt: str, config: EngineConfig | None = None) -> list[Chunk]:
        """Collect all chunks from a streaming session."""
        chunks: list[Chunk] = []
        async for chunk in self.stream(prompt, config):
            chunks.append(chunk)
        return chunks

    async def execute(self, prompt: str, config: EngineConfig | None = None) -> EngineResult:
        """Non-streaming: full response in one call."""
        cfg = config or self._default_config
        start = time.monotonic()

        cmd, prompt_file = self._build_cmd(prompt, cfg)
        # Override output format for non-streaming
        for i, arg in enumerate(cmd):
            if arg == "stream-json":
                cmd[i] = "text"
                break

        env = self._build_env(cfg)
        stdin_data = None
        if prompt_file:
            with open(prompt_file, "r") as f:
                stdin_data = f.read().encode("utf-8")
            os.unlink(prompt_file)

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE if stdin_data else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=cfg.home_dir if cfg.home_dir else None,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(input=stdin_data), timeout=cfg.timeout
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

        error_type = self._classify_error(stdout, stderr, rc)
        if error_type:
            logger.warning(f"engine error: {error_type} (rc={rc}) — {stderr[:200]}")
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
        cmd, prompt_file = self._build_cmd(prompt, cfg)

        stdin_data = None
        if prompt_file:
            with open(prompt_file, "r") as f:
                stdin_data = f.read().encode("utf-8")
            os.unlink(prompt_file)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE if stdin_data else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            cwd=cfg.home_dir if cfg.home_dir else None,
            limit=2 * 1024 * 1024,
        )

        # If using stdin, write prompt and close stdin
        if stdin_data and proc.stdin:
            proc.stdin.write(stdin_data)
            await proc.stdin.drain()
            proc.stdin.close()

        try:
            assert proc.stdout is not None
            while True:
                # Per-line timeout: 120s (enough for tool execution)
                line = await asyncio.wait_for(
                    proc.stdout.readline(), timeout=min(cfg.timeout, 120)
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
            logger.warning("stream readline timeout, killing process tree")
            _kill_process_tree(proc)
            yield Chunk(type="error", text="Превышено время ожидания ответа.")
        except asyncio.CancelledError:
            logger.info("stream cancelled, cleaning up process tree")
            _kill_process_tree(proc)
            raise
        finally:
            try:
                if proc.returncode is None:
                    proc.terminate()
                    await asyncio.wait_for(proc.wait(), timeout=5)
            except Exception:
                _kill_process_tree(proc)
            # Log stderr if any (helps diagnose silent failures)
            if proc.stderr:
                try:
                    stderr_data = await asyncio.wait_for(proc.stderr.read(), timeout=2)
                    if stderr_data:
                        stderr_str = stderr_data.decode("utf-8", errors="replace").strip()
                        if stderr_str:
                            logger.warning(f"stream stderr: {stderr_str[:500]}")
                except Exception:
                    pass

    async def _retry_with_new_session(self, prompt: str, config: EngineConfig) -> EngineResult:
        """Self-healing: kill orphaned processes, retry with fresh session."""
        logger.info("Retrying with fresh session after error...")
        # Kill any orphaned claude processes owned by this capsule
        if config.home_dir:
            try:
                ppid = os.getpid()
                proc = await asyncio.create_subprocess_exec(
                    "pkill", "-f", f"claude.*{config.home_dir}",
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await proc.wait()
            except Exception:
                pass
        return await self.execute(prompt, config)

    def _parse_event(self, event: dict) -> list[Chunk]:
        """Parse a stream-json event into a list of Chunks."""
        etype = event.get("type", "")
        chunks: list[Chunk] = []

        if etype == "assistant" and "message" in event:
            msg = event["message"]
            session_id = event.get("session_id", "")
            for block in msg.get("content", []):
                btype = block.get("type", "")
                if btype == "text":
                    chunks.append(Chunk(type="text", text=block.get("text", ""), session_id=session_id))
                elif btype == "tool_use":
                    tool_name = block.get("name", "unknown")
                    label = TOOL_LABELS.get(tool_name, f"🔧 {tool_name}")
                    chunks.append(Chunk(type="tool_start", text=label, tool=tool_name, session_id=session_id))
            if not chunks:
                chunks.append(Chunk(type="status", text="⏳ Думаю...", session_id=session_id))
            return chunks

        if etype == "content_block_delta":
            delta = event.get("delta", {})
            if delta.get("type") == "text_delta":
                chunks.append(Chunk(type="text", text=delta.get("text", "")))

        if etype == "content_block_start":
            cb = event.get("content_block", {})
            if cb.get("type") == "tool_use":
                tool_name = cb.get("name", "unknown")
                label = TOOL_LABELS.get(tool_name, f"🔧 {tool_name}")
                chunks.append(Chunk(type="tool_start", text=label, tool=tool_name))

        if etype == "result":
            text = event.get("result", "")
            if not text:
                for block in event.get("content", []):
                    if block.get("type") == "text":
                        text += block.get("text", "")
            session_id = event.get("session_id", "")
            cost = event.get("cost_usd", 0)
            duration = event.get("duration_ms", 0) / 1000
            is_error = event.get("is_error", False)
            if is_error:
                chunks.append(Chunk(type="error", text=text or "Ошибка."))
            else:
                chunks.append(Chunk(type="result", text=text, session_id=session_id))

        return chunks
