---
name: platform-ui-builder
description: "Полный цикл создания premium UI для AI-платформ, агентских систем и SaaS. Figma MCP + Pencil + shadcn/ui + Aceternity + Tailwind v4. Проактивность на каждом шаге. Самообучающийся."
version: 1.0.0
author: Antigravity
created: 2026-04-01
category: development
tags: [ui, ux, platform, dashboard, saas, figma, design-system, react, tailwind, glassmorphism, proactive, self-learning]
risk: safe
source: crystallized
---

# Platform UI Builder

> Мощнейший скилл для создания технологичных, современных интерфейсов платформ и AI-систем. Каждый шаг — проактивный. Каждая сессия — обучение.

## Purpose

Создать production-ready UI для AI-платформ, агентских систем, SaaS-дашбордов и web-приложений — от идеи до пиксельного результата. Скилл объединяет:
- **Figma MCP** — дизайн прямо в Figma из кода
- **Pencil MCP** — .pen макеты с стайл-гайдами
- **shadcn/ui + Radix** — компонентная база (94k+ GitHub stars)
- **Aceternity UI / Magic UI** — wow-эффекты и анимации
- **Tailwind v4** — CSS-first, OKLCH, container queries
- **Motion (Framer Motion)** — декларативные анимации
- **Современные CSS** — Liquid Glass, scroll-driven animations, view transitions

---

## When to Use

| Триггер | Пример |
|---------|--------|
| Создание интерфейса платформы | "сделай UI для агентской системы" |
| AI/SaaS дашборд | "дашборд как у ChatGPT/Claude" |
| Дизайн-система с нуля | "создай дизайн-систему для платформы" |
| Редизайн существующего UI | "обнови интерфейс, сделай современнее" |
| Компонентная библиотека | "набор компонентов для SaaS" |
| Figma → код | "реализуй этот макет из Figma" |
| Код → Figma | "загрузи экран в Figma" |
| Landing для продукта | "посадочная для AI-сервиса" |
| Web-приложение | "интерфейс для нейросети" |

**НЕ использовать для:** простых статичных страниц (→ landing-page), только типографика (→ russian-typography), только аудит (→ landing-audit)

---

## Proactivity Engine (ПДМ — Проактивный Движок Мастера)

> Каждый шаг скилла включает проактивные действия. Агент НЕ ждёт запроса — предлагает сам.

### 7 уровней проактивности

| # | Уровень | Что делает агент | Когда срабатывает |
|---|---------|-----------------|-------------------|
| 1 | **Разведка** | Ищет референсы, анализирует конкурентов, предлагает стиль | Начало проекта |
| 2 | **Предложение** | Предлагает 2-3 варианта палитры/шрифтов/layout | Перед дизайном каждого экрана |
| 3 | **Предупреждение** | Находит проблемы a11y, performance, responsive ДО того как спросят | После каждого компонента |
| 4 | **Обогащение** | Добавляет micro-interactions, skeleton loaders, hover states | При реализации |
| 5 | **Оптимизация** | Предлагает lazy-load, code-split, will-change | Перед финализацией |
| 6 | **Альтернативы** | Показывает вариант с другим эффектом (glass → bento → neubrutalism) | При ревью |
| 7 | **Обучение** | Логирует что сработало, обновляет скилл | После завершения |

### Формат проактивных подсказок

```
💡 ПРОАКТИВ [уровень]: [что предлагаю]
   Почему: [1 предложение]
   Варианты: A) ... B) ... C) пропустить
```

Агент выдаёт проактивную подсказку на КАЖДОМ шаге workflow. Если пользователь выбрал C (пропустить) 3+ раза — снизить частоту до ключевых моментов.

---

## Workflow — 6 фаз

### Phase 0: DISCOVERY (обязательная)

**Цель:** Понять ЧТО строим, ДЛЯ КОГО, в каком СТИЛЕ

