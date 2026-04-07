-- Project links (auto-detected from messages + manual)
ALTER TABLE projects ADD COLUMN IF NOT EXISTS links JSONB DEFAULT '[]';

-- Project members (capsule associations)
CREATE TABLE IF NOT EXISTS project_members (
    id SERIAL PRIMARY KEY,
    project_id INT REFERENCES projects(id) ON DELETE CASCADE,
    capsule_id TEXT NOT NULL,
    role TEXT DEFAULT 'member',
    added_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(project_id, capsule_id)
);
