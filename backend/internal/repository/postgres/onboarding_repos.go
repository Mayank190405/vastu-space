package postgres

import (
	"context"
	"errors"

	"vastu/backend/internal/domain"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// ============================================================
// 1. Identifier Repository
// ============================================================

type IdentifierRepo struct {
	pool *pgxpool.Pool
}

func NewIdentifierRepo(pool *pgxpool.Pool) *IdentifierRepo {
	return &IdentifierRepo{pool: pool}
}

func (r *IdentifierRepo) Create(ctx context.Context, ident *domain.OrganizationIdentifier) error {
	query := `
		INSERT INTO organization_identifiers (id, organization_id, type, value, normalized_value, verification_status, verified_at, created_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
	`
	if ident.ID == uuid.Nil {
		ident.ID = uuid.New()
	}
	_, err := r.pool.Exec(ctx, query, ident.ID, ident.OrganizationID, ident.Type, ident.Value, ident.NormalizedValue, ident.VerificationStatus, ident.VerifiedAt)
	return err
}

func (r *IdentifierRepo) GetByNormalized(ctx context.Context, identType, normalized string) (*domain.OrganizationIdentifier, error) {
	query := `
		SELECT id, organization_id, type, value, normalized_value, verification_status, verified_at, created_at
		FROM organization_identifiers
		WHERE type = $1 AND normalized_value = $2
	`
	var i domain.OrganizationIdentifier
	err := r.pool.QueryRow(ctx, query, identType, normalized).Scan(
		&i.ID, &i.OrganizationID, &i.Type, &i.Value, &i.NormalizedValue, &i.VerificationStatus, &i.VerifiedAt, &i.CreatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil
		}
		return nil, err
	}
	return &i, nil
}

