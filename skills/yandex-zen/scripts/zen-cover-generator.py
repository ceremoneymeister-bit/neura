#!/usr/bin/env python3
"""
Zen Cover Generator -- creates cover images for Yandex Dzen articles.

Generates 1920x1080 (16:9) cover images with title text overlay.
Two styles: gradient background or solid color background.

Usage:
    python3 zen-cover-generator.py --title "10 способов заработать на Дзене" --output /tmp/cover.jpg
    python3 zen-cover-generator.py --title "Длинный заголовок" --style solid --color "#1a1a2e" --output cover.jpg
    python3 zen-cover-generator.py --title "Тест" --style gradient --font-size 90 --output /tmp/test.jpg

Requirements:
    pip install Pillow
"""

import argparse
import os
import sys
import textwrap

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print(
        "[ERROR] Pillow is required. Install it with: pip install Pillow",
        file=sys.stderr,
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
WIDTH = 1920
HEIGHT = 1080

# Safe zone for 4:3 crop (centered) -- key content must fit here
SAFE_ZONE_W = 1440
SAFE_ZONE_H = 1080
SAFE_LEFT = (WIDTH - SAFE_ZONE_W) // 2   # 240
SAFE_RIGHT = SAFE_LEFT + SAFE_ZONE_W      # 1680

# Text area with padding inside safe zone
TEXT_PADDING = 80
TEXT_LEFT = SAFE_LEFT + TEXT_PADDING
TEXT_RIGHT = SAFE_RIGHT - TEXT_PADDING
TEXT_MAX_WIDTH = TEXT_RIGHT - TEXT_LEFT  # ~1280 px

# Font search paths (common Linux locations)
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/usr/share/fonts/truetype/ubuntu/Ubuntu-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
]

DEFAULT_FONT_SIZE = 80
MAX_LINES = 2
JPEG_QUALITY = 90

# Gradient presets
GRADIENT_PRESETS = {
    "blue":   ("#0f0c29", "#302b63", "#24243e"),
    "sunset": ("#2b1055", "#d53369", "#daae51"),
    "ocean":  ("#0f2027", "#203a43", "#2c5364"),
    "forest": ("#0b3d0b", "#1a5c1a", "#2d8c2d"),
    "fire":   ("#1a0000", "#8b0000", "#ff4500"),
    "purple": ("#1a002e", "#4a0080", "#7b2fbe"),
    "dark":   ("#0d0d0d", "#1a1a2e", "#16213e"),
}
DEFAULT_GRADIENT = "dark"


def find_font(preferred_size: int) -> ImageFont.FreeTypeFont:
    """Find an available TrueType font on the system."""
    for path in FONT_CANDIDATES:
        if os.path.isfile(path):
            try:
                return ImageFont.truetype(path, preferred_size)
            except Exception:
                continue
    # Fallback to default (bitmap, limited but works)
    print("[WARN] No TrueType font found, using default bitmap font.", file=sys.stderr)
    return ImageFont.load_default()


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert #RRGGBB to (R, G, B) tuple."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        raise ValueError(f"Invalid hex color: #{hex_color}")
    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16),
    )


def interpolate_color(
    c1: tuple[int, int, int],
    c2: tuple[int, int, int],
    t: float,
) -> tuple[int, int, int]:
    """Linearly interpolate between two RGB colors. t in [0, 1]."""
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


def create_gradient_background(
    width: int,
    height: int,
    color_hex: str | None = None,
) -> Image.Image:
    """Create a vertical gradient background image."""
    if color_hex:
        base = hex_to_rgb(color_hex)
        # Create gradient from dark version to the color to lighter version
        dark = (max(0, base[0] - 60), max(0, base[1] - 60), max(0, base[2] - 60))
        light = (min(255, base[0] + 30), min(255, base[1] + 30), min(255, base[2] + 30))
        colors = (dark, base, light)
    else:
        preset = GRADIENT_PRESETS[DEFAULT_GRADIENT]
        colors = tuple(hex_to_rgb(c) for c in preset)

    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    c1, c2, c3 = colors[0], colors[1], colors[2]

    for y in range(height):
        t = y / height
        if t < 0.5:
            color = interpolate_color(c1, c2, t * 2)
        else:
            color = interpolate_color(c2, c3, (t - 0.5) * 2)
        draw.line([(0, y), (width, y)], fill=color)

    return img


def create_solid_background(
    width: int,
    height: int,
    color_hex: str | None = None,
) -> Image.Image:
    """Create a solid color background with subtle vignette effect."""
    base_hex = color_hex or "#1a1a2e"
    base_rgb = hex_to_rgb(base_hex)
    img = Image.new("RGB", (width, height), base_rgb)
    return img


