---
name: agent-test-suite
description: "Полный функциональный тест-сьют для AI-агентов (капсул Neura). 80+ тестов по 12 категориям: инфра, messaging, файлы, интеграции, скиллы, память, безопасность, UX."
version: 1.0.0
author: Dmitry Rostovtsev (ceremoneymeister)
created: 2026-03-24
updated: 2026-03-24
category: testing
tags: [testing, audit, bots, capsules, QA, functional-testing, integration-testing]
risk: medium
---

# Agent Test Suite — полное функциональное тестирование AI-агентов

## Триггеры

- "протестируй агента", "полный тест бота", "тест-сьют"
- "проверь все функции", "функциональный тест"
- "agent test suite", "full test", "QA бота"
- "что работает, что нет?", "полная проверка"
- После крупного обновления бота → автоматический прогон

## Философия

Каждая функция агента должна иметь автоматический тест. Если функция не тестируется — она сломается незаметно. Тесты разделены на **12 категорий** и **3 уровня**:

| Уровень | Что проверяет | Как | Риск |
|---------|---------------|-----|------|
| L0 — Static | Код, конфиги, файлы | Чтение файловой системы | Нулевой |
| L1 — Runtime | Процессы, порты, ресурсы | systemctl, docker, API-вызовы | Низкий |
| L2 — Functional | Реальные Telegram-сообщения боту | Bot API → ожидание ответа | Средний |

## Реестр категорий

```
12 категорий × ~7 тестов = 80+ тестов
```

| # | Категория | Код | Тестов | Уровень |
|---|-----------|-----|--------|---------|
| 1 | Инфраструктура | INFRA | 8 | L0-L1 |
| 2 | Базовый messaging | MSG | 6 | L2 |
| 3 | Файлы и документы | FILE | 8 | L0-L2 |
| 4 | Память и дневник | MEM | 7 | L0-L1 |
| 5 | Скиллы | SKILL | 6 | L0-L1 |
| 6 | Интеграции | INTG | 10 | L0-L2 |
| 7 | Голос и медиа | MEDIA | 5 | L0-L2 |
| 8 | UX и интерфейс | UX | 7 | L0-L2 |
| 9 | Безопасность | SEC | 6 | L0-L1 |
| 10 | Производительность | PERF | 5 | L1 |
| 11 | Мульти-пользователь | MULTI | 4 | L0-L2 |
| 12 | Cross-capsule | CROSS | 5 | L0 |

---

## Категория 1: INFRA — Инфраструктура (L0-L1)

Наследует и расширяет capsule-audit H-01..H-08.

| ID | Тест | Метод | Pass-критерий |
|----|------|-------|---------------|
| INFRA-01 | Сервис запущен | `systemctl is-active` / `docker ps` | active/running |
| INFRA-02 | Нет свежих ошибок (10 мин) | `journalctl` / `docker logs` за 10м | 0 строк ERROR/CRITICAL |
| INFRA-03 | sessions.json валиден | JSON-парсинг | valid JSON |
| INFRA-04 | Нет зомби claude-процессов | `ps aux | grep claude` > 10 мин | 0 зомби |
| INFRA-05 | Память < 80% лимита | `docker stats` / cgroup | < 80% |
| INFRA-06 | Диск < 85% | `df -h` рабочей директории | < 85% |
| INFRA-07 | Bot-токен валиден | `getMe` API-вызов | username совпадает |
| INFRA-08 | Порты не заняты конфликтно | `lsof -i` для портов капсулы | нет конфликтов |

---

## Категория 2: MSG — Базовый messaging (L2)

Реальные сообщения боту через Bot API. ⚠️ НЕ через Telethon (session lock). Тестировать в DM.

