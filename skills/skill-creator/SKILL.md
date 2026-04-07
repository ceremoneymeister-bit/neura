---
name: skill-creator
description: This skill should be used when the user asks to create a new skill, improve an existing skill, evaluate skill quality, or package domain knowledge into a reusable Claude Code skill.
version: 3.0.0
author: Dmitry Rostovtsev (ceremoneymeister)
created: 2025-02-01
updated: 2026-03-25
platforms: [claude-code]
category: meta
tags: [automation, scaffolding, skill-creation, meta-skill, tdd, scoring]
risk: safe
source: internal
usage_count: 2
last_used: 2026-04-01
maturity: seed
proactive_enabled: true
proactive_trigger_1_type: event
proactive_trigger_1_condition: "создание/улучшение скилла"
proactive_trigger_1_action: "TDD + scoring workflow"
proactive_trigger_2_type: threshold
proactive_trigger_2_condition: "задача повторяется 3+ раз без скилла"
proactive_trigger_2_action: "предложить создать seed-скилл"
learning_track_success: true
learning_track_corrections: true
learning_evolve_threshold: 3
learning_auto_update: [anti-patterns, triggers, changelog, scoring-criteria]
---

# skill-creator

## Purpose

Create, evaluate, and improve Claude Code skills using TDD methodology, quality scoring, and iterative refinement. Based on best practices from Skill Conductor, Anthropic Official, and 49+ production skills in the Antigravity ecosystem.

## When to Use This Skill

- User wants to create a new Claude Code skill
- User wants to evaluate or improve an existing skill
- User needs to package domain knowledge into a reusable skill
- User says "create skill", "make skill", "build skill", "new skill"
- User says "improve skill", "fix skill", "evaluate skill", "score skill"

## Three Operating Modes

### Quick Mode (Phases 3→4→4.5→6)
**Trigger:** "оформи как скилл", "package this as a skill", user already has working workflow
- Skip discovery and design — user already knows what they want
- Go straight to creation → validation → **Production Readiness Audit** → installation
- ⛔ **Phase 4.5 ОБЯЗАТЕЛЬНА даже в Quick Mode.** Без неё скиллы выходят с crash-багами и ложными утверждениями
- Phase 5 (Scoring) пропускается ТОЛЬКО если пользователь явно сказал "без скоринга". Иначе — выполнить
- **Если выбираешь Quick Mode — сообщи:** "Quick Mode: пропускаю Phase 1-2, но Phase 4.5 (audit) обязательна. Скоринг Phase 5 — делать? (Да / Нет)"

### Product Mode (Phases 1→2→3→4→5→6)
**Trigger:** "создай скилл для...", "I need a skill that...", new capability from scratch
- Full cycle with TDD, scoring, and iteration
- Minimum 2 iterations before finalizing

### Edit Mode (Phase 5 → fix → Phase 5)
**Trigger:** "улучши скилл", "этот скилл не работает", "score this skill"
- Evaluate existing skill → identify weaknesses → fix → re-evaluate
- Continue until score ≥ 50/60

---

## Phase 1: Reconnaissance (Product Mode)

**Goal:** Understand the landscape before creating anything.

### 1.1 Check for Duplicates
Read the skill routing table in CLAUDE.md. Check both `.agent/skills/` and `~/.claude/skills/`:
```bash
ls .agent/skills/ ~/.claude/skills/ 2>/dev/null
```

**Decision gate:** If a similar skill exists → propose extending it (Edit Mode) instead of creating new.

### 1.2 Analyze Adjacent Skills
Identify skills that overlap or could synergize. Read their SKILL.md files to understand:
- What they cover (avoid duplication)
- What patterns they use (adopt proven approaches)
- What gaps exist (the new skill should fill gaps)

### 1.3 Define the Mission
Clarify with the user:
- **What problem does this skill solve?** (concrete, not abstract)
- **Who is the user?** (Claude Code agent, human developer, both?)
- **What triggers should activate this skill?** (specific phrases/contexts)
- **What does "done well" look like?** (success criteria)

### 1.4 Classify the Skill Type
Two fundamental types (choose one):

| Type | Description | Testing Strategy |
|------|-------------|-----------------|
| **Capability Uplift** | Gives the agent a NEW ability it cannot do alone | Test: run task WITHOUT skill → confirm failure → add skill → confirm success |
| **Encoded Preference** | Enforces a specific ORDER or STYLE of doing things | Test: run task WITHOUT skill → compare quality → add skill → confirm improvement |

