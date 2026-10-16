package domain

import (
	"time"

	"github.com/google/uuid"
)

type AuthProvider string

const (
	AuthProviderLocal  AuthProvider = "local"
	AuthProviderEmail  AuthProvider = "local" // Map to database 'local' auth_provider_enum
	AuthProviderGoogle AuthProvider = "google"
	AuthProviderApple  AuthProvider = "apple"
)

type GlobalRole string

const (
	RolePlatformAdmin GlobalRole = "platform_admin"
	RoleUser          GlobalRole = "user"
)

type User struct {
	ID              uuid.UUID    `json:"id"`
	Email           string       `json:"email"`
	PasswordHash    *string      `json:"-"`
	FullName        string       `json:"full_name"`
	AuthProvider    AuthProvider `json:"auth_provider"`
	GoogleID        *string      `json:"google_id,omitempty"`
	AppleID         *string      `json:"apple_id,omitempty"`
	AvatarURL       *string      `json:"avatar_url,omitempty"`
	IsEmailVerified bool         `json:"is_email_verified"`
	EmailVerifiedAt *time.Time   `json:"email_verified_at,omitempty"`
	Phone           *string      `json:"phone,omitempty"`
	PhoneVerifiedAt *time.Time   `json:"phone_verified_at,omitempty"`
	Status          string       `json:"status"`
	GlobalRole      GlobalRole   `json:"global_role"`
	CreatedAt       time.Time    `json:"created_at"`
	UpdatedAt       time.Time    `json:"updated_at"`
	LastLoginAt     *time.Time   `json:"last_login_at,omitempty"`
}

type AuthIdentity struct {
	ID              uuid.UUID `json:"id"`
	UserID          uuid.UUID `json:"user_id"`
	Provider        string    `json:"provider"`
	ProviderSubject string    `json:"provider_subject"`
	ProviderEmail   string    `json:"provider_email"`
	CreatedAt       time.Time `json:"created_at"`
	LastLoginAt     *time.Time `json:"last_login_at,omitempty"`
}

type UserRegistrationInput struct {
	FullName string `json:"full_name"`
	Email    string `json:"email"`
	Password string `json:"password"`
	Phone    string `json:"phone"`
}

type LoginInput struct {
	Email    string `json:"email"`
	Password string `json:"password"`
}

type UserAuthProvider struct {
	ID             uuid.UUID `json:"id"`
	UserID         uuid.UUID `json:"user_id"`
	Provider       string    `json:"provider"`
	ProviderUserID string    `json:"provider_user_id"`
	CreatedAt      time.Time `json:"created_at"`
}

type GoogleAuthInput struct {
	IDToken string `json:"id_token"`
}

type AppleAuthInput struct {
	IDToken  string  `json:"id_token"`
	FullName *string `json:"full_name,omitempty"`
}