func (r *IdentifierRepo) ListByOrg(ctx context.Context, orgID uuid.UUID) ([]*domain.OrganizationIdentifier, error) {
	query := `
		SELECT id, organization_id, type, value, normalized_value, verification_status, verified_at, created_at
		FROM organization_identifiers
		WHERE organization_id = $1
		ORDER BY created_at ASC
	`
	rows, err := r.pool.Query(ctx, query, orgID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var results []*domain.OrganizationIdentifier
	for rows.Next() {
		var i domain.OrganizationIdentifier
		if err := rows.Scan(&i.ID, &i.OrganizationID, &i.Type, &i.Value, &i.NormalizedValue, &i.VerificationStatus, &i.VerifiedAt, &i.CreatedAt); err != nil {
			return nil, err
		}
		results = append(results, &i)
	}
	return results, nil
}

func (r *IdentifierRepo) Verify(ctx context.Context, id uuid.UUID, status string) error {
	query := `UPDATE organization_identifiers SET verification_status = $2, verified_at = NOW() WHERE id = $1`
	_, err := r.pool.Exec(ctx, query, id, status)
	return err
}

// ============================================================
// 2. Document Repository
// ============================================================

type DocumentRepo struct {
	pool *pgxpool.Pool
}

func NewDocumentRepo(pool *pgxpool.Pool) *DocumentRepo {
	return &DocumentRepo{pool: pool}
}

func (r *DocumentRepo) Create(ctx context.Context, doc *domain.OrganizationDocument) error {
	query := `
		INSERT INTO organization_documents (id, organization_id, document_type, file_id, file_name, mime_type, file_size, document_number, verification_status, uploaded_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
	`
	if doc.ID == uuid.Nil {
		doc.ID = uuid.New()
	}
	_, err := r.pool.Exec(ctx, query, doc.ID, doc.OrganizationID, doc.DocumentType, doc.FileID, doc.FileName, doc.MimeType, doc.FileSize, doc.DocumentNumber, doc.VerificationStatus)
	return err
}

func (r *DocumentRepo) ListByOrg(ctx context.Context, orgID uuid.UUID) ([]*domain.OrganizationDocument, error) {
	query := `
		SELECT id, organization_id, document_type, file_id, file_name, mime_type, file_size, document_number, verification_status, uploaded_at, verified_at
		FROM organization_documents
		WHERE organization_id = $1
		ORDER BY uploaded_at DESC
	`
	rows, err := r.pool.Query(ctx, query, orgID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var results []*domain.OrganizationDocument
	for rows.Next() {
		var d domain.OrganizationDocument
		if err := rows.Scan(&d.ID, &d.OrganizationID, &d.DocumentType, &d.FileID, &d.FileName, &d.MimeType, &d.FileSize, &d.DocumentNumber, &d.VerificationStatus, &d.UploadedAt, &d.VerifiedAt); err != nil {
			return nil, err
		}
		results = append(results, &d)
	}
	return results, nil
}

func (r *DocumentRepo) GetByID(ctx context.Context, id uuid.UUID) (*domain.OrganizationDocument, error) {
	query := `
		SELECT id, organization_id, document_type, file_id, file_name, mime_type, file_size, document_number, verification_status, uploaded_at, verified_at
		FROM organization_documents
		WHERE id = $1
	`
	var d domain.OrganizationDocument
	err := r.pool.QueryRow(ctx, query, id).Scan(&d.ID, &d.OrganizationID, &d.DocumentType, &d.FileID, &d.FileName, &d.MimeType, &d.FileSize, &d.DocumentNumber, &d.VerificationStatus, &d.UploadedAt, &d.VerifiedAt)
	if err != nil {
		return nil, err
	}
	return &d, nil
}

func (r *DocumentRepo) Delete(ctx context.Context, id uuid.UUID) error {
	query := `DELETE FROM organization_documents WHERE id = $1`
	_, err := r.pool.Exec(ctx, query, id)
	return err
}

// ============================================================
// 3. Address Repository
// ============================================================

type AddressRepo struct {
	pool *pgxpool.Pool
}

func NewAddressRepo(pool *pgxpool.Pool) *AddressRepo {
	return &AddressRepo{pool: pool}
}

func (r *AddressRepo) Create(ctx context.Context, addr *domain.OrganizationAddress) error {
	query := `
		INSERT INTO organization_addresses (id, organization_id, type, address_line_1, address_line_2, locality, city, district, state, country, pincode, latitude, longitude, is_primary, created_at, updated_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, NOW(), NOW())
	`
	if addr.ID == uuid.Nil {
		addr.ID = uuid.New()
	}
	_, err := r.pool.Exec(ctx, query, addr.ID, addr.OrganizationID, addr.Type, addr.AddressLine1, addr.AddressLine2, addr.Locality, addr.City, addr.District, addr.State, addr.Country, addr.Pincode, addr.Latitude, addr.Longitude, addr.IsPrimary)
	return err
}

func (r *AddressRepo) GetPrimaryByOrg(ctx context.Context, orgID uuid.UUID) (*domain.OrganizationAddress, error) {
	query := `
		SELECT id, organization_id, type, address_line_1, address_line_2, locality, city, district, state, country, pincode, latitude, longitude, is_primary, created_at, updated_at
		FROM organization_addresses
		WHERE organization_id = $1 AND is_primary = TRUE
		LIMIT 1
	`
	var a domain.OrganizationAddress
	err := r.pool.QueryRow(ctx, query, orgID).Scan(&a.ID, &a.OrganizationID, &a.Type, &a.AddressLine1, &a.AddressLine2, &a.Locality, &a.City, &a.District, &a.State, &a.Country, &a.Pincode, &a.Latitude, &a.Longitude, &a.IsPrimary, &a.CreatedAt, &a.UpdatedAt)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil
		}
		return nil, err
	}
	return &a, nil
}

func (r *AddressRepo) UpdatePrimary(ctx context.Context, addr *domain.OrganizationAddress) error {
	query := `
		UPDATE organization_addresses SET
			address_line_1 = $2, address_line_2 = $3, locality = $4, city = $5,
			district = $6, state = $7, country = $8, pincode = $9, updated_at = NOW()
		WHERE organization_id = $1 AND is_primary = TRUE
	`
	_, err := r.pool.Exec(ctx, query, addr.OrganizationID, addr.AddressLine1, addr.AddressLine2, addr.Locality, addr.City, addr.District, addr.State, addr.Country, addr.Pincode)
	return err
}

