# Google OAuth — Bot Integration Snippets

## Victoria (bot.py)

### Import + Init (после строки `VICTORIA_ID = 623494151`)
```python
from google_oauth_bot import GoogleOAuthFlow, auth_start_message, auth_success_message, auth_error_message
google_oauth = GoogleOAuthFlow(
    credentials_file=str(BOT_DIR / 'credentials.json'),
    token_file=str(BOT_DIR / 'google_token.json'),
)
```

### Command handler
```python
async def cmd_connect_google(update, ctx):
    if not is_authorized(update):
        await update.message.reply_text("Нет доступа.")
        return
    ...
```

### Text intercept (начало handle_message, после `if not text: return`)
```python
if google_oauth.is_waiting_for_code(user_id):
    ...
    return
```

### Registration (перед text handler)
```python
app.add_handler(CommandHandler("connect_google", cmd_connect_google))
```

---

## Marina (bot.py)

### Import + Init (после `EMPLOYEES_DIR`)
```python
from google_oauth_bot import GoogleOAuthFlow, auth_start_message, auth_success_message, auth_error_message
google_oauth = GoogleOAuthFlow(
    credentials_file=str(Path(__file__).parent / 'credentials.json'),
    token_file=str(Path(__file__).parent / 'google_token.json'),
)
```

### Admin check: `is_admin(update)`

### Text intercept: начало handle_text, после проверки доступа

---

## Yulia (main.py)

### Import + Init (после `active_tasks: set = set()`)
```python
from google_oauth_bot import GoogleOAuthFlow, auth_start_message, auth_success_message, auth_error_message
google_oauth = GoogleOAuthFlow(
    credentials_file=str(BOT_DIR / 'credentials.json'),
    token_file=str(BOT_DIR / 'google_token.json'),
)
```

### Admin check: `is_allowed(update)`

### Docker volume: `./data/google_token.json:/app/bot/google_token.json`

---

## Maxim (modular)

### bot/handlers/commands.py — добавить cmd_connect_google
### bot/handlers/text.py — добавить перехват в handle_text
### bot/main.py — добавить CommandHandler
### Admin check: `_is_owner(update)`
