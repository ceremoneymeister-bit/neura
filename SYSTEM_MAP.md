# Neura v2 — System Map
> Единый справочник. Читай первым при старте сессии.
> Обновлено: 2026-04-02 (актуальное состояние)

## Сервисы

| Сервис | Тип | Порт | Назначение | Статус |
|--------|-----|------|------------|--------|
| neura-v2.service | systemd (python3) | — | Ядро: 7 TG-ботов + Web API в одном процессе | **active** |
| neura-postgres | Docker (pgvector:pg16) | 5432 | PostgreSQL + pgvector | **active** |
| neura-redis | Docker (redis:7-alpine) | 6379 | Кеш, очередь, rate limits, onboarding state | **active** |
| argisht-bot.service | systemd | — | Бот Аргишта (отдельный, не v2) | **active** |
| hq-bot.service | systemd | — | HQ-бот Дмитрия | **active** |
| cm-listener.service | systemd | — | Auto-агент поддержки Максима | **active** |

### Остановленные / disabled (V1 legacy)

| Сервис | UnitFileState | ActiveState | Примечание |
|--------|--------------|-------------|------------|
| victoria-bot | disabled | running | V1, заменён neura-v2 |
| nagrada-bot | disabled | running | V1, заменён neura-v2 |
| nikita-bot | disabled | running | V1, заменён neura-v2 |
| yana-bot | disabled | running | V1, заменён neura-v2 |
| neura-bridge | disabled | running | V1, заменён neura-v2 |
| neura-admin | disabled | dead | V1, заменён neura-v2 |

### Docker (остановленные)

LibreChat stack (`restart: no`): LibreChat, chat-mongodb, rag_api, vectordb, chat-meilisearch.
Юлия v1 Docker: yulia-gudymo-bot, yulia-gudymo-platform — exited.

## Файловая структура

```
/opt/neura-v2/
├── neura/                          # Python-пакет (ядро, ~5350 LOC)
│   ├── core/
│   │   ├── engine.py               # Claude CLI wrapper, streaming (281 LOC)
│   │   ├── capsule.py              # YAML loader, trial, employees (202 LOC)
│   │   ├── context.py              # Prompt assembly, truncation (107 LOC)
│   │   ├── memory.py               # Diary/memory/learnings CRUD → PG (214 LOC)
│   │   ├── queue.py                # BTW queue, rate limits → Redis (122 LOC)
│   │   └── skills.py               # SKILL.md parser, per-capsule filter (117 LOC)
│   ├── transport/
│   │   ├── app.py                  # Entry point: TG + uvicorn + signals (202 LOC)
│   │   ├── telegram.py             # Multi-bot adapter, streaming, handlers (896 LOC)
│   │   ├── web.py                  # FastAPI REST + WebSocket (784 LOC)
│   │   ├── auth.py                 # bcrypt + JWT HS256 (98 LOC)
│   │   └── protocol.py            # Message types, ResponseParser, Telegraph (355 LOC)
│   ├── provisioning/
│   │   ├── onboarding.py           # 7-phase onboarding flow (1117 LOC)
│   │   ├── onboarding_state.py     # Redis state machine (113 LOC)
│   │   └── userbot_connect.py      # Telethon QR + phone code (263 LOC)
│   ├── monitoring/
│   │   ├── health.py               # BG checks: postgres/redis/cli/bots (151 LOC)
│   │   ├── alerts.py               # TG alerts → HQ, dedup (107 LOC)
│   │   └── metrics.py              # Per-capsule Redis metrics (79 LOC)
│   ├── storage/
│   │   ├── db.py                   # asyncpg pool + migrations
│   │   ├── cache.py                # Redis connection, DI
│   │   └── migrations/
│   │       ├── 001_initial.sql     # capsules, diary, memory, learnings, files
│   │       └── 002_web.sql         # users, projects, conversations, messages, web_files
│   ├── billing/                    # Заглушки (Phase 6)
│   ├── whitelabel/                 # Заглушки (Phase 6)
│   ├── admin/                      # Заглушки (Phase 4)
│   └── tools/                      # Заглушки (будущие интеграции)
├── config/
│   ├── capsules/                   # 7 YAML-конфигов + SYSTEM.md в подпапках
│   └── integration_catalog.json    # 15 интеграций, 8 профилей
├── web/                            # React SPA (Vite + TS + Tailwind)
│   └── dist/                       # Собранный SPA
├── homes/                          # Изолированные ~/.claude (8 шт, вкл. test_capsule)
├── skills/                         # Общий пул скиллов (84 шт)
├── tests/                          # pytest (17 файлов, 3218 LOC, 230+ тестов)
├── scripts/
│   ├── migrate_data.py             # Миграция v1 → v2
│   ├── create-hq-group.py          # Идемпотентное создание HQ-группы с топиками
│   ├── error-monitor.py            # Мониторинг ошибок (cron каждый час :45)
│   ├── smoke_test.py               # Smoke-тест после деплоя
│   └── night-agent.sh              # Ночной агент
├── docker-compose.yml              # postgres + redis (LibreChat stack — restart: no)
├── SYSTEM_MAP.md                   # Этот файл
├── KNOWN_ISSUES.md                 # 55 багов + 22 антипаттерна (182 строки)
├── .env                            # Токены, DB_PASSWORD, JWT_SECRET, WEB_PORT
└── requirements.txt                # asyncpg, redis, python-telegram-bot, fastapi, ...
```

