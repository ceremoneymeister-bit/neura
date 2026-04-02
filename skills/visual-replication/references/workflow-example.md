# Workflow Example — Visual Replication

## Сценарий

Пользователь прислал скриншот лендинга и просит воспроизвести в React + Tailwind.

## Phase 1 — Extract

### 1.1 Read tool (мультимодальный)

Смотрим на изображение, описываем:
> Тёмный лендинг, минималистичный. Hero с большим заголовком слева, абстрактное 3D-изображение справа. 
> Ниже — 3 карточки в ряд с иконками. CTA-кнопка с градиентом фиолетовый→синий.
> Скруглённые карточки (lg), мягкие тени.

### 1.2 visual-analyzer.py

```bash
python3 scripts/visual-analyzer.py reference.png
```

Выход:
```
🎨 Палитра:
   #0f0f14  ████████ 42.3%  (background-dark)
   #1a1a24  ███     15.1%  (primary)
   #8b5cf6  ██      8.7%   (accent)
   #e2e8f0  ██      7.2%   (text-light)
   #3b82f6  █       4.5%   (accent)
   #64748b  █       3.8%   (text-dark)

🎯 CSS-переменные:
   --bg: #0f0f14;
   --text: #e2e8f0;
   --accent: #8b5cf6;

💨 Tailwind:
   bg: bg-[#0f0f14]
   text: text-[#e2e8f0]
   accent: bg-[#8b5cf6]

📐 Layout: 1440×900px (landscape-wide)
   Колонки: 2
   Spacing: comfortable (avg gap 4.8%)
```

### 1.3 Бриф

```
Стиль: dark minimalist, мягкие тени, скруглённые углы
Палитра: bg=#0f0f14, text=#e2e8f0, accent=#8b5cf6 (purple), secondary=#3b82f6 (blue)
Layout: hero 2-col → cards 3-col, comfortable spacing
Шрифт: крупный заголовок (~48-56px), body (~16px), semi-bold headers
Ключевые: gradient CTA button (purple→blue), 3D illustration, card shadows
```

## Phase 2 — Implement

Создаём компоненты с Tailwind-классами, используя ТОЛЬКО цвета из анализа.

## Phase 3 — Verify

```bash
# Скриншот viewport=1440x900
python3 scripts/visual-analyzer.py reference.png /tmp/result.png --compare

# Выход:
# Сходство: 87.3% (good)
# Значительные отличия: 12.7% пикселей
```

87% > 85% → приемлемо. Визуальная инспекция подтверждает: палитра совпала, spacing немного отличается в footer.

## Phase 4 — Done

Показываем пользователю оба скриншота для финального подтверждения.