// ============================================================
// 4. Invite Repository
// ============================================================

type InviteRepo struct {
	pool *pgxpool.Pool
}

func NewInviteRepo(pool *pgxpool.Pool) *InviteRepo {
	return &InviteRepo{pool: pool}
}

func (r *InviteRepo) Create(ctx context.Context, invite *domain.OrganizationInvite) error {
	query := `
		INSERT INTO organization_invites (id, organization_id, token_hash, raw_token_preview, expires_at, max_uses, use_count, is_revoked, created_by, created_at)
		VALUES ($1, $2, $3, $4, $5, $6, 0, FALSE, $7, NOW())
	`
	if invite.ID == uuid.Nil {
		invite.ID = uuid.New()
	}
	_, err := r.pool.Exec(ctx, query, invite.ID, invite.OrganizationID, invite.TokenHash, invite.RawTokenPreview, invite.ExpiresAt, invite.MaxUses, invite.CreatedBy)
	return err
}

func (r *InviteRepo) GetByTokenHash(ctx context.Context, tokenHash string) (*domain.OrganizationInvite, error) {
	query := `
		SELECT id, organization_id, token_hash, raw_token_preview, expires_at, max_uses, use_count, is_revoked, created_by, created_at
		FROM organization_invites
		WHERE token_hash = $1
	`
	var inv domain.OrganizationInvite
	err := r.pool.QueryRow(ctx, query, tokenHash).Scan(&inv.ID, &inv.OrganizationID, &inv.TokenHash, &inv.RawTokenPreview, &inv.ExpiresAt, &inv.MaxUses, &inv.UseCount, &inv.IsRevoked, &inv.CreatedBy, &inv.CreatedAt)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil
		}
		return nil, err
	}
	return &inv, nil
}

func (r *InviteRepo) GetActiveByOrg(ctx context.Context, orgID uuid.UUID) (*domain.OrganizationInvite, error) {
	query := `
		SELECT id, organization_id, token_hash, raw_token_preview, expires_at, max_uses, use_count, is_revoked, created_by, created_at
		FROM organization_invites
		WHERE organization_id = $1 AND is_revoked = FALSE AND expires_at > NOW()
		ORDER BY created_at DESC
		LIMIT 1
	`
	var inv domain.OrganizationInvite
	err := r.pool.QueryRow(ctx, query, orgID).Scan(&inv.ID, &inv.OrganizationID, &inv.TokenHash, &inv.RawTokenPreview, &inv.ExpiresAt, &inv.MaxUses, &inv.UseCount, &inv.IsRevoked, &inv.CreatedBy, &inv.CreatedAt)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil
		}
		return nil, err
	}
	return &inv, nil
}

func (r *InviteRepo) IncrementUse(ctx context.Context, id uuid.UUID) error {
	query := `UPDATE organization_invites SET use_count = use_count + 1 WHERE id = $1`
	_, err := r.pool.Exec(ctx, query, id)
	return err
}

func (r *InviteRepo) Revoke(ctx context.Context, id uuid.UUID) error {
	query := `UPDATE organization_invites SET is_revoked = TRUE WHERE id = $1`
	_, err := r.pool.Exec(ctx, query, id)
	return err
}

// ============================================================
// 5. Join Request Repository
// ============================================================

type JoinRequestRepo struct {
	pool *pgxpool.Pool
}

func NewJoinRequestRepo(pool *pgxpool.Pool) *JoinRequestRepo {
	return &JoinRequestRepo{pool: pool}
}

func (r *JoinRequestRepo) Create(ctx context.Context, req *domain.OrganizationJoinRequest) error {
	query := `
		INSERT INTO organization_join_requests (id, organization_id, user_id, invite_id, applicant_name, applicant_email, applicant_phone, requested_role, assigned_role, status, created_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW())
		ON CONFLICT (organization_id, user_id) 
		DO UPDATE SET status = 'PENDING', applicant_name = EXCLUDED.applicant_name, applicant_phone = EXCLUDED.applicant_phone, created_at = NOW()
	`
	if req.ID == uuid.Nil {
		req.ID = uuid.New()
	}
	_, err := r.pool.Exec(ctx, query, req.ID, req.OrganizationID, req.UserID, req.InviteID, req.ApplicantName, req.ApplicantEmail, req.ApplicantPhone, req.RequestedRole, req.AssignedRole, req.Status)
	return err
}

