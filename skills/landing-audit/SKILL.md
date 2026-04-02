---
name: landing-audit
description: This skill should be used when the user wants to audit a landing page, check site quality, run Lighthouse, verify after deploy, or get a comprehensive quality score. It chains 6 audit phases (technical, visual, copy, marketing, SEO, performance budget) into a scored report with letter grades A-F and prioritized fix list.
version: 1.0.0
author: Dmitry Rostovtsev
created: 2026-03-30
updated: 2026-03-30
category: quality
tags: [audit, landing-page, lighthouse, seo, performance, copywriting, marketing, playwright]
risk: safe
source: internal
usage_count: 1
last_used: 2026-04-01
maturity: seed
---

# Landing Audit — Полный аудит лендинга

## Триггеры
- `/landing-audit <url_or_alias>`
- "аудит лендинга", "проверь сайт", "оценка страницы", "landing audit"
- "проверь после деплоя", "audit landing", "аудит сайта"

## Быстрый старт
```
/landing-audit intensive              # По алиасу из registry
/landing-audit https://example.com    # По URL
/landing-audit --all                  # Все зарегистрированные сайты
/landing-audit intensive --quick      # Только Lighthouse + screenshot
```

---

## Phase 0: Target Resolution

1. Если передан alias → найти URL в `config/sites-registry.json`
2. Если передан URL → использовать напрямую
3. Если ничего → показать список алиасов, спросить
4. Проверить доступность: `curl -sI <url>` → HTTP 200

---

## Phase 1: Technical (Lighthouse) — 25% веса

```bash
CHROME_PATH=/root/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome \
  bash .agent/skills/landing-audit/scripts/lighthouse-audit.sh <URL>
```

**Берём из вывода:** performance, accessibility, best_practices, seo, lcp_ms, cls, total_weight_kb.

**Score = performance** (из Lighthouse, 0-100 напрямую).

---

## Phase 2: Visual / Design — 15% веса

```bash
python3 .agent/skills/landing-audit/scripts/screenshot.py --url <URL>
```

1. Прочитать оба скриншота (mobile + desktop) через Read tool
2. Оценить по `references/design-checklist.md` (12 категорий, 100 баллов)
3. Ключевые проверки:
   - Body text ≥16px
   - CTA видна без скролла на mobile
   - Контраст ≥4.5:1
   - Нет horizontal scroll
   - Анимации ≤700ms, только transform+opacity

---

## Phase 3: Copywriting — 20% веса

1. Прочитать текст страницы из `/tmp/landing-audit-text-*.txt` (создан Phase 2)
2. Запустить анализ читаемости:
```bash
python3 .agent/skills/landing-audit/scripts/readability.py --file /tmp/landing-audit-text-*.txt
```
3. Оценить по `references/copywriting-checklist.md` (10 категорий × 20 = 200 баллов)
4. Нормализовать 200 → 100: `score_100 = score_200 / 2`

**Ключевые метрики:**
- Headline: 6-12 слов, конкретная выгода
- CTA: глагол, 2-5 слов, описывает результат
- Flesch-Ru ≥60, Fog-Ru <10
- BAB структура, Feature→Benefit→Outcome
- **FAQ↔Pricing consistency:** названия тарифов в FAQ = в Pricing секции
- **Testimonials quality:** нет дублей, нет негативных без resolution

---

## Phase 4: Marketing / Psychology — 15% веса

1. Используя скриншоты + текст, оценить по `references/marketing-checklist.md`
2. 14 измерений × ~7 баллов = 100

**Ключевые проверки:**
- 5-секундный тест: понятно ли предложение?
- Cialdini: social proof, authority, scarcity
- Trust: гарантии, контакты, реальные фото
- Возражения адресованы ДО CTA
- Эмоциональная арка PAS

---

## Phase 5: SEO — 15% веса

1. Прочитать HTML из `/tmp/landing-audit-html-*.html` (создан Phase 2)
2. Проверить вручную из HTML:
   - Title tag (есть, ≤60 символов)
   - Meta description (есть, ≤160 символов)
   - OG tags (og:title, og:description, og:image)
   - JSON-LD schema
   - H1 ровно 1 на странице
   - Alt text на изображениях
   - Canonical URL
   - Viewport meta tag
