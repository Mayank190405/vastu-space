package tests

import (
	"testing"

	"vastu/backend/internal/pkg/hasher"
)

func TestPasswordHashingAndVerification(t *testing.T) {
	password := "SecurePassword123!"

	hash, err := hasher.HashPassword(password)
	if err != nil {
		t.Fatalf("expected no error hashing password, got: %v", err)
	}

	if hash == password {
		t.Fatal("expected hashed password to differ from plaintext")
	}

	if !hasher.VerifyPassword(password, hash) {
		t.Fatal("expected password verification to succeed with correct password")
	}

	if hasher.VerifyPassword("WrongPassword123!", hash) {
		t.Fatal("expected password verification to fail with incorrect password")
	}
}

func TestShortPasswordRejection(t *testing.T) {
	_, err := hasher.HashPassword("short")
	if err == nil {
		t.Fatal("expected error for password shorter than 8 characters")
	}
}
