---
name: cron-guardian
description: "Управление всеми кронами сервера + защита подписки Claude. Реестр слотов, карта, поиск свободных, лимиты, TG-алерты. Триггеры: 'лимиты claude', 'крон', 'слот', 'расписание cron', 'добавить таймер', 'карта кронов', 'сколько кронов'."
version: 2.0.0
author: Dmitry Rostovtsev (ceremoneymeister)
created: 2026-03-25
updated: 2026-04-01
category: infrastructure
tags: [cron, slots, limits, claude-cli, subscription, protection, registry, alerts]
risk: safe
source: internal
proactive_enabled: true
proactive_trigger_1_type: threshold
proactive_trigger_1_condition: "свободных слотов < 3"
proactive_trigger_1_action: "предупредить о лимите"
proactive_trigger_2_type: event
proactive_trigger_2_condition: "добавление нового cron/таймера"
proactive_trigger_2_action: "gate-check бюджета"
learning_track_success: true
learning_track_corrections: true
learning_evolve_threshold: 3
learning_auto_update: [anti-patterns, triggers, changelog]
---

# Cron Guardian + Slot Manager — управление кронами сервера

## Назначение

Единая система управления ВСЕМИ кронами и таймерами сервера:
1. **Реестр** — автосканирование crontab + systemd + reminders → `cron-registry.json`
2. **Карта** — визуальная 24-часовая сетка всех слотов
3. **Слоты** — поиск свободного времени, автосдвиг при конфликтах
4. **Лимиты** — макс. слотов, макс. в час, мин. интервал
5. **Алерты** — TG-уведомления при 75%/90% заполнения
6. **Claude budget** — gate-check для защиты подписки

## ДНК-правила

### Перед добавлением ЛЮБОГО крона:
```bash
python3 guardian.py slot-find <HH:MM>        # Найти свободный слот
python3 guardian.py register --id X --time HH:MM --cmd "..." --apply
```

### Перед вызовом `claude -p` из крона:
```bash
python3 guardian.py gate || exit 0
```

## CLI — все команды

### Карта и слоты (NEW)
```bash
# Полная карта кронов (24ч сетка)
python3 guardian.py map

# Пересканировать crontab + systemd → обновить реестр
python3 guardian.py map --scan

# Найти ближайший свободный слот к указанному времени
python3 guardian.py slot-find 09:00

# Зарегистрировать новый крон (с проверкой конфликтов)
python3 guardian.py register --id my-task --time 09:00 --cmd "python3 script.py"

# + добавить в crontab автоматически
python3 guardian.py register --id my-task --time 09:00 --cmd "python3 script.py" --apply

# + указать owner/priority/claude_calls
python3 guardian.py register --id my-task --time 09:00 --cmd "..." --owner victoria --priority client --claude 1

# Удалить из реестра
python3 guardian.py unregister my-task

# + удалить из crontab автоматически
python3 guardian.py unregister my-task --apply

# Проверить пороги и отправить TG-алерт если нужно
python3 guardian.py alert-check
```

### Бюджет Claude CLI (как раньше)
```bash
python3 guardian.py status              # Текущий статус вызовов
python3 guardian.py schedule            # Расписание Claude-нагрузки
python3 guardian.py check               # Проверка конфликтов
python3 guardian.py gate                # Gate-check для скриптов
python3 guardian.py log <source>        # Логировать вызов Claude CLI
python3 guardian.py report --days 7     # Отчёт за N дней
python3 guardian.py optimize            # Оптимизация расписания
```

## Лимиты (`data/limits.json`)

| Параметр | Значение | Зачем |
|----------|---------|-------|
| `daily_max_calls` | 100 | Max Claude CLI вызовов в день |
| `hourly_max_calls` | 12 | Max вызовов Claude в час |
| `min_interval_seconds` | 60 | Min интервал между Claude вызовами |
| `reserved_for_interactive` | 20 | Резерв для ручной работы |
| `max_total_crons` | 80 | Макс. слотов в реестре |
| `min_interval_minutes` | 2 | Мин. интервал между кронами |
| `max_per_hour` | 8 | Макс. кронов в одном часу |
| `alert_threshold_pct` | 75 | TG-уведомление при заполнении (%) |
| `alert_critical_pct` | 90 | Критическое TG-уведомление (%) |

## Приоритеты

| Приоритет | Можно двигать? | Примеры |
|-----------|---------------|---------|
| `client` | ⛔ НЕТ | victoria-intention, yulia-reflect |
| `system` | ✅ ДА | night-orchestrator, channel-autopilot |
| `optional` | ✅ ДА, можно отключить | reminders, digests |

## Интеграция с ботами

Бот запрашивает свободный слот перед установкой напоминания:
```python
import subprocess, json
result = subprocess.run(
    ["python3", "/root/Antigravity/.agent/skills/cron-guardian/guardian.py",
     "slot-find", time_utc],
    capture_output=True, text=True, timeout=10
)
# Парсим ответ: "✅ Свободный слот: HH:MM ..."
```

Если время занято → guardian предложит ближайшее свободное.

## TG-алерты

| Порог | Сообщение |
|-------|----------|
| 75% | `⚠️ Cron slots: X/80 (75%). Осталось N.` |
| 90% | `🔴 CRITICAL: X/80. Новые задачи заблокированы!` |

Отправляются в Избранное Дмитрия (`tg-send.py me`). Дедупликация: макс 1 алерт уровня в день.

## Anti-Patterns

| Не делай | Почему | Делай вместо |
|----------|--------|-------------|
| Добавлять крон без `register` | Не попадёт в реестр | `guardian.py register --apply` |
| Ставить 3+ задачи на один час | Скопление → конфликт | `slot-find` выберет свободный |
| Двигать client-задачи | Клиент привык к расписанию | Двигать только system/optional |
| Добавлять таймер без gate-check | Может превысить Claude лимит | Оборачивать в `gate` |
| Игнорировать alert-check | Незаметно набегут кроны | Ежедневный крон `alert-check` |

## Файлы

| Файл | Назначение |
|------|-----------|
| `SKILL.md` | Этот файл |
| `guardian.py` | Движок (CLI) — все 13 команд |
| `data/limits.json` | Настраиваемые лимиты |
| `data/cron-registry.json` | Реестр всех кронов (автогенерация) |
| `data/claude_usage.jsonl` | Лог Claude CLI (append-only) |
| `data/alerts_sent.json` | Дедупликация алертов |

---

## Changelog

<!-- Сюда автоматически добавляются уроки после каждого использования скилла -->
