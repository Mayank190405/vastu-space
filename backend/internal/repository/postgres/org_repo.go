package postgres

import (
	"context"
	"errors"
	"time"

	"vastu/backend/internal/domain"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

type OrgRepo struct {
	pool *pgxpool.Pool
}

func NewOrgRepo(pool *pgxpool.Pool) *OrgRepo {
	return &OrgRepo{pool: pool}
}

func (r *OrgRepo) Create(ctx context.Context, org *domain.Organization) error {
	query := `
		INSERT INTO organizations (
			id, org_code, name, legal_name, org_type, industry, country, state, city, website, 
			org_size, address, phone_number, official_email, official_phone, alternate_phone, 
			year_established, number_of_employees, business_type, gst_number, pan_number, 
			registration_number, logo_url, domain, description, tax_id_type, tax_id_number, 
			document_url, document_original_name, status, created_at, updated_at
		) VALUES (
			$1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
			$11, $12, $13, $14, $15, $16, $17, $18, $19, $20,
			$21, $22, $23, $24, $25, $26, $27, $28, $29, $30,
			$31, $32
		)
	`
	now := time.Now().UTC()
	org.CreatedAt = now
	org.UpdatedAt = now

	_, err := r.pool.Exec(ctx, query,
		org.ID, org.OrgCode, org.Name, org.LegalName, org.OrgType, org.Industry, org.Country, org.State, org.City, org.Website,
		org.OrgSize, org.Address, org.PhoneNumber, org.OfficialEmail, org.OfficialPhone, org.AlternatePhone,
		org.YearEstablished, org.NumberOfEmployees, org.BusinessType, org.GSTNumber, org.PANNumber,
		org.RegistrationNumber, org.LogoURL, org.Domain, org.Description, org.TaxIDType, org.TaxIDNumber,
		org.DocumentURL, org.DocumentOriginalName, org.Status, org.CreatedAt, org.UpdatedAt,
	)
	return err
}

func (r *OrgRepo) GetByID(ctx context.Context, id uuid.UUID) (*domain.Organization, error) {
	query := `
		SELECT id, org_code, name, legal_name, org_type, industry, country, state, city, website, 
		       org_size, address, phone_number, official_email, official_phone, alternate_phone, 
		       year_established, number_of_employees, business_type, gst_number, pan_number, 
		       registration_number, logo_url, domain, description, tax_id_type, tax_id_number, 
		       document_url, document_original_name, status, created_at, updated_at
		FROM organizations
		WHERE id = $1
	`
	var o domain.Organization
	err := r.pool.QueryRow(ctx, query, id).Scan(
		&o.ID, &o.OrgCode, &o.Name, &o.LegalName, &o.OrgType, &o.Industry, &o.Country, &o.State, &o.City, &o.Website,
		&o.OrgSize, &o.Address, &o.PhoneNumber, &o.OfficialEmail, &o.OfficialPhone, &o.AlternatePhone,
		&o.YearEstablished, &o.NumberOfEmployees, &o.BusinessType, &o.GSTNumber, &o.PANNumber,
		&o.RegistrationNumber, &o.LogoURL, &o.Domain, &o.Description, &o.TaxIDType, &o.TaxIDNumber,
		&o.DocumentURL, &o.DocumentOriginalName, &o.Status, &o.CreatedAt, &o.UpdatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, domain.ErrOrgNotFound
		}
		return nil, err
	}
	return &o, nil
}

func (r *OrgRepo) GetByCode(ctx context.Context, orgCode string) (*domain.Organization, error) {
	query := `
		SELECT id, org_code, name, legal_name, org_type, industry, country, state, city, website, 
		       org_size, address, phone_number, official_email, official_phone, alternate_phone, 
		       year_established, number_of_employees, business_type, gst_number, pan_number, 
		       registration_number, logo_url, domain, description, tax_id_type, tax_id_number, 
		       document_url, document_original_name, status, created_at, updated_at
		FROM organizations
		WHERE org_code = $1
	`
	var o domain.Organization
	err := r.pool.QueryRow(ctx, query, orgCode).Scan(
		&o.ID, &o.OrgCode, &o.Name, &o.LegalName, &o.OrgType, &o.Industry, &o.Country, &o.State, &o.City, &o.Website,
		&o.OrgSize, &o.Address, &o.PhoneNumber, &o.OfficialEmail, &o.OfficialPhone, &o.AlternatePhone,
		&o.YearEstablished, &o.NumberOfEmployees, &o.BusinessType, &o.GSTNumber, &o.PANNumber,
		&o.RegistrationNumber, &o.LogoURL, &o.Domain, &o.Description, &o.TaxIDType, &o.TaxIDNumber,
		&o.DocumentURL, &o.DocumentOriginalName, &o.Status, &o.CreatedAt, &o.UpdatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, domain.ErrOrgNotFound
		}
		return nil, err
	}
	return &o, nil
}

