#!/usr/bin/env python3
"""Run wisdom graduation for all capsules.

Finds recurring learnings (2+ days, cosine similarity > 0.85)
and promotes them to behavioral rules.
"""
import asyncio
import os
import sys

sys.path.insert(0, "/opt/neura-v2")
os.environ["HF_HUB_OFFLINE"] = "1"


async def main():
    import asyncpg
    from neura.core.memory import MemoryStore

    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://neura:neura_v2_s3cure_2026@localhost:5432/neura",
    )
    pool = await asyncpg.create_pool(db_url, min_size=1, max_size=2)
    store = MemoryStore(pool)

    # Get all capsule IDs
    rows = await pool.fetch(
        "SELECT DISTINCT capsule_id FROM learnings WHERE type='learning'"
    )
    capsules = [r["capsule_id"] for r in rows]
    print(f"Checking {len(capsules)} capsules for wisdom graduation...")

    total = 0
    for cap_id in capsules:
        graduated = await store.graduate_wisdom(cap_id)
        if graduated:
            print(f"\n  {cap_id}: {len(graduated)} rules graduated:")
            for rule in graduated:
                print(f"    → {rule[:80]}...")
            total += len(graduated)
        else:
            print(f"  {cap_id}: no recurring patterns found")

    print(f"\nTotal graduated: {total}")
    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
