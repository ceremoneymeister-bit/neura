---
name: excel-xlsx
description: "Use when creating or editing Excel files (.xlsx) — таблицы, отчёты, экспорт данных, 'создай таблицу', 'сделай Excel', 'xlsx', формулы, аналитика"
proactive_enabled: false
proactive_trigger_1_type: event
proactive_trigger_1_condition: "нужна таблица/аналитика"
proactive_trigger_1_action: "сгенерировать XLSX"
learning_track_success: true
learning_track_corrections: true
learning_evolve_threshold: 5
learning_auto_update: [anti-patterns, triggers, changelog]
---

# Excel / XLSX — работа с таблицами

## Обзор
Создание и редактирование .xlsx файлов. Два инструмента:
- **openpyxl** — структура, формулы, форматирование, сохранение шаблонов
- **pandas** — анализ данных, преобразования, агрегация

## Библиотеки
```bash
pip install openpyxl pandas
```

## Когда что использовать

| Задача | Инструмент |
|--------|-----------|
| Анализ, фильтрация, pivot | pandas |
| Формулы, стили, графики | openpyxl |
| Чтение CSV → обработка → .xlsx | pandas + openpyxl |
| Редактирование шаблона | openpyxl |
| Большие файлы (100k+ строк) | pandas с chunked read |

## Быстрый старт (openpyxl)

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

wb = Workbook()
ws = wb.active
ws.title = "Отчёт"

# Заголовки
headers = ['Имя', 'Email', 'Сумма', 'Статус']
for col, header in enumerate(headers, 1):
    cell = ws.cell(row=1, column=col, value=header)
    cell.font = Font(bold=True, size=12, color='FFFFFF')
    cell.fill = PatternFill(start_color='333333', fill_type='solid')
    cell.alignment = Alignment(horizontal='center')

# Данные
data = [
    ['Иван', 'ivan@mail.ru', 50000, 'Оплачено'],
    ['Мария', 'maria@mail.ru', 75000, 'В работе'],
]
for row_idx, row_data in enumerate(data, 2):
    for col_idx, value in enumerate(row_data, 1):
        ws.cell(row=row_idx, column=col_idx, value=value)

# Формула
ws.cell(row=4, column=3, value='=SUM(C2:C3)')

# Ширина колонок
for col in range(1, 5):
    ws.column_dimensions[get_column_letter(col)].width = 20

# Автофильтр
ws.auto_filter.ref = f'A1:D{len(data)+1}'

wb.save('/tmp/report.xlsx')
```

## Быстрый старт (pandas)

```python
import pandas as pd

# Создание из данных
df = pd.DataFrame({
    'Клиент': ['Виктория', 'Марина', 'Юлия'],
    'Оплата': [50000, 80000, 35000],
    'Статус': ['Активен', 'Активен', 'Пауза']
})

# Сохранение в .xlsx
df.to_excel('/tmp/clients.xlsx', index=False, sheet_name='Клиенты')

# Чтение .xlsx
df = pd.read_excel('/tmp/clients.xlsx')

# Несколько листов
with pd.ExcelWriter('/tmp/report.xlsx', engine='openpyxl') as writer:
    df_sales.to_excel(writer, sheet_name='Продажи', index=False)
    df_costs.to_excel(writer, sheet_name='Расходы', index=False)
```

## Ключевые правила

### Формулы
- **Пиши формулы в ячейки**, не хардкодь результат
- `ws['C10'] = '=SUM(C2:C9)'` — правильно
- `ws['C10'] = 125000` — неправильно (потеряется связь)
- Проверяй: нет `#REF!`, `#DIV/0!`, `#VALUE!`, `#NAME?`

### Даты
- Excel хранит даты как серийные номера (1 = 1 января 1900)
- Используй `datetime` объекты, openpyxl конвертирует автоматически
- Формат даты: `cell.number_format = 'DD.MM.YYYY'`
```python
from datetime import datetime
ws['A1'] = datetime(2026, 3, 19)
ws['A1'].number_format = 'DD.MM.YYYY'
```

### Типы данных
- Длинные ID, телефоны, ИНН → сохраняй как текст
```python
ws['A1'].number_format = '@'  # текстовый формат
ws['A1'] = '79991234567'
```

### Графики
```python
from openpyxl.chart import BarChart, Reference

chart = BarChart()
chart.title = "Продажи"
chart.y_axis.title = "Сумма, ₽"
data = Reference(ws, min_col=2, min_row=1, max_row=5)
cats = Reference(ws, min_col=1, min_row=2, max_row=5)
chart.add_data(data, titles_from_data=True)
chart.set_categories(cats)
ws.add_chart(chart, "E2")
```

### Условное форматирование
```python
from openpyxl.formatting.rule import CellIsRule

red_fill = PatternFill(start_color='FF0000', fill_type='solid')
green_fill = PatternFill(start_color='00FF00', fill_type='solid')

ws.conditional_formatting.add('D2:D100',
    CellIsRule(operator='equal', formula=['"Просрочено"'], fill=red_fill))
ws.conditional_formatting.add('D2:D100',
    CellIsRule(operator='equal', formula=['"Оплачено"'], fill=green_fill))
```

