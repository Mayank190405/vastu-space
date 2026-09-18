-- Migration: 000009_project_timeline_chat_and_client_emails.up.sql
-- Description: Project Timeline Monitor with Milestone Comments, Real-Time Project Chat with Urgency Levels, and Client Email Logs

-- 1. Project Timeline Milestones Table
CREATE TABLE IF NOT EXISTS project_timeline_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    event_type VARCHAR(64) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'completed', -- 'completed', 'in_progress', 'pending', 'blocked'
    milestone_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_timeline_events_project ON project_timeline_events(project_id);

-- 2. Timeline Event Comments & Notes Table
CREATE TABLE IF NOT EXISTS timeline_event_comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID NOT NULL REFERENCES project_timeline_events(id) ON DELETE CASCADE,
    author_id UUID REFERENCES users(id) ON DELETE SET NULL,
    author_name VARCHAR(255) NOT NULL,
    author_role VARCHAR(64) NOT NULL DEFAULT 'Project Member',
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_timeline_comments_event ON timeline_event_comments(event_id);

-- 3. Project Real-Time Chat Messages Table
CREATE TABLE IF NOT EXISTS project_chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    sender_id UUID REFERENCES users(id) ON DELETE SET NULL,
    sender_name VARCHAR(255) NOT NULL,
    sender_role VARCHAR(64) NOT NULL DEFAULT 'Project Member',
    content TEXT NOT NULL,
    urgency_level VARCHAR(32) NOT NULL DEFAULT 'normal', -- 'normal', 'high', 'urgent', 'critical'
    is_pinned BOOLEAN NOT NULL DEFAULT false,
    is_resolved BOOLEAN NOT NULL DEFAULT false,
    resolved_by VARCHAR(255),
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_project ON project_chat_messages(project_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_urgency ON project_chat_messages(urgency_level);

-- 4. Client Email Dispatch Logs Table
CREATE TABLE IF NOT EXISTS client_email_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    recipient_email VARCHAR(255) NOT NULL,
    recipient_name VARCHAR(255),
    subject VARCHAR(255) NOT NULL,
    email_type VARCHAR(64) NOT NULL DEFAULT 'thank_you_and_verification',
    status VARCHAR(32) NOT NULL DEFAULT 'sent', -- 'sent', 'delivered', 'confirmed'
    dispatched_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_client_email_logs_project ON client_email_logs(project_id);
