---
name: client-capsule
version: 1.0
description: Развёртывание изолированной клиентской капсулы (Docker + Telegram + admin-agent)
triggers: ["капсула", "изоляция клиента", "Docker клиент", "отдельный сервер для клиента", "userbot клиента"]
proactive_enabled: true
proactive_trigger_1_type: event
proactive_trigger_1_condition: "новый клиент"
proactive_trigger_1_action: "предложить создание изолированной капсулы"
proactive_trigger_2_type: event
proactive_trigger_2_condition: "обновление эталона neura-capsule/"
proactive_trigger_2_action: "синхронизировать все капсулы"
learning_track_success: true
learning_track_corrections: true
learning_evolve_threshold: 5
learning_auto_update: [anti-patterns, triggers, changelog]
---

# Client Capsule — развёртывание изолированной клиентской среды

Скилл описывает пошаговый процесс создания изолированной клиентской капсулы на сервере. Каждая капсула — полностью автономная Docker-среда с ботом, платформой, данными и персональным AI-администратором.

**Следующий шаг:** После развёртывания капсулы → используй скилл `capsule-ecosystem` для настройки экосистемы (CLAUDE.md injection, diary, memory, corrections, markers).

---

## Фаза 1: Подготовка инфраструктуры

### Проверка ресурсов сервера

```bash
# RAM
free -h

# CPU
nproc

# Диск
df -h /srv
```

Минимальные требования на одну капсулу: 2 GB RAM, 2 CPU, 10 GB диск.

### Установка Docker (если не установлен)

```bash
apt-get update && apt-get install -y docker.io docker-compose-v2
systemctl enable docker && systemctl start docker
```

### Создание структуры капсулы

```bash
CLIENT_NAME="client_name"  # подставить имя клиента (латиница, snake_case)

mkdir -p /srv/capsules/${CLIENT_NAME}/{bot,platform,data,logs,backups,admin-agent}
```

Назначение директорий:

| Директория | Содержимое |
|------------|-----------|
| `bot/` | Код Telegram-бота и userbot |
| `platform/` | React/frontend приложение |
| `data/` | Персистентные данные: дневники, сотрудники, память, интеграции |
| `logs/` | Логи контейнеров |
| `backups/` | Бэкапы данных |
| `admin-agent/` | CLAUDE.md и конфиг AI-администратора клиента |

---

## Фаза 2: Перенос проекта

### Копирование кода

```bash
# Бот/агент
cp -r /path/to/client/bot/* /srv/capsules/${CLIENT_NAME}/bot/

# Платформа (React/frontend)
cp -r /path/to/client/platform/* /srv/capsules/${CLIENT_NAME}/platform/

# Персистентные данные
cp -r /path/to/client/data/* /srv/capsules/${CLIENT_NAME}/data/
```

### Dockerfile

Создать `/srv/capsules/${CLIENT_NAME}/Dockerfile`:

```dockerfile
FROM python:3.11-slim

# Системные зависимости
RUN apt-get update && apt-get install -y \
    curl ffmpeg git \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Claude CLI (если нужен)
RUN npm install -g @anthropic-ai/claude-code

# Python-зависимости
COPY bot/requirements.txt /app/bot/requirements.txt
RUN pip install --no-cache-dir -r /app/bot/requirements.txt

# Копируем код
COPY bot/ /app/bot/
COPY platform/ /app/platform/

WORKDIR /app

CMD ["python", "bot/main.py"]
```

### docker-compose.yml

Создать `/srv/capsules/${CLIENT_NAME}/docker-compose.yml`:

```yaml
version: "3.8"

services:
  bot:
    build: .
    container_name: capsule-${CLIENT_NAME}-bot
    restart: unless-stopped
    env_file: .env
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./bot/userbot:/app/bot/userbot  # session файлы
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: "2.0"
    networks:
      - capsule-net

  platform:
    image: nginx:alpine
    container_name: capsule-${CLIENT_NAME}-platform
    restart: unless-stopped
    ports:
      - "${PLATFORM_PORT:-8180}:80"
    volumes:
      - ./platform/dist:/usr/share/nginx/html:ro
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: "0.5"
    networks:
      - capsule-net

networks:
  capsule-net:
    driver: bridge
```