**Шаги:**
1. **Контекст-интервью** (3-5 вопросов):
   - Тип продукта? (AI-платформа / SaaS / агентская система / dashboard / web-app)
   - Целевая аудитория? (техническая / бизнес / массовая)
   - Настроение? (технологичный / минималистичный / дерзкий / премиальный)
   - Есть ли референсы? (скриншот, URL, Figma)
   - Функционал первого экрана? (чат / дашборд / онбординг / landing)

2. **💡 ПРОАКТИВ [Разведка]:** Агент сам ищет:
   - Сканирует существующий код проекта (если есть)
   - Предлагает 2-3 визуальных направления с описанием
   - Показывает примеры из галерей (saasui.design, saasframe.io)

3. **Стек-решение:**

| Компонент | Рекомендация | Альтернатива |
|-----------|-------------|-------------|
| Framework | React + Vite | Next.js (если SSR нужен) |
| Styling | Tailwind v4 | CSS Modules |
| Components | shadcn/ui + Radix | Mantine / HeroUI |
| Animations | Motion (Framer Motion) | GSAP (для таймлайнов) |
| Effects | Aceternity UI / Magic UI | Кастомные |
| Icons | Lucide (1668+) | Phosphor (9000+) |
| Charts | Recharts / Tremor | Nivo |
| Figma | Figma MCP (get_design_context) | Pencil MCP (.pen) |

4. **Brief Lock** — зафиксировать решения перед Phase 1

**Gate 0:** Brief подтверждён пользователем → Phase 1

---

### Phase 1: DESIGN SYSTEM

**Цель:** Создать токены, палитру, типографику, spacing

**Шаги:**

1. **Палитра** — OKLCH (Tailwind v4 нативный):
   ```
   💡 ПРОАКТИВ [Предложение]: 3 палитры
   A) Midnight Tech — oklch(0.15 0.01 260) фон, oklch(0.7 0.2 275) акцент (фиолет)
   B) Arctic Glass — oklch(0.98 0.01 240) фон, oklch(0.6 0.15 200) акцент (голубой)  
   C) Neon Contrast — oklch(0.12 0.0 0) фон, oklch(0.85 0.25 145) акцент (зелёный)
   ```

2. **Типографика:**
   - Display: Inter / Satoshi / Plus Jakarta Sans / Geist
   - Body: Inter / DM Sans / Outfit
   - Mono: JetBrains Mono / Geist Mono / Fira Code
   - Scale: 12/14/16/18/20/24/30/36/48/60/72

3. **Spacing** — 4px система: 0/1/2/3/4/5/6/8/10/12/16/20/24/32/40/48/64

4. **Border Radius** — 4/6/8/12/16/20/full

5. **Shadows** — 3 уровня (subtle / medium / large):
   ```css
   --shadow-sm: 0 1px 2px oklch(0 0 0 / 0.05);
   --shadow-md: 0 4px 6px -1px oklch(0 0 0 / 0.1);
   --shadow-lg: 0 10px 15px -3px oklch(0 0 0 / 0.1);
   ```

6. **Dark Mode** — обязательно:
   - Фон: НЕ #000, а oklch(0.14-0.18 0.01 260)
   - Текст: НЕ #FFF, а oklch(0.92-0.95 0 0)
   - Elevation через light overlay (oklch(1 0 0 / 0.03-0.08))

7. **💡 ПРОАКТИВ [Предупреждение]:**
   - Проверка контраста WCAG AA (4.5:1 для текста)
   - `contrast-color()` — автоконтраст (CSS 2026)
   - Touch targets ≥ 44x44px

8. **Figma интеграция** (если нужно):
   ```
   → figma-create-design-system-rules (генерация правил)
   → figma-generate-library Phase 1 (токены → Figma variables)
   ```

**Gate 1:** Дизайн-система создана, DFII ≥ 8 → Phase 2

---

### Phase 2: COMPONENT LIBRARY

**Цель:** Собрать библиотеку компонентов — от атомов до организмов

