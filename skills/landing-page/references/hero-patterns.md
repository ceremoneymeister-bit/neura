# Hero Block Patterns — проверенные паттерны (из проекта Neura/ceremoneymeister)

## Архитектура dark hero с canvas-анимацией

### Структура файлов
```
components/agents/
├── AgentsHero.jsx          # Hero-блок: layout, GSAP анимации, модалка
├── hero-variants/
│   ├── SphereProCanvas.jsx # Финальный: 3D сфера + кольца + созвездия + пульс
│   ├── NeuralCanvas.jsx    # Вариант: нейросеть с сигналами
│   ├── FluidCanvas.jsx     # Вариант: градиентные блобы
│   ├── WaveCanvas.jsx      # Вариант: многослойные волны
│   └── OrbitCanvas.jsx     # Вариант: орбитальные кольца
├── MagneticButton.jsx      # Кнопка с magnetic-эффектом
└── ConsultationModal.jsx   # Форма заявки → TG уведомление
```

### Split-layout (текст слева, анимация справа)
```jsx
<section className="min-h-screen relative overflow-hidden bg-[#08080F]">
    {/* Canvas: right side desktop, subtle bg mobile */}
    <div className="absolute inset-0 lg:left-[35%] pointer-events-none">
        <SphereProCanvas dark />
    </div>

    {/* Text: left aligned desktop, centered mobile */}
    <div className="relative z-10 min-h-screen flex flex-col justify-center
                    px-6 lg:pl-20 lg:pr-8 lg:max-w-[52%]">
        <h1>...</h1>
        <p>...</p>
        <buttons />
    </div>
</section>
```

### GSAP char-by-char headline animation
**Ключевое правило: НЕ парсить innerHTML. Текст — из константы.**

```javascript
const HEADLINE = [
    { text: 'Один агент', accent: true },
    { text: 'вместо отдела', accent: false },
];

// В useEffect:
headline.innerHTML = '';
HEADLINE.forEach(({ text, accent }) => {
    const lineDiv = document.createElement('div');
    text.split('').forEach(char => {
        const span = document.createElement('span');
        span.textContent = char;
        span.style.display = 'inline-block';
        span.className = accent ? 'hero-char hero-accent' : 'hero-char';
        if (char === ' ') span.style.width = '0.3em';
        lineDiv.appendChild(span);
    });
    headline.appendChild(lineDiv);
});
```

### GSAP word-by-word subtitle animation
**Ключевое правило: вставлять `\u00A0` (неразрывный пробел) между словами, НЕ marginRight.**

```javascript
const words = text.split(' ').filter(w => w);
words.forEach((word, i) => {
    const span = document.createElement('span');
    span.textContent = word;
    span.style.display = 'inline-block';
    sub.appendChild(span);
    if (i < words.length - 1) {
        sub.appendChild(document.createTextNode('\u00A0'));
    }
});
```

### Accent text styling (вместо rainbow gradient)
```css
.hero-accent {
    color: #C4B5FD;
    text-shadow: 0 0 40px rgba(139, 92, 246, 0.25);
}
```
Лучше rainbow-градиента: чище, премиальнее, читабельнее на тёмном фоне.

### Scroll parallax
```javascript
ScrollTrigger.create({
    trigger: section,
    start: 'top top',
    end: 'bottom top',
    scrub: true,
    onUpdate: (self) => {
        const p = self.progress;
        gsap.set(sphereRef.current, { scale: 1 - p * 0.2, opacity: 1 - p * 1.2 });
        gsap.set(headline, { y: -p * 100, opacity: 1 - p * 1.5 });
    },
});
```

---

## Canvas-анимации: паттерны реализации