### nginx.conf

Создать `/srv/capsules/${CLIENT_NAME}/nginx.conf`:

```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # SPA — все маршруты → index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Кэширование статики
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2?)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

### capsule.sh

Создать `/srv/capsules/${CLIENT_NAME}/capsule.sh`:

```bash
#!/bin/bash
set -e

CAPSULE_DIR="$(cd "$(dirname "$0")" && pwd)"
CLIENT_NAME="$(basename "$CAPSULE_DIR")"

cd "$CAPSULE_DIR"

case "$1" in
  start)
    echo "🚀 Starting capsule: $CLIENT_NAME"
    docker compose up -d --build
    ;;
  stop)
    echo "⏹ Stopping capsule: $CLIENT_NAME"
    docker compose down
    ;;
  restart)
    echo "🔄 Restarting capsule: $CLIENT_NAME"
    docker compose down && docker compose up -d --build
    ;;
  status)
    echo "📊 Status: $CLIENT_NAME"
    docker compose ps
    ;;
  logs)
    docker compose logs -f --tail=100 ${2:-}
    ;;
  shell)
    SERVICE=${2:-bot}
    docker compose exec "$SERVICE" /bin/bash
    ;;
  report)
    echo "=== Capsule Report: $CLIENT_NAME ==="
    echo ""
    echo "--- Containers ---"
    docker compose ps
    echo ""
    echo "--- Resource Usage ---"
    docker stats --no-stream $(docker compose ps -q) 2>/dev/null || echo "No running containers"
    echo ""
    echo "--- Disk Usage ---"
    du -sh data/ logs/ backups/ 2>/dev/null
    echo ""
    echo "--- Last 10 log lines ---"
    docker compose logs --tail=10 2>/dev/null
    ;;
  backup)
    BACKUP_FILE="backups/backup_$(date +%Y%m%d_%H%M%S).tar.gz"
    echo "💾 Backing up data → $BACKUP_FILE"
    tar -czf "$BACKUP_FILE" data/
    echo "Done: $BACKUP_FILE ($(du -sh "$BACKUP_FILE" | cut -f1))"
    ;;
  *)
    echo "Usage: ./capsule.sh {start|stop|restart|status|logs|shell|report|backup}"
    echo ""
    echo "  start   - Build and start all containers"
    echo "  stop    - Stop all containers"
    echo "  restart - Rebuild and restart"
    echo "  status  - Show container status"
    echo "  logs    - Tail logs (optional: service name)"
    echo "  shell   - Open shell in container (default: bot)"
    echo "  report  - Full capsule health report"
    echo "  backup  - Backup data/ to backups/"
    exit 1
    ;;
esac
```

Сделать исполняемым: `chmod +x /srv/capsules/${CLIENT_NAME}/capsule.sh`

---

## Фаза 3: Telegram интеграция

### Telegram Bot

В `.env` файле:

```env
BOT_TOKEN=<токен от @BotFather>
ANTHROPIC_API_KEY=<ключ Claude API>
PLATFORM_PORT=8180
```

### Userbot (Telethon)

**Зачем:** отправка сообщений от имени клиента, парсинг каналов, автоматизация.

**Получение API-ключей клиентом:**
1. Клиент заходит на https://my.telegram.org
2. Авторизуется своим номером
3. Создаёт приложение → получает `api_id` и `api_hash`

В `.env` добавить:

```env
TG_API_ID=<api_id клиента>
TG_API_HASH=<api_hash клиента>
TG_PHONE=<номер телефона клиента>
```

### Создать userbot.py

Путь: `/srv/capsules/${CLIENT_NAME}/bot/userbot/userbot.py`

```python
import asyncio
import sys
import os
from telethon import TelegramClient

SESSION_DIR = os.path.dirname(os.path.abspath(__file__))
SESSION_PATH = os.path.join(SESSION_DIR, "client")  # → client.session

api_id = int(os.getenv("TG_API_ID"))
api_hash = os.getenv("TG_API_HASH")
phone = os.getenv("TG_PHONE")