#### Tier 1 — Atoms (базовые, обязательные)

| Компонент | Источник | Проактивные действия |
|-----------|---------|---------------------|
| Button | shadcn/ui | + loading state, + disabled state, + icon slot |
| Input | shadcn/ui | + validation animation, + auto-label, + copy button |
| Badge | shadcn/ui | + pulse animation для "new", + count variant |
| Avatar | shadcn/ui | + status indicator (online/offline), + fallback initials |
| Tooltip | shadcn/ui + Radix | + keyboard-accessible, + delay tuning |
| Switch / Toggle | shadcn/ui | + motion transition, + label alignment |
| Skeleton | shadcn/ui | + shimmer effect (Aceternity) |

#### Tier 2 — Molecules (составные)

| Компонент | Источник | Проактивные действия |
|-----------|---------|---------------------|
| Card | shadcn/ui | + hover lift, + glass variant, + bento-ready |
| Dialog / Modal | shadcn/ui + Radix | + Motion enter/exit, + focus trap verified |
| Command Palette | shadcn/ui (cmdk) | + fuzzy search, + keyboard shortcuts overlay |
| Data Table | shadcn/ui + TanStack | + sortable, + filterable, + column resize |
| Sidebar | shadcn/ui | + collapsible, + icon-only mode, + mobile drawer |
| Tabs | shadcn/ui + Radix | + animated underline, + overflow scroll |
| Dropdown Menu | shadcn/ui + Radix | + nested menus, + icons, + keyboard nav |
| Toast / Sonner | sonner | + progress bar, + undo action, + stack mode |

#### Tier 3 — Organisms (секции)

| Компонент | Источник | Проактивные действия |
|-----------|---------|---------------------|
| Chat Interface | Custom + shadcn | + streaming animation, + code blocks, + artifacts panel |
| Dashboard Grid | Bento layout | + drag-resize (react-grid-layout), + responsive collapse |
| Navigation Bar | Custom | + scroll hide/show, + breadcrumbs, + model selector |
| Settings Panel | shadcn forms | + grouped sections, + search in settings |
| Onboarding Flow | Custom + Motion | + step indicator, + skip logic, + confetti finish |
| Pricing Table | shadcn + custom | + toggle annual/monthly, + highlight "popular" |
| Feature Grid | Bento + Aceternity | + hover reveal, + icon animations |
| Hero Section | Custom + Motion | + parallax, + gradient mesh, + floating elements |

#### Tier 4 — Wow-компоненты (Aceternity / Magic UI)

| Эффект | Библиотека | Когда использовать |
|--------|-----------|-------------------|
| Spotlight Card | Aceternity | Карточки фич на landing |
| Beam Border | Magic UI | Выделение активного элемента |
| Globe 3D | Magic UI | Hero секция для глобального продукта |
| Typewriter | Aceternity | AI-эффект печатания |
| Moving Border | Aceternity | Кнопки CTA |
| Particles | Magic UI | Фон hero секции |
| Animated Gradient | Custom CSS | Фон для glass-элементов |
| Floating Dock | Aceternity | Навигация в стиле macOS |
| Infinite Scroll Cards | Aceternity | Testimonials, логотипы |
| Text Reveal | Aceternity | Заголовки при скролле |
| Lamp Effect | Aceternity | Секция ценообразования |
| Meteors | Aceternity | Декоративный фон |
| Aurora Background | Aceternity | Hero / backdrop |

**💡 ПРОАКТИВ [Обогащение]:** После создания каждого компонента:
- Предложить micro-interaction (hover, focus, active state)
- Проверить a11y (ARIA, focus-visible, keyboard nav)
- Предложить dark mode вариант
- Показать мобильную адаптацию

**Gate 2:** Компоненты готовы, каждый проверен на a11y + responsive → Phase 3

---

### Phase 3: LAYOUT & SCREENS

**Цель:** Собрать экраны из компонентов

#### Типовые экраны AI-платформы

