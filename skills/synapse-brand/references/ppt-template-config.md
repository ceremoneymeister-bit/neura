# Synapse — конфигурация PPT-шаблона

> Использовать совместно со скиллом `ppt-generator` (python-pptx).
> Формат: 16:9, широкоформатный.

---

## Python-конфиг

```python
from pptx.util import Inches, Pt, Cm, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

SYNAPSE_PPT_CONFIG = {
    # === Цвета (RGBColor) ===
    "lime":         RGBColor(0xCC, 0xFF, 0x00),  # #CCFF00 — основной акцент
    "lime_hover":   RGBColor(0xB3, 0xE6, 0x00),  # #B3E600 — ховер
    "black":        RGBColor(0x00, 0x00, 0x00),  # #000000 — фон, текст
    "white":        RGBColor(0xFF, 0xFF, 0xFF),  # #FFFFFF — текст на тёмном
    "purple":       RGBColor(0x5D, 0x3F, 0xD3),  # #5D3FD3 — вторичный акцент
    "grey_light":   RGBColor(0xF5, 0xF5, 0xF5),  # #F5F5F5 — фон карточек
    "grey_dark":    RGBColor(0x11, 0x11, 0x11),  # #111111 — тёмные секции
    "text_muted":   RGBColor(0x99, 0x99, 0x99),  # #999999 — приглушённый текст

    # === Шрифты ===
    "font_heading": "Space Grotesk",
    "font_body":    "Inter",
    "font_accent":  "Unbounded",

    # === Размеры текста (Pt) ===
    "size_title":       Pt(44),    # Заголовок титульного слайда
    "size_subtitle":    Pt(22),    # Подзаголовок
    "size_section":     Pt(40),    # Заголовок секции
    "size_slide_title": Pt(32),    # Заголовок обычного слайда
    "size_body":        Pt(18),    # Основной текст
    "size_body_sm":     Pt(14),    # Мелкий текст
    "size_caption":     Pt(12),    # Подписи
    "size_number":      Pt(64),    # Крупные числа/статистика
    "size_logo":        Pt(16),    # Логотип в углу

    # === Слайд ===
    "slide_width":  Inches(16),    # 16:9
    "slide_height": Inches(9),

    # === Отступы ===
    "margin_left":   Inches(1.0),
    "margin_right":  Inches(1.0),
    "margin_top":    Inches(0.8),
    "margin_bottom": Inches(0.6),

    # === Логотип ===
    "logo_text":      "SYNAPSE",
    "logo_highlight": "APSE",      # Lime часть
    "logo_font":      "Unbounded",
    "logo_weight":    True,        # Bold
}
```

---

## Вспомогательные функции

```python
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
import copy

C = SYNAPSE_PPT_CONFIG


def create_synapse_presentation():
    """Создаёт пустую презентацию с настройками Synapse."""
    prs = Presentation()
    prs.slide_width = C["slide_width"]
    prs.slide_height = C["slide_height"]
    return prs


def add_background(slide, color=None):
    """Устанавливает цвет фона слайда."""
    if color is None:
        color = C["black"]
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_neo_shadow(shape, offset_x=Emu(57150), offset_y=Emu(57150)):
    """
    Добавляет жёсткую neo-brutalist тень к фигуре.
    57150 EMU ~ 4px при 96 DPI.
    """
    shadow_xml = (
        f'<a:effectLst xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        f'  <a:outerShdw dist="{int((offset_x**2 + offset_y**2)**0.5)}" '
        f'    dir="2700000" blurRad="0" algn="tl" rotWithShape="0">'
        f'    <a:srgbClr val="000000"/>'
        f'  </a:outerShdw>'
        f'</a:effectLst>'
    )
    # Альтернативный подход — прямой XML
    sp = shape._element
    spPr = sp.find(qn('a:spPr')) or sp.find(qn('p:spPr'))
    if spPr is None:
        return
    from lxml import etree
    effect = etree.fromstring(shadow_xml)
    spPr.append(effect)


def add_textbox(slide, left, top, width, height, text, font_name=None,
                font_size=None, font_color=None, bold=False, alignment=PP_ALIGN.LEFT):
    """Добавляет текстовый блок с настройками Synapse."""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.name = font_name or C["font_body"]
    p.font.size = font_size or C["size_body"]
    p.font.color.rgb = font_color or C["white"]
    p.font.bold = bold
    p.alignment = alignment
    return txBox


def add_neo_card(slide, left, top, width, height, fill_color=None):
    """Добавляет neo-brutalist карточку (прямоугольник с рамкой)."""
    from pptx.enum.shapes import MSO_SHAPE
    # Тень (смещённый чёрный прямоугольник за основной карточкой)
    shadow = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        left + Emu(57150), top + Emu(57150), width, height
    )
    shadow.fill.solid()
    shadow.fill.fore_color.rgb = C["black"]
    shadow.line.fill.background()
    # Устанавливаем малый радиус
    shadow_adj = shadow._element.find(qn('a:prstGeom'))

    # Основная карточка
    card = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        left, top, width, height
    )
    card.fill.solid()
    card.fill.fore_color.rgb = fill_color or C["grey_light"]
    card.line.color.rgb = C["black"]
    card.line.width = Pt(2)

    return card


def add_logo(slide, position="bottom-right"):
    """Добавляет текстовый логотип SYN|APSE в угол слайда."""
    positions = {
        "bottom-right": (Inches(13.0), Inches(8.2)),
        "bottom-left":  (Inches(0.8),  Inches(8.2)),
        "top-right":    (Inches(13.0), Inches(0.3)),
        "top-left":     (Inches(0.8),  Inches(0.3)),
    }
    left, top = positions.get(position, positions["bottom-right"])

    txBox = slide.shapes.add_textbox(left, top, Inches(2.5), Inches(0.5))
    tf = txBox.text_frame
    tf.word_wrap = False

    p = tf.paragraphs[0]

    # SYN — белый
    run1 = p.add_run()
    run1.text = "SYN"
    run1.font.name = C["logo_font"]
    run1.font.size = C["size_logo"]
    run1.font.bold = True
    run1.font.color.rgb = C["white"]

    # APSE — lime
    run2 = p.add_run()
    run2.text = "APSE"
    run2.font.name = C["logo_font"]
    run2.font.size = C["size_logo"]
    run2.font.bold = True
    run2.font.color.rgb = C["lime"]

    return txBox
```

