---
name: capsule-ecosystem
description: Use when setting up a new client bot capsule with full ecosystem — CLAUDE.md injection, diary, memory, corrections, Telegraph, skills, session persistence. 'настрой экосистему', 'полная капсула', 'новый бот с нуля
usage_count: 2
last_used: 2026-03-31
maturity: seed
---

# Capsule Ecosystem — полная экосистема бота

## Обзор
10-точечный чеклист для развёртывания бота с полной проактивной экосистемой. От пустой капсулы до агента уровня Виктории за 1 сессию.

**Предварительный шаг:** Если капсула ещё не создана (нет Docker-контейнера) → сначала используй скилл `client-capsule` для инфраструктуры.

## Чеклист развёртывания

### 1. CLAUDE.md с изоляцией
Каждая капсула имеет свой CLAUDE.md, изолированный от родительского.

**⚠️ КРИТИЧНО (урок 24.03.2026):** Текст `Родительские CLAUDE.md НЕ применяются` — только декларативный. Claude CLI ВСЁ РАВНО подтягивает CLAUDE.md из parent-директорий при auto-discovery. Техническая защита ОБЯЗАТЕЛЬНА:
- В `streaming_executor.py` / `claude.py` добавить `--append-system-prompt` с блокировкой мета-правил Antigravity
- Без этого бот будет отвечать мета-мусором (💾, SESSION_LOG, скилл-чек) вместо реальной работы
- Чеклист: `grep "append-system-prompt" bot/engine/claude.py` → должен найти

```markdown
# CLAUDE.md — AI-агент [Имя Клиента]

## ⛔ ИЗОЛЯЦИЯ
Ты работаешь в изолированной капсуле [Имя].
Родительские CLAUDE.md НЕ применяются здесь.

## Кто ты
Ты — персональный AI-ассистент [Имя Клиента].
[Описание бизнеса и задач]

## ДНК-правила
### 🔍 Скилл-чек (перед ЛЮБОЙ задачей)
🔍 Скилл: [название] → читаю SKILL.md

### 💾 Фиксация
После каждого ответа бот автоматически записывает в diary.

## Маркеры для бота
- [LEARN:урок] — сохранить для будущих сессий
- [CORRECTION:коррекция] — зафиксировать исправление
- [FILE:/tmp/path] — отправить файл

## Скиллы — маршрутизация
| Скилл | Путь | Когда |
|-------|------|-------|
| word-docx | skills/word-docx/ | документы Word |
| excel-xlsx | skills/excel-xlsx/ | таблицы Excel |
| ppt-generator | skills/ppt-generator/ | презентации |
| image-processing | skills/image-processing/ | изображения |
```

### 2. Загрузка CLAUDE.md в system prompt
Bot.py должен загружать CLAUDE.md при старте и передавать Claude:

```python
def _load_agent_context(max_chars=3000) -> str:
    claude_file = AGENT_DIR / "CLAUDE.md"
    if claude_file.exists():
        content = claude_file.read_text()
        return content[:max_chars] if len(content) > max_chars else content
    return ""

AGENT_CONTEXT = _load_agent_context()

# В первом сообщении сессии:
if msg_count == 0 and AGENT_CONTEXT:
    parts.insert(0, f"[Правила агента]\n{AGENT_CONTEXT}")
```

### 3. Session persistence (JSON + UUID)
```python
SESSIONS_FILE = BOT_DIR / "memory" / "sessions.json"

def get_session(user_id: int) -> dict:
    sessions = json.loads(SESSIONS_FILE.read_text()) if SESSIONS_FILE.exists() else {}
    uid = str(user_id)
    if uid not in sessions:
        sessions[uid] = {"session_id": str(uuid.uuid4()), "messages": 0}
        save_sessions(sessions)
    return sessions[uid]

# Claude CLI:
# Первое сообщение: --session-id UUID
# Последующие: --resume UUID
```

