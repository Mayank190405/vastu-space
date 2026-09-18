package domain

import (
	"time"

	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
)

type TokenClaims struct {
	UserID     uuid.UUID  `json:"uid"`
	Email      string     `json:"email"`
	FullName   string     `json:"name"`
	GlobalRole GlobalRole `json:"grole"`
	OrgID      *uuid.UUID `json:"oid,omitempty"`
	MemberRole MemberRole `json:"mrole,omitempty"`
	jwt.RegisteredClaims
}

type TokenPair struct {
	AccessToken  string `json:"access_token"`
	RefreshToken string `json:"refresh_token"`
	ExpiresIn    int64  `json:"expires_in"` // in seconds
	TokenType    string `json:"token_type"`
}

type RefreshToken struct {
	ID        uuid.UUID  `json:"id"`
	UserID    uuid.UUID  `json:"user_id"`
	TokenHash string     `json:"token_hash"`
	ExpiresAt time.Time  `json:"expires_at"`
	RevokedAt *time.Time `json:"revoked_at,omitempty"`
	CreatedAt time.Time  `json:"created_at"`
}

type RefreshInput struct {
	RefreshToken string `json:"refresh_token"`
}
