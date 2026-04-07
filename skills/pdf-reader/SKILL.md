---
name: pdf-reader
description: Чтение и анализ PDF файлов любого размера. Автоматическое определение страниц, постраничное чтение, summary, извлечение данных. Для всех капсул.
version: 1.0.0
author: Dmitry Rostovtsev (ceremoneymeister)
created: 2026-04-06
category: infrastructure
tags: [pdf, reader, analysis, document, extract, summary, universal]
risk: safe
source: crystallized
proactive_enabled: true
proactive_trigger_1_type: event
proactive_trigger_1_condition: пользователь прикрепил PDF файл
proactive_trigger_1_action: автоматически определить размер и начать чтение
proactive_trigger_2_type: event
proactive_trigger_2_condition: запрос 'прочитай PDF', 'изучи документ', 'что в файле
proactive_trigger_2_action: полный цикл: разведка → чтение → summary
learning_track_success: true
learning_track_corrections: true
learning_evolve_threshold: 5
learning_auto_update: [anti-patterns, triggers, changelog]
usage_count: 1
last_used: 2026-04-06
maturity: seed
---

# pdf-reader

## Purpose

Полноценное чтение и анализ PDF файлов любого размера (от 1 до 500+ страниц). Работает в капсулах (TG-боты) и на web-платформе. Автоматически определяет количество страниц, читает порциями, строит summary.

## When to Use

| Триггер | Пример |
|---------|--------|
| Пользователь прикрепил PDF | Файл загружен через TG или web-платформу |
| Запрос на чтение документа | "прочитай этот PDF", "что в документе", "изучи файл" |
| Запрос на извлечение данных | "найди в PDF все цены", "выдели ключевые тезисы" |
| Запрос на summary | "кратко о чём документ", "основные выводы" |
| Запрос на перевод/переработку | "перескажи PDF по-русски", "сделай конспект" |

НЕ используй когда:
- Файл не PDF (используй Read tool напрямую для .txt, .md, .csv)
- Нужно СОЗДАТЬ PDF (используй скилл `notion-pdf` или `pdf-generator`)
- Файл — изображение (используй Read tool напрямую, он поддерживает PNG/JPG)

## Workflow

### Phase 1: Разведка (обязательно)

```
1. Определить путь к файлу
2. Узнать размер: python3 -c "import os; print(f'{os.path.getsize(\"PATH\") / 1024 / 1024:.1f} МБ')"
3. Определить кол-во страниц:
   python3 -c "
   import subprocess
   r = subprocess.run(['python3', '-c', '''
   try:
       import fitz  # PyMuPDF
       doc = fitz.open(\"PATH\")
       print(f'pages:{doc.page_count}')
       print(f'title:{doc.metadata.get(\"title\", \"\")}')
       print(f'author:{doc.metadata.get(\"author\", \"\")}')
       doc.close()
   except ImportError:
       # Fallback: pdfinfo
       import subprocess as sp
       r = sp.run(['pdfinfo', 'PATH'], capture_output=True, text=True)
       for line in r.stdout.splitlines():
           if line.startswith('Pages:'):
               print(f'pages:{line.split(\":\")[1].strip()}')
   '''], capture_output=True, text=True)
   print(r.stdout)
   "
4. Прочитать первые 3 страницы для оценки структуры:
   Read tool: file_path="PATH", pages="1-3"
```

### Phase 2: Стратегия чтения

На основе Phase 1 выбрать стратегию:

| Размер PDF | Стратегия |
|-----------|-----------|
| **1-10 страниц** | Прочитать целиком: `pages="1-10"` (один вызов Read) |
| **11-50 страниц** | Порции по 15-20 страниц: `1-20`, `21-40`, `41-50` |
| **51-200 страниц** | Оглавление + ключевые разделы. Спросить пользователя что именно нужно |
| **200+ страниц** | ТОЛЬКО целевой поиск. Оглавление → конкретные страницы по запросу |

### Phase 3: Чтение

```
Для каждой порции:
1. Read tool: file_path="PATH", pages="X-Y"
2. Извлечь ключевые данные
3. Если пользователь ищет что-то конкретное — проверить нашлось ли
4. Max 20 страниц за один вызов Read (ограничение инструмента)
```

