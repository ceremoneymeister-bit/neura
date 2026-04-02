#!/usr/bin/env python3
"""Smart Outreach Engine — исполняемый движок самообучения.

Функции:
  1. log_message()     — записать отправку в tracker
  2. log_correction()  — записать коррекцию
  3. log_outcome()     — записать результат (ответил/нет)
  4. update_profiles() — обновить профили из tracker данных
  5. check_triggers()  — проверить проактивные триггеры
  6. weekly_report()   — еженедельная статистика
  7. promote_corrections() — промоушен коррекций в anti-patterns

Usage:
  python3 engine.py log <recipient> <type> <clear_score>
  python3 engine.py outcome <msg_id> <outcome>
  python3 engine.py triggers [--dry-run]
  python3 engine.py report
  python3 engine.py promote
  python3 engine.py update-profiles
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
TRACKER = DATA_DIR / "tracker.jsonl"
CORRECTIONS = DATA_DIR / "corrections.jsonl"
PROFILES = DATA_DIR / "recipient-profiles.json"
ANTI_PATTERNS = BASE_DIR / "framework" / "anti-patterns.md"


def _read_jsonl(path: Path) -> list:
    """Read JSONL file, return list of dicts."""
    if not path.exists() or path.stat().st_size == 0:
        return []
    entries = []
    for line in path.read_text().strip().split("\n"):
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def _append_jsonl(path: Path, entry: dict):
    """Append one JSON line to JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _read_profiles() -> dict:
    """Read recipient profiles."""
    if PROFILES.exists():
        return json.loads(PROFILES.read_text())
    return {}


def _write_profiles(profiles: dict):
    """Write recipient profiles."""
    PROFILES.write_text(json.dumps(profiles, ensure_ascii=False, indent=2))


def _next_id(entries: list) -> str:
    """Generate next message ID."""
    if not entries:
        return "msg_001"
    last_ids = [e.get("id", "msg_000") for e in entries]
    nums = [int(x.split("_")[1]) for x in last_ids if "_" in x]
    return f"msg_{max(nums) + 1:03d}" if nums else "msg_001"


# ── 1. Log message ──────────────────────────────────────────────

def log_message(recipient: str, msg_type: str, clear_scores: dict,
                template_ver: str = "v1", preview: str = "",
                channel: str = "telethon") -> str:
    """Log sent message. Returns msg_id."""
    entries = _read_jsonl(TRACKER)
    msg_id = _next_id(entries)
    total = sum(clear_scores.values())

    entry = {
        "id": msg_id,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "recipient": recipient,
        "type": msg_type,
        "template_ver": template_ver,
        "channel": channel,
        "clear_score": clear_scores,
        "total_clear": total,
        "preview": preview[:150],
        "outcome": None,
        "outcome_date": None,
        "effective_score": None,
    }
    _append_jsonl(TRACKER, entry)

    # Update last_contact in profile
    profiles = _read_profiles()
    if recipient in profiles:
        profiles[recipient]["last_contact"] = datetime.now().strftime("%Y-%m-%d")
        _write_profiles(profiles)

    print(f"Logged: {msg_id} → {recipient} ({msg_type}) CLEAR={total}/25")
    return msg_id


# ── 2. Log correction ───────────────────────────────────────────

def log_correction(msg_type: str, original: str, corrected: str,
                   pattern: str, severity: str = "medium"):
    """Log Dmitry's correction."""
    entry = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "type": msg_type,
        "original": original[:300],
        "corrected": corrected[:300],
        "pattern": pattern,
        "severity": severity,
    }
    _append_jsonl(CORRECTIONS, entry)
    print(f"Correction logged: [{severity}] {pattern}")

    # Auto-promote high severity
    if severity == "high":
        promote_corrections()


# ── 3. Log outcome ──────────────────────────────────────────────

OUTCOME_SCORES = {
    "responded_fast": 9,
    "responded_positive": 7,
    "responded_neutral": 5,
    "responded_negative": 3,
    "no_response_48h": 2,
    "correction_needed": 1,
    "skipped": 0,
}


