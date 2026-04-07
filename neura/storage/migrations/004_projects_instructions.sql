-- Add instructions field to projects (custom system prompt per project, like Claude.ai)
ALTER TABLE projects ADD COLUMN IF NOT EXISTS instructions TEXT DEFAULT '';
