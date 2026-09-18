-- Migration: 000018_project_creation_and_configuration.down.sql
DROP TABLE IF EXISTS project_members;
DROP TABLE IF EXISTS floor_plans;
DROP TABLE IF EXISTS project_floors;
DROP TABLE IF EXISTS project_addresses;
ALTER TABLE projects
    DROP COLUMN IF EXISTS cover_image_id,
    DROP COLUMN IF EXISTS cover_image_url,
    DROP COLUMN IF EXISTS contact_name,
    DROP COLUMN IF EXISTS contact_email,
    DROP COLUMN IF EXISTS contact_phone,
    DROP COLUMN IF EXISTS project_type,
    DROP COLUMN IF EXISTS custom_type;
