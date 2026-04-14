#!/usr/bin/env python3
"""
Marp Image — генерация визуалов для презентаций.

Объединяет 4 источника:
  1. grsai   — AI-генерация по тексту (nano-banana-pro, дешёвый)
  2. openrouter — AI-генерация + редактирование + vision (Gemini Image, GPT-5 Image)
  3. unsplash — стоковые фото по ключевому слову
  4. qr      — QR-код как SVG

Использование:
  python3 marp-image.py grsai --prompt "бизнес иллюстрация" --aspect 16:9 --preset slide
  python3 marp-image.py openrouter --prompt "иллюстрация AI-агента" [--ref image.png] [--model gemini-3.1-flash-image-preview]
  python3 marp-image.py unsplash --query "business meeting" --orientation landscape
  python3 marp-image.py qr --data "https://t.me/your_bot" --size 200
  python3 marp-image.py resize --input img.png --target 16:9  (или --target a4)

Все команды сохраняют результат в /tmp/marp-output/ и печатают PATH:<путь>
"""

import argparse
import base64
import json
import os
import sys
import subprocess
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path("/tmp/marp-output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# === Размеры для Marp ===
TARGETS = {
    "16:9": (1280, 720),
    "a4": (794, 1123),
    "4:3": (960, 720),
    "1:1": (800, 800),
}

# === ENV ===
def load_env():
    """Загрузить .env файлы."""
    for env_path in [Path("/opt/neura-v2/.env"), Path("/root/Antigravity/.env")]:
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    key, val = line.split("=", 1)
                    val = val.strip().strip("'\"")
                    if key.strip() and val:
                        os.environ.setdefault(key.strip(), val)

load_env()


# ── 1. GRSAI (text → image) ─────────────────────────────────────────────────

SLIDE_PRESETS = {
    "slide": {
        "suffix": "flat vector business illustration, clean lines, minimal detail, professional, pastel colors, white background, no text, no watermark",
        "negative": "blurry, low quality, text, watermark, signature, busy, cluttered, photographic",
        "aspect": "16:9",
    },
    "slide-dark": {
        "suffix": "flat vector illustration, clean lines, minimal detail, professional, neon accents, dark background, no text, no watermark",
        "negative": "blurry, low quality, text, watermark, bright background, busy",
        "aspect": "16:9",
    },
    "bg-abstract": {
        "suffix": "abstract gradient background, soft colors, professional, clean, minimal, no objects, no text",
        "negative": "text, watermark, objects, faces, busy, cluttered",
        "aspect": "16:9",
    },
    "bg-photo": {
        "suffix": "professional photography, soft focus background, business environment, high resolution",
        "negative": "blurry, low quality, text, watermark, faces in focus",
        "aspect": "16:9",
    },
    "icon": {
        "suffix": "single flat icon, vector style, centered, solid color background, minimal, no text",
        "negative": "text, watermark, multiple objects, busy, photographic",
        "aspect": "1:1",
    },
    "a4-cover": {
        "suffix": "professional document cover illustration, clean, premium, minimal, business style",
        "negative": "text, watermark, busy, cluttered, low quality",
        "aspect": "3:4",
    },
}

def cmd_grsai(args):
    """Генерация через grsai-image.py (уже установлен)."""
    grsai_script = Path("/opt/neura-v2/tools/grsai-image.py")
    if not grsai_script.exists():
        print("Ошибка: grsai-image.py не найден", file=sys.stderr)
        sys.exit(1)

    cmd = [
        sys.executable, str(grsai_script), "generate",
        "--prompt", args.prompt,
        "--model", args.model or "nano-banana-pro",
        "--output-dir", str(OUTPUT_DIR),
    ]

    # Пресет для слайдов
    preset = args.preset
    if preset and preset in SLIDE_PRESETS:
        p = SLIDE_PRESETS[preset]
        enhanced = f"{args.prompt}, {p['suffix']}"
        cmd[cmd.index("--prompt") + 1] = enhanced
        cmd.extend(["--negative", p["negative"]])
        if not args.aspect:
            cmd.extend(["--aspect", p["aspect"]])
        cmd.append("--raw")  # уже enhanced вручную
    elif preset:
        cmd.extend(["--preset", preset])

    if args.aspect:
        cmd.extend(["--aspect", args.aspect])
    if args.ref:
        cmd.extend(["--ref", args.ref])

    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    # Извлекаем PATH из вывода
    for line in result.stdout.splitlines():
        if line.startswith("PATH:"):
            path = line[5:]
            # Resize если нужно
            if args.target:
                path = resize_image(path, args.target)
            print(f"PATH:{path}")
            return path
    sys.exit(result.returncode or 1)


# ── 2. OPENROUTER (text → image, image+text → image) ────────────────────────

OPENROUTER_MODELS = {
    "gemini-image": "google/gemini-3.1-flash-image-preview",
    "gpt5-image": "openai/gpt-5-image",
    "flux-pro": "black-forest-labs/flux.2-pro",
    "flux-klein": "black-forest-labs/flux.2-klein-4b",
}

def cmd_openrouter(args):
    """Генерация через OpenRouter API (поддержка vision + image output)."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("Ошибка: OPENROUTER_API_KEY не найден", file=sys.stderr)
        sys.exit(1)

    model = OPENROUTER_MODELS.get(args.model, args.model) if args.model else OPENROUTER_MODELS["gemini-image"]

    # Собираем сообщение
    content = []

    # Референсное изображение (vision input)
    if args.ref:
        ref_path = Path(args.ref)
        if ref_path.exists():
            with open(ref_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            ext = ref_path.suffix.lower().lstrip(".")
            mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}.get(ext, "image/png")
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{b64}"}
            })
        else:
            content.append({
                "type": "image_url",
                "image_url": {"url": args.ref}
            })

    content.append({"type": "text", "text": args.prompt})

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
    }

    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://ceremoneymeister.ru",
        },
    )

    print(f"🎨 OpenRouter: {model}")
    print(f"📝 Промпт: {args.prompt[:80]}...")
    if args.ref:
        print(f"🖼️  Референс: {args.ref}")

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        print(f"Ошибка API ({e.code}): {error_body}", file=sys.stderr)
        sys.exit(1)

    # Извлекаем изображение из ответа
    choices = data.get("choices", [])
    if not choices:
        print(f"Ошибка: пустой ответ от OpenRouter", file=sys.stderr)
        sys.exit(1)

    message = choices[0].get("message", {})

    # OpenRouter возвращает изображения в message.images[] (отдельно от content)
    images = message.get("images") or []
    content_parts = message.get("content") or []

    # Текстовый ответ (если есть)
    if isinstance(content_parts, str) and content_parts:
        print(f"📝 {content_parts[:150]}")

    # Ищем изображение: сначала в images[], потом в content[]
    image_url = None
    for img in images:
        if isinstance(img, dict):
            iu = img.get("image_url", {})
            if isinstance(iu, dict):
                image_url = iu.get("url", "")
            elif isinstance(iu, str):
                image_url = iu
        elif isinstance(img, str):
            image_url = img
        if image_url:
            break

    # Fallback: проверяем content[] (старый формат)
    if not image_url and isinstance(content_parts, list):
        for part in content_parts:
            if isinstance(part, dict) and part.get("type") == "image_url":
                iu = part.get("image_url", {})
                image_url = iu.get("url", "") if isinstance(iu, dict) else str(iu)
                if image_url:
                    break

    if not image_url:
        print(f"⚠️  Изображение не получено. Keys: {list(message.keys())}", file=sys.stderr)
        sys.exit(1)

    # Сохраняем
    if image_url.startswith("data:"):
        header, b64data = image_url.split(",", 1)
        img_bytes = base64.b64decode(b64data)
        ext = "png" if "png" in header else "jpg"
    else:
        with urllib.request.urlopen(image_url, timeout=60) as r:
            img_bytes = r.read()
        ext = "png"

    filename = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-openrouter.{ext}"
    output_path = OUTPUT_DIR / filename
    output_path.write_bytes(img_bytes)

    size_kb = len(img_bytes) / 1024
    print(f"✅ Сохранено: {output_path} ({size_kb:.0f} KB)")

    # Resize
    final_path = str(output_path)
    if args.target:
        final_path = resize_image(final_path, args.target)

    print(f"PATH:{final_path}")


# ── 3. UNSPLASH (stock photos) ──────────────────────────────────────────────

def cmd_unsplash(args):
    """Поиск и скачивание фото с Unsplash."""
    # Unsplash позволяет hotlinking для демо, но лучше использовать API
    access_key = os.environ.get("UNSPLASH_ACCESS_KEY", "")

    orientation = args.orientation or "landscape"
    query = args.query

    if access_key:
        url = f"https://api.unsplash.com/search/photos?query={urllib.request.quote(query)}&per_page=1&orientation={orientation}"
        req = urllib.request.Request(url, headers={
            "Authorization": f"Client-ID {access_key}",
        })
    else:
        # Fallback: source.unsplash.com (без ключа, рандомное фото)
        size = "1280x720" if orientation == "landscape" else "794x1123"
        url = f"https://source.unsplash.com/{size}/?{urllib.request.quote(query)}"
        print(f"🔍 Unsplash (no API key, fallback): {query}")

        filename = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-unsplash.jpg"
        output_path = OUTPUT_DIR / filename
        try:
            urllib.request.urlretrieve(url, str(output_path))
            print(f"✅ Сохранено: {output_path}")
            print(f"PATH:{output_path}")
        except Exception as e:
            print(f"Ошибка: {e}", file=sys.stderr)
            sys.exit(1)
        return

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print(f"Ошибка Unsplash: {e}", file=sys.stderr)
        sys.exit(1)

    results = data.get("results", [])
    if not results:
        print(f"⚠️  Ничего не найдено по запросу '{query}'")
        sys.exit(1)

    photo = results[0]
    photo_url = photo["urls"]["regular"]  # 1080px wide
    author = photo["user"]["name"]

    filename = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-unsplash.jpg"
    output_path = OUTPUT_DIR / filename

    urllib.request.urlretrieve(photo_url, str(output_path))
    size_kb = output_path.stat().st_size / 1024
    print(f"✅ {output_path} ({size_kb:.0f} KB) — by {author}")

    # Resize
    final_path = str(output_path)
    if args.target:
        final_path = resize_image(final_path, args.target)

    print(f"PATH:{final_path}")


# ── 4. QR CODE ──────────────────────────────────────────────────────────────

def cmd_qr(args):
    """Генерация QR-кода как SVG (для inline в Marp)."""
    try:
        import qrcode
        import qrcode.image.svg
    except ImportError:
        print("Устанавливаю qrcode...", file=sys.stderr)
        subprocess.run([sys.executable, "-m", "pip", "install", "qrcode[pil]", "-q"])
        import qrcode
        import qrcode.image.svg

    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(args.data)
    qr.make(fit=True)

    if args.format == "svg":
        factory = qrcode.image.svg.SvgPathImage
        img = qr.make_image(image_factory=factory)
        filename = f"qr-{datetime.now().strftime('%H%M%S')}.svg"
        output_path = OUTPUT_DIR / filename
        img.save(str(output_path))
    else:
        img = qr.make_image(fill_color=args.color or "black", back_color=args.bg or "white")
        if args.size:
            img = img.resize((args.size, args.size))
        filename = f"qr-{datetime.now().strftime('%H%M%S')}.png"
        output_path = OUTPUT_DIR / filename
        img.save(str(output_path))

    size_kb = output_path.stat().st_size / 1024
    print(f"✅ QR: {output_path} ({size_kb:.1f} KB)")
    print(f"PATH:{output_path}")


# ── 5. REMOVE BACKGROUND ─────────────────────────────────────────────────────

def cmd_rembg(args):
    """Удаление фона с изображения (PNG с альфа-каналом)."""
    try:
        from rembg import remove
        from PIL import Image
    except ImportError:
        print("Устанавливаю rembg...", file=sys.stderr)
        subprocess.run([sys.executable, "-m", "pip", "install", "rembg[cpu]", "pillow", "-q", "--break-system-packages"])
        from rembg import remove
        from PIL import Image

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Ошибка: файл не найден: {input_path}", file=sys.stderr)
        sys.exit(1)

    print(f"🔄 Удаляю фон: {input_path}")

    with open(input_path, "rb") as f:
        input_data = f.read()

    # HF_HUB_OFFLINE чтобы не зависало
    os.environ["HF_HUB_OFFLINE"] = "1"

    output_data = remove(input_data)

    # Имя файла
    stem = input_path.stem
    filename = f"{stem}-nobg.png"
    output_path = OUTPUT_DIR / filename

    output_path.write_bytes(output_data)
    size_kb = len(output_data) / 1024
    print(f"✅ Без фона: {output_path} ({size_kb:.0f} KB)")

    # Resize если нужно
    if args.target:
        # Для прозрачных PNG resize через Pillow (ImageMagick может потерять alpha)
        img = Image.open(output_path)
        w, h = TARGETS[args.target]
        img.thumbnail((w, h), Image.LANCZOS)
        img.save(str(output_path), "PNG")
        print(f"📐 Resized: {img.size[0]}x{img.size[1]}")

    print(f"PATH:{output_path}")


# ── 6. RESIZE ───────────────────────────────────────────────────────────────

def resize_image(input_path, target):
    """Resize изображения под Marp target (16:9, a4, 4:3, 1:1)."""
    if target not in TARGETS:
        print(f"⚠️  Unknown target: {target}. Available: {list(TARGETS.keys())}")
        return input_path

    w, h = TARGETS[target]
    output_path = str(Path(input_path).with_suffix("")) + f"-{target}.png"

    try:
        subprocess.run([
            "convert", input_path,
            "-resize", f"{w}x{h}^",
            "-gravity", "center",
            "-extent", f"{w}x{h}",
            output_path,
        ], check=True, capture_output=True)
        print(f"📐 Resized: {w}x{h} → {output_path}")
        return output_path
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"⚠️  ImageMagick не установлен, resize пропущен", file=sys.stderr)
        return input_path


def cmd_resize(args):
    """Standalone resize."""
    result = resize_image(args.input, args.target)
    print(f"PATH:{result}")


# ── MAIN ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Marp Image — визуалы для презентаций")
    sub = parser.add_subparsers(dest="command")

    # grsai
    g = sub.add_parser("grsai", help="AI-генерация по тексту (дешёвый)")
    g.add_argument("--prompt", required=True)
    g.add_argument("--preset", choices=list(SLIDE_PRESETS.keys()) + list({"interior", "portrait", "logo", "social", "product", "art", "photo"}))
    g.add_argument("--aspect", choices=["1:1", "16:9", "9:16", "4:3", "3:4"])
    g.add_argument("--model", default="nano-banana-pro")
    g.add_argument("--ref", help="URL референсного изображения")
    g.add_argument("--target", choices=list(TARGETS.keys()), help="Resize под Marp")

    # openrouter
    o = sub.add_parser("openrouter", help="AI-генерация + vision + editing")
    o.add_argument("--prompt", required=True)
    o.add_argument("--model", default="gemini-image", help="gemini-image, gpt5-image, flux-pro, flux-klein, или full model ID")
    o.add_argument("--ref", help="Путь к референсному изображению (vision input)")
    o.add_argument("--aspect", help="Aspect ratio (16:9, 1:1, etc.)")
    o.add_argument("--target", choices=list(TARGETS.keys()), help="Resize под Marp")

    # unsplash
    u = sub.add_parser("unsplash", help="Стоковое фото по ключевому слову")
    u.add_argument("--query", required=True)
    u.add_argument("--orientation", choices=["landscape", "portrait", "squarish"], default="landscape")
    u.add_argument("--target", choices=list(TARGETS.keys()), help="Resize под Marp")

    # qr
    q = sub.add_parser("qr", help="QR-код для финального слайда")
    q.add_argument("--data", required=True, help="URL или текст для QR")
    q.add_argument("--format", choices=["svg", "png"], default="png")
    q.add_argument("--size", type=int, default=200, help="Размер в пикселях (для png)")
    q.add_argument("--color", default="black")
    q.add_argument("--bg", default="white")

    # rembg
    rb = sub.add_parser("rembg", help="Удалить фон (PNG с прозрачностью)")
    rb.add_argument("--input", required=True, help="Путь к изображению")
    rb.add_argument("--target", choices=list(TARGETS.keys()), help="Resize после удаления фона")

    # resize
    r = sub.add_parser("resize", help="Resize существующего изображения")
    r.add_argument("--input", required=True)
    r.add_argument("--target", required=True, choices=list(TARGETS.keys()))

    # presets
    sub.add_parser("presets", help="Показать пресеты для слайдов")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "grsai":
        cmd_grsai(args)
    elif args.command == "openrouter":
        cmd_openrouter(args)
    elif args.command == "unsplash":
        cmd_unsplash(args)
    elif args.command == "qr":
        cmd_qr(args)
    elif args.command == "rembg":
        cmd_rembg(args)
    elif args.command == "resize":
        cmd_resize(args)
    elif args.command == "presets":
        print("Пресеты для слайдов (--preset):\n")
        for name, cfg in SLIDE_PRESETS.items():
            print(f"  {name:15s} — {cfg['aspect']:5s} | {cfg['suffix'][:60]}...")
        print()


if __name__ == "__main__":
    main()
