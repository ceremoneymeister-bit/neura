---
name: notebooklm-setup
description: Полная установка и настройка NotebookLM на любом Linux-сервере. Включает обход геоблока, авторизацию через noVNC, автодиагностику и обёртку CLI. Используй при запросах «установи NotebookLM», «подключи NotebookLM», «настрой NLM на сервере».
proactive_enabled: false
proactive_trigger_1_type: event
proactive_trigger_1_condition: "установка NotebookLM на новый сервер"
proactive_trigger_1_action: "запустить setup workflow"
learning_track_success: true
learning_track_corrections: true
learning_evolve_threshold: 5
learning_auto_update: [anti-patterns, triggers, changelog]
---

# NotebookLM Setup — установка на сервер с нуля

Скилл для развёртывания Google NotebookLM (через `notebooklm-py`) на headless Linux-сервере.
Решает три главные проблемы: **геоблок** (РФ/СНГ), **отсутствие GUI** для логина, **надёжность**.

## Когда использовать

- «Установи NotebookLM на сервер»
- «Подключи NLM»
- «Настрой NotebookLM»
- Первая настройка на новом сервере
- Перенос авторизации между серверами
- Восстановление после протухания сессии

## Архитектура

```
┌──────────────────────────────────────────────┐
│                  Сервер (VPS)                 │
│                                              │
│  notebooklm-py ──► Cloudflare WARP (proxy)   │
│       │              socks5://127.0.0.1:40000 │
│       ▼                     │                │
│  ~/.notebooklm/             ▼                │
│  storage_state.json    Внешний IP (не РФ)    │
│                             │                │
│  CLI обёртка: nlm           ▼                │
│  (авто-прокси + retry)   Google API          │
└──────────────────────────────────────────────┘
```

## Установка (пошагово)

### Шаг 1: Зависимости

```bash
# Python пакеты
pip install "notebooklm-py[browser]" httpx[socks] socksio --break-system-packages

# Playwright Chromium (для авторизации)
playwright install chromium

# Виртуальный дисплей + VNC (для логина через браузер)
apt-get install -y xvfb x11vnc novnc websockify
```

### Шаг 2: Cloudflare WARP (обход геоблока)

NotebookLM заблокирован для IP из РФ/СНГ. WARP даёт нейтральный IP.

```bash
# Установка
curl -fsSL https://pkg.cloudflareclient.com/pubkey.gpg | \
  gpg --yes --dearmor --output /usr/share/keyrings/cloudflare-warp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/cloudflare-warp-archive-keyring.gpg] \
  https://pkg.cloudflareclient.com/ $(lsb_release -cs) main" \
  > /etc/apt/sources.list.d/cloudflare-client.list
apt-get update -qq && apt-get install -y cloudflare-warp

# Настройка (proxy-режим, не трогает основной трафик)
warp-cli --accept-tos registration new
warp-cli --accept-tos mode proxy
warp-cli --accept-tos proxy port 40000
warp-cli --accept-tos connect

# Проверка (должен показать не-РФ IP)
curl -x socks5://127.0.0.1:40000 -s https://ipinfo.io/json | python3 -m json.tool
```

**Важно:** WARP в режиме `proxy` не влияет на основной трафик сервера. Только приложения, явно использующие `socks5://127.0.0.1:40000`, идут через WARP.

### Шаг 3: Авторизация через noVNC

На headless-сервере нет браузера. Решение — поднять виртуальный дисплей + VNC + web-доступ.

```bash
# Запуск виртуального дисплея + VNC + noVNC
nohup bash -c '
export DISPLAY=:99
Xvfb :99 -screen 0 1280x800x24 &
sleep 1
x11vnc -display :99 -nopw -listen 0.0.0.0 -rfbport 5900 -shared -forever &
sleep 1
websockify --web /usr/share/novnc/ 6080 localhost:5900 &
sleep 1
/root/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome \
  --no-sandbox --disable-gpu --window-size=1280,800 \
  --user-data-dir=/root/.notebooklm/browser_profile \
  "https://notebooklm.google.com/" &
' > /tmp/novnc.log 2>&1 &

sleep 5
echo "Открой в браузере: http://IP_СЕРВЕРА:6080/vnc.html"
```

**Действия пользователя:**
1. Открыть `http://IP_СЕРВЕРА:6080/vnc.html` в браузере
2. Нажать "Connect"
3. Залогиниться в Google аккаунт
4. Дождаться главной страницы NotebookLM
5. Сообщить что готово

**Сохранение сессии (выполняет агент):**
```python
import asyncio
from playwright.async_api import async_playwright

async def save():
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            "/root/.notebooklm/browser_profile", headless=True
        )
        await ctx.storage_state(path="/root/.notebooklm/storage_state.json")
        await ctx.close()
        print("✅ Сессия сохранена")

asyncio.run(save())
```

**Остановка noVNC (после логина):**
```bash
pkill -f "x11vnc|websockify|Xvfb"
pkill -f "chrome.*notebooklm"
```

### Шаг 4: CLI обёртка с авто-прокси

```bash
cat > /usr/local/bin/nlm << 'EOF'
#!/bin/bash
# NotebookLM CLI — обёртка с WARP прокси и автоматическим retry
export ALL_PROXY=socks5://127.0.0.1:40000
export HTTPS_PROXY=socks5://127.0.0.1:40000

# Проверка WARP
if ! warp-cli --accept-tos status 2>/dev/null | grep -q "Connected"; then
    warp-cli --accept-tos connect 2>/dev/null
    sleep 3
fi

# Retry логика: 1 повтор при ошибке авторизации
output=$(notebooklm "$@" 2>&1)
rc=$?

if [ $rc -ne 0 ] && echo "$output" | grep -qi "CSRF\|auth\|cookie\|location=unsupported"; then
    echo "⚠️ Ошибка авторизации/геоблока. Пробую переподключить WARP..." >&2
    warp-cli --accept-tos disconnect 2>/dev/null
    sleep 2
    warp-cli --accept-tos connect 2>/dev/null
    sleep 3
    output=$(notebooklm "$@" 2>&1)
    rc=$?
fi

echo "$output"
exit $rc
EOF
chmod +x /usr/local/bin/nlm
```