**Output:** Brief (3-5 lines) reconnaissance summary. Proceed to Phase 2.

---

## Phase 2: Design (Product Mode)

### 2.1 TDD-First Validation

**Critical step — do NOT skip.**

Run the target task WITHOUT the skill. Document:
- What the agent does by default
- Where it fails or produces suboptimal results
- What specific improvements the skill should bring

This becomes the **baseline** for Phase 5 evaluation.

### 2.2 Choose Architectural Pattern

Select ONE primary pattern:

| Pattern | When to Use | Example |
|---------|-------------|---------|
| **Sequential** | Linear steps, each depends on previous | copywriting: context → brief → writing |
| **Iterative** | Quality improves through cycles | frontend-design: design → score → refine → re-score |
| **Context-Aware** | Different paths based on input | regru: deploy vs DNS vs SSL → different workflows |
| **Domain Intelligence** | Specialized knowledge retrieval | ui-ux-pro-max: style guides, palettes, patterns |
| **Multi-MCP** | Coordinates multiple external services | content-creator: web search + file ops + API calls |

### 2.3 Choose Constraint Level

| Level | Style | Best For | Risk |
|-------|-------|----------|------|
| **Low** | Script-like, exact steps | Deployments, migrations | Low — agent follows precisely |
| **Medium** | Pseudocode, decision points | Analysis, audits | Medium — agent has some freedom |
| **High** | Natural language guidance | Creative tasks, strategy | High — agent interprets freely |

### 2.4 Write the Skeleton

Draft the SKILL.md structure (do NOT write content yet):

```
Purpose → When to Use → Triggers → Core Workflow → Quality Standards → Anti-Patterns → References
```

**⚠️ CRITICAL RULE:** The `description` field in YAML frontmatter must say WHAT the skill does and WHEN to use it. NEVER put HOW (process steps) in description — the model reads description first and may skip the body if steps are already there.

**Output:** Skeleton structure + design decisions. Get user approval before proceeding.

---

## Phase 3: Creation

### 3.1 Generate SKILL.md

Use the template from `references/skill-template.md`. Fill in:

**Frontmatter:**
```yaml
---
name: {kebab-case-name}
description: "This skill should be used when {triggers}. It {what it does}."
version: 1.0.0
author: {from git config or user input}
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
category: {category}
tags: [{relevant, tags}]
risk: {safe|low|medium|high}
source: {internal|community|official}
---
```

**Body structure (see `references/skill-template.md` for full template):**
1. **Purpose** — 2-3 sentences, concrete
2. **When to Use** — bullet list of trigger conditions
3. **Core Workflow** — numbered phases with decision gates
4. **Quality Standards** — scoring or checklist
5. **Anti-Patterns** — what NOT to do (minimum 3)
6. **References** — links to references/ files

**Word count target:** 800-2000 words for SKILL.md. Move detailed content to references/.

### 3.2 Generate References (if needed)

Create files in `references/` for:
- Detailed guides (> 500 words of domain knowledge)
- Examples (input/output pairs)
- Templates (reusable structures)
- Checklists (pre-delivery verification)

### 3.3 Generate Scripts (if needed)

Python scripts in `scripts/` for:
- Validation logic
- Data processing
- CLI tools
- Automation helpers

### 3.4 Generate README.md

Short (200-400 words):
- What the skill does
- When to use it
- File structure
- Quick start

### 3.5 Create Directory Structure

```bash
SKILL_NAME="your-skill-name"
SKILL_PATH=".agent/skills/$SKILL_NAME"
mkdir -p "$SKILL_PATH"/{references,scripts}
```

**Output:** All files created. Display file tree with word counts.

---

## Phase 4: Validation

### 4.1 Security Scan

```bash
skill-scanner scan {skill_path}
```

**Hard gate:** CRITICAL findings = 0 required. Any CRITICAL → fix before proceeding.
HIGH findings → review manually (false positives possible for browser/exec skills).

### 4.2 Structural Validation

Run `scripts/quick_validate.py` or check manually:
- [ ] YAML frontmatter present and valid
- [ ] `name` is kebab-case
- [ ] `description` starts with "This skill should be used when"
- [ ] `description` does NOT contain process steps
- [ ] SKILL.md word count: 800-2000
- [ ] References word count: unlimited but each file < 5000
- [ ] Anti-Patterns section exists (minimum 3 items)
- [ ] No second-person ("you should") — use imperative ("Do X")

### 4.3 Quality Pre-Score

Quick assessment before full testing (Phase 5):

