# Neura v2 — Known Issues & Lessons Learned

> Обновлено: 2026-04-02
> Источники: 6 SESSION_CONTEXT файлов + SESSION_LOG + PROGRESS.md

---

## Resolved Issues

### CRITICAL

| # | Описание | Файл(ы) | Fix | Дата |
|---|----------|---------|-----|------|
| C1 | Toggle race condition при быстрых двойных кликах inline-кнопок — два handler запускались параллельно | `telegram.py:248-267` | `asyncio.Lock` per `(capsule_id, user_id)` | 2026-04-02 |
| C2 | MemoryMax=2G — OOM kill при Claude CLI subprocess | `neura-v2.service` | `MemoryMax=4G`, `TimeoutStopSec=60`, `KillMode=mixed` | 2026-04-02 |
| C3 | Engine orphan processes — Claude CLI zombie после cancellation/shutdown | `engine.py` | `proc.kill()` при cancellation + orphan killer (filter by PPID) | 2026-04-02 |
| C4 | Пустой ответ ("0 chars") — бот молча глотал пустые ответы от Claude | `telegram.py` | Guard: пустой ответ -> "Не удалось получить ответ" | 2026-04-02 |
| C5 | BTW flush race condition — flush без lock, data corruption в multi-message | `queue.py` | flush внутри asyncio.Lock | 2026-04-02 |
| C6 | asyncio buffer overflow (LimitOverrunError) при документах >64KB | `engine.py` | Buffer увеличен 64KB -> 2MB | 2026-04-02 |
| C7 | capsule_id=NULL у web-пользователя — Claude не мог определить капсулу | `web.py` | Привязка dmitry_rostovcev к user, auto-assign capsule при регистрации | 2026-04-02 |
| C8 | Echo mode маскировал ошибки — бот повторял сообщение пользователя вместо error | `web.py` | Убран echo -> error message при отсутствии capsule | 2026-04-02 |
| C9 | PhoneCodeExpired за 11 секунд — TCP disconnect при StringSession, auth_key терялся | `userbot_connect.py` | Файловая сессия (SQLite) вместо StringSession + QR Login как основной метод | 2026-04-02 |
| C10 | OAuth 401 во всех 8 capsule homes — .credentials.json были копиями (устаревали одновременно) | все `homes/*/.credentials.json` | Все копии заменены на symlink -> `~/.claude/.credentials.json` | 2026-04-02 |
| C11 | Claude CLI traverses up to /root/CLAUDE.md — бот подтягивал dev-инструкции, вел себя как dev tool | все `homes/*/` | `.git` + собственный `CLAUDE.md` в каждом capsule home (блокирует upward traversal) | 2026-04-02 |
| C12 | CLAUDE.md в dmitry_test указывал на yana_berezhnaya — перекрестное загрязнение промпта | `homes/dmitry_test/CLAUDE.md` | Исправлен path в CLAUDE.md + YAML owner | 2026-04-02 |

### HIGH