## Капсулы (7 active)

| ID | Владелец | TG ID | Бот | Onboarding | Trial |
|----|----------|-------|-----|------------|-------|
| dmitry_rostovcev | Дмитрий Ростовцев | 1260958591 | тестовый | нет | нет |
| dmitry_test | Сергей Карамушкин | 849524981 | @donttouchmyfckngbot2_bot | да | нет |
| victoria_sel | Виктория Сель | 623494151 | @victoria_sel_ai_bot | pre-completed | нет |
| marina_biryukova | Марина Бирюкова | 459213788 | @nagrada_ai_bot | pre-completed | нет |
| yana_berezhnaya | Яна Бережная | 150716139 | @yana_yoga_ai_bot | да | нет |
| yulia_gudymo | Юлия Гудымо | 398239749 | бот Юлии | да | нет |
| nikita_maltsev | Никита Мальцев | 107365522 | @nikita_m_ai_bot | да | 5 дней |

У всех: model=sonnet, effort=standard, streaming=true, voice_input=true, file_tools=true, btw_queue=true.
SYSTEM.md стандартизированы (7/7): PDF, QR, TTS, Image, Markers, Rules.
User Rules: команда /rule + [RULE:] маркер → CLAUDE.md в homes/.
Privacy Mode disabled для 5/7 ботов (donttouchmyfckngbot2 + yulia_g_ai — другие TG-аккаунты).

## База данных PostgreSQL (neura-postgres)

### Данные (на 02.04.2026)

| Таблица | Записей | Топ по capsule_id |
|---------|---------|-------------------|
| diary | **1102** | marina:868, victoria:109, yana:52, dmitry_test:35, yulia:19, nikita:10, dmitry_r:9 |
| memory | **104** | — |
| learnings | **47** | — |

### Схема (001_initial + 002_web = 10 таблиц)

| Таблица | Назначение |
|---------|------------|
| capsules | Реестр капсул (id PK text, name, config JSONB) |
| diary | Дневник диалогов (capsule_id, date, user_message, bot_response, tools_used[]) |
| memory | Долгосрочная память (capsule_id, content, score, embedding VECTOR(1536)) |
| learnings | Обучение/коррекции (capsule_id, type, content) |
| files | Файлы TG (capsule_id, filename, path, mime_type) |
| users | Веб-пользователи (email, password_hash, capsule_id) |
| projects | Папки чатов (user_id, name, pinned) |
| conversations | Треды (user_id, project_id, title, updated_at) |
| messages | Сообщения (conversation_id, role, content, files JSONB) |
| web_files | Файлы Web (user_id, filename, path) |