### Общий skeleton для canvas-компонента
```jsx
export default function MyCanvas({ dark = false }) {
    const canvasRef = useRef(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const dpr = window.devicePixelRatio || 1;

        const resize = () => {
            canvas.width = canvas.offsetWidth * dpr;
            canvas.height = canvas.offsetHeight * dpr;
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        };
        resize();
        window.addEventListener('resize', resize);

        // Mouse tracking with smooth lerp
        const m = { x: 0, y: 0, sx: 0, sy: 0 };
        const onMM = (e) => {
            m.x = (e.clientX / window.innerWidth - 0.5) * 2;
            m.y = (e.clientY / window.innerHeight - 0.5) * 2;
        };
        window.addEventListener('mousemove', onMM);

        let raf;
        function frame() {
            m.sx += (m.x - m.sx) * 0.04; // lerp smoothing
            m.sy += (m.y - m.sy) * 0.04;
            // ... render ...
            raf = requestAnimationFrame(frame);
        }
        frame();

        return () => {
            cancelAnimationFrame(raf);
            window.removeEventListener('resize', resize);
            window.removeEventListener('mousemove', onMM);
        };
    }, [dark]);

    return <canvas ref={canvasRef} className="absolute inset-0 w-full h-full" />;
}
```

### Dark mode prop
Использовать brightness multiplier:
```javascript
const B = dark ? 2.8 : 1;
// Применять: `rgba(99,102,241,${Math.min(1, 0.05 * B).toFixed(3)})`
```

### Fibonacci sphere (оптимальное распределение точек)
```javascript
const N = 500;
const PHI = Math.PI * (3 - Math.sqrt(5));
const points = [];
for (let i = 0; i < N; i++) {
    const y = 1 - (i / (N - 1)) * 2;
    const r = Math.sqrt(Math.max(0, 1 - y * y));
    const th = PHI * i;
    points.push({ x: Math.cos(th) * r, y, z: Math.sin(th) * r });
}
```

### Pre-compute connections (для constellation эффекта)
```javascript
const CONN_DIST = 0.36;
const conns = [];
for (let i = 0; i < N; i++) {
    for (let j = i + 1; j < N; j++) {
        const d = Math.hypot(pts[i].x-pts[j].x, pts[i].y-pts[j].y, pts[i].z-pts[j].z);
        if (d < CONN_DIST) conns.push({ a: i, b: j, d });
    }
}
// Render: пропускать connections с minDepth < -0.25
```

### Depth normalization (баг-фикс для orbits)
**Всегда нормализовать z-координаты перед использованием:**
```javascript
const maxZ = Math.max(radius * Math.abs(sinTilt), 0.001);
const depth = Math.max(0, Math.min(1, (z / maxZ + 1) / 2));
// Без этого: createRadialGradient получит отрицательный радиус → crash
```

---

## Consultation Form → TG notification

### Frontend (ConsultationModal.jsx)
- Модалка с blur-backdrop на тёмном фоне
- Поля: имя (required), контакт (required), описание бизнеса (optional)
- POST на API: `http://<server>:8899/consultation`
- Fallback при ошибке: "Напишите в Telegram: @username"

### Backend (consultation-api.py)
- Python stdlib HTTP server на порте 8899
- CORS headers для cross-origin запросов
- Отправка через Telegram Bot API → личка + HQ-группа
- systemd service: `consultation-api.service`

---

## Bento-grid для секции "features" (после hero)

### Паттерн: 1 крупная карточка + 2 меньших стакнутых
```jsx
<div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
    {/* Large card */}
    <div className="bg-[#F5F5F7] rounded-3xl p-10 md:p-12 min-h-[420px]">
        <Icon /><h3 /><p /><example-box />
    </div>
    {/* Two stacked */}
    <div className="flex flex-col gap-5">
        <div className="bg-[#F5F5F7] rounded-3xl p-8 md:p-10 flex-1">...</div>
        <div className="bg-[#F5F5F7] rounded-3xl p-8 md:p-10 flex-1">...</div>
    </div>
</div>
```

Визуально сильнее, чем 4 одинаковых карточки. Крупный блок привлекает внимание к главному преимуществу.

---

## Checklist для hero-блока

- [ ] Заголовок ≤ 8 слов, понятен за 3 секунды
- [ ] Подзаголовок — конкретика, не абстракция
- [ ] Accent — одноцветный glow, не rainbow gradient
- [ ] CTA primary — действие с продуктом (Тест-драйв)
- [ ] CTA secondary — мягкий (Получить консультацию)
- [ ] Badge — НЕ дублирует подзаголовок
- [ ] Анимация не мешает чтению текста
- [ ] Mobile: текст по центру, анимация за текстом (opacity: 0.3)
- [ ] GSAP headline из константы, не из innerHTML
- [ ] Subtitle spaces через `\u00A0`, не marginRight
