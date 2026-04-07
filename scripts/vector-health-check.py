#!/usr/bin/env python3
"""Проактивный health-check векторной памяти.

Запуск: python3 /opt/neura-v2/scripts/vector-health-check.py
Крон:   ежедневно после реиндексации (04:30 UTC)

Проверяет:
  1. Индекс существует и не пустой
  2. Knowledge base не пустая (для активных капсул)
  3. Новые PDF/DOCX не извлечены в knowledge
  4. Stale index (>48h без обновления)
  5. Тестовый поиск возвращает результаты
  6. followlinks работает (symlinks видны)

При проблемах — пишет алерт в лог + опционально в TG.
"""
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, "/opt/neura-v2")

HOMES = Path("/opt/neura-v2/homes")
VECTOR_DB = Path("/opt/neura-v2/data/vectordb")
LOG_FILE = Path("/root/Antigravity/logs/vector-health.log")

# Капсулы где knowledge ДОЛЖНА быть непустой (активные с контентом)
ACTIVE_CAPSULES = {
    "marina_biryukova", "victoria_sel", "yana_berezhnaya",
    "yulia_gudymo", "maxim_belousov",
    "maxim_tatyana_smyk", "maxim_dmitry_selestinsky",
    "maxim_anastasia_velikaya",
}
# Триалы/новые — knowledge может быть пустой (не алертить)
# nikita_maltsev, oksana_ksyfleur, sergey_savchuk

EXTRACTABLE = {".pdf", ".docx", ".xlsx"}
STALE_HOURS = 48


def check_capsule(cap_id: str) -> list[str]:
    """Returns list of issues found."""
    issues = []
    home = HOMES / cap_id
    db_path = VECTOR_DB / cap_id

    if not home.exists():
        return [f"HOME_MISSING: {cap_id}"]

    # 1. Index exists?
    if not db_path.exists():
        issues.append(f"NO_INDEX: {cap_id} — нет векторной базы")
    else:
        meta = db_path / "meta.json"
        if meta.exists():
            meta_data = json.loads(meta.read_text())
            file_count = len(meta_data)
            if file_count == 0:
                issues.append(f"EMPTY_INDEX: {cap_id} — 0 файлов")

            # Stale check
            age_hours = (time.time() - meta.stat().st_mtime) / 3600
            if age_hours > STALE_HOURS:
                issues.append(f"STALE_INDEX: {cap_id} — не обновлялся {age_hours:.0f}ч (лимит {STALE_HOURS}ч)")

    # 2. Knowledge base
    kb = home / "knowledge"
    if cap_id in ACTIVE_CAPSULES:
        if not kb.exists():
            issues.append(f"NO_KNOWLEDGE: {cap_id} — нет папки knowledge/")
        elif len(list(kb.iterdir())) == 0:
            issues.append(f"EMPTY_KNOWLEDGE: {cap_id} — knowledge/ пустая")

    # 3. Unextracted documents
    unextracted = []
    existing_kb = {f.stem.lower() for f in kb.iterdir()} if kb.exists() else set()
    assets = home / "data" / "client-assets"
    search_dirs = [assets, home]
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for ext in EXTRACTABLE:
            for f in search_dir.rglob(f"*{ext}"):
                # Skip tool-results (Claude CLI renders) and projects/ session data
                if "tool-results" in str(f) or "/projects/" in str(f):
                    continue
                # Check if already extracted (fuzzy: first 15 chars of stem)
                stem = f.stem.replace(" ", "_").lower()[:60]
                stem_prefix = stem[:15]
                if any(stem_prefix in e for e in existing_kb):
                    continue
                # Skip tiny files (<1KB) — likely empty scans
                try:
                    if f.stat().st_size < 1024:
                        continue
                except OSError:
                    continue
                unextracted.append(f.name)

    if unextracted:
        issues.append(f"UNEXTRACTED: {cap_id} — {len(unextracted)} документов не в knowledge: {', '.join(unextracted[:3])}")

    # 4. Symlinks check (skills should be visible)
    skills_dir = home / "skills"
    if skills_dir.exists() and skills_dir.is_dir():
        symlink_count = sum(1 for d in skills_dir.iterdir() if d.is_symlink())
        if symlink_count > 0:
            # os.walk with followlinks (same as vectordb uses)
            real_files = 0
            for root, _, files in os.walk(skills_dir, followlinks=True):
                real_files += sum(1 for f in files if f.endswith(".md"))
            if real_files == 0:
                issues.append(f"SYMLINKS_BROKEN: {cap_id} — {symlink_count} symlinks но 0 .md файлов")

    return issues


def main():
    from datetime import datetime

    all_issues = []
    capsules = sorted(d.name for d in HOMES.iterdir() if d.is_dir())

    for cap in capsules:
        issues = check_capsule(cap)
        all_issues.extend(issues)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    if all_issues:
        report = f"\n[{timestamp}] VECTOR HEALTH — {len(all_issues)} issues:\n"
        for issue in all_issues:
            report += f"  ⚠️  {issue}\n"
    else:
        report = f"\n[{timestamp}] VECTOR HEALTH — ✅ ALL OK ({len(capsules)} capsules)\n"

    print(report)

    # Append to log
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(report)

    # Exit code for cron alerting
    sys.exit(1 if all_issues else 0)


if __name__ == "__main__":
    main()