3. Проверить ссылки:
```bash
python3 .agent/skills/landing-audit/scripts/broken-links.py --url <URL>
```
4. Использовать Lighthouse SEO score как базу, дополнить ручными проверками

**Score = (Lighthouse_SEO × 0.6) + (manual_checks × 0.4)**

---

## Phase 6: Performance Budget — 10% веса

Из данных Lighthouse (Phase 1):
- Total weight vs threshold (≤2MB)
- JS bundle vs threshold (≤300KB gzip)
- LCP vs threshold (≤2.5s)
- CLS vs threshold (≤0.1)
- Image format coverage (≥80% WebP/AVIF)

Пороги в `references/technical-thresholds.md` и `config/sites-registry.json`.

**Score:** каждая метрика в норме = 20 баллов (5 метрик × 20 = 100)

---

## Scoring & Report

### Формула
```
Overall = technical×0.25 + visual×0.15 + copywriting×0.20 + marketing×0.15 + seo×0.15 + performance×0.10
```

### Грейды
| Score | Grade |
|-------|-------|
| 90-100 | A |
| 80-89 | B |
| 70-79 | C |
| 55-69 | D |
| <55 | F |

### Формат отчёта

```markdown
## 🔍 Landing Audit: <URL>
**Дата:** <timestamp>

### Overall: [GRADE] SCORE/100

| Измерение | Score | Grade | Ключевая проблема |
|-----------|-------|-------|-------------------|
| Technical | XX | X | ... |
| Visual | XX | X | ... |
| Copy | XX | X | ... |
| Marketing | XX | X | ... |
| SEO | XX | X | ... |
| Perf Budget | XX | X | ... |

### 📸 Скриншоты
- Mobile: [path]
- Desktop: [path]

### 📊 Читаемость
Flesch-Ru: XX | Fog-Ru: XX | Слов: XX | Оценка: ...

### 🔗 Ссылки
Всего: XX | OK: XX | Битых: XX

### 🎯 Топ-5 приоритетных фиксов
1. [HIGH] ...
2. [HIGH] ...
3. [MED] ...
4. [MED] ...
5. [LOW] ...
```

---

## Cascading Fix Chain

Когда пользователь одобряет фикс из отчёта:

1. **Diagnose** — определить root cause из отчёта
2. **Fix** — применить изменение (код, контент)
3. **Build** — `npm run build` в local_path из registry
4. **Deploy** — chain к regru скиллу
5. **Re-Audit** — `/landing-audit <alias>` повторно
6. **Compare** — показать before/after scores

**Gate:** Если ЛЮБОЙ score упал >5 пунктов → STOP + alert пользователю.

---

## Anticipatory Actions

После завершения аудита:
- Grade D/F → предложить конкретный план фиксов
- После деплоя (hook) → автоматически запустить quick audit
- Fix applied → повторить только затронутые измерения

---

## Anti-patterns
1. ❌ НЕ запускать Lighthouse без CHROME_PATH (упадёт)
2. ❌ НЕ оценивать дизайн без скриншотов (субъективно)
3. ❌ НЕ использовать Flesch для русского без русской формулы (даст мусор)
4. ❌ НЕ блокировать деплой без явной просьбы пользователя
5. ❌ НЕ ставить 100/100 без обоснования (inflation bias)
6. ❌ НЕ пропускать FAQ↔Pricing consistency check — FAQ может называть тарифы иначе, чем Pricing секция (ошибка из аудита course-platform 01.04.2026)
7. ❌ НЕ пропускать проверку testimonials на дубли и негативные отзывы без позитивного завершения
8. ❌ НЕ забывать проверять config/placeholder данные (example.ru, t.me/channel) — рендерятся в footer

## Dependencies
- `lighthouse` (npm global)
- `linkinator` (npm global)
- Playwright + Chromium (cached)
- Python: requests, bs4, playwright

## Related Skills
- `seo-audit` — детальный SEO (если нужна глубина)
- `regru` — деплой (для cascading chain)
- `frontend-design` — дизайн-решения (если нужен redesign)
- `copywriting` — переработка текстов (если copy score низкий)
- `marketing-psychology` — психология убеждения (если marketing score низкий)
