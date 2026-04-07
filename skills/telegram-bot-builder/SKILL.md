---
name: telegram-bot-builder
description: "Создание premium Telegram-ботов с Claude AI — полный цикл от концепции до продакшна. Триггеры: 'создай бота', 'новый бот', 'Telegram бот', 'капсула', 'AI-агент для клиента', 'настрой бота'"
version: 2.0.0
category: core
tags: [telegram, bot, ai-agent, claude, capsule, premium]
usage_count: 0
maturity: seed
last_used: null
proactive_enabled: true
proactive_trigger_1_type: event
proactive_trigger_1_condition: "новый клиент подключен"
proactive_trigger_1_action: "предложить создание бота по 9 фазам"
learning_track_success: true
learning_track_corrections: true
learning_evolve_threshold: 5
learning_auto_update: [anti-patterns, triggers, changelog]
---

# Telegram Bot Builder — Premium AI-агенты

> Создание Telegram-ботов уровня $20,000+/год. Полный цикл: архитектура → код → интеграции → деплой → самоэволюция.
> Наши боты — не чат-боты. Это AI-команды с памятью, скиллами, инструментами и автономным поведением.

---

## Архитектура Premium-бота (7 уровней)

```
Уровень 7: Самоэволюция     ← скиллы улучшаются при каждом использовании
Уровень 6: Проактивность     ← бот инициирует контакт (утренние сводки, напоминания)
Уровень 5: Экосистема        ← почта, календарь, CRM, соцсети, файлы
Уровень 4: Инструменты       ← PDF, таблицы, изображения, презентации, QR
Уровень 3: Память            ← дневник, обучение, коррекции, предпочтения
Уровень 2: Интеллект         ← Claude Opus/Sonnet, streaming, deep mode
Уровень 1: Транспорт         ← Telegram API, обработка сообщений, буферизация
```

**Минимальный продукт:** уровни 1-3 (транспорт + интеллект + память)
**Стандартный продукт:** уровни 1-5 (+ инструменты + экосистема)
**Premium продукт:** все 7 уровней

---

## Фаза 0: Распаковка клиента (до кода)

### 0.1 Бриф
Собрать ПЕРЕД написанием кода:

```markdown
## Бриф бота
- **Бизнес:** что делает клиент, ниша, продукты
- **Аудитория:** кто пишет боту (клиенты / сотрудники / оба)
- **Задачи:** ТОП-5 задач, которые бот должен решать
- **Тон:** формальный / дружеский / экспертный / провокационный
- **Интеграции:** что подключать (календарь, CRM, почта, соцсети)
- **Контент:** что загрузить (прайсы, FAQ, портфолио, база знаний)
- **Количество пользователей:** 1 / до 5 / до 50 / безлимит
- **Бюджет:** влияет на модель (Opus / Sonnet / Haiku)
```

### 0.2 Загрузка ассетов
```
data/client-assets/
├── brand/          ← логотип, цвета, шрифты, брендбук
├── knowledge/      ← FAQ, прайсы, каталоги, инструкции
├── templates/      ← шаблоны КП, договоров, писем
└── media/          ← фото продуктов, баннеры
```

---

## Фаза 1: Структура проекта

### 1.1 Файловая структура (эталон)

