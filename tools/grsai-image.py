#!/usr/bin/env python3
"""
Grsai Image — генерация изображений через Grsai Nano Banana Pro API.

Использование:
  python3 grsai-image.py generate --prompt "описание" [--model nano-banana-pro] [--aspect 1:1]
  python3 grsai-image.py generate --prompt "описание" --enhance --preset interior
  python3 grsai-image.py generate --prompt "описание" --ref image_url --negative "text, watermark"

Модели:
  nano-banana-pro   — лучшее качество (~$0.012/картинка, ~30с)
  nano-banana-2     — хорошее качество (~$0.008/картинка, ~45с)
  nano-banana-fast  — быстро (~$0.003/картинка, ~15с)
  nano-banana       — стандартная (~$0.010/картинка)

Пресеты (--preset):
  interior  — дизайн интерьера, архитектурная фотография
  portrait  — портрет, headshot
  logo      — логотип, иконка
  social    — соцсети, баннер
  product   — продуктовая фотография
  art       — художественная иллюстрация
  photo     — фотореалистичное изображение
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# API endpoints
GRSAI_DRAW_URL = "https://api.grsai.com/v1/draw/nano-banana"
GRSAI_COMPLETIONS_URL = "https://api.grsai.com/v1/draw/completions"
GRSAI_RESULT_URL = "https://api.grsai.com/v1/draw/result"

# Поддерживаемые соотношения сторон
ASPECT_RATIOS = ["1:1", "16:9", "9:16", "4:3", "3:4", "4:1", "1:4", "8:1"]

# Доступные модели
MODELS = ["nano-banana-pro", "nano-banana-2", "nano-banana-fast", "nano-banana", "gpt-image-1.5"]

# Модели, использующие /v1/draw/completions (SSE streaming)
COMPLETIONS_MODELS = {"gpt-image-1.5"}

# Корень проекта
PROJECT_ROOT = Path(os.environ.get("NEURA_BASE", str(Path(__file__).resolve().parent.parent)))

# Таймауты
POLL_INTERVAL = 3
MAX_WAIT = 120

# ── Prompt Enhancement ──────────────────────────────────────────────────────

QUALITY_SUFFIX = "high quality, detailed, sharp focus, professional"

DEFAULT_NEGATIVE = "blurry, low quality, distorted, ugly, text, watermark, signature, cropped, out of frame, worst quality, low resolution"

PRESETS = {
    "interior": {
        "suffix": "professional interior photography, natural lighting, architectural digest style, 8K resolution, detailed textures, realistic materials",
        "negative": "blurry, low quality, distorted, ugly, text, watermark, cartoon, anime, illustration, unrealistic proportions, bad perspective",
        "aspect": "16:9",
    },
    "portrait": {
        "suffix": "professional portrait photography, soft natural lighting, shallow depth of field, high resolution, detailed skin texture",
        "negative": "blurry, low quality, distorted face, extra fingers, deformed, ugly, bad anatomy, watermark, text",
        "aspect": "3:4",
    },
    "logo": {
        "suffix": "clean vector-like design, minimalist, professional, flat design, centered composition, solid background",
        "negative": "blurry, photographic, realistic, complex background, text, 3D, gradient, busy, cluttered",
        "aspect": "1:1",
    },
    "social": {
        "suffix": "modern social media design, vibrant colors, eye-catching, professional, high contrast, clean composition",
        "negative": "blurry, low quality, boring, muted colors, text, watermark, cluttered",
        "aspect": "1:1",
    },
    "product": {
        "suffix": "professional product photography, studio lighting, clean white background, high detail, commercial quality",
        "negative": "blurry, low quality, distorted, shadows, dirty background, text, watermark",
        "aspect": "1:1",
    },
    "art": {
        "suffix": "artistic illustration, detailed, beautiful composition, professional digital art, trending on artstation",
        "negative": "blurry, low quality, ugly, deformed, text, watermark, bad anatomy",
        "aspect": "1:1",
    },
    "photo": {
        "suffix": "photorealistic, DSLR quality, natural lighting, high resolution, detailed, sharp focus, professional photography",
        "negative": "blurry, low quality, distorted, cartoon, anime, illustration, painting, text, watermark",
        "aspect": "16:9",
    },
}


def enhance_prompt(prompt, preset=None, no_enhance=False):
    """Обогащение промпта качественными суффиксами и пресетами."""
    if no_enhance:
        return prompt, DEFAULT_NEGATIVE, None

    parts = [prompt.rstrip(". ,")]

    if preset and preset in PRESETS:
        parts.append(PRESETS[preset]["suffix"])
        neg = PRESETS[preset]["negative"]
        default_aspect = PRESETS[preset]["aspect"]
    else:
        parts.append(QUALITY_SUFFIX)
        neg = DEFAULT_NEGATIVE
        default_aspect = None

    return ", ".join(parts), neg, default_aspect


# ── API ─────────────────────────────────────────────────────────────────────

def load_api_key(explicit_key=None):
    """Загрузка API-ключа: аргумент → переменная окружения → .env файл."""
    if explicit_key:
        return explicit_key

    key = os.environ.get("GRSAI_API_KEY")
    if key:
        return key

    for env_path in [Path.cwd() / ".env", PROJECT_ROOT / ".env"]:
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if line.startswith("GRSAI_API_KEY="):
                    value = line.split("=", 1)[1].strip().strip("'\"")
                    if value:
                        return value

    print("Ошибка: GRSAI_API_KEY не найден.", file=sys.stderr)
    sys.exit(1)


def generate_filename(description="generated"):
    """Генерация имени файла."""
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    safe_desc = "".join(c if c.isalnum() or c in "-_" else "-" for c in description[:30])
    safe_desc = safe_desc.strip("-") or "generated"
    return f"{timestamp}-{safe_desc}.png"


def api_request(url, data, api_key):
    """HTTP POST запрос к Grsai API."""
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        print(f"Ошибка API ({e.code}): {error_body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Ошибка соединения: {e.reason}", file=sys.stderr)
        sys.exit(1)


def download_file(url, output_path):
    """Скачивание файла по URL."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            with open(output_path, "wb") as f:
                f.write(resp.read())
        return True
    except Exception as e:
        print(f"Ошибка скачивания: {e}", file=sys.stderr)
        return False