### Redis (neura-redis)

| Ключ (паттерн) | Назначение | TTL |
|-----------------|------------|-----|
| `btw:{capsule}:{user}` | BTW-очередь сообщений | до flush |
| `rate:{capsule}:{date}` | Счётчик запросов за день | 48h |
| `processing:{capsule}:{user}` | Лок обработки | до завершения |
| `onboarding:{capsule}:{user}` | Состояние onboarding (7 фаз) | 24h |
| `metrics:*` | Per-capsule метрики | varies |

## RAM (типичное использование)

| Компонент | RAM |
|-----------|-----|
| Node.js (Claude Code IDE) | ~12 GB |
| Python (neura-v2 + боты) | ~2.5 GB |
| Claude Code sessions | ~1 GB / сессия |
| Docker (postgres + redis) | ~50 MB |

Рекомендация: не более 3 interactive claude-сессий одновременно.

## Ключевые модули

| Файл | Назначение | Тесты | LOC |
|------|------------|-------|-----|
| core/engine.py | Claude CLI (stateless, streaming) | 26 | 281 |
| core/capsule.py | YAML loader, trial, employees | 13 | 202 |
| core/context.py | Prompt assembly (diary+memory+learnings) | 8 | 107 |
| core/memory.py | CRUD diary/memory/learnings → PG | 10 | 214 |
| core/queue.py | BTW queue + rate limits → Redis | 9 | 122 |
| core/skills.py | SKILL.md parser, per-capsule filter | 7 | 117 |
| transport/telegram.py | Multi-bot TG, streaming, BTW | 25 | 896 |
| transport/web.py | FastAPI REST + WS, auth, rate limit | 28 | 784 |
| transport/protocol.py | Message types, ResponseParser, Telegraph | 37 | 355 |
| transport/app.py | Entry point, signals, graceful shutdown | 4 | 202 |
| provisioning/onboarding.py | 7-phase onboarding flow | — | 1117 |
| provisioning/userbot_connect.py | Telethon QR + phone code login | — | 263 |
| monitoring/health.py | BG health checks (PG/Redis/CLI/bots) | 13 | 151 |
| **Итого Python** | | **230+** | **~5350** |
| **Итого тестов** | 17 файлов | **230+** | **3218** |

## Навигация

| Задача | Куда смотреть |
|--------|---------------|
| Баг в TG-боте | `neura/transport/telegram.py` → handlers |
| Проблема с памятью/diary | `neura/core/memory.py` → CRUD |
| Ошибка Claude CLI | `neura/core/engine.py` → ClaudeEngine.execute() |
| Новая капсула | `config/capsules/*.yaml` + `config/capsules/*/SYSTEM.md` |
| User Rules / /rule | `neura/transport/telegram.py` + `homes/*/CLAUDE.md` |
| Web UI баг | `web/src/`, `neura/transport/web.py` |
| Rate limit / очередь | `neura/core/queue.py` → Redis keys |
| Onboarding flow | `neura/provisioning/onboarding.py` → 7 фаз |
| Userbot подключение | `neura/provisioning/userbot_connect.py` → QR / phone |
| Мониторинг / alerts | `neura/monitoring/` → health.py, alerts.py |
| Error monitor (cron) | `scripts/error-monitor.py` (каждый час :45) |
| HQ-группа создание | `scripts/create-hq-group.py` (идемпотентный) |
| Миграция данных v1→v2 | `scripts/migrate_data.py` |
| Docker / инфра | `docker-compose.yml` + `/etc/systemd/system/neura-v2.service` |
| Архитектура / решения | `/root/Antigravity/docs/neura-v2/ARCHITECTURE.md` |
| Прогресс фаз | `/root/Antigravity/docs/neura-v2/PROGRESS.md` |
| Known Issues | `KNOWN_ISSUES.md` (55 багов + 22 антипаттерна) |
| Скиллы (пул) | `skills/` (84 шт) |
| Тесты | `tests/test_*.py` — pytest |