```
┌─────────────────────────────────────────────┐
│  ┌──────┐  ┌────────────────────────────┐   │
│  │      │  │        Header / NavBar      │   │
│  │ Side │  ├────────────────────────────┤   │
│  │ bar  │  │                            │   │
│  │      │  │      Main Content Area     │   │
│  │ nav  │  │                            │   │
│  │      │  │   (Chat / Dashboard /      │   │
│  │ +    │  │    Settings / Artifacts)   │   │
│  │ hist │  │                            │   │
│  │      │  ├────────────────────────────┤   │
│  │      │  │  Input Area / Actions       │   │
│  └──────┘  └────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

**Ключевые layout-паттерны:**

1. **Sidebar-first** — свертываемый sidebar (ChatGPT/Claude pattern)
   - Desktop: 260px sidebar + main
   - Tablet: icon-only sidebar (48px) + main
   - Mobile: sheet/drawer overlay
   - Tailwind: `@container` queries для responsive

2. **Bento Grid** — для features/dashboard
   ```jsx
   <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
     <Card className="col-span-2 row-span-2">Главный блок</Card>
     <Card>Метрика 1</Card>
     <Card>Метрика 2</Card>
     <Card className="col-span-2">Широкий блок</Card>
   </div>
   ```

3. **Split Panel** — chat + artifacts (Claude pattern)
   - Resizable panels (react-resizable-panels)
   - Snap to 50/50 или 70/30
   - Mobile: tab switch

4. **Glass Layer** — наложение стекла поверх контента
   ```css
   .glass-panel {
     background: oklch(0.98 0.005 240 / 0.6);
     backdrop-filter: blur(12px) saturate(1.2);
     -webkit-backdrop-filter: blur(12px) saturate(1.2);
     border: 1px solid oklch(1 0 0 / 0.15);
     border-radius: 16px;
   }
   /* Dark mode */
   .dark .glass-panel {
     background: oklch(0.18 0.01 260 / 0.7);
     border: 1px solid oklch(1 0 0 / 0.08);
   }
   ```

5. **Full-bleed Hero** — для landing/onboarding
   - Gradient mesh фон
   - Floating glassmorphism cards
   - Parallax через scroll-driven animations

**💡 ПРОАКТИВ [Предложение]:** Перед каждым экраном:
- Показать wireframe (ASCII или Pencil MCP)
- Предложить 2 варианта layout
- Указать ожидаемый breakpoint-поведение

**💡 ПРОАКТИВ [Оптимизация]:** После экрана:
- `content-visibility: auto` для off-screen секций
- Lazy-load тяжёлых компонентов
- Skeleton screens для async-данных

**Gate 3:** Все экраны собраны, responsive проверен → Phase 4

---

### Phase 4: ANIMATION & EFFECTS

**Цель:** Оживить интерфейс — micro-interactions, transitions, wow-эффекты

#### Обязательные анимации

| Элемент | Анимация | Библиотека | Duration |
|---------|---------|-----------|----------|
| Page transition | Fade + slide | View Transitions API | 200-300ms |
| Hover на карточках | Scale 1.02 + shadow | CSS / Motion | 200ms |
| Модальные окна | Scale 0.95→1 + fade | Motion | 200ms ease-out |
| Sidebar toggle | Width 260→48 | Motion layout | 200ms |
| Skeleton shimmer | Gradient slide | CSS animation | 1.5s infinite |
| Scroll reveal | Fade up 20px | Scroll-driven CSS | 300ms |
| Button press | Scale 0.97 | CSS :active | 100ms |
| Toast enter | Slide from bottom | Sonner | 200ms spring |
| Tab switch | Underline morph | Motion layoutId | 200ms |
| Loading spinner | Rotate | CSS animation | 1s infinite |

#### Wow-эффекты (по запросу)

| Эффект | Сложность | Performance | Когда использовать |
|--------|-----------|-------------|-------------------|
| Parallax scroll | Low | Good | Hero, фоны |
| Cursor glow | Medium | Good | Карточки |
| Text gradient animation | Low | Good | Заголовки |
| 3D card tilt | Medium | Medium | Feature cards |
| Particle field | High | Heavy | Hero (lazy-load!) |
| Globe 3D | High | Heavy | Только hero, lazy |
| Typewriter | Low | Good | AI-чат интерфейс |
| Staggered list | Low | Good | Списки, меню |
| Magnetic button | Medium | Good | CTA |
| Morphing shapes | High | Medium | Декоративные фоны |

#### CSS 2026 — нативные эффекты (без JS!)

```css
/* Scroll-driven animations — НЕ нужен JS */
@keyframes fade-in {
  from { opacity: 0; translate: 0 20px; }
  to { opacity: 1; translate: 0 0; }
}
.scroll-reveal {
  animation: fade-in linear both;
  animation-timeline: view();
  animation-range: entry 0% entry 100%;
}

