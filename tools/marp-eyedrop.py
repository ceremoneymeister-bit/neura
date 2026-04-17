#!/usr/bin/env python3
"""
Marp Eyedrop — определяет доминантный цвет фона изображения.
Используется для seamless-слайдов: фон слайда = фон иллюстрации.

Использование:
    python3 marp-eyedrop.py image.png
    python3 marp-eyedrop.py image1.png image2.png image3.png
    python3 marp-eyedrop.py --css image.png  # выдаёт CSS-класс

Выход:
    image.png: #D6714D (RGB: 214, 113, 77)
"""

import sys
import argparse
from pathlib import Path

def get_bg_color(image_path: str, sample_size: int = 20) -> tuple:
    """Семплирует цвет фона из четырёх углов изображения."""
    from PIL import Image
    img = Image.open(image_path).convert('RGB')
    w, h = img.size

    pixels = []
    corners = [
        (0, 0, sample_size, sample_size),                    # top-left
        (w - sample_size, 0, w, sample_size),                # top-right
        (0, h - sample_size, sample_size, h),                # bottom-left
        (w - sample_size, h - sample_size, w, h),            # bottom-right
    ]

    for x1, y1, x2, y2 in corners:
        for x in range(max(0, x1), min(w, x2)):
            for y in range(max(0, y1), min(h, y2)):
                pixels.append(img.getpixel((x, y)))

    avg = tuple(sum(c) // len(pixels) for c in zip(*pixels))
    return avg


def rgb_to_hex(rgb: tuple) -> str:
    return f'#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}'


def generate_css_class(hex_color: str, class_name: str = 'custom-bg') -> str:
    """Генерирует scoped CSS-класс для Marp слайда."""
    return f"""section.{class_name} {{ background: {hex_color} !important; }}
section.{class_name} h2 {{ color: #fff; border-bottom-color: rgba(255,255,255,0.3) !important; }}
section.{class_name} h3 {{ color: rgba(255,255,255,0.7); }}
section.{class_name}, section.{class_name} li, section.{class_name} p, section.{class_name} td {{ color: rgba(255,255,255,0.9); }}
section.{class_name} strong {{ color: #fff; }}
section.{class_name} em {{ color: rgba(255,255,255,0.6); }}
section.{class_name} li::marker {{ color: #fff; }}
section.{class_name} div.callout {{ background: rgba(0,0,0,0.15) !important; }}
section.{class_name} div.badge {{ background: rgba(255,255,255,0.2) !important; color: #fff; }}
section.{class_name} div.window {{ background: rgba(0,0,0,0.2) !important; border-color: rgba(0,0,0,0.1) !important; }}
section.{class_name} div.window-bar {{ background: rgba(0,0,0,0.25) !important; }}
section.{class_name}::before {{ background: rgba(0,0,0,0.2) !important; }}"""


def main():
    parser = argparse.ArgumentParser(description='Определяет цвет фона изображений для Marp-слайдов')
    parser.add_argument('images', nargs='+', help='Путь к изображениям')
    parser.add_argument('--css', action='store_true', help='Вывести CSS-класс для Marp')
    parser.add_argument('--class-name', default='custom-bg', help='Имя CSS-класса (default: custom-bg)')
    parser.add_argument('--sample', type=int, default=20, help='Размер семпла в пикселях (default: 20)')
    args = parser.parse_args()

    colors = []
    for img_path in args.images:
        if not Path(img_path).exists():
            print(f'❌ {img_path}: файл не найден', file=sys.stderr)
            continue

        rgb = get_bg_color(img_path, args.sample)
        hex_color = rgb_to_hex(rgb)
        colors.append(hex_color)
        print(f'{Path(img_path).name}: {hex_color} (RGB: {rgb[0]}, {rgb[1]}, {rgb[2]})')

    if args.css and colors:
        # Используем средний цвет если несколько изображений
        if len(colors) > 1:
            rgbs = [tuple(int(c[i:i+2], 16) for i in (1, 3, 5)) for c in colors]
            avg = tuple(sum(c) // len(rgbs) for c in zip(*rgbs))
            hex_avg = rgb_to_hex(avg)
            print(f'\n📊 Средний цвет: {hex_avg}')
        else:
            hex_avg = colors[0]

        print(f'\n/* CSS-класс для Marp (вставить в <style>) */\n')
        print(generate_css_class(hex_avg, args.class_name))
        print(f'\n/* Использование: <!-- _class: {args.class_name} --> */')


if __name__ == '__main__':
    main()
