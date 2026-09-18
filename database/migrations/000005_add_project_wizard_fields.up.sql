-- Migration: 000005_add_project_wizard_fields.up.sql
-- Description: Add fields required for the 7-Step Project Creation Wizard

ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS project_code VARCHAR(64),
    ADD COLUMN IF NOT EXISTS postal_code VARCHAR(32),
    ADD COLUMN IF NOT EXISTS primary_contact_name VARCHAR(255),
    ADD COLUMN IF NOT EXISTS primary_contact_email VARCHAR(255),
    ADD COLUMN IF NOT EXISTS primary_contact_phone VARCHAR(64),
    ADD COLUMN IF NOT EXISTS start_date DATE,
    ADD COLUMN IF NOT EXISTS expected_completion_date DATE,
    ADD COLUMN IF NOT EXISTS project_admin_id UUID REFERENCES users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS assigned_members JSONB DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS assigned_operators JSONB DEFAULT '[]'::jsonb;

ALTER TABLE project_structures
    ADD COLUMN IF NOT EXISTS building_address TEXT,
    ADD COLUMN IF NOT EXISTS building_description TEXT;
