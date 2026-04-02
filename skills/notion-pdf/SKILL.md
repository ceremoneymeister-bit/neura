---
name: notion-pdf
description: "Unified Notion-style PDF generator for all bots. Converts Markdown text/files into clean, professional A4 PDFs with Notion aesthetics. Used automatically when bot agent needs to send long structured documents."
version: 1.0.0
author: Dmitry Rostovtsev (ceremoneymeister)
created: 2026-03-20
updated: 2026-03-20
category: infrastructure
tags: [pdf, notion, document, export, markdown, universal]
risk: safe
source: internal
---

# notion-pdf

## Purpose

Единый генератор PDF в стиле Notion для всех ботов экосистемы Neura. Конвертирует Markdown-текст или файлы в чистые, профессиональные A4-документы. Работает на всех серверах и в Docker.

## When to Use

Активируй этот скилл когда:
- Агент создал длинный структурированный ответ (план, отчёт, стратегия, КП, календарь)
- Пользователь просит "сделай PDF", "отправь документом", "экспортируй"
- Нужно отправить красивый документ клиенту или в HQ-группу
- Результат работы > 2000 символов и имеет структуру (заголовки, таблицы, списки)

НЕ используй когда:
- Короткий текстовый ответ (< 2000 символов) — обычное сообщение
- Длинный текст без структуры — используй Telegraph (smart-response скилл)
- Нужна сложная вёрстка с градиентами — используй pdf-generator (WeasyPrint) Максима

## Quick Start

### Из файла
```bash
python3 .agent/skills/notion-pdf/scripts/md2pdf.py \
  --input /path/to/document.md \
  --output /tmp/document.pdf \
  --title "Название документа"
```

### Из stdin (pipe)
```bash
echo "# Заголовок\n\nТекст" | python3 .agent/skills/notion-pdf/scripts/md2pdf.py \
  --output /tmp/document.pdf \
  --title "Название"
```

### Несколько файлов в один PDF (каждый с новой страницы)
```bash
python3 .agent/skills/notion-pdf/scripts/md2pdf.py \
  --input file1.md file2.md file3.md \
  --output /tmp/combined.pdf \
  --title "Сборник документов"
```

### Из Python-кода (для ботов)
```python
from pathlib import Path
import subprocess, json

def generate_notion_pdf(
    markdown_text: str,
    output_path: str = "/tmp/output.pdf",
    title: str = "Document",
    footer: str = "Neura"
) -> str:
    """Generate Notion-style PDF. Returns path to PDF or empty string on error."""
    script = Path(__file__).parent / ".agent/skills/notion-pdf/scripts/md2pdf.py"
    # Fallback: try common locations
    for candidate in [
        Path("/root/Antigravity/.agent/skills/notion-pdf/scripts/md2pdf.py"),
        Path.home() / ".claude/skills/notion-pdf/scripts/md2pdf.py",
    ]:
        if candidate.exists():
            script = candidate
            break

    result = subprocess.run(
        ["python3", str(script), "--output", output_path, "--title", title, "--footer", footer],
        input=markdown_text,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode == 0 and Path(output_path).exists():
        return output_path
    return ""
```

## Стиль PDF