```
bot-name/
├── CLAUDE.md                  # Агентная инструкция (персонализированная)
├── config.json                # Конфигурация (trial, proactive, model)
├── constitution.json          # Этические ограничения
├── .env                       # Токены и ключи
├── requirements.txt           # Python-зависимости
├── bot/
│   ├── main.py                # Точка входа: регистрация хэндлеров
│   ├── config.py              # Загрузка конфигурации из ENV
│   ├── engine/
│   │   ├── claude.py          # Исполнитель Claude CLI (streaming + session)
│   │   ├── sessions.py        # Управление сессиями (UUID, reset, persistence)
│   │   ├── transcribe.py      # STT: Deepgram → Whisper fallback
│   │   └── onboarding_state.py # Состояние первого контакта
│   ├── handlers/
│   │   ├── text.py            # Текстовые сообщения + буферизация
│   │   ├── voice.py           # Голосовые → транскрипция → Claude
│   │   ├── photo.py           # Фото → описание → Claude
│   │   ├── document.py        # Документы → чтение → Claude
│   │   ├── commands.py        # /start, /help, /settings, /diary
│   │   ├── menu.py            # Inline-клавиатура настроек
│   │   ├── callbacks.py       # Обработка кнопок
│   │   ├── access.py          # Контроль доступа + trial
│   │   ├── onboarding.py      # Первый контакт (приветствие, анкета)
│   │   └── _common.py         # Rate limit, token tracking, reply context
│   └── utils/
│       ├── diary.py           # Дневник (episodic memory)
│       ├── memory.py          # 4-уровневая память
│       ├── response.py        # Telegraph + маркеры + кнопки
│       ├── progress.py        # Индикатор "думаю..." + streaming
│       ├── skills.py          # Автообнаружение скиллов
│       ├── error_messages.py  # Человечные ошибки
│       └── quality_logger.py  # Метрики качества
├── skills/                    # Скиллы бота (auto-discovery)
│   ├── image-generation/SKILL.md
│   ├── smart-response/SKILL.md
│   ├── copywriting/SKILL.md
│   └── ... (по потребностям клиента)
├── tools/
│   └── capsule-tools.py       # PDF, QR, TTS
├── memory/
│   ├── diary/                 # Ежедневные записи
│   ├── learnings.md           # Накопленные знания (max 50)
│   ├── corrections.md         # Коррекции от пользователя (max 50)
│   └── rules.md               # Постоянные правила
├── data/
│   ├── client-assets/         # Брендбук, FAQ, каталоги
│   └── sessions.json          # Состояние сессий
└── proactive.py               # Проактивные сообщения (cron)
```

### 1.2 Источник: эталон
```bash
# Копирование из эталона
cp -r /root/Antigravity/neura-capsule/ /srv/capsules/new-client/
```

---

## Фаза 2: CLAUDE.md — мозг бота

### 2.1 Шаблон (CLAUDE.md.template)
Ключевые секции:

```markdown
# Кто я
[Имя бота] — AI-агент для [бизнес клиента].
Владелец: [имя клиента]. Бизнес: [описание].

# Правила
- [тон общения]
- [ограничения контента]
- [специфика ниши]

# Скиллы
{{SKILL_TABLE}}    ← автоматически из skills/*/SKILL.md

# Инструменты
{{TOOLS_TABLE}}    ← автоматически из tools/*.py

# Память
- Дневник: memory/diary/ (читать текущий день)
- Learnings: memory/learnings.md (max 50, с весами)
- Corrections: memory/corrections.md (max 50)
- Маркеры: [LEARN: ...] и [CORRECTION: ...] в ответах
```

### 2.2 Критическое правило: изоляция
```
⚠️ CLAUDE.md бота НЕ ДОЛЖЕН наследовать родительский CLAUDE.md!
В claude.py использовать: --append-system-prompt (не --system-prompt)
Проверить: нет ли SESSION_LOG, 💾, ДНК-правил в ответах бота
```

### 2.3 Антипаттерн: CLAUDE.md утечка
Если бот выдаёт мета-мусор (💾, SESSION_LOG, "Скилл-чек") — это утечка родительского CLAUDE.md. Фикс: блокировка auto-discovery через `--append-system-prompt`.

---

## Фаза 3: Движок Claude (engine/)

### 3.1 claude.py — исполнитель

**Ключевые паттерны:**

```python
# mtime-кэш для CLAUDE.md (горячая перезагрузка без рестарта)
claude_md_mtime = 0
claude_md_cache = ""

def load_claude_md():
    global claude_md_mtime, claude_md_cache
    current_mtime = os.path.getmtime("CLAUDE.md")
    if current_mtime != claude_md_mtime:
        claude_md_cache = open("CLAUDE.md").read()
        claude_md_mtime = current_mtime
    return claude_md_cache
```

```python
# Контекст = CLAUDE.md + дневник + learnings + corrections
def build_context():
    parts = [load_claude_md()[:3000]]
    diary = load_today_diary()
    if diary:
        parts.append(f"## Дневник сегодня\n{diary[-2000:]}")
    learnings = load_learnings()
    if learnings:
        parts.append(f"## Что я узнал\n{learnings}")
    return "\n\n".join(parts)
```