/* View Transitions — нативные page transitions */
@view-transition {
  navigation: auto;
}
::view-transition-old(root) {
  animation: fade-out 200ms ease-out;
}
::view-transition-new(root) {
  animation: fade-in 200ms ease-in;
}

/* Container Queries — responsive по родителю */
@container sidebar (width < 100px) {
  .nav-label { display: none; }
  .nav-icon { margin: auto; }
}
```

**💡 ПРОАКТИВ [Предупреждение]:**
- `@media (prefers-reduced-motion: reduce)` — ОБЯЗАТЕЛЬНО для всех анимаций
- `backdrop-filter: blur()` > 15px — дорого, рекомендую 8-12px
- `will-change` — только на анимируемые элементы, убирать после
- Максимум 3-4 parallax-слоя для 60fps
- `transform` вместо top/left (GPU-ускорение)

**Anti-flicker для Vite SPA (CRITICAL):**
```jsx
// ❌ ПЛОХО — мерцание при scroll
<motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} />

// ✅ ХОРОШО — CSS visibility + useInView
const ref = useRef(null);
const isInView = useInView(ref, { once: true });
<div ref={ref} className={`transition-all duration-500 ${isInView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-5'}`} />
```

**Gate 4:** Анимации работают, reduced-motion проверен, 60fps на мобильных → Phase 5

---

### Phase 5: VERIFICATION & DELIVERY

**Цель:** Проверить всё перед сдачей

#### Чеклист PUQI (Platform UI Quality Index)

| Критерий | Вес | Проверка | Min |
|----------|-----|---------|-----|
| **Design Consistency** | x3 | Токены используются, нет хардкод цветов | 8/10 |
| **Responsive** | x3 | 3 breakpoints (mobile/tablet/desktop) | 8/10 |
| **Dark Mode** | x2 | Оба режима протестированы | 7/10 |
| **Accessibility** | x3 | WCAG AA контраст, keyboard nav, ARIA | 8/10 |
| **Performance** | x2 | LCP < 2.5s, no layout shift, lazy-load | 7/10 |
| **Animations** | x1 | Smooth 60fps, reduced-motion support | 7/10 |
| **Typography** | x2 | Иерархия, contrast, readable sizes | 8/10 |
| **Spacing** | x1 | Consistent 4px grid | 8/10 |
| **Icons** | x1 | Одна библиотека, consistent size/stroke | 8/10 |
| **Wow Factor** | x2 | Минимум 1 wow-момент на экран | 6/10 |

**PUQI = сумма (критерий × вес) / 200 × 100**

**Порог:** PUQI ≥ 75 для production. < 75 → вернуться к слабым областям.

#### Проактивные проверки (автоматические)

```
💡 ПРОАКТИВ [Оптимизация]: Финальный аудит
   ✓ Bundle size: shadcn < 50KB, Aceternity components lazy-loaded
   ✓ Fonts: preload critical, display: swap
   ✓ Images: WebP/AVIF, srcset, lazy
   ✓ CSS: no unused Tailwind (PurgeCSS через Vite)
   ✓ A11y: heading hierarchy, alt texts, focus order
   ✓ SEO: meta tags, OG image, structured data
   ✓ Mobile: touch targets 44px, no horizontal scroll
   ✓ Dark mode: tested on every component
