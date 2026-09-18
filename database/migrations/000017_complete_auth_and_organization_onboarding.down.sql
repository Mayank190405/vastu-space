DROP TABLE IF EXISTS organization_join_requests CASCADE;
DROP TABLE IF EXISTS organization_invites CASCADE;
DROP TABLE IF EXISTS organization_addresses CASCADE;
DROP TABLE IF EXISTS organization_documents CASCADE;
DROP TABLE IF EXISTS organization_identifiers CASCADE;
DROP TABLE IF EXISTS auth_identities CASCADE;

ALTER TABLE organizations DROP COLUMN IF EXISTS legal_name;
ALTER TABLE organizations DROP COLUMN IF EXISTS official_email;
ALTER TABLE organizations DROP COLUMN IF EXISTS official_phone;
ALTER TABLE organizations DROP COLUMN IF EXISTS alternate_phone;
ALTER TABLE organizations DROP COLUMN IF EXISTS year_established;
ALTER TABLE organizations DROP COLUMN IF EXISTS number_of_employees;
ALTER TABLE organizations DROP COLUMN IF EXISTS business_type;

ALTER TABLE users DROP COLUMN IF EXISTS email_verified_at;
ALTER TABLE users DROP COLUMN IF EXISTS phone;
ALTER TABLE users DROP COLUMN IF EXISTS phone_verified_at;
ALTER TABLE users DROP COLUMN IF EXISTS status;