def log_outcome(msg_id: str, outcome: str):
    """Update message outcome in tracker."""
    entries = _read_jsonl(TRACKER)
    updated = False
    for e in entries:
        if e["id"] == msg_id:
            e["outcome"] = outcome
            e["outcome_date"] = datetime.now().strftime("%Y-%m-%d")
            e["effective_score"] = OUTCOME_SCORES.get(outcome, 5)
            updated = True
            break

    if not updated:
        print(f"Message {msg_id} not found")
        return

    # Rewrite tracker
    TRACKER.write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in entries) + "\n"
    )
    print(f"Outcome: {msg_id} → {outcome} (score={OUTCOME_SCORES.get(outcome, 5)})")

    # Update recipient profile
    entry = next((e for e in entries if e["id"] == msg_id), None)
    if entry:
        _update_profile_from_entry(entry)


def _update_profile_from_entry(entry: dict):
    """Update recipient profile from a single tracker entry."""
    profiles = _read_profiles()
    r = entry.get("recipient", "")
    if r not in profiles:
        return
    p = profiles[r]

    # Update effective_templates
    if entry.get("effective_score", 0) >= 7:
        tpl = entry.get("type", "") + "/" + entry.get("template_ver", "v1")
        if tpl not in p.get("effective_templates", []):
            p.setdefault("effective_templates", []).append(tpl)

    # Update anti_patterns from low scores
    if entry.get("effective_score", 10) <= 3:
        note = f"{entry.get('type', 'unknown')} не сработал ({entry.get('outcome', '')})"
        if note not in p.get("anti_patterns", []):
            p.setdefault("anti_patterns", []).append(note)

    _write_profiles(profiles)


# ── 4. Update profiles from tracker ────────────────────────────

def update_profiles():
    """Aggregate tracker data into recipient profiles."""
    entries = _read_jsonl(TRACKER)
    profiles = _read_profiles()

    # Group by recipient
    by_recipient = defaultdict(list)
    for e in entries:
        by_recipient[e.get("recipient", "unknown")].append(e)

    for recipient, msgs in by_recipient.items():
        if recipient not in profiles:
            continue
        p = profiles[recipient]

        # Last contact
        dates = [e["date"][:10] for e in msgs if e.get("date")]
        if dates:
            p["last_contact"] = max(dates)

        # Response rate
        with_outcome = [e for e in msgs if e.get("outcome")]
        responded = [e for e in with_outcome if "responded" in (e.get("outcome") or "")]
        if with_outcome:
            p["response_rate"] = round(len(responded) / len(with_outcome), 2)

        # Total messages
        p["total_messages"] = len(msgs)

        # Avg effective score
        scores = [e["effective_score"] for e in msgs if e.get("effective_score") is not None]
        if scores:
            p["avg_effective_score"] = round(sum(scores) / len(scores), 1)

        # Best templates (score >= 7)
        good = [e for e in msgs if (e.get("effective_score") or 0) >= 7]
        p["effective_templates"] = list(set(
            e.get("type", "") + "/" + e.get("template_ver", "v1") for e in good
        ))

    _write_profiles(profiles)
    print(f"Profiles updated: {len(by_recipient)} recipients")


# ── 5. Check proactive triggers ────────────────────────────────

