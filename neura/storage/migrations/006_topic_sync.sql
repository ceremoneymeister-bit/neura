-- 006_topic_sync.sql
-- Sync Telegram forum topics with web platform conversations.
-- Each TG topic → separate conversation, each HQ group → project.

-- 1. diary: track which TG topic the message came from
ALTER TABLE diary ADD COLUMN IF NOT EXISTS thread_id INTEGER;
CREATE INDEX IF NOT EXISTS idx_diary_capsule_thread
    ON diary (capsule_id, thread_id, date DESC);

-- 2. conversations: link to TG topic
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS telegram_topic_id INTEGER;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS telegram_group_id BIGINT;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS capsule_id TEXT;
CREATE INDEX IF NOT EXISTS idx_conversations_telegram
    ON conversations (capsule_id, telegram_group_id, telegram_topic_id);

-- 3. projects: link to TG HQ group
ALTER TABLE projects ADD COLUMN IF NOT EXISTS telegram_group_id BIGINT;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS capsule_id TEXT;
CREATE INDEX IF NOT EXISTS idx_projects_telegram
    ON projects (capsule_id, telegram_group_id);
