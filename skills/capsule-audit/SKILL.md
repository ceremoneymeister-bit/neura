---
name: capsule-audit
description: Автоматическое тестирование и аудит продакшн-капсул (ботов) — health, messaging, files, integrations, memory, cross-capsule consistency
version: 1.0.0
author: Dmitry Rostovtsev
created: 2026-03-20
updated: 2026-03-20
category: infrastructure
tags: [testing, audit, bots, capsules, health-check, debugging]
risk: medium
usage_count: 1
last_used: 2026-04-03
maturity: seed
proactive_enabled: true
proactive_trigger_1_type: schedule
proactive_trigger_1_condition: "ежедневно 21:00"
proactive_trigger_1_action: "health check всех капсул"
proactive_trigger_2_type: event
proactive_trigger_2_condition: "после обновления бота"
proactive_trigger_2_action: "запустить smoke-тест"
learning_track_success: true
learning_track_corrections: true
learning_evolve_threshold: 3
learning_auto_update: [anti-patterns, triggers, changelog]
---

# Capsule Audit — скилл тестирования и дебага ботов

## Триггеры
- "аудит капсулы", "аудит бота", "проверь бота", "проверь ботов"
- "тестирование ботов", "capsule audit", "health check бота"
- "что с ботами?", "статус капсул", "всё ли работает?"
- Автоматически: после обновления кода бота → health + messaging тесты

## Два слоя тестирования

**Layer 2 (Infrastructure):** Проверка сервисов, логов, сессий, памяти, ресурсов — БЕЗ отправки сообщений в Telegram.

**Layer 1 (Functional):** Реальные Telegram-сообщения боту → ожидание ответа → валидация результата.

## Фаза 1 — Выбор цели

Определи по запросу пользователя:
- **Одна капсула:** "проверь Викторию" → `--capsule victoria`
- **Все капсулы:** "проверь всех ботов" → `--capsule all`
- **Категория:** "проверь здоровье" → `--category health`
- **Конкретный тест:** "тест M-01 на Марину" → `--capsule marina --test M-01`
- **После обновления:** авто → `--capsule <updated> --category health,messaging`

## Фаза 2 — Infrastructure Probes (Layer 2)

Запуск: `python3 .agent/skills/capsule-audit/scripts/capsule-audit.py --capsule <target> --category health`

Тесты H-01..H-08:
| ID | Проверка | Метод |
|----|----------|-------|
| H-01 | Сервис запущен | systemctl is-active / docker ps / ssh |
| H-02 | Нет свежих ошибок | journalctl/docker logs за 10 мин |
| H-03 | sessions.json валиден | JSON-парсинг |
| H-04 | Нет зомби-процессов claude | ps + filter >10 мин |
| H-05 | Память в норме | cgroup / docker stats < 90% |
| H-06 | Диск не переполнен | df -h < 90% |
| H-07 | Бот-токен валиден | getMe API |
| H-08 | Сессии не перегружены | Нет топиков >80 сообщений |

## Фаза 3 — Functional Tests (Layer 1)

Запуск: `python3 .agent/skills/capsule-audit/scripts/capsule-audit.py --capsule <target> --category messaging`

⚠️ **ВАЖНО:** Тестовые сообщения отправляются через Bot API (НЕ Telethon) — избегаем session lock.

🚨 **НЕ использовать префикс `[AUDIT]`!** Он создаёт новую сессию у бота → M-02 (persistence) всегда fail. Тестовые сообщения должны быть обычным текстом без маркеров.

🚨 **Тестировать в DM, не в HQ-топиках.** В топиках другая привязка сессий — результаты не сравнимы с реальным использованием. DM = основной сценарий пользователя.

Тесты M-01..M-05:
| ID | Тест | Сообщение | Ожидание | Таймаут |
|----|------|-----------|----------|---------|
| M-01 | Простой ответ | Сколько будет 2+2? | Ответ содержит "4" | 90с |
| M-02 | Персистентность | Прибавь 10 к результату | Ответ содержит "14" | 90с |
| M-03 | Длинный ответ | Напиши подробный план на неделю | >500 символов или Telegraph-ссылка | 180с |
| M-04 | PDF-генерация | Создай PDF-документ с планом на день | Файл получен (document в ответе) | 300с |
| M-05 | Восстановление | /cancel → Привет | Нормальный ответ | 90с |

