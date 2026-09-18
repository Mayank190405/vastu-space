-- Migration: 000007_complete_project_specification.up.sql
-- Description: Complete 12-Step Project Creation Schema with Client, Contacts, Capture Planning, Configuration, Project Updates, and Floors

-- 1. Extend projects table with complete 12-step specification fields
ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS purpose VARCHAR(255),
    ADD COLUMN IF NOT EXISTS priority VARCHAR(32) DEFAULT 'High',
    ADD COLUMN IF NOT EXISTS client_type VARCHAR(64) DEFAULT 'Organization',
    ADD COLUMN IF NOT EXISTS client_org_name VARCHAR(255),
    ADD COLUMN IF NOT EXISTS client_contact_person VARCHAR(255),
    ADD COLUMN IF NOT EXISTS client_designation VARCHAR(128),
    ADD COLUMN IF NOT EXISTS client_email VARCHAR(255),
    ADD COLUMN IF NOT EXISTS client_phone VARCHAR(64),
    ADD COLUMN IF NOT EXISTS client_website VARCHAR(255),
    ADD COLUMN IF NOT EXISTS client_notes TEXT,
    ADD COLUMN IF NOT EXISTS site_property_name VARCHAR(255),
    ADD COLUMN IF NOT EXISTS latitude NUMERIC(10, 7),
    ADD COLUMN IF NOT EXISTS longitude NUMERIC(10, 7),
    ADD COLUMN IF NOT EXISTS primary_contact_designation VARCHAR(128),
    ADD COLUMN IF NOT EXISTS emergency_contact_name VARCHAR(255),
    ADD COLUMN IF NOT EXISTS emergency_contact_phone VARCHAR(64),
    ADD COLUMN IF NOT EXISTS emergency_contact_availability VARCHAR(128),
    ADD COLUMN IF NOT EXISTS emergency_contact_notes TEXT,
    ADD COLUMN IF NOT EXISTS capture_start_date DATE,
    ADD COLUMN IF NOT EXISTS expected_capture_completion DATE,
    ADD COLUMN IF NOT EXISTS access_policy VARCHAR(64) DEFAULT 'assigned_only',
    ADD COLUMN IF NOT EXISTS capture_method VARCHAR(64) DEFAULT 'Smartphone Video Capture',
    ADD COLUMN IF NOT EXISTS capture_instructions TEXT,
    ADD COLUMN IF NOT EXISTS site_access_requirements TEXT,
    ADD COLUMN IF NOT EXISTS restricted_areas TEXT,
    ADD COLUMN IF NOT EXISTS special_capture_notes TEXT,
    ADD COLUMN IF NOT EXISTS project_config JSONB DEFAULT '{
        "enable_viewer": true,
        "enable_search": true,
        "enable_navigation": true,
        "enable_poi_management": true,
        "enable_model_versioning": true,
        "quality_validation_required": true,
        "require_admin_approval": true,
        "notify_processing": true,
        "notify_quality_failure": true,
        "notify_rescan": true,
        "notify_publication": true
    }'::jsonb;

-- 2. Extend project_structures table
ALTER TABLE project_structures
    ADD COLUMN IF NOT EXISTS building_code VARCHAR(64),
    ADD COLUMN IF NOT EXISTS access_notes TEXT,
    ADD COLUMN IF NOT EXISTS site_restrictions TEXT,
    ADD COLUMN IF NOT EXISTS capture_instructions TEXT,
    ADD COLUMN IF NOT EXISTS working_hours VARCHAR(128);

-- 3. Extend spatial_levels (Floors) table
ALTER TABLE spatial_levels
    ADD COLUMN IF NOT EXISTS floor_description TEXT,
    ADD COLUMN IF NOT EXISTS capture_status VARCHAR(64) DEFAULT 'not_started',
    ADD COLUMN IF NOT EXISTS processing_status VARCHAR(64) DEFAULT 'not_started',
    ADD COLUMN IF NOT EXISTS quality_status VARCHAR(64) DEFAULT 'not_started',
    ADD COLUMN IF NOT EXISTS current_model_version VARCHAR(32);

-- 4. Create project_updates table (Operational progress feed)
CREATE TABLE IF NOT EXISTS project_updates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    author_id UUID REFERENCES users(id) ON DELETE SET NULL,
    update_type VARCHAR(64) NOT NULL DEFAULT 'General Update',
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    priority VARCHAR(32) NOT NULL DEFAULT 'Normal',
    building_id UUID REFERENCES project_structures(id) ON DELETE SET NULL,
    floor_id UUID REFERENCES spatial_levels(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_project_updates_project ON project_updates(project_id);
