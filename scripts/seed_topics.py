#!/usr/bin/env python3
"""Seed web platform with projects/conversations from TG forum topics.

Maps each HQ group → project, each topic → conversation.
Safe to run multiple times (idempotent).

Usage:
    python3 scripts/seed_topics.py
"""
import asyncio
import os
import sys
sys.path.insert(0, "/opt/neura-v2")

import asyncpg

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://neura:neura_v2_s3cure_2026@localhost:5432/neura",
)

# All known HQ groups and their topics
# Format: (capsule_id, group_id, group_name, icon, {topic_id: title})
GROUPS = [
    ("victoria_sel", -1003899251313, "Victoria HQ", "🏠", {
        3: "Контент & Идеи",
        8: "Осознания",
        10: "Ассистент",
        300: "Рефлексия & Дневник",
        450: "Обновления",
        548: "Аудит",
    }),
    ("maxim_belousov", -1003806649394, "Максим | Нэйра", "🚀", {
        3: "Основной",
        159: "Доработка",
    }),
    ("yana_berezhnaya", -1002930580025, "Бережная Йога", "🧘", {
        1: "Общий",
        2: "Йога",
        3: "Дыхательные практики",
        4: "МФР",
        37: "Быстрая йога",
        56: "Аюрведа",
    }),
    ("marina_biryukova", -1003870857965, "Марина HQ", "🏆", {
        # Topics will be discovered when bot joins the group
    }),
]

# Also create a "Личный чат" conversation for each capsule (no group)
PERSONAL_CAPSULES = [
    "victoria_sel",
    "maxim_belousov",
    "yana_berezhnaya",
    "marina_biryukova",
    "yulia_gudymo",
    "nikita_maltsev",
]


async def main():
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=3)

    print("=== Seeding web platform with TG topics ===\n")

    # 1. Create projects and conversations for HQ groups
    for capsule_id, group_id, group_name, icon, topics in GROUPS:
        user = await pool.fetchrow(
            "SELECT id FROM users WHERE capsule_id = $1 LIMIT 1",
            capsule_id,
        )
        if not user:
            print(f"  ⚠ No web user for {capsule_id}, skipping")
            continue
        user_id = user["id"]

        # Find or create project
        project = await pool.fetchrow(
            "SELECT id FROM projects WHERE capsule_id = $1 AND telegram_group_id = $2",
            capsule_id, group_id,
        )
        if project:
            project_id = project["id"]
            print(f"  ✓ Project '{group_name}' exists (id={project_id})")
        else:
            row = await pool.fetchrow(
                """INSERT INTO projects (user_id, name, icon, capsule_id, telegram_group_id)
                   VALUES ($1, $2, $3, $4, $5) RETURNING id""",
                user_id, group_name, icon, capsule_id, group_id,
            )
            project_id = row["id"]
            print(f"  ✚ Created project '{group_name}' (id={project_id})")

        # Create conversations for each topic
        for topic_id, title in topics.items():
            conv = await pool.fetchrow(
                """SELECT id FROM conversations
                   WHERE capsule_id = $1 AND telegram_group_id = $2
                   AND telegram_topic_id = $3""",
                capsule_id, group_id, topic_id,
            )
            if conv:
                print(f"    ✓ '{title}' exists (id={conv['id']})")
            else:
                row = await pool.fetchrow(
                    """INSERT INTO conversations
                       (user_id, project_id, title, capsule_id, telegram_group_id, telegram_topic_id)
                       VALUES ($1, $2, $3, $4, $5, $6) RETURNING id""",
                    user_id, project_id, title, capsule_id, group_id, topic_id,
                )
                print(f"    ✚ Created '{title}' (id={row['id']})")

    # 2. Create "Личный чат" for each capsule (private bot chat)
    print("\n--- Personal chats ---")
    for capsule_id in PERSONAL_CAPSULES:
        user = await pool.fetchrow(
            "SELECT id FROM users WHERE capsule_id = $1 LIMIT 1",
            capsule_id,
        )
        if not user:
            print(f"  ⚠ No web user for {capsule_id}")
            continue
        user_id = user["id"]

        # Check if personal conversation exists
        conv = await pool.fetchrow(
            """SELECT id FROM conversations
               WHERE capsule_id = $1 AND telegram_topic_id IS NULL
               AND telegram_group_id IS NULL""",
            capsule_id,
        )
        if conv:
            print(f"  ✓ {capsule_id}: Личный чат exists (id={conv['id']})")
        else:
            row = await pool.fetchrow(
                """INSERT INTO conversations
                   (user_id, title, capsule_id)
                   VALUES ($1, $2, $3) RETURNING id""",
                user_id, "Личный чат", capsule_id,
            )
            print(f"  ✚ {capsule_id}: Created 'Личный чат' (id={row['id']})")

    # 3. Summary
    total_projects = await pool.fetchval(
        "SELECT COUNT(*) FROM projects WHERE capsule_id IS NOT NULL")
    total_convs = await pool.fetchval(
        "SELECT COUNT(*) FROM conversations WHERE capsule_id IS NOT NULL")
    print(f"\n=== Done: {total_projects} projects, {total_convs} conversations ===")

    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