def wrap_title(
    title: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
    max_lines: int = MAX_LINES,
) -> list[str]:
    """Word-wrap title text to fit within max_width, limited to max_lines."""
    words = title.split()
    lines = []
    current = ""

    for word in words:
        test = f"{current} {word}".strip() if current else word
        bbox = font.getbbox(test)
        text_width = bbox[2] - bbox[0]

        if text_width <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word

            # Check if single word exceeds width
            bbox = font.getbbox(word)
            if bbox[2] - bbox[0] > max_width:
                # Truncate with ellipsis
                while len(word) > 1:
                    word = word[:-1]
                    bbox = font.getbbox(word + "...")
                    if bbox[2] - bbox[0] <= max_width:
                        break
                current = word + "..."

    if current:
        lines.append(current)

    # Limit to max_lines
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        # Add ellipsis to last line if truncated
        last = lines[-1]
        bbox = font.getbbox(last + "...")
        if bbox[2] - bbox[0] <= max_width:
            lines[-1] = last + "..."
        else:
            while len(last) > 1:
                last = last[:-1]
                bbox = font.getbbox(last + "...")
                if bbox[2] - bbox[0] <= max_width:
                    break
            lines[-1] = last + "..."

    return lines if lines else [title[:30] + "..."]


def draw_text_with_shadow(
    draw: ImageDraw.Draw,
    position: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int] = (255, 255, 255),
    shadow_offset: int = 3,
    shadow_color: tuple[int, int, int, int] = (0, 0, 0, 180),
):
    """Draw text with a drop shadow for readability."""
    x, y = position
    # Shadow
    draw.text((x + shadow_offset, y + shadow_offset), text, fill=shadow_color, font=font)
    # Main text
    draw.text((x, y), text, fill=fill, font=font)


def generate_cover(
    title: str,
    output_path: str,
    style: str = "gradient",
    color: str | None = None,
    font_size: int = DEFAULT_FONT_SIZE,
) -> str:
    """
    Generate a cover image for a Dzen article.

    Args:
        title: Title text to display on the cover
        output_path: Path to save the output JPEG
        style: "gradient" or "solid"
        color: Optional hex color (e.g. "#1a1a2e")
        font_size: Font size in pixels

    Returns:
        Path to the generated image file.
    """
    # Create background
    if style == "gradient":
        img = create_gradient_background(WIDTH, HEIGHT, color)
    else:
        img = create_solid_background(WIDTH, HEIGHT, color)

    draw = ImageDraw.Draw(img)
    font = find_font(font_size)

    # Wrap title
    lines = wrap_title(title, font, TEXT_MAX_WIDTH)

    # Calculate vertical position (center in safe zone)
    line_heights = []
    for line in lines:
        bbox = font.getbbox(line)
        line_heights.append(bbox[3] - bbox[1])

    total_text_height = sum(line_heights) + (len(lines) - 1) * 20  # 20px line gap
    start_y = (HEIGHT - total_text_height) // 2

    # Draw each line (centered horizontally within safe zone)
    y = start_y
    for i, line in enumerate(lines):
        bbox = font.getbbox(line)
        line_width = bbox[2] - bbox[0]
        x = SAFE_LEFT + (SAFE_ZONE_W - line_width) // 2

        draw_text_with_shadow(draw, (x, y), line, font)
        y += line_heights[i] + 20

    # Add subtle bottom bar (decorative)
    bar_y = HEIGHT - 60
    bar_color = (255, 255, 255, 40)
    draw.rectangle(
        [(SAFE_LEFT + 200, bar_y), (SAFE_RIGHT - 200, bar_y + 2)],
        fill=bar_color,
    )

    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # Save as JPEG
    if img.mode == "RGBA":
        img = img.convert("RGB")
    img.save(output_path, "JPEG", quality=JPEG_QUALITY)

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Generate cover images for Yandex Dzen articles (1920x1080, 16:9).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python3 zen-cover-generator.py --title "10 способов заработать на Дзене" --output /tmp/cover.jpg
  python3 zen-cover-generator.py --title "AI в 2026" --style solid --color "#1a1a2e"
  python3 zen-cover-generator.py --title "Длинный заголовок статьи" --style gradient --font-size 90

Gradient presets: blue, sunset, ocean, forest, fire, purple, dark (default)
""",
    )
    parser.add_argument(
        "--title", "-t",
        required=True,
        help="Title text to display on the cover",
    )
    parser.add_argument(
        "--output", "-o",
        default="/tmp/zen_cover.jpg",
        help="Output file path (default: /tmp/zen_cover.jpg)",
    )
    parser.add_argument(
        "--style", "-s",
        choices=["gradient", "solid"],
        default="gradient",
        help="Background style: gradient (default) or solid",
    )
    parser.add_argument(
        "--color", "-c",
        default=None,
        help='Base color as hex (e.g. "#1a1a2e"). For gradient, derives shades automatically.',
    )
    parser.add_argument(
        "--font-size",
        type=int,
        default=DEFAULT_FONT_SIZE,
        help=f"Font size in pixels (default: {DEFAULT_FONT_SIZE})",
    )
    args = parser.parse_args()

    result = generate_cover(
        title=args.title,
        output_path=args.output,
        style=args.style,
        color=args.color,
        font_size=args.font_size,
    )

    print(f"[OK] Cover generated: {result}")
    print(f"     Size: {WIDTH}x{HEIGHT} px (16:9)")
    print(f"     Style: {args.style}")
    if args.color:
        print(f"     Color: {args.color}")
    print(f"     Quality: JPEG {JPEG_QUALITY}%")


if __name__ == "__main__":
    main()
