package service

import (
	"context"
	"time"

	"vastu/backend/internal/domain"
	"vastu/backend/internal/pkg/mailer"
	"vastu/backend/internal/pkg/utils"
	"vastu/backend/internal/repository"

	"github.com/google/uuid"
)

type OTPService struct {
	otpRepo repository.OTPRepository
	mailer  *mailer.SMTPMailer
}

func NewOTPService(otpRepo repository.OTPRepository, mailer *mailer.SMTPMailer) *OTPService {
	return &OTPService{
		otpRepo: otpRepo,
		mailer:  mailer,
	}
}

func (s *OTPService) GenerateAndSendOTP(ctx context.Context, email, fullName string, purpose domain.OtpPurpose, metadata map[string]interface{}) (string, error) {
	code, err := utils.GenerateOTP()
	if err != nil {
		return "", err
	}

	otp := &domain.EmailOTP{
		ID:        uuid.New(),
		Email:     email,
		OTPCode:   code,
		Purpose:   purpose,
		Metadata:  metadata,
		ExpiresAt: time.Now().UTC().Add(10 * time.Minute),
		IsUsed:    false,
	}

	if err := s.otpRepo.Create(ctx, otp); err != nil {
		return "", err
	}

	purposeTitle := "Email Verification"
	if purpose == domain.OtpPurposeOrgSignup {
		purposeTitle = "Organization Onboarding"
	} else if purpose == domain.OtpPurposePasswordReset {
		purposeTitle = "Password Reset"
	}

	// Dispatch email via Hostinger SSL SMTP on port 465
	if s.mailer != nil {
		go func() {
			_ = s.mailer.SendOTPEmail(email, fullName, code, purposeTitle)
		}()
	}

	return code, nil
}

func (s *OTPService) VerifyOTP(ctx context.Context, email, otpCode string, purpose domain.OtpPurpose) (*domain.EmailOTP, error) {
	otp, err := s.otpRepo.GetValidOTP(ctx, email, otpCode, purpose)
	if err != nil {
		return nil, err
	}

	if err := s.otpRepo.MarkAsUsed(ctx, otp.ID); err != nil {
		return nil, err
	}

	return otp, nil
}