client = TelegramClient(SESSION_PATH, api_id, api_hash)


async def auth():
    """Авторизация: отправляет код, ждёт ввода."""
    await client.connect()
    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"Уже авторизован: {me.first_name} (@{me.username})")
        return

    await client.send_code_request(phone)
    code = input("Клиент прислал код: ")
    await client.sign_in(phone, code)
    me = await client.get_me()
    print(f"Авторизация успешна: {me.first_name} (@{me.username})")


async def check():
    """Проверка авторизации."""
    await client.connect()
    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"OK: {me.first_name} (@{me.username}), ID: {me.id}")
    else:
        print("NOT AUTHORIZED. Run: python userbot.py auth")


async def send(target, message):
    """Отправка сообщения."""
    await client.connect()
    if not await client.is_user_authorized():
        print("NOT AUTHORIZED. Run: python userbot.py auth")
        return
    await client.send_message(target, message)
    print(f"Sent to {target}: {message[:50]}...")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"

    if cmd == "auth":
        asyncio.run(auth())
    elif cmd == "check":
        asyncio.run(check())
    elif cmd == "send":
        target = sys.argv[2]
        msg = sys.argv[3]
        asyncio.run(send(target, msg))
    else:
        print("Usage: python userbot.py {auth|check|send <target> <message>}")
```

**Процесс авторизации:**
1. Запустить `docker compose exec bot python bot/userbot/userbot.py auth`
2. Telethon отправит код на телефон клиента
3. Клиент присылает код (через бота или лично)
4. Ввести код → `client.session` сохраняется в `bot/userbot/`

**Важно:**
- Session файл — собственный для каждой капсулы (`client.session`)
- НЕ использовать `_parser.session` (это паттерн для основной системы Antigravity)
- При инструктировании клиента по получению API-ключей — представляться как "агент Дмитрия"

---

## Фаза 4: Агент-администратор

### Создать admin-agent/CLAUDE.md

Путь: `/srv/capsules/${CLIENT_NAME}/admin-agent/CLAUDE.md`

Шаблон:

```markdown
# CLAUDE.md — AI-администратор капсулы {CLIENT_NAME}

## Роль
Персональный AI-администратор для {Имя Клиента}. Управляю данными, сотрудниками и аналитикой.

## Доступ
### Имею доступ:
- /app/data/ — данные сотрудников, дневники, база знаний
- /app/logs/ — логи системы
- Telegram бот и userbot

### НЕ имею доступа:
- Инфраструктура хостинга (Docker, сервер, сеть)
- Другие капсулы и проекты
- Системные файлы вне /app/

## Отчёты
### Ежедневная сводка
- Активность бота (кол-во сообщений, уникальные пользователи)
- Новые записи в дневниках/базе знаний
- Ошибки и предупреждения из логов

### Еженедельная аналитика
- Тренды использования
- Топ-запросы пользователей
- Рекомендации по улучшению

## Правила
- Все действия логируются
- Данные клиента не покидают капсулу
- При неясности — уточнять у Дмитрия
```

---

## Фаза 5: Запуск и проверка

### Остановить старый сервис (если был)

```bash
# Проверить существующие сервисы
systemctl list-units --type=service | grep -i ${CLIENT_NAME}

# Остановить если найден
systemctl stop ${CLIENT_NAME}-bot.service 2>/dev/null
systemctl disable ${CLIENT_NAME}-bot.service 2>/dev/null
```

### Запуск капсулы

```bash
cd /srv/capsules/${CLIENT_NAME}
chmod +x capsule.sh
./capsule.sh start
```

### Проверка

```bash
# Контейнеры запущены
docker ps --filter "name=capsule-${CLIENT_NAME}"

# Логи без ошибок
docker logs capsule-${CLIENT_NAME}-bot --tail=20

