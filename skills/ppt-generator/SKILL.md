---
name: ppt-generator
description: "Use when creating PowerPoint presentations (.pptx) — презентации, слайды, 'создай презентацию', 'сделай PPT', 'PowerPoint', питч-дек, отчёт в слайдах"
---

# PPT Generator — создание презентаций

## Обзор
Генерация .pptx презентаций через `python-pptx`. Поддержка шаблонов, графиков, изображений, таблиц.

## Библиотека
```bash
pip install python-pptx
```

## Быстрый старт

```python
from pptx import Presentation
from pptx.util import Inches, Pt, Cm, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.chart import XL_CHART_TYPE

prs = Presentation()
prs.slide_width = Inches(16)  # Широкоформатный 16:9
prs.slide_height = Inches(9)

# Титульный слайд
slide_layout = prs.slide_layouts[0]  # Title Slide
slide = prs.slides.add_slide(slide_layout)
slide.shapes.title.text = "Заголовок презентации"
slide.placeholders[1].text = "Подзаголовок"

prs.save('/tmp/presentation.pptx')
```

## Макеты слайдов (Slide Layouts)

| Индекс | Название | Использование |
|--------|----------|--------------|
| 0 | Title Slide | Титульный |
| 1 | Title and Content | Заголовок + контент |
| 2 | Section Header | Разделитель секции |
| 3 | Two Content | Два блока |
| 4 | Comparison | Сравнение |
| 5 | Title Only | Только заголовок |
| 6 | Blank | Пустой (для кастомного дизайна) |

## Основные операции

### Текст с форматированием
```python
from pptx.util import Pt
from pptx.dml.color import RGBColor

slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank

txBox = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(8), Inches(2))
tf = txBox.text_frame
tf.word_wrap = True

p = tf.paragraphs[0]
p.text = "Основной текст"
p.font.size = Pt(24)
p.font.bold = True
p.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
p.alignment = PP_ALIGN.LEFT

# Новый параграф
p2 = tf.add_paragraph()
p2.text = "Подтекст"
p2.font.size = Pt(16)
p2.font.color.rgb = RGBColor(0x66, 0x66, 0x66)
```

### Изображения
```python
slide.shapes.add_picture(
    '/path/to/image.png',
    left=Inches(1),
    top=Inches(2),
    width=Inches(5)
    # height рассчитается автоматически
)
```

### Таблицы
```python
rows, cols = 4, 3
table_shape = slide.shapes.add_table(rows, cols, Inches(1), Inches(2), Inches(8), Inches(3))
table = table_shape.table

# Заголовки
for i, header in enumerate(['Услуга', 'Цена', 'Срок']):
    cell = table.cell(0, i)
    cell.text = header
    cell.fill.solid()
    cell.fill.fore_color.rgb = RGBColor(0x33, 0x33, 0x33)
    for paragraph in cell.text_frame.paragraphs:
        paragraph.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        paragraph.font.bold = True

# Данные
table.cell(1, 0).text = 'AI-агент'
table.cell(1, 1).text = '80 000 ₽'
table.cell(1, 2).text = '2 недели'
```

### Графики
```python
from pptx.chart.data import CategoryChartData

chart_data = CategoryChartData()
chart_data.categories = ['Янв', 'Фев', 'Мар']
chart_data.add_series('Доход', (100000, 150000, 200000))
chart_data.add_series('Расход', (80000, 90000, 110000))

chart = slide.shapes.add_chart(
    XL_CHART_TYPE.COLUMN_CLUSTERED,
    Inches(1), Inches(2), Inches(8), Inches(4),
    chart_data
).chart

chart.has_legend = True
chart.legend.include_in_layout = False
```

### Фигуры
```python
from pptx.enum.shapes import MSO_SHAPE

shape = slide.shapes.add_shape(
    MSO_SHAPE.ROUNDED_RECTANGLE,
    Inches(1), Inches(1), Inches(3), Inches(1.5)
)
shape.fill.solid()
shape.fill.fore_color.rgb = RGBColor(0x00, 0x7A, 0xFF)
shape.text = "Блок текста"
shape.text_frame.paragraphs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
```

### Фон слайда
```python
# Сплошной цвет
background = slide.background
fill = background.fill
fill.solid()
fill.fore_color.rgb = RGBColor(0x0D, 0x0D, 0x0D)

# Изображение как фон
from pptx.oxml.ns import qn
slide.background.fill.background()  # use image fill method
```

## Шаблоны презентаций

### Питч-дек (10 слайдов)
1. Титульный (название + подзаголовок)
2. Проблема (боль клиента)
3. Решение (наш продукт)
4. Как это работает (3 шага)
5. Результаты/кейсы (цифры)
6. Рынок (TAM/SAM/SOM)
7. Бизнес-модель (тарифы)
8. Команда
9. Roadmap (план)
10. CTA (контакты + призыв)

### Отчёт клиенту
1. Титул
2. Что сделано (список)
3. Метрики (графики)
4. Скриншоты/примеры
5. Следующие шаги
6. Контакты

## Стилевые пресеты

### Neo-Brutalist (наш стиль)
```python
BG_COLOR = RGBColor(0x0D, 0x0D, 0x0D)      # Почти чёрный
TEXT_COLOR = RGBColor(0xF5, 0xF5, 0xF5)      # Почти белый
ACCENT_COLOR = RGBColor(0x00, 0xFF, 0x88)    # Зелёный акцент
HEADING_FONT = 'Inter'
BODY_FONT = 'Inter'
```

### Corporate
```python
BG_COLOR = RGBColor(0xFF, 0xFF, 0xFF)
TEXT_COLOR = RGBColor(0x33, 0x33, 0x33)
ACCENT_COLOR = RGBColor(0x00, 0x7A, 0xFF)
```

## Работа с шаблоном
```python
# Открыть шаблон .pptx
prs = Presentation('/path/to/template.pptx')

# Использовать макеты из шаблона
slide_layout = prs.slide_layouts[0]
slide = prs.slides.add_slide(slide_layout)

# Заменить placeholder
for ph in slide.placeholders:
    print(f"idx={ph.placeholder_format.idx}, name={ph.name}")
    if ph.placeholder_format.idx == 0:
        ph.text = "Новый заголовок"
```

## CLI-скрипт
```bash
python3 scripts/ppt-create.py --title "Neura — AI-агенты" \
    --template pitch-deck \
    --style neo-brutalist \
    --output /tmp/neura-pitch.pptx
```

## Частые ошибки

| Ошибка | Решение |
|--------|---------|
| Кириллица не отображается | Задай шрифт явно: `p.font.name = 'Arial'` |
| Слайд пустой | Проверь slide_layout — не все имеют placeholders |
| Картинка растянута | Задавай только width ИЛИ только height |
| Текст обрезается | `text_frame.word_wrap = True` + увеличь textbox |
| Шрифт не установлен | Используй системные: Arial, Calibri, Times New Roman |

## Интеграция с ботами
```
[FILE:/tmp/presentation.pptx]
```

## Google Slides
Для онлайн-презентаций: загрузить .pptx на Google Drive → откроется в Slides.
Или использовать Google Slides API напрямую (отдельный MCP-сервер, не подключён пока).
