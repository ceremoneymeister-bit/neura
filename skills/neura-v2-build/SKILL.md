---
name: neura-v2-build
description: Workflow для строительства Neura Platform v2 — от проектирования до деплоя. Предотвращение галлюцинаций через TDD + verification gates + hooks.
version: 1.0.0
author: Дмитрий Ростовцев + Claude Code
created: 2026-04-01
category: meta
tags: [architecture, build, workflow, tdd, verification]
risk: high
maturity: seed
---

# Neura v2 Build Workflow

## Purpose
Системный процесс строительства Neura Platform v2, который **гарантирует** качество на каждом шаге. Ни один модуль не считается готовым без прохождения всех gates.

## When to Use
- Начало работы над любой фазой Neura v2 (Phase 0-6)
- Создание нового модуля платформы
- Рефакторинг существующего модуля

## Архитектура workflow

```
                    ┌──────────────┐
                    │ GATE 0       │
                    │ Контекст     │
                    │ (прочитай    │
                    │  ARCHITECTURE│
                    │  .md)        │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ GATE 1       │
                    │ Проектирование│
                    │ (/plan mode) │
                    │              │
                    │ → spec.md    │
                    │ → Дмитрий ✓  │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ GATE 2       │
                    │ Контракт     │
                    │ (тесты ПЕРЕД │
                    │  кодом — TDD)│
                    │              │
                    │ → tests pass │
                    │   RED ✓      │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ GATE 3       │
                    │ Реализация   │
                    │ (код, чтобы  │
                    │  тесты стали │
                    │  GREEN)      │
                    │              │
                    │ → tests pass │
                    │   GREEN ✓    │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ GATE 4       │
                    │ Верификация  │
                    │ (smoke test +│
                    │  integration)│
                    │              │
                    │ → evidence ✓ │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ GATE 5       │
                    │ Review       │
                    │ (Дмитрий     │
                    │  проверяет)  │
                    │              │
                    │ → одобрено ✓ │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ GATE 6       │
                    │ Commit +     │
                    │ Next module  │
                    └──────────────┘
```

---

## Workflow (пошагово)

### GATE 0: Контекст загрузки
**Цель:** Не начинать вслепую. Загрузить всё что нужно.

```
1. Прочитай docs/neura-v2/ARCHITECTURE.md
2. Прочитай docs/neura-v2/MIGRATION_PLAN.md (текущая фаза)
3. Прочитай docs/neura-v2/PROGRESS.md (что уже сделано)
4. Определи: какой МОДУЛЬ строим сейчас?
5. Покажи одной строкой:
   📍 Phase [N] → Модуль: [название] → Файлы: [список]
```

**Антипаттерн:** Начать писать код без чтения архитектуры. ЗАПРЕЩЕНО.

---

### GATE 1: Проектирование (Plan Mode)

**Цель:** Спроектировать модуль ДО написания кода.

```
1. /plan — войти в режим планирования
2. Исследовать:
   - Какие модули v1 переиспользуем? (пути, строки)
   - Какие интерфейсы у соседних модулей?
   - Какие edge cases?
3. Создать spec:
   docs/neura-v2/specs/[module-name].md
   Формат:
   - ## Назначение (1-2 предложения)
   - ## Интерфейс (функции/классы, входы/выходы)
   - ## Зависимости (какие модули использует)
   - ## Edge Cases (что может пойти не так)
   - ## Тест-кейсы (что проверяем)
4. Показать Дмитрию → одобрение
```

**Антипаттерн:** "Я и так знаю как делать" → ВСЕГДА spec сначала.

**Выход gate:** Файл `specs/[module].md` существует + одобрение Дмитрия.

---

### GATE 2: Контракт (TDD — Red Phase)

**Цель:** Написать тесты ПЕРЕД кодом. Тесты = контракт модуля.