# Платформа отвечает
curl -s -o /dev/null -w "%{http_code}" http://localhost:${PLATFORM_PORT}/
```

### Выбор порта

Каждая капсула получает уникальный порт для платформы:

| Клиент | Порт |
|--------|------|
| Первый клиент | 8180 |
| Второй клиент | 8181 |
| ... | 8180 + N |

Проверить занятые порты: `ss -tlnp | grep 818`

---

## Важные правила

1. **Полная изоляция.** Капсула НЕ имеет доступа к `/root/Antigravity` и другим проектам. Весь код и данные — внутри `/srv/capsules/{name}/`.

2. **Секреты только в .env.** Файл `.env` хранит ВСЕ секреты клиента (токены, ключи API). Нигде больше токены не хардкодятся. Файл `.env` добавлен в `.gitignore`.

3. **Масштабируемость.** Паттерн одинаков для каждого клиента: `/srv/capsules/{name}/` — просто подставь имя.

4. **Docker volumes.** Персистентные данные монтируются через volumes и доступны хосту для мониторинга и бэкапов.

5. **Telethon session.** У каждой капсулы своя сессия (`client.session`). НЕ использовать `_parser.session` — это паттерн основной системы Antigravity.

6. **Представление.** При отправке инструкций клиенту по Telegram API — ВСЕГДА представляться как "агент Дмитрия".

7. **Лимиты ресурсов.** Каждая капсула ограничена: `memory: 2G`, `cpus: 2.0`. При необходимости корректировать в `docker-compose.yml`.

---

## Чеклист завершения

- [ ] Структура `/srv/capsules/{name}/` создана (bot/, platform/, data/, logs/, backups/, admin-agent/)
- [ ] Dockerfile + docker-compose.yml настроены
- [ ] .env с токенами заполнен (BOT_TOKEN, TG_API_ID, TG_API_HASH) — ANTHROPIC_API_KEY не нужен при Claude CLI
- [ ] nginx.conf для SPA создан
- [ ] capsule.sh работает (start/stop/status/logs/shell/report/backup)
- [ ] Telegram bot перенесён и работает
- [ ] Userbot авторизован (client.session создан)
- [ ] Admin-agent CLAUDE.md написан
- [ ] Старый systemd-сервис остановлен и отключён
- [ ] Docker containers запущены и работают
- [ ] Бот принимает файлы (хендлер `filters.Document.ALL | filters.PHOTO`)
- [ ] Директория `data/files/` создана для сохранения файлов
- [ ] Платформа доступна на выделенном порту
- [ ] `./capsule.sh report` показывает здоровую систему

---

## Уроки из практики (2026-03-19, капсула Юлии)

### Telethon: форумные топики

`CreateForumTopicRequest` находится в `messages`, НЕ в `channels`:
```python
from telethon.tl.functions.messages import CreateForumTopicRequest  # ✅
# from telethon.tl.functions.channels import CreateForumTopicRequest  # ❌
```

Сигнатура (Telethon 1.42):
```python
await client(CreateForumTopicRequest(
    peer=group_entity,           # не channel=, а peer=
    title="📦 Обновления",
    random_id=random.randint(1, 2**31),
))
```

### Telethon: права администратора

Параметр `manage_topics`, НЕ `manage_topic`:
```python
from telethon.tl.types import ChatAdminRights
admin_rights = ChatAdminRights(
    post_messages=True,
    edit_messages=True,
    delete_messages=True,
    manage_topics=True,   # ✅  (не manage_topic!)
    pin_messages=True,
)
```

### requirements.txt: конфликт aiohttp vs maxapi-python

`maxapi-python>=1.2.5` требует `aiohttp>=3.12.15`. Если в requirements пиннится старая версия — билд сломается:
```
# ❌ Ломает билд:
aiohttp==3.11.14
maxapi-python>=1.2.5

