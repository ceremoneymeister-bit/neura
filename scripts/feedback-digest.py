#!/usr/bin/env python3
"""Daily feedback digest — sends thumbs up/down summary to Dmitry via Telegram.

Cron: 0 10 * * * (10:00 UTC = 16:00 NSK)
"""
import asyncio
import subprocess
import sys
from datetime import datetime, timezone, timedelta

import asyncpg


DB_URL = "postgresql://neura:neura_v2_s3cure_2026@localhost:5432/neura"


async def get_feedback():
    pool = await asyncpg.create_pool(DB_URL, min_size=1, max_size=2)
    try:
        # Feedback from last 24 hours
        rows = await pool.fetch("""
            SELECT
                f.vote,
                f.comment,
                u.name AS user_name,
                m.content AS message_text,
                f.created_at
            FROM message_feedback f
            JOIN users u ON u.id = f.user_id
            LEFT JOIN messages m ON m.id = f.message_id
            WHERE f.created_at > NOW() - INTERVAL '24 hours'
            ORDER BY f.created_at DESC
        """)

        # Counts
        up_count = sum(1 for r in rows if r["vote"] == "up")
        down_count = sum(1 for r in rows if r["vote"] == "down")

        return rows, up_count, down_count
    finally:
        await pool.close()


def format_digest(rows, up_count, down_count):
    today = datetime.now(timezone(timedelta(hours=7))).strftime("%d.%m.%Y")

    if not rows:
        return f"📊 Фидбек за {today}: нет оценок за последние 24ч."

    lines = [f"📊 Фидбек платформы — {today}"]
    lines.append(f"👍 {up_count}  |  👎 {down_count}")
    lines.append("")

    # Show negative feedback with details
    negatives = [r for r in rows if r["vote"] == "down"]
    if negatives:
        lines.append("❌ Негативные:")
        for r in negatives:
            user = r["user_name"] or "?"
            msg = (r["message_text"] or "")[:100]
            comment = r["comment"] or "без комментария"
            lines.append(f"• {user}: «{comment}»")
            if msg:
                lines.append(f"  ↳ ответ: {msg}...")
        lines.append("")

    # Show positive briefly
    positives = [r for r in rows if r["vote"] == "up"]
    if positives:
        names = set(r["user_name"] for r in positives if r["user_name"])
        lines.append(f"✅ Позитивные ({up_count}): {', '.join(names) or '?'}")

    return "\n".join(lines)


async def main():
    rows, up, down = await get_feedback()

    # Skip if nothing
    if not rows:
        print("No feedback in last 24h, skipping.")
        return

    text = format_digest(rows, up, down)
    print(text)
    print("---")

    # Send to Dmitry
    try:
        result = subprocess.run(
            ["python3", "/root/Antigravity/scripts/tg-send.py", "me", text],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            print("Sent to Dmitry ✓")
        else:
            print(f"Send failed: {result.stderr}")
    except Exception as e:
        print(f"Error sending: {e}")


if __name__ == "__main__":
    asyncio.run(main())