| ID | Тест | Сообщение боту | Ожидаемый ответ | Таймаут |
|----|------|----------------|-----------------|---------|
| MSG-01 | Простой ответ | "Сколько будет 2+2?" | Содержит "4" | 90с |
| MSG-02 | Контекст сохраняется | "Прибавь к результату 10" | Содержит "14" | 90с |
| MSG-03 | Длинный ответ | "Напиши подробный план на неделю по пунктам" | >500 символов ИЛИ Telegraph-ссылка | 180с |
| MSG-04 | Восстановление после /cancel | "/cancel" → "Привет!" | Нормальный приветственный ответ | 90с |
| MSG-05 | Emoji и Unicode | "Расскажи про 🎵 музыку и ♻️ экологию" | Не крашится, содержит текст | 90с |
| MSG-06 | Пустое сообщение / спец-символы | "```test\n<script>alert(1)</script>```" | Не крашится, отвечает корректно | 90с |

**Правила:**
- MSG-01 и MSG-02 СТРОГО последовательно (тест персистентности)
- Пауза 15-30с между MSG-01 и MSG-02 (дождаться ответа)
- НЕ использовать [AUDIT] или другие префиксы
- Все тесты в DM, НЕ в HQ-топиках

---

## Категория 3: FILE — Файлы и документы (L0-L2)

| ID | Тест | Уровень | Метод | Pass-критерий |
|----|------|---------|-------|---------------|
| FILE-01 | PDF-генерация (код) | L0 | Проверить наличие md2pdf.py / [FILE:] в коде | Файл существует + импортируется |
| FILE-02 | PDF-генерация (runtime) | L2 | Сообщение: "Создай PDF-документ с планом на день" | Получен document в ответе |
| FILE-03 | Telegraph для длинных | L0 | Grep `telegraph` / `telegra.ph` в коде бота | Найден обработчик >4000 символов |
| FILE-04 | Telegraph (runtime) | L2 | Сообщение требующее >4000 символов | Ответ содержит ссылку telegra.ph |
| FILE-05 | [FILE:] маркер в коде | L0 | Grep `\[FILE:` в коде бота | Парсер маркера найден |
| FILE-06 | Изображение (генерация) | L0 | Проверить наличие image_gen capability | Код или API-ключ найден |
| FILE-07 | QR-код генерация | L0 | Проверить `qrcode` модуль / capsule-tools.py | Модуль доступен |
| FILE-08 | DOCX/XLSX генерация | L0 | Проверить `python-docx` / `openpyxl` в requirements | Модули доступны |

---

## Категория 4: MEM — Память и дневник (L0-L1)

| ID | Тест | Уровень | Метод | Pass-критерий |
|----|------|---------|-------|---------------|
| MEM-01 | Diary директория | L0 | Проверить наличие diary/ или data/diary/ | Директория существует |
| MEM-02 | Diary записи пишутся | L1 | Проверить дату последней записи | ≤ 24 часов назад |
| MEM-03 | Learnings файл | L0 | Проверить memory/learnings.md | Файл существует, не пуст |
| MEM-04 | Corrections файл | L0 | Проверить memory/corrections.md | Файл существует |
| MEM-05 | [LEARN:] маркер | L0 | Grep `\[LEARN:` в коде обработки ответов | Парсер маркера найден |
| MEM-06 | [CORRECTION:] маркер | L0 | Grep `\[CORRECTION:` в коде | Парсер маркера найден |
| MEM-07 | Diary не переполнен | L1 | Подсчёт файлов в diary/ | < 200 файлов (иначе ротация) |

---

## Категория 5: SKILL — Скиллы (L0-L1)

