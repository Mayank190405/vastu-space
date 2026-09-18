package tests

import (
	"testing"

	"vastu/backend/internal/domain"
	"vastu/backend/internal/pkg/jwt"

	"github.com/google/uuid"
)

func TestJWTGenerationAndValidation(t *testing.T) {
	secret := "test_secret_key_1234567890_test_secret_key_1234567890"
	manager := jwt.NewTokenManager(secret, 15, 7)

	user := &domain.User{
		ID:         uuid.New(),
		Email:      "operator@vastu.local",
		FullName:   "Test Operator",
		GlobalRole: domain.RoleUser,
	}
	orgID := uuid.New()

	tokens, hash, err := manager.GenerateTokenPair(user, &orgID, domain.RoleCaptureOperator)
	if err != nil {
		t.Fatalf("expected token generation to succeed, got: %v", err)
	}

	if tokens.AccessToken == "" || tokens.RefreshToken == "" || hash == "" {
		t.Fatal("expected non-empty tokens and hash")
	}

	claims, err := manager.ValidateAccessToken(tokens.AccessToken)
	if err != nil {
		t.Fatalf("expected token validation to succeed, got: %v", err)
	}

	if claims.Email != user.Email || claims.UserID != user.ID {
		t.Fatalf("expected claims to match user, got email: %s, id: %s", claims.Email, claims.UserID)
	}

	if claims.MemberRole != domain.RoleCaptureOperator {
		t.Fatalf("expected member role capture_operator, got: %s", claims.MemberRole)
	}
}

func TestJWTInvalidSecretRejection(t *testing.T) {
	manager1 := jwt.NewTokenManager("secret_key_1_12345678901234567890", 15, 7)
	manager2 := jwt.NewTokenManager("secret_key_2_12345678901234567890", 15, 7)

	user := &domain.User{
		ID:         uuid.New(),
		Email:      "user@vastu.local",
		FullName:   "User",
		GlobalRole: domain.RoleUser,
	}

	tokens, _, _ := manager1.GenerateTokenPair(user, nil, domain.RoleMember)

	_, err := manager2.ValidateAccessToken(tokens.AccessToken)
	if err == nil {
		t.Fatal("expected validation to fail when validated with different secret key")
	}
}