```

#### 🎨 UX Principles проверка

```
🎨 UX: [✓минимализм] [✓единство] [✓честность] [✓невидимость] [✓тактильность] [✓восторг]
```

**Gate 5:** PUQI ≥ 75, все чеклисты пройдены → Delivery

---

### Phase 6: SELF-LEARNING LOOP

**Цель:** Скилл становится лучше после каждого использования

**Автоматический цикл:**

1. **Что сработало?** — запомнить комбинации (палитра + шрифт + layout), которые одобрил пользователь
2. **Что отклонили?** — запомнить варианты, которые не подошли (и почему)
3. **Новые паттерны** — если найден новый компонент/эффект, добавить в каталог
4. **Обновление трендов** — если во время работы нашёл новую библиотеку/приём, добавить
5. **Калибровка PUQI** — если пользователь принял результат с PUQI < 75 или отклонил с > 75, пересмотреть веса

**Формат обучения (в конце каждой сессии):**
```
📝 SELF-LEARN:
   Проект: [название]
   Стиль: [выбранный]
   Палитра: [одобрена / отклонена — причина]
   Компоненты: [какие использованы, какие WOW, какие лишние]
   Урок: [1 предложение — что запомнить]
   → Обновить SKILL.md секцию: [какую]
```

---

## Figma Integration — полный цикл

### Код → Figma (загрузить в Figma)

```
1. Загрузить figma:figma-use skill (ОБЯЗАТЕЛЬНО перед use_figma)
2. figma-generate-design → создать экраны из кода
3. figma-generate-library → создать design system (токены, компоненты)
4. Валидация: get_screenshot() + get_metadata()
```

### Figma → Код (реализовать макет)

```
1. figma-implement-design → get_design_context(fileKey, nodeId)
2. get_screenshot() → визуальный референс
3. Маппинг tokens → Tailwind CSS variables
4. Компонентная реализация → shadcn/ui + кастомные
5. visual-replication skill → pixel-perfect проверка
```

### Design System синхронизация

```
1. figma-create-design-system-rules → правила для агентов
2. figma-code-connect → маппинг Figma ↔ код
3. При изменении токенов → обновить и Figma, и код
```

---

## Pencil MCP Integration

Для быстрых макетов без Figma:

```
1. get_guidelines(topic="web-app") → правила для web-app
2. get_style_guide_tags() → доступные стили
3. get_style_guide(tags=[...]) → вдохновение
4. batch_design() → создать макет (max 25 ops/call)
5. get_screenshot() → превью
6. export_nodes() → PNG/PDF
```

---

## Technology Reference

### Tailwind v4 — ключевые фичи

```css
/* CSS-first конфигурация */
@import "tailwindcss";

@theme {
  --color-primary: oklch(0.7 0.2 275);
  --color-surface: oklch(0.15 0.01 260);
  --color-text: oklch(0.92 0 0);
  --radius-lg: 12px;
  --font-display: "Satoshi", sans-serif;
}

/* Container queries (нативные, без плагина) */
@container main (min-width: 768px) {
  .dashboard-card { grid-column: span 2; }
}

/* 3D transforms */
.card-3d {
  @apply rotate-x-6 perspective-1000;
}
```

### shadcn/ui — установка компонентов

```bash
# Инициализация
npx shadcn@latest init

# Добавление компонентов (по одному)
npx shadcn@latest add button card dialog sidebar
npx shadcn@latest add command data-table sheet tooltip

# Структура
src/
  components/
    ui/           ← shadcn компоненты
    custom/       ← кастомные компоненты
    layouts/      ← layout wrappers
    effects/      ← Aceternity/Magic UI wow-компоненты
