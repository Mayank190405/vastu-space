-- ============================================================
-- Migration: 000012_create_user_auth_providers.up.sql
-- Description: Multi-provider Authentication linking table (Google, Apple, etc.)
-- ============================================================

CREATE TABLE IF NOT EXISTS user_auth_providers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(32) NOT NULL,
    provider_user_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_user_provider_user_id UNIQUE (provider, provider_user_id),
    CONSTRAINT uq_user_id_provider UNIQUE (user_id, provider)
);

CREATE INDEX IF NOT EXISTS idx_user_auth_providers_user ON user_auth_providers(user_id);
CREATE INDEX IF NOT EXISTS idx_user_auth_providers_lookup ON user_auth_providers(provider, provider_user_id);

-- Backfill any existing google_id
INSERT INTO user_auth_providers (user_id, provider, provider_user_id, created_at)
SELECT id, 'google', google_id, created_at FROM users 
WHERE google_id IS NOT NULL AND google_id != ''
ON CONFLICT (provider, provider_user_id) DO NOTHING;

-- Backfill any existing apple_id
INSERT INTO user_auth_providers (user_id, provider, provider_user_id, created_at)
SELECT id, 'apple', apple_id, created_at FROM users 
WHERE apple_id IS NOT NULL AND apple_id != ''
ON CONFLICT (provider, provider_user_id) DO NOTHING;
