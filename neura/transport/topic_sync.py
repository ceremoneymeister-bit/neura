"""Sync Telegram forum topics with web platform projects/conversations.

Each HQ group → Project on web platform.
Each topic in HQ group → Conversation in that project.
Private chat (no topic) → Conversation "Общий" in capsule's project.

Flow:
  1. Message arrives in TG (text/voice/photo/doc)
  2. _process_message calls ensure_web_conversation()
  3. If no project for this capsule+group → create one
  4. If no conversation for this topic → create one
  5. Message is also saved to web conversation (for web UI)
"""
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Cache: (capsule_id, group_id, topic_id) → conversation_id
_conv_cache: dict[tuple[str, int | None, int | None], int] = {}


async def ensure_web_conversation(
    pool,
    capsule_id: str,
    chat_id: int | None,
    thread_id: int | None,
    topic_title: str | None = None,
) -> int | None:
    """Find or create a web conversation for this TG topic.

    Returns conversation_id or None if no web user mapped to this capsule.
    """
    cache_key = (capsule_id, chat_id, thread_id)
    if cache_key in _conv_cache:
        return _conv_cache[cache_key]

    try:
        conv_id = await _ensure_impl(pool, capsule_id, chat_id, thread_id, topic_title)
        if conv_id:
            _conv_cache[cache_key] = conv_id
        return conv_id
    except Exception as e:
        logger.error(f"Topic sync error: {e}")
        return None


async def _ensure_impl(pool, capsule_id, chat_id, thread_id, topic_title):
    """Implementation: find or create project + conversation."""
    # 1. Find web user for this capsule
    user = await pool.fetchrow(
        "SELECT id FROM users WHERE capsule_id = $1 LIMIT 1",
        capsule_id,
    )
    if not user:
        return None
    user_id = user["id"]

    # 2. Find or create project for this HQ group
    project_id = None
    if chat_id:
        project = await pool.fetchrow(
            """SELECT id FROM projects
               WHERE capsule_id = $1 AND telegram_group_id = $2 LIMIT 1""",
            capsule_id, chat_id,
        )
        if project:
            project_id = project["id"]
        else:
            # Create project for this group
            project_name = topic_title or f"Telegram"
            row = await pool.fetchrow(
                """INSERT INTO projects (user_id, name, icon, capsule_id, telegram_group_id)
                   VALUES ($1, $2, $3, $4, $5)
                   RETURNING id""",
                user_id, project_name, "💬", capsule_id, chat_id,
            )
            project_id = row["id"]
            logger.info(f"[topic_sync] Created project '{project_name}' for {capsule_id}")

    # 3. Find or create conversation for this topic
    if thread_id:
        conv = await pool.fetchrow(
            """SELECT id FROM conversations
               WHERE capsule_id = $1 AND telegram_group_id = $2
               AND telegram_topic_id = $3 LIMIT 1""",
            capsule_id, chat_id, thread_id,
        )
    else:
        # Private chat or General topic
        conv = await pool.fetchrow(
            """SELECT id FROM conversations
               WHERE capsule_id = $1
               AND (telegram_group_id IS NULL OR telegram_group_id = $2)
               AND telegram_topic_id IS NULL LIMIT 1""",
            capsule_id, chat_id,
        )

    if conv:
        return conv["id"]

    # Create conversation
    conv_title = topic_title or "Общий"
    row = await pool.fetchrow(
        """INSERT INTO conversations
           (user_id, project_id, title, capsule_id, telegram_group_id, telegram_topic_id)
           VALUES ($1, $2, $3, $4, $5, $6)
           RETURNING id""",
        user_id, project_id, conv_title, capsule_id, chat_id, thread_id,
    )
    conv_id = row["id"]
    logger.info(
        f"[topic_sync] Created conversation '{conv_title}' "
        f"(topic={thread_id}) for {capsule_id}"
    )
    return conv_id


async def save_web_message(
    pool,
    conversation_id: int,
    role: str,
    content: str,
    model: str = "sonnet",
    duration_sec: float = 0,
) -> int | None:
    """Save a message to web conversation (mirrors TG interaction)."""
    try:
        row = await pool.fetchrow(
            """INSERT INTO messages (conversation_id, role, content, model, duration_sec)
               VALUES ($1, $2, $3, $4, $5)
               RETURNING id""",
            conversation_id, role, content, model, duration_sec,
        )
        return row["id"]
    except Exception as e:
        logger.error(f"Web message save error: {e}")
        return None


async def seed_topics(pool, capsule_id: str, group_id: int,
                      topics: dict[int, str], project_name: str,
                      project_icon: str = "💬") -> dict:
    """Batch-create project + conversations for known topics.

    Args:
        topics: {topic_id: topic_title, ...}
        project_name: Name for the project
    Returns:
        {"project_id": int, "conversations": {topic_id: conv_id, ...}}
    """
    user = await pool.fetchrow(
        "SELECT id FROM users WHERE capsule_id = $1 LIMIT 1",
        capsule_id,
    )
    if not user:
        raise ValueError(f"No web user for capsule {capsule_id}")
    user_id = user["id"]

    # Find or create project
    project = await pool.fetchrow(
        "SELECT id FROM projects WHERE capsule_id = $1 AND telegram_group_id = $2",
        capsule_id, group_id,
    )
    if project:
        project_id = project["id"]
    else:
        row = await pool.fetchrow(
            """INSERT INTO projects (user_id, name, icon, capsule_id, telegram_group_id)
               VALUES ($1, $2, $3, $4, $5) RETURNING id""",
            user_id, project_name, project_icon, capsule_id, group_id,
        )
        project_id = row["id"]

    # Create conversations for each topic
    result = {"project_id": project_id, "conversations": {}}
    for topic_id, title in topics.items():
        conv = await pool.fetchrow(
            """SELECT id FROM conversations
               WHERE capsule_id = $1 AND telegram_group_id = $2
               AND telegram_topic_id = $3""",
            capsule_id, group_id, topic_id,
        )
        if conv:
            result["conversations"][topic_id] = conv["id"]
        else:
            row = await pool.fetchrow(
                """INSERT INTO conversations
                   (user_id, project_id, title, capsule_id, telegram_group_id, telegram_topic_id)
                   VALUES ($1, $2, $3, $4, $5, $6) RETURNING id""",
                user_id, project_id, title, capsule_id, group_id, topic_id,
            )
            result["conversations"][topic_id] = row["id"]

    return result
