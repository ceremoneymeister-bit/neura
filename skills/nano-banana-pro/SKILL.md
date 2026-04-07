---
name: nano-banana-pro
description: "Use when generating or editing images via AI — 'создай картинку', 'сгенерируй изображение', 'отредактируй фото', 'нарисуй', image generation, AI art"
proactive_enabled: true
proactive_trigger_1_type: event
proactive_trigger_1_condition: "нужна картинка/иллюстрация"
proactive_trigger_1_action: "сгенерировать через Grsai API"
learning_track_success: true
learning_track_corrections: true
learning_evolve_threshold: 5
learning_auto_update: [anti-patterns, triggers, changelog]
---

# Nano Banana Pro — AI-генерация изображений

## Два движка

### 1. Grsai API (основной) — генерация
- **Скрипт:** `/root/Antigravity/scripts/grsai-image.py`
- **API-ключ:** `GRSAI_API_KEY` в `.env`
- **Стоимость:** ~$0.012/картинка (nano-banana-pro)
- **Время:** ~30-90 сек
- **Зависимости:** никаких (stdlib Python)

### 2. Gemini API (fallback) — генерация + редактирование
- **Скрипт:** `/root/Antigravity/scripts/gemini-image.py`
- **API-ключ:** `GEMINI_API_KEY` в `.env`
- **Зависимости:** `google-genai`, `Pillow`

## Когда что использовать

| Задача | Движок | Почему |
|--------|--------|--------|
| Генерация с нуля | **Grsai** | дешевле, авто-enhance, пресеты |
| Редактирование фото | Gemini | Grsai не поддерживает edit |
| Grsai недоступен | Gemini | fallback |

## ⚡ Prompt Enhancement — КЛЮЧЕВОЕ ОТЛИЧИЕ

**Скрипт автоматически обогащает промпт** — добавляет суффиксы качества и negative prompt. Это устраняет разрыв между "через UI красиво" и "через API плохо".

Дополнительно **агент ОБЯЗАН** обогатить промпт пользователя:
1. Перевести на английский
2. Определить тип (интерьер/портрет/лого/продукт/соцсети/арт/фото)
3. Добавить детали: стиль, освещение, качество, композиция
4. Выбрать пресет

## Быстрый старт

```bash
# С пресетом — рекомендуемый способ
python3 /root/Antigravity/scripts/grsai-image.py generate \
  --prompt "modern kitchen, white marble, natural light" \
  --preset interior \
  --filename kitchen.png

# С custom negative
python3 /root/Antigravity/scripts/grsai-image.py generate \
  --prompt "professional logo, hands symbol, zen" \
  --preset logo \
  --negative "text, complex, busy, photorealistic" \
  --filename logo.png

# Без enhancement (сырой промпт)
python3 /root/Antigravity/scripts/grsai-image.py generate \
  --prompt "exact prompt as-is" \
  --raw \
  --filename raw.png

# Посмотреть пресеты
python3 /root/Antigravity/scripts/grsai-image.py presets
```

## Пресеты

| Пресет | Формат | Для чего |
|--------|--------|----------|
| `interior` | 16:9 | Дизайн интерьера, архитектура |
| `portrait` | 3:4 | Портрет, headshot |
| `logo` | 1:1 | Логотип, иконка |
| `social` | 1:1 | Посты в соцсети |
| `product` | 1:1 | Продуктовая фотография |
| `art` | 1:1 | Художественная иллюстрация |
| `photo` | 16:9 | Фотореалистичное изображение |

## Параметры

| Параметр | Описание | По умолчанию |
|----------|----------|-------------|
| `--prompt` | Описание (на английском!) | обязательный |
| `--preset` | Пресет задачи | — |
| `--model` | `nano-banana-pro`, `nano-banana-2`, `nano-banana-fast` | `nano-banana-pro` |
| `--aspect` | Соотношение сторон | авто из пресета |
| `--negative` | Что исключить | авто из пресета |
| `--guidance` | Guidance scale | авто |
| `--seed` | Seed для воспроизводимости | случайный |
| `--steps` | Шаги инференса | авто |
| `--raw` | Без auto-enhance | false |
| `--filename` | Имя файла | авто (timestamp) |
| `--output-dir` | Директория | `/tmp` |
| `--ref` | URL референсного изображения | — |

## Модели

| Модель | Качество | Цена | Скорость |
|--------|----------|------|----------|
| `nano-banana-pro` | лучшее | ~$0.012 | ~30-90с |
| `nano-banana-2` | хорошее | ~$0.008 | ~30-60с |
| `nano-banana-fast` | базовое | ~$0.003 | ~10-20с |

## Gemini (fallback / редактирование)

```bash
python3 /root/Antigravity/scripts/gemini-image.py generate \
  --prompt "описание" --resolution 1K --filename out.png

python3 /root/Antigravity/scripts/gemini-image.py edit \
  --prompt "инструкция" --input source.png --filename out.png
```

## Интеграция с ботами

```bash
# Генерация → маркер в ответе
python3 /root/Antigravity/scripts/grsai-image.py generate \
  --prompt "описание" --preset photo --filename result.png
# В ответе бота: [FILE:/tmp/result.png]
```

## Антипаттерны

- НЕ писать промпты на русском → качество падает в 2-3 раза
- НЕ отправлять голый промпт пользователя → ВСЕГДА обогащать
- НЕ использовать Gemini для простой генерации → Grsai дешевле
- НЕ забывать `[FILE:]` маркер → иначе пользователь не получит картинку
- Файлы на Grsai сервере живут 2 часа → скрипт скачивает автоматически
- **Консистентность объекта в серии:** при генерации одного предмета в разных сценах — использовать `--seed` (одинаковый) + максимально детальное описание предмета (форма, материал, цвет, текстура, ярусы). Без seed и деталей объект будет разным на каждом кадре
- **Реальные товары:** описывать по реальному фото, а не абстрактно. "green wax Christmas tree candle with 4 tiers of overlapping leaf-shaped petals" >> "christmas tree candle"
- **gpt-image-1.5 + --ref:** таймаутит (120с, 1% прогресса). Не использовать для задач с reference-изображениями
- **Pixel-perfect inpainting (объект из фото + новый фон):** Grsai НЕ поддерживает edit/inpaint. Нужен Gemini edit или OpenAI DALL-E edit. Gemini заблокирован в Латвии (EEA) — требуется прокси (CF Worker / Atlas DNS)

---

## Changelog

<!-- Сюда автоматически добавляются уроки после каждого использования скилла -->










- 2026-04-07: 13 использований, success rate 100.0%, avg latency 20.5s
- 2026-04-07: 12 использований, success rate 100.0%, avg latency 20.0s
- 2026-04-07: 11 использований, success rate 100.0%, avg latency 18.9s
- 2026-04-07: 10 использований, success rate 100.0%, avg latency 17.6s
- 2026-04-07: 9 использований, success rate 100.0%, avg latency 17.6s
- 2026-04-07: 8 использований, success rate 100.0%, avg latency 17.7s
- 2026-04-07: 7 использований, success rate 100.0%, avg latency 18.2s
- 2026-04-07: 6 использований, success rate 100.0%, avg latency 18.6s
- 2026-04-07: 5 использований, success rate 100.0%, avg latency 19.7s