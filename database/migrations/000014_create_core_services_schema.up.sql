-- ============================================================
-- VĀSTU INDOOR SPATIAL COMPUTING PLATFORM
-- Migration: 000014_create_core_services_schema.up.sql
-- Description: Core Services Schema (Captures, Uploads, Jobs, Models, POIs, Navigation, Viewer)
-- ============================================================

-- 1. Captures Table (Session Metadata & Device Intrinsics)
CREATE TABLE IF NOT EXISTS captures (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    structure_id UUID REFERENCES project_structures(id) ON DELETE SET NULL,
    level_id UUID REFERENCES spatial_levels(id) ON DELETE SET NULL,
    section_id UUID REFERENCES spatial_sections(id) ON DELETE SET NULL,
    operator_id UUID REFERENCES users(id) ON DELETE SET NULL,
    device_model VARCHAR(128) NOT NULL,
    device_os VARCHAR(64) NOT NULL,
    device_app_version VARCHAR(32) NOT NULL,
    camera_intrinsics JSONB, -- fx, fy, cx, cy, distortion, resolution
    imu_rate_hz INT DEFAULT 100,
    has_lidar BOOLEAN DEFAULT FALSE,
    capture_mode VARCHAR(64) NOT NULL DEFAULT 'rgb_imu', -- 'rgb_imu', 'rgb_lidar', 'rescan_targeted'
    duration_seconds NUMERIC(8, 2) DEFAULT 0,
    frames_count INT DEFAULT 0,
    file_size_bytes BIGINT DEFAULT 0,
    trajectory_length_meters NUMERIC(8, 2) DEFAULT 0,
    quality_score NUMERIC(5, 2) DEFAULT 0, -- 0-100 quality rating
    blur_score NUMERIC(5, 2) DEFAULT 0,
    lighting_score NUMERIC(5, 2) DEFAULT 0,
    status VARCHAR(32) NOT NULL DEFAULT 'recording', -- 'recording', 'uploaded', 'validating', 'processing', 'completed', 'failed'
    manifest_url TEXT,
    video_url TEXT,
    imu_url TEXT,
    lidar_url TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_captures_project ON captures(project_id);
CREATE INDEX IF NOT EXISTS idx_captures_status ON captures(status);
CREATE INDEX IF NOT EXISTS idx_captures_operator ON captures(operator_id);

-- 2. Resumable Upload Sessions & Chunks Table
CREATE TABLE IF NOT EXISTS upload_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    capture_id UUID REFERENCES captures(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    file_name VARCHAR(255) NOT NULL,
    file_type VARCHAR(64) NOT NULL, -- 'video', 'imu', 'lidar', 'manifest'
    total_size_bytes BIGINT NOT NULL,
    chunk_size_bytes BIGINT NOT NULL DEFAULT 5242880, -- 5MB chunks default
    total_chunks INT NOT NULL,
    uploaded_chunks INT NOT NULL DEFAULT 0,
    sha256_checksum VARCHAR(64),
    target_storage_path TEXT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'in_progress', -- 'in_progress', 'assembling', 'completed', 'aborted', 'expired'
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '24 hours'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_uploads_capture ON upload_sessions(capture_id);
CREATE INDEX IF NOT EXISTS idx_uploads_status ON upload_sessions(status);

CREATE TABLE IF NOT EXISTS upload_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES upload_sessions(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    size_bytes BIGINT NOT NULL,
    sha256_hash VARCHAR(64),
    chunk_file_path TEXT NOT NULL,
    is_uploaded BOOLEAN NOT NULL DEFAULT TRUE,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(session_id, chunk_index)
);

-- 3. Processing Jobs & Diagnostic Logs
CREATE TABLE IF NOT EXISTS processing_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    capture_id UUID REFERENCES captures(id) ON DELETE SET NULL,
    stage VARCHAR(64) NOT NULL DEFAULT 'queued', -- 'queued', 'preprocessing', 'sfm_tracking', 'depth_estimation', 'point_cloud', 'meshing', 'texturing', 'semantic_segmentation', 'cell_fusion', 'completed', 'failed'
    progress_percentage INT NOT NULL DEFAULT 0,
    priority INT NOT NULL DEFAULT 5, -- 1-10
    worker_node_id VARCHAR(128),
    error_code VARCHAR(64),
    error_message TEXT,
    stage_durations JSONB DEFAULT '{}'::jsonb, -- { "sfm": 120, "meshing": 45 }
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_jobs_project ON processing_jobs(project_id);
CREATE INDEX IF NOT EXISTS idx_jobs_stage ON processing_jobs(stage);
CREATE INDEX IF NOT EXISTS idx_jobs_capture ON processing_jobs(capture_id);

CREATE TABLE IF NOT EXISTS job_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID NOT NULL REFERENCES processing_jobs(id) ON DELETE CASCADE,
    stage VARCHAR(64) NOT NULL,
    log_level VARCHAR(16) NOT NULL DEFAULT 'info', -- 'debug', 'info', 'warn', 'error'
    message TEXT NOT NULL,
    meta JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_job_logs_job ON job_logs(job_id);

-- 4. 3D Spatial Models & Artifacts Registry
CREATE TABLE IF NOT EXISTS spatial_models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    level_id UUID REFERENCES spatial_levels(id) ON DELETE SET NULL,
    section_id UUID REFERENCES spatial_sections(id) ON DELETE SET NULL,
    version VARCHAR(32) NOT NULL DEFAULT 'v1.0.0',
    title VARCHAR(255) NOT NULL,
    description TEXT,
    bounding_box JSONB, -- min [x,y,z], max [x,y,z], center [x,y,z]
    coordinate_frame JSONB, -- origin, rotation matrix, scale
    total_vertices BIGINT DEFAULT 0,
    total_faces BIGINT DEFAULT 0,
    point_density_sqm NUMERIC(10, 2) DEFAULT 0,
    precision_deviation_cm NUMERIC(4, 2) DEFAULT 0,
    is_active_version BOOLEAN DEFAULT TRUE,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_models_project ON spatial_models(project_id);
CREATE INDEX IF NOT EXISTS idx_models_active ON spatial_models(is_active_version);

CREATE TABLE IF NOT EXISTS model_artifacts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_id UUID NOT NULL REFERENCES spatial_models(id) ON DELETE CASCADE,
    artifact_type VARCHAR(64) NOT NULL, -- 'point_cloud_ply', 'point_cloud_las', 'mesh_gltf', 'mesh_obj', 'gaussian_splat', 'texture_atlas', 'lod0', 'lod1', 'lod2'
    lod_level INT DEFAULT 0,
    file_format VARCHAR(16) NOT NULL, -- 'ply', 'gltf', 'glb', 'obj', 'splat', 'las'
    file_size_bytes BIGINT NOT NULL,
    file_url TEXT NOT NULL,
    sha256_hash VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_artifacts_model ON model_artifacts(model_id);

-- 5. 3D Points of Interest (POIs) & Semantic Annotations
CREATE TABLE IF NOT EXISTS spatial_pois (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    level_id UUID REFERENCES spatial_levels(id) ON DELETE SET NULL,
    section_id UUID REFERENCES spatial_sections(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(64) NOT NULL DEFAULT 'custom', -- 'room_label', 'asset', 'equipment', 'emergency_exit', 'restroom', 'elevator', 'sensor', 'staircase', 'custom'
    pos_x NUMERIC(12, 4) NOT NULL DEFAULT 0.0,
    pos_y NUMERIC(12, 4) NOT NULL DEFAULT 0.0,
    pos_z NUMERIC(12, 4) NOT NULL DEFAULT 0.0,
    normal_x NUMERIC(6, 4) DEFAULT 0.0,
    normal_y NUMERIC(6, 4) DEFAULT 1.0,
    normal_z NUMERIC(6, 4) DEFAULT 0.0,
    icon_key VARCHAR(64) DEFAULT 'map-pin',
    color_hex VARCHAR(16) DEFAULT '#dfb873',
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    custom_metadata JSONB DEFAULT '{}'::jsonb,
    attachments JSONB DEFAULT '[]'::jsonb,
    camera_viewpoint JSONB, -- pos, target, fov for 3D camera zoom
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pois_project ON spatial_pois(project_id);
CREATE INDEX IF NOT EXISTS idx_pois_category ON spatial_pois(category);
CREATE INDEX IF NOT EXISTS idx_pois_level ON spatial_pois(level_id);

-- 6. Indoor Navigation Graph (Nodes & Edges)
CREATE TABLE IF NOT EXISTS nav_nodes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    level_id UUID REFERENCES spatial_levels(id) ON DELETE SET NULL,
    section_id UUID REFERENCES spatial_sections(id) ON DELETE SET NULL,
    node_type VARCHAR(32) NOT NULL DEFAULT 'walkway', -- 'walkway', 'door', 'intersection', 'stair_entry', 'elevator_door', 'ramp_entry', 'poi_anchor'
    pos_x NUMERIC(12, 4) NOT NULL,
    pos_y NUMERIC(12, 4) NOT NULL,
    pos_z NUMERIC(12, 4) NOT NULL,
    is_wheelchair_accessible BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nav_nodes_project ON nav_nodes(project_id);
CREATE INDEX IF NOT EXISTS idx_nav_nodes_level ON nav_nodes(level_id);

CREATE TABLE IF NOT EXISTS nav_edges (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    from_node_id UUID NOT NULL REFERENCES nav_nodes(id) ON DELETE CASCADE,
    to_node_id UUID NOT NULL REFERENCES nav_nodes(id) ON DELETE CASCADE,
    edge_type VARCHAR(32) NOT NULL DEFAULT 'corridor', -- 'corridor', 'door', 'stairs', 'elevator', 'ramp'
    distance_meters NUMERIC(8, 3) NOT NULL,
    is_bidirectional BOOLEAN NOT NULL DEFAULT TRUE,
    is_wheelchair_accessible BOOLEAN NOT NULL DEFAULT TRUE,
    weight_modifier NUMERIC(4, 2) NOT NULL DEFAULT 1.0, -- stairs have higher weight for wheelchair routing
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(from_node_id, to_node_id)
);

CREATE INDEX IF NOT EXISTS idx_nav_edges_project ON nav_edges(project_id);
CREATE INDEX IF NOT EXISTS idx_nav_edges_from ON nav_edges(from_node_id);
CREATE INDEX IF NOT EXISTS idx_nav_edges_to ON nav_edges(to_node_id);

-- 7. Viewer State, Camera Bookmarks & Annotations
CREATE TABLE IF NOT EXISTS viewer_bookmarks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    camera_position JSONB NOT NULL, -- { x, y, z }
    camera_target JSONB NOT NULL,   -- { x, y, z }
    camera_fov NUMERIC(5, 2) DEFAULT 60.0,
    visible_layers JSONB DEFAULT '["mesh", "pois", "annotations"]'::jsonb,
    is_shared BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_viewer_bookmarks_project ON viewer_bookmarks(project_id);

CREATE TABLE IF NOT EXISTS viewer_annotations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    annotation_type VARCHAR(32) NOT NULL DEFAULT 'distance', -- 'distance', 'area', 'volume', 'text_note', 'angle'
    points_3d JSONB NOT NULL, -- array of [x, y, z] points
    calculated_value NUMERIC(12, 4), -- meters, sq meters, cubic meters
    unit VARCHAR(16) DEFAULT 'meters',
    label VARCHAR(255),
    color_hex VARCHAR(16) DEFAULT '#dfb873',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_viewer_annotations_project ON viewer_annotations(project_id);