```

### Aceternity UI — wow-компоненты

```bash
# Установка отдельных компонентов (copy-paste из aceternity.com)
# Зависимости:
npm install framer-motion clsx tailwind-merge
# Для 3D: npm install three @react-three/fiber @react-three/drei
```

### Icons — Lucide

```bash
npm install lucide-react

# Использование
import { Sparkles, Settings, ArrowRight } from "lucide-react";
<Sparkles className="w-5 h-5 text-primary" />
```

---

## Style Presets — готовые направления

### 1. Midnight Tech (AI/SaaS default)
```
Фон: oklch(0.14 0.015 260) → oklch(0.18 0.01 260)
Акцент: oklch(0.7 0.2 275) (фиолетовый)
Текст: oklch(0.92 0 0)
Шрифт: Geist / Geist Mono
Эффекты: glass panels, glow borders, gradient mesh
Иконки: Lucide (stroke 1.5)
Вдохновение: Vercel, Linear, Raycast
```

### 2. Arctic Glass (чистый, светлый)
```
Фон: oklch(0.98 0.005 240)
Акцент: oklch(0.55 0.15 230) (синий)
Текст: oklch(0.2 0.01 260)
Шрифт: Inter / JetBrains Mono
Эффекты: glassmorphism, soft shadows, blur layers
Иконки: Lucide (stroke 2)
Вдохновение: Apple, Notion, Linear (light)
```

### 3. Neon Contrast (дерзкий)
```
Фон: oklch(0.1 0 0)
Акцент: oklch(0.85 0.25 145) (неоновый зелёный)
Текст: oklch(0.95 0 0)
Шрифт: Space Grotesk / Space Mono
Эффекты: glow text, neon borders, particle bg
Иконки: Phosphor (bold)
Вдохновение: GitHub Copilot, Matrix, Warp terminal
```

### 4. Warm Minimal (премиальный)
```
Фон: oklch(0.97 0.01 80)
Акцент: oklch(0.65 0.12 50) (тёплый оранж)
Текст: oklch(0.25 0.02 60)
Шрифт: Plus Jakarta Sans / IBM Plex Mono
Эффекты: subtle shadows, warm gradients
Иконки: Lucide (stroke 2)
Вдохновение: Stripe, Cal.com, Resend
```

### 5. Neubrutalist (контрастный)
```
Фон: oklch(0.97 0 0) (white)
Акцент: oklch(0.6 0.25 30) (ярко-красный) + oklch(0.9 0.15 95) (жёлтый)
Текст: oklch(0.1 0 0) (чёрный)
Шрифт: Instrument Serif / DM Mono
Эффекты: thick borders (3-5px), box-shadow offset, no border-radius
Иконки: Phosphor (fill)
Вдохновение: Figma, Gumroad, Pitch
```

---

## Anti-patterns

| # | Что НЕЛЬЗЯ | Почему | Вместо этого |
|---|-----------|--------|-------------|
| 1 | Хардкод цветов (#hex) | Ломает dark mode, нет единства | Design tokens / CSS variables |
| 2 | opacity:0 для скрытия motion-элементов в SPA | fm-hide bug, мерцание | CSS transitions + useInView |
| 3 | backdrop-filter blur > 20px | Performance, mobile lag | 8-12px blur |
| 4 | Анимации без reduced-motion | Accessibility нарушение | `@media (prefers-reduced-motion)` |
| 5 | #000 фон в dark mode | Выглядит мёртво | oklch(0.14-0.18 0.01 260) |
| 6 | #FFF текст в dark mode | Ослепляет | oklch(0.90-0.95 0 0) |
| 7 | Tailwind v3 синтаксис в v4 | Ломает конфиг | @theme, @import "tailwindcss" |
| 8 | Импорт всей библиотеки анимаций | Bundle bloat | Tree-shake / lazy import |
| 9 | Media queries для компонентов | Не responsive в разных контекстах | Container queries |
| 10 | random decoration / generic fonts | Выглядит непрофессионально | Intentional design system |
| 11 | Shadows в dark mode | Не видны, бесполезны | Light overlay (oklch(1 0 0 / 0.03-0.08)) |
| 12 | Particle/Globe без lazy-load | 200KB+ на первый экран | `React.lazy()` + Suspense |
| 13 | Множество иконопаков | Визуальный хаос | Одна библиотека (Lucide OR Phosphor) |
| 14 | `!important` в Tailwind | Specificity hell | Правильная структура CSS layers |
| 15 | Framer Motion `initial/animate` для scroll | Мерцание в Vite SPA | useInView + CSS transitions |

---

## Resources & Inspiration

### Галереи
- [saasui.design](https://saasui.design) — UI patterns из реальных SaaS
- [saasframe.io](https://saasframe.io) — 166+ dashboard примеров
- [ui.glass/generator](https://ui.glass/generator) — glassmorphism CSS генератор
- [scroll-driven-animations.style](https://scroll-driven-animations.style) — CSS scroll анимации

### Библиотеки компонентов
- [ui.shadcn.com](https://ui.shadcn.com) — shadcn/ui (Radix + Tailwind)
- [ui.aceternity.com](https://ui.aceternity.com) — animated wow-компоненты
- [magicui.design](https://magicui.design) — animated + 3D компоненты
- [daisyui.com](https://daisyui.com) — Tailwind-based, 30+ тем

### Иконки
- [lucide.dev](https://lucide.dev) — 1668+ иконок (shadcn default)
- [phosphoricons.com](https://phosphoricons.com) — 9000+ иконок, 6 весов
- [heroicons.com](https://heroicons.com) — Tailwind UI default

### Шрифты
- [fonts.google.com](https://fonts.google.com) — Inter, Satoshi, Geist, Plus Jakarta Sans
- [fontsource.org](https://fontsource.org) — self-hosted fonts для Vite

### YouTube-каналы (обучение)
- **DesignCourse** (1.08M) — UI/UX crash courses, Figma
- **Flux Academy** (724K) — Web design 101
- **Juxtopposed** (~300K) — креативный веб-дизайн, glass эффекты
- **Adrian Twarog** (~200K) — Figma + Tailwind tutorials
- **Mizko** (155K) — Figma project-based

---

## Quick Start — 5 минут до первого результата

```bash
# 1. Инициализация проекта
npm create vite@latest my-platform -- --template react-ts
cd my-platform
npm install

