# Output Patterns

Patterns for structuring skill output. Use these when designing the quality standards and delivery format for a new skill.

---

## 1. Scoring System Pattern

**Used by:** ui-ux-pro-max (DFII), frontend-design (DFII), seo-audit (SEO Health Index), marketing-psychology (PLFS), skill-creator (5-axis scoring)

**When to use:** Quality must be measured objectively. Multiple dimensions matter.

### Weighted Score (0-100)

```markdown
## Quality Score

| Axis | Weight | Score | Weighted |
|------|--------|-------|----------|
| Visual Fidelity | 30% | 8/10 | 24 |
| Code Quality | 25% | 7/10 | 17.5 |
| Responsiveness | 25% | 9/10 | 22.5 |
| Accessibility | 20% | 6/10 | 12 |
| **Total** | **100%** | | **76/100** |

**Verdict:** Good (≥70). Ship with minor accessibility fixes.
```

### Simple Score (0-50)

```markdown
## Skill Score

| Axis | Score |
|------|-------|
| Discovery | 8/10 |
| Clarity | 9/10 |
| Efficiency | 7/10 |
| Robustness | 6/10 |
| Completeness | 8/10 |
| **Total** | **38/50** |

**Verdict:** Good, needs one more iteration on Robustness.
```

### Pass/Fail with Thresholds

```markdown
Thresholds:
- ≥ 85/100 → ✅ Production-ready
- 70-84 → ⚠️ Minor fixes needed
- < 70 → ❌ Significant rework required
```

---

## 2. Severity Classification Pattern

**Used by:** seo-audit, systematic-debugging, security (audit)

**When to use:** Findings need prioritization. Not all issues are equal.

### 4-Level Severity

```markdown
## Findings

### 🔴 CRITICAL (fix immediately)
1. **Missing HTTPS redirect** — All traffic is unencrypted
   - Impact: Security vulnerability, SEO penalty
   - Fix: Add `RewriteRule` to .htaccess
   - Confidence: 95%

### 🟠 HIGH (fix this sprint)
2. **No meta description on 3 pages** — Search engines show auto-generated snippets
   - Impact: Lower CTR in search results
   - Fix: Add `<meta name="description">` to affected pages
   - Confidence: 90%

### 🟡 MEDIUM (plan to fix)
3. **Images without alt text (12 found)** — Accessibility and SEO impact
   - Fix: Add descriptive alt text to each image
   - Confidence: 85%

### 🟢 LOW (nice to have)
4. **Heading hierarchy skip (H2→H4)** — Minor SEO signal
   - Fix: Add missing H3 level
   - Confidence: 70%
```

### With Confidence Scores

Each finding includes:
- **Severity:** CRITICAL / HIGH / MEDIUM / LOW
- **Confidence:** 0-100% (how sure are we this is actually a problem?)
- **Impact:** What happens if we don't fix it?
- **Fix:** Specific actionable remediation

Sort by: severity DESC, confidence DESC.

---

## 3. Checklist Pattern

**Used by:** verification-before-completion, regru (deploy checklist), test-driven-development

**When to use:** Pre-delivery verification. Ensuring nothing is missed.

### Pre-Delivery Checklist

```markdown
## Verification Checklist

### Must Pass (block delivery if any fails)
- [ ] Build succeeds without errors
- [ ] All tests pass
- [ ] No console errors in browser
- [ ] Mobile responsive (tested at 375px, 768px, 1024px)
- [ ] Dark mode works (if applicable)

### Should Pass (warn but don't block)
- [ ] Lighthouse score ≥ 90
- [ ] No accessibility warnings
- [ ] All images optimized (WebP, lazy loading)
- [ ] Meta tags present

### Nice to Have
- [ ] Page load < 2s on 3G
- [ ] All links verified (no 404s)
- [ ] Print stylesheet works
```

### Progressive Checklist (phases)

