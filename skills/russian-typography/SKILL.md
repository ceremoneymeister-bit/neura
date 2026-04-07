---
name: russian-typography
description: Rules for proper Russian typography and typesetting, focusing on non-breaking spaces
proactive_enabled: false
proactive_trigger_1_type: event
proactive_trigger_1_condition: "текст на русском для лендинга/бота"
proactive_trigger_1_action: "проверить неразрывные пробелы и висящие предлоги"
learning_track_success: true
learning_track_corrections: true
learning_evolve_threshold: 5
learning_auto_update: [anti-patterns, triggers, changelog]
---

# Russian Typography Guidelines

You must always follow proper typesetting rules when writing or generating Russian text, especially for user interfaces, landing pages, and professional documents.

## Hanging Prepositions (Висящие предлоги)
Hanging prepositions at the end of a line are considered a major typographic error in Russian. 
You must ALWAYS bind short words (prepositions, conjunctions, particles) to the following word using a non-breaking space (NBS).

**Rule:** Use `&nbsp;` (if writing HTML/JSX) or the appropriate non-breaking space character between the short word and the next word.

### Examples of words that require a non-breaking space after them:
*   **Prepositions:** в, на, с, к, к, у, о, об, от, из, за, до, по, под, над, перед, при, без
*   **Conjunctions:** и, а, но, да, или, ни, как, так
*   **Particles:** не, ни, бы, ли, же, то

**❌ INcorrect (Hanging preposition):**
`В 33 года я столкнулась с проблемами со здоровьем — и именно йога вернула меня к полноценной жизни.`

**✅ Correct (Using `&nbsp;`):**
`В&nbsp;33 года я столкнулась с&nbsp;проблемами со&nbsp;здоровьем — и&nbsp;именно йога вернула меня к&nbsp;полноценной жизни.`

### Application
- Applies to all UI elements (React components, HTML, etc.).
- When outputting raw Markdown that will be rendered, use standard non-breaking spaces or tell the user you are applying typographic rules.
- Note: Do NOT add `&nbsp;` to system-level code or keys, only string literals meant for display.

---

## Changelog

<!-- Сюда автоматически добавляются уроки после каждого использования скилла -->
