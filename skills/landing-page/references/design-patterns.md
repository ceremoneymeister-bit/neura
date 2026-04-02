# Design Patterns — Визуальные паттерны для лендингов

## 5 вариантов Hero-секций

### 1. Split Hero (50/50)
**Когда:** Есть сильный визуал продукта (скриншот, фото).

```
┌────────────────┬────────────────┐
│   Headline     │                │
│   Subheadline  │    Product     │
│   [CTA]        │    Visual      │
│   social proof │                │
└────────────────┴────────────────┘
```

**Tailwind-каркас:**
```html
<section class="min-h-screen flex items-center">
  <div class="container mx-auto px-6 grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
    <div class="space-y-6">
      <h1 class="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight">...</h1>
      <p class="text-lg text-muted max-w-lg">...</p>
      <a href="#" class="inline-flex px-8 py-4 rounded-xl bg-primary text-white font-semibold">CTA</a>
    </div>
    <div class="relative"><!-- visual --></div>
  </div>
</section>
```

### 2. Centered Hero
**Когда:** Фокус на тексте, нет сильного визуала. Продуктовые страницы.

```
┌──────────────────────────────────┐
│         (Badge / Label)          │
│         Headline                 │
│         Subheadline              │
│         [CTA]  [Secondary]       │
│         social proof bar         │
└──────────────────────────────────┘
```

**Tailwind-каркас:**
```html
<section class="min-h-screen flex items-center justify-center text-center">
  <div class="max-w-3xl mx-auto px-6 space-y-8">
    <span class="inline-flex px-3 py-1 rounded-full bg-primary/10 text-primary text-sm">Label</span>
    <h1 class="text-4xl md:text-6xl font-bold tracking-tight">...</h1>
    <p class="text-lg text-muted max-w-xl mx-auto">...</p>
    <div class="flex gap-4 justify-center">
      <a href="#" class="px-8 py-4 rounded-xl bg-primary text-white font-semibold">CTA</a>
      <a href="#" class="px-8 py-4 rounded-xl border border-primary/20">Secondary</a>
    </div>
  </div>
</section>
```

### 3. Video/Media Hero
**Когда:** Есть видео-демо, анимация продукта. SaaS, tech.

```
┌──────────────────────────────────┐
│         Headline                 │
│         Subheadline              │
│         [CTA]                    │
│  ┌──────────────────────────┐    │
│  │      Video / Demo        │    │
│  └──────────────────────────┘    │
└──────────────────────────────────┘
```

### 4. Gradient/Abstract Hero
**Когда:** Абстрактный продукт (AI, consulting, SaaS). Mood > визуал.

```
┌══════════════════════════════════┐
│ ░░░ gradient / mesh bg ░░░░░░░░ │
│         Headline                 │
│         Subheadline              │
│         [CTA]                    │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
└══════════════════════════════════┘
```

**Tailwind-каркас:**
```html
<section class="min-h-screen relative flex items-center justify-center overflow-hidden">
  <div class="absolute inset-0 bg-gradient-to-br from-primary/20 via-transparent to-accent/20"></div>
  <div class="relative z-10 max-w-3xl mx-auto px-6 text-center space-y-8">
    <!-- content -->
  </div>
</section>
```

### 5. Full-bleed Image Hero
**Когда:** Lifestyle-продукт, событие, физический продукт с сильным фото.

```
┌══════════════════════════════════┐
│ ▓▓▓▓▓ background image ▓▓▓▓▓▓▓ │
│ ▓▓▓▓▓ dark overlay     ▓▓▓▓▓▓▓ │
│         Headline (white)         │
│         [CTA]                    │
│ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ │
└══════════════════════════════════┘
```

---

## Паттерны секций

### Bento Grid (Benefits / Features)
**Когда:** 4-6 фич/выгод. Визуально интересно, не монотонно.

```
┌──────────┬──────────┐
│  Large   │  Small   │
│  card    ├──────────┤
│          │  Small   │
├──────────┼──────────┤
│  Small   │  Large   │
├──────────┤  card    │
│  Small   │          │
└──────────┴──────────┘
```

**Tailwind:**
```html
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
  <div class="lg:col-span-2 p-8 rounded-2xl bg-surface">Large card</div>
  <div class="p-8 rounded-2xl bg-surface">Small card</div>
  <!-- ... -->
</div>
```

### Timeline (How It Works / Process)
**Когда:** Последовательный процесс из 3-5 шагов.

```
①──────②──────③──────④
Step 1  Step 2  Step 3  Step 4
desc    desc    desc    desc
```

**Tailwind:** `flex` с `relative` connector line между номерами.

### Accordion (FAQ)
**Когда:** 5-10 вопросов. Экономит место, интерактивно.

```html
<details class="group border-b border-border py-4">
  <summary class="flex justify-between items-center cursor-pointer font-semibold">
    <span>Вопрос?</span>
    <span class="transition-transform group-open:rotate-180">▼</span>
  </summary>
  <p class="mt-4 text-muted">Ответ...</p>
</details>
```

### Cards Grid (Testimonials / Pricing)
**Когда:** Тарифы, отзывы, команда.

```
┌──────┐ ┌──────┐ ┌──────┐
│ Card │ │ Card │ │ Card │
│      │ │ ★    │ │      │
│      │ │ best │ │      │
└──────┘ └──────┘ └──────┘
```