```
1. Создать файл теста: tests/test_[module].py
2. Написать тесты по spec:
   - Каждый тест-кейс из spec → один test_*
   - Happy path + error cases + edge cases
   - Минимум 3 теста на модуль
3. Запустить тесты:
   cd /opt/neura-v2 && python3 -m pytest tests/test_[module].py -v
4. УБЕДИТЬСЯ ЧТО ВСЕ ТЕСТЫ КРАСНЫЕ (FAIL)
   Если тесты зелёные без кода → тесты НЕПРАВИЛЬНЫЕ
5. Показать вывод pytest (evidence)
```

**Антипаттерн:** Писать тесты после кода. ЗАПРЕЩЕНО в этом workflow.

**Выход gate:** `pytest` показывает N FAILED, 0 PASSED.

---

### GATE 3: Реализация (Green Phase)

**Цель:** Написать МИНИМАЛЬНЫЙ код, чтобы тесты стали зелёными.

```
1. Реализовать модуль: neura/[path]/[module].py
2. Переиспользовать код из v1 где возможно (указать откуда)
3. НЕ добавлять лишнего — только то, что нужно для тестов
4. Запустить тесты:
   python3 -m pytest tests/test_[module].py -v
5. ВСЕ ТЕСТЫ ЗЕЛЁНЫЕ?
   - Да → переходим к Gate 4
   - Нет → фиксим КОД (не тесты!), повторяем
6. Показать вывод pytest (evidence)
```

**Антипаттерн:** Менять тесты чтобы они прошли. ЗАПРЕЩЕНО.

**Выход gate:** `pytest` показывает N PASSED, 0 FAILED.

---

### GATE 4: Верификация (Evidence-based)

**Цель:** Доказать что модуль работает В РЕАЛЬНЫХ УСЛОВИЯХ, не только в тестах.

```
1. Smoke test (если применимо):
   python3 scripts/smoke_test.py --module [module]
   
2. Integration check:
   - Модуль импортируется без ошибок?
   - Модуль работает с соседними модулями?
   - Docker-контейнер стартует?
   
3. Ручная проверка:
   python3 -c "from neura.[path] import [Class]; print([Class].__doc__)"
   
4. Заполнить чеклист верификации:
   □ Тесты зелёные (pytest output)
   □ Импорт работает
   □ Нет hardcoded путей/токенов
   □ Нет TODO/FIXME в новом коде
   □ Код < 300 строк (если больше — разбить)
   □ Docstring на публичных функциях
```

**Антипаттерн:** "Должно работать" → НЕТ. Покажи ВЫВОД команды.

**Выход gate:** Чеклист заполнен + evidence (вывод команд).

---

### GATE 5: Review (Дмитрий)

**Цель:** Дмитрий видит что сделано и одобряет.

```
1. Показать краткий отчёт:
   
   ## Модуль: [название]
   - Файлы: [список]
   - Тесты: [N passed, 0 failed]
   - Строк кода: [N]
   - Переиспользовано из v1: [что и откуда]
   - Edge cases: [покрыты / нет]
   
2. Показать diff (что изменилось)
3. Ждать одобрения Дмитрия
```

**Выход gate:** Дмитрий сказал "ОК" / одобрил.

---

### GATE 6: Commit + Progress

**Цель:** Зафиксировать результат и обновить прогресс.

```
1. git add [конкретные файлы]
2. git commit -m "neura-v2: [module] — [что сделано]"
3. Обновить docs/neura-v2/PROGRESS.md:
   - [x] Phase N: Module — описание (дата)
4. Обновить SESSION_LOG.md
5. Переход к следующему модулю → GATE 0
```

---

## Параллельная работа (Agent Teams)

Для фаз с независимыми модулями — Agent Teams:

```
Создай команду из 3 агентов:
- Agent A: core/engine.py (Claude CLI wrapper)
- Agent B: core/memory.py (Memory system)  
- Agent C: tests/ (тесты для обоих модулей)

Правила:
- Каждый агент ОБЯЗАН пройти Gates 2-4
- Агент C пишет тесты ПЕРВЫМ (Gate 2)
- Агенты A и B реализуют КОД (Gate 3)
- Никто не трогает файлы другого агента
```

---

