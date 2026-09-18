-- Migration: 000008_normalize_project_dates.up.sql
ALTER TABLE projects 
  ALTER COLUMN start_date TYPE VARCHAR(64) USING start_date::text,
  ALTER COLUMN expected_completion_date TYPE VARCHAR(64) USING expected_completion_date::text,
  ALTER COLUMN capture_start_date TYPE VARCHAR(64) USING capture_start_date::text,
  ALTER COLUMN expected_capture_completion TYPE VARCHAR(64) USING expected_capture_completion::text;
