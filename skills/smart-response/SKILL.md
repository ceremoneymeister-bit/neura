---
name: smart-response
description: "Telegraph для длинных ответов — автоматическая публикация >4000 символов как Telegraph-страниц"
version: 1.0.0
category: development
tags: [telegraph, long-response, telegram, chunking, fallback]
usage_count: 0
maturity: seed
last_used: null
---

# Smart Response — Telegraph для длинных ответов

## Назначение
Длинные ответы агента (>4000 символов) отправляются как Telegraph-страница с превью и ссылкой, вместо разбивки на чанки.

## Пороги
- `MAX_MSG_LEN = 4000` — лимит Telegram
- `TELEGRAPH_PREVIEW_LEN = 800` — длина превью перед ссылкой
- Telegram API: `https://api.telegra.ph`

## Цепочка отправки (fallback)
1. **Короткий** (<=4000) → обычное сообщение с `reply_markup`
2. **Длинный** (>4000) → Telegraph-страница + превью 800 символов + ссылка
3. **Fallback** (Telegraph недоступен) → старые чанки по 4000

## Эталонная реализация

### 1. Получение/кэширование токена
```python
TELEGRAPH_API = "https://api.telegra.ph"
_telegraph_token = None

async def _get_telegraph_token() -> str:
    global _telegraph_token
    if _telegraph_token:
        return _telegraph_token
    token_file = TOKEN_PATH  # Path к .telegraph_token
    if token_file.exists():
        _telegraph_token = token_file.read_text().strip()
        return _telegraph_token
    url = f"{TELEGRAPH_API}/createAccount?short_name=BotName&author_name=AI+Agent"
    try:
        resp = urllib.request.urlopen(url, timeout=10)
        data = json.loads(resp.read())
        if data.get("ok"):
            _telegraph_token = data["result"]["access_token"]
            token_file.write_text(_telegraph_token)
            return _telegraph_token
    except Exception as e:
        logger.error(f"Telegraph createAccount error: {e}")
    return ""
```

### 2. Markdown → Telegraph-ноды
```python
def _md_to_telegraph_nodes(text: str) -> list:
    nodes = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            nodes.append({"tag": "br"})
            continue
        if stripped.startswith("### "):
            nodes.append({"tag": "h4", "children": [stripped[4:]]})
        elif stripped.startswith("## "):
            nodes.append({"tag": "h3", "children": [stripped[3:]]})
        elif stripped.startswith("# "):
            nodes.append({"tag": "h3", "children": [stripped[2:]]})
        elif stripped.startswith("- ") or stripped.startswith("* "):
            nodes.append({"tag": "li", "children": [stripped[2:]]})
        elif stripped.startswith("```"):
            continue
        elif stripped.startswith("`") and stripped.endswith("`"):
            nodes.append({"tag": "code", "children": [stripped.strip("`")]})
        elif stripped.startswith("> "):
            nodes.append({"tag": "blockquote", "children": [stripped[2:]]})
        else:
            processed = re.sub(r'\*\*(.+?)\*\*', lambda m: m.group(1).upper(), stripped)
            nodes.append({"tag": "p", "children": [processed]})
    return nodes
```

### 3. Создание страницы
```python
async def create_telegraph_page(title: str, content: str) -> str:
    token = await _get_telegraph_token()
    if not token:
        return ""
    nodes = _md_to_telegraph_nodes(content)
    payload = json.dumps({
        "access_token": token,
        "title": title[:256],
        "author_name": "AI Agent",
        "content": nodes,
    }).encode("utf-8")
    try:
        req = urllib.request.Request(
            f"{TELEGRAPH_API}/createPage",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read())
        if data.get("ok"):
            return data["result"]["url"]
    except Exception as e:
        logger.error(f"Telegraph createPage error: {e}")
    return ""
