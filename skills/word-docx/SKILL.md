---
name: word-docx
description: "Use when creating or editing Word documents (.docx) — КП, договоры, отчёты, документы, 'создай документ', 'сделай Word', 'docx'"
---

# Word / DOCX — работа с документами

## Обзор
Создание и редактирование .docx файлов через `python-docx`. DOCX = OOXML (ZIP-архив XML-частей).

## Библиотека
```bash
pip install python-docx
```

## Быстрый старт

```python
from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

doc = Document()

# Заголовок
doc.add_heading('Заголовок документа', level=0)

# Параграф с форматированием
p = doc.add_paragraph()
run = p.add_run('Жирный текст')
run.bold = True
run.font.size = Pt(14)
run.font.color.rgb = RGBColor(0x00, 0x00, 0x00)

# Список
doc.add_paragraph('Пункт 1', style='List Bullet')
doc.add_paragraph('Пункт 2', style='List Bullet')

# Таблица
table = doc.add_table(rows=2, cols=3, style='Table Grid')
table.cell(0, 0).text = 'Колонка 1'

# Изображение
doc.add_picture('/path/to/image.png', width=Inches(4))

# Сохранение
doc.save('/tmp/document.docx')
```

## Ключевые правила

### Структура DOCX
- `word/document.xml` — основной контент
- `word/styles.xml` — стили
- `word/numbering.xml` — нумерация списков
- Текст может быть разбит на несколько runs внутри параграфа

### Стили
- **Используй именованные стили** (`Heading 1`, `List Bullet`, `Normal`) вместо прямого форматирования
- Это сохраняет редактируемость в Word/LibreOffice
- Создание кастомного стиля:
```python
from docx.enum.style import WD_STYLE_TYPE
style = doc.styles.add_style('CustomStyle', WD_STYLE_TYPE.PARAGRAPH)
style.font.size = Pt(12)
style.font.bold = True
```

### Списки
- Нумерация живёт в `abstractNum`/`num` определениях, НЕ в Unicode символах
- Используй стили `List Bullet`, `List Number`
- Для вложенных: `List Bullet 2`, `List Number 2`

### Таблицы
```python
# Ширина колонок
from docx.shared import Cm
table = doc.add_table(rows=1, cols=3, style='Table Grid')
table.columns[0].width = Cm(3)
table.columns[1].width = Cm(5)
table.columns[2].width = Cm(4)

# Объединение ячеек
table.cell(0, 0).merge(table.cell(0, 1))

# Выравнивание таблицы
table.alignment = WD_TABLE_ALIGNMENT.CENTER
```

### Колонтитулы
```python
section = doc.sections[0]
header = section.header
header.paragraphs[0].text = 'Шапка документа'

footer = section.footer
footer.paragraphs[0].text = 'Страница'
```

### Поля страницы
```python
from docx.shared import Cm
section = doc.sections[0]
section.top_margin = Cm(2)
section.bottom_margin = Cm(2)
section.left_margin = Cm(2.5)
section.right_margin = Cm(1.5)
```

## Редактирование существующего документа
```python
doc = Document('/path/to/existing.docx')

# Найти и заменить текст
for paragraph in doc.paragraphs:
    if 'OLD_TEXT' in paragraph.text:
        for run in paragraph.runs:
            run.text = run.text.replace('OLD_TEXT', 'NEW_TEXT')

doc.save('/path/to/modified.docx')
```

## Частые ошибки

| Ошибка | Решение |
|--------|---------|
| Текст разбит на runs | Итерировать `paragraph.runs`, не `paragraph.text` при замене |
| Стили не применяются | Проверь что стиль существует: `doc.styles` |
| Таблица «плывёт» | Задавай явные ширины колонок в Cm/Inches |
| Кириллица ломается | python-docx поддерживает Unicode, проблема в шрифте |
| Формат не сохраняется в LibreOffice | Используй именованные стили, не прямое форматирование |

## Шаблоны документов

### КП (Коммерческое предложение)
```python
doc = Document()
doc.add_heading('Коммерческое предложение', 0)
doc.add_paragraph(f'Дата: {date}')
doc.add_heading('О компании', level=1)
doc.add_paragraph('...')
doc.add_heading('Услуги и стоимость', level=1)
# Таблица с тарифами
doc.add_heading('Контакты', level=1)
doc.save(f'/tmp/КП_{client_name}.docx')
```

### Договор
```python
doc = Document()
doc.add_heading('ДОГОВОР №___', 0)
doc.add_paragraph(f'г. Москва, {date}')
doc.add_heading('1. Предмет договора', level=1)
# ...секции договора
doc.save(f'/tmp/Договор_{client_name}.docx')
```

## Интеграция с ботами
Сгенерированный .docx можно отправить через Telegram бот:
```
[FILE:/tmp/document.docx]
```

## Когда НЕ использовать
- Простой текст → .txt или Markdown
- Нужна вёрстка/дизайн → PDF через weasyprint
- Совместное редактирование → Google Docs
- Таблицы с формулами → Excel/Google Sheets
