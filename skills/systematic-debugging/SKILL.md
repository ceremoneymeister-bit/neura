---
name: systematic-debugging
description: Use when encountering any bug, bot error, test failure, or unexpected behavior. Includes proactive bot error forensics — automatically investigates time, topic, message, logs, and root cause before proposing fixes.
version: 2.0.0
author: Dmitry Rostovtsev (ceremoneymeister)
created: 2025-02-01
updated: 2026-03-19
category: development
tags: [debugging, root-cause, proactive, bot-forensics, auto-healing]
risk: safe
source: internal
usage_count: 2
last_used: 2026-03-31
maturity: seed
proactive_enabled: true
proactive_trigger_1_type: threshold
proactive_trigger_1_condition: "errors_today > 5 в journalctl/Docker"
proactive_trigger_1_action: "запустить проактивную форензику"
proactive_trigger_2_type: event
proactive_trigger_2_condition: "бот не отвечает > 5 мин"
proactive_trigger_2_action: "автоматическая диагностика"
learning_track_success: true
learning_track_corrections: true
learning_evolve_threshold: 3
learning_auto_update: [anti-patterns, triggers, changelog]
---

# Systematic Debugging v2 — Proactive Forensics

## Overview

Random fixes waste time and create new bugs. Quick patches mask underlying issues.

**Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.

**v2 addition:** При ошибке бота — НЕ жди команды. Проактивно расследуй: время, топик, сообщение, логи, причину. Построй план фикса и предложи его.

## Proactivity Scale

Каждое расследование выполняется на одном из уровней проактивности:

| Уровень | Название | Поведение |
|---------|----------|-----------|
| **0.8** | Пассивный | Жди команды. Показывай только запрошенное |
| **1.0** | Стандартный | Расследуй по запросу. Покажи факты + 1 рекомендацию |
| **1.2** | Проактивный | Сам начинай расследование при ошибке. Покажи факты + план фикса + предложи действия |
| **1.5** | Агрессивный | Расследуй + построй план + начни выполнять безопасные шаги (чтение логов, поиск в коде) |
| **2.2** | Автономный | Полный цикл: расследовал → нашёл причину → написал фикс → показал diff → жди одобрения на деплой |

**По умолчанию:** 1.2 для ошибок ботов. 1.0 для общих багов. Пользователь может запросить другой уровень.

## The Iron Law

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

If you haven't completed Phase 1, you cannot propose fixes.

---

## Phase 0: Bot Error Forensics (Proactive, ≥1.2)

**Триггер:** Ошибка бота, "техническая ошибка", сообщение от пользователя о сбое, rc≠0 в логах.

При обнаружении ошибки бота — НЕМЕДЛЕННО выполни эти шаги:

### 0.1 Определи время и контекст

```bash
# 1. Логи сервиса — последние ошибки
journalctl -u {SERVICE} --since "1 hour ago" --no-pager | grep -i "error\|exception\|killed\|signal\|rc=" | tail -20

# 2. Время последнего рестарта
systemctl show {SERVICE} -p ActiveEnterTimestamp,ExecMainStartTimestamp

# 3. safe-restart лог (если был рестарт)
cat /tmp/safe-restart-{SERVICE}.log 2>/dev/null
```

### 0.2 Найди сообщение и топик

```bash
# Через Bot API — последние сообщения в HQ-группе
python3 -c "
import requests
token = '{BOT_TOKEN}'
# getUpdates покажет последние сообщения
resp = requests.get(f'https://api.telegram.org/bot{token}/getUpdates', params={'offset': -20})
for u in resp.json().get('result', []):
    msg = u.get('message', {})
    date = msg.get('date', 0)
    thread = msg.get('message_thread_id', 'DM')
    text = (msg.get('text') or msg.get('voice', {}).get('file_id', 'voice') or '')[:50]
    user = msg.get('from', {}).get('first_name', '?')
    print(f'{date} | topic={thread} | {user}: {text}')
"
```

### 0.3 Определи тип ошибки