func (r *OrgRepo) UpdateStatus(ctx context.Context, id uuid.UUID, status domain.OrgStatus) error {
	query := `UPDATE organizations SET status = $2, updated_at = NOW() WHERE id = $1`
	_, err := r.pool.Exec(ctx, query, id, status)
	return err
}

func (r *OrgRepo) UpdateOrgCode(ctx context.Context, id uuid.UUID, newCode string) error {
	query := `UPDATE organizations SET org_code = $2, updated_at = NOW() WHERE id = $1`
	_, err := r.pool.Exec(ctx, query, id, newCode)
	return err
}

func (r *OrgRepo) Update(ctx context.Context, org *domain.Organization) error {
	query := `
		UPDATE organizations SET 
			name = $2, legal_name = $3, org_type = $4, industry = $5, website = $6, 
			official_email = $7, official_phone = $8, alternate_phone = $9, 
			year_established = $10, number_of_employees = $11, business_type = $12, 
			description = $13, logo_url = $14, updated_at = NOW()
		WHERE id = $1
	`
	_, err := r.pool.Exec(ctx, query,
		org.ID, org.Name, org.LegalName, org.OrgType, org.Industry, org.Website,
		org.OfficialEmail, org.OfficialPhone, org.AlternatePhone,
		org.YearEstablished, org.NumberOfEmployees, org.BusinessType,
		org.Description, org.LogoURL,
	)
	return err
}

