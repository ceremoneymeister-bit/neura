# Workflow Patterns

Real examples from production skills in the Antigravity ecosystem.

---

## 1. Sequential Workflow

**Best for:** Tasks with clear linear progression where each step depends on the previous.

### Example: copywriting (context → brief → writing)

```
Phase 1: Context Gathering
  - Read existing page / brand materials
  - Identify target audience
  - Analyze competitors
  ↓ HARD GATE: context document approved by user

Phase 2: Brief Lock
  - Define key message
  - Set tone and style
  - Choose CTA strategy
  ↓ HARD GATE: brief confirmed, no changes allowed after this point

Phase 3: Writing
  - Write headlines (3 variants)
  - Write body copy
  - Write CTAs
  - Internal quality check
  ↓ OUTPUT: Final copy delivered
```

**Key principle:** Hard gates between phases prevent cascading errors. A bad brief → bad copy → wasted iteration.

---

## 2. Iterative Refinement Workflow

**Best for:** Tasks where quality improves through scoring and re-work cycles.

### Example: frontend-design (design → score → refine → re-score)

```
Phase 1: Initial Design
  - Generate component/page based on requirements
  - Apply design system tokens
  ↓

Phase 2: Score (DFII — Design Fidelity & Implementation Index)
  - Visual Fidelity: /10
  - Code Quality: /10
  - Responsiveness: /10
  - Accessibility: /10
  ↓ IF total ≥ 85 → Phase 4
  ↓ IF total < 85 → Phase 3

Phase 3: Refine
  - Address lowest-scoring axis
  - Apply specific fixes
  - Re-run quality checks
  ↓ GOTO Phase 2 (max 3 iterations)

Phase 4: Deliver
  - Final output with score card
  - Anti-pattern verification
```

**Key principle:** Objective scoring removes guesswork. The agent knows exactly when to stop iterating.

---

## 3. Diagnostic Workflow

**Best for:** Investigation tasks with evidence gathering and prioritized findings.

### Example: seo-audit (scan → analyze → prioritize → report)

```
Phase 1: Scan
  - Check meta tags (title, description, OG)
  - Check heading hierarchy (H1-H6)
  - Check images (alt text, size, format)
  - Check links (broken, redirects)
  - Check performance (Core Web Vitals)
  ↓

Phase 2: Analyze
  - Classify each finding: CRITICAL / HIGH / MEDIUM / LOW
  - Assign confidence: 0-100%
  - Calculate SEO Health Index (0-100)
  ↓

Phase 3: Prioritize
  - Sort by severity × confidence
  - Group by category
  - Identify quick wins (high impact + low effort)
  ↓

Phase 4: Report
  - Executive summary (1 paragraph)
  - Score card (SEO Health Index)
  - Findings table (severity, finding, fix)
  - Quick wins section
  - Detailed recommendations
```

**Key principle:** Evidence-based findings with severity classification. Not opinions — data.

---

## 4. Interactive Retrieval Workflow

**Best for:** Tasks requiring access to large knowledge bases or catalogs.

### Example: ui-ux-pro-max (query → retrieve → apply → checklist)

```
Phase 1: Understand Request
  - Parse what the user needs (component, page, style)
  - Identify relevant categories
  ↓

Phase 2: Retrieve
  - Search style catalog (67 styles)
  - Search palette catalog (96 palettes)
  - Search pattern library
  - Present top 3 options to user
  ↓ USER CHOICE required

Phase 3: Apply
  - Generate design using selected style/palette
  - Apply design system tokens
  - Ensure responsive behavior
  ↓

Phase 4: Quality Checklist
  - [ ] Color contrast AAA
  - [ ] Typography scale consistent
  - [ ] Spacing system (4px grid)
  - [ ] Dark/light mode support
  - [ ] Mobile-first responsive
```

**Key principle:** Large catalogs live in references/. SKILL.md orchestrates retrieval. User makes the creative choice.

---

## 5. Context-Aware Workflow

**Best for:** Tasks where the workflow path depends on the input type or context.

### Example: regru (deploy vs DNS vs SSL → different workflows)

```
Phase 0: Detect Context
  - What is the user asking? Parse intent:
    A) "деплой" / "залей на сайт" → Deploy Workflow
    B) "DNS" / "домен" → DNS Workflow
    C) "SSL" / "HTTPS" → SSL Workflow
    D) "создай поддомен" → Subdomain Workflow
  ↓ Route to appropriate workflow

Deploy Workflow:
  1. Read site registry (which host, which path)
  2. Build project (if needed)
  3. FTP upload via ftp-deploy.py
  4. Verify HTTP 200
  ↓ END

DNS Workflow:
  1. Read current DNS records
  2. Determine needed changes
  3. Apply via REG.ru panel
  4. Verify propagation
  ↓ END

SSL Workflow:
  1. Check current SSL status
  2. Request Let's Encrypt
  3. Configure .htaccess redirect
  4. Verify HTTPS
  ↓ END
```

**Key principle:** One skill, multiple paths. The routing logic is in Phase 0, keeping each path focused and simple.

---

## 6. TDD-Driven Workflow

**Best for:** Creating or improving skills themselves.

### Example: skill-creator Product Mode

```
Phase 1: Establish Baseline
  - Run target task WITHOUT the skill
  - Document: what agent does, where it fails
  - This is the "red" in red-green-refactor
  ↓

Phase 2: Design & Create
  - Write SKILL.md based on observed failures
  - Target the specific gaps found in baseline
  ↓

Phase 3: Test
  - Run same task WITH the skill
  - Compare against baseline
  - Score on 5 axes (Discovery, Clarity, Efficiency, Robustness, Completeness)
  ↓ IF score ≥ 45/50 → Phase 4
  ↓ IF score < 45/50 → iterate (fix root cause → re-test)

Phase 4: Install
  - Register in routing table
  - Document in HANDOFF.md
```

**Key principle:** No baseline → no way to measure improvement. Always test without first.

---

## 7. Multi-MCP Coordination Workflow

**Best for:** Tasks that require data from multiple external tools/services.

### Example: content-creator (research + write + publish)

```
Phase 1: Research (parallel MCP calls)
  - Web Search → trending topics, competitor content
  - File Read → brand voice profile, content calendar
  - Knowledge Base → past content performance data
  ↓ Synthesize findings

Phase 2: Plan
  - Select topic + angle
  - Choose format (post, article, reel script)
  - Define SEO targets (if applicable)
  ↓

Phase 3: Create
  - Write content using brand voice
  - Optimize for platform (TG, Instagram, blog)
  - Generate meta/hashtags
  ↓

Phase 4: Review
  - Check against brand voice profile
  - Verify SEO targets met
  - Cross-reference with content calendar (no repeats)
  ↓

Phase 5: Deliver
  - Present to user for approval
  - Optional: schedule via bot/API
```

**Key principle:** Parallel MCP calls in Phase 1 save time. Each subsequent phase uses the synthesized output.

---

## Choosing the Right Pattern

| Your Task | Best Pattern | Why |
|-----------|-------------|-----|
| Clear steps, no branching | Sequential | Simple, predictable |
| Quality matters, need iterations | Iterative | Scoring drives improvement |
| Investigation / audit | Diagnostic | Evidence-based, prioritized |
| Large knowledge base | Interactive Retrieval | Catalog + user choice |
| Multiple input types | Context-Aware | Right path for right input |
| Creating/improving skills | TDD-Driven | Baseline proves value |
| Multiple data sources | Multi-MCP | Parallel research, sequential creation |
