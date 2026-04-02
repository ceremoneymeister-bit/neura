---
name: client-integration
version: 1.0
description: Подключение внешних сервисов клиенту (Telegram userbot, iCloud, Deepgram, и др.)
triggers: ["подключить Telegram", "userbot", "авторизация Telethon", "iCloud календарь", "Deepgram", "подключить сервис клиенту", "интеграция клиента"]
---

# Client Integration — подключение сервисов клиенту

Скилл для подключения внешних сервисов к агентской системе клиента.

---

## Модуль 1: Telegram Userbot (Telethon)

**КРИТИЧЕСКИ ВАЖНО — проверенный процесс:**

### Что нужно ЗАРАНЕЕ:
- Номер телефона клиента
- Пароль 2FA (если включён)
- НЕ нужно: создавать новый API на my.telegram.org клиенту

### ⚠️ ДНК-ПРАВИЛО: API ID
ВСЕГДА использовать API ID Дмитрия: `33869550` / `bcc80776767204e74d728936e1e124a3`
НЕ создавать новый API через my.telegram.org клиента — новые API ID не "прогреты", Telegram не доверяет им и коды не доходят.
Session файл привязывается к аккаунту клиента (через номер + код), а API ID — это просто "приложение".

### Процесс авторизации (3 шага через Python-скрипт, НЕ через бота):

**Шаг 1 — Запрос кода:**
```python
import asyncio
from telethon import TelegramClient

API_ID = 33869550
API_HASH = 'bcc80776767204e74d728936e1e124a3'
SESSION = '/путь/к/client_session'

async def step1():
    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.connect()
    result = await client.send_code_request('+7XXXXXXXXXX')
    print(f'phone_code_hash={result.phone_code_hash}')
    await client.disconnect()

asyncio.run(step1())
```
Код придёт клиенту в чат 777000 (Telegram) или по SMS. Сохрани phone_code_hash.

**Шаг 2 — Ввод кода:**
```python
async def step2():
    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.connect()
    try:
        await client.sign_in(phone='+7XXXXXXXXXX', code='XXXXX', phone_code_hash='SAVED_HASH')
        me = await client.get_me()
        print(f'✅ {me.first_name} (@{me.username}) ID:{me.id}')
    except Exception as e:
        print(f'Ошибка: {e}')  # Если SessionPasswordNeededError — переход к шагу 3
    await client.disconnect()

asyncio.run(step2())
```

**Шаг 3 — 2FA (если нужен):**
```python
async def step3():
    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.connect()
    await client.sign_in(password='ПАРОЛЬ_2FA')
    me = await client.get_me()
    print(f'✅ {me.first_name} (@{me.username})')
    await client.disconnect()

asyncio.run(step3())
```

### ❌ Что НЕ работает (не повторять!):
- `force_sms=True` — deprecated в новом Telethon
- `client.start()` в неинтерактивном режиме — зависнет на вводе
- Авторизация через TG-бота (ConversationHandler) — код может не дойти, лишняя сложность
- Создание нового API ID клиенту — код не приходит, новый API не прогрет
- Отправка по числовому user ID сразу после авторизации — нужен username, т.к. кеш контактов пуст

### ✅ Что работает:
- Прямой Python-скрипт с send_code_request → sign_in → sign_in(password=)
- API ID Дмитрия (33869550)
- Трёхшаговый процесс: запрос кода → ввод кода → 2FA пароль
- Отправка сообщений через @username (не числовой ID) для новой сессии

### Проверка работоспособности:
```python
async def check():
    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.connect()
    if await client.is_user_authorized():
        me = await client.get_me()
        print(f'✅ {me.first_name} (@{me.username}) ID:{me.id}')
    await client.disconnect()
```

### Тест отправки:
```python
await client.send_message('@username', 'Тест от агента 🤖')
```

---

## Модуль 2: iCloud Календарь
(заглушка — будет дополнен)
- Скрипт: `scripts/icloud_calendar.py`
- Команды: add, list, events

---

## Модуль 3: Deepgram STT
- Использовать общий API-ключ из `/root/Antigravity/.env`
- Fallback: Whisper (faster-whisper base)
- Скрипт: `scripts/deepgram-transcribe.py`

---

## Модуль 4: Приём файлов в боте

### ⚠️ ДНК-ПРАВИЛО: Бот ОБЯЗАН принимать файлы
Каждый клиентский бот ДОЛЖЕН иметь хендлер для документов и фото. Без этого файлы в HQ-группе остаются «непрочитанными».

### Реализация:
В `main()` бота добавить хендлер ПЕРЕД текстовым:
```python
app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, handle_document))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
```

### Логика `handle_document`:
1. Скачать файл в `agent/data/files/YYYY-MM-DD/filename`
2. Если текстовый файл (.txt, .md, .json, .csv, .py, .xml, .html, .yaml, .log) и < 500KB — прочитать содержимое
3. Передать Claude: имя файла + caption + содержимое (если текст) или "файл сохранён" (если бинарный)
4. Записать в досье сотрудника

### Поддерживаемые типы:
- **Текстовые** (.txt, .md, .json, .csv, .xml, .html, .py, .js, .yaml, .log и др.) — содержимое читается и передаётся Claude
- **Изображения** (.jpg, .png, .gif, .webp) — сохраняются, Claude получает информацию о файле
- **PDF** — сохраняются, для анализа нужны инструменты чтения PDF
- **Прочие** — сохраняются на сервер для дальнейшей обработки

### Индексация (Phase 2):
- Векторизация через vsearch при накоплении файлов
- Автоматическая категоризация по типу контента

---

## Чеклист подключения клиента:
- [ ] Telegram userbot авторизован (session файл создан)
- [ ] Тест отправки сообщения пройден
- [ ] Session скопирован в капсулу
- [ ] iCloud календарь подключён (если нужен)
- [ ] Deepgram настроен (если нужен)
- [ ] Загрузка файлов работает (если нужен)