| Check | Pass? |
|-------|-------|
| Purpose is concrete (not abstract) | |
| Triggers are specific (not vague) | |
| Workflow has decision gates | |
| Anti-patterns are from real experience | |
| Examples show input AND output | |

**Output:** Validation report. Fix any issues before Phase 4.5.

---

## Phase 4.5: Production Readiness Audit (MANDATORY)

**Goal:** Поймать критические ошибки ДО тестирования. Каждый чек — hard gate.

> **Происхождение:** Эта фаза создана после аудита smart-outreach (2026-03-25), где skill-creator v2 пропустил 11 багов (3 критических). Все 6 чеков ниже = реальные пробелы, найденные в production.

### Check 1 — Executability Audit (0 unexecutable claims)

Grep SKILL.md на слова: "автоматически", "auto", "проверяет", "обновляется", "пополняется", "self-learning", "проактивно".

Для КАЖДОГО найденного вхождения → ответить: **ГДЕ КОД?**

| Утверждение в SKILL.md | Подкреплено кодом? | Где? |
|------------------------|-------------------|------|
| "автоматически обновляется" | ? | script.py / engine.py / hook? |
| ... | ... | ... |

**Hard gate:** Если утверждение не подкреплено исполняемым кодом (Python script, shell hook, cron) → либо написать код, либо переформулировать ("обновляется вручную по запросу").

**Антипаттерн-пример:** `anti-patterns.md` в smart-outreach заявлял "пополняется автоматически из corrections.jsonl" — но не было ни строчки кода. Пришлось писать `engine.py promote` постфактум.

### Check 2 — Portability Check (если capsule-relevant)

**Когда проверять:** Если скилл может быть полезен в клиентских капсулах (боты, агенты).

1. Grep все файлы скилла на:
   - Конкретные имена ("Дмитрий", "Antigravity", конкретные @username)
   - Абсолютные пути ("/root/Antigravity/", ".secrets/")
   - Hardcoded tokens, API keys, session paths
   - Конкретные TG ID, chat ID

2. Для каждого найденного:
   - Вынести в config/переменные (`{{OWNER_NAME}}`, `{{AGENT_INTRO}}`)
   - ИЛИ пометить как Antigravity-only (не портируется)

3. Если скилл отправляет сообщения:
   - Antigravity: Telethon (userbot)
   - Capsule: Bot API (через бота)
   - Нужна capsule-версия с Bot API

**Hard gate:** 0 hardcoded owner-specific значений в портируемых файлах.

### Check 3 — Data Schema Integrity

Для КАЖДОГО файла данных (JSON, JSONL, CSV):

| Файл | Поля | Обязательные | Кто заполняет | Что при пустом? |
|------|------|-------------|---------------|----------------|
| ? | ? | ? | ? | ? |

Проверить:
- [ ] Пустой файл → скрипт/скилл не падает
- [ ] Файл не существует → создаётся автоматически или graceful error
- [ ] Каждое `null` поле → задокументировано кто и когда его заполнит
- [ ] Schema достаточна (не пропущены поля, которые нужны для отчётов/аналитики)

**Антипаттерн-пример:** tracker.jsonl в smart-outreach не имел полей `channel`, `outcome_date` — невозможно было отследить через какой канал отправлено и когда получен ответ.

### Check 4 — Scoring Calibration (если есть скоринг)

**Когда проверять:** Если скилл содержит систему оценки (баллы, рейтинги, scoring).

- [ ] Минимум 2 калибровочные пары: "плохой результат" (score ≤ 40%) + "хороший результат" (score ≥ 80%)
- [ ] Каждая пара показывает КОНКРЕТНЫЙ пример с оценкой
- [ ] Явное правило: "Claude склонен завышать самооценку — будь строже"
- [ ] Если score < порога → указать КОНКРЕТНО какой критерий провален

**Антипаттерн-пример:** CLEAR в smart-outreach имел только позитивные примеры (22-25/25). Claude всегда оценивал свои сообщения на 4-5. Без негативных калибровочных пар (8-9/25) скоринг бесполезен.

### Check 5 — Safety Constraints (если внешние взаимодействия)

**Когда проверять:** Если скилл отправляет сообщения, деплоит код, вызывает API, модифицирует данные других систем.

| Constraint | Реализовано? | Как? |
|-----------|-------------|------|
| **Time-of-day** (не ночью) | ? | script / check в workflow? |
| **Rate limit** (не спамить) | ? | cooldown / counter? |
| **Confirmation gate** (спросить перед действием) | ? | в workflow? |
| **Rollback** (откатить если ошибка) | ? | backup / undo? |
| **Recipient protection** (не слать кому не надо) | ? | whitelist / blacklist? |

