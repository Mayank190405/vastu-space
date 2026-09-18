-- ============================================================
-- VĀSTU INDOOR SPATIAL COMPUTING PLATFORM
-- Migration: 000017_complete_auth_and_organization_onboarding.up.sql
-- Description: Complete schema for multi-tenant organization onboarding,
--              structured identifiers, documents, addresses, invites, and join requests.
-- ============================================================

-- 1. Ensure OWNER is in member_role_enum
DO $$ BEGIN
    ALTER TYPE member_role_enum ADD VALUE IF NOT EXISTS 'owner';
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 2. Update users table with verification timestamps and status
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(32);
ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_verified_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS status VARCHAR(32) NOT NULL DEFAULT 'active';

-- Backfill email_verified_at from is_email_verified
UPDATE users SET email_verified_at = NOW() WHERE is_email_verified = TRUE AND email_verified_at IS NULL;

-- 3. Create auth_identities table for multi-provider linking (Email, Google, etc.)
CREATE TABLE IF NOT EXISTS auth_identities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(32) NOT NULL, -- 'EMAIL', 'GOOGLE', 'APPLE'
    provider_subject VARCHAR(255) NOT NULL, -- Google sub or user email
    provider_email VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMPTZ,
    CONSTRAINT uq_auth_identity_provider_subject UNIQUE (provider, provider_subject),
    CONSTRAINT uq_auth_identity_user_provider UNIQUE (user_id, provider)
);

CREATE INDEX IF NOT EXISTS idx_auth_identities_user ON auth_identities(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_identities_lookup ON auth_identities(provider, provider_subject);

-- 4. Update organizations table with legal and enterprise fields
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS legal_name VARCHAR(255);
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS official_email VARCHAR(255);
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS official_phone VARCHAR(32);
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS alternate_phone VARCHAR(32);
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS year_established INT;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS number_of_employees VARCHAR(64);
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS business_type VARCHAR(64);

-- Enforce 12-character org_code column width if previously longer
ALTER TABLE organizations ALTER COLUMN org_code TYPE VARCHAR(32);

-- 5. Create organization_identifiers table (GSTIN, PAN, UDYAM, SHOP_ACT)
CREATE TABLE IF NOT EXISTS organization_identifiers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    type VARCHAR(32) NOT NULL, -- 'GSTIN', 'PAN', 'UDYAM', 'SHOP_ACT'
    value TEXT NOT NULL,
    normalized_value TEXT NOT NULL,
    verification_status VARCHAR(32) NOT NULL DEFAULT 'UNVERIFIED', -- 'UNVERIFIED', 'VERIFIED', 'FAILED'
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_org_identifier_type_value UNIQUE (type, normalized_value)
);

CREATE INDEX IF NOT EXISTS idx_org_identifiers_org ON organization_identifiers(organization_id);
CREATE INDEX IF NOT EXISTS idx_org_identifiers_normalized ON organization_identifiers(type, normalized_value);

-- 6. Create organization_documents table
CREATE TABLE IF NOT EXISTS organization_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    document_type VARCHAR(64) NOT NULL, -- 'GST Certificate', 'PAN', 'Udyam Certificate', etc.
    file_id VARCHAR(255) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    mime_type VARCHAR(128) NOT NULL,
    file_size BIGINT NOT NULL,
    document_number VARCHAR(128),
    verification_status VARCHAR(32) NOT NULL DEFAULT 'UPLOADED', -- 'UPLOADED', 'VERIFIED', 'REJECTED'
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    verified_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_org_documents_org ON organization_documents(organization_id);

-- 7. Create organization_addresses table
CREATE TABLE IF NOT EXISTS organization_addresses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    type VARCHAR(32) NOT NULL DEFAULT 'PRIMARY', -- 'PRIMARY', 'REGISTERED', 'BRANCH'
    address_line_1 TEXT NOT NULL,
    address_line_2 TEXT,
    locality TEXT,
    city VARCHAR(128) NOT NULL,
    district VARCHAR(128),
    state VARCHAR(128) NOT NULL,
    country VARCHAR(64) NOT NULL DEFAULT 'India',
    pincode VARCHAR(20) NOT NULL,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    is_primary BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_org_addresses_org ON organization_addresses(organization_id);

-- 8. Create organization_invites table
CREATE TABLE IF NOT EXISTS organization_invites (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    raw_token_preview VARCHAR(12),
    expires_at TIMESTAMPTZ NOT NULL,
    max_uses INT NOT NULL DEFAULT 0, -- 0 = unlimited
    use_count INT NOT NULL DEFAULT 0,
    is_revoked BOOLEAN NOT NULL DEFAULT FALSE,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_org_invites_org ON organization_invites(organization_id);
CREATE INDEX IF NOT EXISTS idx_org_invites_token_hash ON organization_invites(token_hash);

-- 9. Create organization_join_requests table
CREATE TABLE IF NOT EXISTS organization_join_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    invite_id UUID REFERENCES organization_invites(id) ON DELETE SET NULL,
    applicant_name VARCHAR(255),
    applicant_email VARCHAR(255),
    applicant_phone VARCHAR(32),
    requested_role VARCHAR(32) NOT NULL DEFAULT 'MEMBER',
    assigned_role VARCHAR(32),
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING', -- 'PENDING', 'APPROVED', 'REJECTED'
    reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_org_join_request UNIQUE (organization_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_join_requests_org ON organization_join_requests(organization_id);
CREATE INDEX IF NOT EXISTS idx_join_requests_user ON organization_join_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_join_requests_status ON organization_join_requests(organization_id, status);
