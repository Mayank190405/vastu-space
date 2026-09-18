package tests

import (
	"testing"
	"time"

	"vastu/backend/internal/domain"
	"vastu/backend/internal/pkg/jwt"

	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// TestAuthSecurity specifically targets Phase 2.3 - JWT SECURITY
func TestAuthSecurity(t *testing.T) {
	jwtManager := jwt.NewTokenManager("vastu_test_secret_key_1234567890", 15, 7) // 15 min expiry

	// Helper to build a minimal domain.User for token generation
	makeUser := func(id string) *domain.User {
		uid, _ := uuid.Parse(id)
		return &domain.User{
			ID:         uid,
			Email:      "test@vastu.space",
			FullName:   "Test User",
			GlobalRole: domain.RoleUser,
		}
	}

	t.Run("Valid Token Succeeds", func(t *testing.T) {
		user := makeUser("00000000-0000-0000-0000-000000000001")
		orgID := uuid.MustParse("00000000-0000-0000-0000-000000000002")
		pair, _, err := jwtManager.GenerateTokenPair(user, &orgID, domain.RoleOrgAdmin)
		require.NoError(t, err)

		claims, err := jwtManager.ValidateAccessToken(pair.AccessToken)
		assert.NoError(t, err)
		assert.Equal(t, user.ID, claims.UserID)
		assert.Equal(t, &orgID, claims.OrgID)
	})

	t.Run("Expired Token Fails", func(t *testing.T) {
		// Manager with 0 minute expiry (will expire immediately)
		shortJWTManager := jwt.NewTokenManager("vastu_test_secret_key_1234567890", 0, 7)
		user := makeUser("00000000-0000-0000-0000-000000000001")
		pair, _, err := shortJWTManager.GenerateTokenPair(user, nil, domain.RoleOrgAdmin)
		require.NoError(t, err)

		time.Sleep(1 * time.Second) // Ensure it's expired

		_, err = shortJWTManager.ValidateAccessToken(pair.AccessToken)
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "token is expired")
	})

	t.Run("Modified Signature Fails", func(t *testing.T) {
		user := makeUser("00000000-0000-0000-0000-000000000001")
		pair, _, err := jwtManager.GenerateTokenPair(user, nil, domain.RoleOrgAdmin)
		require.NoError(t, err)

		// Corrupt the signature part (the part after the last dot)
		corruptedToken := pair.AccessToken[:len(pair.AccessToken)-5] + "XXXXX"

		_, err = jwtManager.ValidateAccessToken(corruptedToken)
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "signature is invalid")
	})

	t.Run("Wrong Secret Fails", func(t *testing.T) {
		user := makeUser("00000000-0000-0000-0000-000000000001")
		pair, _, err := jwtManager.GenerateTokenPair(user, nil, domain.RoleOrgAdmin)
		require.NoError(t, err)

		wrongJWTManager := jwt.NewTokenManager("wrong_secret_key_1234567890_987", 15, 7)
		_, err = wrongJWTManager.ValidateAccessToken(pair.AccessToken)
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "signature is invalid")
	})

	t.Run("Malformed Token Fails", func(t *testing.T) {
		_, err := jwtManager.ValidateAccessToken("this.is.not.a.real.jwt")
		assert.Error(t, err)
	})
}