**Hard gate:** Минимум confirmation gate для всех необратимых действий.

### Check 6 — Self-Test (если есть скрипты)

Для КАЖДОГО скрипта в скилле:

```bash
# 1. Проверить что запускается
python3 script.py --help  # или без аргументов

# 2. Тестовый вызов (dry-run если есть)
python3 script.py [test_command] --dry-run

# 3. Для data-файлов: записать → прочитать → удалить
```

**Hard gate:** Все скрипты запускаются без ошибок. Тестовые данные записываются и читаются корректно.

### Итог Phase 4.5

```
Production Readiness Audit:
  ✅ Check 1 — Executability: X claims, X backed by code
  ✅ Check 2 — Portability: [capsule-ready / antigravity-only]
  ✅ Check 3 — Data Schema: X files, X fields validated
  ✅ Check 4 — Scoring: [N/A / X calibration pairs]
  ✅ Check 5 — Safety: [N/A / X constraints implemented]
  ✅ Check 6 — Self-Test: X scripts tested, 0 errors
```

**Если любой чек ❌ → НЕ переходить к Phase 5. Исправить и перепроверить.**

---

## Phase 5: Testing & Scoring (Product Mode + Edit Mode)

### 5.1 Run Test Case

Execute the target task WITH the skill active. Compare against baseline from Phase 2.1.

Three evaluation levels:

**Level 1 — Discovery:**
- Does the skill trigger on the right phrases?
- Does it NOT trigger on unrelated phrases?
- Is the routing in CLAUDE.md accurate?

**Level 2 — Logic:**
- Does the workflow execute correctly end-to-end?
- Are decision gates working?
- Does it produce the expected output?

**Level 3 — Edge Cases:**
- What happens with minimal input?
- What happens with ambiguous input?
- What happens when external tools fail?

### 5.2 Score on 6 Axes (1-10 each, total 60)

| Axis | 1-3 (Poor) | 4-6 (Acceptable) | 7-8 (Good) | 9-10 (Excellent) |
|------|-----------|-------------------|-------------|-------------------|
| **Discovery** | Wrong triggers, conflicts | Sometimes triggers correctly | Reliable triggers | Perfect routing, no false positives |
| **Clarity** | Ambiguous, confusing | Mostly clear, some gaps | Clear workflow, minor ambiguities | Crystal clear, no interpretation needed |
| **Efficiency** | Wastes tokens, redundant steps | Some waste, acceptable | Lean workflow, focused | Minimal tokens, maximum output |
| **Robustness** | Fails on edge cases | Handles common cases | Handles most edge cases | Graceful degradation everywhere |
| **Executability** | "Auto" claims without code | Some claims backed by code | All claims executable, minor gaps | Every claim has tested code + self-test passes |
| **Completeness** | Missing critical sections | Has basics, missing depth | Complete with anti-patterns + calibration | Complete + examples + references + safety |

**Scoring thresholds:**
- **≥ 50/60** → Production-ready. Proceed to Phase 6
- **40-49/60** → Good but needs polish. One more iteration
- **30-39/60** → Significant gaps. Revisit Phase 2/3
- **< 30/60** → Fundamental issues. Redesign from scratch

**Executability scoring guide:**
- 1-3: SKILL.md says "автоматически обновляется" but there's no script/engine
- 4-6: Scripts exist but untested, or data files have incomplete schemas
- 7-8: All scripts tested, data schemas documented, but no capsule portability
- 9-10: Full engine with CLI, self-test passes, calibration pairs for scoring, capsule-ready

### 5.3 Iterate

If score < 50:
1. Identify the lowest-scoring axis
2. Diagnose ROOT CAUSE (not symptoms)
3. Fix in the appropriate phase (design → Phase 2, content → Phase 3, structure → Phase 4, executability → Phase 4.5)
4. Re-test and re-score
5. Minimum 2 iterations before declaring "good enough"

**Rule:** Fix the cause, not the symptom. If Discovery is low, don't just add more trigger words — ask why the description isn't working. If Executability is low, don't add comments — write actual code.

**Output:** Score card with breakdown. If ≥ 50 → proceed. If < 50 → iterate.

---

## Phase 6: Installation & Registration

### 6.1 Install the Skill

**Local (project-level):**
```bash
# Already in .agent/skills/ from Phase 3
ls -la .agent/skills/$SKILL_NAME/
```