| ID | Тест | Уровень | Метод | Pass-критерий |
|----|------|---------|-------|---------------|
| SKILL-01 | Skills директория | L0 | Проверить skills/ | Существует, не пуста |
| SKILL-02 | Skills auto-discovery | L0 | Grep `get_skill_table` или `skills.py` в коде | Функция найдена |
| SKILL-03 | SKILL.md в каждом скилле | L0 | Проверить skills/*/SKILL.md | ≥ 80% скиллов имеют SKILL.md |
| SKILL-04 | {{SKILL_TABLE}} подстановка | L0 | Grep в CLAUDE.md.template | Placeholder найден |
| SKILL-05 | Hot-reload CLAUDE.md | L0 | Grep `mtime` или `_ctx_cache` в коде | Механизм перечитки найден |
| SKILL-06 | /reload команда | L0 | Grep `reload` в handlers | Команда найдена |

---

## Категория 6: INTG — Интеграции (L0-L2)

Тесты зависят от capabilities капсулы. Пропускать если capability отсутствует.

| ID | Тест | Capability | Уровень | Метод | Pass-критерий |
|----|------|-----------|---------|-------|---------------|
| INTG-01 | Google OAuth настроен | google | L0 | Проверить google_oauth_bot.py / credentials | Файлы существуют |
| INTG-02 | Google Sheets доступ | google | L2 | Сообщение: "Покажи последние данные из таблицы" | Не ошибка авторизации |
| INTG-03 | Google Calendar | icalendar | L0 | Проверить icloud_calendar или gcal интеграцию | Код существует |
| INTG-04 | Bitrix24 подключение | bitrix | L0 | Проверить integrations/bitrix24/ или .env BITRIX_* | Токен найден |
| INTG-05 | Bitrix24 API | bitrix | L1 | Вызвать Bitrix REST API /profile | 200 OK |
| INTG-06 | VK API | vk | L0 | Проверить integrations/vk/ или .env VK_* | Токен найден |
| INTG-07 | VK API вызов | vk | L1 | Вызвать groups.getById | 200 OK |
| INTG-08 | Userbot подключён | userbot | L0 | Проверить .session файл | Файл существует, размер > 0 |
| INTG-09 | Userbot не залочен | userbot | L1 | Проверить что нет другого процесса с этой сессией | Нет конфликта |
| INTG-10 | Mail интеграция | mail | L0 | Проверить SMTP/IMAP настройки | Найдены в .env |

---

## Категория 7: MEDIA — Голос и медиа (L0-L2)

| ID | Тест | Уровень | Метод | Pass-критерий |
|----|------|---------|-------|---------------|
| MEDIA-01 | STT поддержка (код) | L0 | Grep `deepgram\|whisper\|transcri` в коде | Обработчик voice найден |
| MEDIA-02 | Deepgram API ключ | L0 | Проверить DEEPGRAM_API_KEY в .env | Ключ не пуст |
| MEDIA-03 | Image анализ (код) | L0 | Grep `photo\|image.*analys\|Read.*tool.*image` | Обработчик фото найден |
| MEDIA-04 | TTS поддержка | L0 | Grep `tts\|text.to.speech\|voice.*generat` | Код найден |
| MEDIA-05 | Audio конвертация | L0 | `which ffmpeg` и `which ffprobe` | Оба доступны |

---

## Категория 8: UX — Интерфейс пользователя (L0-L2)

| ID | Тест | Уровень | Метод | Pass-критерий |
|----|------|---------|-------|---------------|
| UX-01 | /start команда | L2 | Отправить /start | Ответ с приветствием |
| UX-02 | /menu команда | L2 | Отправить /menu | InlineKeyboard в ответе |
| UX-03 | Menu callbacks | L0 | Grep `menu:open\|menu:close\|menu:stats` | Все 3 callback найдены |
| UX-04 | Response buttons | L0 | Grep `build_response_buttons\|InlineKeyboard` в ответах | Кнопки генерируются |
| UX-05 | Settings menu | L0 | Grep `menu:model\|settings\|⚡.*Fast\|🔬.*Deep` | Переключатель модели найден |
| UX-06 | Streaming typing | L0 | Grep `send_chat_action\|typing` | Индикатор набора отправляется |
| UX-07 | Error handling | L0 | Grep `try.*except\|error.*handler\|on_error` | Обработка ошибок есть |

---

## Категория 9: SEC — Безопасность (L0-L1)

| ID | Тест | Уровень | Метод | Pass-критерий | Критичность |
|----|------|---------|-------|---------------|-------------|
| SEC-01 | --allowedTools ограничение | L0 | Grep `allowedTools` в коде запуска Claude | Bash ограничен | 🔴 CRITICAL |
| SEC-02 | .env не в git | L0 | Проверить .gitignore содержит .env | Да |
| SEC-03 | Secrets не в CLAUDE.md | L0 | Grep `BOT_TOKEN\|API_KEY\|password` в CLAUDE.md | Нет секретов |
| SEC-04 | Docker изоляция (ro mounts) | L0 | Проверить `:ro` в docker-compose.yml | CLAUDE.md, skills/, tools/ read-only |
| SEC-05 | Memory limit задан | L0 | Проверить `mem_limit` в docker-compose.yml | ≥ 2G, ≤ 6G |
| SEC-06 | Admin IDs проверяются | L0 | Grep `ADMIN_IDS\|admin.*check\|is_admin` | Проверка прав найдена |

---

## Категория 10: PERF — Производительность (L1)

| ID | Тест | Уровень | Метод | Pass-критерий |
|----|------|---------|-------|---------------|
| PERF-01 | Время ответа < 60с | L1 | Замер MSG-01 (простой вопрос) | < 60 секунд |
| PERF-02 | Память процесса | L1 | RSS процесса бота | < 500 MB |
| PERF-03 | sessions.json размер | L1 | `wc -c sessions.json` | < 5 MB |
| PERF-04 | Diary размер | L1 | `du -sh diary/` | < 50 MB |
| PERF-05 | Disk I/O | L1 | `iostat` или `/proc/diskstats` | Нет аномалий |

---

## Категория 11: MULTI — Мульти-пользователь (L0-L2)

Применимо только к капсулам с capability `multi_user` (Марина).

| ID | Тест | Уровень | Метод | Pass-критерий |
|----|------|---------|-------|---------------|
| MULTI-01 | employees/ директория | L0 | Проверить employees/*.md | Файлы существуют |
| MULTI-02 | Изоляция сессий | L0 | Проверить session_id содержит user_id | Разные пользователи = разные сессии |
| MULTI-03 | Персонализация | L0 | Grep `employee.*profile\|user.*context` | Контекст сотрудника загружается |
| MULTI-04 | Лимит пользователей | L0 | Подсчёт уникальных user_id в sessions.json | ≤ max_users из config |

---

## Категория 12: CROSS — Cross-capsule consistency (L0)

Сравнение между капсулами для единообразия.

| ID | Тест | Метод | Pass-критерий |
|----|------|-------|---------------|
| CROSS-01 | execute_always_deep сигнатура | Сравнить функцию между капсулами | Одинаковые параметры |
| CROSS-02 | Маркеры [FILE:] [LEARN:] [CORRECTION:] | Grep во всех капсулах | Все поддерживают |
| CROSS-03 | Telegraph обработка | Grep `>4000` или telegraph | Все поддерживают |
| CROSS-04 | CLAUDE.md существует | Проверить во всех | У всех есть |
| CROSS-05 | sessions.json структура | JSON-schema сравнение | Одинаковая |

---

## Запуск тестов

### CLI-интерфейс

```bash
# Базовый синтаксис
python3 .agent/skills/agent-test-suite/scripts/run-tests.py \
  --capsule <id|all> \
  [--category <cat1,cat2,...>] \
  [--level <L0|L1|L2>] \
  [--test <TEST-ID>] \
  [--report <path.md>] \
  [--json] \
  [--dry-run]

# Примеры:

# Полный тест одной капсулы (все категории, все уровни)
python3 .agent/skills/agent-test-suite/scripts/run-tests.py --capsule victoria

# Только статические тесты (безопасно, без отправки сообщений)
python3 .agent/skills/agent-test-suite/scripts/run-tests.py --capsule all --level L0

# Конкретная категория
python3 .agent/skills/agent-test-suite/scripts/run-tests.py --capsule marina --category SEC,MEM

# Один тест
python3 .agent/skills/agent-test-suite/scripts/run-tests.py --capsule victoria --test MSG-01

# Полный аудит с отчётом
python3 .agent/skills/agent-test-suite/scripts/run-tests.py --capsule all --report /tmp/full-audit.md

# JSON для автоматизации (интеграция с админкой)
python3 .agent/skills/agent-test-suite/scripts/run-tests.py --capsule all --level L0 --json

# Dry run — показать план без выполнения
python3 .agent/skills/agent-test-suite/scripts/run-tests.py --capsule all --dry-run
```

### Из Claude Code (рекомендуемый способ)

```
→ "протестируй Викторию полностью"
→ "быстрый тест всех ботов (только L0)"
→ "проверь безопасность всех капсул"
→ "тест интеграций Марины"
```

Claude Code читает этот SKILL.md и выполняет тесты по описанным правилам.

### Из Admin Panel (интеграция)

Кнопка "Запустить тест" на странице Audit → вызывает:
```
POST /admin/api/audit/run
Body: {"capsule": "victoria", "categories": ["all"], "level": "L0"}
```
API запускает `run-tests.py --json` и возвращает результат.

---

## Отчёт

### Формат отчёта (--report)

```markdown
# 🔍 Agent Test Suite — Отчёт
**Дата:** 2026-03-24 14:30
**Капсула:** Victoria Sel (@victoria_sel_ai_bot)

## Сводка
| Метрика | Значение |
|---------|----------|
| Всего тестов | 67 |
| ✅ Passed | 58 |
| ❌ Failed | 4 |
| ⏭️ Skipped | 5 |
| Score | 93.5% |

## По категориям
| Категория | Pass | Fail | Skip | Score |
|-----------|------|------|------|-------|
| INFRA | 8/8 | 0 | 0 | 100% |
| MSG | 5/6 | 1 | 0 | 83% |
| FILE | 6/8 | 0 | 2 | 100% |
| MEM | 7/7 | 0 | 0 | 100% |
| ...

## ❌ Проваленные тесты
### MSG-03: Длинный ответ
- **Ожидание:** >500 символов или Telegraph
- **Результат:** 423 символа, без Telegraph-ссылки
- **Лог:** `Response length: 423 chars, no telegra.ph URL found`
- **Рекомендация:** Проверить порог в smart-response (должен быть >4000)

### SEC-01: --allowedTools
- **Ожидание:** Bash ограничен
- **Результат:** Claude CLI запускается без --allowedTools
- **Критичность:** 🔴 CRITICAL
- **Рекомендация:** Добавить --allowedTools в execute_always_deep()
```

### Scoring

```
Score = (passed / (total - skipped)) × 100

Грейды:
  95-100% → 🏆 A+ (Production Ready)
  85-94%  → ✅ A  (Хорошо, мелкие недочёты)
  70-84%  → ⚠️ B  (Работает, но есть проблемы)
  50-69%  → 🟡 C  (Критические проблемы)
  < 50%   → 🔴 D  (Не готов к продакшну)

Модификатор: если skip > 30% → грейд понижается на 1 ступень
Модификатор: если есть CRITICAL fail → максимум B (независимо от score)
```

---

## Capability-зависимые тесты

Не все тесты применимы ко всем капсулам. Тест пропускается (skip) если у капсулы нет нужной capability.

### Маппинг capability → тесты

| Capability | Тесты |
|-----------|--------|
| userbot | INTG-08, INTG-09 |
| google | INTG-01, INTG-02, INTG-03 |
| bitrix | INTG-04, INTG-05 |
| vk | INTG-06, INTG-07 |
| mail | INTG-10 |
| tts | MEDIA-04 |
| image_gen | FILE-06 |
| multi_user | MULTI-01..MULTI-04 |
| telegraph | FILE-03, FILE-04 |
| pdf | FILE-01, FILE-02 |

### Текущие capabilities по капсулам

| Капсула | Capabilities |
|---------|-------------|
| Victoria | userbot, icalendar, tts, image_gen, pdf, qr, telegraph |
| Marina | userbot, bitrix, vk, google, icalendar, mail, telegraph, pdf, multi_user, markers |
| Yulia | userbot, google, telegraph |
| Maxim | vk, tts, image_gen, telegraph, pdf, markers |

---

## Anti-patterns

- ❌ НЕ использовать Telethon для тестовых сообщений (session lock!)
- ❌ НЕ запускать L2 тесты на Максима без явной просьбы (чужой сервер)
- ❌ НЕ удалять/модифицировать сессии ботов во время теста
- ❌ НЕ использовать [AUDIT] или другие префиксы в тестовых сообщениях
- ❌ НЕ тестировать в HQ-топиках — тестировать в DM
- ❌ НЕ запускать полный L2 чаще раза в день (нагрузка на Claude API)
- ❌ НЕ доверять score 100% если >50% тестов skipped
- ❌ НЕ тестировать L2 все капсулы параллельно (перегрузка сервера)

---

## Конфигурация

- **Реестр капсул:** `/opt/neura-admin/capsule-registry.json` (основной) ИЛИ `.agent/skills/capsule-audit/config/capsule-profiles.json` (fallback)
- **Тест-конфиг:** `.agent/skills/agent-test-suite/config/test-config.json`
- **Отчёты:** `.agent/skills/agent-test-suite/reports/` (хранить последние 10)

### test-config.json

```json
{
  "timeouts": {
    "L2_simple": 90,
    "L2_long": 180,
    "L2_file": 300
  },
  "limits": {
    "max_parallel_L2": 1,
    "max_diary_files": 200,
    "max_sessions_size_mb": 5,
    "max_memory_mb": 500,
    "disk_warning_percent": 85
  },
  "scoring": {
    "skip_penalty_threshold": 0.3,
    "critical_max_grade": "B"
  }
}
```

---

## Расширение тестов

### Добавление нового теста

1. Определи категорию (INFRA/MSG/FILE/MEM/SKILL/INTG/MEDIA/UX/SEC/PERF/MULTI/CROSS)
2. Определи уровень (L0/L1/L2)
3. Определи зависимость от capability (если есть)
4. Добавь строку в таблицу соответствующей категории в этом SKILL.md
5. Реализуй тест в `scripts/run-tests.py`
6. Добавь в test-config.json если нужны параметры

### Добавление новой категории

1. Выбери 3-5 буквенный код
2. Создай секцию в SKILL.md
3. Добавь в реестр категорий
4. Реализуй в скрипте

---

## Интеграция с другими скиллами

| Скилл | Взаимодействие |
|-------|---------------|
| capsule-audit | Базовые H-01..H-08 наследуются как INFRA-01..INFRA-08 |
| systematic-debugging | При CRITICAL fail → автоматический дебаг |
| release-notes | После успешного полного теста → уведомление в HQ |
| capsule-ecosystem | Новые капсулы → первый прогон L0 после создания |
| neura-app (admin) | Кнопка "Аудит" → вызывает run-tests.py --json |

---

## Рекомендуемый workflow

### После обновления бота
```
L0 + L1 тесты → если pass → L2 (MSG-01, MSG-02) → если pass → деплой подтверждён
```

### Еженедельный полный аудит (понедельник 03:00)
```
Все капсулы × все категории × L0+L1 → отчёт → HQ topic 8
L2 тесты только при провале L0/L1
```

### Перед демо/продажей
```
Конкретная капсула × полный L0+L1+L2 → убедиться score ≥ 95%
```

### При жалобе пользователя
```
Конкретная капсула × конкретная категория → найти проблему → systematic-debugging
```
