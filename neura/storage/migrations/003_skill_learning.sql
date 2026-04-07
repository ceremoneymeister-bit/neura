-- Neura v2 — Skill Learning (self-evolving skills)
-- Tracks every skill usage for automatic evolution

CREATE TABLE IF NOT EXISTS skill_usage (
    id SERIAL PRIMARY KEY,
    capsule_id TEXT REFERENCES capsules(id),
    skill_name TEXT NOT NULL,
    used_at TIMESTAMPTZ DEFAULT NOW(),
    success BOOLEAN DEFAULT true,
    duration_sec FLOAT,
    user_intent TEXT,
    tools_used TEXT[],
    correction TEXT,
    lesson TEXT,
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_skill_usage_name ON skill_usage(skill_name, used_at DESC);
CREATE INDEX IF NOT EXISTS idx_skill_usage_capsule ON skill_usage(capsule_id, used_at DESC);
