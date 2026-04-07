---
name: night-session
description: "Night Orchestrator v3: 10-часовая сессия с 3 параллельными агентами, auto-discovery, semantic validation, circuit breaker, resource guard, skill rotation, weekly digest"
version: 3.1.0
author: Dmitry Rostovtsev (ceremoneymeister)
created: 2026-03-20
updated: 2026-03-22
category: meta
tags: [night, autonomous, orchestrator, parallel, validation, resilience, intelligence]
risk: safe
source: internal
proactive_enabled: true
proactive_trigger_1_type: event
proactive_trigger_1_condition: "NIGHT_TASKS.md обновлён"
proactive_trigger_1_action: "запустить ночной оркестратор"
learning_track_success: true
learning_track_corrections: true
learning_evolve_threshold: 5
learning_auto_update: [anti-patterns, triggers, changelog]
---

# night-session — Night Orchestrator v3

## Architecture

```
systemd timer 20:00 UTC → night-orchestrator.py (10 часов)
  ├── resource guard (disk/memory/load check)
  ├── auth health check (3 retries × 5 min)
  ├── load task queue (night-tasks-generator.py v2)
  │   ├── NIGHT_TASKS.md (manual, highest priority)
  │   ├── templates with variable substitution
  │   │   ├── {bot_name} → expands to Victoria/Marina/Yulia
  │   │   ├── {user_name} → expands to all users
  │   │   └── {skill_name} → rotation (next skill each night)
  │   ├── HANDOFF.md ([ночь] tagged items)
  │   └── auto-discovery
  │       ├── journalctl error scanner (3+ errors → fix task)
  │       ├── deadline watcher (≤2 days → priority boost)
  │       └── disk usage monitor (≥80% → cleanup task)
  ├── circuit breaker (3 fails → 15min pause)
  ├── ThreadPoolExecutor(max_workers=3)
  │   ├── agent-1: claude -p (задача A)
  │   ├── agent-2: claude -p (задача B)
  │   └── agent-3: claude -p (задача C)
  ├── per-task validation
  │   ├── file-based (exists, size, modified)
  │   └── semantic (claude scores 1-10, retry if <5)
  ├── per-task HQ report (verified {"ok":true})
  ├── task history tracking (adaptive priority)
  ├── weekly digest (Mondays, PDF)
  └── final summary PDF → HQ thread 962
```

## What's New in v3

| Feature | v2 | v3 |
|---------|----|----|
| Template variables | Raw `{placeholders}` | Auto-resolved (bot/user/skill rosters) |
| Task sources | 3 (manual, templates, handoff) | 4 (+auto-discovery) |
| Auto-discovery | — | journalctl errors, deadlines, disk |
| Validation | file-based only | + semantic (Claude score 1-10) |
| Resilience | — | circuit breaker + resource guard |
| Priority | Static | Adaptive (learns from history) |
| Skill improvement | Manual | Auto-rotation (next skill each night) |
| Digest | Per-session only | + weekly digest (Mondays) |

## When to Use

- Подготовка ночных задач: добавь в `NIGHT_TASKS.md`
- Мониторинг: `systemctl status night-orchestrator.timer`
- Ручной запуск: `python3 scripts/night-orchestrator.py --test --max-tasks 3`
- Dry-run: `python3 scripts/night-orchestrator.py --dry-run`
- Генератор: `python3 scripts/night-tasks-generator.py --dry-run`

## Files

| Файл | Назначение |
|------|-----------|
| `scripts/night-orchestrator.py` | Главный оркестратор |
| `scripts/night-tasks-generator.py` | Генератор очереди v2 (с auto-discovery) |
| `.agent/skills/night-session/config/night-config.yaml` | Конфигурация |
| `.agent/skills/night-session/config/task-templates.yaml` | Шаблоны задач (~10) |
| `.agent/skills/night-session/config/skill-rotation.json` | Состояние ротации скиллов |
| `logs/night/task-history.json` | История задач (для adaptive priority) |
| `/etc/systemd/system/night-orchestrator.service` | Systemd сервис |
| `/etc/systemd/system/night-orchestrator.timer` | Таймер на 20:00 UTC |
| `scripts/night-agent-legacy.sh` | Старый bash-скрипт (архив) |

## Task Queue

Задачи собираются из 4 источников:
1. **NIGHT_TASKS.md** — ручные задачи с `[ ]` (приоритет)
2. **Шаблоны** — автоматические с подстановкой переменных
3. **HANDOFF.md** — задачи с меткой `[ночь]`
4. **Auto-discovery** — автоматически обнаруженные проблемы

## Auto-Discovery Scanners

