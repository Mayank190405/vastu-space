-- Migration: 000011_add_apple_auth_provider.up.sql
-- Description: Add Apple authentication provider and apple_id column

ALTER TYPE auth_provider_enum ADD VALUE IF NOT EXISTS 'apple';

ALTER TABLE users ADD COLUMN IF NOT EXISTS apple_id VARCHAR(255);

CREATE UNIQUE INDEX IF NOT EXISTS users_apple_id_key ON users(apple_id) WHERE apple_id IS NOT NULL;
