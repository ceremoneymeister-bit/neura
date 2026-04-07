#!/usr/bin/env python3
"""Error Tracker — сборщик и агрегатор ошибок со всех источников.

Источники:
  1. journalctl (systemd services: victoria-bot, nagrada-bot, cm-listener, etc.)
  2. Cron logs (${NEURA_BASE}/logs/*.log, /tmp/*.log)
  3. Docker logs (yulia-gudymo-bot)
  4. Claude CLI stderr (если пишется в лог)

Usage:
  python3 collector.py collect [--hours 24] [--save]
  python3 collector.py report [--hours 24]
  python3 collector.py patterns [--min-count 3]
  python3 collector.py top [--limit 10]
"""

import json
import sys
import re
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict, Counter

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
ERRORS_FILE = DATA_DIR / "errors.jsonl"
PATTERNS_FILE = DATA_DIR / "error_patterns.json"

# ── Sources config ──────────────────────────────────────────────

SERVICES = [
    "victoria-bot",
    "nagrada-bot",
    "cm-listener",
    "neura-app-bridge",
    "webchat",
    "hq-bot",
]

DOCKER_CONTAINERS = [
    "yulia-gudymo-bot",
]

_BASE = os.environ.get("NEURA_BASE", "/opt/neura-v2")
CRON_LOGS = [
    f"{_BASE}/logs/reminders.log",
    f"{_BASE}/logs/tasks-sync.log",
    f"{_BASE}/logs/autopilot.log",
    f"{_BASE}/logs/google-oauth-reminder.log",
]

TMP_LOGS = [
    "/tmp/sync-tasks.log",
    "/tmp/nagrada_*.log",
]

# Error signatures — patterns that indicate real errors (not noise)
ERROR_SIGNATURES = [
    (r"error|ошибка|failed|exception|traceback|critical", "error"),
    (r"timeout|timed?\s*out", "timeout"),
    (r"oom|killed|sigkill|sigterm|memory", "crash"),
    (r"permission|denied|forbidden|401|403", "auth"),
    (r"connection\s*(refused|reset|closed)|ECONNR", "connection"),
    (r"database.*locked|locked|sqlite.*lock", "lock"),
    (r"rate.limit|429|too.many.requests|hit.your.limit", "rate_limit"),
    (r"conflict|409|already.in.use", "conflict"),
    (r"not.found|404|no.such.file", "not_found"),
    (r"disk.*full|no.space|ENOSPC", "disk"),
]

# Noise — skip these lines
NOISE_PATTERNS = [
    r"INFO",
    r"DEBUG",
    r"GET /api|POST /api|HTTP/1\.",
    r"sysstat",
    r"CRON\[",
    r"pam_unix",
    r"session opened|session closed",
]


def _classify_error(line: str) -> str:
    """Classify error line into category."""
    line_lower = line.lower()
    for pattern, category in ERROR_SIGNATURES:
        if re.search(pattern, line_lower):
            return category
    return "unknown"


def _is_noise(line: str) -> bool:
    """Check if line is noise (not a real error)."""
    for pattern in NOISE_PATTERNS:
        if re.search(pattern, line):
            return True
    return False