| Сигнал / RC | Значение | Действие |
|-------------|----------|----------|
| rc=143, -15 (SIGTERM) | Процесс убит gracefully | safe-restart во время обработки → улучшить safe-restart |
| rc=137, -9 (SIGKILL) | Процесс убит принудительно | OOM или systemd timeout → проверить память, TimeoutStopSec |
| rc=1 | Общая ошибка | Баг в коде → читать stderr |
| rc=2 | Неверные аргументы | Ошибка вызова Claude CLI → проверить prompt |
| Timeout | Процесс не завершился вовремя | Длинный запрос → увеличить timeout |
| Exception в Python | Ошибка в боте | Traceback → найти строку → фиксить |

### 0.4 Построй отчёт расследования

Формат отчёта:

```
🔍 РАССЛЕДОВАНИЕ ОШИБКИ

⏰ Время: {UTC} ({NSK})
👤 Пользователь: {имя}
📂 Топик: {название} (thread_id={id})
💬 Сообщение: {тип — текст/голосовое/документ}
🔴 Ошибка: {rc/exception/timeout}
📋 Лог: {ключевые строки}

🧠 Причина: {root cause}
🔧 План фикса:
1. {шаг 1}
2. {шаг 2}
3. {шаг 3}

⚡ Проактивность: {уровень}
```

### 0.5 Решение по уровню проактивности

- **1.2:** Покажи отчёт → предложи план → жди одобрения
- **1.5:** Покажи отчёт → начни безопасные шаги (чтение кода, поиск бага) → покажи diff
- **2.2:** Покажи отчёт → реализуй фикс → покажи diff → проверь синтаксис → жди одобрения на деплой

---

## Phase 1: Root Cause Investigation

**BEFORE attempting ANY fix:**

1. **Read Error Messages Carefully**
   - Don't skip past errors or warnings
   - They often contain the exact solution
   - Read stack traces completely
   - Note line numbers, file paths, error codes

2. **Reproduce Consistently**
   - Can you trigger it reliably?
   - What are the exact steps?
   - Does it happen every time?
   - If not reproducible → gather more data, don't guess

3. **Check Recent Changes**
   - What changed that could cause this?
   - Git diff, recent commits
   - New dependencies, config changes
   - Environmental differences

4. **Gather Evidence in Multi-Component Systems**

   **WHEN system has multiple components (bot → Claude CLI → Telegram API):**

   ```
   For EACH component boundary:
     - Log what data enters component
     - Log what data exits component
     - Verify environment/config propagation
     - Check state at each layer

   Run once to gather evidence showing WHERE it breaks
   THEN analyze evidence to identify failing component
   THEN investigate that specific component
   ```

5. **Trace Data Flow**
   See `root-cause-tracing.md` in this directory for the complete backward tracing technique.

### Phase 2: Pattern Analysis

1. **Find Working Examples** — Locate similar working code in same codebase
2. **Compare Against References** — Read reference implementation COMPLETELY
3. **Identify Differences** — What's different between working and broken?
4. **Understand Dependencies** — What other components does this need?

### Phase 3: Hypothesis and Testing

1. **Form Single Hypothesis** — "I think X is the root cause because Y"
2. **Test Minimally** — SMALLEST possible change to test hypothesis
3. **Verify Before Continuing** — Worked? → Phase 4. Didn't? → NEW hypothesis
4. **When You Don't Know** — Say it. Research more. Ask for help.

### Phase 4: Implementation

1. **Create Failing Test Case** — Simplest possible reproduction
2. **Implement Single Fix** — Address root cause. ONE change at a time
3. **Verify Fix** — Test passes? No regressions?
4. **If Fix Doesn't Work** — Count attempts. If ≥ 3 → question architecture
5. **If 3+ Fixes Failed** — STOP. Question fundamentals. Discuss before more attempts.

---

## Bot-Specific Patterns

### Шаблон расследования по сервисам