def do_generate(args):
    """Генерация изображения."""
    api_key = load_api_key(args.api_key)

    # Prompt enhancement
    enhanced_prompt, auto_negative, default_aspect = enhance_prompt(
        args.prompt,
        preset=args.preset,
        no_enhance=args.raw,
    )

    # Aspect: explicit > preset > default
    aspect = args.aspect
    if aspect == "1:1" and default_aspect and not args.aspect_explicit:
        aspect = default_aspect

    # Negative prompt: explicit > auto
    negative = args.negative if args.negative else auto_negative

    # Подготовка запроса
    request_data = {
        "model": args.model,
        "prompt": enhanced_prompt,
        "aspectRatio": aspect,
        "urls": [],
        "webHook": "-1",
    }

    # Дополнительные параметры (если API их поддерживает — они просто игнорируются если нет)
    if negative and not args.raw:
        request_data["negativePrompt"] = negative
    if args.guidance:
        request_data["guidanceScale"] = args.guidance
    if args.seed is not None:
        request_data["seed"] = args.seed
    if args.steps:
        request_data["numInferenceSteps"] = args.steps

    # Референсные изображения (поддержка нескольких через запятую)
    if args.ref:
        urls = []
        for ref in args.ref.split(","):
            ref = ref.strip()
            if Path(ref).exists():
                print(f"⚠️  Grsai API принимает только URL: {ref}", file=sys.stderr)
                sys.exit(1)
            urls.append(ref)
        request_data["urls"] = urls

    # Вывод информации
    print(f"🎨 Промпт: {args.prompt}")
    if not args.raw:
        print(f"✨ Enhanced: {enhanced_prompt[:100]}...")
        if negative:
            print(f"🚫 Negative: {negative[:80]}...")
    print(f"📐 Модель: {args.model} | Формат: {aspect}")
    if args.preset:
        print(f"🎯 Пресет: {args.preset}")

    # Определяем endpoint
    draw_url = GRSAI_COMPLETIONS_URL if args.model in COMPLETIONS_MODELS else GRSAI_DRAW_URL

    # Отправка запроса
    result = api_request(draw_url, request_data, api_key)

    if result.get("code") != 0:
        print(f"Ошибка: {result.get('msg', 'unknown')}", file=sys.stderr)
        sys.exit(1)

    task_id = result["data"]["id"]
    print(f"⏳ Задача создана: {task_id}")

    # Polling результата (одинаковый для всех моделей)
    waited = 0
    image_url = None
    while waited < MAX_WAIT:
        time.sleep(POLL_INTERVAL)
        waited += POLL_INTERVAL

        status = api_request(GRSAI_RESULT_URL, {"id": task_id}, api_key)
        task_data = status.get("data", {})
        progress = task_data.get("progress", 0)
        task_status = task_data.get("status", "unknown")

        if task_status == "succeeded":
            results = task_data.get("results", [])
            if results:
                image_url = results[0].get("url", "")
            break
        elif task_status == "failed":
            error = task_data.get("error") or task_data.get("failure_reason") or "unknown"
            print(f"❌ Генерация не удалась: {error}", file=sys.stderr)
            sys.exit(1)
        else:
            print(f"   [{waited}s] {task_status} {progress}%", end="\r")

    if not image_url:
        print(f"\n⏰ Таймаут или пустой результат.", file=sys.stderr)
        sys.exit(1)

    # ── Скачивание результата (общее для обоих методов) ──
    filename = args.filename or generate_filename("generated")
    if not filename.endswith(".png"):
        filename += ".png"

    output_dir = Path(args.output_dir) if args.output_dir else Path("/tmp")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename

    if download_file(image_url, str(output_path)):
        size_kb = output_path.stat().st_size / 1024
        print(f"✅ Сохранено: {output_path} ({size_kb:.0f} KB)")
        print(f"🔗 URL (2 часа): {image_url}")
        print(f"PATH:{output_path}")
        return str(output_path)
    else:
        print(f"⚠️  Не удалось скачать. URL: {image_url}")
        print(f"PATH:{image_url}")
        return image_url


