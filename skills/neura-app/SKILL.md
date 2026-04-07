---
name: neura-app
description: Веб-интерфейс Neura App — LibreChat fork, Bridge, капсульная архитектура, админ-панель
version: 1.0.0
category: infrastructure
tags: [neura-app, librechat, bridge, docker, web-interface, admin-panel]
usage_count: 3
maturity: tested
last_used: 2026-03-31
proactive_enabled: true
proactive_trigger_1_type: event
proactive_trigger_1_condition: "изменения в Docker/bridge/neura-app"
proactive_trigger_1_action: "предложить аудит и рестарт"
proactive_trigger_2_type: threshold
proactive_trigger_2_condition: "bridge errors > 3 за час"
proactive_trigger_2_action: "предложить диагностику"
learning_track_success: true
learning_track_corrections: true
learning_evolve_threshold: 3
learning_auto_update: [anti-patterns, triggers, changelog]
---

# Neura App — Skill

## Что это
Веб-интерфейс для AI-агентов Neura. Форк LibreChat (MIT, React + Node.js).
Замена/дополнение к Telegram — самостоятельная платформа на случай блокировок.

## Инфраструктура

| Компонент | Расположение | Порт |
|-----------|-------------|------|
| LibreChat (Docker) | `/opt/neura-app/` | 3080 |
| MongoDB | Docker `chat-mongodb` | 27017 |
| MeiliSearch | Docker `chat-meilisearch` | 7700 |
| RAG API | Docker `rag_api` | — |
| VectorDB | Docker `vectordb` | — |
| Neura Bridge | systemd `neura-bridge.service` | 8090 |
| Nginx | `/etc/nginx/sites-available/neura-app` | 443 |

**URL:** https://app.ceremoneymeister.ru
**Домен:** app.ceremoneymeister.ru → 37.233.85.205

## Ключевые файлы

| Файл | Назначение |
|------|-----------|
| `/opt/neura-app/librechat.yaml` | Главный конфиг UI и эндпоинтов |
| `/opt/neura-app/.env` | Переменные окружения (ключи, JWT, порты) |
| `/opt/neura-app/docker-compose.yml` | Основной Docker Compose |
| `/opt/neura-app/docker-compose.override.yml` | Кастомизация (volumes, limits) |
| `/opt/neura-app/bridge/neura-bridge.py` | Bridge: OpenAI API → Claude CLI |
| `/opt/neura-app/branding/` | Логотипы + per-user branding (config.json, branding.js) |
| `/opt/neura-app/branding/config.json` | Маппинг user_id → logo, цвета, title |
| `/opt/neura-app/branding/branding.js` | JS-скрипт per-user брендинга (inject через nginx) |
| `/etc/nginx/sites-available/neura-app` | Nginx конфиг (SSL, proxy) |

## Архитектура Bridge

```
Пользователь → LibreChat UI → POST /v1/chat/completions → Bridge (8090)
                                                              ↓
                                                        Claude CLI
                                                        (--session-id)
                                                              ↓
                                                        SSE stream → UI
```

Bridge (`neura-bridge.py`) принимает OpenAI-compatible запросы и проксирует
к Claude CLI, возвращая ответ как SSE stream. Это позволяет LibreChat
думать, что общается с OpenAI, а на деле работает Claude Max.

## Конфигурация UI

Что включено / выключено для клиентов:

| Элемент | Статус | Настройка |
|---------|--------|-----------|
| Neura Agent (чат) | ✅ вкл | `endpoints.custom` |
| Sidebar (история) | ✅ вкл | `interface.sidePanel: true` |
| Избранное (pin чатов) | ✅ вкл | `interface.bookmarks: true` |
| Поиск по чатам | ✅ вкл | MeiliSearch (SEARCH=true) |
| Загрузка файлов | ✅ вкл | по умолчанию |
| Голосовой ввод (STT) | ✅ вкл | Deepgram Nova-3 |
| Выбор эндпоинтов | ❌ выкл | `endpointsMenu: false` |
| Выбор моделей | ❌ выкл | `modelSelect: false` |
| Параметры (temperature) | ❌ выкл | `parameters: false` |
| Пресеты | ❌ выкл | `presets: false` |
| Agent Constructor | ❌ выкл | `agents: use/create: false` |
| Промпты | ❌ выкл | `prompts: use/create: false` |
| Marketplace | ❌ выкл | `marketplace: use: false` |
| OpenAI/Google/Assistants | ❌ убраны | API ключи закомментированы |