```python
# Сессии с UUID
def execute(prompt, user_id):
    session = sessions.get_or_create(user_id)
    if session.is_new:
        cmd = f"claude -p '{prompt}' --session-id {session.id}"
    else:
        cmd = f"claude -p '{prompt}' --resume {session.id}"
    # ... subprocess + streaming
```

### 3.2 Streaming (обязательно для premium)
```python
# Streaming даёт UX "бот печатает" вместо "бот думает 30 сек"
process = subprocess.Popen(cmd, stdout=PIPE, stderr=PIPE)
buffer = ""
for line in process.stdout:
    buffer += line.decode()
    if len(buffer) > 100:  # отправляем чанками
        await send_typing(chat_id)
        buffer = ""
```

### 3.3 Deep Mode (расширенное мышление)
```python
# Effort levels: standard / deep
# Deep = больше thinking tokens, лучше для сложных задач
# Выбор через меню настроек или автоматически

def should_use_deep(message):
    triggers = ["проанализируй", "стратегия", "план", "сравни", "почему"]
    return any(t in message.lower() for t in triggers)
```

---

## Фаза 4: Обработчики (handlers/)

### 4.1 Буферизация сообщений
```python
# Пользователь отправляет 3 сообщения подряд за 5 секунд
# Без буфера: 3 отдельных запроса к Claude (дорого, бессмысленно)
# С буфером: 1 объединённый запрос

BUFFER_WINDOW = 7   # секунд ожидания
BUFFER_MAX_WAIT = 10 # максимум ожидания
```

### 4.2 BTW-очередь
```python
# Пользователь пишет ПОКА бот думает
# BTW = "By The Way" — сообщения копятся в очереди
# После ответа: "Кстати, пока я думал, вы написали: ..."
```

### 4.3 Маркеры в ответах
```python
# Бот выучил что-то → [LEARN: клиент предпочитает краткие ответы]
# Бот получил коррекцию → [CORRECTION: не использовать слово "дешёвый"]
# Бот отправляет файл → [FILE:/tmp/proposal.pdf]

def parse_markers(response):
    learns = re.findall(r'\[LEARN:\s*(.*?)\]', response)
    corrections = re.findall(r'\[CORRECTION:\s*(.*?)\]', response)
    files = re.findall(r'\[FILE:(.*?)\]', response)
    clean = re.sub(r'\[(LEARN|CORRECTION|FILE):.*?\]', '', response).strip()
    return clean, learns, corrections, files
```

### 4.4 Медиа-обработка
| Тип | Обработка |
|-----|-----------|
| Текст | Буферизация → Claude |
| Голосовое | Deepgram STT → текст → Claude |
| Фото | Скачать → Read tool (мультимодальный Claude) → ответ |
| Документ | Скачать → читать (<500KB) → Claude с контекстом |
| Стикер | Игнорировать или описать |

---

## Фаза 5: Память (4 уровня)

### 5.1 Архитектура памяти
```
Persistent Rules    ← правила, которые не меняются (тон, ограничения)
    ↓
Episodic (Diary)    ← ежедневные записи разговоров
    ↓
Semantic            ← learnings (знания) + corrections (ошибки)
    ↓
Working             ← текущая сессия (session_id)
```

### 5.2 Дневник (diary/)
```markdown
## 2026-03-31

**09:15** [продажи](opus, 45s) Клиент спросил про оптовые цены →
Отправил прайс-лист с калькулятором скидок

**11:30** [контент](sonnet, 12s) Попросил написать пост для Instagram →
Сгенерировал 3 варианта с хештегами
```

### 5.3 Learnings + Corrections
```markdown
# learnings.md (max 50, самые старые удаляются)
- [вес: 3] Клиент предпочитает короткие ответы (до 300 слов)
- [вес: 2] При вопросах о ценах всегда упоминать скидку за опт
- [вес: 1] Формат прайса: таблица с артикулами

# corrections.md (max 50)
- НЕ использовать слово "дешёвый" — заменять на "доступный"
- НЕ отправлять PDF без предварительного подтверждения
```