| # | Описание | Файл(ы) | Fix | Дата |
|---|----------|---------|-----|------|
| H1 | BTW queue per capsule_id, а не per user_id — cross-contamination сообщений в multi-employee (Марина) | `queue.py`, `telegram.py` | Переделан на per user_id + `get_processing_user()` | 2026-04-02 |
| H2 | /start во время QR wait — leak Telethon client + ghost messages | `onboarding.py` | `_cleanup_user_session()` при повторном /start | 2026-04-02 |
| H3 | UserbotConnector не cleanup при service restart — Telethon клиенты висели | `onboarding.py`, `telegram.py` | `cleanup_all()` при shutdown в transport layer | 2026-04-02 |
| H4 | bot_response НЕ включался в diary context — бот не помнил свои ответы | `memory.py`, `context.py` | `bot_response` добавлен в diary write и контекст | 2026-04-02 |
| H5 | Diary truncation 500 символов — слишком жесткая обрезка, теряется контекст | `context.py` | Увеличено до 2000 символов | 2026-04-02 |
| H6 | Двойная обрезка context (80 символов) — context_builder обрезал уже обрезанное | `context.py` | Увеличено до 200/300 символов (user/bot) | 2026-04-02 |
| H7 | _limits из YAML не подключены к context builder — лимиты игнорировались | `context.py`, `capsule.py` | Пробросили capsule config limits в `build_context_parts` | 2026-04-02 |
| H8 | [FILE:] маркер — allowed_prefixes не содержал homes/ — файлы не отправлялись | `protocol.py` | Добавлен `homes/` в allowed_prefixes | 2026-04-02 |
| H9 | Double-send при файлах — текст + файл дублировались | `telegram.py` | `files_only` flag: после finalize() вызывать _send_response только для файлов | 2026-04-02 |
| H10 | Voice handler не перехватывал онбординг — голосовое сообщение уходило в ClaudeEngine | `telegram.py` | + onboarding intercept в `_handle_voice` | 2026-04-02 |
| H11 | Voice handler не проверял BTW queue — голос мог обработаться вне очереди | `telegram.py` | + BTW queue check в voice handler | 2026-04-02 |
| H12 | Orphan killer убивал ВСЕ claude процессы (включая dev сессии) | `engine.py` | Filter by PPID — только дочерние процессы v2 | 2026-04-02 |
| H13 | v1 сервисы auto-start параллельно с v2 — конфликт OAuth refresh, polling conflict | systemd | `systemctl disable + stop` для nagrada, victoria, yana, nikita, yulia-docker | 2026-04-02 |
| H14 | expired_message hardcoded — не бралось из YAML-конфига | `telegram.py` | Читается из capsule config | 2026-04-01 |
| H15 | Capsule home isolation — .credentials.json не копировался при создании | `homes/*/` | Копирование (позже заменено на symlink, см. C10) | 2026-04-01 |
| H16 | Phase 6 auto-complete — пользователь застревал в resume loop после онбординга | `onboarding.py` | fix auto-complete логики | 2026-04-02 |
| H17 | Нет user record для dmitry_test в БД — duration=0, запросы не привязаны | PostgreSQL | user record создан | 2026-04-02 |
| H18 | Файлы не трекаются в БД — отправленные файлы терялись | transport layer | Зафиксировано в аудите | 2026-04-02 |
| H19 | Дубль diary с 401 ответом — diary содержал записи об ошибках | `memory.py` | cleanup дублей | 2026-04-02 |
| H20 | Marina "Message to be replied not found" — race condition при рестарте | `telegram.py` | Не критично, логируется | 2026-04-02 |

### MEDIUM

| # | Описание | Файл(ы) | Fix | Дата |
|---|----------|---------|-----|------|
| M1 | QR background task не отменялся при cancel/restart | `onboarding.py`, `telegram.py` | QR task cancellation + tracking | 2026-04-02 |
| M2 | Phone number хранился в plaintext в Redis (PII) | `onboarding.py` | Перенесено на connector object (не в Redis) | 2026-04-02 |
| M3 | QR image files в /tmp не очищались | `onboarding.py` | cleanup в `_cleanup_user_session()` | 2026-04-02 |
| M4 | Web transport не писал diary | `web.py` | Добавлен diary write в WebSocket handler | 2026-04-02 |
| M5 | finalize(None) AttributeError на пустом ответе | `protocol.py` | Guard: `if msg is None: return` | 2026-04-02 |
| M6 | asyncio import отсутствовал в onboarding — QR refresh crash | `onboarding.py` | `import asyncio` | 2026-04-02 |
| M7 | Memory дубли onboarding profile (5 записей вместо 1) | `memory.py` | DELETE before INSERT | 2026-04-02 |
| M8 | Redis error handling при отправке текста во время онбординга | `onboarding.py` | `try/except` для Redis операций | 2026-04-02 |
| M9 | Текст во время phases 0/1/4 без hint — пользователь не понимал что делать | `onboarding.py` | "Используйте кнопки" hint | 2026-04-02 |
| M10 | DOCX/XLSX/PPTX — Claude CLI не может их читать нативно | `engine.py` | Pre-extraction через `markitdown[all]` | 2026-04-02 |
| M11 | /start после завершения онбординга — некорректная обработка | `onboarding.py` | + logging + правильное перенаправление | 2026-04-02 |
| M12 | Stale .session файл Telethon — auth_key mismatch -> PhoneCodeExpiredError | `userbot_connect.py` | Удаление .session файла перед каждой попыткой | 2026-04-02 |
| M13 | Ctrl+B toggle sidebar сломан | `web/src/` | Фикс обработки клавиш | 2026-04-02 |
| M14 | Working dir не capsule home — ассеты не видны Claude CLI | `engine.py` | `working_dir = home_dir` | 2026-04-01 |
| M15 | Скиллы не инжектились в промпт — Claude не знал о доступных командах | `capsule.py`, `engine.py` | Skills injection через `EngineConfig.append_system_prompt` | 2026-04-01 |
| M16 | Ассеты не скопированы в capsule homes — персональные файлы клиентов недоступны | `homes/*/` | Копирование ассетов Marina/Yana/Yulia/Victoria/Nikita -> homes/ | 2026-04-01 |
| M17 | Досье сотрудников не подгружаются (Marina multi-employee) | `capsule.py` | Зафиксировано в аудите фич | 2026-04-01 |
| M18 | grsai symlink отсутствовал в dmitry_test | `homes/dmitry_test/` | Создан symlink | 2026-04-02 |
| M19 | 20 skills не были symlinked в dmitry_test | `homes/dmitry_test/skills/` | Создано 20 symlinks | 2026-04-02 |

