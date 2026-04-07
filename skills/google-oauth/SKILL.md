---
name: google-oauth
description: "Подключение Google-сервисов (Sheets, Drive, Calendar, Gmail) к клиентским Telegram-ботам через OAuth2"
version: 1.0.0
category: infrastructure
tags: [google, oauth, sheets, drive, calendar, gmail, integration]
usage_count: 0
maturity: seed
last_used: null
proactive_enabled: true
proactive_trigger_1_type: threshold
proactive_trigger_1_condition: "401 ошибки в логах капсул"
proactive_trigger_1_action: "проверить и обновить OAuth токены"
proactive_trigger_2_type: schedule
proactive_trigger_2_condition: "еженедельно"
proactive_trigger_2_action: "проверить срок действия credentials"
learning_track_success: true
learning_track_corrections: true
learning_evolve_threshold: 5
learning_auto_update: [anti-patterns, triggers, changelog]
---

# Google OAuth Skill

## Purpose
Подключение Google-сервисов к клиентским Telegram-ботам через OAuth2.
Один OAuth-клиент (ceremoneymeister@gmail.com) для всех ботов — токен у каждого свой.

## When to Use
- "подключить Google", "Google Sheets", "Google Drive", "Google Calendar", "Gmail"
- `/connect_google` команда в ботах
- Интеграция с Google API через токены

## Architecture

### OAuth Flow
1. Пользователь (админ) отправляет `/connect_google` в Telegram-бот
2. Бот генерирует OAuth URL через `GoogleOAuthFlow.get_auth_url(user_id)`
3. Пользователь нажимает inline-кнопку, авторизуется в Google
4. Google редиректит на `http://localhost/?code=XXXXX` (страница не загрузится — это нормально)
5. Пользователь копирует URL из адресной строки и отправляет боту
6. Бот вытаскивает code через `exchange_code()`, обменивает на токены, сохраняет в `google_token.json`

### Key Components
- **`google_oauth_bot.py`** — модуль с классом `GoogleOAuthFlow` + шаблоны сообщений
- **`credentials.json`** — OAuth-клиент (Desktop App) ceremoneymeister@gmail.com
- **`google_token.json`** — токен пользователя (создаётся после авторизации)

### Scopes (по умолчанию)
- `spreadsheets` — Google Sheets
- `drive.file` — Google Drive (только файлы созданные ботом)
- `calendar` — Google Calendar
- `documents` — Google Docs
- `gmail.readonly` — Gmail (только чтение)

## Integration Pattern

### Шаг 1: Копировать файлы в бот
```bash
cp services/google/google_oauth_bot.py <bot_dir>/
cp services/google/credentials.json <bot_dir>/
```

### Шаг 2: Добавить в bot.py (3 блока)

**Блок 1 — Import + Init (после конфига):**
```python
from google_oauth_bot import GoogleOAuthFlow, auth_start_message, auth_success_message, auth_error_message

google_oauth = GoogleOAuthFlow(
    credentials_file=str(Path(__file__).parent / 'credentials.json'),
    token_file=str(Path(__file__).parent / 'google_token.json'),
)
```

**Блок 2 — Команда /connect_google:**
```python
async def cmd_connect_google(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):  # admin-check (адаптировать под бота)
        await update.message.reply_text("Нет доступа.")
        return
    if google_oauth.is_authorized():
        await update.message.reply_text("Google уже подключён! Сервисы доступны.")
        return
    auth_url = google_oauth.get_auth_url(update.effective_user.id)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔐 Подключить Google", url=auth_url)]
    ])
    await update.message.reply_text(
        auth_start_message(), parse_mode="MarkdownV2", reply_markup=keyboard
    )
```

**Блок 3 — Перехват URL в текстовом хендлере (В НАЧАЛЕ handle_text/handle_message):**
```python
# Google OAuth code intercept
if google_oauth.is_waiting_for_code(user_id):
    result = google_oauth.exchange_code(user_id, text)
    if result['success']:
        await update.message.reply_text(
            auth_success_message(result['scopes']), parse_mode="MarkdownV2"
        )
    else:
        await update.message.reply_text(
            auth_error_message(result['error']), parse_mode="MarkdownV2"
        )
    return
```

### Шаг 3: Регистрация handler
```python
app.add_handler(CommandHandler("connect_google", cmd_connect_google))
# ВАЖНО: добавить ПЕРЕД текстовым MessageHandler
```

### Шаг 4: Рестарт бота

## Anti-Patterns
- **НЕ** создавать отдельные OAuth-клиенты — один клиент Дмитрия для всех
- **НЕ** хардкодить scopes — использовать DEFAULT_SCOPES из модуля
- **НЕ** забывать admin-check — OAuth доступен ТОЛЬКО админам
- **НЕ** забывать перехват в текстовом хендлере — без него exchange не сработает
- **НЕ** использовать ConversationHandler — `GoogleOAuthFlow._pending` сам управляет состоянием

## Deployment per Bot

### Victoria (@victoria_sel_ai_bot)
- Dir: `projects/Producing/Victoria_Sel/bot/`
- Admin check: `is_authorized(update)`
- Restart: `safe-restart victoria-bot`

### Marina (@nagrada_ai_bot)
- Dir: `projects/AI_Business/Marina_Biryukova/agent/bot/`
- Admin check: `is_admin(update)`
- Restart: `safe-restart nagrada-bot`

### Yulia (Docker)
- Dir: `/srv/capsules/yulia_gudymo/bot/`
- Admin check: `is_allowed(update)` (YULIA_ID/DMITRY_ID)
- docker-compose: добавить volume `./data/google_token.json:/app/bot/google_token.json`
- Rebuild: `cd /srv/capsules/yulia_gudymo && docker compose build --no-cache yulia-bot && docker compose up -d yulia-bot`

### Maxim (SSH)
- Dir: `projects/Producing/Maxim_Belousov/agent-system/bot/`
- Admin check: `_is_owner(update)` (OWNER_ID)
- Deploy: `scp` файлов → `systemctl restart maxim-agent`

## Verification Checklist
1. `/connect_google` от не-админа → "Нет доступа"
2. `/connect_google` от админа → кнопка с OAuth URL
3. Нажать кнопку → авторизоваться → скопировать URL → отправить боту
4. Бот подтверждает: "Google подключён! 5 сервисов"
5. Повторно `/connect_google` → "Уже подключён"
6. `google_token.json` создан с `refresh_token`
7. Обычные текстовые сообщения работают (без регрессии)

## Token Refresh
`GoogleOAuthFlow.get_access_token()` автоматически рефрешит токен за 5 минут до истечения.
Для использования в скиллах:
```python
token = google_oauth.get_access_token()
# Использовать token в headers: Authorization: Bearer {token}
```

---

## Changelog

<!-- Сюда автоматически добавляются уроки после каждого использования скилла -->


- 2026-04-07: 5 использований, success rate 100.0%, avg latency 39.6s