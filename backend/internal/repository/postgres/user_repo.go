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

type UserRepo struct {
	pool *pgxpool.Pool
}

func NewUserRepo(pool *pgxpool.Pool) *UserRepo {
	return &UserRepo{pool: pool}
}

func (r *UserRepo) Create(ctx context.Context, user *domain.User) error {
	query := `
		INSERT INTO users (id, email, password_hash, full_name, auth_provider, google_id, apple_id, avatar_url, is_email_verified, email_verified_at, phone, phone_verified_at, status, global_role, created_at, updated_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
	`
	now := time.Now().UTC()
	user.CreatedAt = now
	user.UpdatedAt = now
	if user.Status == "" {
		user.Status = "active"
	}

	_, err := r.pool.Exec(ctx, query,
		user.ID,
		user.Email,
		user.PasswordHash,
		user.FullName,
		user.AuthProvider,
		user.GoogleID,
		user.AppleID,
		user.AvatarURL,
		user.IsEmailVerified,
		user.EmailVerifiedAt,
		user.Phone,
		user.PhoneVerifiedAt,
		user.Status,
		user.GlobalRole,
		user.CreatedAt,
		user.UpdatedAt,
	)
	return err
}

func (r *UserRepo) GetByID(ctx context.Context, id uuid.UUID) (*domain.User, error) {
	query := `
		SELECT id, email, password_hash, full_name, auth_provider, google_id, apple_id, avatar_url, is_email_verified, email_verified_at, phone, phone_verified_at, status, global_role, created_at, updated_at, last_login_at
		FROM users
		WHERE id = $1
	`
	var u domain.User
	err := r.pool.QueryRow(ctx, query, id).Scan(
		&u.ID,
		&u.Email,
		&u.PasswordHash,
		&u.FullName,
		&u.AuthProvider,
		&u.GoogleID,
		&u.AppleID,
		&u.AvatarURL,
		&u.IsEmailVerified,
		&u.EmailVerifiedAt,
		&u.Phone,
		&u.PhoneVerifiedAt,
		&u.Status,
		&u.GlobalRole,
		&u.CreatedAt,
		&u.UpdatedAt,
		&u.LastLoginAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, domain.ErrUserNotFound
		}
		return nil, err
	}
	return &u, nil
}

func (r *UserRepo) GetByEmail(ctx context.Context, email string) (*domain.User, error) {
	query := `
		SELECT id, email, password_hash, full_name, auth_provider, google_id, apple_id, avatar_url, is_email_verified, email_verified_at, phone, phone_verified_at, status, global_role, created_at, updated_at, last_login_at
		FROM users
		WHERE LOWER(email) = LOWER($1)
	`
	var u domain.User
	err := r.pool.QueryRow(ctx, query, email).Scan(
		&u.ID,
		&u.Email,
		&u.PasswordHash,
		&u.FullName,
		&u.AuthProvider,
		&u.GoogleID,
		&u.AppleID,
		&u.AvatarURL,
		&u.IsEmailVerified,
		&u.EmailVerifiedAt,
		&u.Phone,
		&u.PhoneVerifiedAt,
		&u.Status,
		&u.GlobalRole,
		&u.CreatedAt,
		&u.UpdatedAt,
		&u.LastLoginAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, domain.ErrUserNotFound
		}
		return nil, err
	}
	return &u, nil
}

func (r *UserRepo) GetByGoogleID(ctx context.Context, googleID string) (*domain.User, error) {
	return r.GetUserByAuthIdentity(ctx, "GOOGLE", googleID)
}

func (r *UserRepo) GetByAppleID(ctx context.Context, appleID string) (*domain.User, error) {
	return r.GetUserByAuthIdentity(ctx, "APPLE", appleID)
}

func (r *UserRepo) GetUserByAuthProvider(ctx context.Context, provider, providerUserID string) (*domain.User, error) {
	return r.GetUserByAuthIdentity(ctx, provider, providerUserID)
}

