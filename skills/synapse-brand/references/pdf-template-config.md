# Synapse — конфигурация PDF-шаблона

> Использовать совместно со скиллом `notion-pdf` или WeasyPrint генератором.
> Подключение: передать конфиг-словарь при генерации PDF.

---

## Python-конфиг

```python
SYNAPSE_PDF_CONFIG = {
    # === Цвета ===
    "brand_color": "#CCFF00",       # Acid Lime — заголовки, акценты, линии
    "dark_color": "#000000",        # Pure Black — текст, тени, рамки
    "accent_color": "#5D3FD3",      # Deep Purple — вторичные акценты, бейджи
    "bg_color": "#FFFFFF",          # Основной фон
    "card_bg": "#F5F5F5",           # Фон карточек/блоков
    "footer_bg": "#111111",         # Футер
    "text_color": "#000000",        # Основной текст
    "text_muted": "#666666",        # Приглушённый текст (captions, footnotes)

    # === Шрифты ===
    "font_heading": "Space Grotesk",
    "font_body": "Inter",
    "font_accent": "Unbounded",
    "font_heading_weight": 800,
    "font_body_weight": 400,
    "font_accent_weight": 700,

    # === Размеры текста (pt) ===
    "size_h1": 28,
    "size_h2": 22,
    "size_h3": 16,
    "size_body": 11,
    "size_caption": 9,
    "size_footer": 8,

    # === Логотип ===
    "logo_text": "SYNAPSE",
    "logo_highlight": "APSE",       # Часть логотипа, выделенная lime
    "logo_font": "Unbounded",
    "logo_size": 18,

    # === Neo-brutalist стиль ===
    "shadow": "4px 4px 0px 0px #000000",
    "shadow_sm": "2px 2px 0px 0px #000000",
    "border": "2px solid #000000",
    "border_radius": "4px",
    "border_radius_card": "8px",
}
```

---

## CSS-сниппет для WeasyPrint / HTML→PDF

```css
/* === Synapse PDF Brand Styles === */

@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700;800&family=Inter:wght@300;400;500;600;700;800;900&family=Unbounded:wght@400;500;600;700;800;900&display=swap');

:root {
    --syn-lime: #CCFF00;
    --syn-black: #000000;
    --syn-purple: #5D3FD3;
    --syn-white: #FFFFFF;
    --syn-grey-light: #F5F5F5;
    --syn-grey-dark: #111111;
    --syn-text-muted: #666666;
}

/* --- Page setup --- */
@page {
    size: A4;
    margin: 20mm 18mm 25mm 18mm;

    @top-left {
        content: "SYNAPSE";
        font-family: 'Unbounded', sans-serif;
        font-size: 9pt;
        font-weight: 700;
        color: #000000;
    }

    @bottom-center {
        content: counter(page) " / " counter(pages);
        font-family: 'Inter', sans-serif;
        font-size: 8pt;
        color: #666666;
    }
}

/* --- Header gradient bar --- */
.pdf-header {
    background: linear-gradient(135deg, #000000 0%, #111111 60%, #5D3FD3 100%);
    padding: 24px 32px;
    border-radius: 8px;
    margin-bottom: 24px;
    border: 2px solid #000000;
    box-shadow: 4px 4px 0px 0px #000000;
}

.pdf-header h1 {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 800;
    font-size: 28pt;
    color: #CCFF00;
    margin: 0 0 8px 0;
    letter-spacing: -0.02em;
    line-height: 1.1;
}

.pdf-header .subtitle {
    font-family: 'Inter', sans-serif;
    font-weight: 400;
    font-size: 12pt;
    color: #FFFFFF;
    opacity: 0.85;
    margin: 0;
}

/* --- Logo in header --- */
.pdf-logo {
    font-family: 'Unbounded', sans-serif;
    font-weight: 800;
    font-size: 14pt;
    color: #FFFFFF;
    margin-bottom: 16px;
}

.pdf-logo .highlight {
    color: #CCFF00;
}

/* --- Typography --- */
body {
    font-family: 'Inter', sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #000000;
}

h1 {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 800;
    font-size: 28pt;
    color: #000000;
    letter-spacing: -0.02em;
    line-height: 1.1;
    margin-top: 32px;
    margin-bottom: 12px;
    border-bottom: 3px solid #CCFF00;
    padding-bottom: 8px;
}

h2 {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 800;
    font-size: 22pt;
    color: #000000;
    letter-spacing: -0.02em;
    line-height: 1.15;
    margin-top: 24px;
    margin-bottom: 10px;
}

h3 {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    font-size: 16pt;
    color: #000000;
    margin-top: 20px;
    margin-bottom: 8px;
}

p {
    margin-bottom: 10px;
    line-height: 1.6;
}

/* --- Neo-brutalist card --- */
.card-neo {
    background: #F5F5F5;
    border: 2px solid #000000;
    border-radius: 8px;
    box-shadow: 4px 4px 0px 0px #000000;
    padding: 20px 24px;
    margin: 16px 0;
    page-break-inside: avoid;
}

.card-neo h4 {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    font-size: 14pt;
    color: #000000;
    margin: 0 0 8px 0;
}

/* --- Accent border card (purple left stripe) --- */
.card-accent {
    background: #FFFFFF;
    border: 2px solid #000000;
    border-left: 6px solid #5D3FD3;
    border-radius: 4px;
    padding: 16px 20px;
    margin: 16px 0;
    page-break-inside: avoid;
}

/* --- Lime highlight card --- */
.card-lime {
    background: #CCFF00;
    border: 2px solid #000000;
    border-radius: 8px;
    box-shadow: 4px 4px 0px 0px #000000;
    padding: 20px 24px;
    margin: 16px 0;
    page-break-inside: avoid;
    color: #000000;
}

/* --- Badge --- */
.badge {
    display: inline-block;
    padding: 2px 10px;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    font-size: 9pt;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border: 2px solid #000000;
    border-radius: 4px;
    box-shadow: 2px 2px 0px 0px #000000;
}

.badge-lime {
    background: #CCFF00;
    color: #000000;
}

.badge-purple {
    background: #5D3FD3;
    color: #FFFFFF;
}

.badge-dark {
    background: #000000;
    color: #CCFF00;
}

/* --- Table --- */
table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    border: 2px solid #000000;
    border-radius: 8px;
    overflow: hidden;
    margin: 16px 0;
    font-size: 10pt;
}

thead {
    background: #000000;
    color: #CCFF00;
}

th {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    text-align: left;
    padding: 10px 14px;
    font-size: 10pt;
    text-transform: uppercase;
    letter-spacing: 0.03em;
}

td {
    padding: 10px 14px;
    border-top: 1px solid rgba(0, 0, 0, 0.1);
}

tr:nth-child(even) {
    background: #F5F5F5;
}

/* --- Divider --- */
hr {
    border: none;
    height: 3px;
    background: #CCFF00;
    margin: 24px 0;
}

/* --- Lists --- */
ul, ol {
    padding-left: 20px;
    margin-bottom: 12px;
}

li {
    margin-bottom: 4px;
    line-height: 1.5;
}

li::marker {
    color: #5D3FD3;
    font-weight: 700;
}

/* --- Code/monospace --- */
code {
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 10pt;
    background: #F5F5F5;
    border: 1px solid rgba(0, 0, 0, 0.15);
    border-radius: 4px;
    padding: 1px 5px;
}

pre {
    background: #111111;
    color: #CCFF00;
    border: 2px solid #000000;
    border-radius: 8px;
    padding: 16px;
    font-size: 9pt;
    line-height: 1.5;
    overflow-x: auto;
    margin: 16px 0;
}

/* --- Footer --- */
.pdf-footer {
    background: #111111;
    color: #FFFFFF;
    padding: 16px 24px;
    border-radius: 8px;
    margin-top: 32px;
    font-size: 9pt;
    border: 2px solid #000000;
}

.pdf-footer .brand {
    font-family: 'Unbounded', sans-serif;
    font-weight: 700;
    color: #CCFF00;
}

/* --- Utility: lime text highlight --- */
.lime {
    color: #CCFF00;
    background: #000000;
    padding: 0 4px;
    border-radius: 2px;
}

.purple {
    color: #5D3FD3;
}

strong {
    font-weight: 700;
}
```

