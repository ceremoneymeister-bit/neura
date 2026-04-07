#!/usr/bin/env python3
"""Cron Guardian + Slot Manager — управление всеми кронами сервера.

Считает Claude CLI вызовы, управляет слотами, предотвращает конфликты.

Usage:
  python3 guardian.py status              # текущий статус: сколько вызовов, сколько осталось
  python3 guardian.py schedule            # показать расписание с Claude-нагрузкой
  python3 guardian.py check               # проверить конфликты и скопления
  python3 guardian.py gate                # gate-check: можно ли сейчас запустить Claude CLI?
  python3 guardian.py log [source]        # записать использование Claude CLI
  python3 guardian.py report [--days 7]   # отчёт за N дней
  python3 guardian.py optimize            # предложить оптимальное расписание
  python3 guardian.py map                 # карта всех кронов (24-часовая сетка)
  python3 guardian.py map --scan          # пересканировать crontab + systemd → обновить реестр
  python3 guardian.py slot-find <HH:MM>   # найти ближайший свободный слот
  python3 guardian.py register --id X --time HH:MM --cmd "..."  # зарегистрировать крон
  python3 guardian.py unregister <id>     # удалить крон из реестра
  python3 guardian.py alert-check         # проверить пороги и отправить TG-уведомление
"""

import json
import re
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
USAGE_LOG = DATA_DIR / "claude_usage.jsonl"
CONFIG_FILE = DATA_DIR / "limits.json"
REGISTRY_FILE = DATA_DIR / "cron-registry.json"
ALERTS_FILE = DATA_DIR / "alerts_sent.json"
_PROJECT = Path(os.environ.get("NEURA_BASE", str(Path(__file__).resolve().parent.parent.parent)))
REMINDERS_FILE = _PROJECT / "data" / "reminders.json"
TG_SEND = _PROJECT / "scripts" / "tg-send.py"

# ── Default limits ──────────────────────────────────────────────

DEFAULT_LIMITS = {
    "daily_max_calls": 45,          # Max Claude CLI вызовов в день (безопасный порог)
    "hourly_max_calls": 8,          # Max вызовов в час
    "min_interval_seconds": 120,    # Минимум 2 минуты между вызовами
    "reserved_for_interactive": 15, # Резерв для ручной работы Дмитрия
    "peak_hours_utc": [6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
    "night_budget_pct": 30,         # % бюджета на ночные задачи (20:00-06:00 UTC)
    # Slot Manager limits
    "max_total_crons": 60,          # Максимум слотов в реестре
    "min_interval_minutes": 2,      # Минимальный интервал между кронами (минут)
    "max_per_hour": 8,              # Максимум кронов в одном часу
    "alert_threshold_pct": 75,      # Уведомление при заполнении (%)
    "alert_critical_pct": 90,       # Критическое уведомление (%)
}


def _load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(DEFAULT_LIMITS, indent=2))
    return DEFAULT_LIMITS.copy()


