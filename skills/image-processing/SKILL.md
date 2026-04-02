---
name: image-processing
description: "Use when working with images — optimization, resizing, compression, format conversion, social media sizes, web images, 'оптимизируй картинку', 'размер для Instagram', alt-text, favicon"
---

# Image Processing — работа с изображениями

## Обзор
Правила обработки изображений: выбор формата, оптимизация для веба, размеры для соцсетей, сжатие, метаданные.

## 8 основных правил

### 1. Выбирай workflow по назначению
| Назначение | Формат | Качество | Макс. размер |
|-----------|--------|----------|-------------|
| Hero-баннер сайта | WebP/AVIF | 80-85% | < 200 KB |
| Контент-изображение | WebP | 75-80% | < 100 KB |
| Фото товара | JPEG/WebP | 85-90% | < 150 KB |
| Логотип/иконка | SVG/PNG | Lossless | < 50 KB |
| Скриншот UI | PNG | Lossless | < 500 KB |
| Favicon | ICO/PNG | Lossless | < 10 KB |
| OG-image (соцсети) | JPEG | 80% | < 300 KB |

### 2. Формат по типу контента
| Контент | Лучший формат | Fallback |
|---------|--------------|----------|
| Фотографии | WebP → AVIF | JPEG |
| Графика/иллюстрации | SVG | PNG |
| Скриншоты | PNG | WebP lossless |
| Анимация | WebP animated | GIF (тяжелее) |
| Прозрачность | PNG / WebP | — |
| Печать | TIFF / PNG | JPEG (300 DPI) |

### 3. Размеры для соцсетей

#### Instagram
| Тип | Размер (px) | Соотношение |
|-----|------------|-------------|
| Пост (квадрат) | 1080 × 1080 | 1:1 |
| Пост (портрет) | 1080 × 1350 | 4:5 |
| Пост (ландшафт) | 1080 × 566 | 1.91:1 |
| Stories/Reels | 1080 × 1920 | 9:16 |
| Аватар | 320 × 320 | 1:1 |
| Карусель | 1080 × 1080 | 1:1 |

#### Telegram
| Тип | Размер (px) |
|-----|------------|
| Пост в канале | 800-1280 по ширине |
| Стикер | 512 × 512 |
| Аватар бота | 640 × 640 |
| Inline preview | 300 × 200 |

#### VK
| Тип | Размер (px) |
|-----|------------|
| Пост | 1000 × 700 |
| Обложка сообщества | 1590 × 400 |
| Аватар | 200 × 200 |
| История | 1080 × 1920 |

#### YouTube
| Тип | Размер (px) |
|-----|------------|
| Обложка видео | 1280 × 720 |
| Баннер канала | 2560 × 1440 |

#### OG / Meta Tags
| Тип | Размер (px) |
|-----|------------|
| og:image | 1200 × 630 |
| Twitter Card | 1200 × 628 |

### 4. Порядок обработки
```
Resize → Crop → Compress → Strip metadata
```
Именно в таком порядке. Не сжимай до ресайза.

### 5. Метаданные
- **Для веба:** strip EXIF (`-strip` в ImageMagick)
- **Для печати:** сохраняй ICC-профиль и DPI
- **EXIF-ориентация:** всегда проверяй `Orientation` тег перед обработкой
```bash
# Проверить ориентацию
identify -verbose image.jpg | grep Orientation
# Автоповорот + strip
convert image.jpg -auto-orient -strip output.jpg
```

### 6. Бюджеты размеров
| Категория | Макс. вес |
|-----------|----------|
| Hero (above fold) | 200 KB |
| Контентное фото | 100 KB |
| Превью/thumbnail | 30 KB |
| Иконка/лого | 50 KB |
| OG-image | 300 KB |

### 7. Инструменты

#### ImageMagick (CLI)
```bash
# Ресайз с сохранением пропорций
convert input.jpg -resize 1200x -quality 82 -strip output.webp

# Batch-конвертация в WebP
for f in *.jpg; do convert "$f" -resize 1200x -quality 80 "${f%.jpg}.webp"; done

# Создание favicon
convert logo.png -resize 32x32 favicon.ico

# Создание OG-image (1200x630)
convert input.jpg -resize 1200x630^ -gravity center -extent 1200x630 -quality 85 og-image.jpg

# Оптимизация PNG
pngquant --quality=65-80 --output optimized.png input.png
```

#### Pillow (Python)
```python
from PIL import Image

# Ресайз
img = Image.open('input.jpg')
img.thumbnail((1200, 1200), Image.LANCZOS)
img.save('output.webp', 'WebP', quality=80)

# Кроп центральный
width, height = img.size
new_size = min(width, height)
left = (width - new_size) // 2
top = (height - new_size) // 2
img.crop((left, top, left + new_size, top + new_size)).save('square.jpg')

# Strip EXIF
from PIL.ExifTags import Base
img_clean = Image.new(img.mode, img.size)
img_clean.putdata(list(img.getdata()))
img_clean.save('clean.jpg')

# Batch resize
from pathlib import Path
for p in Path('.').glob('*.jpg'):
    img = Image.open(p)
    img.thumbnail((1080, 1080))
    img.save(f'optimized/{p.stem}.webp', 'WebP', quality=80)
```

### 8. Web-оптимизация
- **LCP (Largest Contentful Paint):** hero-image < 200KB, preload в `<head>`
- **CLS (Cumulative Layout Shift):** всегда указывай width/height в HTML
- **Lazy loading:** `loading="lazy"` для below-fold изображений
- **Responsive:** `srcset` + `sizes` для разных экранов
```html
<img
  src="photo-800.webp"
  srcset="photo-400.webp 400w, photo-800.webp 800w, photo-1200.webp 1200w"
  sizes="(max-width: 600px) 400px, (max-width: 1024px) 800px, 1200px"
  width="800" height="600"
  loading="lazy"
  alt="Описание изображения"
>
```

## Accessibility
- **Alt-text:** описывай содержание, не файл. "Команда обсуждает проект" не "IMG_4521.jpg"
- **Декоративные:** `alt=""` (пустой alt, не отсутствующий)
- **Текст в изображениях:** дублируй в HTML (невидим для скринридеров)
- **Контраст:** текст поверх фото → overlay или text-shadow

## Частые ошибки
| Ошибка | Решение |
|--------|---------|
| Фото 5MB на сайте | Resize + compress + WebP |
| PNG для фотографий | JPEG/WebP (PNG для графики) |
| Нет alt-text | Всегда описывай содержание |
| GIF 10MB | WebP animated или MP4 |
| Игнор EXIF orientation | `convert -auto-orient` перед обработкой |
| Ресайз после сжатия | Порядок: resize → crop → compress |

## Интеграция с ботами
```
[FILE:/tmp/optimized-image.webp]
```
