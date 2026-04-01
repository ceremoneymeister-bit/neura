"""Prompt assembly — builds full prompt from capsule config + context parts.

Pure function: (capsule, prompt, parts) → assembled prompt string.
No side effects, no file I/O, no database calls.
Data sources (diary, memory) are provided via ContextParts.
"""
import logging
from dataclasses import dataclass

from neura.core.capsule import Capsule

logger = logging.getLogger(__name__)

# Default max chars for context sections
DEFAULT_LEARNINGS_CHARS = 1500
DEFAULT_CORRECTIONS_CHARS = 1500
DEFAULT_MEMORY_CHARS = 2000
DEFAULT_DIARY_CHARS = 3000


@dataclass
class ContextParts:
    """Container for all context data injected into the prompt."""
    system_prompt: str = ""
    today_diary: str = ""
    recent_diary: str = ""
    memory: str = ""
    learnings: str = ""
    corrections: str = ""


class ContextBuilder:
    """Assembles full prompt from capsule config + context parts."""

    def __init__(self, capsule: Capsule):
        self._capsule = capsule
        self._limits = capsule.config.memory.get("context_window", {})

    def build(self, user_prompt: str, parts: ContextParts,
              is_first_message: bool = True) -> str:
        """Assemble full prompt for ClaudeEngine.

        First message: full context (system prompt, diary, memory, learnings).
        Subsequent messages: minimal context (memory + prompt).
        """
        if is_first_message:
            return self._build_first(user_prompt, parts)
        return self._build_followup(user_prompt, parts)

    def _build_first(self, user_prompt: str, parts: ContextParts) -> str:
        """Full context for first message in session."""
        sections = []

        if parts.system_prompt:
            sections.append(self._format_section(
                "[Правила агента]", parts.system_prompt))

        if parts.memory:
            sections.append(self._format_section(
                "📚 Релевантные данные",
                self._truncate_tail(parts.memory, DEFAULT_MEMORY_CHARS)))

        if parts.today_diary:
            sections.append(self._format_section(
                "📋 Сегодня обсуждали", parts.today_diary))

        if parts.recent_diary:
            sections.append(self._format_section(
                "📅 Недавно обсуждали", parts.recent_diary))

        if parts.learnings:
            sections.append(self._format_section(
                "🧠 Уроки",
                self._truncate_tail(parts.learnings, DEFAULT_LEARNINGS_CHARS)))

        if parts.corrections:
            sections.append(self._format_section(
                "⚠️ Коррекции",
                self._truncate_tail(parts.corrections, DEFAULT_CORRECTIONS_CHARS)))

        sections.append(f"\nЗадача: {user_prompt}")
        sections.append("\nОтвечай кратко и по делу. Если нужно действие — выполняй.")

        return "\n".join(s for s in sections if s)

    def _build_followup(self, user_prompt: str, parts: ContextParts) -> str:
        """Minimal context for follow-up messages."""
        if parts.memory:
            return f"📚 Доп. контекст:\n{parts.memory}\n\n{user_prompt}"
        return user_prompt

    def _format_section(self, label: str, content: str,
                        max_chars: int = 0) -> str:
        """Format a labeled section. Returns empty string if content is empty."""
        if not content or not content.strip():
            return ""
        if max_chars > 0:
            content = self._truncate_tail(content, max_chars)
        return f"\n{label}\n{content}"

    def _truncate_tail(self, text: str, max_chars: int) -> str:
        """Keep last max_chars characters (tail of text)."""
        if len(text) <= max_chars:
            return text
        return text[-max_chars:]