---

## Шаблоны слайдов

### Титульный слайд (чёрный фон)

```python
def slide_title(prs, title, subtitle=""):
    """Титульный слайд: чёрный фон, lime заголовок, белый подзаголовок."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank
    add_background(slide, C["black"])

    # Заголовок
    add_textbox(
        slide,
        left=C["margin_left"], top=Inches(2.5),
        width=Inches(14), height=Inches(3),
        text=title,
        font_name=C["font_heading"],
        font_size=C["size_title"],
        font_color=C["lime"],
        bold=True,
        alignment=PP_ALIGN.LEFT,
    )

    # Подзаголовок
    if subtitle:
        add_textbox(
            slide,
            left=C["margin_left"], top=Inches(5.5),
            width=Inches(12), height=Inches(1.5),
            text=subtitle,
            font_name=C["font_body"],
            font_size=C["size_subtitle"],
            font_color=C["white"],
            bold=False,
            alignment=PP_ALIGN.LEFT,
        )

    # Логотип
    add_logo(slide, "bottom-right")

    return slide
```

### Слайд с контентом (белый фон)

```python
def slide_content(prs, title, bullets):
    """Контентный слайд: белый фон, чёрный заголовок, маркированный список."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank
    add_background(slide, C["white"])

    # Lime полоска сверху (декоративная)
    from pptx.enum.shapes import MSO_SHAPE
    bar = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0), Inches(0), Inches(16), Inches(0.08)
    )
    bar.fill.solid()
    bar.fill.fore_color.rgb = C["lime"]
    bar.line.fill.background()

    # Заголовок
    add_textbox(
        slide,
        left=C["margin_left"], top=Inches(0.8),
        width=Inches(14), height=Inches(1.2),
        text=title,
        font_name=C["font_heading"],
        font_size=C["size_slide_title"],
        font_color=C["black"],
        bold=True,
    )

    # Список
    txBox = slide.shapes.add_textbox(
        C["margin_left"], Inches(2.2), Inches(13), Inches(5.5)
    )
    tf = txBox.text_frame
    tf.word_wrap = True

    for i, bullet in enumerate(bullets):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = f"→  {bullet}"
        p.font.name = C["font_body"]
        p.font.size = C["size_body"]
        p.font.color.rgb = C["black"]
        p.space_after = Pt(12)

    # Логотип
    add_logo(slide, "bottom-right")

    return slide
```

### Слайд-разделитель секции

```python
def slide_section(prs, section_title, section_number=None):
    """Разделитель секции: чёрный фон, крупный lime-текст."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank
    add_background(slide, C["black"])

    # Номер секции (опционально)
    if section_number is not None:
        add_textbox(
            slide,
            left=C["margin_left"], top=Inches(2.0),
            width=Inches(3), height=Inches(2),
            text=f"{section_number:02d}",
            font_name=C["font_accent"],
            font_size=C["size_number"],
            font_color=C["purple"],
            bold=True,
        )

    # Текст секции
    title_top = Inches(3.0) if section_number else Inches(3.5)
    add_textbox(
        slide,
        left=C["margin_left"], top=title_top,
        width=Inches(14), height=Inches(2),
        text=section_title,
        font_name=C["font_heading"],
        font_size=C["size_section"],
        font_color=C["lime"],
        bold=True,
    )

    # Логотип
    add_logo(slide, "bottom-right")

    return slide
```

### Слайд со статистикой (3 числа)

