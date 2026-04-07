---
name: youtube-monitor
description: "Мониторинг YouTube-каналов AI-блогеров. RSS → keyword scoring → транскрипция → Claude анализ → TG-дайджест. Триггеры: 'youtube', 'видео', 'новое видео', 'AI каналы', 'мониторинг каналов', 'дайджест видео', 'транскрипция видео'."
version: 1.0.0
author: Dmitry Rostovtsev (ceremoneymeister)
created: 2026-04-01
updated: 2026-04-01
category: content
tags: [youtube, monitoring, transcription, AI, digest, cron]
risk: safe
source: internal
proactive_enabled: true
proactive_trigger_1_type: schedule
proactive_trigger_1_condition: "ежедневно 08:00"
proactive_trigger_1_action: "проверить новые видео на отслеживаемых каналах"
learning_track_success: true
learning_track_corrections: true
learning_evolve_threshold: 5
learning_auto_update: [anti-patterns, triggers, changelog]
---

# YouTube Monitor — мониторинг AI-каналов

## Назначение

Ежедневный мониторинг YouTube-каналов AI-блогеров → скачивание транскрипций → оценка актуальности → дайджест в Telegram Дмитрию.

## Архитектура (3 уровня фильтрации)

```
RSS (бесплатно, 0 ресурсов)
  ↓ новые видео за 24ч
Keyword Scoring (мгновенно, без Claude)
  ↓ score ≥ 3 → скачать транскрипт
youtube-transcript-api (бесплатно)
  ↓ score ≥ 5 → глубокий анализ
Claude CLI (1 вызов на видео, gate-check)
  ↓
TG-дайджест → Избранное Дмитрия
```

**Ресурсы:** RSS бесплатен, транскрипции бесплатны, Claude вызывается только для действительно релевантных видео (обычно 1-3/день).

## CLI

```bash
# Полный цикл
python3 scripts/youtube-monitor.py

# Только показать (не отправлять, не вызывать Claude)
python3 scripts/youtube-monitor.py --dry-run

# За 3 дня вместо 1
python3 scripts/youtube-monitor.py --days 3

# Перепроверить всё (игнорировать историю)
python3 scripts/youtube-monitor.py --force

# Только один канал
python3 scripts/youtube-monitor.py --channel UCqib0rC7oNo4dXr0RpbtYRg
```

## Мониторимые каналы (6)

| Канал | YouTube ID | Приоритет | Теги |
|-------|-----------|-----------|------|
| Несерьёзный айтишник | UCqib0rC7oNo4dXr0RpbtYRg | high | claude-code, AI, курсы |
| ИИздец | UCjtTkXEapjlgCNsD9s0RwWA | high | n8n, AI-агенты, шаблоны |
| ИИшенка | UCq_L4pHHIuWBW6OSKKxBbgw | high | автоматизация, AI-агенты |
| Алексей Орфеев | UCSFNvPPUBn4KOteRF3Nbd7Q | medium | AI, vibe-coding |
| Никита Велс | UCgFaudM5mLnF4ixj6qeRhPQ | high | claude-code, antigravity |
| Влад Воронежцев | UC797Sd_fYNILYZFuXsjjFDA | medium | нейросети, дизайн |

Добавить канал: отредактировать `data/channels.json`.

## Крон

```
5 12 * * *  python3 /root/Antigravity/scripts/youtube-monitor.py >> /root/Antigravity/logs/youtube-monitor.log 2>&1
```

Зарегистрирован через `guardian.py register --id youtube-monitor --time 12:05`.

## Scoring

**Keyword matching** по title + description:
- Каждое совпадение = +1 очко
- High-value keywords (claude, AI агент, n8n, MCP, antigravity, neura) = +2 бонус
- Score ≥ 3 → скачиваем транскрипт
- Score ≥ 5 → глубокий анализ через Claude

## Файлы

| Файл | Назначение |
|------|-----------|
| `SKILL.md` | Этот файл |
| `data/channels.json` | Конфиг каналов + ключевые слова |
| `data/processed_videos.json` | История обработанных видео |
| `data/last_digest.md` | Последний дайджест |
| `/root/Antigravity/scripts/youtube-monitor.py` | Основной скрипт |

## Зависимости

- `youtube-transcript-api` — уже установлена
- `yt-dlp` — fallback для транскрипций
- `tg-send.py` — отправка дайджеста
- `guardian.py` — gate-check перед Claude

## Anti-Patterns

| Не делай | Почему | Делай вместо |
|----------|--------|-------------|
| Транскрибировать через Whisper/Deepgram | Дорого, YouTube сам отдаёт субтитры | youtube-transcript-api |
| Вызывать Claude для всех видео | Трата бюджета на мусор | Keyword scoring → только score ≥ 5 |
| Запускать чаще 1 раза в день | Видео выходят не каждый час | 1 раз/день достаточно |

---

## Changelog

<!-- Сюда автоматически добавляются уроки после каждого использования скилла -->
