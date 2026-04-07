---
name: visual-replication
description: "This skill should be used when replicating a visual design from a screenshot, mockup, or reference image into code. It extracts exact colors, layout parameters, and spacing, then iterates using Playwright screenshots for pixel-accurate results."
version: 2.1.0
author: Dmitry Rostovtsev (ceremoneymeister)
created: 2026-04-01
updated: 2026-04-01
category: development
tags: [design, visual, frontend, css, replication, screenshot, pixel-perfect]
risk: safe
source: internal
proactive_enabled: false
proactive_trigger_1_type: event
proactive_trigger_1_condition: "скриншот/макет для воспроизведения"
proactive_trigger_1_action: "pixel-perfect реплика"
learning_track_success: true
learning_track_corrections: true
learning_evolve_threshold: 5
learning_auto_update: [anti-patterns, triggers, changelog]
---

# visual-replication

## Purpose

Точное воспроизведение визуального дизайна из референсного изображения (скриншот, макет, фото) в код (React + Tailwind). Закрывает две слепые зоны: извлечение точных параметров из картинки и обратная связь через скриншот результата.

## When to Use

- Пользователь присылает скриншот/макет и просит воспроизвести
- "Сделай как на картинке", "повтори этот дизайн", "pixel-perfect"
- "Сверстай по макету", "по референсу"
- Любая задача, где нужно визуально совпасть с образцом
- Сравнение двух версий сайта (до/после)

### Проактивный триггер

Если при работе над фронтендом пользователь прислал изображение через Read tool — **автоматически** предложить:
> "Вижу референс. Запустить visual-analyzer для точных параметров? (Да / Нет)"

Не ждать пока скажут "сделай pixel-perfect" — предложить сам.

### Когда НЕ использовать

- Макет в Figma → использовать `figma:figma-implement-design` (точнее, есть токены)
- Простая правка цвета/шрифта → не нужен полный workflow, достаточно `visual-analyzer.py` напрямую
- Контент без визуала (текст, структура) → скилл не поможет
- SVG-иконки → напрямую скопировать код, не анализировать как растр

## Core Workflow

### Phase 1 — Извлечение (Extract)

**1.1 Визуальный анализ (мультимодальный)**

Прочитать изображение через Read tool. Описать словами:
- Общий стиль (минимализм, neo-brutalist, corporate, playful)
- Расположение блоков (header, hero, grid, footer)
- Визуальные акценты (градиенты, тени, скруглённости, анимации)
- Типографика (размер заголовков vs body, жирность, межстрочный)
- Иконки и декоративные элементы

**1.2 Инструментальный анализ**

```bash
python3 scripts/visual-analyzer.py <image_path>
```

Скрипт извлекает:
- **Палитра** — топ-N цветов с HEX, RGB, процент площади, роль (bg/text/accent)
- **Layout** — размеры, aspect ratio, количество колонок, зоны контента
- **Typography** — тема (dark/light), контраст, плотность текста
- **Font sizes** — heading/body в px, Tailwind-классы, scale (compact/moderate/dramatic)
- **Gradients** — направление, стопы, готовый CSS `linear-gradient()`
- **Components** — UI-элементы: navbar, hero, cards, buttons, icons (contour detection)
- **Border-radius** — стиль (sharp/subtle/moderate/rounded/pill) → Tailwind-класс
- **Shadows** — интенсивность (none/subtle/moderate/prominent/heavy) → Tailwind-класс
- **Spacing** — паттерн (tight/comfortable/spacious), средний gap
- **WCAG** — контрастность пар цветов, AA/AAA compliance
- **Design tokens** — готовый `tailwind.config.js` + CSS custom properties

**1.3 Дизайн-бриф**

Объединить 1.1 + 1.2 в структурированный бриф:

```
Стиль: [описание]
Палитра: bg=#xxx, text=#xxx, accent=#xxx
Layout: [N]-col, [spacing_pattern]
Шрифт: [наблюдения]
Ключевые элементы: [список]
```

### Phase 2 — Реализация (Implement)

**2.1 Структура компонентов**

Разбить макет на React-компоненты снизу вверх:
1. Атомы (кнопки, бейджи, инпуты)
2. Молекулы (карточки, навбар)
3. Секции (Hero, Features, CTA)
4. Страница (сборка)

**2.2 Стили**

Приоритет источников стилей:
1. Tailwind-классы (основной)
2. CSS-переменные из visual-analyzer (цвета)
3. Inline styles (только для динамических значений)

Правила:
- Цвета — ТОЛЬКО из палитры visual-analyzer, НЕ "на глаз"
- Spacing — брать из анализа (`avg_gap_pct` → конвертировать в rem/px)
- Border-radius — оценить визуально (none / sm / md / lg / full)
- Shadows — оценить визуально (none / sm / md / lg)

**2.3 Контент**

- Текст — из референса (если читаем) или placeholder
- Изображения — заглушки `/api/placeholder/WxH` или реальные
- Иконки — Lucide React (ближайший аналог)

### Phase 3 — Верификация (Verify)

**3.1 Playwright-скриншот**

```bash
# Скриншот с viewport из референса (W и H из layout.dimensions)
python3 scripts/visual-screenshot.py http://localhost:PORT/path /tmp/result.png --width W --height H

# Полная страница (с прокруткой)
python3 scripts/visual-screenshot.py http://localhost:PORT/path /tmp/result.png --full-page

# Скриншот + сразу сравнение с референсом
python3 scripts/visual-screenshot.py http://localhost:PORT/path /tmp/result.png --compare reference.png
```