def _read_jsonl(path: Path) -> list:
    if not path.exists() or path.stat().st_size == 0:
        return []
    entries = []
    for line in path.read_text().strip().split("\n"):
        if line.strip():
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def _append_jsonl(path: Path, entry: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ── Registry (Slot Manager) ─────────────────────────────────────

def _load_registry() -> dict:
    if REGISTRY_FILE.exists():
        try:
            return json.loads(REGISTRY_FILE.read_text())
        except json.JSONDecodeError:
            pass
    return {"version": 1, "updated": "", "slots": []}


def _save_registry(reg: dict):
    reg["updated"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REGISTRY_FILE.write_text(json.dumps(reg, indent=2, ensure_ascii=False))


def _parse_cron_expr_minutes(expr: str) -> list:
    """Parse cron expression to list of (hour, minute) tuples for a typical day.
    Handles: '0 3 * * *', '*/15 * * * *', '3 19 * * 1-5', '0 0,6,12,18 * * *'
    Returns only daily-recurring entries (ignores specific dates for simplicity).
    """
    parts = expr.strip().split()
    if len(parts) < 5:
        return []
    m_part, h_part = parts[0], parts[1]

    def expand(field, max_val):
        if field == "*":
            return list(range(max_val))
        if field.startswith("*/"):
            step = int(field[2:])
            return list(range(0, max_val, step))
        results = []
        for chunk in field.split(","):
            if "-" in chunk:
                a, b = chunk.split("-", 1)
                results.extend(range(int(a), int(b) + 1))
            else:
                results.append(int(chunk))
        return results

    hours = expand(h_part, 24)
    minutes = expand(m_part, 60)
    return [(h, m) for h in hours for m in minutes]


def _parse_crontab() -> list:
    """Parse root crontab into slot entries."""
    try:
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=5)
        lines = result.stdout.strip().split("\n") if result.returncode == 0 else []
    except Exception:
        return []

    slots = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Match cron expression (5 fields) + command
        m = re.match(r'^([\d\*/,\-]+\s+[\d\*/,\-]+\s+[\d\*/,\-]+\s+[\d\*/,\-]+\s+[\d\*/,\-]+)\s+(.+)$', line)
        if not m:
            continue
        cron_expr, command = m.group(1), m.group(2)
        # Derive ID from command
        cmd_basename = re.search(r'([\w\-]+)\.py', command)
        slot_id = cmd_basename.group(1) if cmd_basename else command[:30].replace(" ", "-")
        # Deduplicate with suffix if needed
        existing_ids = [s["id"] for s in slots]
        if slot_id in existing_ids:
            slot_id = f"{slot_id}-{len([x for x in existing_ids if x.startswith(slot_id)]) + 1}"

        hm_list = _parse_cron_expr_minutes(cron_expr)
        if hm_list:
            schedule_str = f"{hm_list[0][0]:02d}:{hm_list[0][1]:02d}"
            if len(hm_list) > 1:
                schedule_str += f" (+{len(hm_list)-1} more)"
        else:
            schedule_str = cron_expr

        slots.append({
            "id": slot_id,
            "source": "crontab",
            "schedule": schedule_str,
            "cron_expr": cron_expr,
            "timer_unit": None,
            "command": command[:200],
            "owner": "system",
            "priority": "system",
            "claude_calls": 0,
            "enabled": True,
            "added": datetime.now().strftime("%Y-%m-%d"),
        })
    return slots


def _parse_systemd_timers() -> list:
    """Parse enabled systemd timers into slot entries."""
    try:
        result = subprocess.run(
            ["systemctl", "list-timers", "--all", "--no-pager", "--output=json"],
            capture_output=True, text=True, timeout=10
        )
    except Exception:
        return []

    # Fallback: parse text output
    slots = []
    try:
        result2 = subprocess.run(
            ["systemctl", "list-unit-files", "--type=timer", "--state=enabled", "--no-pager", "--no-legend"],
            capture_output=True, text=True, timeout=10
        )
        enabled_timers = []
        for line in result2.stdout.strip().split("\n"):
            if line.strip():
                unit = line.split()[0]
                enabled_timers.append(unit)
    except Exception:
        enabled_timers = []

    for timer_unit in enabled_timers:
        # Get timer info
        try:
            show = subprocess.run(
                ["systemctl", "show", timer_unit, "--property=TimersCalendar,Description"],
                capture_output=True, text=True, timeout=5
            )
            props = {}
            for pline in show.stdout.strip().split("\n"):
                if "=" in pline:
                    k, v = pline.split("=", 1)
                    props[k.strip()] = v.strip()
        except Exception:
            props = {}

        timer_cal = props.get("TimersCalendar", "")
        # Extract time from calendar spec like "{ OnCalendar=*-*-* 01:30:00 }"
        time_match = re.search(r'(\d{2}):(\d{2})', timer_cal)
        if time_match:
            schedule_str = f"{time_match.group(1)}:{time_match.group(2)} daily"
        else:
            schedule_str = timer_cal or "unknown"

        service_name = timer_unit.replace(".timer", "")
        slots.append({
            "id": service_name,
            "source": "systemd",
            "schedule": schedule_str,
            "cron_expr": None,
            "timer_unit": timer_unit,
            "command": props.get("Description", service_name),
            "owner": "system",
            "priority": "system",
            "claude_calls": 0,
            "enabled": True,
            "added": datetime.now().strftime("%Y-%m-%d"),
        })
    return slots


def _parse_reminders() -> list:
    """Parse reminders.json into slot entries."""
    if not REMINDERS_FILE.exists():
        return []
    try:
        reminders = json.loads(REMINDERS_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return []

    slots = []
    for i, r in enumerate(reminders):
        time_str = r.get("time", "")
        time_match = re.search(r'(\d{2}):(\d{2})', time_str)
        if time_match:
            schedule_str = f"{time_match.group(1)}:{time_match.group(2)}"
        else:
            schedule_str = time_str

        slots.append({
            "id": f"reminder-{i}",
            "source": "reminder",
            "schedule": schedule_str,
            "cron_expr": None,
            "timer_unit": None,
            "command": r.get("text", "")[:100],
            "owner": "dmitry",
            "priority": "optional",
            "claude_calls": 0,
            "enabled": True,
            "added": time_str[:10] if len(time_str) >= 10 else datetime.now().strftime("%Y-%m-%d"),
        })
    return slots


def _scan_and_merge() -> dict:
    """Scan all sources and merge with existing registry (preserving manual fields)."""
    existing = _load_registry()
    existing_by_id = {s["id"]: s for s in existing.get("slots", [])}

    scanned = []
    scanned.extend(_parse_crontab())
    scanned.extend(_parse_systemd_timers())
    scanned.extend(_parse_reminders())

    # Merge: scanned data + preserved manual fields from existing
    manual_fields = ("owner", "priority", "claude_calls", "tags")
    merged = []
    seen_ids = set()

    for slot in scanned:
        sid = slot["id"]
        if sid in existing_by_id:
            # Preserve manual overrides
            for field in manual_fields:
                if field in existing_by_id[sid]:
                    slot[field] = existing_by_id[sid][field]
        merged.append(slot)
        seen_ids.add(sid)

    # Keep manually-added entries that weren't found in scan
    for sid, slot in existing_by_id.items():
        if sid not in seen_ids:
            slot["enabled"] = False  # Mark as possibly removed
            merged.append(slot)

    reg = {"version": 1, "updated": "", "slots": merged}
    _save_registry(reg)
    return reg


def _get_all_minutes(slots: list, skip_highfreq: bool = True) -> list:
    """Build array of 1440 booleans — occupied minutes in a day.
    skip_highfreq: ignore crons that fire >24 times/day (*/5, */15 etc) — they're background tasks.
    """
    MAX_FIRES = 24  # More than hourly = background task
    occupied = [False] * 1440
    for slot in slots:
        if not slot.get("enabled", True):
            continue
        if slot.get("cron_expr"):
            fires = _parse_cron_expr_minutes(slot["cron_expr"])
            if skip_highfreq and len(fires) > MAX_FIRES:
                continue
            for h, m in fires:
                idx = h * 60 + m
                if 0 <= idx < 1440:
                    occupied[idx] = True
        else:
            match = re.search(r'(\d{2}):(\d{2})', slot.get("schedule", ""))
            if match:
                idx = int(match.group(1)) * 60 + int(match.group(2))
                if 0 <= idx < 1440:
                    occupied[idx] = True
    return occupied


def _find_free_slot(preferred_hm: str, slots: list, min_gap: int = 2, window: int = 60) -> str | None:
    """Find nearest free minute to preferred time (HH:MM), with min_gap buffer."""
    occupied = _get_all_minutes(slots)
    # Expand occupied zones by min_gap
    expanded = [False] * 1440
    for i in range(1440):
        if occupied[i]:
            for d in range(-min_gap, min_gap + 1):
                idx = (i + d) % 1440
                expanded[idx] = True

    h, m = int(preferred_hm.split(":")[0]), int(preferred_hm.split(":")[1])
    center = h * 60 + m

    # Search outward from center
    for offset in range(window + 1):
        for sign in (1, -1):
            candidate = (center + sign * offset) % 1440
            if not expanded[candidate]:
                return f"{candidate // 60:02d}:{candidate % 60:02d}"

    return None


# ── Known Claude-consuming tasks ────────────────────────────────

# Each entry: (name, schedule_utc, estimated_calls, owner, priority)
# priority: "client" = не трогать, "system" = можно сдвинуть, "optional" = можно отключить
KNOWN_TASKS = [
    # Victoria — client priority
    ("victoria-intention",  "01:30", 1, "victoria", "client"),
    ("victoria-fact",       "04:00", 1, "victoria", "client"),
    ("victoria-content",    "07:00", 1, "victoria", "client"),
    ("victoria-tool",       "11:00", 1, "victoria", "client"),
    ("victoria-reflect",    "14:30", 1, "victoria", "client"),
    # Yulia — client priority
    ("yulia-intention",     "06:00", 1, "yulia",    "client"),
    ("yulia-reflect",       "18:00", 1, "yulia",    "client"),
    # Marina — client priority
    ("proactive-marina",    "06:03", 1, "marina",   "client"),
    # Night orchestrator — system
    ("night-orchestrator",  "20:00", 5, "system",   "system"),  # ~5 calls per session
    # Autopilot (cron) — system, uses Claude for rewrite
    ("channel-autopilot",   "19:00", 3, "system",   "system"),
]

# Non-Claude tasks (for reference, don't count)
NON_CLAUDE_TASKS = [
    "block-monitor", "email-digest", "vector-reindex", "generate-system-map",
    "reminders", "sync-tasks-to-web", "sync-tasks-from-web",
    "error-tracker", "neura-app-healthcheck", "acme-ssl",
]


def _get_today_usage() -> list:
    """Get today's Claude CLI usage from log."""
    entries = _read_jsonl(USAGE_LOG)
    today = datetime.now().strftime("%Y-%m-%d")
    return [e for e in entries if e.get("date", "").startswith(today)]


def _get_hour_usage() -> list:
    """Get current hour's Claude CLI usage."""
    entries = _read_jsonl(USAGE_LOG)
    now = datetime.now()
    hour_start = now.replace(minute=0, second=0).strftime("%Y-%m-%d %H")
    return [e for e in entries if e.get("date", "").startswith(hour_start)]


# ── Commands ────────────────────────────────────────────────────

def status():
    """Show current usage status."""
    config = _load_config()
    today_entries = _get_today_usage()
    hour_entries = _get_hour_usage()

    daily_used = len(today_entries)
    hourly_used = len(hour_entries)
    daily_limit = config["daily_max_calls"]
    hourly_limit = config["hourly_max_calls"]
    reserved = config["reserved_for_interactive"]

    # Scheduled calls remaining today
    now_hour = datetime.now().hour
    scheduled_remaining = sum(
        t[2] for t in KNOWN_TASKS
        if int(t[1].split(":")[0]) > now_hour
    )

    available = daily_limit - daily_used - reserved
    available_for_cron = available - scheduled_remaining

    # Status icons
    daily_icon = "🟢" if daily_used < daily_limit * 0.6 else "🟡" if daily_used < daily_limit * 0.85 else "🔴"
    hourly_icon = "🟢" if hourly_used < hourly_limit * 0.6 else "🟡" if hourly_used < hourly_limit * 0.85 else "🔴"

    print(f"""📊 Cron Guardian — статус

{daily_icon} День:     {daily_used}/{daily_limit} использовано ({available} доступно)
{hourly_icon} Час:      {hourly_used}/{hourly_limit}
🔒 Резерв:  {reserved} для интерактивной работы
📅 План:    ~{scheduled_remaining} вызовов ещё запланировано на сегодня
💡 Свободно для доп. задач: {max(0, available_for_cron)}

Источники за сегодня:""")

    by_source = defaultdict(int)
    for e in today_entries:
        by_source[e.get("source", "unknown")] += 1
    for src, count in sorted(by_source.items(), key=lambda x: x[1], reverse=True):
        print(f"  {src}: {count}")


def schedule():
    """Show daily schedule with Claude load."""
    print("📅 Расписание Claude CLI вызовов (UTC)\n")
    print(f"{'Время':<8} {'Задача':<25} {'Calls':<7} {'Owner':<10} {'Приоритет'}")
    print("─" * 65)

    total = 0
    by_hour = defaultdict(int)

    for name, time_utc, calls, owner, priority in sorted(KNOWN_TASKS, key=lambda x: x[1]):
        hour = int(time_utc.split(":")[0])
        by_hour[hour] += calls
        total += calls
        pri_icon = {"client": "🔒", "system": "⚙️", "optional": "💤"}.get(priority, "?")
        print(f"{time_utc:<8} {name:<25} {calls:<7} {owner:<10} {pri_icon} {priority}")

    print(f"\n{'─' * 65}")
    print(f"ИТОГО:   {total} Claude CLI вызовов/день")

    # Show hourly distribution
    print(f"\nПо часам (UTC):")
    for h in range(24):
        if by_hour[h] > 0:
            bar = "█" * by_hour[h]
            print(f"  {h:02d}:00  {bar} {by_hour[h]}")

    # Check conflicts (same hour)
    conflicts = [(h, c) for h, c in by_hour.items() if c > 3]
    if conflicts:
        print(f"\n⚠️ Скопления (>3 вызова/час):")
        for h, c in conflicts:
            tasks = [t[0] for t in KNOWN_TASKS if int(t[1].split(":")[0]) == h]
            print(f"  {h:02d}:00 — {c} вызовов: {', '.join(tasks)}")


def check():
    """Check for scheduling conflicts and suggest fixes."""
    issues = []
    config = _load_config()

    # 1. Check total daily budget
    total_scheduled = sum(t[2] for t in KNOWN_TASKS)
    budget = config["daily_max_calls"] - config["reserved_for_interactive"]
    if total_scheduled > budget:
        issues.append(f"🔴 Запланировано {total_scheduled} вызовов, бюджет {budget}. Превышение на {total_scheduled - budget}!")

    # 2. Check hourly conflicts
    by_hour = defaultdict(list)
    for t in KNOWN_TASKS:
        hour = int(t[1].split(":")[0])
        by_hour[hour].append(t)

    for hour, tasks in by_hour.items():
        total = sum(t[2] for t in tasks)
        if total > config["hourly_max_calls"]:
            names = [t[0] for t in tasks]
            issues.append(f"🟡 {hour:02d}:00 UTC — {total} вызовов ({', '.join(names)}). Лимит: {config['hourly_max_calls']}/час")

    # 3. Check min interval
    times = sorted([(int(t[1].split(":")[0]) * 60 + int(t[1].split(":")[1]), t[0]) for t in KNOWN_TASKS])
    for i in range(1, len(times)):
        diff = times[i][0] - times[i-1][0]
        if diff < config["min_interval_seconds"] / 60:
            issues.append(f"🟡 {times[i-1][1]} и {times[i][1]} слишком близко ({diff} мин). Мин. интервал: {config['min_interval_seconds']//60} мин")

    # 4. Night budget
    night_calls = sum(t[2] for t in KNOWN_TASKS if int(t[1].split(":")[0]) >= 20 or int(t[1].split(":")[0]) < 6)
    night_budget = budget * config["night_budget_pct"] / 100
    if night_calls > night_budget:
        issues.append(f"🟡 Ночные задачи: {night_calls} вызовов, бюджет ночи: {int(night_budget)}")

    if not issues:
        print("✅ Расписание в порядке. Конфликтов не найдено.")
    else:
        print(f"⚠️ Найдено {len(issues)} проблем:\n")
        for issue in issues:
            print(f"  {issue}")

    return issues


def gate() -> bool:
    """Gate check: can we run Claude CLI right now?
    Returns True if OK, False if limit reached.
    Use this in scripts: if guardian.py gate exits 0 → run, else → skip.
    """
    config = _load_config()
    today = _get_today_usage()
    hour = _get_hour_usage()

    daily_limit = config["daily_max_calls"]
    hourly_limit = config["hourly_max_calls"]

    if len(today) >= daily_limit:
        print(f"⛔ BLOCKED: дневной лимит {daily_limit} исчерпан ({len(today)} вызовов)")
        sys.exit(1)

    if len(hour) >= hourly_limit:
        print(f"⛔ BLOCKED: часовой лимит {hourly_limit} исчерпан ({len(hour)} вызовов)")
        sys.exit(1)

    # Check min interval
    if today:
        last = today[-1]
        try:
            last_time = datetime.strptime(last["date"], "%Y-%m-%d %H:%M:%S")
            diff = (datetime.now() - last_time).total_seconds()
            if diff < config["min_interval_seconds"]:
                print(f"⏳ WAIT: {int(config['min_interval_seconds'] - diff)}s до следующего вызова")
                sys.exit(1)
        except (ValueError, KeyError):
            pass

    remaining = daily_limit - len(today)
    print(f"✅ OK: {remaining} вызовов осталось сегодня")
    sys.exit(0)


def log_usage(source: str = "unknown"):
    """Log a Claude CLI usage event."""
    entry = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": source,
    }
    _append_jsonl(USAGE_LOG, entry)
    today_count = len(_get_today_usage())
    config = _load_config()
    remaining = config["daily_max_calls"] - today_count
    print(f"Logged: {source} ({today_count}/{config['daily_max_calls']}, осталось {remaining})")


def report(days: int = 7):
    """Usage report for N days."""
    entries = _read_jsonl(USAGE_LOG)
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    recent = [e for e in entries if e.get("date", "")[:10] >= cutoff]

    if not recent:
        print(f"Нет данных за {days} дней.")
        return

    by_day = defaultdict(int)
    by_source = defaultdict(int)
    for e in recent:
        by_day[e["date"][:10]] += 1
        by_source[e.get("source", "unknown")] += 1

    config = _load_config()
    limit = config["daily_max_calls"]

    print(f"📊 Cron Guardian — отчёт за {days} дней\n")
    print(f"{'Дата':<12} {'Вызовов':<10} {'% от лимита':<15} {'Статус'}")
    print("─" * 45)
    for day in sorted(by_day.keys()):
        count = by_day[day]
        pct = round(count / limit * 100)
        icon = "🟢" if pct < 60 else "🟡" if pct < 85 else "🔴"
        print(f"{day:<12} {count:<10} {pct}%{'':>10} {icon}")

    print(f"\nПо источникам:")
    for src, count in sorted(by_source.items(), key=lambda x: x[1], reverse=True):
        print(f"  {src}: {count}")

    avg = round(sum(by_day.values()) / max(len(by_day), 1), 1)
    print(f"\nСреднее: {avg} вызовов/день (лимит: {limit})")


def optimize():
    """Suggest optimal schedule to avoid conflicts."""
    print("🔧 Оптимизация расписания\n")

    # Separate client (locked) and system (moveable)
    locked = [t for t in KNOWN_TASKS if t[4] == "client"]
    moveable = [t for t in KNOWN_TASKS if t[4] != "client"]

    print("🔒 Зафиксированные (client):")
    for t in locked:
        print(f"  {t[1]} — {t[0]} ({t[2]} calls)")

    if not moveable:
        print("\n✅ Нет задач для оптимизации.")
        return

    # Find free hours (no client tasks)
    occupied_hours = set()
    for t in locked:
        h = int(t[1].split(":")[0])
        occupied_hours.add(h)

    free_hours = [h for h in range(24) if h not in occupied_hours]

    print(f"\n⚙️ Передвигаемые (system/optional):")
    suggestions = []
    for i, t in enumerate(moveable):
        current_hour = int(t[1].split(":")[0])
        if current_hour in occupied_hours:
            # Find nearest free hour
            best = min(free_hours, key=lambda h: abs(h - current_hour)) if free_hours else current_hour
            suggestions.append((t[0], t[1], f"{best:02d}:15", t[2]))
            print(f"  {t[0]}: {t[1]} → {best:02d}:15 (сдвинуть, конфликт с client)")
        else:
            print(f"  {t[0]}: {t[1]} — ✅ ок")

    if suggestions:
        print(f"\n📋 Предложения:")
        for name, old, new, calls in suggestions:
            print(f"  {name}: {old} → {new}")
        print(f"\nПрименить: вручную через `systemctl edit {suggestions[0][0]}.timer`")


# ── Slot Manager Commands ──────────────────────────────────────

def cron_map(scan: bool = False):
    """Show or scan the cron slot map."""
    if scan:
        reg = _scan_and_merge()
        print(f"🔄 Реестр обновлён: {len(reg['slots'])} слотов найдено")
    else:
        reg = _load_registry()
        if not reg["slots"]:
            print("⚠️ Реестр пуст. Запусти: guardian.py map --scan")
            return

    slots = [s for s in reg["slots"] if s.get("enabled", True)]
    config = _load_config()
    max_total = config.get("max_total_crons", 60)

    print(f"\n🗺️  Карта кронов ({len(slots)}/{max_total} слотов)")
    if reg.get("updated"):
        print(f"📅 Обновлено: {reg['updated']}")

    # Group by hour
    by_hour = defaultdict(list)
    for s in slots:
        match = re.search(r'(\d{2}):', s.get("schedule", ""))
        hour = int(match.group(1)) if match else -1
        by_hour[hour].append(s)

    print(f"\n{'Час':<6} {'#':<4} {'Слоты'}")
    print("─" * 70)
    for h in range(24):
        hour_slots = by_hour.get(h, [])
        if not hour_slots:
            print(f"{h:02d}:00  {'·':<4}")
            continue
        count = len(hour_slots)
        max_h = config.get("max_per_hour", 8)
        icon = "🔴" if count >= max_h else "🟡" if count >= max_h * 0.7 else "🟢"
        names = ", ".join(s["id"] for s in hour_slots[:5])
        if len(hour_slots) > 5:
            names += f" (+{len(hour_slots)-5})"
        print(f"{h:02d}:00  {icon}{count:<3} {names}")

    # Summary
    sources = defaultdict(int)
    for s in slots:
        sources[s.get("source", "?")] += 1
    src_str = ", ".join(f"{k}: {v}" for k, v in sorted(sources.items()))
    pct = round(len(slots) / max_total * 100)
    fill_icon = "🟢" if pct < 75 else "🟡" if pct < 90 else "🔴"
    print(f"\n{fill_icon} Заполнение: {len(slots)}/{max_total} ({pct}%)")
    print(f"📦 Источники: {src_str}")


def slot_find_cmd(preferred: str):
    """Find nearest free slot to preferred time."""
    reg = _load_registry()
    if not reg["slots"]:
        print("⚠️ Реестр пуст. Сначала: guardian.py map --scan")
        return
    config = _load_config()
    min_gap = config.get("min_interval_minutes", 2)
    result = _find_free_slot(preferred, reg["slots"], min_gap=min_gap)
    if result:
        print(f"✅ Свободный слот: {result} (ближайший к {preferred}, интервал ±{min_gap} мин)")
    else:
        print(f"❌ Нет свободных слотов в окне ±60 мин от {preferred}")


def register_cmd(args: list):
    """Register a new cron slot."""
    # Parse args: --id X --time HH:MM --cmd "..." [--owner X] [--priority X] [--claude N] [--apply]
    parsed = {}
    i = 0
    while i < len(args):
        if args[i] == "--id" and i + 1 < len(args):
            parsed["id"] = args[i + 1]; i += 2
        elif args[i] == "--time" and i + 1 < len(args):
            parsed["time"] = args[i + 1]; i += 2
        elif args[i] == "--cmd" and i + 1 < len(args):
            parsed["cmd"] = args[i + 1]; i += 2
        elif args[i] == "--owner" and i + 1 < len(args):
            parsed["owner"] = args[i + 1]; i += 2
        elif args[i] == "--priority" and i + 1 < len(args):
            parsed["priority"] = args[i + 1]; i += 2
        elif args[i] == "--claude" and i + 1 < len(args):
            parsed["claude"] = int(args[i + 1]); i += 2
        elif args[i] == "--apply":
            parsed["apply"] = True; i += 1
        else:
            i += 1

    if "id" not in parsed or "time" not in parsed:
        print("Usage: guardian.py register --id <name> --time <HH:MM> --cmd <command> [--owner X] [--priority X] [--claude N] [--apply]")
        sys.exit(1)

    reg = _load_registry()
    config = _load_config()
    max_total = config.get("max_total_crons", 60)
    enabled_count = len([s for s in reg["slots"] if s.get("enabled", True)])

    # Check limit
    if enabled_count >= max_total:
        print(f"⛔ Лимит достигнут: {enabled_count}/{max_total}. Удали ненужные слоты.")
        sys.exit(1)

    # Check if ID exists
    if any(s["id"] == parsed["id"] for s in reg["slots"]):
        print(f"⚠️ Слот '{parsed['id']}' уже существует. Используй unregister сначала.")
        sys.exit(1)

    # Check if time is free
    min_gap = config.get("min_interval_minutes", 2)
    occupied = _get_all_minutes(reg["slots"])
    h, m = int(parsed["time"].split(":")[0]), int(parsed["time"].split(":")[1])
    idx = h * 60 + m
    conflict = False
    for d in range(-min_gap, min_gap + 1):
        if occupied[(idx + d) % 1440]:
            conflict = True
            break

    actual_time = parsed["time"]
    if conflict:
        alt = _find_free_slot(parsed["time"], reg["slots"], min_gap=min_gap)
        if alt:
            print(f"⚠️ {parsed['time']} занято. Ближайший свободный: {alt}")
            actual_time = alt
        else:
            print(f"❌ {parsed['time']} занято и нет свободных слотов рядом.")
            sys.exit(1)

    slot = {
        "id": parsed["id"],
        "source": "crontab",
        "schedule": f"{actual_time} daily",
        "cron_expr": f"{int(actual_time.split(':')[1])} {int(actual_time.split(':')[0])} * * *",
        "timer_unit": None,
        "command": parsed.get("cmd", ""),
        "owner": parsed.get("owner", "system"),
        "priority": parsed.get("priority", "system"),
        "claude_calls": parsed.get("claude", 0),
        "enabled": True,
        "added": datetime.now().strftime("%Y-%m-%d"),
    }
    reg["slots"].append(slot)
    _save_registry(reg)

    if parsed.get("apply"):
        # Add to crontab
        try:
            result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
            current = result.stdout if result.returncode == 0 else ""
            new_line = f"{slot['cron_expr']}  {slot['command']}  # guardian:{slot['id']}"
            new_crontab = current.rstrip() + "\n" + new_line + "\n"
            subprocess.run(["crontab", "-"], input=new_crontab, text=True, check=True)
            print(f"✅ Добавлено в crontab: {new_line}")
        except Exception as e:
            print(f"⚠️ Не удалось добавить в crontab: {e}")

    new_count = len([s for s in reg["slots"] if s.get("enabled", True)])
    print(f"✅ Зарегистрирован: {slot['id']} → {actual_time} ({new_count}/{max_total})")

    # Check alert thresholds
    _check_thresholds_silent(new_count, max_total, config)


def unregister_cmd(slot_id: str, apply: bool = False):
    """Remove a slot from registry."""
    reg = _load_registry()
    found = False
    new_slots = []
    for s in reg["slots"]:
        if s["id"] == slot_id:
            found = True
            if apply and s.get("cron_expr"):
                # Remove from crontab
                try:
                    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
                    if result.returncode == 0:
                        lines = [l for l in result.stdout.split("\n")
                                 if f"guardian:{slot_id}" not in l and slot_id not in l]
                        subprocess.run(["crontab", "-"], input="\n".join(lines) + "\n", text=True, check=True)
                        print(f"🗑️ Удалено из crontab: {slot_id}")
                except Exception as e:
                    print(f"⚠️ Не удалось удалить из crontab: {e}")
        else:
            new_slots.append(s)

    if not found:
        print(f"❌ Слот '{slot_id}' не найден в реестре.")
        return

    reg["slots"] = new_slots
    _save_registry(reg)
    print(f"✅ Удалён из реестра: {slot_id}")


def _check_thresholds_silent(count: int, max_total: int, config: dict):
    """Check thresholds and send TG alert if needed (with dedup)."""
    pct = round(count / max_total * 100)
    threshold = config.get("alert_threshold_pct", 75)
    critical = config.get("alert_critical_pct", 90)

    if pct < threshold:
        return

    # Dedup: check alerts_sent.json
    today = datetime.now().strftime("%Y-%m-%d")
    alerts = {}
    if ALERTS_FILE.exists():
        try:
            alerts = json.loads(ALERTS_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            alerts = {}

    level = "critical" if pct >= critical else "warning"
    key = f"{level}_{today}"
    if key in alerts:
        return  # Already sent today

    if pct >= critical:
        msg = f"🔴 CRITICAL: Cron slots {count}/{max_total} ({pct}%). Новые задачи заблокированы!"
    else:
        msg = f"⚠️ Cron slots: {count}/{max_total} ({pct}%). Осталось {max_total - count}."

    # Send via tg-send.py
    if TG_SEND.exists():
        try:
            subprocess.run(
                ["python3", str(TG_SEND), "me", msg],
                timeout=15, capture_output=True
            )
            print(f"📨 Алерт отправлен: {msg}")
        except Exception:
            print(f"⚠️ Не удалось отправить алерт. Текст: {msg}")
    else:
        print(f"📨 Алерт (tg-send не найден): {msg}")

    alerts[key] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ALERTS_FILE.write_text(json.dumps(alerts, indent=2))


def alert_check():
    """Check thresholds and send alerts if needed."""
    reg = _load_registry()
    if not reg["slots"]:
        # Try scanning first
        reg = _scan_and_merge()

    config = _load_config()
    max_total = config.get("max_total_crons", 60)
    enabled = [s for s in reg["slots"] if s.get("enabled", True)]
    count = len(enabled)
    pct = round(count / max_total * 100)

    print(f"📊 Alert check: {count}/{max_total} ({pct}%)")
    _check_thresholds_silent(count, max_total, config)

    if pct < config.get("alert_threshold_pct", 75):
        print(f"✅ Всё в норме ({pct}% < {config.get('alert_threshold_pct', 75)}%)")


# ── CLI ─────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "status":
        status()
    elif cmd == "schedule":
        schedule()
    elif cmd == "check":
        check()
    elif cmd == "gate":
        gate()
    elif cmd == "log":
        source = sys.argv[2] if len(sys.argv) > 2 else "manual"
        log_usage(source)
    elif cmd == "report":
        days = 7
        for i, arg in enumerate(sys.argv):
            if arg == "--days" and i + 1 < len(sys.argv):
                days = int(sys.argv[i + 1])
        report(days)
    elif cmd == "optimize":
        optimize()
    elif cmd == "map":
        scan = "--scan" in sys.argv
        cron_map(scan=scan)
    elif cmd == "slot-find":
        if len(sys.argv) < 3:
            print("Usage: guardian.py slot-find <HH:MM>")
            sys.exit(1)
        slot_find_cmd(sys.argv[2])
    elif cmd == "register":
        register_cmd(sys.argv[2:])
    elif cmd == "unregister":
        if len(sys.argv) < 3:
            print("Usage: guardian.py unregister <id> [--apply]")
            sys.exit(1)
        apply = "--apply" in sys.argv
        unregister_cmd(sys.argv[2], apply=apply)
    elif cmd == "alert-check":
        alert_check()
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
