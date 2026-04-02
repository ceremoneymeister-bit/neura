# Задача: bot-branding.py — автоматическая визуальная упаковка ботов

## Что нужно создать
Скрипт `scripts/bot-branding.py` который генерирует полный визуальный пакет для Telegram-бота за 1 команду.

## Использование
```bash
python3 scripts/bot-branding.py \
  --name "PRO:МАССАЖ" \
  --niche "массаж и лимфодренаж" \
  --color "#6366F1" \
  --style "warm, professional, medical" \
  --output-dir /tmp/branding
```

## Что генерируется

### 1. Аватарка бота (avatar.png)
- Размер: 640x640 px
- Формат: PNG
- Стиль: минималистичный лого, flat design, символ ниши
- Генерация: `grsai-image.py --preset logo --aspect 1:1`
- После генерации: ресайз PIL до точных 640x640

### 2. Баннер описания (banner.png)
- Размер: 1280x640 px
- Для BotFather `/setdescriptionpic`
- Стиль: градиент цветов бренда, пространство для текста
- Генерация: `grsai-image.py --preset social --aspect 16:9`
- Ресайз до 1280x640

### 3. Welcome-картинка (welcome.jpg)
- Размер: 1280x720 px
- Отправляется при /start
- Стиль: дружелюбный, приглашающий, соответствует нише
- Генерация: `grsai-image.py --preset photo --aspect 16:9`
- Оптимизация: JPEG quality=85

### 4. Набор иконок (icons/)
- 4 штуки: program.png, tariffs.png, register.png, faq.png
- Размер: 256x256 px каждая
- Стиль: flat, цвет бренда, минимализм
- Генерация: `grsai-image.py --preset logo --aspect 1:1` x4

## Промпты по нишам (встроить в скрипт)

```python
NICHE_PROMPTS = {
    "massage": {
        "avatar": "minimalist logo, two hands massage symbol, warm amber gradient, zen circle, clean flat design",
        "banner": "professional banner, massage therapy, warm tones gradient, calm zen atmosphere, space for text",
        "welcome": "welcoming massage studio interior, warm lighting, professional spa atmosphere, inviting",
    },
    "fitness": {
        "avatar": "minimalist logo, abstract running figure, energetic green accent, dynamic motion, clean flat",
        "banner": "fitness banner, dynamic energy, green gradient, athletic silhouette, modern typography space",
        "welcome": "modern gym interior, motivating atmosphere, natural light, professional fitness",
    },
    "interior_design": {
        "avatar": "minimalist logo, geometric house cross-section, indigo accent, architectural lines, modern flat",
        "banner": "interior design banner, elegant room, indigo to cream gradient, sophisticated space for text",
        "welcome": "beautiful modern interior, scandinavian style, natural light, inspiring design workspace",
    },
    "beauty": {
        "avatar": "minimalist logo, abstract face profile, rose gold accent, elegant lines, modern flat design",
        "banner": "beauty salon banner, rose gold gradient, elegant feminine aesthetic, space for text",
        "welcome": "luxury beauty salon interior, soft lighting, elegant mirrors, professional atmosphere",
    },
    "craft": {
        "avatar": "minimalist logo, geometric handmade symbol, warm terracotta accent, artisan aesthetic, flat",
        "banner": "handmade craft banner, warm earthy tones, artisan workshop, natural textures, text space",
        "welcome": "cozy craft workshop, handmade products on wooden shelves, warm natural lighting",
    },
    "legal": {
        "avatar": "minimalist logo, balanced scales symbol, deep navy blue, professional, clean geometric flat",
        "banner": "professional legal banner, deep navy gradient, trust and authority, clean typography space",
        "welcome": "modern law office interior, bookshelves, professional desk, trust atmosphere",
    },
    "education": {
        "avatar": "minimalist logo, open book with light, blue accent, knowledge symbol, clean flat design",
        "banner": "education banner, blue gradient, bright inspiring atmosphere, growth symbol, text space",
        "welcome": "modern classroom or workshop, people learning, bright inspiring atmosphere, collaborative",
    },
    "default": {
        "avatar": "minimalist professional logo, abstract geometric symbol, {color} accent, clean flat design",
        "banner": "professional banner, {color} gradient, modern clean design, ample space for text",
        "welcome": "professional modern workspace, clean design, inviting atmosphere, {style}",
    },
}
```

## Архитектура скрипта

```python
#!/usr/bin/env python3
"""Bot Branding — генерация визуального пакета для Telegram-бота."""

import argparse
import subprocess
from PIL import Image
from pathlib import Path

def generate_image(prompt, preset, aspect, filename, output_dir):
    """Вызов grsai-image.py + ресайз."""
    cmd = [
        "python3", "scripts/grsai-image.py", "generate",
        "--prompt", prompt,
        "--preset", preset,
        "--aspect", aspect,
        "--filename", filename,
        "--output-dir", str(output_dir),
    ]
    subprocess.run(cmd, check=True)
    return output_dir / filename

def resize_image(path, width, height, format="PNG"):
    """Ресайз до точных размеров."""
    img = Image.open(path)
    img = img.resize((width, height), Image.LANCZOS)
    if format == "JPEG":
        img = img.convert("RGB")
    img.save(path, format, quality=85 if format == "JPEG" else None)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--niche", default="default")
    parser.add_argument("--color", default="#6366F1")
    parser.add_argument("--style", default="professional, modern")
    parser.add_argument("--output-dir", default="/tmp/branding")
    args = parser.parse_args()

    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)

    niche = NICHE_PROMPTS.get(args.niche, NICHE_PROMPTS["default"])

    # 1. Avatar
    avatar = generate_image(niche["avatar"], "logo", "1:1", "avatar.png", output)
    resize_image(avatar, 640, 640)

    # 2. Banner
    banner = generate_image(niche["banner"], "social", "16:9", "banner.png", output)
    resize_image(banner, 1280, 640)

    # 3. Welcome
    welcome = generate_image(niche["welcome"], "photo", "16:9", "welcome.jpg", output)
    resize_image(welcome, 1280, 720, "JPEG")

    print(f"✅ Branding ready: {output}/")
    print(f"   avatar.png  (640x640)")
    print(f"   banner.png  (1280x640)")
    print(f"   welcome.jpg (1280x720)")

if __name__ == "__main__":
    main()
```

## Зависимости
- `scripts/grsai-image.py` (уже есть)
- `Pillow` (pip install Pillow) — для ресайза
- `GRSAI_API_KEY` в `.env`

## Стоимость
~$0.036 за полный пакет (3 картинки × $0.012 на nano-banana-pro)

## Тестирование
```bash
python3 scripts/bot-branding.py --name "Тест" --niche "massage" --output-dir /tmp/test-branding
ls -la /tmp/test-branding/
```