def check_triggers(dry_run: bool = False) -> list:
    """Check proactive triggers. Returns list of suggested actions."""
    entries = _read_jsonl(TRACKER)
    profiles = _read_profiles()
    today = datetime.now()
    suggestions = []

    for key, profile in profiles.items():
        relation = profile.get("relation", "client")
        last = profile.get("last_contact")

        if not last:
            # Never contacted — suggest initial outreach
            if relation in ("client", "prospect"):
                suggestions.append({
                    "recipient": key,
                    "name": profile.get("name", key),
                    "trigger": "never_contacted",
                    "template": "check-in/health-check" if relation == "client" else "sales/cold-intro",
                    "urgency": "medium",
                })
            continue

        try:
            last_date = datetime.strptime(last, "%Y-%m-%d")
        except ValueError:
            continue

        days_silent = (today - last_date).days

        # Silence > 7 days for clients
        if relation == "client" and days_silent >= 7:
            # Check: did we already send 2 without response?
            recent = [e for e in entries if e.get("recipient") == key
                      and e.get("date", "")[:10] >= last]
            no_response = [e for e in recent if e.get("outcome") == "no_response_48h"]
            if len(no_response) >= 2:
                continue  # STOP rule: 2 without response

            suggestions.append({
                "recipient": key,
                "name": profile.get("name", key),
                "trigger": f"silence_{days_silent}_days",
                "template": "check-in/reactivation",
                "urgency": "high" if days_silent >= 14 else "medium",
            })

        # Lead cooling > 3 days for prospects
        if relation == "prospect" and days_silent >= 3:
            recent = [e for e in entries if e.get("recipient") == key]
            no_response = [e for e in recent if e.get("outcome") == "no_response_48h"]
            if len(no_response) >= 2:
                continue
            suggestions.append({
                "recipient": key,
                "name": profile.get("name", key),
                "trigger": f"lead_cooling_{days_silent}_days",
                "template": "sales/warm-follow-up",
                "urgency": "high" if days_silent >= 7 else "medium",
            })

    if dry_run:
        for s in suggestions:
            print(f"  [{s['urgency'].upper()}] {s['name']}: {s['trigger']} → {s['template']}")
    elif suggestions:
        print(f"\n📨 Smart Outreach — {len(suggestions)} предложений:")
        for s in suggestions:
            print(f"  [{s['urgency'].upper()}] {s['name']}: {s['trigger']} → {s['template']}")
    else:
        print("Проактивных предложений нет — все клиенты на связи.")

    return suggestions


# ── 6. Weekly report ────────────────────────────────────────────

def weekly_report() -> str:
    """Generate weekly outreach report."""
    entries = _read_jsonl(TRACKER)
    corrections = _read_jsonl(CORRECTIONS)
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    week_msgs = [e for e in entries if (e.get("date", "")[:10]) >= week_ago]
    week_corrections = [c for c in corrections if (c.get("date", "")) >= week_ago]

    if not week_msgs and not week_corrections:
        report = "За последнюю неделю сообщений не отправлялось."
        print(report)
        return report

    # Stats
    total = len(week_msgs)
    with_outcome = [e for e in week_msgs if e.get("outcome")]
    responded = [e for e in with_outcome if "responded" in (e.get("outcome") or "")]
    avg_clear = round(sum(e.get("total_clear", 0) for e in week_msgs) / max(total, 1), 1)
    scores = [e["effective_score"] for e in week_msgs if e.get("effective_score") is not None]
    avg_eff = round(sum(scores) / max(len(scores), 1), 1) if scores else "N/A"

    # Best/worst templates
    by_type = defaultdict(list)
    for e in week_msgs:
        if e.get("effective_score") is not None:
            by_type[e.get("type", "unknown")].append(e["effective_score"])

    best = max(by_type.items(), key=lambda x: sum(x[1]) / len(x[1])) if by_type else ("N/A", [0])
    worst = min(by_type.items(), key=lambda x: sum(x[1]) / len(x[1])) if by_type else ("N/A", [0])

    report = f"""📊 Smart Outreach — неделя {week_ago} → {datetime.now().strftime('%Y-%m-%d')}

Сообщений: {total}
Avg CLEAR: {avg_clear}/25
Response rate: {len(responded)}/{len(with_outcome)} ({round(len(responded)/max(len(with_outcome),1)*100)}%)
Avg effective: {avg_eff}/10
Коррекций: {len(week_corrections)}

Лучший шаблон: {best[0]} (avg={round(sum(best[1])/len(best[1]),1)})
Худший шаблон: {worst[0]} (avg={round(sum(worst[1])/len(worst[1]),1)})"""

    if len(week_corrections) > 0:
        patterns = [c.get("pattern", "") for c in week_corrections]
        report += f"\n\nПаттерны коррекций:\n" + "\n".join(f"  — {p}" for p in patterns)

    # Recommendations
    recs = []
    if avg_clear < 20:
        recs.append("CLEAR < 20 — пересмотреть шаблоны, усилить Context и Lead")
    if len(responded) < len(with_outcome) * 0.5:
        recs.append("Response rate < 50% — проверить тон и длину сообщений")
    if len(week_corrections) >= 3:
        recs.append(f"{len(week_corrections)} коррекций — запустить promote_corrections()")

    if recs:
        report += "\n\nРекомендации:\n" + "\n".join(f"  ⚠️ {r}" for r in recs)

    print(report)
    return report


