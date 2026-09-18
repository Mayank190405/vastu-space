-- ============================================================
-- VĀSTU INDOOR SPATIAL COMPUTING PLATFORM
-- Migration: 000016_create_spatial_cells_quality_rescan_schema.up.sql
-- Description: Supports Points 25-31:
--   - Point 25: spatial_cells (3D cellular partitioning)
--   - Point 27: quality_reports (7-score quality gating)
--   - Point 28: rescan_requests (targeted mobile rescan workflow)
--   - Point 30: spatial_models versioning & immutable lineage
-- ============================================================

-- 1. Spatial Cells Table (Point 25)
CREATE TABLE IF NOT EXISTS spatial_cells (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    model_id UUID REFERENCES spatial_models(id) ON DELETE CASCADE,
    cell_x INT NOT NULL,
    cell_y INT NOT NULL,
    cell_z INT NOT NULL,
    cell_size_m NUMERIC(6, 2) NOT NULL DEFAULT 1.00,
    min_x NUMERIC(12, 4) NOT NULL,
    min_y NUMERIC(12, 4) NOT NULL,
    min_z NUMERIC(12, 4) NOT NULL,
    max_x NUMERIC(12, 4) NOT NULL,
    max_y NUMERIC(12, 4) NOT NULL,
    max_z NUMERIC(12, 4) NOT NULL,
    geom_bbox GEOMETRY(POLYHEDRALSURFACEZ, 0) NULL,
    geometry_stats JSONB DEFAULT '{"vertices": 0, "faces": 0}'::jsonb,
    observation_views INT DEFAULT 0,
    texture_chart_ids TEXT[] DEFAULT ARRAY[]::TEXT[],
    semantic_object_ids TEXT[] DEFAULT ARRAY[]::TEXT[],
    quality_score NUMERIC(5, 2) DEFAULT 0.0,
    is_low_confidence BOOLEAN DEFAULT FALSE,
    neighbor_cell_ids UUID[] DEFAULT ARRAY[]::UUID[],
    version INT NOT NULL DEFAULT 1,
    is_dirty BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(project_id, model_id, cell_x, cell_y, cell_z)
);

CREATE INDEX IF NOT EXISTS idx_spatial_cells_project ON spatial_cells(project_id);
CREATE INDEX IF NOT EXISTS idx_spatial_cells_model ON spatial_cells(model_id);
CREATE INDEX IF NOT EXISTS idx_spatial_cells_coords ON spatial_cells(cell_x, cell_y, cell_z);
CREATE INDEX IF NOT EXISTS idx_spatial_cells_quality ON spatial_cells(quality_score);
CREATE INDEX IF NOT EXISTS idx_spatial_cells_low_conf ON spatial_cells(is_low_confidence);
CREATE INDEX IF NOT EXISTS idx_spatial_cells_geom_bbox ON spatial_cells USING GIST(geom_bbox);

-- 2. Quality Reports Table (Point 27)
CREATE TABLE IF NOT EXISTS quality_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    job_id UUID REFERENCES processing_jobs(id) ON DELETE SET NULL,
    model_id UUID REFERENCES spatial_models(id) ON DELETE SET NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING', -- 'PASS', 'FAIL', 'WARNING'
    overall_score NUMERIC(5, 2) NOT NULL DEFAULT 0.0,
    geometry_score NUMERIC(5, 2) NOT NULL DEFAULT 0.0,
    tracking_score NUMERIC(5, 2) NOT NULL DEFAULT 0.0,
    coverage_score NUMERIC(5, 2) NOT NULL DEFAULT 0.0,
    texture_score NUMERIC(5, 2) NOT NULL DEFAULT 0.0,
    semantic_score NUMERIC(5, 2) NOT NULL DEFAULT 0.0,
    cell_consistency_score NUMERIC(5, 2) NOT NULL DEFAULT 0.0,
    navigation_score NUMERIC(5, 2) NOT NULL DEFAULT 0.0,
    low_confidence_cells JSONB DEFAULT '[]'::jsonb,
    failure_reasons TEXT[] DEFAULT ARRAY[]::TEXT[],
    recommendations TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_quality_reports_project ON quality_reports(project_id);
CREATE INDEX IF NOT EXISTS idx_quality_reports_status ON quality_reports(status);
CREATE INDEX IF NOT EXISTS idx_quality_reports_job ON quality_reports(job_id);

-- 3. Targeted Rescan Requests Table (Point 28)
CREATE TABLE IF NOT EXISTS rescan_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    quality_report_id UUID REFERENCES quality_reports(id) ON DELETE SET NULL,
    cell_id UUID REFERENCES spatial_cells(id) ON DELETE SET NULL,
    assigned_operator_id UUID REFERENCES users(id) ON DELETE SET NULL,
    area_name VARCHAR(255) NOT NULL,
    failure_reason VARCHAR(255) NOT NULL,
    mobile_instruction TEXT NOT NULL,
    target_center_x NUMERIC(12, 4) NOT NULL,
    target_center_y NUMERIC(12, 4) NOT NULL,
    target_center_z NUMERIC(12, 4) NOT NULL,
    target_radius_m NUMERIC(6, 2) NOT NULL DEFAULT 2.50,
    status VARCHAR(32) NOT NULL DEFAULT 'pending', -- 'pending', 'assigned', 'capturing', 'uploaded', 'fused', 'ignored'
    rescan_capture_id UUID REFERENCES captures(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rescan_requests_project ON rescan_requests(project_id);
CREATE INDEX IF NOT EXISTS idx_rescan_requests_status ON rescan_requests(status);
CREATE INDEX IF NOT EXISTS idx_rescan_requests_operator ON rescan_requests(assigned_operator_id);

-- 4. Enhance spatial_models for Immutability, Lineage & Version Registry (Point 30)
ALTER TABLE spatial_models
    ADD COLUMN IF NOT EXISTS parent_model_id UUID REFERENCES spatial_models(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS is_immutable BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS quality_report_id UUID REFERENCES quality_reports(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS source_capture_id UUID REFERENCES captures(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS lineage_depth INT NOT NULL DEFAULT 1;

CREATE INDEX IF NOT EXISTS idx_spatial_models_parent ON spatial_models(parent_model_id);
CREATE INDEX IF NOT EXISTS idx_spatial_models_immutable ON spatial_models(is_immutable);
