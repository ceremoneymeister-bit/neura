#!/usr/bin/env python3
"""
Marp SVG — генерация SVG-диаграмм для вставки в Marp-презентации.

Использование:
  python3 marp-svg.py bar --data '{"Продажи": 85, "Маркетинг": 60, "Сервис": 92}' --color "#D97757"
  python3 marp-svg.py pie --data '{"Россия": 45, "СНГ": 30, "Европа": 25}' --colors "#D97757,#3b82f6,#8C8C8C"
  python3 marp-svg.py progress --value 73 --label "Прогресс" --color "#4CAF50"
  python3 marp-svg.py timeline --data '["Аудит", "Настройка", "Запуск", "Оптимизация"]' --active 2
  python3 marp-svg.py metric --value "+47%" --label "Рост аудитории" --color "#D97757"
  python3 marp-svg.py icons --names "rocket,chart,users,shield"

Все команды выводят SVG в stdout (для inline в markdown) или сохраняют в файл (--output).
"""

import argparse
import json
import sys
from pathlib import Path

# === Палитры ===
PALETTES = {
    "claude": ["#D97757", "#B8603F", "#8C8C8C", "#E8E5DE", "#1A1A1A"],
    "blue": ["#3b82f6", "#1a56db", "#60a5fa", "#93c5fd", "#1e3a5f"],
    "dark": ["#58a6ff", "#a78bfa", "#f97316", "#22d3ee", "#c9d1d9"],
    "gradient": ["#667eea", "#764ba2", "#f093fb", "#4facfe", "#fbc2eb"],
    "minimal": ["#444444", "#888888", "#cccccc", "#e0e0e0", "#1a1a1a"],
    "green": ["#22c55e", "#16a34a", "#86efac", "#bbf7d0", "#166534"],
}

DEFAULT_COLORS = PALETTES["claude"]


# ── BAR CHART ────────────────────────────────────────────────────────────────

