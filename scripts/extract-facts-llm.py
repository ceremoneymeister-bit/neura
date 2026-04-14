#!/usr/bin/env python3
"""Extract SPO triples from diary entries using LLM (OpenRouter free model).

Much higher quality than regex-based extract-facts.py.
Uses batch processing (10 diary entries per LLM call) to minimize API calls.

Usage:
    python3 scripts/extract-facts-llm.py              # last 7 days
    python3 scripts/extract-facts-llm.py --days 30    # last 30 days
    python3 scripts/extract-facts-llm.py --dry-run    # preview only
    python3 scripts/extract-facts-llm.py --capsule marina_biryukova  # specific capsule
"""

import asyncio
import json
import os
import re
import sys
from datetime import datetime

sys.path.insert(0, "/opt/neura-v2")

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://neura:neura_v2_s3cure_2026@localhost:5432/neura",
)
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openai/gpt-oss-120b:free"  # free, good Russian
BATCH_SIZE = 10  # diary entries per LLM call
MAX_BATCHES = 50  # safety limit

SYSTEM_PROMPT = """You are a knowledge graph extractor. Given diary entries from an AI assistant's conversations with a user, extract factual SPO (Subject-Predicate-Object) triples.

Rules:
- Extract ONLY concrete, verifiable facts (names, URLs, dates, preferences, skills, relationships)
- Subject = person, company, project, or entity name
- Predicate = relationship type (has_website, has_channel, works_at, prefers, located_in, birthday, price, deadline, uses_tool, skill, contact, etc.)
- Object = the concrete value
- Do NOT extract opinions, emotions, or vague statements
- Do NOT extract conversational filler
- Normalize predicates to snake_case English
- Keep subject/object in their original language (Russian/English)
- Each triple must be a standalone fact

Return JSON array of objects: [{"s": "Subject", "p": "predicate", "o": "Object"}]
If no facts found, return: []"""


async def call_llm(entries: list[dict]) -> list[dict]:
    """Call OpenRouter LLM to extract facts from diary entries."""
    import aiohttp

    # Format entries for the prompt
    text_parts = []
    for e in entries:
        date_str = e["day"].isoformat() if hasattr(e["day"], "isoformat") else str(e["day"])
        user_msg = (e.get("user_message") or "")[:500]
        bot_resp = (e.get("bot_response") or "")[:500]
        text_parts.append(f"[{date_str}] User: {user_msg}\nAssistant: {bot_resp}")

    user_text = f"Capsule: {entries[0]['capsule_id']}\n\n" + "\n---\n".join(text_parts)

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ],
        "temperature": 0.1,
        "max_tokens": 2000,
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession() as session:
        for attempt in range(3):
            async with session.post(OPENROUTER_URL, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status == 429:
                    wait = min(60, 10 * (attempt + 1))
                    print(f"  Rate limited, waiting {wait}s (attempt {attempt + 1}/3)...")
                    await asyncio.sleep(wait)
                    continue
                if resp.status != 200:
                    err = await resp.text()
                    print(f"  LLM error {resp.status}: {err[:200]}")
                    return []
                data = await resp.json()
                break
        else:
            print(f"  Rate limit exceeded after 3 retries, stopping batch.")
            return []

    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

    # Parse JSON from response (may be wrapped in ```json ... ```)
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```\w*\n?", "", content)
        content = re.sub(r"\n?```$", "", content)

    try:
        triples = json.loads(content)
        if isinstance(triples, list):
            return [t for t in triples if isinstance(t, dict) and "s" in t and "p" in t and "o" in t]
    except json.JSONDecodeError:
        print(f"  Failed to parse LLM response: {content[:200]}")
    return []


async def main():
    import asyncpg

    if not OPENROUTER_API_KEY:
        print("ERROR: OPENROUTER_API_KEY not set. Source .env first.")
        sys.exit(1)

    days = 7
    dry_run = "--dry-run" in sys.argv
    target_capsule = None
    for i, arg in enumerate(sys.argv):
        if arg == "--days" and i + 1 < len(sys.argv):
            days = int(sys.argv[i + 1])
        if arg == "--capsule" and i + 1 < len(sys.argv):
            target_capsule = sys.argv[i + 1]

    pool = await asyncpg.create_pool(DB_URL, min_size=1, max_size=2)

    # Get diary entries
    query = """
        SELECT capsule_id, user_message, bot_response, created_at::date as day
        FROM diary
        WHERE created_at > NOW() - make_interval(days => $1)
    """
    params = [days]
    if target_capsule:
        query += " AND capsule_id = $2"
        params.append(target_capsule)
    query += " ORDER BY capsule_id, created_at"

    rows = await pool.fetch(query, *params)
    print(f"Processing {len(rows)} diary entries from last {days} days...")

    # Get existing triples for dedup
    existing = set()
    existing_rows = await pool.fetch(
        "SELECT capsule_id, subject, predicate, object FROM knowledge_graph WHERE valid_to IS NULL"
    )
    for r in existing_rows:
        existing.add((r["capsule_id"], r["subject"].lower(), r["predicate"].lower(), r["object"].lower()))

    # Group by capsule_id
    by_capsule = {}
    for row in rows:
        cid = row["capsule_id"]
        if cid not in by_capsule:
            by_capsule[cid] = []
        by_capsule[cid].append(dict(row))

    all_new = []
    total_api_calls = 0

    for capsule_id, entries in by_capsule.items():
        print(f"\n  [{capsule_id}] {len(entries)} entries")

        # Process in batches
        for i in range(0, len(entries), BATCH_SIZE):
            if total_api_calls >= MAX_BATCHES:
                print(f"  ⚠️ Reached max API calls limit ({MAX_BATCHES})")
                break

            batch = entries[i:i + BATCH_SIZE]
            triples = await call_llm(batch)
            total_api_calls += 1

            for t in triples:
                subj = t["s"].strip()
                pred = t["p"].strip().lower()
                obj = t["o"].strip()
                key = (capsule_id, subj.lower(), pred, obj.lower())
                if key not in existing:
                    all_new.append({
                        "capsule_id": capsule_id,
                        "subject": subj,
                        "predicate": pred,
                        "object": obj,
                        "source": f"llm:{datetime.now().strftime('%Y-%m-%d')}",
                    })
                    existing.add(key)

            found = len(triples)
            new_in_batch = sum(1 for t in triples
                              if (capsule_id, t["s"].strip().lower(), t["p"].strip().lower(), t["o"].strip().lower())
                              not in existing or True)  # already added above
            print(f"    batch {i // BATCH_SIZE + 1}: {found} triples extracted, API call #{total_api_calls}")

            # Rate limit: 1.5s between calls (free tier = 50/day)
            await asyncio.sleep(1.5)

    print(f"\n{'=' * 50}")
    print(f"Total API calls: {total_api_calls}")
    print(f"New triples: {len(all_new)} (after dedup)")

    if dry_run:
        for t in all_new[:30]:
            print(f"  [{t['capsule_id']}] {t['subject']} -> {t['predicate']} -> {t['object']}")
        if len(all_new) > 30:
            print(f"  ... and {len(all_new) - 30} more")
        print("\n--dry-run: no changes made.")
        await pool.close()
        return

    # Insert
    inserted = 0
    for t in all_new:
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
