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

type MemberRepo struct {
	pool *pgxpool.Pool
}

func NewMemberRepo(pool *pgxpool.Pool) *MemberRepo {
	return &MemberRepo{pool: pool}
}

func (r *MemberRepo) Create(ctx context.Context, m *domain.OrganizationMember) error {
	query := `
		INSERT INTO organization_members (id, org_id, user_id, role, status, approved_by, approved_at, created_at, updated_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
	`
	now := time.Now().UTC()
	m.CreatedAt = now
	m.UpdatedAt = now

	_, err := r.pool.Exec(ctx, query,
		m.ID,
		m.OrgID,
		m.UserID,
		m.Role,
		m.Status,
		m.ApprovedBy,
		m.ApprovedAt,
		m.CreatedAt,
		m.UpdatedAt,
	)
	return err
}

func (r *MemberRepo) GetByID(ctx context.Context, id uuid.UUID) (*domain.OrganizationMember, error) {
	query := `
		SELECT m.id, m.org_id, m.user_id, m.role, m.status, m.approved_by, m.approved_at, m.created_at, m.updated_at,
		       u.full_name as user_name, u.email as user_email, o.name as org_name, o.org_code
		FROM organization_members m
		JOIN users u ON m.user_id = u.id
		JOIN organizations o ON m.org_id = o.id
		WHERE m.id = $1
	`
	var m domain.OrganizationMember
	err := r.pool.QueryRow(ctx, query, id).Scan(
		&m.ID,
		&m.OrgID,
		&m.UserID,
		&m.Role,
		&m.Status,
		&m.ApprovedBy,
		&m.ApprovedAt,
		&m.CreatedAt,
		&m.UpdatedAt,
		&m.UserName,
		&m.UserEmail,
		&m.OrgName,
		&m.OrgCode,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, domain.ErrMembershipNotFound
		}
		return nil, err
	}
	return &m, nil
}

func (r *MemberRepo) GetByOrgAndUser(ctx context.Context, orgID, userID uuid.UUID) (*domain.OrganizationMember, error) {
	query := `
		SELECT id, org_id, user_id, role, status, approved_by, approved_at, created_at, updated_at
		FROM organization_members
		WHERE org_id = $1 AND user_id = $2
	`
	var m domain.OrganizationMember
	err := r.pool.QueryRow(ctx, query, orgID, userID).Scan(
		&m.ID,
		&m.OrgID,
		&m.UserID,
		&m.Role,
		&m.Status,
		&m.ApprovedBy,
		&m.ApprovedAt,
		&m.CreatedAt,
		&m.UpdatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, domain.ErrMembershipNotFound
		}
		return nil, err
	}
	return &m, nil
}

func (r *MemberRepo) GetUserMemberships(ctx context.Context, userID uuid.UUID) ([]*domain.OrganizationMember, error) {
	query := `
		SELECT m.id, m.org_id, m.user_id, m.role, m.status, m.approved_by, m.approved_at, m.created_at, m.updated_at,
		       o.name as org_name, o.org_code
		FROM organization_members m
		JOIN organizations o ON m.org_id = o.id
		WHERE m.user_id = $1
		ORDER BY m.created_at DESC
	`
	rows, err := r.pool.Query(ctx, query, userID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var members []*domain.OrganizationMember
	for rows.Next() {
		var m domain.OrganizationMember
		err := rows.Scan(
			&m.ID,
			&m.OrgID,
			&m.UserID,
			&m.Role,
			&m.Status,
			&m.ApprovedBy,
			&m.ApprovedAt,
			&m.CreatedAt,
			&m.UpdatedAt,
			&m.OrgName,
			&m.OrgCode,
		)
		if err != nil {
			return nil, err
		}
		members = append(members, &m)
	}
	return members, nil
}

func (r *MemberRepo) GetPendingMembersByOrg(ctx context.Context, orgID uuid.UUID) ([]*domain.OrganizationMember, error) {
	query := `
		SELECT m.id, m.org_id, m.user_id, m.role, m.status, m.approved_by, m.approved_at, m.created_at, m.updated_at,
		       u.full_name as user_name, u.email as user_email, o.name as org_name, o.org_code
		FROM organization_members m
		JOIN users u ON m.user_id = u.id
		JOIN organizations o ON m.org_id = o.id
		WHERE m.org_id = $1 AND m.status = 'pending_approval'
		ORDER BY m.created_at ASC
	`
	rows, err := r.pool.Query(ctx, query, orgID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var members []*domain.OrganizationMember
	for rows.Next() {
		var m domain.OrganizationMember
		err := rows.Scan(
			&m.ID,
			&m.OrgID,
			&m.UserID,
			&m.Role,
			&m.Status,
			&m.ApprovedBy,
			&m.ApprovedAt,
			&m.CreatedAt,
			&m.UpdatedAt,
			&m.UserName,
			&m.UserEmail,
			&m.OrgName,
			&m.OrgCode,
		)
		if err != nil {
			return nil, err
		}
		members = append(members, &m)
	}
	return members, nil
}

func (r *MemberRepo) UpdateStatus(ctx context.Context, id uuid.UUID, status domain.MemberStatus, role domain.MemberRole, approvedBy uuid.UUID, approvedAt time.Time) error {
	query := `
		UPDATE organization_members
		SET status = $2, role = $3, approved_by = $4, approved_at = $5, updated_at = NOW()
		WHERE id = $1
	`
	_, err := r.pool.Exec(ctx, query, id, status, role, approvedBy, approvedAt)
	return err
}

func (r *MemberRepo) ListByOrg(ctx context.Context, orgID uuid.UUID) ([]*domain.OrganizationMember, error) {
	query := `
		SELECT m.id, m.org_id, m.user_id, m.role, m.status, m.approved_by, m.approved_at, m.created_at, m.updated_at,
		       u.full_name as user_name, u.email as user_email, o.name as org_name, o.org_code
		FROM organization_members m
		JOIN users u ON m.user_id = u.id
		JOIN organizations o ON m.org_id = o.id
		WHERE m.org_id = $1
		ORDER BY m.created_at ASC
	`
	rows, err := r.pool.Query(ctx, query, orgID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var members []*domain.OrganizationMember
	for rows.Next() {
		var m domain.OrganizationMember
		err := rows.Scan(
			&m.ID,
			&m.OrgID,
			&m.UserID,
			&m.Role,
			&m.Status,
			&m.ApprovedBy,
			&m.ApprovedAt,
			&m.CreatedAt,
			&m.UpdatedAt,
			&m.UserName,
			&m.UserEmail,
			&m.OrgName,
			&m.OrgCode,
		)
		if err != nil {
			return nil, err
		}
		members = append(members, &m)
	}
	return members, nil
}

