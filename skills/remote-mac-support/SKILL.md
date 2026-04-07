---
name: remote-mac-support
description: Удалённая диагностика, очистка и оптимизация Mac через Tailscale SSH
version: 0.1.0
author: Auto-crystallized from task
created: 2026-03-30
updated: 2026-03-30
category: infrastructure
tags: [mac, diagnostics, cleanup, tailscale, ssh, remote-support]
risk: medium
source: crystallized
usage_count: 1
maturity: seed
last_used: 2026-03-30
created_from: Диагностика Mac Марины Павловой — remote session через Tailscale
proactive_enabled: true
proactive_trigger_1_type: event
proactive_trigger_1_condition: "проблема с Mac клиента"
proactive_trigger_1_action: "удалённая диагностика через Tailscale"
learning_track_success: true
learning_track_corrections: true
learning_evolve_threshold: 5
learning_auto_update: [anti-patterns, triggers, changelog]
---

# remote-mac-support

## Purpose

Удалённая поддержка Mac-пользователей: диагностика производительности, очистка, оптимизация. Подключение через Tailscale SSH без необходимости физического присутствия.

## When to Use

- "проблема с Mac", "Mac тормозит", "Mac зависает"
- "удалённая диагностика", "почистить Mac"
- "Mac медленно работает", "много памяти занято"
- Любые запросы на техническую поддержку Mac через удалённый доступ

## Workflow

### 1. Подключение
```bash
ssh <user>@<tailscale-ip>
```
Tailscale должен быть установлен на целевом Mac. Standalone-версия (не App Store) для поддержки --ssh.

### 2. Диагностика

**Система:**
```bash
sw_vers                                          # версия macOS
system_profiler SPHardwareDataType               # железо (модель, RAM, CPU)
```

**Нагрузка:**
```bash
top -l 1 -n 0 -s 0 | head -12                   # общая нагрузка
ps -eo pid,%cpu,%mem,rss,comm -m | head -30      # процессы по памяти
ps -eo pid,%cpu,%mem,rss,comm -r | head -30      # процессы по CPU
sysctl vm.swapusage                              # swap
```

**Питание и температура:**
```bash
pmset -g                                         # настройки питания
pmset -g therm                                   # термальный тротлинг
system_profiler SPPowerDataType | grep -E 'Cycle|Condition'  # батарея
```

**Автозапуски:**
```bash
ls ~/Library/LaunchAgents/                       # пользовательские
ls /Library/LaunchDaemons/                       # системные демоны
```

**Кеши и логи:**
```bash
du -sh ~/Library/Caches/* | sort -rh | head -15  # размер кешей
ls ~/Library/Fonts/ | wc -l                      # количество шрифтов
ls -lt ~/Library/Logs/DiagnosticReports/ | head -15  # краш-репорты
find ~/Library/Logs/DiagnosticReports /Library/Logs/DiagnosticReports -name '*.ips' -mtime -30  # недавние крэши
```

### 3. Очистка

**Кеши** (по списку из диагностики):
```bash
rm -rf ~/Library/Caches/<app>/*
```

**LaunchAgents** (пользовательские):
```bash
launchctl unload ~/Library/LaunchAgents/<plist>
mv ~/Library/LaunchAgents/<plist> ~/Desktop/disabled_agents/
```

**LaunchDaemons** (системные, нужен sudo):
```bash
echo 'password' | sudo -S launchctl unload /Library/LaunchDaemons/<plist>
echo 'password' | sudo -S mv /Library/LaunchDaemons/<plist> ~/Desktop/disabled_daemons/
```

**Старые логи:**
```bash
find ~/Library/Logs -name "*.log" -mtime +30 -delete
```

### 4. Оптимизация

```bash
pmset -a displaysleep 10    # дисплей засыпает через 10 мин
pmset -a powernap 0         # отключить Power Nap
pmset -a womp 0             # отключить Wake on LAN
```

### 5. Отчёт

Сформировать PDF-отчёт (WeasyPrint + CSS) и отправить пользователю:
```bash
python3 scripts/tg-send.py <user> "[FILE:/tmp/mac-report.pdf]"
```

## Anti-patterns

- **НЕ** запускать много SSH-сессий параллельно — macOS ограничивает MaxSessions
- **НЕ** использовать `client.start()` в Telethon — вызывает prompt авторизации. Использовать `client.connect()` + `is_user_authorized()`
- **НЕ** копировать SSH-ключи через Telegram — кавычки ломаются при копировании. Лучше через curl или пароль
- Tailscale GUI (App Store) **НЕ** поддерживает `--ssh`. Нужен standalone или обычный SSH
- Parser-сессия Telethon может быть залочена — проверять `fuser`, использовать readonly-сессию
- `sudo` через SSH: использовать `echo 'password' | sudo -S bash -c '...'`

## Tools & Scripts

- **Tailscale** — VPN-мост между VPS и Mac
- **SSH** — основной канал подключения
- **tg-send.py** — отправка отчёта пользователю
- **WeasyPrint** — генерация PDF-отчёта

---

## Changelog

<!-- Сюда автоматически добавляются уроки после каждого использования скилла -->
