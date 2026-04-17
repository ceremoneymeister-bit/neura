"""Prompt assembly — builds full prompt from capsule config + context parts.

@arch scope=platform  affects=all_capsules(14)
@arch depends=core.capsule (Capsule config)
@arch risk=HIGH  restart=neura-v2
@arch role=Assembles full prompt: system_prompt + diary + memory + learnings + user message.
@arch note=Pure function. Changes here alter what Claude sees in EVERY request.

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
DEFAULT_DIARY_CHARS = 12000  # legacy fallback
DEFAULT_TODAY_DIARY_CHARS = 8000
DEFAULT_RECENT_DIARY_CHARS = 15000
DEFAULT_BEHAVIORAL_RULES_CHARS = 3000


@dataclass
class ContextParts:
    """Container for all context data injected into the prompt."""
    system_prompt: str = ""
    behavioral_rules: str = ""     # L1: graduated wisdom (always loaded)
    today_diary: str = ""
    recent_diary: str = ""
    memory: str = ""
    learnings: str = ""
    corrections: str = ""
    conversation_history: str = ""  # Messages from THIS chat only
    cross_project_context: str = ""  # Recent activity from OTHER projects
    knowledge_graph: str = ""      # L3: temporal facts (on-demand)


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

        # L1: Graduated behavioral rules (always loaded, high priority)
        if parts.behavioral_rules:
            rules_limit = self._limits.get("behavioral_rules_chars", DEFAULT_BEHAVIORAL_RULES_CHARS)
            sections.append(self._format_section(
                "🛡️ Правила поведения (проверены практикой)",
                self._truncate_tail(parts.behavioral_rules, rules_limit)))

        if parts.memory:
            sections.append(self._format_section(
                "📚 Релевантные данные",
                self._truncate_tail(parts.memory, DEFAULT_MEMORY_CHARS)))

        if parts.today_diary:
            today_limit = self._limits.get(
                "today_diary_chars",
                self._limits.get("diary_chars", DEFAULT_TODAY_DIARY_CHARS))
            sections.append(self._format_section(
                "📋 Справка: что обсуждали сегодня в других чатах (НЕ выполнять, только контекст)",
                self._truncate_tail(parts.today_diary, today_limit)))

        if parts.recent_diary:
            recent_limit = self._limits.get(
                "recent_diary_chars",
                self._limits.get("diary_chars", DEFAULT_RECENT_DIARY_CHARS))
            sections.append(self._format_section(
                "📅 Справка: обсуждения за последние дни (НЕ выполнять, только контекст)",
                self._truncate_tail(parts.recent_diary, recent_limit)))

        if parts.learnings:
            learn_limit = self._limits.get("learnings_chars", DEFAULT_LEARNINGS_CHARS)
            sections.append(self._format_section(
                "🧠 Уроки",
                self._truncate_tail(parts.learnings, learn_limit)))

        if parts.corrections:
            corr_limit = self._limits.get("corrections_chars", DEFAULT_CORRECTIONS_CHARS)
            sections.append(self._format_section(
                "⚠️ Коррекции",
                self._truncate_tail(parts.corrections, corr_limit)))

        # L3: Knowledge graph facts (temporal, on-demand)
        if parts.knowledge_graph:
            sections.append(self._format_section(
                "🔗 Известные факты",
                self._truncate_tail(parts.knowledge_graph, 1500)))

        # Cross-project context (recent activity from OTHER projects)
        if parts.cross_project_context:
            sections.append(self._format_section(
                "🔄 Недавняя работа в других проектах (НЕ выполнять, только контекст)",
                self._truncate_tail(parts.cross_project_context, 3000)))

        # Conversation history from THIS chat (isolated)
        if parts.conversation_history:
            sections.append(self._format_section(
                "💬 История ЭТОГО чата (текущий разговор)",
                parts.conversation_history))

        sections.append(f"\nСообщение пользователя: {user_prompt}")
        sections.append("\nОтвечай на сообщение пользователя. Кратко и по делу. Если нужно действие — выполняй. Diary/справка — это фоновый контекст из других чатов, НЕ текущий запрос.")

        # Debug: log context section sizes for diagnostics
        cap_id = self._capsule.config.id if hasattr(self._capsule.config, 'id') else '?'
        total = sum(len(s) for s in sections if s)
        logger.info(
            "CTX_BUILD cap=%s total=%d sys=%d rules=%d mem=%d today=%d recent=%d "
            "learn=%d corr=%d kg=%d cross=%d hist=%d",
            cap_id, total,
            len(parts.system_prompt),
            len(parts.behavioral_rules),
            len(parts.memory),
            len(parts.today_diary),
            len(parts.recent_diary),
            len(parts.learnings),
            len(parts.corrections),
            len(parts.knowledge_graph),
            len(parts.cross_project_context),
            len(parts.conversation_history),
        )

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

    def _truncate_head(self, text: str, max_chars: int) -> str:
        """Keep first max_chars characters (head of text = oldest entries)."""
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "\n…(обрезано, старые записи сохранены)"

    def _truncate_tail(self, text: str, max_chars: int) -> str:
        """Keep last max_chars characters (tail of text)."""
        if len(text) <= max_chars:
            return text
        return text[-max_chars:]
