-- 007_memory_hierarchy.sql
-- Memory Architecture Upgrade: layered loading, knowledge graph, wisdom graduation
-- Fully additive — no destructive changes to existing tables
-- Inspired by MemPalace (wings/layers) + Karpathy LLM Wiki (lint/ingest)

-- === Extend memory table with layer classification ===
ALTER TABLE memory ADD COLUMN IF NOT EXISTS layer TEXT DEFAULT 'L2';
ALTER TABLE memory ADD COLUMN IF NOT EXISTS wing TEXT;
ALTER TABLE memory ADD COLUMN IF NOT EXISTS hit_count INTEGER DEFAULT 0;
ALTER TABLE memory ADD COLUMN IF NOT EXISTS last_hit TIMESTAMPTZ;

-- Faster lookups by layer
CREATE INDEX IF NOT EXISTS idx_memory_layer ON memory(capsule_id, layer);

-- === Extend learnings table for wisdom graduation ===
ALTER TABLE learnings ADD COLUMN IF NOT EXISTS embedding VECTOR(1024);

-- === Knowledge Graph: temporal triples ===
-- Stores subject-predicate-object facts with time validity
-- Example: ("клиент", "предпочитает", "утренние встречи", valid_from=2026-04-01)
CREATE TABLE IF NOT EXISTS knowledge_graph (
    id SERIAL PRIMARY KEY,
    capsule_id TEXT NOT NULL,
    subject TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object TEXT NOT NULL,
    confidence FLOAT DEFAULT 1.0,
    valid_from TIMESTAMPTZ DEFAULT NOW(),
    valid_to TIMESTAMPTZ,          -- NULL = still active
    source TEXT,                    -- 'diary:123', 'learning:45', 'manual'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Fast lookup: active facts about a subject
CREATE INDEX IF NOT EXISTS idx_kg_capsule_subject
    ON knowledge_graph(capsule_id, subject);
CREATE INDEX IF NOT EXISTS idx_kg_active
    ON knowledge_graph(capsule_id, valid_to)
    WHERE valid_to IS NULL;

-- === Behavioral Rules: graduated wisdom ===
-- Recurring learnings that proved themselves over 2+ days
-- become permanent behavioral rules (L1 layer)
CREATE TABLE IF NOT EXISTS behavioral_rules (
    id SERIAL PRIMARY KEY,
    capsule_id TEXT NOT NULL,
    rule TEXT NOT NULL,
    source_pattern TEXT,            -- the learning text that was repeated
    occurrence_count INTEGER DEFAULT 0,
    first_seen TIMESTAMPTZ,
    graduated_at TIMESTAMPTZ DEFAULT NOW(),
    active BOOLEAN DEFAULT true,
    embedding VECTOR(1024)
);

-- Only load active rules
CREATE INDEX IF NOT EXISTS idx_rules_capsule_active
    ON behavioral_rules(capsule_id)
    WHERE active = true;
