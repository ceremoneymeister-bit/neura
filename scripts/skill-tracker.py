#!/usr/bin/env python3
"""Skill Compound Engine v2 — Tracker + Verifier.

Commands:
  use <name>       — snapshot content hash + increment usage counter
  verify <name>    — check if content actually changed since snapshot (EXIT 1 if not)
  verify-all       — verify all skills with pending snapshots
  status           — table of all skills
  audit            — find legacy/unused/never-evolved skills
  report           — summary report
  add-changelog    — add ## Changelog section to skills that don't have one

Zero external dependencies (stdlib only).
"""

import os, sys, re, datetime, hashlib, json

SKILLS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".agent", "skills")
SNAPSHOTS_FILE = os.path.join(SKILLS_DIR, "_snapshots.json")
TODAY = datetime.date.today().isoformat()
MATURITY_THRESHOLDS = {"seed": (0, 2), "tested": (3, 5), "mature": (6, float("inf"))}
LEGACY_DAYS = 60
CHANGELOG_HEADER = "\n\n---\n\n## Changelog\n\n<!-- Сюда автоматически добавляются уроки после каждого использования скилла -->\n"


def load_snapshots():
    if os.path.isfile(SNAPSHOTS_FILE):
        with open(SNAPSHOTS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_snapshots(data):
    with open(SNAPSHOTS_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def content_hash(path):
    """Hash of SKILL.md content EXCLUDING frontmatter (usage_count, last_used, maturity lines)."""
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    # Remove frontmatter block entirely for hashing
    text_no_fm = re.sub(r"^---\n.*?\n---\n?", "", text, count=1, flags=re.DOTALL)
    return hashlib.sha256(text_no_fm.encode()).hexdigest()[:16]


def parse_frontmatter(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return None, text
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            val = val.strip().strip('"').strip("'")
            if val == "null" or val == "":
                val = None
            elif val.isdigit():
                val = int(val)
            fm[key.strip()] = val
    return fm, text


def write_frontmatter(path, fm, text):
    lines = []
    for k, v in fm.items():
        if v is None:
            lines.append(f"{k}: null")
        elif isinstance(v, int):
            lines.append(f"{k}: {v}")
        else:
            lines.append(f"{k}: {v}")
    new_fm = "---\n" + "\n".join(lines) + "\n---"
    new_text = re.sub(r"^---\n.*?\n---", new_fm, text, count=1, flags=re.DOTALL)
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_text)


def calc_maturity(count, last_used):
    if last_used and last_used != "null":
        try:
            delta = (datetime.date.today() - datetime.date.fromisoformat(str(last_used))).days
            if delta > LEGACY_DAYS:
                return "legacy"
        except ValueError:
            pass
    count = int(count) if count else 0
    for level, (lo, hi) in MATURITY_THRESHOLDS.items():
        if lo <= count <= hi:
            return level
    return "seed"


def has_changelog(path):
    with open(path, "r", encoding="utf-8") as f:
        return bool(re.search(r"^## Changelog", f.read(), re.MULTILINE))


def iter_skills():
    for entry in sorted(os.listdir(SKILLS_DIR)):
        if entry.startswith("_"):
            continue
        p = os.path.join(SKILLS_DIR, entry, "SKILL.md")
        if os.path.isfile(p):
            yield entry, p


# ── Commands ──────────────────────────────────────────────


def cmd_use(name):
    """Snapshot content hash + increment counter. Call BEFORE working with skill."""
    path = os.path.join(SKILLS_DIR, name, "SKILL.md")
    if not os.path.isfile(path):
        print(f"ERROR: skill '{name}' not found at {path}")
        sys.exit(1)

    # Save snapshot of current content
    snapshots = load_snapshots()
    h = content_hash(path)
    snapshots[name] = {"hash": h, "date": TODAY}
    save_snapshots(snapshots)

    # Update frontmatter
    fm, text = parse_frontmatter(path)
    if fm is None:
        print(f"ERROR: no frontmatter in {path}")
        sys.exit(1)
    count = int(fm.get("usage_count", 0)) + 1
    fm["usage_count"] = count
    fm["last_used"] = TODAY
    fm["maturity"] = calc_maturity(count, TODAY)
    write_frontmatter(path, fm, text)

    # Check if Changelog section exists
    has_cl = has_changelog(path)

    print(f"OK: {name} → usage={count}, snapshot={h}")
    if not has_cl:
        print(f"WARNING: {name} не имеет секции ## Changelog. Добавь: `skill-tracker.py add-changelog {name}`")
    print(f"НАПОМИНАНИЕ: после работы вызови `skill-tracker.py verify {name}` чтобы подтвердить обновление")


def cmd_verify(name):
    """Verify that skill content actually changed since snapshot. EXIT 1 if not."""
    path = os.path.join(SKILLS_DIR, name, "SKILL.md")
    if not os.path.isfile(path):
        print(f"ERROR: skill '{name}' not found")
        sys.exit(1)

    snapshots = load_snapshots()
    if name not in snapshots:
        print(f"WARNING: нет snapshot для '{name}'. Невозможно верифицировать.")
        print("Подсказка: вызови `skill-tracker.py use {name}` ПЕРЕД работой.")
        sys.exit(1)

    old_hash = snapshots[name]["hash"]
    new_hash = content_hash(path)

    if old_hash == new_hash:
        print(f"FAIL: {name} — содержимое НЕ изменилось (hash={old_hash})")
        print(f"Скилл заявлен как 'обновлён', но реально ничего не поменялось.")
        print(f"Что нужно сделать:")
        print(f"  1. Открой .agent/skills/{name}/SKILL.md")
        print(f"  2. Добавь урок в ## Changelog: что узнал, что сработало/не сработало")
        print(f"  3. ИЛИ исправь workflow/антипаттерны если нашёл проблему")
        print(f"  4. Повтори verify")
        sys.exit(1)
    else:
        # Clear snapshot on success
        del snapshots[name]
        save_snapshots(snapshots)
        print(f"OK: {name} — содержимое РЕАЛЬНО обновлено (old={old_hash} → new={new_hash})")
        sys.exit(0)


def cmd_verify_all():
    """Verify all skills with pending snapshots."""
    snapshots = load_snapshots()
    if not snapshots:
        print("Нет pending snapshots. Все скиллы верифицированы или не использовались.")
        return

    passed, failed = [], []
    for name, snap in list(snapshots.items()):
        path = os.path.join(SKILLS_DIR, name, "SKILL.md")
        if not os.path.isfile(path):
            failed.append((name, "файл не найден"))
            continue

        new_hash = content_hash(path)
        if snap["hash"] == new_hash:
            failed.append((name, f"не изменён с {snap['date']}"))
        else:
            passed.append(name)
            del snapshots[name]

    save_snapshots(snapshots)

    print("=== VERIFY ALL ===\n")
    if passed:
        print(f"РЕАЛЬНО обновлены ({len(passed)}):")
        for n in passed:
            print(f"  ✓ {n}")
    if failed:
        print(f"\nНЕ обновлены ({len(failed)}):")
        for n, reason in failed:
            print(f"  ✗ {n} — {reason}")

    if failed:
        sys.exit(1)


def cmd_status():
    snapshots = load_snapshots()
    header = f"{'Skill':<35} {'Uses':>5} {'Maturity':<8} {'Last Used':<12} {'Pending':>7}"
    print(header)
    print("-" * len(header))
    for name, path in iter_skills():
        fm, _ = parse_frontmatter(path)
        if fm is None:
            count, mat, lu = 0, "?", "no-fm"
        else:
            count = fm.get("usage_count", "-")
            lu = fm.get("last_used") or "-"
            mat = fm.get("maturity") or calc_maturity(count if isinstance(count, int) else 0, lu)
        pending = "YES" if name in snapshots else ""
        print(f"{name:<35} {str(count):>5} {str(mat):<8} {str(lu):<12} {pending:>7}")


def cmd_audit():
    no_fm, unused, legacy, no_changelog, never_evolved = [], [], [], [], []
    snapshots = load_snapshots()

    for name, path in iter_skills():
        fm, text = parse_frontmatter(path)
        if fm is None:
            no_fm.append(name)
            continue

        count = int(fm.get("usage_count", 0))
        lu = fm.get("last_used")
        mat = calc_maturity(count, lu)

        if count == 0:
            unused.append(name)
        if mat == "legacy":
            legacy.append((name, lu))
        if not has_changelog(path):
            no_changelog.append(name)

        # "Never evolved" = used 2+ times but Changelog has no real entries
        if count >= 2:
            cl_match = re.search(r"## Changelog\s*\n(.*)", text, re.DOTALL)
            if cl_match:
                content = cl_match.group(1).strip()
                # Strip HTML comments to check for real content
                content_clean = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL).strip()
                if not content_clean:
                    never_evolved.append((name, count))
            else:
                never_evolved.append((name, count))

    print("=== AUDIT REPORT ===\n")

    print(f"No frontmatter ({len(no_fm)}):")
    for n in no_fm:
        print(f"  - {n}")

    print(f"\nUnused / count=0 ({len(unused)}):")
    for n in unused:
        print(f"  - {n}")

    print(f"\nLegacy / last_used > {LEGACY_DAYS} days ({len(legacy)}):")
    for n, lu in legacy:
        print(f"  - {n} (last: {lu})")

    print(f"\nНет секции ## Changelog ({len(no_changelog)}):")
    for n in no_changelog:
        print(f"  - {n}")

    print(f"\n⚠️  Использованы 2+ раз, но НЕ эволюционировали ({len(never_evolved)}):")
    for n, c in never_evolved:
        print(f"  - {n} ({c} uses, changelog пуст)")

    pending = load_snapshots()
    if pending:
        print(f"\nPending верификация ({len(pending)}):")
        for n, s in pending.items():
            print(f"  - {n} (snapshot от {s['date']})")


def cmd_report():
    total = seeds = tested = mature = legacy_count = no_fm = with_changelog = 0
    for name, path in iter_skills():
        total += 1
        fm, _ = parse_frontmatter(path)
        if fm is None:
            no_fm += 1
            continue
        if has_changelog(path):
            with_changelog += 1
        count = int(fm.get("usage_count", 0))
        mat = calc_maturity(count, fm.get("last_used"))
        if mat == "seed":
            seeds += 1
        elif mat == "tested":
            tested += 1
        elif mat == "mature":
            mature += 1
        elif mat == "legacy":
            legacy_count += 1

    print("╔══════════════════════════════════════╗")
    print("║   SKILL COMPOUND ENGINE v2 REPORT    ║")
    print("╠══════════════════════════════════════╣")
    print(f"║  Total skills:      {total:<16} ║")
    print(f"║  Seed:              {seeds:<16} ║")
    print(f"║  Tested:            {tested:<16} ║")
    print(f"║  Mature:            {mature:<16} ║")
    print(f"║  Legacy:            {legacy_count:<16} ║")
    print(f"║  No frontmatter:    {no_fm:<16} ║")
    print(f"║  With ## Changelog: {with_changelog:<16} ║")
    print(f"║  Without Changelog: {total - with_changelog - no_fm:<16} ║")
    print("╚══════════════════════════════════════╝")


def cmd_add_changelog(name=None):
    """Add ## Changelog section to skill(s) that don't have one."""
    targets = []
    if name:
        path = os.path.join(SKILLS_DIR, name, "SKILL.md")
        if not os.path.isfile(path):
            print(f"ERROR: skill '{name}' not found"); sys.exit(1)
        targets = [(name, path)]
    else:
        targets = list(iter_skills())

    added = 0
    for n, p in targets:
        if has_changelog(p):
            continue
        with open(p, "r", encoding="utf-8") as f:
            text = f.read()
        # Append changelog section at the end
        text = text.rstrip() + CHANGELOG_HEADER
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        added += 1
        print(f"  + {n}")

    print(f"\nДобавлено ## Changelog: {added} скиллов")


def cmd_evolve_check():
    """Check which skills have reached evolve_threshold and need structured update."""
    ready = []
    for name, path in iter_skills():
        fm, text = parse_frontmatter(path)
        if fm is None:
            continue
        count = int(fm.get("usage_count", 0))
        threshold = int(fm.get("learning_evolve_threshold", 5))
        if count >= threshold:
            # Check if Changelog has real entries (not just comment)
            cl_match = re.search(r"## Changelog\s*\n(.*)", text, re.DOTALL)
            has_entries = False
            if cl_match:
                content = cl_match.group(1).strip()
                # Remove HTML comments
                content = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL).strip()
                has_entries = len(content) > 10
            ready.append((name, count, threshold, has_entries))

    if not ready:
        print("Нет скиллов, достигших evolve_threshold.")
        return

    print(f"=== EVOLVE CHECK — скиллы готовы к обновлению ===\n")
    for name, count, threshold, has_entries in ready:
        status = "Changelog есть" if has_entries else "⚠️  Changelog ПУСТ"
        print(f"  {name}: {count}/{threshold} uses — {status}")

    no_entries = [n for n, _, _, h in ready if not h]
    if no_entries:
        print(f"\n⚠️  {len(no_entries)} скиллов достигли порога, но Changelog пуст:")
        print("Это значит скилл использовался много раз, но ни один урок не записан.")
        print("Рекомендация: при следующем использовании — обязательно добавить записи.")


