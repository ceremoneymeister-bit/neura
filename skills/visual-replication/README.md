# visual-replication

Скилл для точного воспроизведения визуального дизайна из референсных изображений в код.

## Что делает

1. **Извлекает** точные цвета, layout, spacing из скриншота через `visual-analyzer.py`
2. **Реализует** дизайн в React + Tailwind с цветами из анализа (не "на глаз")
3. **Верифицирует** результат через Playwright-скриншот + автосравнение
4. **Итерирует** до 85%+ сходства с референсом

## Файлы

```
visual-replication/
├── SKILL.md                          # Основной workflow
├── README.md                         # Этот файл
└── references/
    └── workflow-example.md           # Пример полного прохода

scripts/
└── visual-analyzer.py                # Анализатор изображений (Pillow + OpenCV)
```

## Быстрый старт

```bash
# Анализ референса
python3 scripts/visual-analyzer.py screenshot.png

# JSON для парсинга
python3 scripts/visual-analyzer.py screenshot.png --json

# Сравнение результата с референсом
python3 scripts/visual-analyzer.py reference.png result.png --compare
```

## Триггеры

"Сделай как на картинке", "повтори дизайн", "pixel-perfect", "по макету", "по референсу", "сверстай по скриншоту"
