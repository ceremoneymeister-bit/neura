# Visual / Design Checklist

## Scoring: 0-100 (12 categories)

### 1. Visual Hierarchy (10 pts)
- [ ] Squint test: заголовок + CTA различимы за 3 секунды
- [ ] ≤4 визуальных блока на один viewport
- [ ] Z-pattern: logo→trust→visual→CTA
- [ ] Заголовок ≥2x размер body текста

### 2. Above the Fold (10 pts)
- [ ] 7 элементов: headline, subheadline, CTA, visual, trust signal, value prop, mobile-first
- [ ] CTA видна без скролла на mobile (375px)
- [ ] Hero image показывает результат/продукт, не stock photo

### 3. Typography (10 pts)
- [ ] Body text ≥16px (mobile и desktop)
- [ ] Line-height 1.5-1.7 (body), 1.1-1.3 (headings)
- [ ] Длина строки 45-90 символов (идеал 66-80)
- [ ] ≤3 font families на странице
- [ ] Left-aligned body text (не justified)
- [ ] H1: 28-32px (mobile), 40-52px (desktop)

### 4. Color & Contrast (10 pts)
- [ ] Текст vs фон ≥4.5:1 (WCAG AA)
- [ ] Крупный текст (≥18px) ≥3:1
- [ ] CTA кнопка — самый контрастный элемент
- [ ] 2-3 основных цвета + нейтральные
- [ ] Цвет не единственный индикатор смысла

### 5. Spacing (8 pts)
- [ ] 8px grid rhythm (8, 16, 24, 32, 48, 64, 80px)
- [ ] Side padding ≥16px (mobile), ≥24px (desktop)
- [ ] Отступы вокруг CTA 40-60px
- [ ] Связанные элементы ближе друг к другу (Gestalt proximity)
- [ ] Секции разделены ≥48px вертикально

### 6. CTA Button Design (10 pts)
- [ ] Tap target ≥48×48px (рекомендуется 60×60px)
- [ ] Height ≥44px, padding 16-20px vertical
- [ ] Button text ≥16px
- [ ] В зоне большого пальца на mobile (нижняя 1/3 или центр)
- [ ] 4 состояния: default, hover, active, disabled
- [ ] Кнопка формы (не текстовая ссылка) — +45% кликов

### 7. Mobile Responsiveness (10 pts)
- [ ] Нет horizontal scroll на любом breakpoint
- [ ] Текст читаем без зума
- [ ] Touch targets ≥48px с ≥8px spacing
- [ ] Hero image адаптирован к portrait (не обрезается критично)
- [ ] Форма ≤5 полей
- [ ] Numeric keyboard для телефона, email keyboard для email

### 8. Animation & Motion (8 pts)
- [ ] Все анимации ≤700ms
- [ ] Только transform + opacity (GPU-ускорение)
- [ ] prefers-reduced-motion учтён
- [ ] Нет бесконечных loop-анимаций на интерактивных элементах
- [ ] Нет flash/blink >3 раз/сек
- [ ] Каждая анимация = feedback, orientation или delight (не декор)

### 9. Performance Impact (8 pts)
- [ ] LCP ≤2.5s
- [ ] CLS ≤0.1 (все img/video с explicit width/height)
- [ ] Total page weight ≤2MB
- [ ] Images lazy-loaded below fold

### 10. Visual Consistency (6 pts)
- [ ] Одна icon library (не mixed outline + filled)
- [ ] Единый border-radius для всех карточек
- [ ] Единая shadow system (sm/md/lg)
- [ ] Heading hierarchy: H1 > H2 > H3 визуально нисходящие

### 11. Image Quality (5 pts)
- [ ] ≥80% изображений в WebP/AVIF
- [ ] Alt-text на всех информационных изображениях
- [ ] Единый стиль обработки фото (radius, filter, aspect ratio)

### 12. Layout (5 pts)
- [ ] Max content width 960-1140px (landing), 640-760px (long-form)
- [ ] Single-column на mobile, ≤3 columns на desktop
- [ ] Нет пустых/сломанных секций
