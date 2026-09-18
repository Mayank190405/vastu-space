-- Migration: 000019_add_capture_sop_and_assignment.up.sql
-- Description: Supports automated SOP generation, Reconnaissance Video, Operator Assignment, and Area-by-Area Capture with Floor Plan Projection

ALTER TABLE captures
    ADD COLUMN IF NOT EXISTS floor_id UUID REFERENCES project_floors(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS assigned_to UUID REFERENCES users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS recon_video_url TEXT,
    ADD COLUMN IF NOT EXISTS capture_sop JSONB,
    ADD COLUMN IF NOT EXISTS current_phase VARCHAR(64) NOT NULL DEFAULT 'ASSIGNED',
    ADD COLUMN IF NOT EXISTS zone_progress JSONB DEFAULT '[]'::jsonb;

CREATE INDEX IF NOT EXISTS idx_captures_floor ON captures(floor_id);
CREATE INDEX IF NOT EXISTS idx_captures_assigned ON captures(assigned_to);
CREATE INDEX IF NOT EXISTS idx_captures_phase ON captures(current_phase);