Notion-inspired минимализм:
- **Шрифт:** DejaVu Sans (кириллица-safe, есть на всех Linux)
- **Фон:** белый (#FFFFFF)
- **Текст:** #37352F (тёплый тёмно-серый Notion)
- **Таблицы:** тонкие бордюры #E9E9E7, чередование строк #F7F6F3
- **Заголовки:** жирные, чистые, h1 с нижней линией
- **Blockquotes:** левый бордюр #37352F, фон #F7F6F3
- **Code:** фон #F7F6F3, моноширинный DejaVu Sans Mono
- **Footer:** номер страницы + кастомный текст (по умолчанию "Neura")
- **Размер:** A4, margins 20mm top/bottom, 25mm left/right

## Движок рендеринга (Fallback Chain)

| Приоритет | Движок | Качество | Требования |
|-----------|--------|----------|------------|
| 1 | **wkhtmltopdf** | ★★★★★ | `apt install wkhtmltopdf` |
| 2 | **WeasyPrint** | ★★★★★ | `pip install weasyprint` + cairo/pango |
| 3 | **fpdf2** | ★★★☆☆ | `pip install fpdf2` (zero deps) |

Скрипт автоматически определяет доступный движок. fpdf2 всегда доступен как fallback — он не рендерит CSS, но корректно выводит текст, таблицы и заголовки.

## Установка на новый сервер / в Docker

### Сервер (Ubuntu/Debian)
```bash
apt-get install -y wkhtmltopdf fonts-dejavu-core
pip install markdown fpdf2
```

### Docker (добавить в Dockerfile)
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    wkhtmltopdf fonts-dejavu-core xvfb \
    && pip install markdown fpdf2 \
    && rm -rf /var/lib/apt/lists/*
```

### Минимальная установка (только fpdf2, без wkhtmltopdf)
```bash
pip install fpdf2
```

## Интеграция с ботами

### Инструкция для CLAUDE.md бота
Добавить в системный промпт каждого бота:

```
### 📄 Документы → Notion PDF (НЕУДАЛЯЕМОЕ)
Когда создаёшь длинный структурированный документ (план, отчёт, КП, календарь):
1. Напиши содержимое в Markdown
2. Сохрани в /tmp/document.md
3. Сгенерируй PDF:
   python3 /root/Antigravity/.agent/skills/notion-pdf/scripts/md2pdf.py \
     --input /tmp/document.md --output /tmp/document.pdf --title "Название"
4. Добавь маркер: [FILE:/tmp/document.pdf]
Бот автоматически отправит PDF пользователю.
```

### Для Docker-ботов (Юлия)
Путь к скрипту внутри контейнера должен быть смонтирован или скопирован:
```yaml
volumes:
  - /root/Antigravity/.agent/skills/notion-pdf/scripts:/app/skills/notion-pdf:ro
```

Или скопировать скрипт при сборке:
```dockerfile
COPY .agent/skills/notion-pdf/scripts/md2pdf.py /app/skills/md2pdf.py
```

## Параметры CLI

| Параметр | Описание | По умолчанию |
|----------|----------|-------------|
| `--input` | Путь к .md файлу (можно несколько) | stdin |
| `--output` | Путь к выходному .pdf | `/tmp/output.pdf` |
| `--title` | Заголовок документа (header) | Имя входного файла |
| `--footer` | Текст в футере | `Neura` |
| `--engine` | Принудительный движок: `wkhtmltopdf`, `weasyprint`, `fpdf2` | auto |
| `--no-footer` | Убрать футер | false |
| `--page-break` | Разрыв страницы между файлами при --input с несколькими файлами | true |

## Anti-Patterns

- **НЕ** используй для генерации изображений или сложной графики
- **НЕ** хардкодь пути к шрифтам — скрипт сам находит DejaVu
- **НЕ** генерируй PDF для текста < 500 символов — это пустая трата
- **НЕ** забывай маркер `[FILE:/tmp/path.pdf]` в ответе бота
- **НЕ** используй вместо Telegraph для обычных длинных текстовых ответов

## Совместимость со скиллами

| Скилл | Взаимодействие |
|-------|---------------|
| smart-response | Текст > 4000 символов → Telegraph. Структурированный документ → notion-pdf |
| word-docx | Для Word-документов. PDF → notion-pdf |
| excel-xlsx | Для таблиц Excel. Отчёты → notion-pdf |
| ppt-generator | Для презентаций. Документы → notion-pdf |
| release-notes | Release notes могут использовать notion-pdf для красивых апдейтов |

## Уроки из практики

### 2026-03-20 — Первое использование
- wkhtmltopdf отлично рендерит кириллицу с DejaVu Sans
- Markdown-таблицы корректно конвертируются через `markdown` библиотеку с расширением `tables`
- Для объединения нескольких файлов page-break через CSS `page-break-before: always` работает
- Размер PDF: ~10-12 KB на страницу текста, таблицы увеличивают на ~2-3 KB