---

## Фаза 6: Инструменты и скиллы

### 6.1 Стандартный набор скиллов (подключить всем)

| Скилл | Что делает | Файл |
|-------|-----------|------|
| image-generation | Генерация картинок (Grsai API) | skills/image-generation/ |
| smart-response | Длинные ответы через Telegraph | skills/smart-response/ |
| copywriting | Тексты, описания, заголовки | skills/copywriting/ |
| pdf-generator | PDF: КП, прайсы, отчёты | skills/pdf-generator/ |
| excel-xlsx | Таблицы, сметы, аналитика | skills/excel-xlsx/ |

### 6.2 Инструменты (tools/)

```python
# capsule-tools.py — единый CLI
# Использование из Claude: python3 tools/capsule-tools.py <command>

def pdf(text, filename, style="notion"):
    """Генерация PDF из Markdown"""

def qr(url, filename):
    """QR-код для ссылки"""

def tts(text, filename, voice="nova"):
    """Озвучка текста (Grsai TTS)"""
```

### 6.3 Auto-discovery скиллов
```python
# skills.py — сканирует skills/*/SKILL.md при каждом запросе
def get_skill_table():
    skills = []
    for skill_dir in Path("skills").iterdir():
        skill_md = skill_dir / "SKILL.md"
        if skill_md.exists():
            # Парсим name и description из frontmatter
            name, desc = parse_frontmatter(skill_md)
            skills.append(f"| {name} | {skill_dir} | {desc} |")
    return "\n".join(skills)
```

---

## Фаза 7: Экосистема

### 7.1 Telethon Userbot
```python
# Даёт боту доступ к Telegram от имени клиента
# Может: искать в чатах, читать каналы, пересылать, отправлять

# ВАЖНО: API ID = Дмитрия (33869550), НЕ создавать новый!
# Сессия: bot/userbot/client.session
```

### 7.2 Интеграции (примеры)
| Интеграция | Что даёт | Сложность |
|-----------|---------|-----------|
| iCloud Calendar | Создание/чтение событий | Средняя |
| Google Calendar | OAuth → Calendar API | Высокая |
| Bitrix24 | CRM, задачи, чаты | Средняя |
| Mail.ru/Gmail | Чтение/отправка почты | Средняя |
| VK сообщества | Постинг, сообщения | Средняя |
| Instagram | Публикация (через Playwright) | Высокая |

### 7.3 HQ-группа (мониторинг)
```
Создать группу "Клиент | HQ" с топиками:
- #general — общие вопросы
- #errors — ошибки бота
- #analytics — метрики
- #content — контент (черновики, посты)
```

---

## Фаза 8: Проактивность

### 8.1 Архитектура
```python
# proactive.py — ОТДЕЛЬНЫЙ процесс (не в боте!)
# Запускается по cron: 0 9 * * * python3 proactive.py morning

def morning_message(user_id):
    diary = load_yesterday_diary()
    prompt = f"""Ты — AI-агент. Вчера было: {diary}.
    Напиши короткое утреннее сообщение: итоги вчера + план на сегодня.
    Максимум 3 предложения. Тон: дружеский, бодрый."""
    response = claude_haiku(prompt)  # Haiku = дёшево
    send_telegram(user_id, response)
```

### 8.2 Типы проактивных сообщений
| Тип | Когда | Модель | Пример |
|-----|-------|--------|--------|
| morning | 09:00 | haiku | "Доброе утро! Вчера мы..." |
| evening | 21:00 | haiku | "Итоги дня: сделано 3 задачи..." |
| reminder | по расписанию | haiku | "Не забудь про встречу в 15:00" |
| insight | 1 раз/неделю | sonnet | "Заметил паттерн: клиенты чаще..." |
| follow-up | через 2 дня | haiku | "Как прошла встреча с...?" |

---

## Фаза 9: Самоэволюция

### 9.1 Механика улучшения скиллов
```
Каждое использование скилла:
1. Скилл сработал? → Да: продолжить. Нет: записать в corrections
2. Результат хороший? → Да: увеличить вес в learnings. Нет: исправить SKILL.md
3. Новый паттерн? → Добавить в SKILL.md (антипаттерн или best practice)

Принцип: каждая задача делает бота ЛУЧШЕ
```