| Бот | Сервис | Лог-команда | Код |
|-----|--------|-------------|-----|
| Марина | `nagrada-bot` | `journalctl -u nagrada-bot` | `projects/AI_Business/Marina_Biryukova/agent/bot/bot.py` |
| Виктория | `victoria-bot` | `journalctl -u victoria-bot` | `projects/Producing/Victoria_Sel/bot/bot.py` |
| Юлия | Docker `yulia-gudymo-bot` | `docker logs yulia-gudymo-bot` | `/srv/capsules/yulia_gudymo/bot/main.py` |
| Максим | `maxim-agent` (его сервер) | SSH → `journalctl -u maxim-agent` | `projects/Producing/Maxim_Belousov/agent-system/` |

### Типичные причины ошибок ботов

| Симптом | Вероятная причина | Проверка |
|---------|-------------------|----------|
| "техническая ошибка" | Claude CLI убит (SIGTERM/SIGKILL) | `journalctl` → rc=143/137 |
| Пустой ответ | Claude CLI timeout или пустой stdout | Проверить timeout в subprocess |
| Двойное сообщение | Дублирование вызова функции | grep по коду на двойные вызовы |
| Бот не отвечает | Сервис упал | `systemctl status` |
| "Ошибка: ..." | Exception в Python | Traceback в логах |

### Чеклист auto-healing (после фикса)

- [ ] SIGTERM-aware: бот отличает "обновлялся" от "техническая ошибка" (rc 143/-15/137/-9)
- [ ] safe-restart: ждёт завершения Claude CLI перед рестартом
- [ ] systemd: TimeoutStopSec ≥ 45, KillMode=mixed
- [ ] Синтаксис проверен: `python3 -c "import py_compile; py_compile.compile('...', doraise=True)"`
- [ ] Сервис перезапущен и active
- [ ] Пользователю отправлено объяснение (если была ошибка на его стороне)

---

## Red Flags — STOP and Follow Process

If you catch yourself thinking:
- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- "I don't fully understand but this might work"
- "One more fix attempt" (when already tried 2+)
- Proposing solutions before tracing data flow

**ALL of these mean: STOP. Return to Phase 1.**

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Issue is simple, don't need process" | Simple issues have root causes too |
| "Emergency, no time for process" | Systematic is FASTER than thrashing |
| "Just try this first" | First fix sets the pattern. Do it right |
| "One more fix attempt" (after 2+) | 3+ failures = architectural problem |

## Quick Reference

| Phase | Key Activities | Success Criteria |
|-------|---------------|------------------|
| **0. Forensics** | Logs, time, topic, message, error type | Full investigation report |
| **1. Root Cause** | Read errors, reproduce, check changes | Understand WHAT and WHY |
| **2. Pattern** | Find working examples, compare | Identify differences |
| **3. Hypothesis** | Form theory, test minimally | Confirmed or new hypothesis |
| **4. Implementation** | Create test, fix, verify | Bug resolved, tests pass |

## Supporting Techniques

- **`root-cause-tracing.md`** — Trace bugs backward through call stack
- **`defense-in-depth.md`** — Add validation at multiple layers
- **`condition-based-waiting.md`** — Replace arbitrary timeouts with condition polling
- **`bot-forensics-checklist.md`** — Step-by-step checklist for bot error investigation

## Real-World Impact

From debugging sessions:
- Systematic approach: 15-30 minutes to fix
- Random fixes approach: 2-3 hours of thrashing
- First-time fix rate: 95% vs 40%
- **Proactive forensics (v2):** ошибка Марины 19.03 — от обнаружения до полного фикса + auto-healing за 1 сессию

## Уроки из практики (2026-03-24)

### CLAUDE.md context leaking — бот отвечает мета-мусором
- **Симптом:** Бот отвечает 💾, SESSION_LOG, "Скиллы: без изменений", скилл-чек вместо реального ответа
- **Причина:** Claude CLI при `cwd` внутри `/root/Antigravity/` авто-подтягивает родительский CLAUDE.md с ДНК-правилами Дмитрия (SESSION_LOG, AI-факт, Teams). Бот выполняет эти мета-правила вместо задачи
- **Диагностика:** проверить ответ на маркеры: 💾, "SESSION_LOG", "Скиллы:", "AI-факт", "Нейро-факт", "Teams:"
- **Фикс (3 слоя):**
  1. `--append-system-prompt` в Claude CLI команду — блокирует мета-правила на уровне системного промпта
  2. Сброс сессии в sessions.json (новый UUID, messages=0) — убирает отравленную историю
  3. Очистка дневника от ложных записей ("задача залогирована ранее") — убирает ложный контекст