### 4. Diary (ежедневный лог)
```python
def save_diary_entry(topic: str, user_msg: str, bot_response: str):
    diary_dir = AGENT_DIR / "diary"
    diary_dir.mkdir(exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    time_str = datetime.now().strftime("%H:%M")
    entry = f"- **{time_str}** [{topic}] {user_msg[:80]} → {bot_response[:80]}\n"
    with open(diary_dir / f"{today}.md", "a") as f:
        f.write(entry)

def get_today_diary() -> str:
    diary_file = AGENT_DIR / "diary" / f"{datetime.now().strftime('%Y-%m-%d')}.md"
    if diary_file.exists():
        lines = diary_file.read_text().strip().splitlines()
        return "\n".join(lines[-10:])
    return ""
```

Вызывать `save_diary_entry()` после каждого ответа Claude.
Подгружать `get_today_diary()` в промпт первого сообщения.

### 5. Memory/learnings (persistent уроки)
```python
def _save_learning(lesson: str):
    memory_dir = AGENT_DIR / "memory"
    memory_dir.mkdir(exist_ok=True)
    f = memory_dir / "learnings.md"
    lines = f.read_text().splitlines() if f.exists() else []
    lines.append(f"- [{datetime.now().strftime('%Y-%m-%d %H:%M')}] {lesson}")
    if len(lines) > 50: lines = lines[-50:]
    f.write_text("\n".join(lines) + "\n")

def _load_learnings() -> str:
    f = AGENT_DIR / "memory" / "learnings.md"
    return f.read_text()[-1500:] if f.exists() else ""
```

Агент использует маркер `[LEARN:урок]` в ответе → бот парсит и сохраняет.

### 6. Corrections log
```python
def _save_correction(correction: str):
    memory_dir = AGENT_DIR / "memory"
    memory_dir.mkdir(exist_ok=True)
    f = memory_dir / "corrections.md"
    lines = f.read_text().splitlines() if f.exists() else []
    lines.append(f"- [{datetime.now().strftime('%Y-%m-%d %H:%M')}] {correction}")
    if len(lines) > 50: lines = lines[-50:]
    f.write_text("\n".join(lines) + "\n")
```

Агент использует маркер `[CORRECTION:текст]` → бот парсит и сохраняет.

### 7. Парсинг маркеров
```python
import re

def _parse_and_strip_markers(response: str) -> str:
    for m in re.finditer(r'\[LEARN:(.*?)\]', response):
        _save_learning(m.group(1).strip())
    for m in re.finditer(r'\[CORRECTION:(.*?)\]', response):
        _save_correction(m.group(1).strip())
    response = re.sub(r'\[LEARN:.*?\]', '', response)
    response = re.sub(r'\[CORRECTION:.*?\]', '', response)
    return response.strip()
```

Вызывать ПЕРЕД отправкой ответа пользователю.

### 8. Telegraph для длинных ответов
```python
import httpx

async def create_telegraph_page(title: str, content: str) -> str:
    try:
        resp = httpx.post("https://api.telegra.ph/createPage", json={
            "access_token": TELEGRAPH_TOKEN,
            "title": title[:256],
            "content": [{"tag": "p", "children": [content]}],
            "author_name": "AI-агент"
        })
        data = resp.json()
        if data.get("ok"):
            return data["result"]["url"]
    except Exception:
        pass
    return ""

# В отправке ответа:
if len(response) > 4000:
    url = await create_telegraph_page("Ответ", response)
    if url:
        preview = response[:500] + f"\n\n📄 Полный ответ: {url}"
        # отправить preview
```

### 9. [FILE:path] extraction
```python
import re

async def extract_and_send_files(response: str, update, context):
    files = re.findall(r'\[FILE:(.*?)\]', response)
    for fpath in files:
        fpath = fpath.strip()
        if Path(fpath).exists():
            await update.message.reply_document(open(fpath, 'rb'))
    return re.sub(r'\[FILE:.*?\]', '', response).strip()
```

