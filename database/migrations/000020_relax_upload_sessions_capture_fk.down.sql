ALTER TABLE upload_sessions ADD CONSTRAINT upload_sessions_capture_id_fkey FOREIGN KEY (capture_id) REFERENCES captures(id) ON DELETE CASCADE;