### LOW

| # | Описание | Файл(ы) | Fix | Дата |
|---|----------|---------|-----|------|
| L1 | Diary retention cleanup отсутствовал — diary росло бесконечно | `memory.py` | `cleanup_old_diary()` метод | 2026-04-02 |
| L2 | search_memory ORDER BY score бессмысленный (все записи 0.5) | `memory.py` | ORDER BY removed | 2026-04-02 |
| L3 | tempfile.mktemp() deprecated (security warning) | `userbot_connect.py` | `tempfile.NamedTemporaryFile` | 2026-04-02 |
| L4 | 2 сломанных скилла (knowledge-absorption, synapse-platform) | skills/ | Удалены | 2026-04-02 |

---

## Anti-patterns (что НЕ делать)

### Инфраструктура

1. **НЕ копировать .credentials.json** — только symlink на `~/.claude/.credentials.json`. Копии устаревают при OAuth refresh, все капсулы ломаются одновременно (см. C10)
2. **НЕ использовать StringSession в Telethon** — TCP disconnect теряет auth_key. Только файловая сессия (SQLite) — она переживает reconnect (см. C9)
3. **НЕ использовать MemoryMax < 4G** для сервисов с Claude CLI subprocess — OOM kill гарантирован (см. C2)
4. **НЕ ставить asyncio buffer по умолчанию (64KB)** для LLM streaming — документы и длинные ответы вызовут LimitOverrunError (см. C6)
5. **НЕ оставлять v1 сервисы enabled** при запуске v2 — конфликт polling и OAuth refresh (см. H13)

### Архитектура Claude CLI

6. **НЕ допускать отсутствие .git в capsule home** — Claude CLI traverses вверх по fs и подтягивает /root/CLAUDE.md с dev-инструкциями. Каждый home ДОЛЖЕН иметь .git + свой CLAUDE.md (см. C11)
7. **НЕ использовать echo mode** как fallback — маскирует реальные ошибки. Всегда возвращать человекочитаемое сообщение об ошибке (см. C8)
8. **НЕ убивать ВСЕ claude процессы** в orphan killer — фильтровать по PPID, иначе падают dev-сессии (см. H12)

### Data & Memory

9. **НЕ обрезать diary до <2000 символов** — теряется контекст, бот не помнит разговор (см. H5)
10. **НЕ забывать bot_response в diary** — без ответа бота в контексте невозможен нормальный диалог (см. H4)
11. **НЕ использовать INSERT без DELETE** для уникальных записей (onboarding profile) — дубли (см. M7)
12. **НЕ полагаться на ORDER BY score** если все score одинаковые (0.5) — бесполезная сортировка (см. L2)

### Onboarding & Userbot

13. **НЕ отправлять phone code без проверки rate limit** — Telegram: 5 попыток/день, после чего PhoneCodeExpired мгновенно (см. C9)
14. **НЕ удалять .session файл без проверки** — stale session вызывает auth_key mismatch. При повторе: удалять .session, создавать новый клиент (см. M12)
15. **НЕ хранить PII (phone number) в Redis** в plaintext — держать на объекте connector в памяти процесса (см. M2)
16. **НЕ оставлять QR/Telethon ресурсы без cleanup** — при /start, cancel, restart обязательно: cancel задачи, disconnect клиенты, удалить tmp файлы (см. H2, H3, M1, M3)

### Transport & Protocol

17. **НЕ вызывать _send_response после finalize()** если streaming msg уже удалён — double-send. Использовать files_only flag (см. H9)
18. **НЕ пропускать voice handler через onboarding** — голос должен перехватываться как текст (см. H10)
19. **НЕ игнорировать BTW queue в voice handler** — голосовые сообщения должны проходить ту же очередь (см. H11)
20. **НЕ полагаться на Claude CLI для чтения DOCX/XLSX/PPTX** — нужен pre-extraction через markitdown (см. M10)

### Web UI

21. **НЕ создавать web-пользователя без capsule_id** — все запросы сломаются. Auto-assign при регистрации (см. C7)
22. **НЕ забывать diary write в web transport** — web-чат и Telegram должны писать diary одинаково (см. M4)

---

## Open Issues

