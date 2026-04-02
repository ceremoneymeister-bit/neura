# 🔍 Capsule Audit Report
**Дата:** {{date}}
**Капсулы:** {{capsules}}
**Общий балл:** {{score}}/100

## Сводка
- Протестировано: {{capsule_count}} капсул, {{total_tests}} тестов
- ✅ Пройдено: {{passed}} | ❌ Провалено: {{failed}} | ⏭️ Пропущено: {{skipped}}
- Критические проблемы: {{critical}}

## {{capsule_name}} ({{capsule_score}}/100)

### Health {{health_icon}} {{health_passed}}/{{health_total}}
| # | Тест | Статус | Детали |
|---|------|--------|--------|
| {{test_id}} | {{test_name}} | {{test_icon}} | {{test_details}} |

### Messaging {{msg_icon}} {{msg_passed}}/{{msg_total}}
| # | Тест | Статус | Детали |
|---|------|--------|--------|
| {{test_id}} | {{test_name}} | {{test_icon}} | {{test_details}} |

### ❌ Проблемы и рекомендации
- **{{problem_id}}:** {{problem_description}}

## Cross-Capsule Consistency
| Проверка | Victoria | Marina | Yulia | Maxim |
|----------|---------|--------|-------|-------|
| {{check_name}} | {{v_status}} | {{m_status}} | {{y_status}} | {{x_status}} |

---
*Сгенерировано capsule-audit {{date}}*