---

## Пример использования

### Генерация PDF через notion-pdf с брендингом Synapse

```python
import subprocess
import json

# 1. Подготовь markdown-контент
markdown_content = """
# Программа обучения AI-мышлению

## Модуль 1: Основы промптинга

Дети изучают принципы формулирования запросов к AI...

## Модуль 2: Генерация изображений

Работа с Midjourney, Leonardo.ai, DALL-E...
"""

# 2. Сохрани во временный файл
with open("/tmp/synapse_program.md", "w") as f:
    f.write(markdown_content)

# 3. Генерируй PDF с кастомным CSS
subprocess.run([
    "python3", ".agent/skills/notion-pdf/scripts/md2pdf.py",
    "--input", "/tmp/synapse_program.md",
    "--output", "/tmp/synapse_program.pdf",
    "--title", "SYNAPSE — Программа обучения",
    "--css", ".agent/skills/synapse-brand/references/synapse.css"  # если CSS вынесен в файл
], check=True)
```

### Генерация HTML→PDF через WeasyPrint (полный контроль)

```python
from weasyprint import HTML

html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        {open('.agent/skills/synapse-brand/references/pdf-template-config.md').read()
         .split('```css')[1].split('```')[0]}
    </style>
</head>
<body>
    <div class="pdf-header">
        <div class="pdf-logo">SYN<span class="highlight">APSE</span></div>
        <h1>Программа обучения</h1>
        <p class="subtitle">AI-мышление для детей 9–14 лет</p>
    </div>

    <h2>Модуль 1: Основы промптинга</h2>
    <div class="card-neo">
        <h4>Что изучаем</h4>
        <p>Принципы формулирования запросов к ChatGPT, Claude, Gemini.</p>
    </div>

    <div class="card-accent">
        <p><strong>Результат:</strong> ребёнок уверенно работает с 3+ AI-инструментами.</p>
    </div>

    <div class="card-lime">
        <h4>Ключевая метрика</h4>
        <p>4 проекта за первый месяц обучения.</p>
    </div>

    <div class="pdf-footer">
        <span class="brand">SYN<span style="color:#CCFF00">APSE</span></span> — школа AI-мышления | Новосибирск
    </div>
</body>
</html>
"""

HTML(string=html_content).write_pdf("/tmp/synapse_branded.pdf")
```

---

## Checklist перед генерацией

- [ ] Шрифт заголовков: Space Grotesk 800
- [ ] Шрифт текста: Inter 400
- [ ] Логотип: SYN + APSE (lime highlight)
- [ ] Header gradient: чёрный → тёмно-серый → фиолетовый
- [ ] Акцентные линии: #CCFF00 (lime)
- [ ] Таблицы: чёрный header, lime текст в header
- [ ] Карточки: рамка 2px + тень 4px 4px 0px 0px #000
- [ ] Радиус углов: 4-8px (не круглые)
- [ ] Нет размытых теней — только жёсткие
