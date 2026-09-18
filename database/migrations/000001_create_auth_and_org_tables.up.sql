-- ============================================================
-- VĀSTU INDOOR SPATIAL COMPUTING PLATFORM
-- Migration: 000001_create_auth_and_org_tables.up.sql
-- Description: Multi-tenant Organizations, Users, Membership, OTPs, Tokens & Auditing
-- ============================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "citext";
CREATE EXTENSION IF NOT EXISTS "postgis";

-- Enum Types
DO $$ BEGIN
    CREATE TYPE org_status_enum AS ENUM ('pending_review', 'active', 'suspended', 'rejected');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE auth_provider_enum AS ENUM ('local', 'google');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE global_role_enum AS ENUM ('platform_admin', 'user');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE member_role_enum AS ENUM ('org_admin', 'project_manager', 'capture_operator', 'viewer', 'member');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE member_status_enum AS ENUM ('pending_approval', 'active', 'rejected', 'suspended');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE otp_purpose_enum AS ENUM ('org_signup', 'user_signup', 'password_reset');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 1. Organizations Table
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_code VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    country VARCHAR(64) NOT NULL,
    tax_id_type VARCHAR(32) NOT NULL,
    tax_id_number VARCHAR(64) NOT NULL,
    document_url TEXT NOT NULL,
    document_original_name VARCHAR(255),
    status org_status_enum NOT NULL DEFAULT 'pending_review',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_orgs_code ON organizations(org_code);
CREATE INDEX IF NOT EXISTS idx_orgs_status ON organizations(status);

-- 2. Users Table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email CITEXT NOT NULL UNIQUE,
    password_hash TEXT,
    full_name VARCHAR(255) NOT NULL,
    auth_provider auth_provider_enum NOT NULL DEFAULT 'local',
    google_id VARCHAR(255) UNIQUE,
    avatar_url TEXT,
    is_email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    global_role global_role_enum NOT NULL DEFAULT 'user',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id) WHERE google_id IS NOT NULL;

-- 3. Organization Members (Pivot Table with Role & Approval Gate)
CREATE TABLE IF NOT EXISTS organization_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role member_role_enum NOT NULL DEFAULT 'member',
    status member_status_enum NOT NULL DEFAULT 'pending_approval',
    approved_by UUID REFERENCES users(id) ON DELETE SET NULL,
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_org_user UNIQUE (org_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_org_members_org ON organization_members(org_id);
CREATE INDEX IF NOT EXISTS idx_org_members_user ON organization_members(user_id);
CREATE INDEX IF NOT EXISTS idx_org_members_status ON organization_members(org_id, status);

-- 4. Email OTPs Table
CREATE TABLE IF NOT EXISTS email_otps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email CITEXT NOT NULL,
    otp_code VARCHAR(6) NOT NULL,
    purpose otp_purpose_enum NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    expires_at TIMESTAMPTZ NOT NULL,
    is_used BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_email_otps_lookup ON email_otps(email, otp_code, purpose, is_used);

-- 5. Refresh Tokens Table
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_hash ON refresh_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id);

-- 6. Audit Logs Table
CREATE TABLE IF NOT EXISTS user_audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    org_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    action VARCHAR(128) NOT NULL,
    ip_address INET,
    user_agent TEXT,
    payload JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON user_audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_org ON user_audit_logs(org_id);
