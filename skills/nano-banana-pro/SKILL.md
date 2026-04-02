---
name: nano-banana-pro
description: "Use when generating or editing images via AI — 'создай картинку', 'сгенерируй изображение', 'отредактируй фото', 'нарисуй', image generation, AI art"
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