| Scanner | Что проверяет | Когда генерирует задачу |
|---------|--------------|----------------------|
| Service errors | journalctl -p err за 12ч | 3+ ошибок у сервиса |
| Docker errors | docker logs --since 12h | 3+ error/exception/traceback |
| Deadline watcher | Даты в HANDOFF/NIGHT_TASKS | ≤2 дней до дедлайна |
| Disk monitor | df / | ≥80% заполнено |

## Resilience

| Механизм | Описание |
|----------|---------|
| Circuit breaker | 3 задачи подряд failed → пауза 15 мин → 1 retry → abort |
| Resource guard | Проверка disk/memory/load перед каждой задачей |
| Semantic validation | Claude оценивает результат 1-10, retry если <5 |
| Adaptive priority | Задачи с 3+ последовательных fails → понижение приоритета |

## Commands

```bash
# Dry-run: посмотреть очередь
python3 scripts/night-orchestrator.py --dry-run

# Генератор задач (с auto-discovery)
python3 scripts/night-tasks-generator.py --dry-run
python3 scripts/night-tasks-generator.py --no-auto --dry-run

# Тест: 3 задачи, окно 10 мин
python3 scripts/night-orchestrator.py --test --window-minutes 10 --max-tasks 3

# Полный запуск
python3 scripts/night-orchestrator.py

# Управление таймером
systemctl status night-orchestrator.timer
systemctl start night-orchestrator.service
journalctl -u night-orchestrator.service -f
```

## ⛔ Safety

| Действие | Разрешено? |
|----------|-----------|
| Отправка клиентам/пользователям | ⛔ НЕТ |
| Отправка в HQ "Ночные сессии" | ✅ ДА |
| git push | ⛔ НЕТ |
| Сервер Максима (45.11.93.179) | ⛔ НЕТ |
| sshpass | ⛔ НЕТ |
| Создание/изменение файлов | ✅ ДА |
| Запуск сервисов | ✅ ДА |
| Веб-ресёрч | ✅ ДА |

## Task Quality Gate (ОБЯЗАТЕЛЬНО при написании NIGHT_TASKS.md)

Перед добавлением задачи в NIGHT_TASKS.md — проверь по чеклисту. Если задача не проходит 4+ из 6 — переписать.

### Чеклист сильной задачи

| # | Критерий | ❌ Слабо | ✅ Сильно |
|---|----------|---------|----------|
| 1 | **Артефакт** | "исследуй и напиши отчёт" | "создай скрипт `scripts/X.py` + тест + результат в `/tmp/X.md`" |
| 2 | **Конкретность** | "проверь что всё работает" | "запусти `curl https://api.X.com`, сохрани latency, сравни с вчера" |
| 3 | **Реальные данные** | "создай 5 тестовых промптов" | "возьми 5 промптов из `logs/conversations/2026-03-21.md`" |
| 4 | **Зависимости** | задача 4 нуждается в результате задачи 7 | зависимости указаны: `depends_on: task_7` |
| 5 | **Валидация** | "проверь результат" | файл создан + size > 500 bytes + содержит ожидаемые ключевые слова |
| 6 | **Действие, не отчёт** | "напиши план настройки VPN" | "создай `scripts/setup-vpn.sh`, проверь синтаксис, протестируй генерацию ключа" |

### Anti-Patterns (ночной агент НЕ должен)

- ❌ Писать отчёты которые никто не прочитает → вместо отчёта создай рабочий скрипт
- ❌ "Исследуй возможности X" → конкретно: "установи X, протестируй, сохрани результат"
- ❌ Выдумывать тестовые данные → бери реальные из логов/файлов
- ❌ Задачи без валидации → каждая задача = конкретный файл + проверка
- ❌ 15 мелких задач по 5 мин → лучше 6 сильных по 25 мин с глубоким результатом

### Формула сильной задачи

```
ЗАДАЧА = Глагол действия + конкретный артефакт + источник данных + валидация
```

Примеры:
- ✅ "Создай `scripts/block-monitor.py` (проверка 7 API endpoints), запусти, сохрани baseline в `logs/block-monitor/`"
- ✅ "Возьми 10 промптов из `logs/conversations/2026-03-21.md`, прогони через DeepSeek API, сравни с Claude, таблица в `docs/benchmark.md`"
- ❌ "Исследуй как работает DeepSeek и напиши отчёт"

### Стратегическая проактивность

Каждую ночь хотя бы 1 задача должна быть **проактивной** — не реагировать на проблемы, а предотвращать:
- Мониторинг блокировок (ежедневно)
- Тест устойчивости инфраструктуры
- Бэкап критических данных
- Сканирование новых угроз/возможностей

## Multi-Agent Delegation Protocol (MADP)

> Урок 01.04.2026: при раздаче задач 4+ ночным агентам без этого протокола —
> конфликты файлов, поломка сервисов, зависшие npm, неработающие зависимости.

