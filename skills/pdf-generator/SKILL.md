---
name: pdf-generator
description: "Генерация премиальных PDF — КП, отчёты, презентации, сертификаты. WeasyPrint + HTML/CSS. Красивый дизайн, кириллица, градиенты."
---

# PDF Generator — премиальные документы

## Обзор
Генерация стильных PDF-файлов через **WeasyPrint** (HTML/CSS → PDF). Полная поддержка кириллицы, градиентов, карточек, таблиц, колонтитулов.

## Когда использовать
- "создай PDF", "коммерческое предложение", "КП", "отчёт в PDF"
- "сертификат", "диплом", "прайс-лист", "инвойс"
- Любой запрос на создание красивого документа в PDF

## Библиотеки

**Основная:** WeasyPrint (HTML/CSS → PDF, премиум качество)
```bash
pip install weasyprint
# Системные зависимости (Debian/Ubuntu):
apt-get install -y libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 fonts-dejavu-core
```

**Запасная:** fpdf2 (если WeasyPrint недоступен)
```bash
pip install fpdf2
```

## Docker установка
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*
RUN pip install weasyprint fpdf2
```

## Фазы создания PDF

### Фаза 1: Определить тип документа
| Тип | Акцент | Цветовая схема |
|-----|--------|---------------|
| КП / Proposal | Продающий, с CTA | Бренд-цвет + тёмный |
| Отчёт / Report | Данные, графики | Нейтральный + акцент |
| Сертификат | Торжественный | Золото + тёмный |
| Прайс-лист | Структура, таблицы | Минимализм |
| Инвойс / Счёт | Формальный | Серый + акцент |

### Фаза 2: Собрать контент
- Заголовок и подзаголовок
- Секции (текст, таблицы, списки, карточки)
- Контакты / футер
- Бренд-цвета (спросить или использовать нейтральные)

### Фаза 3: Генерация через шаблон

## Главный шаблон — `generate_premium_pdf()`

```python
import weasyprint
from datetime import datetime

def generate_premium_pdf(
    title: str,
    subtitle: str = "",
    sections: list = None,
    output_path: str = "/tmp/output.pdf",
    brand_color: str = "#6c5ce7",
    dark_color: str = "#0f0c29",
    accent_color: str = "#00cec9",
    author: str = "",
    logo_text: str = "",
) -> str:
    """
    Генерирует премиальный PDF.

    sections — список словарей:
      {"type": "text", "heading": "...", "content": "..."}
      {"type": "card", "heading": "...", "content": "..."}
      {"type": "highlight", "heading": "...", "content": "...", "value": "15 000 ₽"}
      {"type": "table", "heading": "...", "rows": [["H1","H2"], ["v1","v2"], ...]}
      {"type": "list", "heading": "...", "items": ["item1", "item2", ...]}
      {"type": "columns", "heading": "...", "cols": [{"title": "...", "text": "..."}, ...]}
      {"type": "quote", "content": "...", "author": "..."}
      {"type": "divider"}
    """
    date_str = datetime.now().strftime("%d.%m.%Y")

    sections_html = ""
    for s in (sections or []):
        stype = s.get("type", "text")
        heading = s.get("heading", "")
        heading_html = f'<h2>{heading}</h2>' if heading else ""

        if stype == "text":
            # Поддержка переносов строк
            content = s.get("content", "").replace("\n", "<br>")
            sections_html += f'{heading_html}<p>{content}</p>'

        elif stype == "card":
            content = s.get("content", "").replace("\n", "<br>")
            sections_html += f'{heading_html}<div class="card">{content}</div>'

        elif stype == "highlight":
            content = s.get("content", "")
            value = s.get("value", "")
            sections_html += f'''
            <div class="highlight-box">
                <div class="highlight-value">{value}</div>
                <div class="highlight-label">{content}</div>
            </div>'''

        elif stype == "table":
            rows = s.get("rows", [])
            if not rows:
                continue
            ths = "".join(f"<th>{h}</th>" for h in rows[0])
            trs = ""
            for row in rows[1:]:
                tds = "".join(f"<td>{c}</td>" for c in row)
                trs += f"<tr>{tds}</tr>"
            sections_html += f'{heading_html}<table><thead><tr>{ths}</tr></thead><tbody>{trs}</tbody></table>'

        elif stype == "list":
            items = s.get("items", [])
            lis = "".join(f"<li>{item}</li>" for item in items)
            sections_html += f'{heading_html}<ul class="check-list">{lis}</ul>'

        elif stype == "columns":
            cols = s.get("cols", [])
            cols_html = ""
            for col in cols:
                cols_html += f'<div class="col"><h3>{col.get("title","")}</h3><p>{col.get("text","")}</p></div>'
            sections_html += f'{heading_html}<div class="columns">{cols_html}</div>'

        elif stype == "quote":
            content = s.get("content", "")
            qauthor = s.get("author", "")
            attr = f'<div class="quote-author">— {qauthor}</div>' if qauthor else ""
            sections_html += f'<blockquote class="styled-quote">{content}{attr}</blockquote>'

        elif stype == "divider":
            sections_html += '<hr class="divider">'

    logo_html = f'<div class="logo">{logo_text}</div>' if logo_text else ""

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
@page {{
    size: A4;
    margin: 0;
    @bottom-center {{
        content: counter(page) " / " counter(pages);
        font-size: 9px;
        color: #999;
        padding-bottom: 20px;
    }}
}}