# 2. Tailwind v4
npm install tailwindcss @tailwindcss/vite
# vite.config.ts: import tailwindcss from '@tailwindcss/vite'

# 3. shadcn/ui
npx shadcn@latest init
npx shadcn@latest add button card sidebar sheet

# 4. Анимации
npm install motion clsx tailwind-merge

# 5. Иконки
npm install lucide-react

# 6. Готово — запускай
npm run dev
```

Затем скажи агенту:
> "Создай дашборд AI-платформы в стиле Midnight Tech с sidebar, чатом и панелью артефактов"

Агент применит Phase 0-5 автоматически с проактивными подсказками на каждом шаге.

---

## Связанные скиллы

| Скилл | Когда подключать |
|-------|-----------------|
| ui-ux-pro-max | Поиск стилей/палитр/шрифтов (search.py) |
| frontend-design | DFII метрика, дизайн-мышление |
| landing-page | Если задача — лендинг (Phase 1-6 лендинга) |
| visual-replication | Pixel-perfect по скриншоту |
| react-best-practices | Оптимизация React (45 правил) |
| tailwind-patterns | Tailwind v4 глубоко |
| figma:figma-use | ОБЯЗАТЕЛЬНО перед use_figma |
| figma:figma-implement-design | Figma → код |
| figma:figma-generate-design | Код → Figma |
| figma:figma-generate-library | Design system → Figma |
| russian-typography | Неразрывные пробелы в русских текстах |
| seo-audit | SEO проверка после создания |