### Шаг 5: Установка скилла Claude Code

```bash
ALL_PROXY=socks5://127.0.0.1:40000 notebooklm skill install
```

### Шаг 6: Проверка

```bash
nlm list                              # Список блокнотов
nlm create "Тест"                     # Создать блокнот
nlm source add "https://example.com"  # Добавить источник
nlm ask "О чём этот сайт?"            # Задать вопрос
```

## Диагностика ошибок

### Дерево решений

```
Ошибка?
├── "location=unsupported" / "CSRF token not found"
│   ├── WARP подключён? → warp-cli --accept-tos status
│   │   ├── Нет → warp-cli --accept-tos connect
│   │   └── Да → curl -x socks5://127.0.0.1:40000 https://ipinfo.io/json
│   │       └── country=RU? → warp-cli disconnect && warp-cli connect
│   └── Прокси передаётся? → ALL_PROXY=socks5://127.0.0.1:40000 notebooklm list
│
├── "Auth/cookie error" / "Not authenticated"
│   ├── Сессия есть? → ls ~/.notebooklm/storage_state.json
│   │   ├── Нет → Повторить авторизацию (Шаг 3)
│   │   └── Да, но старая → Сессия протухла (~2 недели). Повторить Шаг 3.
│   └── notebooklm auth check --test
│
├── "socksio not installed"
│   └── pip install httpx[socks] socksio --break-system-packages
│
├── "Rate limit" / "No result found for RPC ID"
│   └── Подождать 5-10 минут, повторить
│
├── Timeout при генерации
│   └── Нормально для audio (10-20 мин), video (15-45 мин)
│       Использовать: nlm artifact wait <id> --timeout 1800
│
└── Playwright ошибка при логине
    └── apt-get install -y xvfb && playwright install chromium
```

### Быстрые команды диагностики

```bash
# Статус WARP
warp-cli --accept-tos status

# Текущий IP через WARP
curl -x socks5://127.0.0.1:40000 -s https://ipinfo.io/json | jq .country

# Статус авторизации
ALL_PROXY=socks5://127.0.0.1:40000 notebooklm auth check

# Полная проверка с сетевым тестом
ALL_PROXY=socks5://127.0.0.1:40000 notebooklm auth check --test

# Лог noVNC (если логин не работает)
cat /tmp/novnc.log
```

## Обновление сессии (когда протухнет)

Сессия живёт ~2 недели. Признак протухания: `Auth/cookie error`.

```bash
# 1. Поднять noVNC (Шаг 3)
# 2. Пользователь логинится в браузере
# 3. Сохранить сессию (Python скрипт из Шага 3)
# 4. Остановить noVNC
# 5. Проверить: nlm list
```

## Перенос на другой сервер

```bash
# На исходном сервере:
cat ~/.notebooklm/storage_state.json | base64 > /tmp/nlm_session.b64

# На целевом сервере:
# 1. Выполнить Шаги 1-2 (установка + WARP)
# 2. Перенести сессию:
mkdir -p ~/.notebooklm
base64 -d < /tmp/nlm_session.b64 > ~/.notebooklm/storage_state.json
# 3. Создать обёртку (Шаг 4)
# 4. Проверить: nlm list
```

## Примеры использования

### Быстрый ресёрч
```bash
nlm create "Исследование: AI агенты 2026"
nlm source add "https://arxiv.org/abs/..."
nlm source add "https://blog.example.com/..."
nlm ask "Какие ключевые тренды в AI-агентах?"
nlm ask "Есть ли противоречия между источниками?"
nlm generate mind-map
nlm download mind-map ./ai-agents-map.json
```

### Подкаст из документов
```bash
nlm create "Подкаст: Обзор продукта"
nlm source add ./product-spec.pdf
nlm source add ./user-feedback.csv
nlm generate audio "Разговорный стиль, фокус на боли пользователей" --language ru
nlm artifact wait <id> --timeout 1200
nlm download audio ./product-podcast.mp3
```

### Анализ конкурентов
```bash
nlm create "Конкуренты: [ниша]"
nlm source add-research "конкурент1 vs конкурент2" --mode deep --no-wait
# Ждём...
nlm research wait --import-all --timeout 300
nlm ask "Сравни стратегии конкурентов. Где слабые места?"
nlm generate report --format briefing-doc
nlm download report ./competitor-analysis.md
```

## Безопасность

- `storage_state.json` содержит Google cookies — **не коммитить в git**
- WARP не шифрует DNS по умолчанию — для чувствительных данных включить DoH
- noVNC без пароля — **закрывать порт 6080** после логина
- Сессия ограничена аккаунтом Google — все блокноты будут доступны
- Добавить в `.gitignore`: `~/.notebooklm/`

## Лимиты

| Параметр | Бесплатный | Plus | Pro |
|----------|-----------|------|-----|
| Запросов в день | ~50 | больше | больше |
| Источников на блокнот | 50 | 100 | 300 |
| Генерация audio/video | Лимит | Расширенный | Расширенный |

---

## Changelog

<!-- Сюда автоматически добавляются уроки после каждого использования скилла -->
