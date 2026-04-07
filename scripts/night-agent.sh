#!/bin/bash
# Night agent launcher for Neura Web Platform build
# Usage: night-agent.sh <task_number> <description>

TASK_NUM=$1
DESC=$2
LOG_DIR=/opt/neura-v2/logs
mkdir -p $LOG_DIR

PROMPT="Ты — ночной автономный агент. Дмитрий спит. Работай самостоятельно и тщательно.

ЗАДАЧА: Прочитай ${NEURA_BASE:-/opt/neura-v2}/NIGHT_TASKS.md → выполни задачу $TASK_NUM ('$DESC').

КРИТИЧЕСКИЕ ПРАВИЛА:
- ⛔ НЕ перезапускать neura-v2.service — 6 ботов работают! Только СОЗДАВАЙ файлы, не трогай запущенный процесс
- ⛔ НЕ делать systemctl restart/stop neura-v2
- ⛔ НЕ делать git push
- ⛔ НЕ отправлять сообщения клиентам
- ✅ Используй WebSearch для исследований best practices
- ✅ Перед написанием кода — прочитай существующий код в /opt/neura-v2/
- ✅ Если файл от предыдущего агента ещё не создан — создай заглушку и продолжай
- ✅ Будь ПРОАКТИВНЫМ: находи лучшие решения, добавляй полезные фичи
- ✅ После завершения отправь отчёт: python3 ${NEURA_BASE:-/opt/neura-v2}/scripts/tg-send-hq.py 962 'краткий отчёт что сделано'

КОНТЕКСТ: Neura v2 — платформа AI-агентов. 6 ботов в одном процессе, PostgreSQL + Redis, FastAPI backend + React frontend. Всё в /opt/neura-v2/."

# Cron Guardian gate
python3 ${NEURA_BASE:-/opt/neura-v2}/.agent/skills/cron-guardian/guardian.py gate || exit 1

cd /opt/neura-v2 && claude -p "$PROMPT" \
  --model sonnet \
  --allowedTools "Read,Write,Edit,Glob,Grep,Bash,WebSearch,WebFetch" \
  --verbose \
  > "$LOG_DIR/night-agent-${TASK_NUM}.log" 2>&1

# Log to guardian
python3 ${NEURA_BASE:-/opt/neura-v2}/.agent/skills/cron-guardian/guardian.py log "night-web-${TASK_NUM}"
