-- ============================================================
-- Migration: 000013_add_login_to_otp_purpose.up.sql
-- Description: Add 'login' value to otp_purpose_enum
-- ============================================================

ALTER TYPE otp_purpose_enum ADD VALUE IF NOT EXISTS 'login';