func (r *UserRepo) LinkAuthProvider(ctx context.Context, userID uuid.UUID, provider, providerUserID string) error {
	identity := &domain.AuthIdentity{
		ID:              uuid.New(),
		UserID:          userID,
		Provider:        provider,
		ProviderSubject: providerUserID,
		ProviderEmail:   "",
		CreatedAt:       time.Now().UTC(),
	}
	return r.LinkAuthIdentity(ctx, identity)
}

func (r *UserRepo) GetAuthProvider(ctx context.Context, provider, providerUserID string) (*domain.UserAuthProvider, error) {
	ident, err := r.GetAuthIdentity(ctx, provider, providerUserID)
	if err != nil {
		return nil, err
	}
	return &domain.UserAuthProvider{
		ID:             ident.ID,
		UserID:         ident.UserID,
		Provider:       ident.Provider,
		ProviderUserID: ident.ProviderSubject,
		CreatedAt:      ident.CreatedAt,
	}, nil
}

func (r *UserRepo) LinkAuthIdentity(ctx context.Context, identity *domain.AuthIdentity) error {
	query := `
		INSERT INTO auth_identities (id, user_id, provider, provider_subject, provider_email, created_at, last_login_at)
		VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
		ON CONFLICT (provider, provider_subject)
		DO UPDATE SET user_id = EXCLUDED.user_id, last_login_at = NOW()
	`
	if identity.ID == uuid.Nil {
		identity.ID = uuid.New()
	}
	_, err := r.pool.Exec(ctx, query, identity.ID, identity.UserID, identity.Provider, identity.ProviderSubject, identity.ProviderEmail)
	return err
}

func (r *UserRepo) GetAuthIdentity(ctx context.Context, provider, providerSubject string) (*domain.AuthIdentity, error) {
	query := `
		SELECT id, user_id, provider, provider_subject, provider_email, created_at, last_login_at
		FROM auth_identities
		WHERE provider = $1 AND provider_subject = $2
	`
	var ai domain.AuthIdentity
	err := r.pool.QueryRow(ctx, query, provider, providerSubject).Scan(
		&ai.ID,
		&ai.UserID,
		&ai.Provider,
		&ai.ProviderSubject,
		&ai.ProviderEmail,
		&ai.CreatedAt,
		&ai.LastLoginAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, domain.ErrUserNotFound
		}
		return nil, err
	}
	return &ai, nil
}

func (r *UserRepo) GetUserByAuthIdentity(ctx context.Context, provider, providerSubject string) (*domain.User, error) {
	query := `
		SELECT u.id, u.email, u.password_hash, u.full_name, u.auth_provider, u.google_id, u.apple_id, u.avatar_url, 
		       u.is_email_verified, u.email_verified_at, u.phone, u.phone_verified_at, u.status, u.global_role, 
		       u.created_at, u.updated_at, u.last_login_at
		FROM users u
		INNER JOIN auth_identities ai ON u.id = ai.user_id
		WHERE ai.provider = $1 AND ai.provider_subject = $2
	`
	var u domain.User
	err := r.pool.QueryRow(ctx, query, provider, providerSubject).Scan(
		&u.ID,
		&u.Email,
		&u.PasswordHash,
		&u.FullName,
		&u.AuthProvider,
		&u.GoogleID,
		&u.AppleID,
		&u.AvatarURL,
		&u.IsEmailVerified,
		&u.EmailVerifiedAt,
		&u.Phone,
		&u.PhoneVerifiedAt,
		&u.Status,
		&u.GlobalRole,
		&u.CreatedAt,
		&u.UpdatedAt,
		&u.LastLoginAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, domain.ErrUserNotFound
		}
		return nil, err
	}
	return &u, nil
}

func (r *UserRepo) UpdateEmailVerified(ctx context.Context, id uuid.UUID, verified bool) error {
	query := `UPDATE users SET is_email_verified = $2, email_verified_at = CASE WHEN $2 THEN NOW() ELSE NULL END, updated_at = NOW() WHERE id = $1`
	_, err := r.pool.Exec(ctx, query, id, verified)
	return err
}

func (r *UserRepo) UpdateLastLogin(ctx context.Context, id uuid.UUID) error {
	query := `UPDATE users SET last_login_at = NOW(), updated_at = NOW() WHERE id = $1`
	_, err := r.pool.Exec(ctx, query, id)
	return err
}
