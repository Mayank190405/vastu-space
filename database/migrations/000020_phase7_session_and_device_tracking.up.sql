-- ============================================================
-- VĀSTU INDOOR SPATIAL COMPUTING PLATFORM
-- Migration: 000020_phase7_session_and_device_tracking.up.sql
-- Description: Phase 7 Session Management, Devices, Heartbeats, and Real-Time Pipeline Stages
-- ============================================================

-- 1. Ensure project_structures has a default building if not present
-- (Spatial structure / building anchor for floors)

-- 2. Enhanced Rooms / Sections Table Support
ALTER TABLE spatial_sections
    ADD COLUMN IF NOT EXISTS capture_status VARCHAR(64) NOT NULL DEFAULT 'UNCAPTURED',
    ADD COLUMN IF NOT EXISTS provisional_floorplan_url TEXT,
    ADD COLUMN IF NOT EXISTS floorplan_data JSONB,
    ADD COLUMN IF NOT EXISTS dimensions_validated JSONB, -- { "length_m": 5.4, "width_m": 4.2, "height_m": 2.8 }
    ADD COLUMN IF NOT EXISTS coverage_percentage NUMERIC(5, 2) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS quality_score NUMERIC(5, 2) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS last_capture_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS rescan_requested BOOLEAN DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_spatial_sections_level ON spatial_sections(level_id);
CREATE INDEX IF NOT EXISTS idx_spatial_sections_status ON spatial_sections(capture_status);

-- 3. Connected Devices Table
CREATE TABLE IF NOT EXISTS devices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_uuid VARCHAR(128) NOT NULL UNIQUE,
    device_model VARCHAR(128) NOT NULL,
    device_os VARCHAR(64) NOT NULL,
    app_version VARCHAR(32) NOT NULL,
    battery_level NUMERIC(4, 2) DEFAULT -1.0, -- 0.0 to 1.0, -1 if unknown
    arkit_tracking_status VARCHAR(64) DEFAULT 'NORMAL',
    local_ai_status VARCHAR(64) DEFAULT 'READY',
    network_type VARCHAR(32) DEFAULT 'WIFI',
    current_session_id VARCHAR(128),
    current_project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    current_room_id UUID REFERENCES spatial_sections(id) ON DELETE SET NULL,
    last_heartbeat_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_devices_uuid ON devices(device_uuid);
CREATE INDEX IF NOT EXISTS idx_devices_last_heartbeat ON devices(last_heartbeat_at);

-- 4. Device Heartbeats Telemetry Table
CREATE TABLE IF NOT EXISTS device_heartbeats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_uuid VARCHAR(128) NOT NULL REFERENCES devices(device_uuid) ON DELETE CASCADE,
    session_id VARCHAR(128),
    battery_level NUMERIC(4, 2) DEFAULT -1.0,
    arkit_tracking_status VARCHAR(64) NOT NULL,
    local_ai_status VARCHAR(64) NOT NULL,
    recording_state VARCHAR(32) NOT NULL, -- 'IDLE', 'RECORDING', 'PAUSED', 'UPLOADING'
    network_type VARCHAR(32) DEFAULT 'WIFI',
    storage_free_mb BIGINT DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_device_heartbeats_device ON device_heartbeats(device_uuid);
CREATE INDEX IF NOT EXISTS idx_device_heartbeats_created ON device_heartbeats(created_at);

-- 5. Capture Sessions Table (QR Session Creator & Authorization)
CREATE TABLE IF NOT EXISTS capture_sessions (
    id VARCHAR(128) PRIMARY KEY, -- e.g. sess_living_room_01
    session_code VARCHAR(32) NOT NULL UNIQUE, -- e.g. #S-1042
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    floor_id UUID REFERENCES spatial_levels(id) ON DELETE SET NULL,
    room_id UUID REFERENCES spatial_sections(id) ON DELETE SET NULL,
    room_name VARCHAR(255) NOT NULL,
    operator_name VARCHAR(255),
    challenge_token VARCHAR(255) NOT NULL UNIQUE,
    nonce VARCHAR(128) NOT NULL,
    grant_token VARCHAR(255),
    device_id VARCHAR(128),
    status VARCHAR(32) NOT NULL DEFAULT 'CREATED', -- 'CREATED', 'AUTHORIZED', 'RECORDING', 'UPLOADING', 'COMPLETED', 'EXPIRED', 'REVOKED'
    expires_at TIMESTAMPTZ NOT NULL,
    redeemed_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    capture_package_url TEXT,
    quality_summary JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_capture_sessions_project ON capture_sessions(project_id);
CREATE INDEX IF NOT EXISTS idx_capture_sessions_room ON capture_sessions(room_id);
CREATE INDEX IF NOT EXISTS idx_capture_sessions_status ON capture_sessions(status);
CREATE INDEX IF NOT EXISTS idx_capture_sessions_challenge ON capture_sessions(challenge_token);

-- 6. Pipeline Stages Table (Real-Time 18-Stage Execution Tracking)
CREATE TABLE IF NOT EXISTS pipeline_stages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(128) NOT NULL REFERENCES capture_sessions(id) ON DELETE CASCADE,
    job_id UUID REFERENCES processing_jobs(id) ON DELETE SET NULL,
    stage_name VARCHAR(64) NOT NULL,
    stage_order INT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING', -- 'PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'RETRYING', 'CANCELLED', 'SKIPPED'
    progress_percentage INT DEFAULT 0,
    responsible_worker VARCHAR(128) NOT NULL, -- e.g. 'iPhone 15 Pro (Mobile)', 'SfM-Worker-01 (GPU)'
    error_details TEXT,
    retry_count INT DEFAULT 0,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(session_id, stage_name)
);

CREATE INDEX IF NOT EXISTS idx_pipeline_stages_session ON pipeline_stages(session_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_stages_status ON pipeline_stages(status);

-- 7. Durable Pipeline Events Log
CREATE TABLE IF NOT EXISTS pipeline_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(128) NOT NULL REFERENCES capture_sessions(id) ON DELETE CASCADE,
    stage_name VARCHAR(64) NOT NULL,
    event_type VARCHAR(64) NOT NULL, -- 'STAGE_STARTED', 'STAGE_PROGRESS', 'STAGE_COMPLETED', 'STAGE_FAILED'
    sequence_number BIGSERIAL,
    payload JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pipeline_events_session ON pipeline_events(session_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_events_seq ON pipeline_events(sequence_number);