**Правила тестирования M-02 (persistence):**
- M-01 и M-02 ОБЯЗАТЕЛЬНО отправляются последовательно в одном чате (DM)
- Пауза между M-01 и M-02: 15-30 секунд (дождаться ответа на M-01)
- НЕ использовать [AUDIT] или другие префиксы
- Если бот ответил на M-01 но M-02 не помнит контекст → проверить: тот же session_id используется?

## Фаза 4 — Cross-Capsule Consistency

Запуск: `python3 .agent/skills/capsule-audit/scripts/capsule-audit.py --capsule all --category cross_capsule`

Сравнивает код и структуру между капсулами:
- X-01: Сигнатура `execute_always_deep` одинакова
- X-02: Маркеры [FILE:], [LEARN:], [CORRECTION:] поддержаны
- X-03: Telegraph-обработка >4000 символов
- X-04: Каждая капсула имеет CLAUDE.md
- X-05: sessions.json одинаковая структура

## Фаза 5 — Отчёт

Полный прогон с отчётом:
```bash
python3 .agent/skills/capsule-audit/scripts/capsule-audit.py --capsule all --report /tmp/audit.md
```

Отчёт содержит:
- Общий балл (0-100) по каждой капсуле
- Таблицу тестов со статусами
- Лог-сниппеты для провалов
- Cross-capsule матрицу
- Рекомендации

После генерации → отправить в HQ topic 8 (infra):
```bash
python3 scripts/tg-send.py hq:8 "$(cat /tmp/audit.md | head -30)"
```

## Фаза 6 — Auto-Debug

При провале тестов:
1. Проанализируй log_snippet из результата теста
2. Подключи скилл `systematic-debugging` для расследования
3. Если проблема простая (зомби-процесс, переполненная сессия) → фикс сразу
4. Если проблема сложная → отчёт + план действий пользователю
5. После фикса → ре-тест конкретного теста

## CLI Reference

```bash
# Одна капсула, все тесты:
python3 .agent/skills/capsule-audit/scripts/capsule-audit.py --capsule victoria

# Все капсулы, только health:
python3 .agent/skills/capsule-audit/scripts/capsule-audit.py --capsule all --category health

# Один конкретный тест:
python3 .agent/skills/capsule-audit/scripts/capsule-audit.py --capsule victoria --test M-01

# Полный аудит с отчётом:
python3 .agent/skills/capsule-audit/scripts/capsule-audit.py --capsule all --report /tmp/audit.md

# Dry run (показать план без отправки):
python3 .agent/skills/capsule-audit/scripts/capsule-audit.py --capsule all --dry-run

# JSON-вывод для автоматизации:
python3 .agent/skills/capsule-audit/scripts/capsule-audit.py --capsule victoria --json
```

## Конфигурация

- **Реестр капсул:** `.agent/skills/capsule-audit/config/capsule-profiles.json`
- **Тест-кейсы:** `.agent/skills/capsule-audit/config/test-registry.json`

### Добавление нового бота
1. Добавить профиль в `capsule-profiles.json`
2. При необходимости — добавить capability-зависимые тесты в `test-registry.json`
3. Создать тестовый топик в HQ-группе бота

## Транспорты

| Капсула | Транспорт | Layer 2 | Layer 1 |
|---------|-----------|---------|---------|
| Victoria | systemd | journalctl + systemctl | Bot API |
| Marina | systemd | journalctl + systemctl | Bot API |
| Yulia | docker | docker logs + docker stats | Bot API |
| Maxim | ssh | ssh + journalctl | Bot API |

## Дополнительные проверки v2 (добавлены 03.04.2026)