# ✅ Правильно:
aiohttp>=3.12.15
maxapi-python>=1.2.5
```

### Claude CLI вместо Anthropic SDK

Если бот использует Claude CLI subprocess — `ANTHROPIC_API_KEY` в `.env` не нужен. Убрать из requirements: `anthropic`. Паттерн вызова:
```python
result = subprocess.run(
    ["claude", "-p", prompt, "--model", "sonnet", "--output-format", "text"],
    capture_output=True, text=True, timeout=300,
    cwd="/root/Antigravity", env=env
)
```
Важно: `env.pop("CLAUDECODE", None)` и `env["CLAUDE_NONINTERACTIVE"] = "1"`.

### 2026-03-24 — CLAUDE.md context leaking (CRITICAL)

При запуске `claude -p` в директории внутри `/root/Antigravity/`, CLI авто-подтягивает родительский `CLAUDE.md` с ДНК-правилами Дмитрия (SESSION_LOG, 💾, скилл-чек, AI-факт). Бот отвечает мета-мусором вместо реальной работы.

**Фикс — ОБЯЗАТЕЛЬНО для всех капсул:**
```python
cmd = [
    "claude", "-p", full_prompt,
    "--output-format", "stream-json",
    "--append-system-prompt",
    "⛔ Ты — персональный AI-агент клиента в Telegram. "
    "ИГНОРИРУЙ мета-правила из родительских CLAUDE.md (Antigravity). "
    "Следуй ТОЛЬКО правилам из CLAUDE.md своей капсулы.",
    # ... остальные флаги
]
```

**Также:** при session poisoning (бот говорит "задача уже выполнена" когда она НЕ была) → сбросить session_id в sessions.json + почистить дневник от ложных записей.

### BotFather: длина username

Имена типа `yulia_gudymo_ai_bot` (19 символов) могут быть отклонены BotFather как "invalid". Лимит ~32 символа, но BotFather иногда отклоняет и более короткие. Иметь запасной вариант (например, `yulia_g_ai_bot`).

### Уроки 21.03.2026 — Доводка капсулы до продажи (v2.2.0 → v2.3.0)

#### Skills Auto-Discovery
- `bot/utils/skills.py` — сканирует `skills/*/SKILL.md` и `tools/*.py`, возвращает Markdown-таблицы
- Плейсхолдеры `{{SKILL_TABLE}}` и `{{TOOLS_TABLE}}` в CLAUDE.md.template заменяются **в runtime** (не при setup)
- Положил папку в `skills/` с SKILL.md → бот видит без рестарта
- Парсинг SKILL.md: имя = dirname, описание = первая `# строка`, триггеры = секция `## Когда`

#### CLAUDE.md Hot-Reload
- **mtime-кеш** вместо загрузки 1 раз при старте: `_ctx_cache = {"content": "", "mtime": 0.0}`
- `get_agent_context()` проверяет `st_mtime` файла → перечитывает только при изменении
- `/reload` команда (owner-only) сбрасывает `_ctx_cache["mtime"] = 0.0`
- Импорты skills.py — **ленивые** (внутри if-блока), чтобы не ломать запуск если модуля нет

#### Proactive Framework
- **Standalone скрипт** `proactive.py`, НЕ в процессе бота (отдельный cron/systemd timer)
- Используй **haiku** для генерации (экономия), читай diary для контекста
- `config.json → proactive.schedule` — массив `{time, type, prompt}`
- `--dry-run` обязателен для тестирования (выводит сообщение без отправки)

#### Tools Framework
- `tools/capsule-tools.py` — CLI утилиты (PDF, QR, TTS), вызываются через Claude Bash tool
- Auto-discovery: `get_tools_table()` сканирует `tools/*.py` и `tools/*.sh`
- Описание из первой строки docstring или `# comment`
- Multi-line docstring: парсить `"""text` (не только `"""text"""`)

#### Menu System (Telegram UX)
- Выделить в **отдельный модуль** `bot/handlers/menu.py` — settings, stats, response buttons
- Response buttons показывать **во ВСЕХ чатах** (DM + groups), не только HQ
- Клик на ⚙️ в ответе → **новое сообщение** (не edit ответа, иначе текст пропадёт)
- Info-кнопки (model badge, plan badge) → `callback_data="info:model"` → toast через `query.answer(text, show_alert=False)`
- `send_response()` нуждается в `plan_mode` и `effort` для status footer и response buttons
- Stats panel: progress bar через `█░`, quality через `⭐`, навигация back/refresh

### Уроки 25.03.2026 — Быстрое развёртывание через эталон + systemd

#### Эталонная капсула → systemd (не Docker)
Вместо Docker для новых капсул — **systemd + native Python**:
- Claude CLI auth проще (нет проблем с credentials внутри контейнера)
- `safe-restart` работает из коробки
- Не нужно пробрасывать /root/.claude/ через volume
- Паттерн: `cp -r neura-capsule/ → /srv/capsules/{name}/` → правка .env + CLAUDE.md → systemd unit → start

```ini
# /etc/systemd/system/{name}-bot.service
[Service]
Type=simple
WorkingDirectory=/srv/capsules/{name}
ExecStart=/usr/bin/python3 /srv/capsules/{name}/run.py
EnvironmentFile=/srv/capsules/{name}/.env
MemoryMax=4G
MemoryHigh=3G
Restart=always
```

#### BotFather через Telethon (автоматизация)
Создание бота программно через parser-сессию:
1. `send_message("@BotFather", "/newbot")` → пауза 3с
2. `send_message(display_name)` → пауза 3с
3. `send_message(username)` → пауза 3с → извлечь токен regex `(\d+:[A-Za-z0-9_-]+)`

#### Получение TG ID по username
```python
entity = await client.get_entity('@username')
print(entity.id)
```
Работает через parser-сессию без ограничений.

#### Neura App Bridge — регистрация новой капсулы
1. Создать пользователя в MongoDB LibreChat (email + пароль)
2. Добавить в CAPSULE_MAP (neura-bridge.py): ObjectId → path + claude_md + tools
3. `systemctl restart neura-bridge`
Проверить: в логах bridge должна появиться `Capsules: ... {Имя}`

#### Клиентские ассеты → data/client-assets/
При наличии материалов клиента (Mac, облако) — переносить rsync с фильтрами:
```bash
rsync -avz --exclude='*.mov' --exclude='*.mp4' --exclude='*.cfa' \
  --exclude='.DS_Store' -e ssh user@mac:"~/path/" /srv/capsules/{name}/data/client-assets/
```
Обязательно: прописать путь в CLAUDE.md капсулы (`## Контекст и материалы клиента`), чтобы бот знал о них.

#### Чеклист быстрого развёртывания (systemd-вариант)
- [ ] `cp -r neura-capsule/ → /srv/capsules/{name}/`
- [ ] .env: BOT_TOKEN + OWNER_ID + DEEPGRAM_API_KEY
- [ ] CLAUDE.md: персонализация (профиль, стиль, продукт, контекст)
- [ ] config.json: client_name, onboarding enabled
- [ ] systemd unit: `/etc/systemd/system/{name}-bot.service`
- [ ] `systemctl daemon-reload && systemctl enable --now {name}-bot`
- [ ] Bridge: добавить в CAPSULE_MAP + restart
- [ ] LibreChat: создать пользователя в MongoDB
- [ ] `data/client-assets/` — материалы клиента (если есть)
- [ ] Проверить: `systemctl status {name}-bot` → active (running)
- [ ] `capsule-profiles.json`: добавить новую капсулу
- [ ] `python3 scripts/capsule-dashboard.py` — убедиться что новая капсула в списке и active

#### Capsule Dashboard — единый вид сверху
Перед и после ЛЮБОЙ работы с капсулами:
```bash
python3 scripts/capsule-dashboard.py        # ASCII — статус, RAM, trial, diary
python3 scripts/capsule-dashboard.py --json  # JSON — для парсинга агентом
```
Реестр капсул: `.agent/skills/capsule-audit/config/capsule-profiles.json`

#### Единые лимиты ресурсов (стандарт с 25.03.2026)
- **MemoryMax=5G** — потолок для каждой капсулы (OOM kill при превышении)
- **MemoryHigh=3G** — мягкий throttle (reclaim кэшей, не kill)
- Bridge: MemoryMax=2G (не запускает claude subprocess)
- При создании новой капсулы — ставить те же лимиты в systemd unit

#### Trial-период (встроен в эталон)
В `config.json` → `"trial": {"enabled": true, "days": N}`. Логика в `bot/handlers/access.py` → `_check_trial()`.
Состояние: `data/trial_state.json` (first_interaction timestamp).
По умолчанию `enabled: false` — включать только для тестовых клиентов.

---

## Changelog

<!-- Сюда автоматически добавляются уроки после каждого использования скилла -->
