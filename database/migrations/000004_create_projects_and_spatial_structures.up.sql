-- ============================================================
-- VĀSTU INDOOR SPATIAL COMPUTING PLATFORM
-- Migration: 000004_create_projects_and_spatial_structures.up.sql
-- Description: Configurable Multi-Typology Spatial Projects, Buildings, Levels, and Sections
-- ============================================================

-- 1. Projects Table
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL,
    description TEXT,
    client_name VARCHAR(255),
    location_address TEXT,
    location_city VARCHAR(128),
    location_state VARCHAR(128),
    location_country VARCHAR(128) DEFAULT 'India',
    typology VARCHAR(64) NOT NULL DEFAULT 'commercial_office',
    total_area_sqft NUMERIC(12, 2) DEFAULT 0,
    total_area_sqm NUMERIC(12, 2) DEFAULT 0,
    ceiling_height_meters NUMERIC(6, 2) DEFAULT 3.0,
    total_floors_count INT NOT NULL DEFAULT 1,
    total_halls_count INT NOT NULL DEFAULT 0,
    total_rooms_count INT NOT NULL DEFAULT 0,
    total_corridors_count INT NOT NULL DEFAULT 0,
    precision_gate_cm NUMERIC(4, 2) NOT NULL DEFAULT 2.5,
    status VARCHAR(32) NOT NULL DEFAULT 'draft',
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_projects_org ON projects(org_id);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
CREATE INDEX IF NOT EXISTS idx_projects_typology ON projects(typology);

-- 2. Project Structures / Buildings Table
CREATE TABLE IF NOT EXISTS project_structures (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    structure_type VARCHAR(64) NOT NULL DEFAULT 'building',
    floors_count INT NOT NULL DEFAULT 1,
    halls_count INT NOT NULL DEFAULT 0,
    rooms_count INT NOT NULL DEFAULT 0,
    corridors_count INT NOT NULL DEFAULT 0,
    area_sqm NUMERIC(12, 2) DEFAULT 0,
    ceiling_height_meters NUMERIC(6, 2) DEFAULT 3.0,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_structures_project ON project_structures(project_id);

-- 3. Spatial Levels / Floors / Decks Table
CREATE TABLE IF NOT EXISTS spatial_levels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    structure_id UUID NOT NULL REFERENCES project_structures(id) ON DELETE CASCADE,
    level_number INT NOT NULL DEFAULT 0,
    level_name VARCHAR(128) NOT NULL,
    elevation_meters NUMERIC(6, 2) DEFAULT 0.0,
    halls_count INT NOT NULL DEFAULT 0,
    rooms_count INT NOT NULL DEFAULT 0,
    corridors_count INT NOT NULL DEFAULT 0,
    area_sqm NUMERIC(12, 2) DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_levels_structure ON spatial_levels(structure_id);

-- 4. Spatial Sections / Rooms / Halls / Corridors Table
CREATE TABLE IF NOT EXISTS spatial_sections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    level_id UUID NOT NULL REFERENCES spatial_levels(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    section_type VARCHAR(64) NOT NULL DEFAULT 'room', -- 'room', 'hall', 'corridor', 'atrium', 'bay', 'cell', 'vault', 'staircase', 'elevator'
    area_sqm NUMERIC(10, 2) DEFAULT 0,
    bounding_box JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sections_level ON spatial_sections(level_id);