**Pricing tip:** Средний тариф = "Рекомендуем" (выделить визуально). Anchoring: показать самый дорогой первым.

### Stats Bar (Social Proof)
**Когда:** 3-4 ключевых числа.

```
┌────────┬────────┬────────┬────────┐
│  500+  │  24/7  │  98%   │  3 мин │
│ clients│  work  │  happy │ setup  │
└────────┴────────┴────────┴────────┘
```

---

## Responsive-стратегия

### Breakpoints (mobile-first)
```css
/* Base: 375px (mobile) */
/* sm: 640px (large phone) */
/* md: 768px (tablet) */
/* lg: 1024px (laptop) */
/* xl: 1280px (desktop) */
/* 2xl: 1440px (wide) */
```

### Ключевые правила

1. **Начинай с mobile (375px)** — single column, всё стековано
2. **768px** — 2 колонки для grid, split hero включается
3. **1024px** — sidebar layout, полная навигация
4. **1440px** — max-width container, увеличенные отступы

### Типичные адаптации

| Элемент | Mobile | Desktop |
|---------|--------|---------|
| Hero | Stacked (text → image) | Split (50/50) |
| Benefits grid | 1 column | 2-3 columns |
| Stats bar | 2×2 grid | 4 inline |
| Testimonials | 1 (carousel) | 3 columns |
| FAQ | Full width | 60-70% width centered |
| CTA buttons | Full width | Auto width |
| Heading size | text-3xl | text-5xl/6xl |
| Padding | px-4 py-12 | px-6 py-24 |

---

## Color & Theme System

### CSS Custom Properties

```css
:root {
  /* Backgrounds */
  --color-bg: oklch(0.98 0 0);
  --color-surface: oklch(0.95 0 0);
  --color-surface-hover: oklch(0.92 0 0);

  /* Text */
  --color-text: oklch(0.15 0 0);
  --color-text-muted: oklch(0.45 0 0);

  /* Brand */
  --color-primary: oklch(0.65 0.25 265);
  --color-primary-hover: oklch(0.58 0.25 265);
  --color-accent: oklch(0.75 0.18 85);

  /* Semantic */
  --color-success: oklch(0.72 0.19 145);
  --color-warning: oklch(0.80 0.15 85);
  --color-error: oklch(0.63 0.24 25);

  /* Borders */
  --color-border: oklch(0.88 0 0);
  --radius-sm: 0.5rem;
  --radius-md: 0.75rem;
  --radius-lg: 1rem;
  --radius-xl: 1.5rem;
}

.dark {
  --color-bg: oklch(0.12 0 0);
  --color-surface: oklch(0.18 0 0);
  --color-surface-hover: oklch(0.22 0 0);
  --color-text: oklch(0.92 0 0);
  --color-text-muted: oklch(0.60 0 0);
  --color-border: oklch(0.25 0 0);
}
```

### Tailwind v4 интеграция

```css
/* app.css */
@import "tailwindcss";

@theme {
  --color-bg: var(--color-bg);
  --color-surface: var(--color-surface);
  --color-primary: var(--color-primary);
  --color-text: var(--color-text);
  --color-muted: var(--color-text-muted);
}
```

---

## Pre-Delivery Checklist

Финальная проверка перед сдачей лендинга:

### Design
- [ ] Типографика: шрифт не из "дефолтных 5" (Inter, Roboto, Open Sans, Montserrat, Poppins)
- [ ] Контраст текста ≥ 4.5:1 (проверить через DevTools)
- [ ] Spacing консистентен (одна шкала для всех отступов)
- [ ] Dark mode работает корректно (если применимо)
- [ ] Иконки одного стиля и размера

### Content
- [ ] H1 — один на странице
- [ ] Заголовки (H2-H6) — иерархия без пропусков
- [ ] `&nbsp;` после предлогов, союзов, частиц (≤3 буквы): в, на, и, а, но, с, к, о, у, за, из, не, ни, бы, ли, же, то, до, по, от, об, их, её, его
- [ ] Каждая фича — полная F→B→O цепочка
- [ ] CTA-текст — глагол + выгода (не "Отправить", а "Получить доступ")
- [ ] Нет орфографических ошибок

### SEO
- [ ] `<title>` ≤ 60 символов, содержит ключевое слово
- [ ] `<meta description>` ≤ 160 символов, содержит CTA
- [ ] Open Graph теги: og:title, og:description, og:image
- [ ] Семантический HTML: header, main, section, footer
- [ ] Alt-тексты для всех изображений
- [ ] Canonical URL

### Technical
- [ ] `vite build` проходит без ошибок
- [ ] Mobile: 375px — всё видно, ничего не обрезано
- [ ] Tablet: 768px — grid перестраивается
- [ ] Desktop: 1440px — max-width container, не растягивается
- [ ] CTA-кнопки кликабельны на всех breakpoints
- [ ] Ссылки рабочие (href не пустые)
- [ ] Нет console errors
- [ ] Bundle size разумный (JS < 500KB, CSS < 50KB gzip)

### Psychology
- [ ] Каждая ментальная модель привязана к конкретной секции
- [ ] Loss Aversion — не манипулятивно, а информативно
- [ ] Social proof — реальные данные (не выдуманные)
- [ ] Urgency — обоснованная (реальный дедлайн / лимит)
