#!/usr/bin/env python3
"""Create HQ group with forum topics for a capsule — IDEMPOTENT.

Usage:
    python3 scripts/create-hq-group.py --capsule victoria_sel --bot-token $VICTORIA_BOT_TOKEN

Telethon 1.42 API notes:
- ToggleForumRequest requires `tabs` argument (bool)
- CreateForumTopicRequest is in `messages`, uses `peer=` not `channel=`
- GetForumTopicsRequest is in `messages`, not `channels`
- Bot entity must be resolved by username, not raw ID
"""
import argparse
import asyncio
import json
import logging
import random

from telethon import TelegramClient
from telethon.tl.functions.channels import (
    CreateChannelRequest,
    EditAdminRequest,
    ToggleForumRequest,
)
from telethon.tl.functions.messages import (
    CreateForumTopicRequest,
    GetForumTopicsRequest,
)
from telethon.tl.types import (
    ChatAdminRights,
    InputChannel,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

API_ID = 33869550
API_HASH = "489e85e0aa5bfbf3cee2c74e8044a5e0"
DEFAULT_SESSION = os.path.join(os.environ.get("NEURA_BASE", "/opt/neura-v2"), "data", "telegram_userbot_parser")

STANDARD_TOPICS = [
    {"title": "📦 Обновления", "icon_color": 0x6FB9F0},
    {"title": "🐛 Баги и ошибки", "icon_color": 0xFF93B2},
    {"title": "💬 Общее", "icon_color": 0xCB86DB},
    {"title": "📊 Аналитика", "icon_color": 0x8EEE98},
    {"title": "📝 Заметки", "icon_color": 0xFFD67E},
]


async def find_existing_group(client, group_name: str):
    """Search existing dialogs for a group with matching name."""
    dialogs = await client.get_dialogs(limit=100)
    for d in dialogs:
        if d.is_group and d.name and group_name.lower() in d.name.lower():
            log.info(f"Found existing group: {d.name} (id={d.entity.id})")
            return d.entity
    return None


async def create_hq_group(capsule_id: str, owner_name: str, bot_token: str, session: str = DEFAULT_SESSION):
    client = TelegramClient(session, API_ID, API_HASH)
    await client.start()

    group_name = f"{owner_name} | HQ"

    # Step 1: Check if group already exists
    log.info(f"Searching for existing group '{group_name}'...")
    entity = await find_existing_group(client, group_name)

    if entity:
        log.info(f"✅ Reusing existing group: {group_name} (id={entity.id})")
    else:
        # Step 2: Create supergroup
        log.info(f"Creating group '{group_name}'...")
        result = await client(CreateChannelRequest(
            title=group_name,
            about=f"HQ группа для капсулы {capsule_id}",
            megagroup=True,
        ))
        entity = result.chats[0]
        log.info(f"✅ Group created: id={entity.id}")

    input_channel = InputChannel(entity.id, entity.access_hash)

    # Step 3: Enable forum mode (Telethon 1.42: tabs= required)
    try:
        await client(ToggleForumRequest(
            channel=input_channel,
            enabled=True,
            tabs=True,
        ))
        log.info("✅ Forum mode enabled")
    except Exception as e:
        err = str(e)
        if "FORUM_ALREADY_ENABLED" in err or "already" in err.lower():
            log.info("Forum already enabled, skipping")
        else:
            log.error(f"Forum enable error: {e}")

    # Step 4: Add bot as admin (resolve by @username)
    bot_username = None
    try:
        import urllib.request
        resp = urllib.request.urlopen(f"https://api.telegram.org/bot{bot_token}/getMe")
        bot_info = json.loads(resp.read())
        bot_username = bot_info["result"]["username"]
    except Exception as e:
        log.error(f"Cannot get bot username: {e}")

    if bot_username:
        try:
            bot_entity = await client.get_entity(f"@{bot_username}")
            admin_rights = ChatAdminRights(
                post_messages=True,
                edit_messages=True,
                delete_messages=True,
                manage_topics=True,
                pin_messages=True,
                invite_users=True,
            )
            await client(EditAdminRequest(
                channel=input_channel,
                user_id=bot_entity,
                admin_rights=admin_rights,
                rank="AI Agent",
            ))
            log.info(f"✅ Bot @{bot_username} added as admin")
        except Exception as e:
            if "ADMIN_NOT_MODIFIED" in str(e):
                log.info("Bot already admin, skipping")
            else:
                log.error(f"Failed to add bot as admin: {e}")

    # Step 5: Get existing topics
    existing_topics = {}
    try:
        result = await client(GetForumTopicsRequest(
            peer=input_channel,
            offset_date=0, offset_id=0, offset_topic=0, limit=50,
        ))
        for topic in result.topics:
            existing_topics[topic.title] = topic.id
            log.info(f"  Existing topic: {topic.title} (id={topic.id})")
    except Exception as e:
        log.warning(f"Could not list topics: {e}")

    # Step 6: Create missing topics
    topic_ids = dict(existing_topics)
    for t in STANDARD_TOPICS:
        if t["title"] in existing_topics:
            log.info(f"  ⏭ Topic '{t['title']}' already exists (id={existing_topics[t['title']]})")
            continue
        try:
            result = await client(CreateForumTopicRequest(
                peer=input_channel,
                title=t["title"],
                random_id=random.randint(1, 2**31),
                icon_color=t.get("icon_color"),
            ))
            # Extract topic ID from updates
            tid = None
            for update in getattr(result, 'updates', []):
                if hasattr(update, 'id'):
                    tid = update.id
                    break
            topic_ids[t["title"]] = tid
            log.info(f"  ✅ Topic created: {t['title']} (id={tid})")
        except Exception as e:
            log.error(f"  ❌ Failed to create topic '{t['title']}': {e}")

    # Output result
    result = {
        "capsule_id": capsule_id,
        "group_id": entity.id,
        "group_name": group_name,
        "topics": topic_ids,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    log.info(f"✅ Done. Group chat_id: -100{entity.id}")

    await client.disconnect()
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create HQ group with forum topics")
    parser.add_argument("--capsule", required=True, help="Capsule ID")
    parser.add_argument("--owner", required=True, help="Owner name for group title")
    parser.add_argument("--bot-token", required=True, help="Bot token to add as admin")
    parser.add_argument("--session", default=DEFAULT_SESSION, help="Telethon session file path")
    args = parser.parse_args()

    asyncio.run(create_hq_group(args.capsule, args.owner, args.bot_token, args.session))
