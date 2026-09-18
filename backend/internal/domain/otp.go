package domain

import (
	"time"

	"github.com/google/uuid"
)

type OtpPurpose string

const (
	OtpPurposeOrgSignup      OtpPurpose = "org_signup"
	OtpPurposeUserSignup     OtpPurpose = "user_signup"
	OtpPurposeEmployeeSignup OtpPurpose = "employee_signup"
	OtpPurposeLogin          OtpPurpose = "login"
	OtpPurposePasswordReset  OtpPurpose = "password_reset"
)

type EmailOTP struct {
	ID        uuid.UUID              `json:"id"`
	Email     string                 `json:"email"`
	OTPCode   string                 `json:"otp_code"`
	Purpose   OtpPurpose             `json:"purpose"`
	Metadata  map[string]interface{} `json:"metadata"`
	ExpiresAt time.Time              `json:"expires_at"`
	IsUsed    bool                   `json:"is_used"`
	CreatedAt time.Time              `json:"created_at"`
}

type VerifyOTPInput struct {
	Email   string     `json:"email"`
	OTPCode string     `json:"otp_code"`
	Purpose OtpPurpose `json:"purpose"`
}
