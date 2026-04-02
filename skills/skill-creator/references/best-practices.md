# Best Practices — Patterns from 49+ Production Skills

Extracted from the Antigravity ecosystem (`.agent/skills/` + `~/.claude/skills/`), Skill Conductor, and Anthropic Official guidelines.

---

## Structural Patterns

### 1. Scoring Systems — Objective Quality Assessment

**Used by:** ui-ux-pro-max (DFII), frontend-design (DFII), seo-audit (SEO Health Index), marketing-psychology (PLFS)

**Pattern:** Define 3-5 axes, score 0-10 each, set thresholds for pass/fail.

```markdown
## Quality Score (DFII — Design Fidelity & Implementation Index)

| Axis | Weight | Score |
|------|--------|-------|
| Visual Fidelity | 25% | /10 |
| Code Quality | 25% | /10 |
| Responsiveness | 25% | /10 |
| Accessibility | 25% | /10 |

**Thresholds:**
- ≥ 85/100 → Ship it
- 70-84 → Minor fixes needed
- < 70 → Significant rework
```

**Why it works:** Removes subjectivity. Forces explicit evaluation. Prevents "good enough" bias.

### 2. Anti-Patterns — Preventing Common Mistakes

**Used by:** frontend-design, copywriting, seo-audit, marketing-psychology

**Pattern:** List 3-7 things the agent must NOT do. Include why.

```markdown
## Anti-Patterns

1. **Generic stock copy** — "Welcome to our website" adds zero value. Every line must earn its place
2. **Feature dumping** — Listing features without benefits. Always: feature → benefit → proof
3. **Passive voice overuse** — "Results will be delivered" → "You'll see results in 48 hours"
```

**Why it works:** Agents follow positive instructions well but also need explicit boundaries. Anti-patterns catch the most common failure modes.

### 3. Hard Gates — Quality at Every Step

**Used by:** copywriting (brief lock), verification-before-completion, test-driven-development

**Pattern:** Require explicit approval or validation before proceeding to next phase.

```markdown
### Phase 2: Brief Lock
Before proceeding to writing:
- [ ] Target audience defined
- [ ] Key message identified
- [ ] Tone confirmed with user

**HARD GATE:** Do NOT proceed to Phase 3 until all boxes are checked.
```

**Why it works:** Prevents cascading errors. A bad brief → bad copy → wasted iteration. Catch it early.

### 4. Python CLI Tools — Skill Autonomy

**Used by:** ui-ux-pro-max (CLI retrieval), seo-audit (analysis scripts), skill-creator (validate/package)

**Pattern:** Include Python scripts in `scripts/` that the skill calls directly.

```markdown
Run the analysis:
```bash
python3 scripts/analyze.py --input {file} --format json
```

**Why it works:** Deterministic operations (validation, parsing, scoring) are better as scripts than natural language instructions. Less token waste, more reliable.

### 5. References for Depth — Keep SKILL.md Lean

**Used by:** ui-ux-pro-max (67 styles + 96 palettes), marketing-psychology (70+ mental models), brand-voice-clone (platform adaptation)

**Pattern:** SKILL.md ≤ 2000 words. Move detailed knowledge to `references/`.

```markdown
## References
For detailed style guides, see `references/style-catalog.md`.
For palette options, see `references/color-palettes.md`.
```

**Why it works:** SKILL.md is loaded on every trigger. References are loaded on demand. Saves tokens on simple tasks, provides depth when needed.

### 6. Examples (Input/Output Pairs)

**Used by:** copywriting, brand-voice-clone, content-creator

**Pattern:** Show 2-3 concrete examples of expected input → output.

```markdown
## Examples

**Input:** "Write a CTA for a massage course landing page"
**Output:** "Получите программу курса бесплатно — начните зарабатывать на массаже от 150 000 ₽/мес"

