# skill-creator

Meta-skill for creating, evaluating, and improving Claude Code skills. Uses TDD methodology, 5-axis quality scoring, and iterative refinement based on best practices from 49+ production skills.

## Three Modes

| Mode | When | Phases |
|------|------|--------|
| **Quick** | Package an existing workflow as a skill | 3→4→6 |
| **Product** | Create a new skill from scratch with full TDD cycle | 1→2→3→4→5→6 |
| **Edit** | Improve an existing skill | 5→fix→5 |

## Files

| File | Purpose |
|------|---------|
| `SKILL.md` | Main workflow — 6 phases, 3 modes, scoring system |
| `references/best-practices.md` | Patterns from 49+ production skills, 5-axis scoring rubric |
| `references/skill-template.md` | Simple + Advanced SKILL.md templates with comments |
| `references/workflows.md` | 7 workflow patterns with real examples |
| `references/output-patterns.md` | Scoring, severity, checklist, comparison, progress patterns |
| `scripts/init_skill.py` | Directory scaffolding from template |
| `scripts/quick_validate.py` | YAML frontmatter validation |
| `scripts/package_skill.py` | Packaging utility |

## Quality Scoring (5 axes × 10 = 50)

| Axis | What it Measures |
|------|-----------------|
| Discovery | Does it trigger correctly? |
| Clarity | Are instructions unambiguous? |
| Efficiency | Minimal tokens, maximum result? |
| Robustness | Handles edge cases? |
| Completeness | All sections present? |

**Thresholds:** ≥45 production-ready, 35-44 needs polish, 25-34 rework, <25 redesign.

## Triggers

- "create a skill", "make a skill", "new skill"
- "evaluate skill", "score skill", "improve skill"
- "создай скилл", "оформи как скилл", "оцени скилл"

## Version

**2.0.0** — Complete rewrite. TDD, 5-axis scoring, 3 modes, real examples from Antigravity ecosystem.
