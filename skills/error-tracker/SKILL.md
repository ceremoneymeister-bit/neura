---
name: error-tracker
description: "Автосборщик и агрегатор ошибок со всех источников (journalctl, Docker, cron logs). Находит повторяющиеся паттерны ошибок и предлагает фиксы. Триггеры: 'какие ошибки', 'что сломалось', 'error report', 'паттерны ошибок', cron ежедневно."
version: 1.0.0
author: Dmitry Rostovtsev (ceremoneymeister)
created: 2026-03-25
updated: 2026-03-25
category: infrastructure
tags: [errors, debugging, monitoring, proactive, self-healing]
risk: safe
source: internal
proactive_enabled: true
proactive_trigger_1_type: schedule
proactive_trigger_1_condition: "ежедневно 21:00"
proactive_trigger_1_action: "агрегировать ошибки из journalctl + Docker + cron"
proactive_trigger_2_type: threshold
proactive_trigger_2_condition: "critical errors > 0"
proactive_trigger_2_action: "немедленный алерт"
learning_track_success: true
learning_track_corrections: true
learning_evolve_threshold: 3
learning_auto_update: [anti-patterns, triggers, changelog]
---

# Error Tracker — сборщик и агрегатор ошибок

## Назначение

Единый пункт сбора ошибок со всех источников: systemd сервисы, Docker, cron логи. Агрегирует, классифицирует, находит повторяющиеся паттерны. Вместо "разбирайся в journalctl сам" — один отчёт "вот 5 ошибок, которые повторяются чаще всего".

## Когда использовать

**Автоматически:**
- Cron: ежедневно в 21:00 — `collector.py report --hours 24`
- Ночные сессии: перед задачами — `collector.py report --hours 12`

**По запросу:**
- "какие ошибки за сегодня?", "error report"
- "что сломалось?", "какие баги повторяются?"
- "паттерны ошибок", "top ошибок"

## Источники

| Источник | Что собирает | Как |
|----------|-------------|-----|
| systemd (6 сервисов) | victoria-bot, nagrada-bot, cm-listener, neura-app-bridge, webchat, hq-bot | `journalctl -u <service>` |
| Docker | yulia-gudymo-bot | `docker logs` |
| Cron logs | reminders, tasks-sync, autopilot, oauth-reminder | Чтение файлов из `logs/` |
| TMP logs | Марина посты, sync-tasks | `/tmp/*.log` |

## Классификация ошибок

| Категория | Иконка | Примеры |
|-----------|--------|---------|
| error | ❌ | Exception, Traceback, Failed |
| timeout | ⏱ | Timeout, Timed out |
| crash | 💀 | OOM, SIGKILL, SIGTERM |
| auth | 🔐 | Permission denied, 401, 403 |
| connection | 🔌 | Connection refused/reset |
| lock | 🔒 | Database locked, sqlite lock |
| rate_limit | 🚫 | 429, Too many requests, hit limit |
| conflict | ⚡ | 409, Already in use |
| not_found | ❓ | 404, No such file |
| disk | 💾 | No space, ENOSPC |

## CLI

```bash
# Собрать ошибки за 24ч и сохранить
python3 collector.py collect --hours 24 --save

# Отчёт (собрать + показать)
python3 collector.py report --hours 24

# Найти повторяющиеся паттерны (≥3 раз)
python3 collector.py patterns --min-count 3

# Топ-10 ошибок за всё время
python3 collector.py top --limit 10
```

## Core Workflow

### 1. Ежедневный сбор (cron 21:00)

```bash
# Добавить в crontab:
0 21 * * * python3 /root/Antigravity/.agent/skills/error-tracker/collector.py collect --hours 24 --save >> /root/Antigravity/logs/error-tracker.log 2>&1
```

### 2. Отчёт по запросу

```
python3 collector.py report --hours 24
```

Выводит:
```
📊 Error Report — 15 ошибок за 24ч

По категориям:
  🚫 rate_limit: 6
  ⏱ timeout: 4
  🔌 connection: 3
  ❌ error: 2

По источникам:
  systemd:victoria-bot: 8
  docker:yulia-gudymo-bot: 4
  log:autopilot.log: 3

Топ-5 уникальных ошибок:
  [6x] (systemd:victoria-bot) You've hit your limit
  [4x] (docker:yulia-gudymo-bot) Connection reset by peer
  ...
```

### 3. Поиск паттернов

```
python3 collector.py patterns --min-count 3
```

Находит ошибки, которые повторяются 3+ раз за всё время → это кандидаты на системный фикс.

### 4. Реакция на паттерны

Когда найден повторяющийся паттерн:

| Категория | Автодействие | Ручное действие |
|-----------|-------------|----------------|
| rate_limit | Увеличить интервал cron | Проверить подписку |
| timeout | Увеличить CLAUDE_TIMEOUT | Проверить нагрузку сервера |
| crash (OOM) | Увеличить cgroup MemoryMax | Оптимизировать бота |
| lock | Проверить параллельные процессы | Добавить retry с backoff |
| connection | Проверить DNS/firewall | Добавить retry |
| conflict | Убить дубликат процесса | Проверить systemd + Telethon сессии |

## Дедупликация

Ошибки нормализуются перед сохранением:
- Убираются timestamps → `<TIME>`
- Убираются hex/UUID → `<ID>`
- Убираются большие числа → `<NUM>`
- Убираются пути → `<FILE>.py`

Это позволяет считать "одинаковые" ошибки с разными timestamp как один паттерн.

## Anti-Patterns

| Не делай | Почему | Делай вместо |
|----------|--------|-------------|
| Читать journalctl вручную | Долго, нет агрегации | `collector.py report` |
| Фиксить каждую ошибку по одной | Не масштабируется | Сначала `patterns` → фиксить системно |
| Игнорировать rate_limit | Подписка может заблокироваться | Уменьшить частоту cron/таймеров |
| Хранить ошибки бесконечно | Файл растёт | Ротация: `errors.jsonl` > 10MB → архивировать |

## Файлы

| Файл | Назначение |
|------|-----------|
| `SKILL.md` | Этот файл |
| `collector.py` | Движок сбора и агрегации (CLI) |
| `data/errors.jsonl` | Все собранные ошибки (append-only) |
| `data/error_patterns.json` | Повторяющиеся паттерны |

---

## Changelog

<!-- Сюда автоматически добавляются уроки после каждого использования скилла -->