## Hooks (автоматические проверки)

### Hook 1: PreToolUse — защита v2 файлов
Блокирует случайное редактирование v1 файлов при работе над v2:
```
При работе в /opt/neura-v2/:
- НЕ редактировать /srv/capsules/
- НЕ редактировать /opt/neura-app/
- НЕ редактировать neura-capsule/bot/
```

### Hook 2: PostToolUse — авто-pytest
После КАЖДОГО Edit/Write в `/opt/neura-v2/neura/`:
```
Автоматически запустить pytest для изменённого модуля.
Если тесты падают → показать warning.
```

### Hook 3: Stop — verification gate
Перед завершением работы над модулем:
```
Проверить:
1. Все тесты зелёные?
2. PROGRESS.md обновлён?
3. Spec файл существует?
Если нет → блокировать завершение.
```

---

## Anti-patterns (ЗАПРЕЩЕНО)

| # | Антипаттерн | Почему опасно | Что делать вместо |
|---|-------------|---------------|-------------------|
| 1 | Писать код без spec | Галлюцинация архитектуры | Gate 1: spec → одобрение |
| 2 | Писать тесты после кода | Тесты подстраиваются под баги | Gate 2: тесты ПЕРВЫМИ |
| 3 | "Должно работать" | 48% времени на дебаг в v1 | Gate 4: evidence-based |
| 4 | Менять тест чтобы прошёл | Маскировка бага | Фиксить КОД, не тест |
| 5 | Пропустить Gate | "Этот модуль простой" | НИКАКИХ исключений |
| 6 | Писать >300 строк за раз | Необозримый diff | Разбить на подмодули |
| 7 | Редактировать v1 при работе v2 | Сломать текущих клиентов | Изолированная директория |
| 8 | Начать без /plan | Не понял задачу | ВСЕГДА /plan сначала |

---

## Progress tracking

Файл `docs/neura-v2/PROGRESS.md` — единственный источник правды:

```markdown
# Neura v2 — Progress

## Phase 0: Foundation
- [ ] core/engine.py — Claude CLI wrapper
- [ ] core/capsule.py — Capsule runtime
- [ ] core/context.py — Prompt assembly
- [ ] core/memory.py — Memory CRUD (PostgreSQL)
- [ ] core/skills.py — Skill loader
- [ ] core/queue.py — Request queue (Redis)
- [ ] storage/db.py — PostgreSQL connection
- [ ] storage/migrations/001_initial.sql — DB schema
- [ ] scripts/migrate_data.py — v1 → v2 migration
- [ ] Docker Compose (postgres, redis)
- [ ] Тесты для каждого модуля

## Phase 1: Telegram + Никита
- [ ] transport/telegram.py — TG adapter
- [ ] config/capsules/nikita.yaml — First capsule
- [ ] Миграция данных Никиты
- [ ] Smoke test
- [ ] 24ч мониторинг

... (Phase 2-6)
```

---

## Быстрый старт

```
Дмитрий: "Начинаем Phase 0, модуль core/engine.py"

Claude:
📍 Phase 0 → Модуль: core/engine.py → Файлы: neura/core/engine.py, tests/test_engine.py

[Gate 0] ✅ Контекст загружен (ARCHITECTURE.md, MIGRATION_PLAN.md)
[Gate 1] Вхожу в /plan...
         → Создаю spec: docs/neura-v2/specs/core-engine.md
         → [Показываю Дмитрию]
[Gate 2] Пишу тесты: tests/test_engine.py
         → pytest: 5 FAILED, 0 PASSED ✅ (Red phase)
[Gate 3] Реализую: neura/core/engine.py
         → pytest: 5 PASSED, 0 FAILED ✅ (Green phase)
[Gate 4] Верификация:
         □ ✅ Тесты зелёные
         □ ✅ Импорт работает
         □ ✅ Нет hardcoded
         □ ✅ < 300 строк
[Gate 5] [Показываю Дмитрию отчёт]
[Gate 6] git commit + PROGRESS.md обновлён
```