### Когда использовать
- 3+ агентов работают параллельно над ОДНИМ проектом
- Задачи имеют зависимости (backend → frontend → компоненты)
- Агенты создают файлы в общей директории

### Чеклист подготовки задач (7 пунктов)

| # | Проверка | Что делать |
|---|----------|-----------|
| 1 | **Service Protection** | Явно запретить restart/stop/kill ВСЕХ работающих сервисов. Список: `systemctl list-units --state=active \| grep neura` |
| 2 | **Dependency Chain** | Нарисовать граф зависимостей: Agent 1 → 2 → 3. Каждый агент получает fallback: "если файл X не создан — создай заглушку" |
| 3 | **File Isolation** | Каждый агент = своя папка. Перечислить явно: "Agent 2 пишет ТОЛЬКО в `web/src/layout/`, НЕ трогает `web/src/components/chat/`" |
| 4 | **Non-Interactive Commands** | Все CLI команды должны быть неинтерактивными: `echo y \| npm create vite`, `pip install --quiet`, `yes \| ...` |
| 5 | **Standalone Modules** | Новый код = standalone модуль с `if __name__ == "__main__"`. Интеграцию в основной процесс делать ВРУЧНУЮ утром |
| 6 | **Interval Calculation** | Минимум 30 мин между зависимыми агентами. Независимые можно параллельно |
| 7 | **Auditor Agent** | Последний агент ВСЕГДА аудитор: проверяет все результаты, фиксит баги, делает `build` и `pytest` |

### Формула интервала между агентами

```
Independent agents (no deps):     5 min apart
Dependent agents (reads output):  30 min apart
Auditor (checks all):             max(90 min after last builder, 60 min)
```

### Шаблон промпта для night-agent.sh

```bash
PROMPT="Ты — ночной автономный агент. Дмитрий спит.

ЗАДАЧА: [читай NIGHT_TASKS.md → задача N]

КРИТИЧЕСКИЕ ПРАВИЛА:
- ⛔ НЕ перезапускать [список сервисов]
- ⛔ НЕ делать git push
- ⛔ НЕ отправлять клиентам
- ✅ Используй WebSearch для best practices
- ✅ Если файл от предыдущего агента не создан — создай заглушку
- ✅ Будь ПРОАКТИВНЫМ
- ✅ Отправь отчёт в HQ topic 962"
```

### Anti-Patterns делегации

| ❌ Ошибка | ✅ Правильно |
|-----------|-------------|
| "Интегрируй в app.py" (модифицирует running code) | "Создай standalone web.py, интеграцию утром вручную" |
| `npm create vite` (интерактивно) | `echo y \| npm create vite@latest -- --template react-ts` |
| Agent 3 зависит от Agent 2, но стартует через 5 мин | Интервал 30 мин + fallback инструкция |
| "Все тесты должны пройти" (без конкретики) | "pytest tests/test_web.py -xvs && pytest tests/ -x" |
| 4 агента, нет аудитора | Всегда 5-й агент = аудитор (через 90 мин) |

### Прогнозирование результатов

Перед запуском — составь таблицу прогнозов для каждого агента:

| Агент | Ожидаемые файлы | LOC | Уверенность | Главный риск |
|-------|----------------|-----|-------------|-------------|
| 1 | web.py, auth.py, 002.sql | ~800 | 90% | pip install |
| 2 | web/src/ (15+ файлов) | ~600 | 85% | npm interactive |
| ... | ... | ... | ... | ... |

Если уверенность < 70% — переписать спеку или добавить fallback.

## PDF Themes

Ночные отчёты генерируются через `md2pdf.py`. Доступные темы:

| Тема | Флаг | Стиль |
|------|------|-------|
| Notion (по умолчанию) | `--theme notion` | Светлый, #37352F на белом |
| Claude Code | `--theme claude` | Тёмный, оранжевый акцент на #1A1A2E |

Пример: `python3 md2pdf.py --input report.md --output /tmp/report.pdf --theme claude`

## Pre-flight Path Validation (ОБЯЗАТЕЛЬНО при составлении NIGHT_TASKS.md)

**Урок 22.03.2026:** 6 из 13 задач содержали неверные пути — агент бы упал на каждой. Теперь перед добавлением задач ОБЯЗАТЕЛЬНА валидация.

### Чеклист валидации путей

После составления NIGHT_TASKS.md — выполни перед запуском:

