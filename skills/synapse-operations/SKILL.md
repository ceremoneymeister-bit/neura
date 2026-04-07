---
name: synapse-operations
description: "Операционное управление школой {{SCHOOL_NAME}}: чеклисты запуска, помещения, оборудование, юридика, финансы. 'Как запустить школу', 'чеклист', 'помещение', 'договор', 'финансовая модель'."
proactive_enabled: true
proactive_trigger_1_type: schedule
proactive_trigger_1_condition: "понедельник"
proactive_trigger_1_action: "операционный чеклист школы"
learning_track_success: true
learning_track_corrections: true
learning_evolve_threshold: 5
learning_auto_update: [anti-patterns, triggers, changelog]
---

# Операционное управление {{SCHOOL_NAME}}

## Когда использовать

- Поиск и оценка помещений
- Подготовка юридических документов
- Закупка оборудования и подписок
- Финансовое планирование и P&L
- Чеклист запуска школы

## Воркфлоу

1. Прочитай `SYNAPSE_CANONICAL.md` — каноничные параметры
2. Определи задачу (помещение / юридика / финансы / общий чеклист)
3. Используй соответствующий reference-файл
4. Результат: конкретный чеклист с владельцами и сроками

## Ключевые файлы

| Файл | Описание |
|------|----------|
| `references/launch-checklist.md` | 50+ пунктов запуска с владельцами |
| `references/venue-requirements.md` | Критерии коворкинга, скоринг |
| `references/equipment-list.md` | Оборудование и расходники |
| `references/subscription-matrix.md` | AI-подписки и стоимости |
| `references/contract-templates.md` | Шаблоны договоров |
| `references/legal-checklist.md` | Юридика: ИП/ООО, 152-ФЗ, лицензии |
| `references/financial-model.md` | P&L и сценарии |

## Владелец задач

- **Влад Коренда** (@VladiFame99) — основной исполнитель операционки
- **Дмитрий** — ревью и стратегические решения
- **Анастасия** — обратная связь по помещению и оборудованию

---

## Changelog

<!-- Сюда автоматически добавляются уроки после каждого использования скилла -->