| ID | Проверка | Метод |
|----|----------|-------|
| V2-01 | Docker v1 zombie containers | `docker ps \| grep -iE "yulia\|victoria\|marina"` — если running = 409 Conflict |
| V2-02 | V1 systemd таймеры живы | `systemctl list-timers --all \| grep -iE "victoria\|marina\|yana\|yulia"` |
| V2-03 | SYSTEM.md содержит userbot section | `grep "Интеграции Telegram" config/capsules/*/SYSTEM.md` |
| V2-04 | SYSTEM.md содержит Telethon code | `grep "Telethon" config/capsules/*/SYSTEM.md` |
| V2-05 | Userbot session существует | `find homes/ -name "*.session"` — каждая активная капсула должна иметь |
| V2-06 | API creds НЕ hardcoded | `grep "33869550" config/capsules/*/SYSTEM.md` — должно быть 0 |
| V2-07 | Context window настроен | `grep "recent_days" config/capsules/*.yaml` — должно быть 7 для всех |
| V2-08 | diary_bot_chars настроен | `grep "diary_bot_chars" config/capsules/*.yaml` — должно быть >=500 |
| V2-09 | Согласование перед действиями | `grep "Согласование" config/capsules/*/SYSTEM.md` — должно быть в каждом |
| V2-10 | PDF warning в SYSTEM.md | `grep "capsule-tools.py для PDF" config/capsules/*/SYSTEM.md` |
| V2-11 | Onboarding не застрял | `python3 -c "import redis; r=redis.Redis(); print(list(r.scan_iter('neura:onb:*')))"` |
| V2-12 | Prompt pipeline safe | engine.py: threshold 120KB, stdin pipe для >120KB, NO bash -c |

## Чтение чатов пользователей (deep audit)

Для глубокого аудита — читай РЕАЛЬНЫЕ сообщения через userbot:
```python
# Рабочие сессии:
# Дмитрий (основной): /root/Antigravity/.secrets/telegram_userbot
# Victoria: /opt/neura-v2/homes/victoria_sel/victoria_userbot.session
# Yana: /opt/neura-v2/homes/yana_berezhnaya/yana_berezhnaya_userbot.session
# Yulia: /opt/neura-v2/homes/yulia_gudymo/yulia_gudymo_userbot.session
# Marina: EXPIRED — нужно переподключить
```

Deepgram транскрипция для голосовых: `scripts/tg-send.py` или прямой API call.

## Anti-patterns
- ❌ НЕ использовать Telethon для тестовых сообщений (session lock!)
- ❌ НЕ запускать Layer 1 тесты на Максима без явной просьбы (чужой сервер)
- ❌ НЕ удалять/модифицировать сессии ботов во время аудита
- ❌ НЕ использовать префикс [AUDIT] — ломает persistence тест (M-02)
- ❌ НЕ тестировать в HQ-топиках — тестировать в DM (основной сценарий)
- ❌ НЕ запускать полный аудит чаще раза в день (нагрузка на Claude API)
- ❌ НЕ доверять score 100/100 если >50% тестов skipped — формула врёт
- ❌ НЕ игнорировать мета-мусор (💾, SESSION_LOG, скилл-чек) в ответах бота — это признак утечки CLAUDE.md из родительской директории (инцидент 24.03.2026)
- ❌ НЕ менять shared код (engine.py, telegram.py) без проверки влияния на ВСЕ капсулы (инцидент 03.04 — bash -c сломал Яну и Марину)
- ❌ НЕ использовать bash -c с пользовательским текстом — shell escaping injection (инцидент 03.04)
- ❌ НЕ снижать threshold/timeout без проверки что все промпты помещаются (инцидент 03.04 — 50KB threshold → Яна 46KB сломалась)

## Тесты изоляции (добавлены 24.03.2026)

### C-01: Изоляция CLAUDE.md (Layer 1)
Проверить что Claude CLI НЕ подтягивает родительский CLAUDE.md с мета-правилами Antigravity.
- **Метод:** отправить тест-сообщение "Сколько будет 2+2?", проверить ответ
- **Pass:** Ответ содержит "4" и НЕ содержит 💾, SESSION_LOG, "Скиллы:", AI-факт, Нейро-факт
- **Fail:** Ответ содержит маркеры ДНК-правил Antigravity → CLAUDE.md утечка
- **Критичность:** 🔴 CRITICAL — без изоляции бот отвечает мета-мусором вместо реальной работы
- **Фикс:** добавить `--append-system-prompt` в Claude CLI команду (streaming_executor.py / claude.py)

