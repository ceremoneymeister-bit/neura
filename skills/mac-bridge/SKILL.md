---
name: mac-bridge
description: "Удалённый доступ к MacBook через Tailscale — SSH, файлы, команды. Использовать когда нужно взаимодействие с Mac: скачать файл, запустить приложение, открыть Figma/Canva, выполнить brew-команду."
version: 1.0.0
author: Dmitry Rostovtsev (ceremoneymeister)
created: 2026-03-22
platforms: [claude-code]
category: infrastructure
tags: [mac, tailscale, ssh, files, remote, bridge]
risk: medium
source: internal
proactive_enabled: true
proactive_trigger_1_type: event
proactive_trigger_1_condition: "нужен файл с Mac / Figma / Canva"
proactive_trigger_1_action: "подключиться через Tailscale SSH"
learning_track_success: true
learning_track_corrections: true
learning_evolve_threshold: 5
learning_auto_update: [anti-patterns, triggers, changelog]
---

# mac-bridge — Удалённый доступ к Mac

## Purpose

Выполнение задач на MacBook Дмитрия с VPS через Tailscale SSH-мост. Без необходимости держать терминал открытым на Mac.

## When to Use

- «Скачай файл с Mac / с рабочего стола»
- «Открой на Mac», «Запусти на Mac»
- Figma/Canva задачи (GUI через Mac)
- «Скопируй на Mac / с Mac»
- Любое взаимодействие с macOS (brew, open, osascript)
- Синхронизация файлов VPS ↔ Mac

## Connection Details

```
HOST: 100.126.72.64   # macbook-pro-1 (активный с 2026-03-25)
HOST_OLD: 100.77.93.12  # macbook-pro (offline)
USER: dmitrijrostovcev
SSH:  ssh dmitrijrostovcev@100.126.72.64
```

**Full Disk Access:** включён — доступ к Desktop, Documents, Downloads и всем папкам.

## Commands Reference

### Выполнить команду на Mac
```bash
ssh dmitrijrostovcev@100.126.72.64 "<command>"
```

### Скопировать файл VPS → Mac
```bash
scp /path/to/file dmitrijrostovcev@100.77.93.12:~/Desktop/
```

### Скопировать файл Mac → VPS
```bash
scp dmitrijrostovcev@100.126.72.64:~/Desktop/file.txt /tmp/
```

### Скопировать папку
```bash
scp -r dmitrijrostovcev@100.77.93.12:~/Desktop/FOLDER /tmp/
```

### Открыть файл/URL на Mac (GUI)
```bash
ssh dmitrijrostovcev@100.126.72.64 "open 'https://figma.com/...'"
ssh dmitrijrostovcev@100.126.72.64 "open ~/Desktop/file.pdf"
```

### Запустить AppleScript (автоматизация GUI)
```bash
ssh dmitrijrostovcev@100.126.72.64 "osascript -e 'tell application \"Finder\" to get name of every file of desktop'"
```

### Проверить доступность Mac
```bash
ping -c 1 -W 2 100.126.72.64 && echo "MAC_ONLINE" || echo "MAC_OFFLINE"
```

### Список файлов на рабочем столе
```bash
ssh dmitrijrostovcev@100.126.72.64 "ls -la ~/Desktop/"
```

## Patterns

### Pattern 1: Скачать файл с Mac на VPS для обработки
```bash
# 1. Найти файл
ssh dmitrijrostovcev@100.126.72.64 "find ~/Desktop -name '*.mp3' -maxdepth 2"
# 2. Скопировать на VPS
scp dmitrijrostovcev@100.126.72.64:~/Desktop/audio.mp3 /tmp/
# 3. Обработать на VPS (транскрибация, конвертация и т.д.)
```

### Pattern 2: Отправить результат на Mac
```bash
# Результат работы → на рабочий стол Mac
scp /tmp/result.pdf dmitrijrostovcev@100.77.93.12:~/Desktop/
```

### Pattern 3: Figma/Canva через Mac
```bash
# Открыть URL в браузере Mac
ssh dmitrijrostovcev@100.126.72.64 "open 'https://www.figma.com/file/...'"
```

### Pattern 4: Brew/системные команды
```bash
ssh dmitrijrostovcev@100.126.72.64 "brew list"
ssh dmitrijrostovcev@100.126.72.64 "sw_vers"  # версия macOS
ssh dmitrijrostovcev@100.126.72.64 "df -h"    # диск
```

## Pre-flight Check

Перед любой операцией — проверь доступность:
```bash
ssh -o ConnectTimeout=5 dmitrijrostovcev@100.77.93.12 "echo MAC_READY" 2>/dev/null || echo "MAC_OFFLINE — Mac выключен или не в сети"
```

Если MAC_OFFLINE — сообщи пользователю: «Mac сейчас недоступен. Включи Mac или проверь подключение Tailscale.»

## Limitations

- Mac должен быть включён и подключён к интернету (Tailscale работает фоном)
- GUI-приложения (Figma, Canva) можно **открыть**, но не управлять ими программно
- Спящий Mac: Tailscale обычно переподключается при пробуждении
- Большие файлы: скорость зависит от интернет-канала Mac

## Troubleshooting

| Проблема | Решение |
|----------|---------|
| Connection refused | Mac выключен или Tailscale отключён |
| Permission denied | Проверить `~/.ssh/authorized_keys` на Mac |
| Operation not permitted | Full Disk Access для sshd не включён |
| Timeout | Mac в спящем режиме или слабый интернет |

## Security

- Tailscale = end-to-end WireGuard шифрование
- SSH по ключу (не по паролю)
- Только устройства в tailnet `ceremoneymeister@gmail.com` видят друг друга

---

## Changelog

<!-- Сюда автоматически добавляются уроки после каждого использования скилла -->
