#!/usr/bin/env python3
"""Extract SPO triples from diary entries into knowledge_graph.

Extracts facts using pattern matching (no LLM calls).
Safe to run multiple times — deduplicates by (capsule_id, subject, predicate, object).

Usage:
    python3 scripts/extract-facts.py              # process last 7 days
    python3 scripts/extract-facts.py --days 30    # process last 30 days
    python3 scripts/extract-facts.py --dry-run    # show what would be extracted
"""

import asyncio
import re
import sys
import os
from datetime import timedelta

sys.path.insert(0, "/opt/neura-v2")

# Patterns for fact extraction from diary bot_summary fields
# Format: (compiled_regex, subject_group, predicate, object_group)
PATTERNS = [
    # Сайт: domain.com (strict URL pattern)
    (re.compile(r"(?:^|\s)сайт[:\s]+([a-zA-Z0-9][a-zA-Z0-9.-]+\.[a-zA-Z]{2,6})\b", re.I),
     None, "имеет_сайт", 1),
    # Канал @username (strict TG username)
    (re.compile(r"(?:^|\s)канал\s+(@[a-zA-Z]\w{3,31})\b", re.I),
     None, "имеет_канал", 1),
    # Бот @username_bot
    (re.compile(r"бот\s+(@\w{3,31}_bot)\b", re.I),
     None, "имеет_бот", 1),
    # Цена/стоимость с числами + валюта
    (re.compile(r"(?:цена|стоимость|оплата|тариф)[:\s]+(\d[\d\s]{0,10}(?:руб|₽|р\.)\S{0,5})", re.I),
     None, "цена", 1),
    # Дата/дедлайн (strict date format)
    (re.compile(r"(?:дедлайн|запуск|старт)[:\s]+(\d{1,2}[./]\d{1,2}[./]\d{2,4})", re.I),
     None, "дата", 1),
    # Email
    (re.compile(r"(?:email|почта|e-mail)[:\s]+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", re.I),
     None, "email", 1),
    # Город (only after explicit marker, cyrillic word 3-20 chars)
    (re.compile(r"(?:^|\s)(?:город|живёт в|находится в)[:\s]+([А-ЯЁ][а-яё]{2,19})\b"),
     None, "город", 1),
    # Профессия / занятость (very strict — only explicit markers)
    (re.compile(r"(?:^|\s)(?:профессия|занятие|специальность)[:\s]+([А-ЯЁа-яё][А-ЯЁа-яё\s]{3,40})\b"),
     None, "профессия", 1),
]


async def main():
    import asyncpg

    days = 7
    dry_run = "--dry-run" in sys.argv
    for i, arg in enumerate(sys.argv):
        if arg == "--days" and i + 1 < len(sys.argv):
            days = int(sys.argv[i + 1])

    db_url = os.environ.get("DATABASE_URL", "postgresql://neura:neura_v2_s3cure_2026@localhost:5432/neura")
    pool = await asyncpg.create_pool(db_url, min_size=1, max_size=2)

    # Get diary entries from last N days
    rows = await pool.fetch("""
        SELECT capsule_id, user_message, bot_response, created_at::date as day
        FROM diary
        WHERE created_at > NOW() - make_interval(days => $1)
        ORDER BY capsule_id, created_at
    """, days)

    print(f"Processing {len(rows)} diary entries from last {days} days...")

    # Get existing triples to deduplicate
    existing = set()
    existing_rows = await pool.fetch(
        "SELECT capsule_id, subject, predicate, object FROM knowledge_graph WHERE valid_to IS NULL"
    )
    for r in existing_rows:
        existing.add((r["capsule_id"], r["subject"], r["predicate"], r["object"]))

    new_triples = []
    for row in rows:
        capsule_id = row["capsule_id"]
        # Combine user text and bot summary for pattern matching
        texts = []
        if row["user_message"]:
            texts.append(row["user_message"])
        if row["bot_response"]:
            texts.append(row["bot_response"])
        combined = " ".join(texts)

        # Subject defaults to capsule owner name
        subject = capsule_id.replace("_", " ").title()

        for pattern, subj_group, predicate, obj_group in PATTERNS:
            for match in pattern.finditer(combined):
                obj_val = match.group(obj_group).strip().rstrip(".,;:!")
                if not obj_val or len(obj_val) < 3:
                    continue
                subj_val = match.group(subj_group).strip() if subj_group else subject
                key = (capsule_id, subj_val, predicate, obj_val)
                if key not in existing:
                    new_triples.append({
                        "capsule_id": capsule_id,
                        "subject": subj_val,
                        "predicate": predicate,
                        "object": obj_val,
                        "source": f"diary:{row['day']}",
                    })
                    existing.add(key)

    print(f"Found {len(new_triples)} new triples (deduplicated)")

    if dry_run:
        for t in new_triples[:20]:
            print(f"  [{t['capsule_id']}] {t['subject']} -> {t['predicate']} -> {t['object']}")
        if len(new_triples) > 20:
            print(f"  ... and {len(new_triples) - 20} more")
        print("\n--dry-run: no changes made.")
        await pool.close()
        return

    inserted = 0
    for t in new_triples:
        await pool.execute(
            """INSERT INTO knowledge_graph (capsule_id, subject, predicate, object, source)
               VALUES ($1, $2, $3, $4, $5)""",
            t["capsule_id"], t["subject"], t["predicate"], t["object"], t["source"],
        )
        inserted += 1

    print(f"Inserted {inserted} triples into knowledge_graph")
    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