### C-02: Session poisoning recovery (Layer 1)
Проверить что сброс сессии (`/reset`) очищает отравленную историю.
- **Метод:** отправить `/reset` → задать вопрос → проверить ответ
- **Pass:** Ответ не содержит "задача уже выполнена", "залогирована ранее"
- **Fail:** Ответ ссылается на предыдущую несуществующую работу
- **Фикс:** сброс session_id в sessions.json (новый UUID, messages=0) + очистка дневника

### C-03: --append-system-prompt наличие (Layer 2)
Проверить что Claude CLI запускается с `--append-system-prompt` для блокировки родительского CLAUDE.md.
- **Метод:** grep в коде бота за `append-system-prompt`
- **Pass:** Найден флаг с инструкцией изоляции
- **Fail:** Нет защиты → бот уязвим к CLAUDE.md утечке
- **Критичность:** 🔴 CRITICAL для капсул внутри `/root/Antigravity/`

## Новые тесты (добавлены 21.03.2026)

### S-01: Безопасность Bash (Layer 2)
Проверить что Claude CLI запускается с `--allowedTools` (без unrestricted Bash).
- **Метод:** grep в коде бота за `--allowedTools` или `allowedTools`
- **Pass:** Найден флаг с ограничением Bash
- **Fail:** Claude CLI запускается без ограничений → может выполнить `kill`, `rm` и т.д.
- **Критичность:** 🔴 CRITICAL — без этого бот может быть заморожен (инцидент Максима 21.03)

### S-02: md2pdf.py доступен (Layer 2)
Проверить что скрипт генерации PDF доступен в рабочей директории бота.
- **Метод:** проверить существование файла по пути из CLAUDE.md
- **Pass:** Файл найден и `python3 <path> --help` возвращает usage
- **Fail:** Файл не найден или ошибка импорта

## Уроки ночного аудита 20→21.03.2026

### HQ entity resolution
Parser session (`telegram_userbot_parser`) может не иметь кэшированного entity для HQ-групп.
**Симптом:** `Could not find the input entity for PeerChannel` — все тесты error.
**Фикс v1.1:** Автоматический DM fallback при ошибке entity (если `bot_username` задан).
**Долгосрочный фикс:** Добавить parser userbot во все HQ-группы клиентов.

### Scoring с all-skipped
Капсулы без Layer 1 (Maxim — no bot_id) получали score 100/100 из-за пропущенных тестов.
**Рекомендация:** Формула scoring должна учитывать skip-ratio.

### Паттерны по капсулам (обновлено 21.03.2026)
| Паттерн | Victoria | Marina | Yulia | Maxim |
|---------|----------|--------|-------|-------|
| Персистентность (M-02) | ✅ код | ✅ код | ✅ тест | ✅ код |
| Длинные ответы (M-03) | ✅ Telegraph | ✅ Telegraph | ✅ код | ✅ Telegraph |
| PDF-генерация (M-04) | ✅ [FILE:] | ✅ [FILE:] | ✅ [FILE:] | ✅ [FILE:] + md2pdf |
| execute_always_deep | ✅ | ✅ | ✅ | ✅ |
| Telegraph в коде | ✅ | ✅ | ✅ | ✅ |
| --allowedTools (S-01) | ❓ | ❓ | ❓ | ✅ (21.03) |
| md2pdf.py доступен (S-02) | ✅ сервер | ✅ сервер | ✅ Docker | ✅ (21.03) |

**⚠️ Важно:** "✅ код" означает что функционал есть в коде, но тест M-02 провалился из-за методологии ([AUDIT] префикс). Реальная работоспособность требует DM-теста без префикса.

### Уроки 21.03.2026 — инцидент Максима (kill-STOP)
**Инцидент:** Claude CLI subprocess (запущенный ботом) выполнил `kill -STOP` на процесс бота → бот заморожен 5 часов.
**Причина:** Claude CLI запускался без `--allowedTools` → полный доступ к Bash → мог выполнить любую команду.
**Фикс:** Добавлен `--allowedTools` по умолчанию (без unrestricted Bash).
**Урок:** Добавлен тест S-01 (безопасность Bash) как CRITICAL проверка для всех капсул.

## Интеграция с проактивностью

- После обновления бота → автоматически `--capsule <updated> --category health,messaging`
- Еженедельный полный аудит (понедельник 03:00): `capsule-audit.py --capsule all --report`
- При обнаружении проблемы → сразу systematic-debugging → фикс → ре-тест

