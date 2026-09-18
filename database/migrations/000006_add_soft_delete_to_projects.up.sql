-- Migration: 000006_add_soft_delete_to_projects.up.sql
-- Description: Add soft delete support with 30-day recovery window

ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_projects_deleted_at ON projects(deleted_at);
