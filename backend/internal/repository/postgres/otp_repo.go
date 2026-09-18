package postgres

import (
	"context"
	"encoding/json"
	"errors"
	"time"

	"vastu/backend/internal/domain"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

type OTPRepo struct {
	pool *pgxpool.Pool
}

func NewOTPRepo(pool *pgxpool.Pool) *OTPRepo {
	return &OTPRepo{pool: pool}
}

func (r *OTPRepo) Create(ctx context.Context, otp *domain.EmailOTP) error {
	query := `
		INSERT INTO email_otps (id, email, otp_code, purpose, metadata, expires_at, is_used, created_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
	`
	now := time.Now().UTC()
	otp.CreatedAt = now

	metaJSON, err := json.Marshal(otp.Metadata)
	if err != nil {
		metaJSON = []byte("{}")
	}

	_, err = r.pool.Exec(ctx, query,
		otp.ID,
		otp.Email,
		otp.OTPCode,
		otp.Purpose,
		metaJSON,
		otp.ExpiresAt,
		otp.IsUsed,
		otp.CreatedAt,
	)
	return err
}

func (r *OTPRepo) GetValidOTP(ctx context.Context, email, otpCode string, purpose domain.OtpPurpose) (*domain.EmailOTP, error) {
	query := `
		SELECT id, email, otp_code, purpose, metadata, expires_at, is_used, created_at
		FROM email_otps
		WHERE email = $1 AND otp_code = $2 AND purpose = $3 AND is_used = false
		ORDER BY created_at DESC
		LIMIT 1
	`
	var o domain.EmailOTP
	var metaBytes []byte
	err := r.pool.QueryRow(ctx, query, email, otpCode, purpose).Scan(
		&o.ID,
		&o.Email,
		&o.OTPCode,
		&o.Purpose,
		&metaBytes,
		&o.ExpiresAt,
		&o.IsUsed,
		&o.CreatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, domain.ErrInvalidOTP
		}
		return nil, err
	}

	if len(metaBytes) > 0 {
		_ = json.Unmarshal(metaBytes, &o.Metadata)
	}

	if time.Now().UTC().After(o.ExpiresAt) {
		return nil, domain.ErrOTPExpired
	}

	return &o, nil
}

func (r *OTPRepo) MarkAsUsed(ctx context.Context, id uuid.UUID) error {
	query := `UPDATE email_otps SET is_used = true WHERE id = $1`
	_, err := r.pool.Exec(ctx, query, id)
	return err
}

func (r *OTPRepo) CountRecentAttempts(ctx context.Context, email string, purpose domain.OtpPurpose, window time.Duration) (int, error) {
	since := time.Now().UTC().Add(-window)
	query := `SELECT COUNT(*) FROM email_otps WHERE email = $1 AND purpose = $2 AND created_at >= $3`
	var count int
	err := r.pool.QueryRow(ctx, query, email, purpose, since).Scan(&count)
	return count, err
}

