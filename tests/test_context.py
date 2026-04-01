"""Tests for core/context.py — Prompt Assembly.

TDD Red Phase — written BEFORE implementation.
"""
import os
import pytest
from unittest.mock import patch
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures" / "capsules"


def _make_capsule():
    """Helper: load test capsule for context tests."""
    from neura.core.capsule import Capsule
    with patch.dict(os.environ, {"TEST_BOT_TOKEN": "tok"}):
        return Capsule.load("test_capsule", config_dir=str(FIXTURES))


class TestBuildFirstMessage:
    def test_full_context(self):
        from neura.core.context import ContextBuilder, ContextParts
        capsule = _make_capsule()
        builder = ContextBuilder(capsule)
        parts = ContextParts(
            system_prompt="You are Test Bot.",
            today_diary="10:00 User asked about weather",
            recent_diary="[31.03] Discussed plans",
            memory="User likes concise answers",
            learnings="Always check timezone",
            corrections="Don't use emojis",
        )
        result = builder.build("What's the weather?", parts, is_first_message=True)
        assert "You are Test Bot." in result
        assert "weather" in result  # user prompt
        assert "10:00 User asked" in result  # today diary
        assert "Discussed plans" in result  # recent diary
        assert "concise answers" in result  # memory
        assert "Always check timezone" in result  # learnings
        assert "Don't use emojis" in result  # corrections

    def test_subsequent_message_minimal(self):
        from neura.core.context import ContextBuilder, ContextParts
        capsule = _make_capsule()
        builder = ContextBuilder(capsule)
        parts = ContextParts(memory="relevant context")
        result = builder.build("Follow up question", parts, is_first_message=False)
        # Should NOT include system prompt on follow-up
        assert "Follow up question" in result
        assert "relevant context" in result

    def test_empty_parts(self):
        from neura.core.context import ContextBuilder, ContextParts
        capsule = _make_capsule()
        builder = ContextBuilder(capsule)
        parts = ContextParts()
        result = builder.build("Simple question", parts, is_first_message=True)
        assert "Simple question" in result
        # Should still be a valid prompt, not empty
        assert len(result) > len("Simple question")


class TestTruncation:
    def test_truncate_long_content(self):
        from neura.core.context import ContextBuilder, ContextParts
        capsule = _make_capsule()
        builder = ContextBuilder(capsule)
        long_text = "A" * 5000
        parts = ContextParts(learnings=long_text)
        result = builder.build("Test", parts, is_first_message=True)
        # Learnings should be truncated, not full 5000 chars
        assert result.count("A") < 5000


class TestFormatSection:
    def test_with_content(self):
        from neura.core.context import ContextBuilder
        capsule = _make_capsule()
        builder = ContextBuilder(capsule)
        result = builder._format_section("📋 Diary", "Entry 1\nEntry 2")
        assert "📋 Diary" in result
        assert "Entry 1" in result

    def test_empty_content_returns_empty(self):
        from neura.core.context import ContextBuilder
        capsule = _make_capsule()
        builder = ContextBuilder(capsule)
        result = builder._format_section("📋 Diary", "")
        assert result == ""


class TestTruncateTail:
    def test_truncates_to_tail(self):
        from neura.core.context import ContextBuilder
        capsule = _make_capsule()
        builder = ContextBuilder(capsule)
        text = "AAAA" + "BBBB"
        result = builder._truncate_tail(text, 4)
        assert result == "BBBB"

    def test_short_text_unchanged(self):
        from neura.core.context import ContextBuilder
        capsule = _make_capsule()
        builder = ContextBuilder(capsule)
        result = builder._truncate_tail("short", 100)
        assert result == "short"