def do_presets(args):
    """Показать доступные пресеты."""
    print("Доступные пресеты:\n")
    for name, cfg in PRESETS.items():
        print(f"  {name:12s} — aspect: {cfg['aspect']}")
        print(f"  {'':12s}   suffix: {cfg['suffix'][:70]}...")
        print(f"  {'':12s}   negative: {cfg['negative'][:60]}...")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Grsai Image — генерация изображений через Nano Banana Pro API"
    )
    sub = parser.add_subparsers(dest="command")

    # generate
    gen = sub.add_parser("generate", help="Генерация изображения")
    gen.add_argument("--prompt", required=True, help="Описание изображения")
    gen.add_argument("--model", choices=MODELS, default="nano-banana-pro",
                     help="Модель (по умолчанию: nano-banana-pro)")
    gen.add_argument("--aspect", choices=ASPECT_RATIOS, default="1:1",
                     help="Соотношение сторон (по умолчанию: 1:1)")
    gen.add_argument("--preset", choices=list(PRESETS.keys()),
                     help="Пресет задачи (interior, portrait, logo, social, product, art, photo)")
    gen.add_argument("--negative", help="Negative prompt (что исключить)")
    gen.add_argument("--guidance", type=float, help="Guidance scale (по умолчанию: авто)")
    gen.add_argument("--seed", type=int, help="Seed для воспроизводимости")
    gen.add_argument("--steps", type=int, help="Количество шагов инференса")
    gen.add_argument("--raw", action="store_true",
                     help="Без auto-enhance (отправить промпт как есть)")
    gen.add_argument("--filename", help="Имя выходного файла")
    gen.add_argument("--output-dir", help="Директория (по умолчанию: /tmp)")
    gen.add_argument("--ref", help="URL референсных изображений (до 6, через запятую)")
    gen.add_argument("--api-key", help="API-ключ Grsai")

    # presets
    sub.add_parser("presets", help="Показать доступные пресеты")

    args = parser.parse_args()

    # Hack: определяем, был ли --aspect задан явно
    args.aspect_explicit = "--aspect" in sys.argv

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "generate":
        do_generate(args)
    elif args.command == "presets":
        do_presets(args)


if __name__ == "__main__":
    main()