```bash
# 1. Извлечь все пути из задач и проверить существование
grep -oP '`[^`]*`' NIGHT_TASKS.md | \
  grep -E '(projects/|/srv/|scripts/|logs/|bot/|agent/|templates/)' | \
  tr -d '`' | sort -u | while read p; do
    if [ -e "$p" ]; then echo "✅ $p"
    else echo "❌ MISSING: $p"; fi
  done
```

### Типичные ошибки путей (из реальных инцидентов)

| Ошибка | Реальный путь | Почему ошиблись |
|--------|--------------|-----------------|
| `Victoria: bot/google_token.json` | **НЕ СУЩЕСТВУЕТ** | Victoria не подключала Google OAuth |
| `Marina: agent/bot/diary/` | `agent/diary/` | diary на уровне agent, не bot |
| `Marina: agent/bot/google_token.json` | `agent/integrations/google_token.json` | token в integrations/ |
| `Yulia: /srv/capsules/.../bot/data/` | `/srv/capsules/.../data/` | data на уровне capsule, не bot |
| `scripts/always_deep.py` | `bot/streaming_executor.py` (в каждом боте) | execute_always_deep встроен в бота, не отдельный файл |

### Реальная структура данных ботов (актуальная на 22.03.2026)

```
# Victoria (projects/Producing/Victoria_Sel/bot/):
memory/
  ├── diary/           → ежедневные логи (## HH:MM [тип] user:ID)
  ├── journal/         → осознания Виктории (### HH:MM свободный текст)
  ├── awareness/       → месячные инсайты
  ├── preferences/     → victoria_prefs.md
  ├── sessions.json    → сессии
  └── context_log.jsonl
streaming_executor.py  → execute_always_deep() :416

# Marina (projects/AI_Business/Marina_Biryukova/agent/):
diary/                 → ежедневные логи (8 файлов)
employees/             → досье сотрудников (3 файла)
integrations/          → google_token.json
bot/
  ├── memory/          → существует, ПУСТАЯ
  ├── .env             → конфиг бота
  └── streaming_executor.py

# Yulia (/srv/capsules/yulia_gudymo/):
data/                  → diary/, employees/, memory/, integrations/
  └── google_token.json
docker-compose.yml     → env конфиг

# Maxim (УДАЛЁННЫЙ — 45.11.93.179):
/root/agent-system/    → код на его сервере
```

### Расположение .env / конфигов ботов

| Бот | Тип конфига | Путь |
|-----|------------|------|
| Victoria | systemd Environment= | `victoria-bot.service` (нет .env файла!) |
| Marina | .env файл | `projects/AI_Business/Marina_Biryukova/agent/bot/.env` |
| Yulia | Docker env | `/srv/capsules/yulia_gudymo/docker-compose.yml` |
| Maxim | удалённый .env | SSH → `45.11.93.179:/root/agent-system/.env` |

### Ключевые API-ключи

| Ключ | Статус | Где |
|------|--------|-----|
| DEEPGRAM_API_KEY | ✅ есть | `/root/Antigravity/.env` |
| DEEPSEEK_API_KEY | ❌ нет | Не настроен — задачи должны skip с сообщением |
| OPENROUTER_API_KEY | ❌ нет | Не настроен — задачи должны skip с сообщением |

### Правило: пиши задачу → проверяй пути → только потом добавляй

1. Написал задачу с путями
2. Для КАЖДОГО пути — `ls -la <путь>` (или `ssh` для удалённых)
3. Если путь не существует — исправь ДО добавления в NIGHT_TASKS.md
4. Если путь может быть создан задачей — пометь `# will be created`
5. Для зависимостей между задачами — укажи `**Зависит от:** Задача N`

## Lessons

- v1: Lock timeout 25 мин → v2: per-agent, 50 мин
- v1: Auth cascade 5.5 часов → v2: 3 retries × 5 мин, abort
- v1: `curl > /dev/null` → v2: JSON response parsing, retry 3x
- v1: 1 агент → v2: ThreadPoolExecutor(3)
- v1: exit=0 = "готово" → v2: file checks → v3: + semantic validation
- v2: static templates → v3: variable substitution + auto-discovery
- v2: no history → v3: adaptive priority from task history
- v2: no resilience → v3: circuit breaker + resource guard
- v3: 22.03 — 6/13 задач с неверными путями → добавлен Pre-flight Path Validation
- v3: 22.03 — Marina diary не в bot/, а в agent/ → задокументирована реальная структура
- v3: 22.03 — Victoria не имеет .env → задокументированы типы конфигов всех ботов
- v3: 22.03 — execute_always_deep не в scripts/, а в streaming_executor.py каждого бота
- v3: 28.03 — ручные задачи не отмечались [✓] автоматически → оркестратор крутил одни и те же задачи. Добавлен `_mark_task_done()` в `_handle_result()`
- v3: 28.03 — шаблоны proactive_message/skill_improvement/content были daily → перерасход токенов. Пересмотрены на weekly/2x_week
- v3: 28.03 — NIGHT_TASKS.md нужно чистить после выполнения всех задач, иначе парсер тратит время на 300+ строк заметок

---

## Changelog

<!-- Сюда автоматически добавляются уроки после каждого использования скилла -->
