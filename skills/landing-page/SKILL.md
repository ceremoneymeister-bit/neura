---
name: landing-page
description: "This skill should be used when creating, building, or designing a landing page, conversion page, or promotional web page. It orchestrates copy, design, psychology, SEO, and implementation into a unified workflow with quality scoring."
version: 1.0.0
category: dev
tags: [landing-page, conversion, copywriting, design, seo, react, tailwind]
risk: safe
source: internal
---

# Landing Page — Unified Creation Workflow

Оркестратор для создания лендингов от брифа до деплоя. Объединяет 10 скиллов экосистемы в единый последовательный процесс с hard gates и скорингом качества.

## Зависимые скиллы (читать по мере необходимости)

| Скилл | Фаза | Что берём |
|-------|------|-----------|
| copywriting | 1, 4 | Brief framework, Feature→Benefit→Outcome |
| marketing-psychology | 2 | Ментальные модели, PLFS-скоринг |
| frontend-design | 2, 3 | DFII-скоринг, дизайн-направление |
| ui-ux-pro-max | 3 | Дизайн-система, палитра, типографика |
| tailwind-patterns | 3, 5 | Tailwind v4 CSS-first, утилиты |
| react-best-practices | 5 | Архитектура компонентов, оптимизация |
| russian-typography | 4 | `&nbsp;` после предлогов/союзов/частиц |
| seo-audit | 4, 6 | Мета-теги, OG, структура |
| brand-voice-clone | 1 | Профиль голоса бренда (если есть) |
| verification-before-completion | 6 | 5-step verification gate |

---

## Фаза 1: Discovery & Brief

**Цель:** Собрать полный контекст перед любой работой.

```pseudo
INPUT: user_request

brief = {
  purpose: "",        // Зачем страница? (продажа, лид, запись, waitlist)
  product: "",        // Что продаём? Ключевые характеристики
  audience: "",       // Кто целевая? Боли, желания, уровень awareness
  traffic_source: "", // Откуда трафик? (ads, organic, email, social)
  brand_voice: "",    // Тон (проверить brand-voice профиль если есть)
  competitors: "",    // Кто конкуренты? Чем отличаемся?
  constraints: ""     // Бюджет, сроки, техн. ограничения
}

// Определить уровень awareness аудитории:
// unaware → problem-aware → solution-aware → product-aware → most-aware
// Это определяет длину страницы и количество образовательных секций

awareness_level = classify_awareness(brief.audience, brief.traffic_source)
```

### Правило 3 секунд (Источник: НЕЧ20 / ConversionArt)
Если посетитель не понимает, о чём страница, за 3 секунды — он уходит. Первый экран должен мгновенно отвечать на два вопроса: **«Что вы предлагаете?»** и **«Почему мне это нужно?»** Тестируй brief через этот фильтр: если нельзя сформулировать ответ в одно предложение — brief недоработан.

**Действия:**
1. Задать пользователю вопросы по каждому полю brief (или извлечь из контекста)
2. Если есть brand-voice профиль в `profiles/` — загрузить и учесть
3. Определить `awareness_level` аудитории (см. `references/conversion-architecture.md`)
4. Сформулировать 1 предложение: "Страница должна [действие] для [аудитория] через [механизм]"
5. Проверить через «правило 3 секунд»: можно ли за 3 секунды понять суть предложения из brief?

### HARD GATE: Brief Lock
**Показать brief пользователю → получить подтверждение.**
Не переходить к Фазе 2 без явного "да" / "ок" / "погнали".
Если пользователь вносит правки — обновить brief и снова показать.

---

## Фаза 2: Strategy & Psychology

**Цель:** Выбрать ментальные модели и дизайн-направление.

```pseudo
// 1. Загрузить marketing-psychology SKILL.md
// 2. Выбрать 3-5 моделей с PLFS ≥ 8

models = select_mental_models(brief, count=3..5, min_plfs=8)

// 3. Маппинг моделей на секции (см. conversion-architecture.md)
section_map = {}
for model in models:
    section_map[model] = best_section(model, awareness_level)

// 4. Выбрать дизайн-направление
design_direction = {
  mood: "",          // Напр: "технологичный минимализм" / "тёплый и живой"
  hero_type: "",     // См. design-patterns.md — 5 вариантов
  color_approach: "" // Монохром / Duo-tone / Brand-driven
}
```

**Действия:**
1. Прочитать `marketing-psychology` SKILL.md
2. Выбрать 3-5 ментальных моделей, показать маппинг: модель → секция → как применяем
3. Определить hero-тип и общее дизайн-направление
4. Показать стратегию пользователю