Viewport задать из `layout.dimensions` референса. Dev-server запустить заранее.

**3.2 Сравнение (отдельно)**

```bash
python3 scripts/visual-analyzer.py <reference.png> /tmp/result.png --compare
```

Выход: процент сходства, отклонения палитры, вердикт.

**Калибровка порога 85%:**
- **92-100%** (excellent) — отличия только в anti-aliasing/субпиксельном рендере. Принять.
- **85-91%** (good) — мелкие отклонения в spacing/шрифтах. Принять, если визуальная инспекция ОК.
- **70-84%** (needs_work) — заметные отличия в цвете/layout. 1-2 итерации.
- **50-69%** — серьёзные расхождения. Проверить: правильный ли viewport? Загрузились ли шрифты/изображения?
- **< 50%** (major) — вероятно неверная страница или viewport. Не итерировать — разобраться в причине.

**3.3 Визуальная инспекция**

Прочитать оба изображения через Read tool. Сравнить:
- [ ] Палитра совпадает (допуск ±5% на каждый цвет)
- [ ] Layout совпадает (колонки, зоны)
- [ ] Spacing паттерн совпадает
- [ ] Ключевые элементы на месте
- [ ] Общее ощущение / стиль

### Phase 4 — Итерация (Iterate)

Если сходство < 85% или визуальная инспекция нашла расхождения:

1. Определить ТОП-3 отклонения (что больше всего отличается)
2. Исправить код
3. Повторить Phase 3
4. Максимум 3 итерации (после 3-й — показать пользователю diff и спросить)

**Decision gate:** similarity ≥ 85% ИЛИ пользователь подтвердил → DONE.

## Quality Checklist

Перед завершением проверить:

- [ ] Все цвета из visual-analyzer (не "на глаз")
- [ ] Layout соответствует анализу (колонки, spacing)
- [ ] **Playwright-скриншоты 390px + 430px + 1440px** — проверены через Read tool
- [ ] На мобиле: текст читается, элементы не наезжают, фото позиционировано правильно
- [ ] Лого не дублируется (hero + navbar)
- [ ] background-position раздельный для mobile/desktop
- [ ] Нет hardcoded px для spacing (использовать Tailwind токены)
- [ ] Скриншот результата сохранён для истории

## Anti-Patterns

1. **Цвета "на глаз"** — ВСЕГДА запускать `visual-analyzer.py`. Человеческое восприятие цвета обманчиво, особенно для серых и нейтральных тонов
2. **Без обратной связи** — ВСЕГДА делать Playwright-скриншот и сравнивать. Код без визуальной проверки = угадывание
3. **Бесконечные итерации** — максимум 3 прохода. Если 3 не хватило — показать пользователю и спросить что важнее
4. **Игнорирование spacing** — spacing важнее цвета. Правильные отступы создают 80% "ощущения" дизайна
5. **Копирование пиксель-в-пиксель** — цель не идентичный скриншот, а визуально неотличимый результат. Разумный допуск = 85%
6. **Забыть про адаптив** — референс обычно один viewport, но код должен работать на всех
7. **Background-size: cover для людей** — cover обрезает непредсказуемо. Для hero с человеком → `auto 100%` + точный `background-position`. Раздельные стили для mobile/desktop
8. **Один background-position для всех viewport** — на мобиле 390px и десктопе 1440px РАЗНЫЕ части изображения попадают в viewport. Всегда 2 div: `hidden sm:block` + `sm:hidden`
9. **Уменьшение клиентского изображения** — если клиент дал hero 1920×1080, НЕ уменьшать (auto 70%, contain). Всегда `auto 100%`, сдвигать position
10. **Отдавать без проверки** — НИКОГДА. После каждого визуального изменения → Playwright-скриншоты 390/430/1440 → Read → проверить → только потом показать
11. **Neo-brutalism для клиентов** — чёрные обводки + offset-тени = "Windows 98". Для клиентских проектов → чистый premium стиль (мягкие тени, скругления, пространство)
12. **Gradient overlay на светлом фоне** — если изображение УЖЕ на белом/светлом фоне, overlay не нужен. Он "засвечивает" содержимое

## Tools & Scripts

| Инструмент | Назначение |
|-----------|------------|
| `scripts/visual-analyzer.py` | Полный анализ: палитра, layout, fonts, gradients, components, radius, shadows, WCAG |
| `scripts/visual-analyzer.py --compare` | Сравнение + diff heatmap + problem zones |
| `scripts/visual-analyzer.py --json` | JSON для программной обработки |
| `scripts/visual-analyzer.py --tokens out.js` | Экспорт design tokens в tailwind.config.js |
| `scripts/visual-analyzer.py --palette N` | Извлечь N цветов (по умолчанию 6) |
| `scripts/visual-screenshot.py` | Скриншот через Playwright (viewport, full-page, auto-compare) |
| Read tool | Мультимодальный анализ изображений |

## Error Handling

- **SVG** — не анализируется как растр. Скрипт предупредит и предложит конвертацию
- **GIF** — анализируется только первый кадр
- **Невалидный файл** — graceful error, exit code 1
- **Playwright недоступен** — fallback: только visual-analyzer + Read tool (без автоскриншотов)
- **Dev-server не запущен** — visual-screenshot.py выдаст ошибку подключения, не зависнет (timeout 15s)

## References

- `references/workflow-example.md` — Пример полного прохода от референса до готового кода
- `references/calibration.md` — Калибровочные примеры для scoring

---

## Changelog

<!-- Сюда автоматически добавляются уроки после каждого использования скилла -->