```python
def slide_stats(prs, stats):
    """
    Слайд со статистикой: 3 карточки с числами.
    stats = [("9–14", "лет"), ("4", "проекта/мес"), ("90", "минут")]
    """
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank
    add_background(slide, C["grey_dark"])

    card_width = Inches(4)
    card_height = Inches(4)
    gap = Inches(0.8)
    total_width = 3 * card_width.inches + 2 * gap.inches
    start_x = (16 - total_width) / 2

    for i, (number, label) in enumerate(stats[:3]):
        x = Inches(start_x + i * (card_width.inches + gap.inches))
        y = Inches(2.5)

        # Карточка
        card = add_neo_card(slide, x, y, card_width, card_height, C["white"])

        # Число
        add_textbox(
            slide,
            left=x + Inches(0.3), top=y + Inches(0.5),
            width=Inches(3.4), height=Inches(2),
            text=str(number),
            font_name=C["font_accent"],
            font_size=C["size_number"],
            font_color=C["lime"],
            bold=True,
            alignment=PP_ALIGN.CENTER,
        )

        # Подпись
        add_textbox(
            slide,
            left=x + Inches(0.3), top=y + Inches(2.5),
            width=Inches(3.4), height=Inches(1),
            text=label,
            font_name=C["font_body"],
            font_size=C["size_body"],
            font_color=C["black"],
            bold=False,
            alignment=PP_ALIGN.CENTER,
        )

    # Логотип
    add_logo(slide, "bottom-right")

    return slide
```

### Финальный слайд (CTA)

```python
def slide_final(prs, cta_text="Запишись на пробное занятие", contact=""):
    """Финальный слайд: lime CTA на чёрном фоне."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank
    add_background(slide, C["black"])

    # CTA-текст
    add_textbox(
        slide,
        left=Inches(1), top=Inches(2.5),
        width=Inches(14), height=Inches(2),
        text=cta_text,
        font_name=C["font_heading"],
        font_size=C["size_section"],
        font_color=C["lime"],
        bold=True,
        alignment=PP_ALIGN.CENTER,
    )

    # Контакт
    if contact:
        add_textbox(
            slide,
            left=Inches(1), top=Inches(5.5),
            width=Inches(14), height=Inches(1),
            text=contact,
            font_name=C["font_body"],
            font_size=C["size_subtitle"],
            font_color=C["white"],
            bold=False,
            alignment=PP_ALIGN.CENTER,
        )

    # Логотип по центру внизу
    txBox = slide.shapes.add_textbox(Inches(6), Inches(7.5), Inches(4), Inches(0.6))
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER

    run1 = p.add_run()
    run1.text = "SYN"
    run1.font.name = C["logo_font"]
    run1.font.size = Pt(24)
    run1.font.bold = True
    run1.font.color.rgb = C["white"]

    run2 = p.add_run()
    run2.text = "APSE"
    run2.font.name = C["logo_font"]
    run2.font.size = Pt(24)
    run2.font.bold = True
    run2.font.color.rgb = C["lime"]

    return slide
```

---

## Полный пример: генерация презентации

```python
# === Генерация презентации Synapse ===

prs = create_synapse_presentation()

# 1. Титульный
slide_title(prs,
    title="SYNAPSE",
    subtitle="Школа AI-мышления для детей 9–14 лет"
)

# 2. Проблема
slide_section(prs, "Почему это важно", section_number=1)

slide_content(prs,
    title="AI уже здесь",
    bullets=[
        "87% профессий изменятся из-за AI к 2030 году",
        "Дети скроллят нейросети, но не умеют ими ДУМАТЬ",
        "Школа не учит AI-мышлению — мы учим",
        "4 проекта за первый месяц — конкретный результат",
    ]
)

# 3. Статистика
slide_stats(prs, [
    ("9–14", "лет — целевой возраст"),
    ("4", "проекта за месяц"),
    ("90", "минут — одно занятие"),
])

# 4. Формат
slide_section(prs, "Как устроено обучение", section_number=2)

slide_content(prs,
    title="Формат занятий",
    bullets=[
        "Группы 4–6 детей — каждому внимание",
        "1 раз в неделю, 90 минут",
        "Проектный подход: не упражнения, а реальные проекты",
        "9 AI-инструментов: ChatGPT, Midjourney, Claude, Cursor...",
        "Все подписки включены в стоимость",
    ]
)

# 5. CTA
slide_final(prs,
    cta_text="Не скроллить — создавать",
    contact="Новосибирск | Запись: @synapse_school"
)

# Сохраняем
prs.save("/tmp/synapse_presentation.pptx")
print("Презентация сохранена: /tmp/synapse_presentation.pptx")
```

---

## Checklist перед генерацией

- [ ] Формат: 16:9 (Inches(16) x Inches(9))
- [ ] Фон титульных/секционных слайдов: чёрный #000000
- [ ] Фон контентных слайдов: белый #FFFFFF
- [ ] Заголовки: Space Grotesk Bold, lime #CCFF00 (на чёрном) / чёрный (на белом)
- [ ] Текст: Inter Regular, белый (на чёрном) / чёрный (на белом)
- [ ] Акцентный шрифт (числа): Unbounded Bold
- [ ] Карточки: neo-brutalist с чёрной тенью
- [ ] Логотип SYN + APSE (lime) — на каждом слайде
- [ ] Lime полоска-декор на контентных слайдах
- [ ] Номера секций: Unbounded, purple #5D3FD3