### 9.2 Quality Logger
```python
# Логирование метрик каждого запроса
{
    "timestamp": "2026-03-31T09:15:00",
    "user_id": 123,
    "model": "opus",
    "duration_s": 45,
    "tokens_in": 1200,
    "tokens_out": 800,
    "tools_used": ["pdf-generator"],
    "had_error": false,
    "telegraph_used": false,
    "markers": {"learns": 1, "corrections": 0, "files": 1}
}
```

---

## Деплой

### Вариант A: systemd (рекомендуемый)
```bash
# /etc/systemd/system/client-bot.service
[Unit]
Description=Client AI Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/srv/capsules/client-name
ExecStart=/usr/bin/python3 bot/main.py
Restart=always
RestartSec=5
MemoryMax=4G
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

### Вариант B: Docker
```yaml
# docker-compose.yml
services:
  bot:
    build: .
    restart: always
    mem_limit: 4g
    volumes:
      - ./memory:/app/memory
      - ./data:/app/data
    env_file: .env
```

### Рестарт
```bash
# systemd
safe-restart client-bot

# Docker
docker compose build --no-cache && docker compose up -d
```

---

## Чеклист запуска (10 пунктов)

- [ ] BotFather: создан бот, установлены команды и описание
- [ ] CLAUDE.md: персонализирован, проверен на утечки
- [ ] .env: BOT_TOKEN, ANTHROPIC_API_KEY (или Claude Max), GRSAI_API_KEY
- [ ] Память: diary/, learnings.md, corrections.md инициализированы
- [ ] Скиллы: минимум image-generation + smart-response
- [ ] Тест: /start → онбординг → первый ответ → проверка маркеров
- [ ] HQ-группа: создана, бот добавлен
- [ ] Proactive: cron настроен (утро/вечер)
- [ ] Мониторинг: error_messages.py проверен, ошибки не утекают
- [ ] Изоляция: CLAUDE.md НЕ наследует родительский (проверить ответы)

---

---

## LITE: Маркетинговые боты (без AI)

### Когда использовать Lite
- Запись на вебинар / мастер-класс / интенсив
- Воронка продаж (прогрев → оффер → оплата)
- Сбор заявок и лидов
- Рассылки и напоминания
- Продажа курсов / тарифов с оплатой

### Структура Lite-бота
```
lite-bot/
├── bot.py              # Один файл — вся логика
├── .env                # BOT_TOKEN, ADMIN_IDS
├── requirements.txt    # python-telegram-bot, httpx, python-dotenv
└── data.db             # SQLite — пользователи, заявки, статистика
```

### Компоненты Lite

**1. Регистрация + SQLite**
```python
# Таблица users: user_id, username, full_name, reg_time, source, paid
# /start → приветствие → запись в БД → меню с кнопками
```

**2. Inline-меню (кнопки)**
```python
# Главное меню после /start
keyboard = [
    [InlineKeyboardButton("📋 Программа", callback_data="program")],
    [InlineKeyboardButton("💰 Тарифы", callback_data="tariffs")],
    [InlineKeyboardButton("✅ Записаться", callback_data="register")],
    [InlineKeyboardButton("❓ Вопросы", callback_data="faq")],
]
```

**3. Тарифы + оплата (Prodamus / ЮKassa / Payform)**
```python
TARIFFS = {
    "base":  {"name": "Базовый",  "price": 5000,  "url": "https://payform.ru/xxx"},
    "pro":   {"name": "Продвинутый", "price": 15000, "url": "https://payform.ru/yyy"},
    "vip":   {"name": "VIP",      "price": 30000, "url": "https://payform.ru/zzz"},
}
# Кнопка → ссылка на оплату → webhook подтверждения
```

**4. Автонапоминания (cron)**
```python
# За 1 день: "Завтра в 19:00 — вебинар! Не забудьте..."
# За 1 час: "Через час начинаем! Ссылка: ..."
# За 15 мин: "Уже скоро! Зайдите по ссылке заранее"
# schedule: [{hours_before: 24, template: "..."}, ...]
```

**5. Воронка после события**
```python
# +1 час: "Спасибо что были! Вот запись: ..."
# +1 день: "Вчера мы разобрали X. Готовы к следующему шагу?"
# +3 дня: "Последний день скидки на курс. Осталось N мест"
# +7 дней: "Финальное предложение. После этого цена вернётся"
```

**6. Рассылка (/broadcast)**
```python
# /broadcast Текст сообщения
# Рассылает всем зарегистрированным
# С задержкой 0.05с между сообщениями (anti-flood)
# Статистика: отправлено / заблокировали бота
```

**7. Статистика (/stats)**
```python
# Регистрации: всего / сегодня / за неделю
# Оплаты: всего / сумма / по тарифам
# Конверсия: регистрация → просмотр → оплата
```

### Воронка продаж (шаблон)

```
/start
  ↓