body {{
    font-family: 'DejaVu Sans', 'Liberation Sans', 'FreeSans', sans-serif;
    margin: 0;
    color: #1a1a2e;
    line-height: 1.7;
    font-size: 12px;
}}

/* === HEADER === */
.header {{
    background: linear-gradient(135deg, {dark_color} 0%, {brand_color} 100%);
    color: white;
    padding: 50px 60px 40px;
    position: relative;
}}
.header::after {{
    content: "";
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 4px;
    background: linear-gradient(90deg, {accent_color}, {brand_color});
}}
.header h1 {{
    font-size: 28px;
    margin: 0 0 8px;
    letter-spacing: -0.5px;
}}
.header .sub {{
    font-size: 14px;
    opacity: 0.8;
    font-weight: 300;
}}
.header .date {{
    font-size: 10px;
    opacity: 0.5;
    margin-top: 20px;
    text-transform: uppercase;
    letter-spacing: 1px;
}}
.logo {{
    font-size: 11px;
    opacity: 0.6;
    position: absolute;
    top: 20px;
    right: 60px;
    text-transform: uppercase;
    letter-spacing: 2px;
}}

/* === CONTENT === */
.content {{
    padding: 40px 60px;
}}
h2 {{
    color: {brand_color};
    font-size: 18px;
    margin: 30px 0 12px;
    padding-bottom: 8px;
    border-bottom: 2px solid {brand_color};
}}
h3 {{
    color: {dark_color};
    font-size: 14px;
    margin: 16px 0 8px;
}}
p {{
    color: #444;
    margin: 0 0 16px;
}}