func (r *JoinRequestRepo) GetByID(ctx context.Context, id uuid.UUID) (*domain.OrganizationJoinRequest, error) {
	query := `
		SELECT id, organization_id, user_id, invite_id, applicant_name, applicant_email, applicant_phone, requested_role, assigned_role, status, reviewed_by, reviewed_at, created_at
		FROM organization_join_requests
		WHERE id = $1
	`
	var req domain.OrganizationJoinRequest
	err := r.pool.QueryRow(ctx, query, id).Scan(&req.ID, &req.OrganizationID, &req.UserID, &req.InviteID, &req.ApplicantName, &req.ApplicantEmail, &req.ApplicantPhone, &req.RequestedRole, &req.AssignedRole, &req.Status, &req.ReviewedBy, &req.ReviewedAt, &req.CreatedAt)
	if err != nil {
		return nil, err
	}
	return &req, nil
}

func (r *JoinRequestRepo) GetByOrgAndUser(ctx context.Context, orgID, userID uuid.UUID) (*domain.OrganizationJoinRequest, error) {
	query := `
		SELECT id, organization_id, user_id, invite_id, applicant_name, applicant_email, applicant_phone, requested_role, assigned_role, status, reviewed_by, reviewed_at, created_at
		FROM organization_join_requests
		WHERE organization_id = $1 AND user_id = $2
	`
	var req domain.OrganizationJoinRequest
	err := r.pool.QueryRow(ctx, query, orgID, userID).Scan(&req.ID, &req.OrganizationID, &req.UserID, &req.InviteID, &req.ApplicantName, &req.ApplicantEmail, &req.ApplicantPhone, &req.RequestedRole, &req.AssignedRole, &req.Status, &req.ReviewedBy, &req.ReviewedAt, &req.CreatedAt)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil
		}
		return nil, err
	}
	return &req, nil
}

func (r *JoinRequestRepo) ListPendingByOrg(ctx context.Context, orgID uuid.UUID) ([]*domain.OrganizationJoinRequest, error) {
	query := `
		SELECT r.id, r.organization_id, r.user_id, r.invite_id, r.applicant_name, r.applicant_email, r.applicant_phone, 
		       r.requested_role, r.assigned_role, r.status, r.reviewed_by, r.reviewed_at, r.created_at, o.name, o.org_code
		FROM organization_join_requests r
		INNER JOIN organizations o ON r.organization_id = o.id
		WHERE r.organization_id = $1 AND r.status = 'PENDING'
		ORDER BY r.created_at DESC
	`
	rows, err := r.pool.Query(ctx, query, orgID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var results []*domain.OrganizationJoinRequest
	for rows.Next() {
		var req domain.OrganizationJoinRequest
		if err := rows.Scan(&req.ID, &req.OrganizationID, &req.UserID, &req.InviteID, &req.ApplicantName, &req.ApplicantEmail, &req.ApplicantPhone, &req.RequestedRole, &req.AssignedRole, &req.Status, &req.ReviewedBy, &req.ReviewedAt, &req.CreatedAt, &req.OrgName, &req.OrgCode); err != nil {
			return nil, err
		}
		results = append(results, &req)
	}
	return results, nil
}

func (r *JoinRequestRepo) UpdateStatus(ctx context.Context, id uuid.UUID, status string, assignedRole *string, reviewerID uuid.UUID) error {
	query := `
		UPDATE organization_join_requests SET
			status = $2, assigned_role = $3, reviewed_by = $4, reviewed_at = NOW()
		WHERE id = $1
	`
	_, err := r.pool.Exec(ctx, query, id, status, assignedRole, reviewerID)
	return err
}
