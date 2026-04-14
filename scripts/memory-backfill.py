#!/usr/bin/env python3
"""Backfill embeddings for learnings table (for wisdom graduation).

Computes e5-large embeddings for all learnings that have embedding=NULL.
Safe to run multiple times (idempotent).
"""
import asyncio
import os
import sys

sys.path.insert(0, "/opt/neura-v2")
os.environ["HF_HUB_OFFLINE"] = "1"


async def main():
    import asyncpg
    from neura.core.memory import _embed_text, _vec_to_pg_literal

    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://neura:neura_v2_s3cure_2026@localhost:5432/neura",
    )
    pool = await asyncpg.create_pool(db_url, min_size=1, max_size=2)

    rows = await pool.fetch(
        "SELECT id, content FROM learnings WHERE embedding IS NULL"
    )
    print(f"Found {len(rows)} learnings without embeddings")

    success = 0
    for row in rows:
        emb = await _embed_text(row["content"], is_query=False)
        if emb:
            await pool.execute(
                "UPDATE learnings SET embedding = $1::vector WHERE id = $2",
                _vec_to_pg_literal(emb), row["id"],
            )
            success += 1
            print(f"  [{success}/{len(rows)}] id={row['id']}: {row['content'][:60]}...")
        else:
            print(f"  SKIP id={row['id']}: embedding failed")

    print(f"\nDone: {success}/{len(rows)} embeddings computed")
    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
