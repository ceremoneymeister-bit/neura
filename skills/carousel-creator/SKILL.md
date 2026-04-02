---
name: carousel-creator
description: Создание современных Instagram-каруселей из идеи/темы. Полный пайплайн: хук → контент → дизайн → HTML → верификация. Best practices 2026, формат 4:5.
version: 1.1.0
author: Dmitry Rostovtsev (ceremoneymeister)
created: 2026-04-01
updated: 2026-04-01
category: content
tags: [instagram, carousel, design, content, social-media, templates, marketing, 4u, cta, funnel]
risk: safe
maturity: growing
usage_count: 1
last_used: 2026-04-01
---

# carousel-creator — Создание Instagram-каруселей

## Purpose

Генерация современных стильных Instagram-каруселей от идеи до готового HTML. Кодифицирует best practices 2026 + бренд клиента + 6 типов хуков + правила алгоритма Instagram.

## When to Use

- "Сделай карусель", "создай карусель", "carousel"
- "Пост для Instagram", "контент для Insta"
- "Карусель про [тема]", "слайды про [тема]"
- Любая задача по созданию многослайдового контента для Instagram

## Метрики 2026 (зачем именно так)

- Карусели: **1.9× reach** vs одиночные посты, **3× engagement**
- Engagement rate: **1.92%** (vs 0.50% Reels, 0.45% static)
- Алгоритм ценит (в порядке важности): **saves > completion rate > dwell time > shares**
- Решение о свайпе: **1.3 секунды** — хук решает всё
- **8-10 слайдов** — sweet spot (engagement падает после 3-го, растёт после 8-го)

---

## Core Workflow

### Phase 1 — INPUT

Получить от пользователя:

| Параметр | Обязательный | По умолчанию |
|----------|-------------|--------------|
| Тема/идея | Да | — |
| Палитра | Нет | green |
| Тип хука | Нет | авто-выбор по теме |
| Кол-во слайдов | Нет | 8 |
| Клиент | Нет | Victoria Sel |

Если клиент = Victoria Sel → загрузить:
- ToV: `projects/Producing/Victoria_Sel/.agent/skills/victoria-tone-of-voice/SKILL.md`
- Content generator: `projects/Producing/Victoria_Sel/.agent/skills/victoria-content-generator/SKILL.md`
- Brandbook: `projects/Producing/Victoria_Sel/08_Assets/brand/BRANDBOOK.md`
- Catalog: `projects/Producing/Victoria_Sel/08_Assets/brand/generated/catalog.json`

### Phase 2 — HOOK (первый слайд)

**Правило:** хук решает 80% успеха карусели. 1.3 секунды на решение.

**Формула 4U для заголовка cover-слайда:**

| U | Что | Примерные паттерны |
|---|-----|--------------------|
| **Usefulness** | Что получит читатель | "Научишься создавать AI-ботов" |
| **Ultra-specificity** | Измеримый результат | "за 5 шагов", "за 10 минут" |
| **Uniqueness** | Чем отличается | "без программирования", "без бюджета" |
| **Urgency** | Временной элемент | "прямо сейчас", "пока бесплатно" |

Примеры cover-заголовков по 4U:
- "5 AI-инструментов, которые сэкономят 10 часов/нед — бесплатные"
- "Как запустить Telegram-бота за 30 минут без кода — пошаговый гайд"
- "3 ошибки в AI-автоматизации, которые стоят 100k₽/мес — проверь себя"

Не обязательно все 4U в одном заголовке — минимум 2 из 4.

**6 типов хуков** (выбрать по теме):

| Тип | Формула | Когда использовать | Пример |
|-----|---------|-------------------|--------|
| **Question** | "Ты правда [убеждение]?" | Разрушение мифов | "Ты правда думаешь, что привычка формируется за 21 день?" |
| **Shock** | "[X%] [группа] [проблема]. Вот что делают [Y%]." | Статистика, данные | "87% людей живут на автопилоте. Вот как переключиться." |
| **Promise** | "Как [результат] без [препятствие]" | Обучающий контент | "Как перестать тревожиться без медитации и таблеток" |
| **Steps** | "Как [цель] за [X] шагов →" | Пошаговые инструкции | "Как перепрошить реакцию за 4 шага →" |
| **Myth** | "Ты [делаешь] неправильно" | Провокация + коррекция | "Ты расслабляешься неправильно. Вот почему." |
| **Curiosity** | "Я [действие]... вот что произошло →" | Личные истории | "Я 49 дней делала одну практику... вот что изменилось →" |