```

## Конфигурация по ботам

| Бот | short_name | author_name | token_file |
|-----|-----------|-------------|------------|
| Максим | MaximAgent | AI Agent | `../../.telegraph_token` |
| Марина | NagradaAI | AI Награда | `Path(__file__).parent / ".telegraph_token"` |
| Виктория | VictoriaAI | AI Виктории | `BOT_DIR / ".telegraph_token"` |
| Юлия | YuliaAI | AI Юлии | `DATA_DIR / ".telegraph_token"` (Docker volume!) |

## Anti-patterns
- **НЕ** обрезай ответ агента — бот сам обработает длину
- **НЕ** пиши "ответ слишком длинный" — дай полный ответ
- **НЕ** храни токен в /tmp (потеряется при рестарте)
- **НЕ** используй Markdown parse_mode для превью (может сломаться на незакрытых тегах)
- Юлия Docker: token в `DATA_DIR` (volume mount), НЕ в `BOT_DIR` (не персистентен)

## ДНК-правило для CLAUDE.md ботов
```
### 📄 Длинные ответы → Telegraph (НЕУДАЛЯЕМОЕ)
Если твой ответ длинный — НЕ обрезай его.
Бот автоматически: <=4000 → сообщение, >4000 → Telegraph + превью + ссылка.
Структурируй ответ (## заголовки, - списки, > цитаты) — Telegraph красиво отобразит.
НЕ пиши "ответ слишком длинный" — дай полный ответ.
```

## Уроки из практики

### Развёртывание (19.03.2026)
- Telegraph внедрён одновременно во все 4 бота (Виктория, Марина, Юлия, Максим) за одну сессию
- ДНК-правило добавлено в 4 CLAUDE.md ботов + главный CLAUDE.md
- Паттерн: сначала эталонная реализация в Victoria → копирование с адаптацией в остальных

### Архитектурные различия между ботами

**Модульность:**
- Виктория, Марина, Юлия — Telegraph-функции встроены прямо в `bot.py`
- Максим — выделен отдельный модуль `bot/utils/response.py` (лучший паттерн для масштабирования)

**Preview-генерация (два подхода):**
1. `rsplit` (Виктория, Марина, Юлия) — обрезает по последнему `\n`, сохраняет абзацы:
   ```python
   preview = full[:800].rsplit("\n", 1)[0] + "\n\n..."
   ```
2. Простое обрезание (Максим) — может обрезать посреди слова:
   ```python
   preview = full[:800] + "\n\n..."
   ```
   → **Рекомендация:** использовать `rsplit` подход во всех ботах

**Обработка перед отправкой:**
- Максим Agent: парсит маркеры `[FILE:/path]`, `[LEARN:...]`, `[CORRECTION:...]` ДО Telegraph
- Демо-бот Максима: интеграция с TTS-кнопками (200-2000 символов — показать кнопку "Озвучить")
- Марина: отдельная обработка демо-ответов (callbacks через `demo_key`)

### Обработка ошибок

**Трёхуровневый fallback (подтверждён на всех ботах):**
1. Короткий → `reply_text(parse_mode="Markdown")` → если ошибка → `reply_text()` без parse_mode
2. Длинный → Telegraph → если URL пуст → чанки по 4000
3. Чанки → последний чанк получает `reply_markup`, остальные без

**Markdown parse_mode fallback:** Все боты (кроме Юлии) оборачивают `reply_text` в try/except — при ошибке Markdown отправляют plain text. Юлия отправляет всё без parse_mode (упрощение для Docker).

### Токен-менеджмент

**Паттерн (одинаковый у всех):**
1. Глобальная переменная `_telegraph_token` (кэш в памяти)
2. Файл `.telegraph_token` (персистентный кэш)
3. `createAccount` API (создание нового, если файла нет)

**Docker (Юлия):** Токен ОБЯЗАН быть в `DATA_DIR` (примонтированный volume), не в `BOT_DIR` — иначе потеряется при пересборке контейнера.

**Таймауты:** createAccount = 10 сек, createPage = 15 сек. Retry-логики нет — при timeout сразу fallback на чанки.

### Потенциальные edge-cases (обнаружены при аудите)

1. **Вложенный Markdown:** Парсер построчный — не поддерживает вложенные списки, таблицы, многострочные блоки кода. Для большинства ответов агента это ОК, но сложные технические ответы могут потерять форматирование
2. **Лимит размера страницы Telegraph:** ~64KB soft limit. Очень длинные ответы (>60K символов) могут молча обрезаться Telegraph API
3. **Rate limiting:** Telegraph позволяет ~5 req/sec. При массовой рассылке или нагрузке возможен 429 — текущий код обработает как ошибку → fallback чанки
4. **Конкурентное создание токена:** Глобальная переменная не thread-safe, но для asyncio (один event loop) это не проблема
5. **Заголовок усекается до 256 символов** — реализовано корректно во всех ботах

### Паттерн HQ-группы (Максим)

В HQ-группе добавляются inline-кнопки выбора модели (Sonnet/Opus/Haiku) через `menu_button(model)`. В обычных чатах кнопки не показываются. Это **не** часть smart-response, но тесно связано — `reply_markup` передаётся в ту же `send_response`.

### Checklist при добавлении Telegraph в нового бота

1. [ ] Определить `TOKEN_PATH` — персистентное хранилище (не /tmp, не build dir)
2. [ ] Задать уникальные `short_name` и `author_name` для createAccount
3. [ ] Реализовать fallback: Telegraph → чанки → plain text
4. [ ] Обработать Markdown parse_mode ошибки (try/except → plain)
5. [ ] Добавить ДНК-правило в CLAUDE.md бота
6. [ ] Проверить `[FILE:/path]` маркеры — извлечь ДО отправки в Telegraph
7. [ ] `reply_markup` только на последнем сообщении (при чанках)
8. [ ] Для Docker: token в volume, не в image layer