### Тесты v2.2.0+ (добавлены 21.03.2026)

| Тест | Категория | Проверка |
|------|-----------|----------|
| SK-01 | skills | `skills/` директория существует, есть хотя бы `.gitkeep` |
| SK-02 | skills | `bot/utils/skills.py` — `get_skill_table()` возвращает не пустую строку при наличии skills |
| SK-03 | skills | `{{SKILL_TABLE}}` в CLAUDE.md.template заменяется в runtime |
| HR-01 | hot-reload | Изменить CLAUDE.md → mtime-кеш обновляется при следующем вызове `get_agent_context()` |
| HR-02 | hot-reload | `/reload` команда сбрасывает `_ctx_cache["mtime"]` |
| PR-01 | proactive | `python3 proactive.py morning --dry-run` выводит сообщение (exit 0) |
| PR-02 | proactive | `config.json` содержит `proactive.schedule` массив |
| TL-01 | tools | `tools/capsule-tools.py list` возвращает список инструментов |
| TL-02 | tools | `tools/capsule-tools.py qr "test" /tmp/test.png` создаёт файл (при установленном qrcode) |
| MN-01 | menu | `bot/handlers/menu.py` существует и импортируется |
| MN-02 | menu | `build_response_buttons()` возвращает InlineKeyboardMarkup |
| MN-03 | menu | `callbacks.py` обрабатывает `menu:open`, `menu:close`, `menu:stats`, `info:model` |
| MN-04 | menu | Response buttons показываются в DM (не только HQ group) |
| PT-01 | portability | `cp -r capsule /tmp/test && cd /tmp/test && bash setup.sh --dry-run` проходит |

### Уроки 21.03.2026 — доводка до продажи

- **5 критических gaps** найдены при сравнении с production-ботом Виктории: skills не подключаются, CLAUDE.md не перечитывается, проактивности нет, инструментов нет, diary без метаданных
- **Портативность уже работает** (10/10), но без skills и tools капсула — пустая оболочка
- **Тестирование через HQ-топик** — создать топик `🧪 Neura Etalon` и отправлять туда тестовые сообщения с inline keyboard для визуальной проверки
- **Menu callbacks** — самая частая ошибка: `menu:open` и `menu:model` в кнопках ответа не обрабатывались в callbacks.py (мёртвые кнопки)

---

## Changelog

### 2026-04-03 — Полный аудит neura-v2 (7 капсул, 50 находок)

**Уроки:**
1. **journalctl = чёрный ящик для Claude subprocess.** Telethon/userbot операции НЕ видны в `journalctl -u neura-v2`. Для поиска userbot активности → diary в PostgreSQL (`SELECT * FROM diary WHERE bot_response ILIKE '%userbot%'`)
2. **Dashboard undercounts ошибки.** 15+ early return paths в telegram.py (auth, trial, rate limit) выходят ДО `_process_message()` → не попадают в метрики. Реальный error rate = запросы из diary, не из dashboard
3. **v1 таймеры = источник CLAUDE.md утечки.** Victoria v1 proactive timers (content/fact/intention/reflect/tool) работают из `/root/Antigravity/` с родительским CLAUDE.md → мета-мусор в ответах. Фикс: `--append-system-prompt` в v1 скрипте
4. **API credentials в SYSTEM.md** — были plaintext (API_ID, API_HASH). Заменены на `os.environ['TELETHON_API_ID']`. Claude адаптируется и подставляет из diary-контекста даже без env vars, но это ненадёжно
5. **Добавить в чеклист:** проверка v1 таймеров (`systemctl list-units | grep -iE "victoria|marina|yana"`) как обязательный пункт аудита
6. **Neura-v2 архитектура:** context.py всегда `is_first_message=True`, BTW queue без лимита, diary cleanup не в cron — найдены 50 архитектурных точек для проработки

**Anti-patterns обнаруженные:**
- ❌ НЕ грепать journalctl для поиска userbot-активности → смотреть diary в DB
- ❌ НЕ доверять dashboard OK% → считать ошибки по diary + Stream done 0 chunks
- ❌ НЕ менять WorkingDirectory в systemd если скрипт использует `Path(__file__)` для BASE