**Input:** "Write a CTA for an AI agents service"
**Output:** "Запустите AI-агента за 3 дня — первый месяц обслуживания бесплатно"
```

**Why it works:** Examples communicate expectations better than descriptions. The agent pattern-matches from examples to produce similar quality.

---

## Content Patterns

### Writing Style Rules

1. **Imperative form** — "Analyze the input" not "You should analyze the input"
2. **Third-person description** — "This skill should be used when..." in YAML
3. **Concrete triggers** — "When deploying to FTP" not "When working with websites"
4. **No process in description** — Description says WHAT and WHEN, body says HOW
5. **Active voice** — "Run the scan" not "The scan should be run"

### Word Count Guidelines

| File | Target | Maximum |
|------|--------|---------|
| SKILL.md | 800-2000 words | 3000 |
| README.md | 200-400 words | 600 |
| references/*.md | 500-3000 words each | 5000 |
| Total skill | 1500-5000 words | 8000 |

### Frontmatter Best Practices

```yaml
---
name: kebab-case-name          # Must match directory name
description: "This skill should be used when [specific triggers]. It [concrete outcome]."
version: 1.0.0                 # SemVer
category: {meta|deploy|dev|content|strategy|media}
tags: [specific, relevant, tags]
risk: {safe|low|medium|high}   # safe=no side effects, high=modifies external systems
source: {internal|community|official}
---
```

**Critical:** The `description` field is what the routing system reads to decide whether to activate the skill. It must be:
- Specific enough to trigger on the right tasks
- Broad enough to not miss relevant tasks
- Free of process steps (only WHAT and WHEN)

---

## Quality Scoring System (5 Axes × 10 = 50)

Adapted from Skill Conductor. Use for evaluating any skill.

### Axis 1: Discovery (0-10)
Does the skill trigger correctly?

| Score | Criteria |
|-------|----------|
| 1-3 | Wrong triggers, conflicts with other skills, never activates |
| 4-6 | Sometimes triggers, but misses cases or has false positives |
| 7-8 | Reliable triggering, rare edge case misses |
| 9-10 | Perfect routing, no false positives, no missed triggers |

**How to improve:** Rewrite `description` field. Add/remove trigger words. Check routing table conflicts.

### Axis 2: Clarity (0-10)
Are instructions unambiguous?

| Score | Criteria |
|-------|----------|
| 1-3 | Confusing, contradictory, agent guesses what to do |
| 4-6 | Mostly clear, some sections need interpretation |
| 7-8 | Clear workflow, minor ambiguities in edge cases |
| 9-10 | Crystal clear, zero interpretation needed |

**How to improve:** Add decision gates. Replace vague verbs ("consider") with concrete ones ("check", "run", "output"). Add examples.

### Axis 3: Efficiency (0-10)
Minimal tokens, maximum result?

| Score | Criteria |
|-------|----------|
| 1-3 | Bloated, redundant steps, wastes tokens on every run |
| 4-6 | Some waste, but acceptable for the task complexity |
| 7-8 | Lean workflow, focused on essentials |
| 9-10 | Minimal tokens, references loaded on demand, no waste |

**How to improve:** Move content to references/. Remove redundant instructions. Use scripts for deterministic ops.

### Axis 4: Robustness (0-10)
How does it handle edge cases and failures?

| Score | Criteria |
|-------|----------|
| 1-3 | Crashes or produces wrong output on unexpected input |
| 4-6 | Handles common cases, fails on edge cases |
| 7-8 | Handles most edge cases, graceful degradation |
| 9-10 | Handles everything, clear error messages, fallback paths |

**How to improve:** Add error handling. Define fallback paths. Test with minimal/ambiguous/missing input.

### Axis 5: Completeness (0-10)
Does the skill cover everything needed?

| Score | Criteria |
|-------|----------|
| 1-3 | Missing critical sections, workflow incomplete |
| 4-6 | Has basics, missing anti-patterns or examples |
| 7-8 | Complete workflow, anti-patterns, basic examples |
| 9-10 | Complete + examples + references + scripts + README |

**How to improve:** Add anti-patterns (minimum 3). Add examples. Create references for deep content.

### Scoring Thresholds

| Score | Verdict | Action |
|-------|---------|--------|
| **45-50** | Production-ready | Install and register |
| **35-44** | Good, needs polish | One more iteration |
| **25-34** | Significant gaps | Revisit design |
| **< 25** | Fundamental issues | Redesign from scratch |

---

## Skill Types: Capability vs Preference

### Capability Uplift
The agent CANNOT do this task without the skill.

**Examples:** ui-ux-pro-max (needs style catalogs), seo-audit (needs scoring methodology), getcourse-manager (needs API knowledge)

**Testing:** Run task without skill → confirm it fails or produces garbage → add skill → confirm success.

**Design focus:** Domain knowledge, specific procedures, external tool integration.

### Encoded Preference
The agent CAN do the task, but does it differently than desired.

**Examples:** copywriting (enforces brief-first approach), russian-typography (enforces non-breaking spaces), verification-before-completion (enforces final check)

**Testing:** Run task without skill → compare quality → add skill → confirm measurable improvement.

**Design focus:** Order of operations, quality gates, style enforcement.

---

## Degrees of Freedom

How much latitude does the agent get?

| Level | Description | Best For |
|-------|-------------|----------|
| **Low** | Script-like, exact commands | Deployments, data migrations, security scans |
| **Medium** | Pseudocode with decision points | Analysis, audits, code reviews |
| **High** | Natural language guidance | Creative writing, brainstorming, strategy |

**Rule of thumb:** Higher risk → lower freedom. If the skill modifies production systems, constrain tightly. If it generates ideas, let it breathe.

---

## Critical Rules from Skill Conductor

1. **⚠️ NEVER put process steps in `description`** — The model reads description first. If steps are there, it may follow them and skip the SKILL.md body entirely
2. **TDD-first** — Always confirm the agent cannot do the task without the skill before creating it. No baseline → no way to measure improvement
3. **Fix causes, not symptoms** — If the skill scores low on Discovery, don't just add trigger words. Ask: is the description fundamentally wrong?
4. **Human in the loop** — Skills that modify external systems (deploy, send messages, create resources) MUST have confirmation points
5. **2-3 iterations minimum** — First draft is never production-ready. Plan for iteration from the start
6. **Security scan ALWAYS** — `skill-scanner scan` before installation. 36% of community skills have security holes
