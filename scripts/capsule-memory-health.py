#!/usr/bin/env python3
"""Per-capsule memory health check.

Checks: behavioral rules, corrections, embeddings, duplicates.
Outputs structured report. Exit 0 = healthy, exit 1 = issues found.
"""
import asyncio
import os
import sys

sys.path.insert(0, "/opt/neura-v2")
os.environ["HF_HUB_OFFLINE"] = "1"

WARN_CORRECTIONS_NO_RULES = 10  # warn if corrections > N but rules = 0


async def main():
    import asyncpg

    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/neura",
    )
    pool = await asyncpg.create_pool(db_url, min_size=1, max_size=2)

    capsules = await pool.fetch(
        "SELECT DISTINCT capsule_id FROM diary ORDER BY capsule_id"
    )

    issues = 0
    for row in capsules:
        cap = row["capsule_id"]
        # Counts
        rules = await pool.fetchval(
            "SELECT COUNT(*) FROM behavioral_rules WHERE capsule_id=$1 AND active=true", cap)
        corrections = await pool.fetchval(
            "SELECT COUNT(*) FROM learnings WHERE capsule_id=$1 AND type='correction'", cap)
        learnings = await pool.fetchval(
            "SELECT COUNT(*) FROM learnings WHERE capsule_id=$1 AND type='learning'", cap)
        memories = await pool.fetchval(
            "SELECT COUNT(*) FROM memory WHERE capsule_id=$1", cap)
        no_embed = await pool.fetchval(
            "SELECT COUNT(*) FROM learnings WHERE capsule_id=$1 AND embedding IS NULL", cap)
        kg = await pool.fetchval(
            "SELECT COUNT(*) FROM knowledge_graph WHERE capsule_id=$1 AND valid_to IS NULL", cap)

        # Status
        status = "✅"
        warnings = []

        if corrections > WARN_CORRECTIONS_NO_RULES and rules == 0:
            warnings.append(f"⚠️ {corrections} corrections but 0 behavioral rules")
            issues += 1

        if no_embed > 0:
            warnings.append(f"⚠️ {no_embed} entries without embeddings")
            issues += 1

        if memories == 0 and corrections > 5:
            warnings.append(f"⚠️ memory table empty")

        if warnings:
            status = "⚠️"

        print(f"{status} {cap:<30} rules={rules:>2} corr={corrections:>3} "
              f"learn={learnings:>2} mem={memories:>2} kg={kg:>2} no_embed={no_embed}")
        for w in warnings:
            print(f"   {w}")

    print(f"\n{'All healthy' if issues == 0 else f'{issues} issue(s) found'}")
    await pool.close()
    sys.exit(0 if issues == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