Приветствие + лид-магнит (PDF/видео)
  ↓
Программа мероприятия (кнопки)
  ↓
Напоминания (авто, cron)
  ↓
Мероприятие (ссылка)
  ↓
Follow-up серия (1ч → 1д → 3д → 7д)
  ↓
Оффер + тарифы + оплата
  ↓
Подтверждение оплаты → чат участников
```

### Примеры Lite-ботов
- **Вебинарный бот** — запись → напоминания → трансляция → оффер
- **Бот сбора заявок** — анкета → сохранение → уведомление админу
- **Бот-каталог** — товары с фото → корзина → оплата
- **Бот-квиз** — вопросы → результат → персональный оффер
- **Бот-автоответчик** — FAQ по кнопкам, без AI

---

## SMART: Мини-агент (Claude без капсулы)

### Когда использовать Smart
- Клиент хочет AI-помощника, но бюджет ограничен
- Нужен 1 бот для 1 человека
- Без экосистемы (без userbot, CRM, почты)
- Достаточно текстового общения + базовые инструменты

### Структура Smart-бота
```
smart-bot/
├── bot.py              # Хэндлеры + Claude CLI вызов
├── claude_config.md    # Инструкция для Claude (аналог CLAUDE.md)
├── .env                # BOT_TOKEN + ANTHROPIC_API_KEY (или Claude Max)
├── memory/
│   ├── diary.md        # Простой дневник (append-only)
│   └── rules.md        # Правила пользователя
└── requirements.txt
```

### Отличия от Premium

| | Smart | Premium (Neura) |
|---|---|---|
| Claude вызов | `claude -p "prompt" --model sonnet` | Streaming executor + sessions |
| Память | 1 файл diary.md | 4-уровневая система |
| Скиллы | 0-3 встроенных | 30+ auto-discovery |
| Проактивность | Нет | Утро/вечер/инсайты |
| Userbot | Нет | Полный доступ к TG |
| Стоимость | $5-15/мес | $30-100/мес |
| Деплой | 1 файл + systemd | Полная капсула |

### Быстрый старт Smart
```python
import subprocess

def ask_claude(prompt, context_file="claude_config.md"):
    context = open(context_file).read()
    full_prompt = f"{context}\n\n---\nПользователь: {prompt}"
    result = subprocess.run(
        ["claude", "-p", full_prompt, "--model", "sonnet"],
        capture_output=True, text=True, timeout=120
    )
    return result.stdout.strip()
```

### Smart + инструменты
```python
# Добавляем 2-3 инструмента без полной капсулы
TOOLS = {
    "image": "python3 scripts/grsai-image.py generate --prompt '{prompt}'",
    "pdf":   "python3 scripts/md2pdf.py --input '{text}' --output /tmp/doc.pdf",
}
# Claude решает какой инструмент вызвать → бот выполняет → отправляет результат
```

---

---

## Визуальная упаковка бота (авто)

### При создании ЛЮБОГО бота — сгенерировать визуал:

**1. Аватарка бота (BotFather)**
```bash
# Круглая аватарка 640x640
python3 scripts/grsai-image.py generate \
  --prompt "minimalist logo for [бизнес], [символ ниши], clean circular composition, solid [цвет бренда] background, modern flat design" \
  --preset logo \
  --aspect 1:1 \
  --filename bot-avatar.png

