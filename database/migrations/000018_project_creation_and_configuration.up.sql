-- Migration: 000018_project_creation_and_configuration.up.sql
-- Description: Comprehensive Project Creation, Structured Address, Floors, Floor Plans (Upload/Draw), and Project Members

-- 1. Extend projects table with escalation columns
ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS cover_image_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS cover_image_url TEXT,
    ADD COLUMN IF NOT EXISTS contact_name VARCHAR(255),
    ADD COLUMN IF NOT EXISTS contact_email VARCHAR(255),
    ADD COLUMN IF NOT EXISTS contact_phone VARCHAR(64),
    ADD COLUMN IF NOT EXISTS project_type VARCHAR(64) NOT NULL DEFAULT 'Building',
    ADD COLUMN IF NOT EXISTS custom_type VARCHAR(128);

-- 2. Structured Project Address table
CREATE TABLE IF NOT EXISTS project_addresses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    address_line_1 TEXT NOT NULL,
    address_line_2 TEXT,
    area VARCHAR(255),
    city VARCHAR(128) NOT NULL,
    state VARCHAR(128) NOT NULL,
    pincode VARCHAR(32) NOT NULL,
    country VARCHAR(128) NOT NULL DEFAULT 'India',
    latitude NUMERIC(10, 7),
    longitude NUMERIC(10, 7),
    place_id VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_project_address UNIQUE(project_id)
);

CREATE INDEX IF NOT EXISTS idx_project_addresses_project ON project_addresses(project_id);
CREATE INDEX IF NOT EXISTS idx_project_addresses_city ON project_addresses(city);

-- 3. Project Floors table (independent entity for building/structure levels)
CREATE TABLE IF NOT EXISTS project_floors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    floor_number INT NOT NULL DEFAULT 0,
    floor_type VARCHAR(64) NOT NULL DEFAULT 'Ground Floor',
    area_value NUMERIC(12, 2) NOT NULL DEFAULT 0,
    area_unit VARCHAR(16) NOT NULL DEFAULT 'SQFT',
    height_value NUMERIC(6, 2) NOT NULL DEFAULT 10,
    height_unit VARCHAR(16) NOT NULL DEFAULT 'FT',
    sequence INT NOT NULL DEFAULT 1,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_project_floors_project ON project_floors(project_id);
CREATE INDEX IF NOT EXISTS idx_project_floors_sequence ON project_floors(project_id, sequence);

-- 4. Floor Plans table (supports UPLOADED and DRAWN vector floor plans)
CREATE TABLE IF NOT EXISTS floor_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    floor_id UUID NOT NULL REFERENCES project_floors(id) ON DELETE CASCADE,
    plan_type VARCHAR(32) NOT NULL DEFAULT 'UPLOADED', -- 'UPLOADED' or 'DRAWN'
    file_id VARCHAR(255),
    file_url TEXT,
    original_file_name VARCHAR(255),
    file_size_bytes BIGINT DEFAULT 0,
    mime_type VARCHAR(128),
    canvas_width NUMERIC(10, 2) DEFAULT 1200,
    canvas_height NUMERIC(10, 2) DEFAULT 800,
    scale_ratio NUMERIC(10, 4) DEFAULT 1.0,
    drawing_data JSONB DEFAULT '{"objects": []}'::jsonb,
    preview_file_id VARCHAR(255),
    preview_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_floor_plan UNIQUE(floor_id)
);

CREATE INDEX IF NOT EXISTS idx_floor_plans_floor ON floor_plans(floor_id);

-- 5. Project Members table (organization users with project-specific roles & permissions)
CREATE TABLE IF NOT EXISTS project_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_role VARCHAR(64) NOT NULL DEFAULT 'Viewer',
    permissions JSONB DEFAULT '[]'::jsonb,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    assigned_by UUID REFERENCES users(id) ON DELETE SET NULL,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_project_member UNIQUE(project_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_project_members_project ON project_members(project_id);
CREATE INDEX IF NOT EXISTS idx_project_members_user ON project_members(user_id);