- **Профилактика:** тест C-01 в capsule-audit (проверка изоляции CLAUDE.md)

### Service masking + 409 Conflict (zombie processes)
- **Симптом:** бот не отвечает, `systemctl status` показывает masked или failed
- **Причина:** zombie node-процессы от Claude CLI (start_new_session=True) продолжают getUpdates → новый экземпляр получает 409 Conflict → crash loop → service masked
- **Диагностика:** `ls -la /etc/systemd/system/<service>.service` (→ /dev/null = masked). `ps aux | grep bot.py` (несколько процессов)
- **Фикс:** `systemctl unmask` → восстановить .service файл → `deleteWebhook?drop_pending_updates=true` → `systemctl start`

## Уроки из практики (2026-03-20)

### cgroup SIGKILL без следов в journal
- **Симптом:** процесс убит SIGKILL (status=9), нет OOM в dmesg, нет записей в journal
- **Причина:** systemd cgroup MemoryMax слишком низкий (2G). Subprocess (claude CLI + node) пробивает лимит, cgroup controller убивает без лога
- **Диагностика:** `systemctl show <service> | grep Memory` → проверить MemoryMax. `free -h` покажет что RAM свободна (это не kernel OOM, а cgroup limit)
- **Фикс:** увеличить MemoryMax через override: `mkdir -p /etc/systemd/system/<service>.service.d && echo -e '[Service]\nMemoryMax=4G' > override.conf && systemctl daemon-reload`

### bot-doctor агрессивные рестарты
- **Симптом:** бот рестартится каждые 2 мин во время обработки запроса
- **Причина:** bot-doctor сканирует логи за 5 мин, видит СТАРЫЕ ошибки (до фикса), рестартит
- **Диагностика:** `journalctl --since '5 min ago' | grep doctor`
- **Фикс:** `systemctl stop bot-doctor.timer`, подождать 5 мин (ошибки выйдут из окна), `systemctl start bot-doctor.timer`

### LiveStatus + asyncio subprocess = краш
- **Симптом:** GeneratorExit → Event loop is closed → RuntimeError
- **Причина:** LiveStatus (async loop каждые 3с) и asyncio.create_subprocess_exec конкурируют. При shutdown — race condition
- **Фикс:** убрать LiveStatus, использовать on_progress callback от execute_always_deep

---

## Changelog

<!-- Сюда автоматически добавляются уроки после каждого использования скилла -->

### 2026-03-19 — v2: проактивная форензика
- Баг Марины: двойной _extract_and_send_files (voice+document), safe-restart не ждал Claude CLI
- SIGTERM-aware ошибки внедрены в 3 ботов, systemd TimeoutStopSec=45
- Phase 0: шкала проактивности 0.8-2.2, bot-forensics-checklist.md
- Урок: safe-restart ДОЛЖЕН ждать Claude CLI (до 120с), иначе SIGTERM → "Техническая ошибка"
- Урок: systemd TimeoutStopSec >= 45 для ботов с Claude CLI subprocess

### 2026-03-31 — дебаг stream-json + --verbose + Neura App UFW
- ВСЕ боты (Марина/Никита/Яна) → "Техническая ошибка" одновременно
- Root cause #1: Claude CLI --verbose меняет stream-json (новые event types: assistant/result)
- Root cause #2: --verbose пишет ошибки в stdout (JSON), не stderr → is_session_error не матчил
- Параллельно: debugging Neura App (UFW Docker→Bridge, agents.use 403, MongoDB ban)
- Антипаттерн: при "Техническая ошибка" — НЕ рестартовать. Сначала journalctl → rc код → root cause
- Антипаттерн: парсить stderr для ошибок CLI = неполная картина. --verbose кладёт ВСЁ в stdout
- Урок: фикс одного бота = немедленно патчить ВСЕ + эталон. "Обновил одного → забыл остальных" → повтор
