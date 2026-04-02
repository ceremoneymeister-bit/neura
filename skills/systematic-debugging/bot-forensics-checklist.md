# Bot Forensics Checklist — Пошаговое расследование ошибки бота

## Шаг 1: Определи сервис и время

```bash
# Какой бот? Проверь все
for svc in nagrada-bot victoria-bot; do
    echo "=== $svc ==="
    journalctl -u $svc --since "2 hours ago" --no-pager | grep -c "error\|Error\|ERROR"
done

# Docker-боты
docker logs yulia-gudymo-bot --since 2h 2>&1 | grep -c "error\|Error\|ERROR"
```

## Шаг 2: Найди конкретную ошибку

```bash
# Последние 20 ошибок с контекстом
journalctl -u {SERVICE} --since "2 hours ago" --no-pager | grep -B2 -A5 "error\|rc=\|killed\|signal"
```

Ищи:
- `rc=143` / `rc=-15` → SIGTERM (бот рестартнули во время обработки)
- `rc=137` / `rc=-9` → SIGKILL (OOM или force kill)
- `rc=1` → ошибка в коде
- `Traceback` → Python exception
- `TimeoutExpired` → subprocess timeout

## Шаг 3: Найди сообщение пользователя

```bash
# Через Telegram Bot API
python3 -c "
import requests, datetime
TOKEN = '{BOT_TOKEN}'  # из .env бота
r = requests.get(f'https://api.telegram.org/bot{TOKEN}/getUpdates', params={'offset': -30, 'timeout': 1})
for u in r.json().get('result', []):
    m = u.get('message') or u.get('edited_message') or {}
    ts = datetime.datetime.fromtimestamp(m.get('date', 0))
    thread = m.get('message_thread_id', 'DM')
    user = m.get('from', {}).get('first_name', '?')
    mtype = 'voice' if m.get('voice') else 'doc' if m.get('document') else 'text'
    text = (m.get('text') or '')[:40]
    print(f'{ts} | topic={thread} | {user} | {mtype} | {text}')
"
```

## Шаг 4: Сопоставь время ошибки с сообщением

- Ошибка в логе в 11:41 UTC?
- Сообщение от пользователя в ~11:41 UTC?
- topic_id = X → значит ошибка в этом топике
- Тип сообщения (voice/doc/text) → какой handler сломался

## Шаг 5: Проверь, был ли рестарт

```bash
# Логи safe-restart
cat /tmp/safe-restart-{SERVICE}.log

# Время последнего рестарта
systemctl show {SERVICE} -p ActiveEnterTimestamp

# Был ли деплой? (git log)
git log --oneline --since="3 hours ago" -- {путь_к_боту}
```

## Шаг 6: Определи root cause

Матрица решений:

| Время ошибки совпадает с рестартом? | rc=143/137? | Root cause |
|-------------------------------------|-------------|------------|
| Да | Да | safe-restart убил активную задачу |
| Да | Нет | Рестарт прервал Python-процесс |
| Нет | Да | OOM kill или внешний сигнал |
| Нет | Нет | Баг в коде → читать traceback |

## Шаг 7: Построй план фикса

Формат:
```
1. [IMMEDIATE] Что сделать прямо сейчас (отправить извинение, рестартнуть)
2. [FIX] Какой код поправить и где
3. [PREVENT] Что добавить, чтобы не повторилось (auto-healing)
4. [VERIFY] Как проверить что фикс работает
```

## Шаг 8: После фикса

- [ ] Синтаксис проверен
- [ ] Сервис рестартнут и active
- [ ] Пользователю отправлено сообщение
- [ ] Причина задокументирована (SESSION_LOG)
- [ ] Auto-healing добавлен (если применимо)

## Примеры реальных расследований

### 2026-03-19: Голосовое Марины → "техническая ошибка"
- **Время:** 18:41 NSK (11:41 UTC)
- **Топик:** ⚙️ Настройки (thread_id=9)
- **Тип:** voice message
- **rc=143** (SIGTERM) — safe-restart убил Claude CLI при деплое Telegraph
- **Доп. баг:** двойной `_extract_and_send_files` в handle_voice и handle_document
- **Фикс:** удалён дубль, safe-restart ждёт Claude, SIGTERM-aware ошибки, systemd TimeoutStopSec=45
- **Уровень проактивности:** 2.2 (полный автономный цикл)