```markdown
## Quality Gates

### Gate 1: Structure ✅
- [x] File structure matches spec
- [x] All required sections present

### Gate 2: Content ⏳
- [x] Word count in range
- [ ] Anti-patterns section complete
- [ ] Examples provided

### Gate 3: Validation ⬜
- [ ] skill-scanner CRITICAL = 0
- [ ] YAML frontmatter valid
- [ ] No second-person language
```

---

## 4. Comparison Pattern

**Used by:** competitive-ads-extractor, decision-lab, neura (agents comparison)

**When to use:** Making a choice between options. Before/after analysis.

### Before/After

```markdown
## Impact Analysis

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Page load time | 4.2s | 1.8s | -57% ⬇️ |
| Lighthouse score | 62 | 91 | +47% ⬆️ |
| Bundle size | 847KB | 386KB | -54% ⬇️ |
| Test coverage | 0% | 78% | +78% ⬆️ |
```

### A/B Comparison

```markdown
## Option Comparison

| Criteria | Option A: Next.js | Option B: Vite + React | Winner |
|----------|-------------------|----------------------|--------|
| Build speed | 45s | 12s | B |
| SSR support | Native | Manual | A |
| Bundle size | 520KB | 340KB | B |
| Learning curve | Medium | Low | B |
| **Verdict** | | | **B** (3/4) |
```

### Multi-Option Matrix

```markdown
## Decision Matrix

| Criteria (weight) | Option A | Option B | Option C |
|-------------------|----------|----------|----------|
| Cost (30%) | ⭐⭐⭐ | ⭐⭐ | ⭐ |
| Speed (25%) | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Quality (25%) | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| Risk (20%) | ⭐⭐ | ⭐⭐⭐ | ⭐ |
| **Weighted** | **2.55** | **2.50** | **2.05** |
```

---

## 5. Progress Tracking Pattern

**Used by:** skill-creator (phase progress), executing-plans (task progress)

**When to use:** Multi-step processes where user needs visibility.

### Phase Progress

```markdown
╔═══════════════════════════════════════════╗
║  Phase 1: Reconnaissance        ✅ Done   ║
║  Phase 2: Design                ✅ Done   ║
║  Phase 3: Creation              → Active  ║
║  Phase 4: Validation            ○ Pending ║
║  Phase 5: Testing               ○ Pending ║
║  Phase 6: Installation          ○ Pending ║
╠═══════════════════════════════════════════╣
║  Progress: ██████████░░░░░░░░░░  50%     ║
╚═══════════════════════════════════════════╝
```

### Task List Progress

```markdown
## Progress: 4/7 tasks complete

- [x] Read existing code
- [x] Design component structure
- [x] Implement main component
- [x] Add responsive styles
- [ ] Write tests ← current
- [ ] Add dark mode
- [ ] Update documentation
```

---

## 6. Template Pattern

**Used by:** copywriting (copy templates), content-creator (post templates), brand-voice-clone (profile template)

**When to use:** Output must follow a specific structure.

### Strict Template

```markdown
## Output Format

ALWAYS use this exact structure:

### {Title}

**Hook:** {First sentence that grabs attention}

**Body:** {2-3 paragraphs of content}

**CTA:** {Clear call to action}

**Hashtags:** {3-5 relevant hashtags}
```

### Flexible Template

```markdown
## Output Format

Use this as a starting point, adapt to context:

### {Title}

{Opening — adapt based on platform and audience}

{Body — adjust length for platform: TG=500-1500 chars, Instagram=300-800}

{Closing — CTA or thought-provoking question}
```

---

## Choosing the Right Pattern

| Your Need | Best Pattern |
|-----------|-------------|
| Measure quality objectively | Scoring System |
| Prioritize findings | Severity Classification |
| Verify completeness | Checklist |
| Choose between options | Comparison |
| Show multi-step progress | Progress Tracking |
| Ensure consistent structure | Template |

**Combining patterns:** Most skills use 2-3 patterns together. E.g., seo-audit uses Severity + Scoring + Checklist. skill-creator uses Scoring + Progress + Checklist.