def svg_bar(data: dict, colors=None, width=600, height=300, bar_width=60):
    """Горизонтальный bar chart."""
    if not colors:
        colors = DEFAULT_COLORS
    if isinstance(colors, str):
        colors = colors.split(",")

    items = list(data.items())
    max_val = max(data.values()) or 1
    bar_h = min(36, (height - 40) // len(items) - 8)
    y_start = 10

    bars = []
    for i, (label, value) in enumerate(items):
        y = y_start + i * (bar_h + 12)
        w = int((value / max_val) * (width - 180))
        color = colors[i % len(colors)]
        bars.append(f'''  <text x="0" y="{y + bar_h//2 + 5}" font-size="13" fill="#666" font-family="Inter, system-ui, sans-serif">{label}</text>
  <rect x="130" y="{y}" width="{w}" height="{bar_h}" rx="4" fill="{color}" opacity="0.85"/>
  <text x="{135 + w}" y="{y + bar_h//2 + 5}" font-size="12" fill="#333" font-family="Inter, system-ui, sans-serif" font-weight="600">{value}</text>''')

    total_h = y_start + len(items) * (bar_h + 12) + 10
    return f'<svg viewBox="0 0 {width} {total_h}" xmlns="http://www.w3.org/2000/svg">\n' + "\n".join(bars) + "\n</svg>"


# ── PIE CHART ────────────────────────────────────────────────────────────────

def svg_pie(data: dict, colors=None, size=250):
    """Donut/pie chart через stroke-dasharray."""
    if not colors:
        colors = DEFAULT_COLORS
    if isinstance(colors, str):
        colors = colors.split(",")

    total = sum(data.values()) or 1
    r = 80
    cx, cy = size // 2, size // 2
    circumference = 2 * 3.14159 * r
    offset = 0

    segments = []
    legend = []
    for i, (label, value) in enumerate(data.items()):
        pct = value / total
        dash = pct * circumference
        gap = circumference - dash
        color = colors[i % len(colors)]

        segments.append(
            f'  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="35" '
            f'stroke-dasharray="{dash:.1f} {gap:.1f}" stroke-dashoffset="{-offset:.1f}" '
            f'transform="rotate(-90 {cx} {cy})"/>'
        )
        offset += dash

        lx = size + 15
        ly = 30 + i * 24
        legend.append(
            f'  <rect x="{lx}" y="{ly - 10}" width="14" height="14" rx="3" fill="{color}"/>'
            f'  <text x="{lx + 20}" y="{ly + 1}" font-size="12" fill="#333" font-family="Inter, system-ui, sans-serif">{label} ({value}%)</text>'
        )

    total_w = size + 160
    return (f'<svg viewBox="0 0 {total_w} {size}" xmlns="http://www.w3.org/2000/svg">\n'
            + "\n".join(segments) + "\n" + "\n".join(legend) + "\n</svg>")


# ── PROGRESS BAR ─────────────────────────────────────────────────────────────

def svg_progress(value: int, label="", color="#D97757", width=500):
    """Прогресс-бар с процентом."""
    fill_w = int((value / 100) * (width - 20))
    return f'''<svg viewBox="0 0 {width} 50" xmlns="http://www.w3.org/2000/svg">
  <text x="0" y="15" font-size="13" fill="#666" font-family="Inter, system-ui, sans-serif">{label}</text>
  <text x="{width - 5}" y="15" font-size="13" fill="#333" font-family="Inter, system-ui, sans-serif" text-anchor="end" font-weight="600">{value}%</text>
  <rect x="0" y="24" width="{width}" height="16" rx="8" fill="#e5e7eb"/>
  <rect x="0" y="24" width="{fill_w}" height="16" rx="8" fill="{color}"/>
</svg>'''


# ── TIMELINE ─────────────────────────────────────────────────────────────────

def svg_timeline(steps: list, active=0, color="#D97757", width=700):
    """Горизонтальный таймлайн с шагами."""
    n = len(steps)
    pad = 50  # enough for centered text not to clip
    step_w = (width - 2 * pad) // max(n - 1, 1)

    nodes = []
    for i, label in enumerate(steps):
        x = pad + i * step_w
        is_active = i < active
        is_current = i == active
        fill = color if (is_active or is_current) else "#e5e7eb"
        text_color = "#333" if (is_active or is_current) else "#999"
        r = 10 if is_current else 7

        # Линия к следующему
        if i < n - 1:
            nx = pad + (i + 1) * step_w
            line_color = color if is_active else "#e5e7eb"
            nodes.append(f'  <line x1="{x}" y1="30" x2="{nx}" y2="30" stroke="{line_color}" stroke-width="3"/>')

        nodes.append(f'  <circle cx="{x}" cy="30" r="{r}" fill="{fill}"/>')
        nodes.append(f'  <text x="{x}" y="58" font-size="11" fill="{text_color}" text-anchor="middle" font-family="Inter, system-ui, sans-serif">{label}</text>')

    return f'<svg viewBox="0 0 {width} 70" xmlns="http://www.w3.org/2000/svg">\n' + "\n".join(nodes) + "\n</svg>"


# ── METRIC CARD ──────────────────────────────────────────────────────────────

def svg_metric(value: str, label: str, color="#D97757"):
    """Большая метрика (число + подпись)."""
    return f'''<svg viewBox="0 0 200 80" xmlns="http://www.w3.org/2000/svg">
  <text x="100" y="40" font-size="36" fill="{color}" font-weight="800" text-anchor="middle" font-family="Inter, system-ui, sans-serif">{value}</text>
  <text x="100" y="65" font-size="12" fill="#888" text-anchor="middle" font-family="Inter, system-ui, sans-serif" text-transform="uppercase" letter-spacing="1">{label}</text>
</svg>'''


# ── ICONS ────────────────────────────────────────────────────────────────────

ICONS = {
    "rocket": '<path d="M12 2L8 12h3v8l5-10h-3z" fill="currentColor"/>',
    "chart": '<path d="M3 20h18v-2H3v2zm0-4h6v-4H3v4zm8 0h6V8h-6v8zm8 0h2V4h-2v12z" fill="currentColor"/>',
    "users": '<path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z" fill="currentColor"/>',
    "shield": '<path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4z" fill="currentColor"/>',
    "check": '<path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" fill="currentColor"/>',
    "star": '<path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01z" fill="currentColor"/>',
    "lightning": '<path d="M7 2v11h3v9l7-12h-4l4-8z" fill="currentColor"/>',
    "clock": '<path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10 10-4.5 10-10S17.5 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z" fill="currentColor"/>',
    "target": '<circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="12" r="6" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="12" r="2" fill="currentColor"/>',
    "trending": '<path d="M16 6l2.29 2.29-4.88 4.88-4-4L2 16.59 3.41 18l6-6 4 4 6.3-6.29L22 12V6z" fill="currentColor"/>',
}

def svg_icon(name: str, size=24, color="#D97757"):
    """Одна иконка."""
    path = ICONS.get(name, ICONS["star"])
    return f'<svg viewBox="0 0 24 24" width="{size}" height="{size}" xmlns="http://www.w3.org/2000/svg" style="color:{color}">{path}</svg>'

def svg_icons_row(names: list, size=32, color="#D97757", gap=16):
    """Ряд иконок."""
    total_w = len(names) * (size + gap) - gap
    icons = []
    for i, name in enumerate(names):
        x = i * (size + gap)
        path = ICONS.get(name, ICONS["star"])
        icons.append(f'  <g transform="translate({x},0)" style="color:{color}">{path}</g>')
    return f'<svg viewBox="0 0 {total_w} 24" width="{total_w}" height="{size}" xmlns="http://www.w3.org/2000/svg">\n' + "\n".join(icons) + "\n</svg>"


# ── STEPS (numbered) ─────────────────────────────────────────────────────────

def svg_steps(steps: list, color="#D97757", width=700):
    """Горизонтальные шаги с большими номерами."""
    n = len(steps)
    step_w = width // n

    nodes = []
    for i, label in enumerate(steps):
        cx = step_w * i + step_w // 2
        num = i + 1
        # Большой номер
        nodes.append(f'  <text x="{cx}" y="35" font-size="32" fill="{color}" font-weight="800" text-anchor="middle" font-family="Inter, system-ui, sans-serif">{num}</text>')
        # Подпись
        nodes.append(f'  <text x="{cx}" y="60" font-size="12" fill="#666" text-anchor="middle" font-family="Inter, system-ui, sans-serif">{label}</text>')
        # Стрелка между шагами
        if i < n - 1:
            ax = step_w * (i + 1)
            nodes.append(f'  <text x="{ax}" y="35" font-size="20" fill="#ccc" text-anchor="middle" font-family="Inter, system-ui, sans-serif">→</text>')

    return f'<svg viewBox="0 0 {width} 75" xmlns="http://www.w3.org/2000/svg">\n' + "\n".join(nodes) + "\n</svg>"


# ── COMPARISON (before/after) ────────────────────────────────────────────────

def svg_comparison(before: str, after: str, before_val="", after_val="", color="#D97757", width=600):
    """Before/After сравнение."""
    mid = width // 2
    return f'''<svg viewBox="0 0 {width} 90" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="0" width="{mid - 10}" height="85" rx="8" fill="#f3f1ec"/>
  <rect x="{mid + 10}" y="0" width="{mid - 10}" height="85" rx="8" fill="{color}" opacity="0.1"/>
  <text x="{mid // 2}" y="25" font-size="11" fill="#999" text-anchor="middle" font-family="Inter, system-ui, sans-serif" text-transform="uppercase" letter-spacing="1">ДО</text>
  <text x="{mid // 2}" y="50" font-size="14" fill="#666" text-anchor="middle" font-family="Inter, system-ui, sans-serif">{before}</text>
  <text x="{mid // 2}" y="72" font-size="18" fill="#999" text-anchor="middle" font-family="Inter, system-ui, sans-serif" font-weight="700">{before_val}</text>
  <text x="{mid + mid // 2}" y="25" font-size="11" fill="{color}" text-anchor="middle" font-family="Inter, system-ui, sans-serif" text-transform="uppercase" letter-spacing="1">ПОСЛЕ</text>
  <text x="{mid + mid // 2}" y="50" font-size="14" fill="#333" text-anchor="middle" font-family="Inter, system-ui, sans-serif">{after}</text>
  <text x="{mid + mid // 2}" y="72" font-size="18" fill="{color}" text-anchor="middle" font-family="Inter, system-ui, sans-serif" font-weight="700">{after_val}</text>
  <text x="{mid}" y="50" font-size="20" fill="#ccc" text-anchor="middle" font-family="Inter, system-ui, sans-serif">→</text>
</svg>'''


# ── STAT CARD ────────────────────────────────────────────────────────────────

def svg_stat_card(value: str, label: str, icon: str = "", color="#D97757", width=180):
    """Карточка статистики с рамкой."""
    icon_svg = ""
    if icon and icon in ICONS:
        icon_svg = f'<g transform="translate({width//2 - 12}, 8) scale(1)" style="color:{color}">{ICONS[icon]}</g>'

    y_val = 55 if icon else 40
    y_label = y_val + 22
    h = y_label + 15

    return f'''<svg viewBox="0 0 {width} {h}" xmlns="http://www.w3.org/2000/svg">
  <rect x="1" y="1" width="{width-2}" height="{h-2}" rx="10" fill="none" stroke="{color}" stroke-width="1.5" opacity="0.3"/>
  {icon_svg}
  <text x="{width//2}" y="{y_val}" font-size="28" fill="{color}" font-weight="800" text-anchor="middle" font-family="Inter, system-ui, sans-serif">{value}</text>
  <text x="{width//2}" y="{y_label}" font-size="11" fill="#888" text-anchor="middle" font-family="Inter, system-ui, sans-serif">{label}</text>
</svg>'''


# ── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Marp SVG — диаграммы для презентаций")
    sub = parser.add_subparsers(dest="command")

    # bar
    b = sub.add_parser("bar", help="Столбчатая диаграмма")
    b.add_argument("--data", required=True, help='JSON: {"Label": value, ...}')
    b.add_argument("--colors", help="Цвета через запятую")
    b.add_argument("--palette", choices=list(PALETTES.keys()))
    b.add_argument("--output", help="Сохранить в файл")

    # pie
    p = sub.add_parser("pie", help="Круговая диаграмма")
    p.add_argument("--data", required=True, help='JSON: {"Label": percent, ...}')
    p.add_argument("--colors", help="Цвета через запятую")
    p.add_argument("--palette", choices=list(PALETTES.keys()))
    p.add_argument("--output", help="Сохранить в файл")

    # progress
    pr = sub.add_parser("progress", help="Прогресс-бар")
    pr.add_argument("--value", type=int, required=True, help="0-100")
    pr.add_argument("--label", default="")
    pr.add_argument("--color", default="#D97757")
    pr.add_argument("--output", help="Сохранить в файл")

    # timeline
    t = sub.add_parser("timeline", help="Таймлайн")
    t.add_argument("--data", required=True, help='JSON: ["Step1", "Step2", ...]')
    t.add_argument("--active", type=int, default=0, help="Текущий шаг (0-based)")
    t.add_argument("--color", default="#D97757")
    t.add_argument("--output", help="Сохранить в файл")

    # metric
    m = sub.add_parser("metric", help="Большая метрика")
    m.add_argument("--value", required=True, help="Число/процент")
    m.add_argument("--label", required=True, help="Подпись")
    m.add_argument("--color", default="#D97757")
    m.add_argument("--output", help="Сохранить в файл")

    # icons
    ic = sub.add_parser("icons", help="Иконки")
    ic.add_argument("--names", required=True, help="rocket,chart,users,shield,check,star,lightning,clock,target,trending")
    ic.add_argument("--color", default="#D97757")
    ic.add_argument("--size", type=int, default=32)
    ic.add_argument("--output", help="Сохранить в файл")

    # steps
    st = sub.add_parser("steps", help="Нумерованные шаги")
    st.add_argument("--data", required=True, help='JSON: ["Step1", "Step2", ...]')
    st.add_argument("--color", default="#D97757")
    st.add_argument("--output", help="Сохранить в файл")

    # comparison
    cmp = sub.add_parser("comparison", help="До/После сравнение")
    cmp.add_argument("--before", required=True, help="Текст 'до'")
    cmp.add_argument("--after", required=True, help="Текст 'после'")
    cmp.add_argument("--before-val", default="", help="Значение 'до'")
    cmp.add_argument("--after-val", default="", help="Значение 'после'")
    cmp.add_argument("--color", default="#D97757")
    cmp.add_argument("--output", help="Сохранить в файл")

    # stat-card
    sc = sub.add_parser("stat-card", help="Карточка статистики")
    sc.add_argument("--value", required=True)
    sc.add_argument("--label", required=True)
    sc.add_argument("--icon", default="", help="rocket,chart,users,shield,check,star,trending")
    sc.add_argument("--color", default="#D97757")
    sc.add_argument("--output", help="Сохранить в файл")

    # palettes
    sub.add_parser("palettes", help="Показать палитры")
    sub.add_parser("icon-list", help="Показать доступные иконки")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    svg = ""

    if args.command == "bar":
        data = json.loads(args.data)
        colors = args.colors.split(",") if args.colors else PALETTES.get(args.palette, DEFAULT_COLORS)
        svg = svg_bar(data, colors)
    elif args.command == "pie":
        data = json.loads(args.data)
        colors = args.colors.split(",") if args.colors else PALETTES.get(args.palette, DEFAULT_COLORS)
        svg = svg_pie(data, colors)
    elif args.command == "progress":
        svg = svg_progress(args.value, args.label, args.color)
    elif args.command == "timeline":
        steps = json.loads(args.data)
        svg = svg_timeline(steps, args.active, args.color)
    elif args.command == "metric":
        svg = svg_metric(args.value, args.label, args.color)
    elif args.command == "icons":
        names = [n.strip() for n in args.names.split(",")]
        svg = svg_icons_row(names, args.size, args.color)
    elif args.command == "steps":
        steps = json.loads(args.data)
        svg = svg_steps(steps, args.color)
    elif args.command == "comparison":
        svg = svg_comparison(args.before, args.after, args.before_val, args.after_val, args.color)
    elif args.command == "stat-card":
        svg = svg_stat_card(args.value, args.label, args.icon, args.color)
    elif args.command == "palettes":
        for name, colors in PALETTES.items():
            print(f"  {name:10s}: {', '.join(colors)}")
        return
    elif args.command == "icon-list":
        print(f"  Иконки: {', '.join(ICONS.keys())}")
        return

    if hasattr(args, 'output') and args.output:
        Path(args.output).write_text(svg)
        print(f"✅ Сохранено: {args.output}", file=sys.stderr)
    else:
        print(svg)


if __name__ == "__main__":
    main()
