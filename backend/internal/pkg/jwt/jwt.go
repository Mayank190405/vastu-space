package jwt

import (
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"time"

	"vastu/backend/internal/domain"

	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
)

type TokenManager struct {
	secretKey        []byte
	accessExpiryMin  time.Duration
	refreshExpiryDay time.Duration
	issuer           string
}

func NewTokenManager(secret string, accessExpiryMin, refreshExpiryDay int) *TokenManager {
	return &TokenManager{
		secretKey:        []byte(secret),
		accessExpiryMin:  time.Duration(accessExpiryMin) * time.Minute,
		refreshExpiryDay: time.Duration(refreshExpiryDay) * 24 * time.Hour,
		issuer:           "vastu-spatial-platform",
	}
}

func (tm *TokenManager) GenerateTokenPair(user *domain.User, orgID *uuid.UUID, memberRole domain.MemberRole) (*domain.TokenPair, string, error) {
	now := time.Now().UTC()
	accessExpiresAt := now.Add(tm.accessExpiryMin)

	claims := &domain.TokenClaims{
		UserID:     user.ID,
		Email:      user.Email,
		FullName:   user.FullName,
		GlobalRole: user.GlobalRole,
		OrgID:      orgID,
		MemberRole: memberRole,
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(accessExpiresAt),
			IssuedAt:  jwt.NewNumericDate(now),
			NotBefore: jwt.NewNumericDate(now),
			Issuer:    tm.issuer,
			Subject:   user.ID.String(),
		},
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	accessTokenString, err := token.SignedString(tm.secretKey)
	if err != nil {
		return nil, "", err
	}

	// Generate opaque random refresh token
	rawRefreshToken := uuid.New().String() + "-" + uuid.New().String()
	refreshTokenHash := HashRefreshToken(rawRefreshToken)

	pair := &domain.TokenPair{
		AccessToken:  accessTokenString,
		RefreshToken: rawRefreshToken,
		ExpiresIn:    int64(tm.accessExpiryMin.Seconds()),
		TokenType:    "Bearer",
	}

	return pair, refreshTokenHash, nil
}

func (tm *TokenManager) ValidateAccessToken(tokenString string) (*domain.TokenClaims, error) {
	token, err := jwt.ParseWithClaims(tokenString, &domain.TokenClaims{}, func(t *jwt.Token) (interface{}, error) {
		if _, ok := t.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, errors.New("unexpected signing method")
		}
		return tm.secretKey, nil
	})

	if err != nil {
		return nil, err
	}

	claims, ok := token.Claims.(*domain.TokenClaims)
	if !ok || !token.Valid {
		return nil, errors.New("invalid token claims")
	}

	return claims, nil
}

func HashRefreshToken(rawToken string) string {
	hasher := sha256.New()
	hasher.Write([]byte(rawToken))
	return hex.EncodeToString(hasher.Sum(nil))
}
