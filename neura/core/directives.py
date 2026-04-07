"""Auto-reply directives parser.

Extracts !directives from user messages:
  !elevated   — switch to opus model + high effort for this request
  !think      — add "show your reasoning step by step" to prompt
  !queue      — add to BTW queue without immediate response
  !fast       — use haiku model for quick reply
  !web        — force web search for this request
  !brief      — request ultra-short response (1-2 sentences)

Directives are stripped from the message text before processing.
Multiple directives can be combined: "!elevated !think Проанализируй..."
"""
import re
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

DIRECTIVE_RE = re.compile(r"!(elevated|think|queue|fast|web|brief)\b", re.IGNORECASE)


@dataclass
class ParsedDirectives:
    """Result of parsing directives from a message."""
    clean_text: str           # Message with directives stripped
    elevated: bool = False    # Use opus + high effort
    think: bool = False       # Show reasoning
    queue: bool = False       # Queue without response
    fast: bool = False        # Use haiku
    web: bool = False         # Force web search
    brief: bool = False       # Ultra-short response
    raw_directives: list[str] = field(default_factory=list)

    @property
    def has_any(self) -> bool:
        return bool(self.raw_directives)

    def apply_to_engine_config(self, engine_config) -> None:
        """Mutate EngineConfig based on parsed directives."""
        if self.elevated:
            engine_config.model = "opus"
            engine_config.effort = "high"
        elif self.fast:
            engine_config.model = "haiku"

        if self.web:
            if "WebSearch" not in engine_config.allowed_tools:
                engine_config.allowed_tools.append("WebSearch")
            if "WebFetch" not in engine_config.allowed_tools:
                engine_config.allowed_tools.append("WebFetch")

    def apply_to_prompt(self, prompt: str) -> str:
        """Add directive instructions to prompt."""
        additions = []

        if self.think:
            additions.append(
                "\n[ДИРЕКТИВА: покажи ход рассуждений пошагово, "
                "перед финальным ответом]"
            )
        if self.brief:
            additions.append(
                "\n[ДИРЕКТИВА: ответь максимально кратко, 1-2 предложения]"
            )
        if self.web:
            additions.append(
                "\n[ДИРЕКТИВА: обязательно используй WebSearch для поиска "
                "актуальной информации]"
            )

        if additions:
            return prompt + "\n".join(additions)
        return prompt


def parse_directives(text: str) -> ParsedDirectives:
    """Parse !directives from message text.

    Returns ParsedDirectives with clean_text (directives stripped)
    and boolean flags for each directive found.
    """
    found = DIRECTIVE_RE.findall(text)
    if not found:
        return ParsedDirectives(clean_text=text)

    # Strip directives from text
    clean = DIRECTIVE_RE.sub("", text).strip()
    # Collapse multiple spaces
    clean = re.sub(r"\s{2,}", " ", clean)

    directives = [d.lower() for d in found]
    logger.info(f"Parsed directives: {directives}")

    return ParsedDirectives(
        clean_text=clean,
        elevated="elevated" in directives,
        think="think" in directives,
        queue="queue" in directives,
        fast="fast" in directives,
        web="web" in directives,
        brief="brief" in directives,
        raw_directives=directives,
    )