/* === CARD === */
.card {{
    background: linear-gradient(135deg, #f8f7ff 0%, #f0eeff 100%);
    border-left: 4px solid {brand_color};
    padding: 20px 24px;
    border-radius: 0 12px 12px 0;
    margin: 16px 0;
    font-size: 12px;
    color: #333;
}}

/* === HIGHLIGHT BOX === */
.highlight-box {{
    background: linear-gradient(135deg, {brand_color} 0%, {dark_color} 100%);
    color: white;
    padding: 30px;
    border-radius: 16px;
    margin: 20px 0;
    text-align: center;
}}
.highlight-value {{
    font-size: 36px;
    font-weight: bold;
    margin-bottom: 8px;
}}
.highlight-label {{
    font-size: 14px;
    opacity: 0.85;
}}

/* === TABLE === */
table {{
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    border-radius: 12px;
    overflow: hidden;
    margin: 16px 0;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}}
thead tr {{
    background: linear-gradient(135deg, {brand_color} 0%, {dark_color} 100%);
}}
th {{
    color: white;
    padding: 14px 16px;
    text-align: left;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-weight: 600;
}}
td {{
    padding: 12px 16px;
    border-bottom: 1px solid #f0f0f0;
    font-size: 12px;
    color: #333;
}}
tbody tr:nth-child(even) {{
    background: #fafafe;
}}
tbody tr:last-child td {{
    border-bottom: none;
}}

/* === LIST === */
.check-list {{
    list-style: none;
    padding: 0;
    margin: 16px 0;
}}
.check-list li {{
    padding: 12px 0 12px 32px;
    position: relative;
    border-bottom: 1px solid #f0f0f0;
    font-size: 12px;
    color: #333;
}}
.check-list li::before {{
    content: "\\2713";
    position: absolute;
    left: 4px;
    color: {accent_color};
    font-weight: bold;
    font-size: 14px;
}}
.check-list li:last-child {{
    border-bottom: none;
}}

/* === COLUMNS === */
.columns {{
    display: flex;
    gap: 20px;
    margin: 16px 0;
}}
.col {{
    flex: 1;
    background: #f9f9fd;
    padding: 20px;
    border-radius: 12px;
    border-top: 3px solid {brand_color};
}}
.col h3 {{
    margin-top: 0;
    color: {brand_color};
}}
.col p {{
    font-size: 11px;
    margin: 0;
}}

/* === QUOTE === */
.styled-quote {{
    border-left: 4px solid {accent_color};
    margin: 20px 0;
    padding: 16px 24px;
    font-style: italic;
    color: #555;
    background: #f8fffe;
    border-radius: 0 8px 8px 0;
}}
.quote-author {{
    font-style: normal;
    font-size: 11px;
    color: {brand_color};
    margin-top: 8px;
}}

/* === DIVIDER === */
.divider {{
    border: none;
    height: 1px;
    background: linear-gradient(90deg, transparent, {brand_color}40, transparent);
    margin: 30px 0;
}}

/* === FOOTER === */
.footer {{
    background: {dark_color};
    color: white;
    padding: 24px 60px;
    font-size: 11px;
    margin-top: 40px;
    display: flex;
    justify-content: space-between;
}}
.footer .copy {{
    opacity: 0.6;
}}
</style></head><body>
<div class="header">
    {logo_html}
    <h1>{title}</h1>
    <div class="sub">{subtitle}</div>
    <div class="date">{date_str}</div>
</div>
<div class="content">
    {sections_html}
</div>
<div class="footer">
    <div>{author}</div>
    <div class="copy">{date_str}</div>
</div>
</body></html>"""

    weasyprint.HTML(string=html).write_pdf(output_path)
    return output_path
```

## Примеры вызова

### КП (коммерческое предложение)
```python
generate_premium_pdf(
    title="Коммерческое предложение",
    subtitle="Отбеливание зубов — клиника Евромед",
    brand_color="#2d6cdf",
    dark_color="#0a1929",
    accent_color="#00b894",
    author="Клиника Евромед | Новосибирск",
    logo_text="ЕВРОМЕД",
    sections=[
        {"type": "card", "heading": "", "content": "Предлагаем профессиональное отбеливание зубов по технологии ZOOM-4"},
        {"type": "highlight", "value": "15 000 ₽", "content": "Стоимость процедуры (1 сеанс, 60 мин)"},
        {"type": "list", "heading": "Что входит", "items": [
            "Консультация стоматолога",
            "Профессиональная чистка",
            "Отбеливание ZOOM-4 (3 цикла)",
            "Фторирование после процедуры",
        ]},
        {"type": "table", "heading": "Сравнение методов", "rows": [
            ["Метод", "Эффект", "Длительность", "Цена"],
            ["ZOOM-4", "До 8 тонов", "60 мин", "15 000 ₽"],
            ["Домашнее", "До 3 тонов", "2 недели", "8 000 ₽"],
            ["Полоски", "До 2 тонов", "1 месяц", "3 000 ₽"],
        ]},
    ],
    output_path="/tmp/kp_evomed.pdf",
)
```

### Отчёт
```python
generate_premium_pdf(
    title="Маркетинговый отчёт",
    subtitle="Январь — Март 2026",
    brand_color="#e17055",
    dark_color="#2d3436",
    sections=[
        {"type": "columns", "heading": "Ключевые метрики", "cols": [
            {"title": "Лиды", "text": "342 заявки (+28%)"},
            {"title": "Конверсия", "text": "4.2% (было 3.1%)"},
            {"title": "ROI", "text": "280% от рекламы"},
        ]},
        {"type": "table", "heading": "По каналам", "rows": [
            ["Канал", "Бюджет", "Лиды", "CPL"],
            ["Яндекс.Директ", "120 000 ₽", "156", "769 ₽"],
            ["Instagram", "80 000 ₽", "98", "816 ₽"],
            ["SEO", "40 000 ₽", "88", "454 ₽"],
        ]},
    ],
)
```

## Цветовые палитры (готовые)

| Назначение | brand_color | dark_color | accent_color |
|-----------|-------------|------------|-------------|
| Медицина | `#2d6cdf` | `#0a1929` | `#00b894` |
| Финансы | `#6c5ce7` | `#0f0c29` | `#00cec9` |
| Красота | `#e84393` | `#2d3436` | `#fd79a8` |
| Образование | `#0984e3` | `#2d3436` | `#74b9ff` |
| Еда/ресторан | `#e17055` | `#2d3436` | `#ffeaa7` |
| Технологии | `#00b894` | `#0f0c29` | `#55efc4` |
| Нейтральный | `#636e72` | `#2d3436` | `#b2bec3` |

## Anti-Patterns
- ❌ НЕ используй fpdf2 для красивых документов — нет градиентов, скруглений, flexbox
- ❌ НЕ хардкодь шрифты — используй 'DejaVu Sans' (есть везде)
- ❌ НЕ делай страницу перегруженной — максимум 3-4 секции на страницу
- ❌ НЕ забывай `[FILE:/tmp/path.pdf]` маркер в ответе для отправки
- ❌ НЕ используй pdfkit/wkhtmltopdf — deprecated, медленный

## Fallback (если WeasyPrint недоступен)
Если `import weasyprint` падает, используй fpdf2:
```python
from fpdf import FPDF
pdf = FPDF()
pdf.add_page()
pdf.add_font('DejaVu', '', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', uni=True)
pdf.set_font('DejaVu', size=12)
pdf.cell(0, 10, 'Текст на русском', ln=True)
pdf.output('/tmp/fallback.pdf')
```

## Docker: что нужно установить
```bash
# В Dockerfile или при первом запуске
apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 fonts-dejavu-core
pip install weasyprint
```

## Уроки из практики

### 2026-03-20: Docker + Claude CLI
- fpdf2 в Docker без кириллических шрифтов → кракозябры
- WeasyPrint требует system deps (cairo, pango) — включать в Dockerfile
- Агент в Docker сам установит `pip install weasyprint` при первом вызове, но system deps нужны заранее
- `/root/.claude` должен быть writable (не `:ro`), иначе Claude CLI не может сохранять permissions
