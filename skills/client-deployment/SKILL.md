---
name: client-deployment
description: "Деплой агентской AI-системы клиенту. Telegram бот + Claude Code + досье сотрудников + скиллы + база знаний + интеграции. Пошаговый процесс от init до сдачи."
version: 1.0.0
author: Dmitry Rostovtsev (ceremoneymeister)
created: 2026-03-17
platforms: [claude-code]
category: deployment
tags: [client, deployment, agent, telegram, onboarding]
risk: safe
source: internal
proactive_enabled: true
proactive_trigger_1_type: event
proactive_trigger_1_condition: "агент готов к сдаче"
proactive_trigger_1_action: "запустить workflow деплоя и онбординга"
learning_track_success: true
learning_track_corrections: true
learning_evolve_threshold: 5
learning_auto_update: [anti-patterns, triggers, changelog]
---

# client-deployment

## Purpose
Полный цикл деплоя AI-агентской системы клиенту: от создания структуры до сдачи проекта. Включает Telegram-бота, систему скиллов, базу знаний, персонализацию и интеграции.

## When to Use This Skill
- Новый клиент → нужна агентская система
- Сдача проекта клиенту
- Развёртывание AI-бота для бизнеса
- "разверни агента для...", "подготовь систему для клиента"

---

## Phase 1: Инициализация структуры

### Шаблон директории
```
{client_dir}/agent/
├── CLAUDE.md           # Личность и правила агента
├── HANDOFF.md          # Статус и следующие шаги
├── DEMO_SCRIPT.md      # Сценарий демо/сдачи
├── bot/
│   ├── bot.py          # Telegram-бот (шаблон из ag-bot-template)
│   ├── .env            # BOT_TOKEN, GROUP_ID
│   ├── users.json      # Пользователи
│   └── requirements.txt
├── skills/             # Специализированные скиллы
├── knowledge/          # База знаний
├── employees/          # Досье сотрудников
│   └── README.md       # Формат досье
├── integrations/       # Стабы для API
│   ├── config.json
│   ├── bitrix24.json
│   └── vk_token.json
├── memory/             # Долгосрочная память
├── diary/              # Дневник диалогов
└── scripts/            # Скрипты деплоя
```

### Чеклист
- [ ] Создать директорию `agent/`
- [ ] Написать CLAUDE.md с полным контекстом бизнеса
- [ ] Создать скиллы под отделы/задачи клиента
- [ ] Наполнить knowledge/ из документов клиента
- [ ] Настроить bot.py с маппингом топиков
- [ ] Создать досье директора/ключевых сотрудников

---

## Phase 2: Бот и бэкенд

### Telegram-бот
1. Зарегистрировать через @BotFather
2. Сохранить BOT_TOKEN в `.env`
3. Настроить `users.json` с директором и admin
4. Создать systemd service

### Функции бота (минимум для MVP)
- Текстовые сообщения → Claude Code → ответ
- Голосовые → Whisper → Claude → ответ
- Демо-кнопки для ключевых сценариев
- Инъекция досье сотрудника в промпт
- Авто-маршрутизация по топикам
- Сессии и дневник

### Деплой
```bash
# Systemd service
sudo cp nagrada-bot.service /etc/systemd/system/{client}-bot.service
sudo systemctl enable {client}-bot
sudo systemctl start {client}-bot
```

---

## Phase 3: Персонализация

### Досье сотрудников
- Файл `employees/{telegram_id}.md` для каждого
- Автосоздание при `/adduser`
- Инъекция в промпт при первом сообщении сессии
- Обновление истории после каждого значимого диалога

### Формат досье
```markdown
# {Имя} — {Должность}
## Профиль
## Стиль общения
## Активные задачи
## История запросов
## Заметки агента
```

---

## Phase 4: Скиллы

### Обязательные скиллы
Зависят от бизнеса клиента. Минимум 3-5 скиллов по ключевым процессам.

### Структура скилла
```markdown
# Скилл: {Название}
## Назначение
## Когда использовать
## Процесс (шаги)
## Правила (hard constraints)
## Шаблоны (copy-paste)
## Anti-Patterns
```

---

## Phase 5: Интеграции

### Стабы (MVP)
- `integrations/config.json` — все API в одном месте
- Placeholder для webhook URL и токенов
- Заполняется на встрече с клиентом

### Реальные API (Phase 2)
- Bitrix24 webhook → CRM вызовы
- VK API → ответы клиентам
- СДЭК API → расчёт доставки

---

## Phase 6: Claude Remote Control

### Watchdog
Добавить в `scripts/claude-watchdog.sh`:
```bash
"{name}|{workdir}|{display_name}"
```

### Запуск
```bash
tmux new-session -d -s {name} -c {workdir} \
    "/root/Antigravity/scripts/claude-persistent.sh {name} {workdir} \"{display}\""
```

---

## Phase 7: Сдача

### Демо-скрипт (30-40 мин)
1. Показать бота (текст, голос, демо-кнопки)
2. Добавить сотрудников live
3. Показать персонализацию
4. Подключить CRM (если готов)
5. Показать Claude Remote Control
6. Показать React платформу (будущее)
7. Обсудить следующие шаги

### Верификация
- [ ] Бот отвечает на текст
- [ ] Бот отвечает на голосовые
- [ ] Демо-кнопки работают
- [ ] Досье создаётся при /adduser
- [ ] Claude Remote Control сессия жива
- [ ] vsearch находит данные клиента

---

## Anti-Patterns
- НЕ давать сотрудникам доступ к терминалу
- НЕ обещать функции Phase 2 как готовые
- НЕ показывать сырые логи клиенту
- НЕ подключать API без согласия клиента
- НЕ копировать данные клиента в другие проекты

## Lessons Learned (Награда, март 2026)
- n8n workflow (37 нодов) оказался избыточным → Claude Code через subprocess проще и мощнее
- Telegram бот = основной канал для нетехнических пользователей
- Досье сотрудников = killer feature для персонализации
- Демо-кнопки в /start — лучший способ показать возможности
- Стабы интеграций → реальные API делать ПОСЛЕ сдачи MVP

---

## Changelog

<!-- Сюда автоматически добавляются уроки после каждого использования скилла -->