### Правило 80/20 — первый экран (Источник: НЕЧ20 / ConversionArt)
Данные eye-tracking (NENGROUP): **80% времени посетитель проводит на первом экране, 20% — на всех остальных вместе.** Это означает: первый экран должен быть самодостаточным и доносить ключевое сообщение полностью. Стратегия должна концентрировать лучшие модели и сильнейший копи именно на Hero-секции.

### Decision Gate: Strategy Approved
Пользователь видит: модели, маппинг на секции, дизайн-направление. Согласует или корректирует.

---

## Фаза 3: Design System

**Цель:** Создать дизайн-систему до написания кода.

```pseudo
// 1. Загрузить ui-ux-pro-max SKILL.md
// 2. Сгенерировать дизайн-систему

design_system = generate_design_system({
  domain: "landing",
  mood: design_direction.mood,
  brand: brief.brand_voice
})

// Обязательные компоненты:
// - OKLCH палитра (primary, secondary, accent, neutral, semantic)
// - Типографика: НЕ Inter, НЕ Roboto, НЕ system fonts
// - Spacing scale: 4px base
// - Border radius, shadows, transitions
// - Dark/light mode через CSS custom properties

// 3. DFII-скоринг (frontend-design)
dfii = score_dfii(design_system)
```

**Действия:**
1. Прочитать `ui-ux-pro-max` SKILL.md, запустить `--design-system --domain landing`
2. Прочитать `tailwind-patterns` SKILL.md для Tailwind v4 CSS-first конфигурации
3. Сгенерировать палитру, типографику, spacing
4. Прочитать `frontend-design` SKILL.md, применить DFII-скоринг

### HARD GATE: DFII ≥ 8
Если DFII < 8 — итерировать дизайн-систему. Не переходить к контенту с плохой основой.

---

## Фаза 4: Content Creation

**Цель:** Написать весь копирайтинг страницы.

```pseudo
// 1. Загрузить copywriting SKILL.md (Phases 3-5)
// 2. Для каждой секции (из conversion-architecture.md):

for section in page_sections:
    copy[section] = {
      headline: generate_headlines(3),  // 3 варианта
      body: write_body(section, models_map),
      cta: generate_cta(3)              // 3 варианта
    }
    // Feature → Benefit → Outcome цепочки для каждого пункта

// 3. Russian typography
apply_nbs(copy)  // &nbsp; после предлогов, союзов, частиц ≤3 букв

// 4. SEO мета-теги
meta = {
  title: "",        // ≤60 символов
  description: "",  // ≤160 символов
  og_title: "",
  og_description: "",
  og_image: ""
}
```

### CTA Stress Matrix (Источник: НЕЧ20 / ConversionArt)

Фундаментальный принцип: **Стресс CTA ≤ Уровень доверия посетителя.** Каждый CTA имеет уровень стресса — он должен соответствовать awareness и доверию аудитории.

| Тип CTA | Стресс | Когда использовать |
|---------|--------|--------------------|
| Скачать каталог / гайд | Низкий | Холодный трафик, unaware аудитория |
| Получить КП / расчёт | Средний | Problem-aware, есть базовое доверие |
| Записаться / вызвать замерщика | Высокий | Solution-aware, тёплая аудитория |
| Купить / оплатить | Максимальный | Product-aware, горячая аудитория |

Две тактики:
1. **Min-stress CTA** — максимум лидов (холодный трафик, первое касание)
2. **Max-tolerable CTA** — качественные лиды (тёплый трафик, ретаргетинг)

При выборе CTA для каждой секции — сверяться с `awareness_level` из brief.

**Действия:**
1. Прочитать `copywriting` SKILL.md
2. Написать копи для каждой секции (см. `references/copy-frameworks.md`)
3. Для каждой фичи — Feature → Benefit → Outcome цепочка
4. 3 варианта заголовков Hero + 3 варианта основного CTA
5. Подобрать CTA по CTA Stress Matrix — стресс не должен превышать доверие аудитории
6. Прочитать `russian-typography` SKILL.md — применить `&nbsp;` правила
7. Прочитать `seo-audit` SKILL.md — написать мета-теги
8. Показать лучшие варианты пользователю, выбрать

---

## Фаза 5: Implementation

**Цель:** Реализовать лендинг в коде.