### 10. Model/effort/plan_mode
```python
CONFIG_DEFAULTS = {"model": "sonnet", "effort": "standard", "plan_mode": "auto"}
EFFORT_MAP = {"fast": "low", "standard": "", "deep": "high"}

# Inline keyboard для настроек
def settings_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ Быстро", callback_data="effort_fast"),
         InlineKeyboardButton("⚖️ Стандарт", callback_data="effort_standard"),
         InlineKeyboardButton("🔬 Глубоко", callback_data="effort_deep")]
    ])
```

## Структура директорий капсулы

```
capsule/
├── CLAUDE.md              # Правила агента (изолированный)
├── bot/
│   ├── main.py            # Основной код бота
│   ├── requirements.txt   # Зависимости
│   └── sessions.json      # Сессии (автогенерация)
├── skills/                # Скиллы агента
│   ├── word-docx/
│   ├── excel-xlsx/
│   ├── ppt-generator/
│   ├── image-processing/
│   └── ...
├── diary/                 # Дневники по дням
│   └── 2026-03-19.md
├── memory/                # Persistent память
│   ├── learnings.md       # Уроки (макс 50)
│   └── corrections.md     # Коррекции (макс 50)
├── knowledge/             # База знаний
│   └── *.md
└── data/                  # Файлы пользователя
    └── files/
```

## Быстрый старт

```bash
# 1. Создать структуру
mkdir -p capsule/{bot,skills,diary,memory,knowledge,data/files}

# 2. Скопировать базовые скиллы
for skill in word-docx excel-xlsx ppt-generator image-processing; do
    cp -r /root/Antigravity/.agent/skills/$skill capsule/skills/
done

# 3. Создать CLAUDE.md (шаблон выше)

# 4. Настроить bot/main.py с экосистемой (паттерны выше)

# 5. Для Docker-капсулы:
# docker compose build && docker compose up -d
```

## Чеклист проверки

- [ ] CLAUDE.md загружается в промпт?
- [ ] CLAUDE.md перечитывается при изменении? (hot-reload, не рестарт)
- [ ] Скилл-чек работает? (агент пишет 🔍 Скилл:)
- [ ] Skills auto-discovery работает? (положи `skills/test/SKILL.md` → виден в таблице)
- [ ] Tools auto-discovery работает? (положи `tools/test.py` → виден в таблице)
- [ ] Diary пишется с метаданными? (model, duration, tools_used в записи)
- [ ] [LEARN:] сохраняется? (проверить memory/learnings.md)
- [ ] [CORRECTION:] сохраняется? (проверить memory/corrections.md)
- [ ] [FILE:] отправляется?
- [ ] Длинные ответы → Telegraph?
- [ ] Model/effort/plan настраивается через inline меню?
- [ ] Response buttons видны в DM? (не только HQ)
- [ ] План-режим: бейдж `📋 План` + футер в ответе?
- [ ] `/reload` сбрасывает кеш CLAUDE.md?
- [ ] `proactive.py morning --dry-run` генерирует сообщение?

## Уроки 21.03.2026 — v2.2.0/v2.3.0

### Директории в setup.sh
- `mkdir -p memory/diary data skills tools` — skills/ и tools/ создаются при setup
- `setup.sh` спрашивает про proactive → генерирует crontab
- `config.json` нуждается в секции `proactive: {enabled, schedule: [...]}`

### Docker volumes
- `skills/` и `tools/` монтируются **read-only** (`:ro`) — клиент не должен менять код инструментов через бота
- CLAUDE.md монтируется read-only — hot-reload читает по mtime, не пишет

### Rich diary metadata
- `save_diary_entry(topic, user, bot, metadata={model, duration, tools_used, success})`
- Формат записи: `**14:30** [тема](sonnet, 8s) вопрос → ответ`
- Все хендлеры (text, photo, document, voice) передают metadata

### /reload команда
- Owner-only, сбрасывает `_ctx_cache["mtime"] = 0.0`
- Показывает кол-во обнаруженных skills и tools
- Регистрируется в main.py: `CommandHandler("reload", cmd_reload)`
