-- Migration: 000010_create_project_activity_history.up.sql
-- Description: Project Activity History & Audit Log tracking who did what action

CREATE TABLE IF NOT EXISTS project_activity_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    actor_id UUID REFERENCES users(id) ON DELETE SET NULL,
    actor_name VARCHAR(255) NOT NULL,
    actor_role VARCHAR(64) NOT NULL DEFAULT 'Admin',
    action_type VARCHAR(64) NOT NULL, -- 'status_change', 'milestone_updated', 'comment_added', 'email_dispatched', 'member_assigned', 'project_created', 'project_updated'
    action_title VARCHAR(255) NOT NULL,
    details TEXT,
    old_value TEXT,
    new_value TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_project_activity_logs_project ON project_activity_logs(project_id);
CREATE INDEX IF NOT EXISTS idx_project_activity_logs_created ON project_activity_logs(created_at DESC);
