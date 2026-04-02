# Technical Thresholds

## Core Web Vitals (Google ranking signals)

| Метрика | Good | Needs Improvement | Poor |
|---------|------|-------------------|------|
| LCP (Largest Contentful Paint) | ≤2.5s | 2.5-4.0s | >4.0s |
| CLS (Cumulative Layout Shift) | ≤0.1 | 0.1-0.25 | >0.25 |
| INP (Interaction to Next Paint) | ≤200ms | 200-500ms | >500ms |
| FCP (First Contentful Paint) | ≤1.8s | 1.8-3.0s | >3.0s |
| TTFB (Time to First Byte) | ≤600ms | 600-1500ms | >1500ms |

## Lighthouse Score Bands

| Score | Rating |
|-------|--------|
| 90-100 | Good (green) |
| 50-89 | Needs Improvement (orange) |
| 0-49 | Poor (red) |

## Performance Budget

| Ресурс | Порог |
|--------|-------|
| Total page weight | ≤2MB (2048KB) |
| JS bundle (gzip) | ≤300KB |
| CSS (gzip) | ≤100KB |
| Images total | ≤1MB |
| Font files | ≤3 файла, ≤200KB total |
| HTTP requests | ≤50 |
| Third-party scripts | ≤5 |

## Image Formats

| Формат | Когда |
|--------|-------|
| WebP | Фото, сложная графика (25-50% меньше JPEG) |
| AVIF | Фото (ещё меньше WebP, но медленнее кодируется) |
| SVG | Иконки, логотипы, простая графика |
| PNG | Скриншоты, изображения с текстом |

**Цель:** ≥80% изображений в next-gen форматах (WebP/AVIF)

## Video Performance

| Правило | Значение |
|---------|----------|
| Background video codec | H.264 Main profile |
| Background video FPS | 30fps (не 60) |
| Background video preload | poster + preload="none" для lazy |
| Video в React | React.memo() для изоляции от re-renders |
| Autoplay | muted + playsinline обязательны |

## SEO Technical

| Элемент | Требование |
|---------|-----------|
| Title tag | ≤60 символов, ключевое слово в начале |
| Meta description | ≤160 символов, содержит CTA |
| H1 | Ровно 1 на странице |
| OG tags | og:title, og:description, og:image обязательны |
| JSON-LD | Schema.org: Product, Course, Organization (по контексту) |
| Canonical | Указан, корректный |
| robots.txt | Доступен, не блокирует индексацию |
| Alt text | На всех информационных изображениях |
| Mobile viewport | `<meta name="viewport" content="width=device-width, initial-scale=1">` |