| # | Описание | Severity | Файл(ы) | Статус |
|---|----------|----------|---------|--------|
| O1 | Phone Code тест не выполнен — rate limit на номере @sega, нужна 1 попытка | MEDIUM | `userbot_connect.py` | Ждет снятия rate limit |
| O2 | 24ч мониторинг neura-v2 не завершен | HIGH | — | В процессе |
| O3 | Стандартные шаблоны для типовых документов | LOW | — | Необязательно |
| O4 | Mobile API (transport/mobile_api.py) | LOW | — | Phase 7 |
| O5 | Grafana dashboards | LOW | — | Phase 4 optional |
| O6 | Proactive messages | MEDIUM | — | Phase 4 |
| O7 | Admin API (admin/api.py) | MEDIUM | — | Phase 4 |
| O8 | Billing + ЮKassa (billing/plans.py, payment.py) | HIGH | — | Phase 6 |
| O9 | Auto capsule creation (provisioning/auto_deploy.py) | HIGH | — | Phase 6 |
| O10 | White-label (whitelabel/partner.py, branding.py) | MEDIUM | — | Phase 6 |
| O11 | Diary retention cron не настроен | LOW | `memory.py` | cleanup_old_diary() готов, cron нет |
| O12 | Яна: не может зайти в Neura App (Invalid email/password) | LOW | — | Платформа переделывается |
| O13 | Яна: просит визитки — отдельная задача | LOW | — | Backlog |
| O14 | Включить onboarding для Никиты (первый реальный пользователь) | MEDIUM | `nikita_maltsev.yaml` | features.onboarding: true |
| O15 | Victoria: проверить что flo_cycle работает в контексте | MEDIUM | — | Нужен тест |
| O16 | Dmitry test bot: проверить что НЕ подтягивает dev CLAUDE.md (.git isolation) | MEDIUM | — | Фикс применен, верификация нужна |
| O17 | Никита: триал истек (9 дней назад) — решение: продлить/отключить? | MEDIUM | `nikita_maltsev.yaml` | Ждет решения Дмитрия |
| O18 | Возможный конфликт v1/v2 OAuth refresh при параллельной работе | LOW | — | v1 остановлены, мониторить |
| O19 | Engine error (401/timeout) текст показывался пользователю как ответ | HIGH | `telegram.py` | ✅ Fix 2026-04-04: engine_error flag + user-friendly message |
| O20 | LibreChat restart loop (generateCapabilityCheck not a function) | LOW | Docker | ✅ Stopped 2026-04-04, не нужен при v2 |
| O21 | capsule-healthcheck-cron.py проверял v1 сервисы | MEDIUM | `scripts/` | ✅ Fix 2026-04-04: обновлено на neura-v2 |
| O22 | users.md и failover-manager.py ссылались на v1 команды | MEDIUM | `docs/`, `scripts/` | ✅ Fix 2026-04-04: обновлено на v2 |

---

## Хронология по фазам

| Фаза | Даты | Тестов | Багов найдено | Багов пофикшено |
|------|------|--------|---------------|-----------------|
| Phase 0: Foundation | 2026-04-01 | 98 | 0 | 0 |
| Phase 1: Telegram + Никита | 2026-04-01 | 164 | 3 | 3 |
| Phase 2: Все капсулы | 2026-04-01 | 199 | 4 | 4 |
| Phase 3: Web UI | 2026-04-02 (ночь) | 227 | 1 | 1 |
| Phase 4: Monitoring | 2026-04-01 | 199 | 0 | 0 |
| Phase 5: Deploy + Integration | 2026-04-02 | 230 | ~15 | ~15 |
| Phase 6: Onboarding + Userbot | 2026-04-02 | 230 | 30+ | 28 |
| **ИТОГО** | 2 дня | **230** | **50+** | **47+** |

---

## References

| Файл | Содержание |
|------|-----------|
| `docs/neura-v2/SESSION_CONTEXT_2026-04-01_phase1.md` | Phase 0 + 0.5 + 1, первый live тест, уроки изоляции |
| `docs/neura-v2/SESSION_CONTEXT_2026-04-01_nikita.md` | Миграция Никиты, триал, rollback plan |
| `docs/neura-v2/SESSION_CONTEXT_2026-04-02_post-launch.md` | Phase 5 deploy, миграция контекста всех, critical fixes |
| `docs/neura-v2/SESSION_CONTEXT_2026-04-02_onboarding.md` | Баг-фиксы transport, тестовая капсула, userbot API ID |
| `docs/neura-v2/SESSION_CONTEXT_2026-04-02_post-audit.md` | 7-фазный онбординг, 30 багов аудит, QR/Phone Code root cause |
| `docs/neura-v2/SESSION_CONTEXT_2026-04-02_post-bugfix.md` | 11 отложенных багов, тестирование документов, 230 тестов |
| `docs/neura-v2/PROGRESS.md` | Полный трекер всех модулей и фиксов |
| `SESSION_LOG.md` | Хронологический лог всех действий |