## Управление

### Рестарт
```bash
cd /opt/neura-app && docker compose down && docker compose up -d
```

### Логи
```bash
docker logs LibreChat --tail 50 -f
```

### Bridge
```bash
systemctl status neura-bridge
systemctl restart neura-bridge
curl http://localhost:8090/health
```

### Создание пользователя
Регистрация закрыта (`ALLOW_REGISTRATION=false`).
Создавать через MongoDB:
```bash
docker exec -it chat-mongodb mongosh LibreChat --eval '
  db.users.insertOne({
    name: "Имя",
    email: "email@example.com",
    password: "<bcrypt hash>",
    role: "USER",
    provider: "local",
    createdAt: new Date()
  })
'
```

### Бэкап
```bash
/opt/neura-app/scripts/backup.sh
```

## Сохранение данных

- **Чаты** — MongoDB (`chat-mongodb`), volume `mongodb_data`
- **Поиск** — MeiliSearch, volume `meili_data_v1.35.1`
- **Файлы** — `/opt/neura-app/uploads/`, `/opt/neura-app/images/`
- **Сессии** — JWT (7 дней refresh token)

Все данные переживают рестарт Docker. Пользователь логинится →
все чаты на месте, избранное сохранено.

## Безопасность

- HTTPS (Let's Encrypt, auto-renew)
- Регистрация закрыта
- Social login отключён
- Password reset отключён
- Rate limiting включён (100 req/15min)
- Ban system (20 violations = ban 2h)

## История изменений

### v1.0 (2026-03-23) — Первый деплой
- LibreChat форк задеплоен (Docker, 5 сервисов)
- Neura Bridge (Claude CLI → OpenAI API)
- SSL, Nginx, домен app.ceremoneymeister.ru
- Брендинг (SVG лого, иконки)

### v1.1 (2026-03-23) — Очистка UI
- Скрыты: OpenAI, Google, Assistants, Agent Constructor
- Скрыты: model select, parameters, presets, marketplace
- Исправлен дубликат APP_TITLE (LibreChat → Neura)
- Приветственное сообщение на русском

### v1.2 (2026-03-23) — Избранное
- Включены bookmarks для закрепления чатов
- Sidebar: Избранное (сверху) + Чаты (по датам)

### v2.0 (2026-03-24) — Капсульная архитектура + изображения
- Bridge v2: user→capsule routing через CAPSULE_MAP + MongoDB
- Image handling: extract_user_message() возвращает (text, image_paths)
- resolve_image_url_to_path(): HTTP URL / relative / base64 → local file
- build_image_instruction(): инструкция для Claude Read tool
- process_response_file_markers(): [FILE:] с path validation
- capsule_tools(): полные инструменты с path restrictions
- Per-user branding: nginx sub_filter + branding.js + config.json
- Защита системных файлов в CLAUDE.md капсул
- Полный аудит: 22/22 PASS

## Архитектура капсул (реализовано v2.0, 2026-03-24)

```
LibreChat UI → Bridge v2 → Capsule Routing (CAPSULE_MAP)
                              ↓
                         execute_always_deep()
                         [CLAUDE.md + diary + learnings + corrections]
                              ↓
                         Claude CLI (--allowedTools, --session-id)
                              ↓
                    [parse LEARN/CORRECTION markers, save diary]
                              ↓
                    [process FILE markers, path validation]
                              ↓
                         SSE Stream → UI
```

### Капсульная изоляция

Каждый пользователь LibreChat маппится на свою капсулу:
```python
CAPSULE_MAP = {
    "user_objectid": {
        "path": "/srv/capsules/user_name",
        "claude_md": "/srv/capsules/user_name/CLAUDE.md",
        "name": "Имя",
        "tools": capsule_tools("/srv/capsules/user_name"),
    }
}
```

### Tool sets

| Уровень | Инструменты | Кому |
|---------|-------------|------|
| **ADMIN_TOOLS** | Read, Write, Edit, Glob, Grep, WebSearch, WebFetch, Bash(*) | Дмитрий |
| **capsule_tools(path)** | Read, Write, Edit, Glob, Grep, Web*, Bash(restricted to capsule path) | Марина и капсулы |
| **CLIENT_TOOLS** | Read, Glob, Grep, WebSearch, WebFetch | Default (read-only) |

### Изображения и файлы

- `extract_user_message()` → возвращает `(text, image_paths)`
- `resolve_image_url_to_path()` → URL → локальный путь файла
- `build_image_instruction()` → "Используй Read tool для анализа по пути: ..."
- `process_response_file_markers()` → [FILE:path] → описание файла (с path validation)
- image_instruction вшивается в промпт (работает и при resume-сессии)

### Per-user branding

- nginx `sub_filter` инжектирует `/branding/branding.js` в HTML
- `branding.js` запрашивает `/api/user` → получает user ID → загружает `config.json`
- Применяет: CSS variables, logo, title, badge
- Для добавления пользователя: запись в `config.json` + логотип в `branding/users/{name}/`

### Защита системных файлов

CLAUDE.md каждой капсулы содержит правило: при попытке изменить CLAUDE.md, config.json, .env, bot/ → предупреждение "Согласуйте с Дмитрием".

## Neura Admin Panel (v1.0, 2026-03-24)

Визуальная админ-панель для управления всеми капсулами.

**URL:** https://app.ceremoneymeister.ru/admin/
**Пароль:** `neura-admin-2026`

| Компонент | Расположение | Порт |
|-----------|-------------|------|
| Admin API (FastAPI) | `/opt/neura-admin/api/` | 8091 |
| Admin Frontend (React) | `/opt/neura-admin/frontend/` | — (static) |
| Capsule Registry | `/opt/neura-admin/capsule-registry.json` | — |
| systemd service | `neura-admin.service` | — |

### Архитектура

```
app.ceremoneymeister.ru/admin/       → React SPA (Vite + Tailwind)
app.ceremoneymeister.ru/admin/api/   → FastAPI (port 8091, nginx proxy)
                                        ↓
                          Файловая система, Docker, systemd, MongoDB
```

### Страницы

| Страница | Путь | Описание |
|----------|------|----------|
| Dashboard | `/admin/` | Сетка капсул со статусами, быстрые действия |
| Capsule Detail | `/admin/capsules/:id` | Табы: Overview, Editor, Skills, Memory, Logs |
| Capsule Map | `/admin/map` | vis-network граф связей |
| New Capsule | `/admin/new` | 5-шаговый wizard |
| Users | `/admin/users` | Маппинг пользователь → капсула |
| Audit | `/admin/audit` | Health checks + error logs |

### API endpoints

| Метод | Путь | Описание |
|-------|------|----------|
| POST | /auth/login | JWT авторизация |
| GET | /capsules | Все капсулы со статусом |
| GET | /capsules/{id} | Детали + config + memory stats |
| POST | /capsules/{id}/restart | Рестарт (docker/systemd) |
| POST | /capsules/{id}/stop | Остановка |
| POST | /capsules/{id}/backup | Создание tar.gz |
| POST | /capsules/{id}/duplicate | Дублирование |
| GET/PUT | /capsules/{id}/files/{type} | CLAUDE.md, config, .env |
| GET | /capsules/{id}/skills | Список скиллов |
| GET | /capsules/{id}/memory/* | Diary, learnings, corrections |
| GET | /capsules/{id}/logs | Логи (с фильтрацией ошибок) |
| GET | /system/stats | CPU, RAM, disk |
| GET | /system/graph | Данные для vis-network |

### Capsule Registry

Единый реестр всех капсул (`capsule-registry.json`):
- Нормализует разнородные транспорты: Docker, systemd, SSH
- Каждая запись содержит: path, transport, owner_tg_id, config_paths
- При добавлении новой капсулы — добавить запись в реестр

### Управление

```bash
# Рестарт API
systemctl restart neura-admin

# Логи
journalctl -u neura-admin -f

# Деплой (сборка + рестарт)
/opt/neura-admin/deploy.sh

# Пересборка только фронта
cd /opt/neura-admin/frontend && npm run build && systemctl reload nginx
```

### Безопасность

- API на 127.0.0.1 — только через nginx
- JWT 24h expiry, bcrypt password
- .env маскировка при чтении
- Path traversal защита
- Destructive actions: подтверждение

### Изоляция параллельных чатов (v2.1, 2026-03-26)

Каждый чат в LibreChat = независимая сессия:
- **Сессии** — `get_session(user_id, conversation_id)` возвращает уникальный `session_id` на чат
- **Дневник** — записи тегируются `[web:conv_short]` (первые 8 символов conversation_id)
- **Контекст** — `load_capsule_context(capsule, conversation_id)` фильтрует diary:
  - `[web:текущий_conv]` → показывается
  - `[web:другой_conv]` → НЕ показывается
  - `[telegram]` → показывается во всех чатах (общий контекст)
- **Промпт** — содержит "Это чат #XXX. Каждый чат независим"

### Поддержка Word-файлов (v2.1, 2026-03-26)

`fileTokenLimit: 32000` в `librechat.yaml` → `extractFileContext()` → `mammoth.extractRawText()`.
LibreChat извлекает текст из .docx и вставляет inline в сообщение.
Ранее: файлы не доходили (LangChain выбрасывал нестандартный `{type: "file"}` при сериализации).

### Фикс микрофона Safari/iOS (v2.1, 2026-03-26)

`AudioContext` в `monitorSilence()` не закрывался → оранжевая точка Dynamic Island.
Фикс: `branding.js` перехватывает `createMediaStreamSource` + `visibilitychange` handler.
Скрипт загружается до React-модулей через `<script>` в `index.html`.

### Persistent file storage (v2.2, 2026-03-27)

Файлы из `[FILE:path]` маркеров копируются в persistent storage:
- **Путь**: `/opt/neura-app/bridge/user-files/{user_id}/{date}/{timestamp}_{filename}`
- **Раздача**: nginx напрямую через `/user-files/` (не через Python-прокси)
- **Без TTL** — ссылки не протухают, файлы доступны навсегда
- **Chunk size**: 200 символов (было 20, ломало markdown-ссылки)
- Legacy `/bridge-files/` токены → 410 "попросите сгенерировать заново"

### Client-side file injection (v2.2, 2026-03-28)

LibreChat's `extractFileContext()` проверяет `source === 'text'`, но загруженные файлы имеют `source: 'local'` → контент отбрасывается. `fileTokenLimit` — необходимое, но **не достаточное** условие.

**Решение**: `branding.js` читает текстовые файлы на клиенте через `FileReader`:
- 40+ расширений (.txt, .json, .md, .py, .js, .csv, .yaml и т.д.)
- До 500KB / 50K символов на файл
- Содержимое инжектируется в textarea как `📎 Файл: name.txt` + code block
- Агент видит текст файла прямо в сообщении — 100% надёжность

### Artifact Viewer (v2.2, 2026-03-28)

Боковая панель для просмотра файлов (как Claude Artifacts):
- Клик по файлу/картинке → панель выезжает справа (50% экрана, 100% mobile)
- **Изображения** — inline preview, клик → полный размер
- **PDF** — встроенный embed viewer
- **HTML** — sandboxed iframe (можно ревьюить сайты)
- **Текст/код** — fetch + pre (40+ расширений)
- **Остальное** — кнопка «Скачать файл»
- Кнопки: ⬇ скачать, ↗ новая вкладка, ✕ закрыть
- Закрытие: фон, ✕, ESC

### Login page split-screen (v2.2, 2026-03-26)

Claude-style split-screen: левая половина — AI-изображение (Nano Banana Pro), правая — форма.
CSS + JS injection, no Docker rebuild. Mobile: vertical stack (35vh image / 65vh form).

### Wildcard file types (v2.2, 2026-03-28)

`supportedMimeTypes: [".*"]` в librechat.yaml + `branding.js` interceptor `HTMLInputElement.click()`.
Обход атрибута `accept` на file input. Mac/iOS показывают ВСЕ файлы, не только PDF+изображения.

### Локализация UI (v2.2, 2026-03-28)

`branding.js` MutationObserver заменяет: "Upload to provider" → "Загрузить файл", "Upload Image for Input" → "Загрузить изображение".

### Anti-selection bug (v2.2, 2026-03-28)

CSS `user-select: none` на input controls (кнопки, toolbar). Предотвращает выделение текста при удержании микрофона на mobile.

### Diary tag sync (v2.2, 2026-03-26)

Все Telegram-боты тегируют записи `[telegram]`. Bridge backward compat: записи без `[web:]` = telegram.
Файлы обновлены: 3x streaming_executor.py, 3x diary.py, 2x bot.py + эталон.

### Proactive Health Check (v2.2, 2026-03-28)

`/opt/neura-app/scripts/health-check.py` — 23 проверки:
Docker, Bridge, Nginx, SSL, File serving, Config, Branding assets (6 фич), Capsules, Claude CLI.
**Cron**: ежедневно 06:30 UTC → `/root/Antigravity/logs/neura-healthcheck.log`

## Gap-анализ: Neura App vs Claude Code Terminal

### ✅ Что уже работает как в терминале
| Возможность | Реализация |
|---|---|
| Чат с Claude | Bridge → Claude CLI (claude -p) |
| Инструменты (Read/Write/Edit/Glob/Grep) | `--allowedTools` per capsule |
| WebSearch / WebFetch | Включены в capsule_tools |
| Bash (ограниченный) | Path-restricted per capsule |
| Файлы — текстовые | Client-side FileReader injection |
| Файлы — изображения | base64 через image_url |
| Файлы — генерация (отдача) | Persistent user-files/ + nginx |
| Сессии (resume) | --session-id / --resume per conversation |
| Параллельные чаты | conversation_id isolation |
| Voice input | Deepgram Nova-3 STT |
| Просмотр файлов | Artifact Viewer (side panel) |
| pip install | Разрешён в capsule_tools |

### ⚠️ Частично работает
| Возможность | Статус | Что не хватает |
|---|---|---|
| Tool use visibility | Стриминг показывает "Запускаю Claude..." | Нет отображения каждого tool_use шага в UI |
| Word/PDF upload | fileTokenLimit=32000, mammoth | Для PDF нужен отдельный парсер (не mammoth) |
| web-reader.py | Доступен через Bash | Нет UI-кнопки "открыть URL" |
| Thinking display | Не реализовано | Claude CLI поддерживает --thinking, но bridge не стримит |

### ❌ Не реализовано (требует значительной работы)
| Возможность | Сложность | Как реализовать |
|---|---|---|
| Thinking/reasoning display | Высокая | Парсить thinking блоки из Claude CLI stream, стримить отдельно |
| Real-time tool progress | Средняя | Парсить tool_use events из Claude stream, SSE в UI |
| Agent/subagent spawning | Высокая | Поддержка `--teammate-mode` через bridge |
| Plan mode | Средняя | Передача `--plan` флага, UI для approve/reject |
| MCP tools | Средняя | Пробросить MCP конфиг через bridge |
| Git operations | Низкая | Добавить git в capsule_tools Bash whitelist |
| Code execution sandbox | Высокая | Docker-in-Docker или gVisor |

## Антипаттерны и уроки

### ⚠️ Docker→Bridge UFW блокировка (31.03.2026)
LibreChat v0.8.4 роутит ВСЕ chat-запросы через `/api/agents/chat/:endpoint` (включая custom endpoints).
AgentClient делает HTTP из контейнера → `host.docker.internal:8090`. UFW INPUT policy=DROP → таймаут.

**Диагностика:**
```bash
# Тест связности из контейнера
docker exec LibreChat node -e "
const http = require('http');
http.get({hostname:'host.docker.internal', port:8090, path:'/health', timeout:3000}, r => console.log(r.statusCode))
.on('error', e => console.log('ERROR:', e.message));
"
```

**Фикс:** `ufw allow from 172.16.0.0/12 to any port 8090`

**Симптомы:** "Используя инструменты" → зависание → timeout. Bridge logs = 0 POST. LibreChat logs = `agents/client.js #sendCompletion Operation aborted`.

### ⚠️ agents.use: false → 403 Forbidden
`interface.agents.use: false` в librechat.yaml → LibreChat при рестарте СБРАСЫВАЕТ role permissions `AGENTS.USE=false`.
Это вызывает 403 на `GET /api/agents`. Даже если чат работает (skipAgentCheck пропускает POST), UI ломается.

**Фикс:** `interface.agents.use: true` + `endpoints.agents.disableBuilder: true` + `endpointsMenu: false`.
Пользователи не видят agents UI, но API permission = true.

### ⚠️ Ban хранится в MongoDB
Ban-записи в коллекции `logs` (ключи `ban:*` и `BANS:*`). Переживает рестарт контейнера!
Очистка: `db.logs.deleteMany({key: /^(ban|BAN)/})`
Причина бана: User-Agent без "Mozilla" → `non_browser` violation → 20 violations = ban 2h.

### ⚠️ innerHTML во время стриминга = потеря букв (31.03.2026)
`processProgressMarkers()` и `processThinkingMarkers()` делали `msg.innerHTML = html` пока LibreChat стримил чанки. Чанки между read/write innerHTML терялись → "буквы исчезают".
**Фикс:** НЕ трогать innerHTML пока `.result-streaming` активен. Обработка тегов — после завершения стрима.

### ⚠️ Thinking в тексте ответа = теги мерцают (31.03.2026)
`<neura-thinking>` вставлялся В текст ответа, потом стримился чанками по 200 символов. Тег разбивался → сырые теги мелькали 100-300мс перед обработкой branding.js.
**Фикс:** Thinking отправляется ОДНИМ SSE-чанком целиком, ДО основного текста.

### ⚠️ PDF race condition — файл теряется (31.03.2026)
`extractPdfText()` асинхронный (загрузка pdf.js + парсинг). Если пользователь нажмёт Send до окончания → `_pendingFileContents` пустой → файл не инжектится.
**Фикс:** Счётчик `_filesExtracting` + блокировка Enter/Send пока > 0 + индикатор "Извлекаю текст из файла...".

### ⚠️ History pollution — thinking мусор в контексте (31.03.2026)
MongoDB хранит ответы с `<neura-thinking>` тегами. `get_chat_history_from_db()` передавала этот мусор в контекст → лишние токены + путаница агента.
**Фикс:** `_strip_neura_tags()` очищает теги из history и diary перед сохранением.

## TODO (приоритизировано)

### P0 — Критично
- [x] ~~Download файлов из [FILE:] маркеров~~ → persistent user-files/ (v2.2)
- [x] ~~Файлы не доходят до агента~~ → client-side FileReader injection (v2.2)
- [x] ~~PDF text extraction~~ → pdf.js client-side extraction (v2.2)
- [x] ~~Thinking leak во время стриминга~~ → отдельный SSE чанк (v2.3)
- [x] ~~Буквы исчезают~~ → guard innerHTML during streaming (v2.3)
- [x] ~~PDF race condition~~ → send blocking + indicator (v2.3)
- [ ] Real-time tool progress в UI (парсинг tool_use events)

### P1 — Важно
- [ ] Thinking/reasoning display
- [ ] Auto-sync CAPSULE_MAP при изменении через админку
- [ ] WebSocket для real-time логов в админке
- [ ] Кнопка "Create LibreChat user" в админке (MongoDB insert)

### P2 — Улучшения
- [ ] Telegram userbot в веб-интерфейсе
- [ ] MCP tools через bridge
- [ ] Plan mode UI
- [ ] Git в capsule_tools

---

## Changelog

<!-- Сюда автоматически добавляются уроки после каждого использования скилла -->

### 2026-03-23 — создание скилла, UI v1.2
- Включено Избранное (bookmarks: true), скилл создан (инфра, конфиг, bridge, roadmap)
- Зарегистрирован в таблице маршрутизации CLAUDE.md

### 2026-03-28 — масштабное обновление v2.2 (14 фич)
- Client-side file injection (FileReader, 40+ расширений, обход сломанного extractFileContext)
- PDF extraction (pdf.js), Artifact Viewer (side panel), wildcard file types
- health-check.py (23 проверки), cron 06:30 UTC
- Антипаттерн: LibreChat extractFileContext() проверяет source==='text', загруженные source='local' → контент отбрасывается
- Урок: при дебаге стороннего софта — читать исходники, а не полагаться на документацию

### 2026-03-31 — критический debugging (UFW + agents.use + ban + thinking)
- ROOT CAUSE: UFW блокирует Docker→Bridge (порт 8090). Правило: `ufw allow from 172.16.0.0/12 to any port 8090`
- agents.use: false → 403 Forbidden. Фикс: agents.use: true + disableBuilder: true
- Ban хранится в MongoDB (переживает рестарт!). Очистка: `db.logs.deleteMany({key: /^(ban|BAN)/})`
- Thinking blocks v2: live streaming, пульс, авто-скролл, сворачивание
- Антипаттерн: innerHTML во время стриминга = потеря букв. НЕ трогать DOM пока .result-streaming активен
- Антипаттерн: thinking теги → мерцание (тег разбивается по чанкам). Отправлять ОДНИМ SSE-чанком
- Урок: SESSION_EXPIRY 15мин для LibreChat → рестарт = 401 у всех. Минимум 24ч
- Урок: при 401 — проверить: браузерный кеш, ban в MongoDB, SESSION_EXPIRY, UFW