### Phase 4: Результат

Формат ответа зависит от запроса:

**Summary (по умолчанию):**
```
📄 **{название документа}** ({N} стр., {размер})

**О чём:** {1-2 предложения}

**Ключевые разделы:**
1. {раздел} (стр. X-Y) — {суть}
2. {раздел} (стр. X-Y) — {суть}
...

**Основные выводы:**
- {вывод 1}
- {вывод 2}
- {вывод 3}

💡 Хотите подробнее о каком-то разделе?
```

**Извлечение данных:**
```
📊 Извлечено из {название} (стр. X-Y):

{таблица / список / структурированные данные}
```

**Полный конспект (для длинных документов):**
- Если конспект > 4000 символов → использовать скилл `smart-response` (Telegraph)
- Если нужен PDF-конспект → использовать скилл `notion-pdf`

## Антипаттерны

1. **НЕ читать весь PDF если > 50 страниц** без уточнения у пользователя. Спросить: "Документ {N} страниц. Прочитать целиком или есть конкретный вопрос?"
2. **НЕ вызывать Read без параметра pages для PDF > 10 стр.** — вернёт ошибку
3. **НЕ отправлять весь текст PDF пользователю** — делать summary, не copy-paste
4. **НЕ пропускать Phase 1** — без разведки можно выбрать неправильную стратегию
5. **НЕ читать 200+ страниц подряд** — контекст переполнится, качество упадёт

## Зависимости

- **Read tool** — основной инструмент (встроен в Claude Code)
- **python3** — для определения кол-ва страниц (PyMuPDF или pdfinfo)
- **smart-response** — для длинных конспектов (> 4000 символов)
- **notion-pdf** — если нужно создать PDF-конспект

## Установка PyMuPDF (если не установлен)

```bash
pip install PyMuPDF
```

Fallback: если PyMuPDF нет, используется `pdfinfo` (из poppler-utils):
```bash
apt-get install -y poppler-utils
```

## Интеграция с web-платформой

Файлы загруженные через web-платформу сохраняются в `/tmp/neura-uploads/`.
В prompt агента автоматически добавляется:
```
[PDF: document.pdf, 45.2 МБ] — ОБЯЗАТЕЛЬНО прочитай через Read tool с параметром pages.
  Путь: /tmp/neura-uploads/abc_document.pdf
```

## Интеграция с Telegram

Файлы из TG сохраняются во временную директорию капсулы.
Агент получает путь через `[FILE_RECEIVED: /path/to/file.pdf]` маркер.

## Document Intelligence (Фаза A)

С 2026-04-06 на платформе работает модуль `document_processor.py`:
- **Путь:** `/opt/neura-v2/neura/core/document_processor.py`
- **Что делает:** автоматический анализ PDF при загрузке (PyMuPDF)
- **Результат:** агент получает в промпте: тип документа, страницы, оглавление, стратегию
- **Агенту НЕ нужно** самому считать страницы — информация уже в промпте

### Как это меняет workflow
- Phase 1 (разведка) теперь частично автоматизирована — тип и размер уже известны
- Агент должен следовать стратегии из промпта, а не определять сам
- Для юр.документов автоматическое предупреждение "не замена юристу"

## Changelog

### 2026-04-06 — Document Intelligence (Фаза A)
- Создан `document_processor.py`: analyze_document() + build_file_context()
- Обновлён web.py: промпт-инъекция через document_processor вместо inline
- 13 капсул + эталон: добавлена секция "Работа с документами" в CLAUDE.md
- Детекция типов: contract, report, invoice, article, unknown
- TOC extraction: PyMuPDF get_toc() + regex fallback
- Scan detection: < 50 символов/страница → предупреждение
- Стратегия автоматическая по размеру: full_read/chunked/targeted/question_only

### 2026-04-06 — Создание скилла
- Причина: PDF файлы загружаются на платформу, но агент не знает как их правильно читать порциями
- Стратегия чтения по размеру: 1-10 целиком, 11-50 порциями, 50+ целевой поиск
- Антипаттерн: Read без pages для больших PDF = ошибка