**Global (user-level):**
```bash
cp -r .agent/skills/$SKILL_NAME ~/.claude/skills/$SKILL_NAME
```

### 6.2 Register in CLAUDE.md

Add a row to the skill routing table in CLAUDE.md:

```markdown
| {skill-name} | `.agent/skills/{skill-name}/` | {trigger description} |
```

Choose the correct category section in the table.

### 6.3 Record in HANDOFF.md

Add entry:
```markdown
### {Skill Name} — skill created
- ✅ SKILL.md ({word_count} words), score {X}/60
- Path: `.agent/skills/{skill-name}/`
- Registered in CLAUDE.md routing table
```

### 6.4 Session Log

Add line to SESSION_LOG.md.

**Output:** Installation confirmation. Display final score and file tree.

---

## Anti-Patterns

1. **Description as workflow** — NEVER put process steps in the YAML `description` field. The model may follow description and skip SKILL.md body entirely
2. **Create without testing** — NEVER finalize a skill without running it on at least one real task
3. **Copy-paste from ChatGPT** — Skills are for Claude Code. Generic AI instructions don't work. Be specific to the Claude Code environment
4. **Kitchen sink** — Don't try to cover everything. A focused skill (800 words) beats a bloated one (5000 words). Use references/ for depth
5. **No anti-patterns** — Every skill MUST have anti-patterns section. These prevent the most common mistakes
6. **Vague triggers** — "Use when working with code" is useless. "Use when deploying to REG.ru via FTP" is actionable
7. **Skip security scan** — ALWAYS run `skill-scanner scan` before installation. 36% of community skills have vulnerabilities
8. **"Auto" without code** — Если SKILL.md говорит "автоматически обновляется" или "пополняется автоматически", но нет скрипта/engine → это ложь. Либо напиши код, либо напиши "обновляется вручную". *Реальный кейс: smart-outreach anti-patterns.md заявлял авто-обновление, но код отсутствовал*
9. **Hardcoded owner** — Если шаблоны содержат "Это агент Дмитрия 🤖" или конкретные пути `/root/Antigravity/` → скилл не портируется в капсулы. Используй `{{OWNER_NAME}}`, `{{AGENT_INTRO}}` и config.json. *Реальный кейс: все 12 шаблонов smart-outreach содержали хардкод*
10. **Self-scoring inflation** — Если скилл оценивает свои результаты (scoring, CLEAR, рейтинг) → Claude ВСЕГДА завышает оценку. Обязательны: минимум 2 калибровочные пары (плохой + хороший пример с баллами) и правило "будь строже". *Реальный кейс: CLEAR в smart-outreach имел только примеры на 22-25/25 — бесполезно*

## References

- `references/best-practices.md` — Patterns from 49+ production skills in our ecosystem
- `references/skill-template.md` — Simple and Advanced SKILL.md templates with comments
- `references/workflows.md` — Workflow pattern examples from real skills
- `references/output-patterns.md` — Scoring, severity, checklist, and comparison patterns

---

## Changelog

<!-- Сюда автоматически добавляются уроки после каждого использования скилла -->

### 2026-03-25 — апгрейд v2→v3: Phase 4.5 + скоринг
- Создана Phase 4.5 (6 чеков: Executability, Portability, Data Schema, Scoring Calibration, Safety, Self-Test)
- 6-я ось скоринга: Executability (6×10=60 вместо 5×10=50)
- 3 антипаттерна из smart-outreach: "Auto без кода" (заявка авто-обновления без реального кода), "Hardcoded owner" (12 шаблонов с хардкодом), "Self-scoring inflation" (CLEAR давал 22-25/25 без негативных примеров)
- Антипаттерн: скоринг без калибровочных пар (и плохой, и хороший пример) = Claude всегда ставит 5/5
- Урок: Phase 4.5 ловит crash-баги которые Phase 4 пропускает. ОБЯЗАТЕЛЬНА даже в Quick Mode

### 2026-04-01 — глубокий аудит visual-replication + Quick Mode fix
- Phase 4.5 + Phase 5: 7 проблем (crash на невалидных файлах, inline-Playwright, нет калибровки, нет проактивности)
- Score: 38→50/60. Создан visual-screenshot.py
- Quick Mode ОБЯЗАТЕЛЬНО включает Phase 4.5. Ранее пропускал → crash-баги
- Урок: при аудите проверять не только SKILL.md, но и все скрипты на реальных данных (невалидный файл, пустой ввод)