```pseudo
// Стек: React + Vite + Tailwind v4
// Загрузить react-best-practices SKILL.md

structure = {
  framework: "React + Vite",
  styling: "Tailwind v4 CSS-first",
  responsive: "mobile-first: 375 → 768 → 1024 → 1440",
  theme: "dark/light via CSS custom properties",
  a11y: "contrast ≥ 4.5:1, semantic HTML, focus management"
}

// Порядок реализации:
// 1. CSS variables + Tailwind config (@theme)
// 2. Layout skeleton (секции в правильном порядке)
// 3. Hero секция (первое впечатление)
// 4. Остальные секции top-to-bottom
// 5. CTA-блоки и интерактивность
// 6. Responsive проверка всех breakpoints
// 7. Dark mode переключение
// 8. Performance: lazy loading, оптимизация бандла
```

**Действия:**
1. Прочитать `react-best-practices` SKILL.md
2. Прочитать `tailwind-patterns` SKILL.md
3. Создать проект (или компонент в существующем)
4. Реализовать секции в порядке из conversion-architecture.md
5. Применить дизайн-систему из Фазы 3
6. Вставить копирайтинг из Фазы 4
7. Mobile-first: начать с 375px, расширять
8. Применить паттерны из `references/design-patterns.md`

---

## Фаза 6: Verification & Delivery

**Цель:** Проверить качество и собрать проект.

### LPQI — Landing Page Quality Index

| Ось | Макс | Источник | Критерии |
|-----|------|----------|----------|
| Design (DFII) | /15 | frontend-design | Визуальная гармония, типографика, spacing, цвет |
| Copy Quality | /10 | copywriting | Заголовки, CTA, F→B→O цепочки, тон |
| SEO Readiness | /10 | seo-audit | Meta, OG, семантика, alt, H1-H6 |
| Psychology | /10 | marketing-psychology | Модели интегрированы, не декоративны |
| Technical | /10 | react + build | Build OK, responsive, a11y, perf |
| **Итого** | **/55** | | **Порог: ≥ 40** |

```pseudo
// 1. Скоринг по каждой оси
lpqi = score_all_axes()

IF lpqi.total < 40:
    identify_weakest_axis(lpqi)
    iterate_and_rescore()

// 2. Build verification
run("npm run build")  // или vite build
assert build.exit_code == 0

// 3. Pre-delivery checklist (references/design-patterns.md)
checklist = run_pre_delivery_checklist()

// 4. verification-before-completion 5-step gate
run_verification_skill()
```

**Действия:**
1. Оценить каждую ось LPQI, показать таблицу с баллами
2. Если < 40 — определить слабейшую ось, исправить, пересчитать
3. `vite build` — должен пройти без ошибок
4. Прочитать `verification-before-completion` SKILL.md, пройти 5-step gate
5. Пройти pre-delivery checklist из `references/design-patterns.md`
6. Показать финальный LPQI и чеклист пользователю

---

## Anti-Patterns

| # | Anti-Pattern | Проверка |
|---|-------------|----------|
| 1 | Скипнуть brief, сразу дизайнить | Brief Lock пройден? |
| 2 | Generic template look | Differentiation Anchor: чем визуально отличается от конкурентов? |
| 3 | Inter / Roboto / system fonts | Шрифт уникален? Не из "дефолтных 5"? |
| 4 | Психология как декорация | Каждая модель привязана к конкретной секции с конкретным приёмом? |
| 5 | Фичи без Benefit→Outcome | Каждая фича имеет цепочку F→B→O? |
| 6 | Claim completion без build | `vite build` прошёл? LPQI ≥ 40? |
| 7 | Забыть русскую типографику | `&nbsp;` после предлогов/союзов/частиц? |
| 8 | Мерцание анимаций (flicker) | См. ⚡ Anti-Flicker ниже |
| 9 | Стоковые фото на первом экране | Реальные фото продукта/команды/процесса? (НЕЧ20) |
| 10 | CTA стрессует больше, чем доверяет аудитория | CTA Stress ≤ Trust Level? (НЕЧ20) |

---

## ⚡ Anti-Flicker: Анимации секций (Framer Motion / Vite SPA)

Scroll-анимации в Vite SPA мерцают если сделаны неправильно. Проверенный паттерн:

### Запрещено
- `stagger.hidden: { opacity: 0 }` при том что дети тоже анимируют opacity → двойное мерцание
- CSS `.fm-hide { opacity: 0 }` на motion-элементах → ломает видимость
- Отдельный `whileInView` на каждом элементе секции → двойное срабатывание