**Дизайн cover:**
- Макс **8-10 слов** (squint test — читаемо при прищуре)
- Шрифт: **64-80px** Inter SemiBold или Source Serif 4
- Текст в **верхних 60%** (низ закрыт UI Instagram)
- Обязательно: **swipe indicator** ("→" или "листай") — +15-30% свайпов
- Фон: dramatic overlay 70-85% поверх текстуры

### Phase 2.5 — THEME-RHEME FLOW (межслайдовая связка)

Каждый слайд строится по схеме **ИЗВЕСТНОЕ (theme) → НОВОЕ (rheme)**:

- Slide 1 (cover): Известная проблема → обещание нового решения
- Slide 2: Повтор обещания → первый пункт
- Slide 3: Развитие первого пункта → второй пункт
- ...
- **Первая строка слайда** = callback к главной идее предыдущего слайда
- **Последняя строка слайда** = hook на следующий слайд

Это создаёт эффект "невозможно остановиться" — каждый свайп подтверждается и вознаграждается.

⚠️ **Антипаттерн:** слайды как изолированные карточки без связи = потеря completion rate.

### Phase 3 — CONTENT (слайды 2-N)

**Slide 2: Credibility** — зачем листать дальше

4 шаблона:
- "Почему это важно" — для доверительных тем
- "Что ты узнаешь" — roadmap карусели (1→2→3)
- "Proof" — кейс или факт
- "Самоквалификация" — "Если ты [ситуация], это для тебя"

**Slides 3-7: Content** — основной контент

Правила:
- **1 мысль = 1 слайд** (не полотно текста!)
- **Open loop** между слайдами: "Но это не всё..." / "А теперь главное..." / "Дальше — интереснее"
- **Bold key phrases** — дизайн для скиммеров
- Макс **40-60 слов** на слайд
- Шрифт body: **24-28px** Source Serif 4

**Slide 8-9: Key Insight** — главный вывод

- Highlight box (border-left accent + italic)
- Одно мощное утверждение
- Научный факт + эмоциональный вывод

**Slide 10: CTA** — мягкое приглашение

CTA формулы:
- **Save:** "Сохрани на случай, когда [ситуация]"
- **Send:** "Отправь тому, кто [описание]"
- **DM:** "Напиши '[слово]' в директ"
- **Follow:** "Подпишись — каждую [день] новая [тема]"

**CTA Stress Matrix** — подбирай CTA по температуре аудитории:

| Аудитория | CTA | Давление |
|-----------|-----|----------|
| **Холодная** (Explore, хэштеги) | "Сохрани 🔖" / "Подпишись" | Минимальное |
| **Тёплая** (подписчики) | "Напиши 🔥 в комменты" / "Скачай гайд по ссылке" | Среднее |
| **Горячая** (вовлечённые) | "Записывайся на МК" / "Тест-драйв 7 000₽" | Высокое |

**Правило:** Если карусель рассчитана на холодную аудиторию (хэштеги, Explore) → НИКОГДА не ставить высокое давление CTA.

**Вопрос на последнем слайде** — бустер комментариев. Пример: "А у тебя так же? Напиши в комменты 👇"

⚠️ **Victoria Sel specific:** ТОЛЬКО мягкие CTA. ЗАПРЕЩЕНО: "Записывайся!", "Осталось N мест!", urgency, FOMO.

### Phase 3.5 — ENGAGEMENT BOOSTERS + FUNNEL TYPE

**Бустеры охватов** (применять к каждой карусели):

- **Конкретные числа** в заголовках: "7 инструментов", НЕ "несколько инструментов"
- **Списки/чек-листы** — естественный формат для каруселей, алгоритм ценит saves
- **Контраст** в cover: неожиданный угол ("Перестань медитировать. Вот почему.")
- **Серия** "Часть 1/3" — создаёт возвраты, подписки, ожидание следующей части
- **Вопрос на последнем слайде** — бустер комментариев (алгоритм = engagement)

**Тип карусели по воронке** (определить ДО создания контента):