// CreateOrganizationAtomic executes the complete onboarding sequence atomically
func (r *OrgRepo) CreateOrganizationAtomic(
	ctx context.Context,
	user *domain.User,
	authIdentity *domain.AuthIdentity,
	org *domain.Organization,
	identifier *domain.OrganizationIdentifier,
	document *domain.OrganizationDocument,
	address *domain.OrganizationAddress,
	member *domain.OrganizationMember,
	invite *domain.OrganizationInvite,
) error {
	tx, err := r.pool.Begin(ctx)
	if err != nil {
		return err
	}
	defer tx.Rollback(ctx)

	now := time.Now().UTC()

	// 1. Upsert User
	upsertUserQuery := `
		INSERT INTO users (id, email, password_hash, full_name, auth_provider, is_email_verified, email_verified_at, phone, phone_verified_at, status, global_role, created_at, updated_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $12)
		ON CONFLICT (email) DO UPDATE SET 
			full_name = EXCLUDED.full_name,
			password_hash = COALESCE(EXCLUDED.password_hash, users.password_hash),
			is_email_verified = TRUE,
			email_verified_at = COALESCE(users.email_verified_at, NOW()),
			phone = COALESCE(EXCLUDED.phone, users.phone),
			updated_at = NOW()
		RETURNING id
	`
	var actualUserID uuid.UUID
	err = tx.QueryRow(ctx, upsertUserQuery,
		user.ID, user.Email, user.PasswordHash, user.FullName, user.AuthProvider,
		user.IsEmailVerified, user.EmailVerifiedAt, user.Phone, user.PhoneVerifiedAt,
		"active", domain.RoleUser, now,
	).Scan(&actualUserID)
	if err != nil {
		return err
	}
	user.ID = actualUserID

	// 2. Link Auth Identity if present
	if authIdentity != nil {
		upsertIdentityQuery := `
			INSERT INTO auth_identities (id, user_id, provider, provider_subject, provider_email, created_at, last_login_at)
			VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
			ON CONFLICT (provider, provider_subject) DO UPDATE SET user_id = EXCLUDED.user_id, last_login_at = NOW()
		`
		if authIdentity.ID == uuid.Nil {
			authIdentity.ID = uuid.New()
		}
		_, err = tx.Exec(ctx, upsertIdentityQuery, authIdentity.ID, actualUserID, authIdentity.Provider, authIdentity.ProviderSubject, authIdentity.ProviderEmail)
		if err != nil {
			return err
		}
	}

	// 3. Create Organization
	insertOrgQuery := `
		INSERT INTO organizations (
			id, org_code, name, legal_name, org_type, industry, country, state, city, website, 
			org_size, address, phone_number, official_email, official_phone, alternate_phone, 
			year_established, number_of_employees, business_type, gst_number, pan_number, 
			registration_number, logo_url, domain, description, tax_id_type, tax_id_number, 
			document_url, document_original_name, status, created_at, updated_at
		) VALUES (
			$1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
			$11, $12, $13, $14, $15, $16, $17, $18, $19, $20,
			$21, $22, $23, $24, $25, $26, $27, $28, $29, $30,
			$31, $32
		)
	`
	org.CreatedAt = now
	org.UpdatedAt = now
	_, err = tx.Exec(ctx, insertOrgQuery,
		org.ID, org.OrgCode, org.Name, org.LegalName, org.OrgType, org.Industry, org.Country, org.State, org.City, org.Website,
		org.OrgSize, org.Address, org.PhoneNumber, org.OfficialEmail, org.OfficialPhone, org.AlternatePhone,
		org.YearEstablished, org.NumberOfEmployees, org.BusinessType, org.GSTNumber, org.PANNumber,
		org.RegistrationNumber, org.LogoURL, org.Domain, org.Description, org.TaxIDType, org.TaxIDNumber,
		org.DocumentURL, org.DocumentOriginalName, org.Status, org.CreatedAt, org.UpdatedAt,
	)
	if err != nil {
		return err
	}

	// 4. Create Organization Identifier
	if identifier != nil {
		insertIdentQuery := `
			INSERT INTO organization_identifiers (id, organization_id, type, value, normalized_value, verification_status, verified_at, created_at)
			VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
		`
		if identifier.ID == uuid.Nil {
			identifier.ID = uuid.New()
		}
		_, err = tx.Exec(ctx, insertIdentQuery,
			identifier.ID, org.ID, identifier.Type, identifier.Value, identifier.NormalizedValue,
			identifier.VerificationStatus, identifier.VerifiedAt,
		)
		if err != nil {
			return err
		}
	}

	// 5. Create Supporting Document if provided
	if document != nil {
		insertDocQuery := `
			INSERT INTO organization_documents (id, organization_id, document_type, file_id, file_name, mime_type, file_size, document_number, verification_status, uploaded_at)
			VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
		`
		if document.ID == uuid.Nil {
			document.ID = uuid.New()
		}
		_, err = tx.Exec(ctx, insertDocQuery,
			document.ID, org.ID, document.DocumentType, document.FileID, document.FileName,
			document.MimeType, document.FileSize, document.DocumentNumber, document.VerificationStatus,
		)
		if err != nil {
			return err
		}
	}

	// 6. Create Organization Address
	if address != nil {
		insertAddrQuery := `
			INSERT INTO organization_addresses (id, organization_id, type, address_line_1, address_line_2, locality, city, district, state, country, pincode, latitude, longitude, is_primary, created_at, updated_at)
			VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, NOW(), NOW())
		`
		if address.ID == uuid.Nil {
			address.ID = uuid.New()
		}
		_, err = tx.Exec(ctx, insertAddrQuery,
			address.ID, org.ID, address.Type, address.AddressLine1, address.AddressLine2,
			address.Locality, address.City, address.District, address.State, address.Country,
			address.Pincode, address.Latitude, address.Longitude, address.IsPrimary,
		)
		if err != nil {
			return err
		}
	}

	// 7. Create Membership with role OWNER
	insertMemberQuery := `
		INSERT INTO organization_members (id, org_id, user_id, role, status, approved_by, approved_at, created_at, updated_at)
		VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW(), NOW())
		ON CONFLICT (org_id, user_id) DO UPDATE SET role = EXCLUDED.role, status = 'active'
	`
	if member.ID == uuid.Nil {
		member.ID = uuid.New()
	}
	_, err = tx.Exec(ctx, insertMemberQuery,
		member.ID, org.ID, actualUserID, domain.RoleOwner, domain.MemberStatusActive, actualUserID,
	)
	if err != nil {
		return err
	}

	// 8. Create Default Employee Invite
	if invite != nil {
		insertInviteQuery := `
			INSERT INTO organization_invites (id, organization_id, token_hash, raw_token_preview, expires_at, max_uses, use_count, is_revoked, created_by, created_at)
			VALUES ($1, $2, $3, $4, $5, $6, 0, FALSE, $7, NOW())
		`
		if invite.ID == uuid.Nil {
			invite.ID = uuid.New()
		}
		_, err = tx.Exec(ctx, insertInviteQuery,
			invite.ID, org.ID, invite.TokenHash, invite.RawTokenPreview, invite.ExpiresAt, invite.MaxUses, actualUserID,
		)
		if err != nil {
			return err
		}
	}

	return tx.Commit(ctx)
}