### Рабочий паттерн: useInView + CSS transitions
```jsx
const ref = useRef(null);
const isInView = useInView(ref, { once: true, margin: "-50px" });

<div ref={ref}>
  <div style={{
    opacity: isInView ? 1 : 0,
    transform: isInView ? 'translateY(0)' : 'translateY(20px)',
    transition: 'opacity 0.5s ease, transform 0.5s ease',
  }}>ЗАГОЛОВОК</div>
  {items.map((item, i) => (
    <div style={{
      opacity: isInView ? 1 : 0,
      transform: isInView ? 'translateY(0)' : 'translateY(20px)',
      transition: 'opacity 0.5s ease, transform 0.5s ease',
      transitionDelay: `${0.1 + i * 0.08}s`,
    }}>КАРТОЧКА</div>
  ))}
</div>
```

### Правила
1. **Один `useInView` ref на секцию** — единственный триггер
2. **CSS transition** вместо framer-motion — браузерный compositor, 0 glitches
3. **transitionDelay** для каскада вместо staggerChildren
4. **Duration 0.4–0.6s** — больше 0.8s = ощущение задержки
5. **once: true** — анимация один раз

**Перед сдачей — пройти каждый пункт. Если хоть один "нет" — исправить.**

---

## Quick Reference

### Секции лендинга (стандартный порядок)
Hero → Social Proof → Pain/Problem → Solution → Benefits → How It Works → Proof/Testimonials → FAQ → Final CTA

### Awareness → Длина страницы
- **Unaware:** Длинная, много образования. Hero = провокация/история
- **Problem-aware:** Средняя. Hero = "Знакомо? Вот решение"
- **Solution-aware:** Средняя. Hero = "Почему именно мы"
- **Product-aware:** Короткая. Hero = оффер + социальное доказательство
- **Most-aware:** Минимальная. Hero = CTA + цена

### CTA-стратегии

**По уровню стресса (НЕЧ20):**

| Стресс | CTA | Аудитория |
|--------|-----|-----------|
| Низкий | "Скачать бесплатно" / "Получить гайд" | Холодная, unaware |
| Средний | "Получить расчёт" / "Обсудить проект" | Problem-aware |
| Высокий | "Записаться на консультацию" / "Вызвать замерщика" | Solution-aware |
| Макс | "Купить за X ₽" / "Начать за X ₽" | Product-aware, горячая |

**По типу:**
- **Purchase:** "Купить за X ₽" / "Начать за X ₽"
- **Lead magnet:** "Скачать бесплатно" / "Получить гайд"
- **Free trial:** "Попробовать бесплатно" / "7 дней бесплатно"
- **Consultation:** "Записаться на консультацию" / "Обсудить проект"
- **Waitlist:** "Занять место" / "Войти в список ожидания"

### Анатомия первого экрана (Источник: НЕЧ20 / ConversionArt)

Первый экран **обязан** содержать:
1. **Шапка:** Логотип + Дескриптор + Телефон (формат 8-800, не мобильный) + Кнопка обратного звонка
2. **Заголовок:** По формуле 4U (см. headline-lab скилл)
3. **Подзаголовок:** Выгоды, которые не вместились в заголовок
4. **Изображение:** Реальное фото (НЕ сток!) — продукт, процесс, результат, команда
5. **Форма захвата:** С CTA, соответствующим уровню доверия аудитории
6. **Иконки преимуществ:** 2-3 ключевых факта (бесплатный X, гарантия Y лет, от Z ₽)

**Антипаттерны для изображений:**
- Стоковые офисные работники
- Белые 3D-человечки
- Абстрактные фото без связи с продуктом
- Используй реальные фото продукта / команды / процесса / результата

### Размещение квиза (Источник: НЕЧ20 / ConversionArt)

- Квиз на **2-м экране** — CTA первого экрана скроллит к нему
- **Дублировать квиз перед футером** — ловит тех, кто быстро прокрутил до конца
- Квиз + футер = перехватывает и внимательных читателей, и быстрых скроллеров
- Если формат страницы «unit by quiz» — весь лендинг строится вокруг квиза

### Топ-10 конвертирующих типов экранов (Источник: НЕЧ20 / ConversionArt)

1. Первый экран (hero + CTA)
2. Социальное доказательство (логотипы, цифры)
3. Боль / Проблема (артикуляция)
4. Каталог продуктов / услуг
5. Процесс / Как это работает (шаги)
6. До / После
7. Отзывы / Кейсы
8. Команда
9. FAQ
10. Финальный CTA + резюме оффера

Полный список (20 типов) — в рабочей тетради НЕЧ20.

Детальные фреймворки → `references/`