| Тип | Цель | CTA | Пример финального слайда |
|-----|------|-----|--------------------------|
| **Lead magnet** | Обучить, дать ценность | "Скачай гайд" (бесплатно) | Ссылка в био на PDF/чек-лист |
| **Tripwire** | Тизер платного контента | Низкий чек (490-2990₽) | "Полный курс за 990₽ — ссылка в био" |
| **Authority** | Экспертность, доверие | "Подпишись" | Кейс/результат + приглашение |
| **Sales** | Прямая продажа | Оффер + дедлайн | Цена + бонус + "до [дата]" |

⚠️ Victoria Sel: только Lead magnet и Authority. Tripwire/Sales — для других клиентов.

### Phase 4 — DESIGN (визуальная композиция)

**Формат: 1080×1350px (4:5)** — НЕ 1:1!

**Layer stack (каждый слайд):**
```
.slide {1080×1350px}
  ├─ .bg        → текстура (cover/object-fit)
  ├─ .element   → декоративный элемент (mix-blend-mode: screen/multiply, opacity 0.06-0.25)
  ├─ .overlay   → градиент для контраста (radial/linear)
  └─ .content   → текст (z-index: 10, padding: 80-100px)
```

**Texture↔Theme matching:**

| Тема контента | Текстуры | Элементы |
|--------------|----------|----------|
| Перепрошивка, нейроны | nature-neurons, glass-mixed | neural-network, bio-network, bark-circuit |
| Тело, соматика | moss-macro, water-surface | body-silhouette, fern-fractal |
| 49 дней, время, процесс | fern-fractal, succulent | moon-phases, spiral-path, ammonite |
| Секретный ингредиент | golden-light, glass-amber | golden-particles, spiral-path |
| Наука, факты | parchment, leaf-veins | leaf-skeleton, neural-network |
| Природа, рост | moss-macro, mushroom-gills | dry-botanics, coral-honeycomb |
| Стекло, свет, прозрачность | glass-green, glass-amber | golden-particles, ammonite |

**Overlay intensity по типу слайда:**

| Тип слайда | Overlay opacity | Стиль |
|-----------|----------------|-------|
| Cover (Hook) | 70-85% | Dramatic, тёмный |
| Credibility | 60-70% | Средний |
| Content | 50-65% | Readable |
| Key Insight | 55-70% | Акцентный |
| CTA | 40-55% | Тёплый, inviting |

**Палитры:**

Earth:
- Text light: `#E1D3A9` (на тёмном), `#371E13` (на светлом)
- Accent: `#B54B11` (теги, highlight, кнопки)
- Muted: `#C0AA8A` (подписи, мелкий текст)

Green:
- Text light: `#f0ead2` (на тёмном)
- Accent: `#B54B11` (оранжевый — только для акцентов!)
- Muted: `#d4c9a8` (подписи)
- Highlight: `rgba(181,75,17,0.12)` (box background)

**Типографика:**

| Элемент | Шрифт | Размер (4:5) | Вес |
|---------|-------|-------------|-----|
| Hook (cover) | Source Serif 4 | 64-80px | 500 |
| Slide heading | Inter | 34-40px | 700 |
| Body text | Source Serif 4 | 26-30px | 300-400 |
| Tag/label | Inter | 13-14px uppercase | 600 |
| Slide number | Caveat | 24px | 400 |
| CTA question | Source Serif 4 | 52-64px | 400 |
| CTA button | Inter | 17px uppercase | 600 |
| Author | Inter | 15px | 400 |

### Phase 5 — BUILD (HTML generation)

Сгенерировать файл: `templates/carousel-{topic-slug}.html`

Структура HTML:
```html
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=1080">
  <title>Carousel — {Topic}</title>
  <link fonts>
  <style>
    .slide { width: 1080px; height: 1350px; position: relative; overflow: hidden; }
    .slide .bg { position: absolute; inset: 0; background-size: cover; }
    .slide .element { position: absolute; inset: 0; background-repeat: no-repeat; }
    .slide .overlay { position: absolute; inset: 0; }
    .slide .content { position: relative; z-index: 10; height: 100%; padding: 80px; }
    /* Per-slide styles */
  </style>
</head>
<body>
  <!-- Slide 1: Cover -->
  <!-- Slide 2: Credibility -->
  <!-- Slides 3-7: Content -->
  <!-- Slide 8-9: Key Insight -->
  <!-- Slide 10: CTA -->
</body>
</html>
```

