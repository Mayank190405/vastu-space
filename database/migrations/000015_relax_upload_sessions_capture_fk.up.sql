-- Relax strict foreign key constraint on upload_sessions(capture_id) so client-generated capture sessions can initiate uploads cleanly before/after capture metadata registration
ALTER TABLE upload_sessions DROP CONSTRAINT IF EXISTS upload_sessions_capture_id_fkey;