# ── 7. Promote corrections to anti-patterns ────────────────────

def promote_corrections():
    """Move repeated/high-severity corrections to anti-patterns.md."""
    corrections = _read_jsonl(CORRECTIONS)
    if not corrections:
        print("No corrections to promote.")
        return

    # Find high-severity or repeated patterns
    pattern_counts = defaultdict(int)
    high_severity = []
    for c in corrections:
        pattern_counts[c.get("pattern", "")] += 1
        if c.get("severity") == "high":
            high_severity.append(c)

    repeated = [p for p, count in pattern_counts.items() if count >= 2 and p]
    to_promote = list(set(
        [c.get("pattern", "") for c in high_severity] + repeated
    ))

    if not to_promote:
        print("No patterns to promote (need severity=high or 2+ repeats).")
        return

    # Read current anti-patterns
    content = ANTI_PATTERNS.read_text() if ANTI_PATTERNS.exists() else ""

    # Check which patterns are already there
    new_patterns = [p for p in to_promote if p and p not in content]
    if not new_patterns:
        print("All patterns already in anti-patterns.md.")
        return

    # Append to "Паттерны из коррекций" section
    today = datetime.now().strftime("%Y-%m-%d")
    additions = "\n".join(
        f"{today} — \"{p}\" — автопромоушен из corrections.jsonl"
        for p in new_patterns
    )

    if "Паттерны из коррекций" in content:
        # Remove comment block and add real entries
        content = content.replace(
            "<!-- Пример:\n"
            "2026-03-25 — \"убрать 'надеюсь' из check-in\" — слово создаёт неуверенность, заменять на прямой вопрос\n"
            "2026-03-26 — \"Виктории писать короче\" — она отвечает быстро на 2-3 предложения, игнорирует длинные\n"
            "-->", ""
        )
        content = content.rstrip() + "\n" + additions + "\n"
    else:
        content += f"\n\n## Паттерны из коррекций\n\n{additions}\n"

    ANTI_PATTERNS.write_text(content)
    print(f"Promoted {len(new_patterns)} patterns to anti-patterns.md")


# ── 8. Time-of-day safety ──────────────────────────────────────

def is_safe_to_send(tz_offset: int = 3) -> tuple:
    """Check if current time is appropriate for sending.
    Returns (is_safe, reason)."""
    from datetime import timezone as tz
    now = datetime.now(tz(timedelta(hours=tz_offset)))
    hour = now.hour

    if hour < 8:
        return False, f"Слишком рано ({hour}:00). Безопасное время: 08:00–21:00"
    if hour >= 22:
        return False, f"Слишком поздно ({hour}:00). Безопасное время: 08:00–21:00"
    return True, "OK"


# ── CLI ─────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "log" and len(sys.argv) >= 5:
        recipient = sys.argv[2]
        msg_type = sys.argv[3]
        # Parse CLEAR scores: "C=5,L=4,E=5,A=4,R=5"
        scores_raw = sys.argv[4]
        scores = {}
        for pair in scores_raw.split(","):
            k, v = pair.split("=")
            scores[k.strip()] = int(v.strip())
        template_ver = sys.argv[5] if len(sys.argv) > 5 else "v1"
        channel = sys.argv[6] if len(sys.argv) > 6 else "telethon"
        log_message(recipient, msg_type, scores, template_ver, channel=channel)

    elif cmd == "outcome" and len(sys.argv) >= 4:
        log_outcome(sys.argv[2], sys.argv[3])

    elif cmd == "triggers":
        dry_run = "--dry-run" in sys.argv
        check_triggers(dry_run)

    elif cmd == "report":
        weekly_report()

    elif cmd == "promote":
        promote_corrections()

    elif cmd == "update-profiles":
        update_profiles()

    elif cmd == "time-check":
        tz = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        safe, reason = is_safe_to_send(tz)
        print(f"{'✅' if safe else '⛔'} {reason}")

    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