# Ресайз до 640x640 (BotFather требует)
python3 -c "from PIL import Image; Image.open('/tmp/bot-avatar.png').resize((640,640), Image.LANCZOS).save('/tmp/bot-avatar.png')"
```

Установка через Telethon (parser session):
```python
from telethon.tl.functions.bots import SetBotInfoRequest
# Или через BotFather: /setuserpic → отправить фото
```

**2. Баннер для описания бота**
```bash
# Баннер 1280x640 для BotFather /setdescriptionpic
python3 scripts/grsai-image.py generate \
  --prompt "professional banner for [название бота], [тематика], gradient [цвет1] to [цвет2], modern typography placeholder, clean minimal" \
  --preset social \
  --aspect 16:9 \
  --filename bot-banner.png

python3 -c "from PIL import Image; Image.open('/tmp/bot-banner.png').resize((1280,640), Image.LANCZOS).save('/tmp/bot-banner.png')"
```

**3. Меню-картинки (для кнопок)**
```bash
# Карточки для inline-меню (если бот использует WebApp или Telegraph)
python3 scripts/grsai-image.py generate \
  --prompt "flat icon [действие], minimalist, [цвет бренда] accent, white background, simple geometric" \
  --preset logo \
  --filename menu-icon-1.png
```

**4. Welcome-картинка**
```bash
# Приветственное изображение при /start
python3 scripts/grsai-image.py generate \
  --prompt "welcoming hero image for [бизнес], warm friendly atmosphere, [стиль ниши], professional, inviting" \
  --preset photo \
  --aspect 16:9 \
  --filename welcome.jpg
```

### Промпты по нишам (готовые)

| Ниша | Промпт для аватарки |
|------|---------------------|
| Массаж | `minimalist logo, two hands massage symbol, warm amber gradient, zen circle, clean flat design` |
| Фитнес | `minimalist logo, abstract running figure, energetic green accent, dynamic motion, clean flat` |
| Дизайн интерьера | `minimalist logo, geometric house cross-section, indigo accent, architectural lines, modern flat` |
| Кондитер | `minimalist logo, elegant cake silhouette, pastel pink accent, clean lines, modern flat design` |
| Юрист | `minimalist logo, balanced scales symbol, deep navy blue, professional, clean geometric flat` |
| Бьюти | `minimalist logo, abstract face profile, rose gold accent, elegant lines, modern flat design` |
| Силиконовые формы | `minimalist logo, geometric mold shape, warm terracotta accent, craft aesthetic, clean flat` |

### Автоматизация: скрипт упаковки
```bash
# Полная визуальная упаковка за 1 команду (будущее)
# python3 scripts/bot-branding.py --name "Название" --niche "ниша" --color "#6366F1"
# Генерирует: avatar.png + banner.png + welcome.jpg + 4 menu-icons
```

---

## Ценообразование (для продажи)

| Уровень | Что включено | Разовая | Абонемент |
|---------|-------------|---------|-----------|
| **Lite** | Воронка + оплата + рассылка + напоминания | 10,000–30,000 ₽ | 0 ₽ (без AI) |
| **Smart** | Claude + память + 2-3 инструмента | 15,000–40,000 ₽ | 5,000–10,000 ₽ |
| **Premium** | Полная капсула Neura (7 уровней) | 30,000–80,000 ₽ | 15,000–40,000 ₽ |

---

## Антипаттерны

- НЕ наследовать CLAUDE.md от родителя → утечка ДНК-правил
- НЕ использовать `--system-prompt` → использовать `--append-system-prompt`
- НЕ хардкодить цвета/стили → брать из brandbook
- НЕ создавать новый API ID для Telethon → использовать Дмитрия (33869550)
- НЕ запускать proactive внутри бота → отдельный процесс (cron)
- НЕ игнорировать буферизацию → 3 сообщения подряд = 1 запрос
- НЕ отправлять >4000 символов в Telegram → Telegraph автоматически
- НЕ ставить MemoryMax < 4G для ботов с Claude CLI subprocess

---

## Changelog

<!-- Сюда автоматически добавляются уроки после каждого использования скилла -->
