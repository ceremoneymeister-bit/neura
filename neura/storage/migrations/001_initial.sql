-- Neura Platform v2 — Initial Schema
-- Based on ARCHITECTURE.md section 7

-- Enable pgvector for future semantic search
CREATE EXTENSION IF NOT EXISTS vector;

-- Capsules
CREATE TABLE IF NOT EXISTS capsules (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    config JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Diary (one entry per user↔bot interaction)
CREATE TABLE IF NOT EXISTS diary (
    id SERIAL PRIMARY KEY,
    capsule_id TEXT REFERENCES capsules(id),
    date DATE NOT NULL,
    time TIME NOT NULL,
    source TEXT DEFAULT 'telegram',
    user_message TEXT,
    bot_response TEXT,
    model TEXT,
    duration_sec FLOAT,
    tools_used TEXT[],
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_diary_capsule_date ON diary(capsule_id, date DESC);

-- Long-term memory
CREATE TABLE IF NOT EXISTS memory (
    id SERIAL PRIMARY KEY,
    capsule_id TEXT REFERENCES capsules(id),
    content TEXT NOT NULL,
    score FLOAT DEFAULT 0.5,
    source TEXT,
    embedding VECTOR(1536),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_memory_capsule ON memory(capsule_id);

-- Learnings & Corrections
CREATE TABLE IF NOT EXISTS learnings (
    id SERIAL PRIMARY KEY,
    capsule_id TEXT REFERENCES capsules(id),
    type TEXT CHECK (type IN ('learning', 'correction')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Files
CREATE TABLE IF NOT EXISTS files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    capsule_id TEXT REFERENCES capsules(id),
    filename TEXT NOT NULL,
    path TEXT NOT NULL,
    mime_type TEXT,
    size_bytes BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
