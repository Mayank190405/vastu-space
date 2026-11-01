ALTER TABLE capture_sessions
 ADD COLUMN IF NOT EXISTS capture_id UUID REFERENCES captures(id),
 ADD COLUMN IF NOT EXISTS upload_id UUID REFERENCES upload_sessions(id),
 ADD COLUMN IF NOT EXISTS job_id UUID REFERENCES processing_jobs(id),
 ADD COLUMN IF NOT EXISTS video_url TEXT,
 ADD COLUMN IF NOT EXISTS raw_object_key TEXT,
 ADD COLUMN IF NOT EXISTS upload_verified_at TIMESTAMPTZ,
 ADD COLUMN IF NOT EXISTS viewer_url TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS capture_session_capture_idx ON capture_sessions(capture_id);
