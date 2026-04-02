# Skill Templates

Two templates: Simple (Quick Mode) and Advanced (Product Mode).

---

## Simple Template (Quick Mode)

Use when packaging an existing working workflow into a skill. Minimal structure, fast creation.

```markdown
---
name: {skill-name}
description: "This skill should be used when {specific trigger conditions}. It {what it does in one sentence}."
version: 1.0.0
author: {author}
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
category: {category}
tags: [{tag1}, {tag2}]
risk: {safe|low|medium|high}
source: internal
---

# {skill-name}

## Purpose

{2-3 sentences explaining what this skill does and why it exists.}

## When to Use

- {Specific trigger condition 1}
- {Specific trigger condition 2}
- {Specific trigger condition 3}

## Workflow

### Step 1: {Name}
{Instructions}

### Step 2: {Name}
{Instructions}

### Step 3: {Name}
{Instructions}

## Anti-Patterns

1. **{Name}** — {What not to do and why}
2. **{Name}** — {What not to do and why}
3. **{Name}** — {What not to do and why}
```

**Target:** 400-800 words. No references needed.

---

## Advanced Template (Product Mode)

Use when creating a comprehensive skill with domain knowledge, scoring, and testing.

```markdown
---
name: {skill-name}
description: "This skill should be used when {specific trigger conditions}. It {what it does in one sentence}."
version: 1.0.0
author: {author}
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
category: {meta|deploy|dev|content|strategy|media}
tags: [{tag1}, {tag2}, {tag3}]
risk: {safe|low|medium|high}
source: {internal|community|official}
---

# {skill-name}

## Purpose

{2-3 sentences. Be concrete — what problem does this solve? For whom? What's the expected outcome?}

## When to Use

Activate this skill when:
- {Trigger 1 — specific phrase or context}
- {Trigger 2 — specific phrase or context}
- {Trigger 3 — specific phrase or context}

Do NOT use when:
- {Exclusion 1 — when another skill is more appropriate}
- {Exclusion 2 — when the task is too simple for this skill}

## Core Workflow

### Phase 1: {Name} — {Goal}

{Instructions for this phase.}

**Decision gate:** {What must be true before proceeding to Phase 2?}

### Phase 2: {Name} — {Goal}

{Instructions for this phase.}

**Decision gate:** {What must be true before proceeding to Phase 3?}

### Phase 3: {Name} — {Goal}

{Instructions for this phase.}

### Phase 4: {Name} — Verification

{Quality check before delivering results.}

**Quality checklist:**
- [ ] {Check 1}
- [ ] {Check 2}
- [ ] {Check 3}

## Quality Standards

{Define how to measure output quality. Use one of:}

### Option A: Scoring System
| Axis | Weight | Target |
|------|--------|--------|
| {Axis 1} | {%} | ≥ {X}/10 |
| {Axis 2} | {%} | ≥ {X}/10 |
| {Axis 3} | {%} | ≥ {X}/10 |

### Option B: Checklist
- [ ] {Mandatory check 1}
- [ ] {Mandatory check 2}
- [ ] {Nice-to-have check 3}

### Option C: Output Example
**Input:** {example input}
**Expected output:** {example output}

## Anti-Patterns

1. **{Pattern name}** — {What not to do}. {Why it's bad}. {What to do instead}
2. **{Pattern name}** — {What not to do}. {Why it's bad}. {What to do instead}
3. **{Pattern name}** — {What not to do}. {Why it's bad}. {What to do instead}
4. **{Pattern name}** — {What not to do}. {Why it's bad}. {What to do instead}
5. **{Pattern name}** — {What not to do}. {Why it's bad}. {What to do instead}

## References

{Only if references/ directory has content:}
- `references/{file1}.md` — {what it contains}
- `references/{file2}.md` — {what it contains}
```

**Target:** 1000-2000 words. Use references/ for domain knowledge.

---

## Directory Structure

```
{skill-name}/
├── SKILL.md              # Main instructions (800-2000 words)
├── README.md             # User-facing docs (200-400 words)
├── references/           # Detailed knowledge (loaded on demand)
│   ├── {topic1}.md       # Domain-specific content
│   └── {topic2}.md       # Examples, catalogs, guides
└── scripts/              # Python utilities (optional)
    └── {tool}.py         # Validation, analysis, automation
```

---

## README.md Template

```markdown
# {skill-name}

{One paragraph: what it does, when to use it.}

## Files

| File | Purpose |
|------|---------|
| `SKILL.md` | Main workflow and instructions |
| `references/*.md` | {What's in references} |
| `scripts/*.py` | {What scripts do} |

## Triggers

This skill activates when:
- {trigger 1}
- {trigger 2}
- {trigger 3}

## Quick Start

{1-3 sentences on how to invoke the skill.}
```

**Target:** 200-400 words. No installation instructions (Claude Code handles this automatically).

---

## Naming Conventions

- **Skill name:** kebab-case, 2-4 words, descriptive (`brand-voice-clone`, `seo-audit`, `batch-transcription`)
- **Directory:** must match `name` field in YAML frontmatter
- **References:** descriptive filenames (`style-catalog.md`, `mental-models.md`, `platform-adaptation.md`)
- **Scripts:** verb-noun pattern (`validate_skill.py`, `analyze_content.py`, `generate_report.py`)

## Frontmatter Field Reference

| Field | Required | Format | Example |
|-------|----------|--------|---------|
| `name` | Yes | kebab-case | `brand-voice-clone` |
| `description` | Yes | "This skill should be used when..." | See examples |
| `version` | Recommended | SemVer | `1.0.0` |
| `author` | Recommended | Name | `Dmitry Rostovtsev` |
| `created` | Recommended | YYYY-MM-DD | `2026-03-17` |
| `updated` | Recommended | YYYY-MM-DD | `2026-03-17` |
| `category` | Recommended | One of predefined | `dev` |
| `tags` | Recommended | Array | `[seo, audit]` |
| `risk` | Recommended | safe/low/medium/high | `safe` |
| `source` | Recommended | internal/community/official | `internal` |
