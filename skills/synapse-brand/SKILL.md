---
name: synapse-brand
description: "Брендбук школы Synapse. Цвета, типографика, стиль, tone of voice, конфиги для PDF/PPT, альтернативы нейминга. Единый источник брендинга для всех материалов."
version: 1.0.0
author: Дмитрий Ростовцев
created: 2026-03-26
category: branding
tags: [synapse, brand, children, school, ai, pdf, ppt, naming, design-system]
risk: safe
source: custom
proactive_enabled: false
proactive_trigger_1_type: event
proactive_trigger_1_condition: "брендинг-материалы школы"
proactive_trigger_1_action: "применить лайм+чёрный стиль"
learning_track_success: true
learning_track_corrections: true
learning_evolve_threshold: 5
learning_auto_update: [anti-patterns, triggers, changelog]
---

# Synapse Brand — брендинг школы AI-мышления

## Назначение

Единый скилл брендинга для проекта Synapse — детской школы AI-мышления (Новосибирск). Содержит полный брендбук, конфиги для генерации документов (PDF, PPT), альтернативы нейминга и правила применения визуального стиля.

## Триггеры

Активировать при:
- «Synapse», «синапс», «школа AI», «школа для детей»
- «брендбук», «branding», «фирменный стиль», «айдентика»
- «PDF для Synapse», «презентация Synapse», «документ для школы»
- «нейминг», «название школы», «ребрендинг Synapse», «альтернативы названия»
- «цвета Synapse», «шрифты», «tone of voice школы»
- Любые задачи по дизайну/документам/контенту, связанные с проектом `projects/Synapse/`

## Каноничный источник

**ВСЕГДА** сначала сверяйся с каноничным файлом:
```
projects/Synapse/SYNAPSE_CANONICAL.md
```
Если параметры расходятся — каноничный файл имеет приоритет.

## Файлы скилла

| Файл | Содержание |
|------|-----------|
| `references/brand-guide.md` | Полный брендбук: цвета, типографика, тени, углы, tone of voice, do's & don'ts |
| `references/naming-alternatives.md` | 10 альтернатив названию Synapse с анализом |
| `references/pdf-template-config.md` | Python-конфиг для notion-pdf / WeasyPrint генератора |
| `references/ppt-template-config.md` | Python-конфиг для python-pptx генератора |

## Workflow: применение бренда к документу

### 1. Определи тип документа
- **PDF** (отчёт, КП, план, программа) → читай `references/pdf-template-config.md`
- **PPT** (презентация, питч-дек, слайды) → читай `references/ppt-template-config.md`
- **Веб** (лендинг, компонент) → используй `projects/Synapse/website/tailwind.config.js`
- **Контент** (пост, описание, текст) → читай tone of voice в `references/brand-guide.md`

### 2. Загрузи конфиг
```python
# Для PDF
exec(open('.agent/skills/synapse-brand/references/pdf-template-config.md').read())
# Используй SYNAPSE_PDF_CONFIG

# Для PPT
exec(open('.agent/skills/synapse-brand/references/ppt-template-config.md').read())
# Используй SYNAPSE_PPT_CONFIG
```

### 3. Примени бренд
- Заголовки: Space Grotesk, 800 weight, чёрный #000000
- Акценты: #CCFF00 (acid lime) — подсветки, кнопки, выделения
- Вторичный акцент: #5D3FD3 (purple) — иконки, бейджи, графики
- Тени: 4px 4px 0px 0px #000000 (neo-brutalist)
- Углы: 4-8px (жёсткие, не rounded)
- Тон: уверенный, прямой, «крутой старший друг» (не корпоративный, не детский)

### 4. Проверь соответствие
- [ ] Основной цвет #CCFF00 присутствует
- [ ] Заголовки — Space Grotesk (или fallback sans-serif, bold)
- [ ] Текст — Inter (или fallback sans-serif)
- [ ] Тени жёсткие (не размытые)
- [ ] Углы 4-8px (не круглые)
- [ ] Тон текста: прямой, без «школьной» или «корпоративной» тональности

## Антипаттерны

- **НЕ** использовать rounded углы (border-radius > 16px) — это не про Synapse
- **НЕ** использовать пастельные цвета — бренд построен на контрасте
- **НЕ** использовать «детский» язык (уменьшительно-ласкательные, восклицательные знаки подряд)
- **НЕ** использовать корпоративный канцелярит
- **НЕ** путать с брендингом Neura / ceremoneymeister — это отдельный проект

## Зависимости

- `notion-pdf` — для генерации PDF
- `ppt-generator` — для генерации PPT
- `frontend-design` — для веб-компонентов
- `tailwind-patterns` — для Tailwind CSS

---

## Changelog

<!-- Сюда автоматически добавляются уроки после каждого использования скилла -->