После создания:
1. Добавить в `catalog.json` с уникальными ID
2. Обновить `studio.html` если нужно (каталог динамический)

### Phase 6 — VERIFY

**Чек-лист (все пункты обязательны):**

- [ ] Формат **4:5** (1080×1350), НЕ 1:1
- [ ] Hook **≤ 10 слов**, squint test пройден
- [ ] **1 мысль = 1 слайд**, нет полотен текста
- [ ] Текст в **safe zone** (верхние 60-70%)
- [ ] **Контраст** достаточный (overlay на каждом слайде)
- [ ] **Нет запрещённых слов** (масштабирование, инфоцыганщина, прогрев, оффер и т.д.)
- [ ] CTA **мягкий** (приглашение, не давление)
- [ ] **Swipe indicator** на cover ("→" или "листай")
- [ ] **Progress dots** на каждом слайде
- [ ] **Open loops** между слайдами
- [ ] **Author footer** на каждом слайде (Victoria Sel)
- [ ] Текстуры и элементы **соответствуют теме** по matching table
- [ ] Tone-of-voice чек-лист пройден (для Victoria)
- [ ] Cover-заголовок содержит **минимум 2 из 4U** (usefulness, ultra-specificity, uniqueness, urgency)
- [ ] **Theme-Rheme flow**: каждый слайд начинается с callback к предыдущему
- [ ] **CTA stress** соответствует температуре аудитории (холодная ≠ высокое давление)
- [ ] **Тип воронки** определён (lead magnet / tripwire / authority / sales)

---

## Anti-Patterns

1. ❌ **Квадратный формат (1:1)** → ВСЕГДА 4:5 (1080×1350). 4:5 занимает максимум экрана
2. ❌ **Cover > 12 слов** → Невозможно остановить скролл за 1.3 сек
3. ❌ **Текст-полотно** → 1 мысль = 1 слайд, макс 40-60 слов
4. ❌ **Жёсткий CTA** → "Записывайся!", "Осталось 3 места!" — ЗАПРЕЩЕНО для Victoria
5. ❌ **Текст без overlay** → На любой текстуре/фото ОБЯЗАТЕЛЬНО полупрозрачный градиент
6. ❌ **Одинаковые хуки подряд** → Чередовать 6 типов, не повторяться
7. ❌ **Нет open loop** → Каждый слайд намекает на следующий, иначе completion rate падает
8. ❌ **Текст в нижних 40%** → Закрыт UI Instagram (лайки, комменты)
9. ❌ **Мелкий шрифт (< 24px body)** → Нечитаемо на мобилке при скролле
10. ❌ **Случайный выбор текстур** → Текстура должна соответствовать теме по matching table
11. ❌ **Изолированные слайды** → Без Theme-Rheme связки completion rate падает. Каждый слайд = мост к следующему
12. ❌ **Высокий CTA на холодную аудиторию** → "Записывайся на МК" в Explore-контенте = отписки
13. ❌ **Размытые числа** → "Несколько способов" вместо "7 способов" = меньше кликов и saves

## Tools & Integrations

| Инструмент | Назначение |
|-----------|------------|
| victoria-content-generator | Генерация текстов в ToV Виктории |
| victoria-tone-of-voice | Проверка тона |
| nano-banana-pro | Генерация новых текстур при необходимости |
| visual-replication (visual-analyzer.py) | Верификация палитры и контраста |
| catalog.json | Регистрация новых каруселей с ID |
| studio.html (Brand Studio) | Просмотр и редактирование Викторией |

## References

- [Instagram Carousel Strategy 2026](https://www.truefuturemedia.com/articles/instagram-carousel-strategy-2026) — TrueFuture Media
- [Top Instagram Carousel Hooks](https://resont.com/blog/top-instagram-carousel-hooks/) — Resont
- [Mastering Carousel Strategy 2026](https://marketingagent.blog/2026/01/03/mastering-instagram-carousel-strategy-in-2026/) — Marketing Agent
- [Instagram Carousel Best Practices](https://blog.hootsuite.com/instagram-carousel/) — Hootsuite
- [Best Practices for Carousels 2026](https://metricool.com/instagram-carousels/) — Metricool
- Источники маркетинговых фреймворков: НЕЧ20 (4U, CTA stress matrix, Theme-Rheme flow), Тимочко (бустеры охватов)
