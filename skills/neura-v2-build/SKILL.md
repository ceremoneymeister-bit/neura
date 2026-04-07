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
usage_count: 2
last_used: 2026-04-02
proactive_enabled: true
proactive_trigger_1_type: event
proactive_trigger_1_condition: "работа над Neura v2 модулем"
proactive_trigger_1_action: "6 Gates TDD workflow"
learning_track_success: true
learning_track_corrections: true
learning_evolve_threshold: 5
learning_auto_update: [anti-patterns, triggers, changelog]
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
| 9 | Smoke test = "всё работает" | 4 gap найдены после 60/60 smoke | Feature Audit после КАЖДОЙ фазы |
| 10 | nohup вместо systemd | Не переживёт reboot | .service + enable СРАЗУ |
| 11 | Hardcoded пути (/root/Antigravity/) | Не портативно | ${NEURA_BASE} + env vars |
| 12 | FK insert без проверки parent | migrate_data.py crash | Сначала INSERT parent, потом child |
| 13 | Migrate без cwd fix | Claude не видит assets | cwd=home_dir в engine.py |
| 14 | Standalone web.py на отдельном порту | Два процесса, сложнее управлять | Интегрировать в app.py через uvicorn.Server + asyncio.create_task |
| 15 | VITE_API_URL с абсолютным URL | Ломается при смене домена | Пустой VITE_API_URL → relative paths (клиент на том же домене) |
| 16 | UI без Agent Teams | Один агент = последовательно, долго | 2+ UI-агента на разные файлы (layout vs components) параллельно |
| 17 | Перехват только в _handle_text | Voice/photo/doc обходят онбординг | Онбординг-intercept во ВСЕХ handler'ах (text+voice+photo+doc) |
| 18 | StringSession для Telethon auth | TCP disconnect → auth_key теряется → PhoneCodeExpired | Файловая сессия (SQLite) — auth_key переживает reconnect |
| 19 | Не удалять stale .session перед retry | Старый auth_key конфликтует с новым send_code | _delete_stale_session() ПЕРЕД каждой новой попыткой |
| 20 | Phone code как единственный метод auth | Rate limit 5/day, TCP disconnect | QR Login (primary) + Phone Code (fallback) |
| 21 | Diary truncation 500 символов | Бот "не помнит" длинные сообщения | Минимум 2000 символов для user_message и bot_response |
| 22 | Phase 6 как gate (не auto-complete) | Пользователь застревает в resume loop | Phase 6 = авто-complete при показе, кнопка для UX |

---

## Post-Migration Checklist (ОБЯЗАТЕЛЬНО после каждой миграции/фазы)

> Урок 01.04.2026: после Phase 2 (миграция капсул) smoke test прошёл 60/60,
> но 4 критических gap обнаружились только при аудите функциональной полноты.

### Smoke test ≠ Feature completeness

Smoke test проверяет: "пайплайн работает" (capsule loads → engine responds).
Feature completeness проверяет: "пользователь может делать ВСЁ что мог раньше".

**После КАЖДОЙ миграции/фазы — запусти Feature Audit:**

```
1. Working directory: cwd=home_dir в subprocess? Claude может читать локальные файлы?
2. Assets: knowledge/, employees/, data/, skills/ скопированы в новое расположение?
3. Skills injection: скиллы из YAML конфига попадают в промпт Claude?
4. Employee context: для мульти-user ботов — досье грузится per-user?
5. File markers: [FILE:/tmp/path] → файл отправляется?
6. Telegraph: длинные ответы > 4000 → Telegraph page?
7. Voice: транскрибация работает?
8. Persistence: systemd service создан + enabled? old services disabled?
9. Портативность: все пути через env/config, не hardcoded?
10. Мониторинг: health checks + алерты настроены?
```

### systemd — создавай СРАЗУ

| ❌ Как было | ✅ Как надо |
|-------------|-----------|
| Запустить через nohup, потом на аудите обнаружить | Сразу создать .service + enable |
| v1 services остаются enabled | `systemctl disable` всех v1 сервисов |

### Портативность — по умолчанию

Все пути через:
- `${NEURA_BASE}` в SYSTEM.md (подставляется в capsule.py)
- `NEURA_SKILLS_DIR` env var (default: `./skills/`)
- `NEURA_HOMES_DIR` env var (default: `./homes/`)
- Относительные пути в engine.py (`cwd=home_dir`)

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

---

## Changelog

<!-- Сюда автоматически добавляются уроки после каждого использования скилла -->

### 2026-04-01 — создание скилла + Phase 0 (9 модулей, 98 тестов)
- 6 Gates workflow: spec→TDD→implement→verify→review→commit. 3 хук-скрипта
- Phase 0: 9 модулей за 1 сессию (engine 268 LOC, capsule 192, context 105, memory 195, db 68, cache+queue, skills 106, migrate_data 185)
- Deep verify нашёл баги в 3 модулях: memory (DATE/TIME types), cache (3 бага), skills (pipe escaping)
- CRITICAL: v1 enabled одновременно с v2 → конфликт. neura-v2.service создан
- Урок: Gate 4 (deep verification) ловит баги, которые unit-тесты пропускают. Explore agent должен проверять spec vs код vs arch
- Тайминг: ~200 LOC модуль + 6 Gates = ~30 мин (бенчмарк)

### 2026-04-02 — Phase 1-5 + миграция + 12 антипаттернов
- Phase 1 (Telegram): 66 тестов, 803 LOC. Phase 3 (Web): 3 параллельных агента, 227 тестов
- Phase 5 (Deploy): uvicorn+Telegram одним процессом, LibreChat остановлен
- Migration: 507 diary + 102 memory + 60 learnings → PostgreSQL
- Feature Audit нашёл 4 critical gap (cwd, assets, skills injection, employee context)
- Антипаттерн: nohup вместо systemd — не переживёт reboot. Создавать .service СРАЗУ
- Антипаттерн: hardcoded пути — использовать ${NEURA_BASE} + env vars
- Антипаттерн: standalone web.py на порту — интегрировать в app.py через uvicorn.Server
- Антипаттерн: StringSession для Telethon → auth_key теряется. Файловая сессия (SQLite)
- Антипаттерн: diary truncation 500 символов → бот "не помнит". Минимум 2000
- Урок: Smoke test ≠ Feature completeness. Feature Audit ОБЯЗАТЕЛЕН после каждой фазы
- Урок: Agent Teams (3-5) ускоряют Web UI кратно, но каждый агент ОБЯЗАН пройти Gates 2-4
