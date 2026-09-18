-- ============================================================
-- VĀSTU INDOOR SPATIAL COMPUTING PLATFORM
-- Rollback Migration: 000001_create_auth_and_org_tables.down.sql
-- ============================================================

DROP TABLE IF EXISTS user_audit_logs CASCADE;
DROP TABLE IF EXISTS refresh_tokens CASCADE;
DROP TABLE IF EXISTS email_otps CASCADE;
DROP TABLE IF EXISTS organization_members CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS organizations CASCADE;

DROP TYPE IF EXISTS otp_purpose_enum CASCADE;
DROP TYPE IF EXISTS member_status_enum CASCADE;
DROP TYPE IF EXISTS member_role_enum CASCADE;
DROP TYPE IF EXISTS global_role_enum CASCADE;
DROP TYPE IF EXISTS auth_provider_enum CASCADE;
DROP TYPE IF EXISTS org_status_enum CASCADE;
