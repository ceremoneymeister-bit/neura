"""Tests for core/engine.py — Claude CLI wrapper.

Written BEFORE implementation (TDD Red Phase).
All tests must FAIL until Gate 3 implementation.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from dataclasses import fields


# === Data structures ===

class TestEngineConfig:
    def test_defaults(self):
        from neura.core.engine import EngineConfig
        cfg = EngineConfig()
        assert cfg.model == "sonnet"
        assert cfg.effort == "standard"
        assert cfg.timeout == 600
        assert cfg.home_dir is None
        assert isinstance(cfg.allowed_tools, list)

    def test_custom_values(self):
        from neura.core.engine import EngineConfig
        cfg = EngineConfig(model="opus", effort="high", timeout=300, home_dir="/tmp/test-home")
        assert cfg.model == "opus"
        assert cfg.effort == "high"
        assert cfg.timeout == 300
        assert cfg.home_dir == "/tmp/test-home"


class TestChunk:
    def test_text_chunk(self):
        from neura.core.engine import Chunk
        c = Chunk(type="text", text="Hello world")
        assert c.type == "text"
        assert c.text == "Hello world"
        assert c.tool == ""

    def test_tool_chunk(self):
        from neura.core.engine import Chunk
        c = Chunk(type="tool_start", tool="Read", text="📖 Читаю")
        assert c.type == "tool_start"
        assert c.tool == "Read"


class TestEngineResult:
    def test_success_result(self):
        from neura.core.engine import EngineResult
        r = EngineResult(success=True, text="Answer", tools_used=["Read"],
                         duration_sec=2.5, session_id="abc123")
        assert r.success is True
        assert r.text == "Answer"
        assert r.tools_used == ["Read"]
        assert r.error_type is None

    def test_error_result(self):
        from neura.core.engine import EngineResult
        r = EngineResult(success=False, text="Lock error", tools_used=[],
                         duration_sec=0.1, session_id="abc", error_type="SESSION_LOCK")
        assert r.success is False
        assert r.error_type == "SESSION_LOCK"


# === Command building ===

class TestInit:
    def test_claude_not_found(self):
        from unittest.mock import patch
        with patch("shutil.which", return_value=None):
            from neura.core.engine import ClaudeEngine
            with pytest.raises(RuntimeError, match="Claude CLI not found"):
                ClaudeEngine()


class TestBuildCmd:
    def test_default_config(self):
        from neura.core.engine import ClaudeEngine, EngineConfig
        engine = ClaudeEngine()
        cfg = EngineConfig()
        cmd, _ = engine._build_cmd("Hello", cfg)
        assert "claude" in cmd
        assert "-p" in cmd
        assert "Hello" in cmd
        assert "--model" in cmd
        assert "sonnet" in cmd
        assert "--output-format" in cmd
        assert "stream-json" in cmd
        # Stateless: no --resume
        assert "--resume" not in cmd

    def test_custom_model(self):
        from neura.core.engine import ClaudeEngine, EngineConfig
        engine = ClaudeEngine()
        cfg = EngineConfig(model="opus")
        cmd, _ = engine._build_cmd("Test", cfg)
        idx = cmd.index("--model")
        assert cmd[idx + 1] == "opus"

    def test_effort_mapping(self):
        from neura.core.engine import ClaudeEngine, EngineConfig
        engine = ClaudeEngine()
        # standard = no --effort flag
        cmd_std, _ = engine._build_cmd("Test", EngineConfig(effort="standard"))
        assert "--effort" not in cmd_std
        # low
        cmd_low, _ = engine._build_cmd("Test", EngineConfig(effort="low"))
        idx = cmd_low.index("--effort")
        assert cmd_low[idx + 1] == "low"
        # high
        cmd_high, _ = engine._build_cmd("Test", EngineConfig(effort="high"))
        idx = cmd_high.index("--effort")
        assert cmd_high[idx + 1] == "high"

    def test_allowed_tools(self):
        from neura.core.engine import ClaudeEngine, EngineConfig
        engine = ClaudeEngine()
        cfg = EngineConfig(allowed_tools=["Read", "Grep", "WebSearch"])
        cmd, _ = engine._build_cmd("Test", cfg)
        assert "--allowedTools" in cmd

    def test_append_system_prompt(self):
        from neura.core.engine import ClaudeEngine, EngineConfig
        engine = ClaudeEngine()
        cfg = EngineConfig(append_system_prompt="Be concise")
        cmd, _ = engine._build_cmd("Test", cfg)
        assert "--append-system-prompt" in cmd
        idx = cmd.index("--append-system-prompt")
        assert cmd[idx + 1] == "Be concise"


class TestBuildEnv:
    def test_isolation(self):
        from neura.core.engine import ClaudeEngine, EngineConfig
        engine = ClaudeEngine()
        cfg = EngineConfig()
        env = engine._build_env(cfg)
        assert env.get("CLAUDE_NONINTERACTIVE") == "1"
        assert "CLAUDECODE" not in env
        assert env.get("NEURA_CAPSULE") == "1"

    def test_home_override(self):
        from neura.core.engine import ClaudeEngine, EngineConfig
        engine = ClaudeEngine()
        cfg = EngineConfig(home_dir="/tmp/test-claude-home")
        env = engine._build_env(cfg)
        assert env.get("CLAUDE_CONFIG_DIR") == "/tmp/test-claude-home"


# === Error classification ===

class TestClassifyError:
    def test_session_lock(self):
        from neura.core.engine import ClaudeEngine
        engine = ClaudeEngine()
        err = engine._classify_error("", "Session is already in use", 1)
        assert err == "SESSION_LOCK"

    def test_sigterm(self):
        from neura.core.engine import ClaudeEngine
        engine = ClaudeEngine()
        assert engine._classify_error("", "", 143) == "SIGTERM"
        assert engine._classify_error("", "", -15) == "SIGTERM"
        assert engine._classify_error("", "", 137) == "SIGTERM"
        assert engine._classify_error("", "", -9) == "SIGTERM"

    def test_rate_limit(self):
        from neura.core.engine import ClaudeEngine
        engine = ClaudeEngine()
        err = engine._classify_error("", "rate limit exceeded", 1)
        assert err == "RATE_LIMIT"

    def test_auth_expired(self):
        from neura.core.engine import ClaudeEngine
        engine = ClaudeEngine()
        err = engine._classify_error("", "auth token expired", 1)
        assert err == "AUTH"
        err2 = engine._classify_error("", "unauthorized: invalid auth", 1)
        assert err2 == "AUTH"

    def test_no_error(self):
        from neura.core.engine import ClaudeEngine
        engine = ClaudeEngine()
        assert engine._classify_error("Some output", "", 0) is None


# === Stream parsing ===

class TestStreamParsing:
    def test_parse_text_event(self):
        """--verbose format: assistant message with text content block."""
        from neura.core.engine import ClaudeEngine
        engine = ClaudeEngine()
        event = {
            "type": "assistant",
            "message": {
                "content": [{"type": "text", "text": "Hello world"}]
            }
        }
        chunks = list(engine._parse_event(event))
        assert len(chunks) >= 1
        text_chunks = [c for c in chunks if c.type == "text"]
        assert text_chunks[0].text == "Hello world"

    def test_parse_tool_use_event(self):
        from neura.core.engine import ClaudeEngine
        engine = ClaudeEngine()
        event = {
            "type": "assistant",
            "message": {
                "content": [{"type": "tool_use", "name": "Read"}]
            }
        }
        chunks = list(engine._parse_event(event))
        tool_chunks = [c for c in chunks if c.type == "tool_start"]
        assert len(tool_chunks) >= 1
        assert tool_chunks[0].tool == "Read"
        assert "📖" in tool_chunks[0].text  # Humanized label

    def test_parse_result_event(self):
        from neura.core.engine import ClaudeEngine
        engine = ClaudeEngine()
        event = {
            "type": "result",
            "result": "Final answer",
            "session_id": "sess-123"
        }
        chunks = list(engine._parse_event(event))
        result_chunks = [c for c in chunks if c.type == "result"]
        assert len(result_chunks) == 1
        assert result_chunks[0].text == "Final answer"
        assert result_chunks[0].session_id == "sess-123"

    def test_tool_labels_exist(self):
        from neura.core.engine import TOOL_LABELS
        assert "Read" in TOOL_LABELS
        assert "Grep" in TOOL_LABELS
        assert "WebSearch" in TOOL_LABELS
        assert "Bash" in TOOL_LABELS


# === Execute (mocked subprocess) ===

class TestExecute:
    @pytest.mark.asyncio
    async def test_success(self):
        from neura.core.engine import ClaudeEngine, EngineConfig
        engine = ClaudeEngine()

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"Answer text", b""))
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await engine.execute("Hello", EngineConfig())

        assert result.success is True
        assert result.text == "Answer text"

    @pytest.mark.asyncio
    async def test_empty_response(self):
        from neura.core.engine import ClaudeEngine, EngineConfig
        engine = ClaudeEngine()

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await engine.execute("Hello", EngineConfig())

        assert result.success is True
        assert "Пустой ответ" in result.text

    @pytest.mark.asyncio
    async def test_timeout(self):
        from neura.core.engine import ClaudeEngine, EngineConfig
        engine = ClaudeEngine()

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_proc.kill = MagicMock()
        mock_proc.returncode = None

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await engine.execute("Hello", EngineConfig(timeout=1))

        assert result.success is False
        assert result.error_type == "TIMEOUT"