# ── Main ──────────────────────────────────────────────────

USAGE = """Usage: skill-tracker.py <command> [args]

  use <name>       — snapshot + increment (вызывай ПЕРЕД работой со скиллом)
  verify <name>    — проверить что содержимое РЕАЛЬНО изменилось
  verify-all       — проверить все pending скиллы
  evolve-check     — показать скиллы, достигшие порога обновления
  status           — таблица всех скиллов
  audit            — найти проблемные скиллы
  report           — сводный отчёт
  add-changelog    — добавить ## Changelog в скиллы без него
  add-changelog <name> — добавить ## Changelog в конкретный скилл
"""

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(USAGE)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "use":
        if len(sys.argv) < 3:
            print("ERROR: specify skill name"); sys.exit(1)
        cmd_use(sys.argv[2])
    elif cmd == "verify":
        if len(sys.argv) < 3:
            print("ERROR: specify skill name"); sys.exit(1)
        cmd_verify(sys.argv[2])
    elif cmd == "verify-all":
        cmd_verify_all()
    elif cmd == "evolve-check":
        cmd_evolve_check()
    elif cmd == "status":
        cmd_status()
    elif cmd == "audit":
        cmd_audit()
    elif cmd == "report":
        cmd_report()
    elif cmd == "add-changelog":
        cmd_add_changelog(sys.argv[2] if len(sys.argv) > 2 else None)
    else:
        print(f"Unknown command: {cmd}")
        print(USAGE)
        sys.exit(1)