def _normalize_error(line: str) -> str:
    """Normalize error for dedup (remove timestamps, IDs, paths)."""
    # Remove timestamps
    line = re.sub(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[.\d]*Z?', '<TIME>', line)
    # Remove hex/uuid
    line = re.sub(r'[0-9a-f]{8,}', '<ID>', line)
    # Remove numbers > 4 digits (likely IDs, not error codes)
    line = re.sub(r'\b\d{5,}\b', '<NUM>', line)
    # Remove file paths
    line = re.sub(r'/[\w/.-]+\.py', '<FILE>.py', line)
    line = re.sub(r'line \d+', 'line <N>', line)
    return line.strip()[:200]


# ── Collect from sources ────────────────────────────────────────

def _collect_journalctl(hours: int = 24) -> list:
    """Collect errors from systemd services."""
    errors = []
    since = f"{hours} hours ago"

    for service in SERVICES:
        try:
            result = subprocess.run(
                ["journalctl", "-u", service, "--since", since,
                 "--no-pager", "-q", "--output=short-iso"],
                capture_output=True, text=True, timeout=10
            )
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                if _is_noise(line):
                    continue
                line_lower = line.lower()
                if any(re.search(p, line_lower) for p, _ in ERROR_SIGNATURES):
                    errors.append({
                        "source": f"systemd:{service}",
                        "line": line.strip()[:500],
                        "category": _classify_error(line),
                        "normalized": _normalize_error(line),
                    })
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue

    return errors


def _collect_docker(hours: int = 24) -> list:
    """Collect errors from Docker containers."""
    errors = []
    since = f"{hours}h"

    for container in DOCKER_CONTAINERS:
        try:
            result = subprocess.run(
                ["docker", "logs", container, "--since", since, "--tail", "500"],
                capture_output=True, text=True, timeout=10
            )
            # Docker outputs to stderr
            output = result.stderr + result.stdout
            for line in output.strip().split("\n"):
                if not line.strip():
                    continue
                if _is_noise(line):
                    continue
                line_lower = line.lower()
                if any(re.search(p, line_lower) for p, _ in ERROR_SIGNATURES):
                    errors.append({
                        "source": f"docker:{container}",
                        "line": line.strip()[:500],
                        "category": _classify_error(line),
                        "normalized": _normalize_error(line),
                    })
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue

    return errors


def _collect_logs(hours: int = 24) -> list:
    """Collect errors from log files."""
    errors = []
    cutoff = datetime.now() - timedelta(hours=hours)

    import glob
    all_logs = list(CRON_LOGS)
    for pattern in TMP_LOGS:
        all_logs.extend(glob.glob(pattern))

    for log_path in all_logs:
        p = Path(log_path)
        if not p.exists():
            continue
        # Skip old files
        try:
            if datetime.fromtimestamp(p.stat().st_mtime) < cutoff:
                continue
        except OSError:
            continue

        try:
            content = p.read_text(errors="replace")
            for line in content.strip().split("\n")[-200:]:  # Last 200 lines
                if not line.strip():
                    continue
                if _is_noise(line):
                    continue
                line_lower = line.lower()
                if any(re.search(p_re, line_lower) for p_re, _ in ERROR_SIGNATURES):
                    errors.append({
                        "source": f"log:{p.name}",
                        "line": line.strip()[:500],
                        "category": _classify_error(line),
                        "normalized": _normalize_error(line),
                    })
        except Exception:
            continue

    return errors


# ── Main commands ───────────────────────────────────────────────

def collect(hours: int = 24, save: bool = True) -> list:
    """Collect all errors from all sources."""
    all_errors = []

    print(f"Сбор ошибок за {hours}ч...")
    journal_errors = _collect_journalctl(hours)
    docker_errors = _collect_docker(hours)
    log_errors = _collect_logs(hours)

    all_errors = journal_errors + docker_errors + log_errors

    # Add timestamp
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    for e in all_errors:
        e["collected_at"] = now

    print(f"  systemd: {len(journal_errors)}")
    print(f"  docker:  {len(docker_errors)}")
    print(f"  logs:    {len(log_errors)}")
    print(f"  ИТОГО:   {len(all_errors)}")

    if save and all_errors:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(ERRORS_FILE, "a") as f:
            for e in all_errors:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
        print(f"  Сохранено в {ERRORS_FILE}")

    return all_errors


def report(hours: int = 24):
    """Generate error report."""
    errors = collect(hours, save=True)

    if not errors:
        print("\n✅ За последние {hours}ч ошибок не обнаружено.")
        return

    # Group by category
    by_category = defaultdict(list)
    for e in errors:
        by_category[e["category"]].append(e)

    # Group by source
    by_source = defaultdict(int)
    for e in errors:
        by_source[e["source"]] += 1

    print(f"\n📊 Error Report — {len(errors)} ошибок за {hours}ч\n")

    print("По категориям:")
    for cat, errs in sorted(by_category.items(), key=lambda x: len(x[1]), reverse=True):
        icon = {"error": "❌", "timeout": "⏱", "crash": "💀", "auth": "🔐",
                "connection": "🔌", "lock": "🔒", "rate_limit": "🚫",
                "conflict": "⚡", "not_found": "❓", "disk": "💾"}.get(cat, "⚪")
        print(f"  {icon} {cat}: {len(errs)}")

    print("\nПо источникам:")
    for source, count in sorted(by_source.items(), key=lambda x: x[1], reverse=True):
        print(f"  {source}: {count}")

    # Top 5 unique errors
    print("\nТоп-5 уникальных ошибок:")
    normalized = Counter(e["normalized"] for e in errors)
    for err, count in normalized.most_common(5):
        src = next(e["source"] for e in errors if e["normalized"] == err)
        print(f"  [{count}x] ({src}) {err[:100]}")


def find_patterns(min_count: int = 3):
    """Find recurring error patterns across all collected data."""
    if not ERRORS_FILE.exists() or ERRORS_FILE.stat().st_size == 0:
        print("Нет данных. Запустите: python3 collector.py collect")
        return

    entries = []
    for line in ERRORS_FILE.read_text().strip().split("\n"):
        if line.strip():
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if not entries:
        print("Нет записей об ошибках.")
        return

    # Group by normalized error
    by_normalized = defaultdict(list)
    for e in entries:
        by_normalized[e.get("normalized", "")].append(e)

    patterns = []
    for norm, errs in by_normalized.items():
        if len(errs) >= min_count:
            sources = list(set(e["source"] for e in errs))
            categories = list(set(e["category"] for e in errs))
            dates = sorted(set(e.get("collected_at", "")[:10] for e in errs))
            patterns.append({
                "pattern": norm,
                "count": len(errs),
                "sources": sources,
                "categories": categories,
                "dates": dates,
                "example": errs[0]["line"][:200],
            })

    patterns.sort(key=lambda x: x["count"], reverse=True)

    if not patterns:
        print(f"Паттернов с {min_count}+ повторами не найдено.")
        return

    # Save
    PATTERNS_FILE.write_text(json.dumps(patterns, ensure_ascii=False, indent=2))

    print(f"\n🔄 Error Patterns — {len(patterns)} повторяющихся ошибок (≥{min_count}x)\n")
    for i, p in enumerate(patterns[:15], 1):
        icon = "🔴" if p["count"] >= 10 else "🟡" if p["count"] >= 5 else "⚪"
        print(f"  {icon} [{p['count']}x] {p['pattern'][:80]}")
        print(f"     Источники: {', '.join(p['sources'])}")
        print(f"     Категории: {', '.join(p['categories'])}")
        print()


def top_errors(limit: int = 10):
    """Show top errors by frequency."""
    if not ERRORS_FILE.exists() or ERRORS_FILE.stat().st_size == 0:
        print("Нет данных. Запустите: python3 collector.py collect")
        return

    entries = []
    for line in ERRORS_FILE.read_text().strip().split("\n"):
        if line.strip():
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    normalized = Counter(e.get("normalized", "") for e in entries)
    print(f"\n🏆 Top-{limit} ошибок (все время):\n")
    for err, count in normalized.most_common(limit):
        src = next((e["source"] for e in entries if e.get("normalized") == err), "?")
        cat = next((e["category"] for e in entries if e.get("normalized") == err), "?")
        print(f"  [{count}x] ({cat}) {src}")
        print(f"    {err[:120]}")
        print()


# ── CLI ─────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "collect":
        hours = 24
        save = "--save" in sys.argv
        for i, arg in enumerate(sys.argv):
            if arg == "--hours" and i + 1 < len(sys.argv):
                hours = int(sys.argv[i + 1])
        collect(hours, save)

    elif cmd == "report":
        hours = 24
        for i, arg in enumerate(sys.argv):
            if arg == "--hours" and i + 1 < len(sys.argv):
                hours = int(sys.argv[i + 1])
        report(hours)

    elif cmd == "patterns":
        min_count = 3
        for i, arg in enumerate(sys.argv):
            if arg == "--min-count" and i + 1 < len(sys.argv):
                min_count = int(sys.argv[i + 1])
        find_patterns(min_count)

    elif cmd == "top":
        limit = 10
        for i, arg in enumerate(sys.argv):
            if arg == "--limit" and i + 1 < len(sys.argv):
                limit = int(sys.argv[i + 1])
        top_errors(limit)

    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