### Защита листа
```python
ws.protection.sheet = True
ws.protection.password = 'pass123'
# Разблокировать отдельные ячейки для редактирования
ws['B2'].protection = Protection(locked=False)
```

## Частые ошибки

| Ошибка | Решение |
|--------|---------|
| Формулы не пересчитываются | Открыть в Excel → Ctrl+Shift+F9 |
| Телефон стал числом | Формат `@` (текст) ДО записи значения |
| Merged cells ломаются | `ws.merge_cells('A1:C1')` — осторожно с итерацией |
| Большой файл — OOM | `pd.read_excel(chunk_size=10000)` или `openpyxl.load_workbook(read_only=True)` |
| Кириллица в имени файла | Используй транслит или латиницу в пути |

## Шаблоны

### Финансовый отчёт
```python
wb = Workbook()
ws = wb.active
ws.title = 'Финансы'
# Шапка: Месяц | Доход | Расход | Прибыль
# Формула прибыли: =B2-C2
# Итого: =SUM(B2:B13)
```

### CRM-выгрузка
```python
# pandas для обработки
df = pd.DataFrame(crm_data)
df['Дата'] = pd.to_datetime(df['Дата'])
df = df.sort_values('Дата', ascending=False)
df.to_excel('/tmp/crm_export.xlsx', index=False)
```

## Интеграция с ботами
```
[FILE:/tmp/report.xlsx]
```

## vs Google Sheets
| Когда | Инструмент |
|-------|-----------|
| Совместное редактирование | Google Sheets (MCP) |
| Локальный файл клиенту | .xlsx (этот скилл) |
| Формулы + макросы | .xlsx |
| Дашборд онлайн | Google Sheets |

---

## Changelog

<!-- Сюда автоматически добавляются уроки после каждого использования скилла -->






































- 2026-04-07: 41 использований, success rate 100.0%, avg latency 54.0s
- 2026-04-07: 40 использований, success rate 100.0%, avg latency 54.3s
- 2026-04-07: 39 использований, success rate 100.0%, avg latency 55.2s
- 2026-04-07: 38 использований, success rate 100.0%, avg latency 55.4s
- 2026-04-07: 37 использований, success rate 100.0%, avg latency 55.1s
- 2026-04-07: 36 использований, success rate 100.0%, avg latency 56.0s
- 2026-04-07: 35 использований, success rate 100.0%, avg latency 57.1s
- 2026-04-07: 34 использований, success rate 100.0%, avg latency 57.8s
- 2026-04-07: 33 использований, success rate 100.0%, avg latency 59.0s
- 2026-04-07: 32 использований, success rate 100.0%, avg latency 60.3s
- 2026-04-07: 31 использований, success rate 100.0%, avg latency 57.8s
- 2026-04-07: 30 использований, success rate 100.0%, avg latency 58.9s
- 2026-04-07: 29 использований, success rate 100.0%, avg latency 59.8s
- 2026-04-07: 28 использований, success rate 100.0%, avg latency 60.7s
- 2026-04-07: 27 использований, success rate 100.0%, avg latency 61.6s
- 2026-04-06: 26 использований, success rate 100.0%, avg latency 62.7s
- 2026-04-06: 25 использований, success rate 100.0%, avg latency 63.8s
- 2026-04-06: 24 использований, success rate 100.0%, avg latency 65.5s
- 2026-04-06: 23 использований, success rate 100.0%, avg latency 67.1s
- 2026-04-06: 22 использований, success rate 100.0%, avg latency 69.3s
- 2026-04-06: 21 использований, success rate 100.0%, avg latency 71.5s
- 2026-04-06: 20 использований, success rate 100.0%, avg latency 53.5s
- 2026-04-06: 19 использований, success rate 100.0%, avg latency 51.5s
- 2026-04-06: 18 использований, success rate 100.0%, avg latency 53.6s
- 2026-04-06: 17 использований, success rate 100.0%, avg latency 53.8s
- 2026-04-06: 16 использований, success rate 100.0%, avg latency 56.8s
- 2026-04-06: 15 использований, success rate 100.0%, avg latency 58.9s
- 2026-04-06: 14 использований, success rate 100.0%, avg latency 60.1s
- 2026-04-06: 13 использований, success rate 100.0%, avg latency 61.5s
- 2026-04-06: 12 использований, success rate 100.0%, avg latency 62.5s
- 2026-04-06: 11 использований, success rate 100.0%, avg latency 57.2s
- 2026-04-06: 10 использований, success rate 100.0%, avg latency 60.6s
- 2026-04-06: 9 использований, success rate 100.0%, avg latency 44.5s
- 2026-04-06: 8 использований, success rate 100.0%, avg latency 48.0s
- 2026-04-06: 7 использований, success rate 100.0%, avg latency 52.4s
- 2026-04-06: 6 использований, success rate 100.0%, avg latency 55.9s
- 2026-04-06: 5 использований, success rate 100.0%, avg latency 62.4s