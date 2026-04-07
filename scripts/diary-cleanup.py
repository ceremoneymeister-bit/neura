#!/usr/bin/env python3
"""Daily diary cleanup — delete entries older than retention_days per capsule.

Run via cron: 0 4 * * * python3 /opt/neura-v2/scripts/diary-cleanup.py
"""
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from neura.core.capsule import Capsule
from neura.core.memory import MemoryStore
from neura.storage.db import Database


async def main():
    # Load .env
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

    db = Database()
    await db.connect()
    memory = MemoryStore(db.pool)

    capsules = Capsule.load_all()
    total = 0

    for cap_id, capsule in capsules.items():
        retention = capsule.config.memory.get("diary_retention_days", 90)
        deleted = await memory.cleanup_old_diary(cap_id, retention)
        if deleted > 0:
            print(f"  {cap_id}: deleted {deleted} entries (retention={retention}d)")
            total += deleted

    if total > 0:
        print(f"Total: {total} old diary entries cleaned up")
    else:
        print("No old entries to clean up")

    await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
