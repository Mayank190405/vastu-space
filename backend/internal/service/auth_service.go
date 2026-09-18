package service

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"time"

	"vastu/backend/internal/domain"
	"vastu/backend/internal/pkg/hasher"
	"vastu/backend/internal/pkg/jwt"
	"vastu/backend/internal/pkg/utils"
	"vastu/backend/internal/pkg/validator"
	"vastu/backend/internal/repository"

	"github.com/google/uuid"
)

type AuthService struct {
	userRepo        repository.UserRepository
	orgRepo         repository.OrgRepository
	memberRepo      repository.MemberRepository
	tokenRepo       repository.TokenRepository
	identRepo       repository.IdentifierRepository
	docRepo         repository.DocumentRepository
	addrRepo        repository.AddressRepository
	inviteRepo      repository.InviteRepository
	joinReqRepo     repository.JoinRequestRepository
	otpService      *OTPService
	googleSvc       *GoogleService
	appleSvc        *AppleService
	jwtManager      *jwt.TokenManager
	appBaseURL      string
}

func NewAuthService(
	userRepo repository.UserRepository,
	orgRepo repository.OrgRepository,
	memberRepo repository.MemberRepository,
	tokenRepo repository.TokenRepository,
	identRepo repository.IdentifierRepository,
	docRepo repository.DocumentRepository,
	addrRepo repository.AddressRepository,
	inviteRepo repository.InviteRepository,
	joinReqRepo repository.JoinRequestRepository,
	otpService *OTPService,
	googleSvc *GoogleService,
	appleSvc *AppleService,
	jwtManager *jwt.TokenManager,
	appBaseURL string,
) *AuthService {
	if appBaseURL == "" {
		appBaseURL = "http://localhost:3000"
	}
	return &AuthService{
		userRepo:    userRepo,
		orgRepo:     orgRepo,
		memberRepo:  memberRepo,
		tokenRepo:   tokenRepo,
		identRepo:   identRepo,
		docRepo:     docRepo,
		addrRepo:    addrRepo,
		inviteRepo:  inviteRepo,
		joinReqRepo: joinReqRepo,
		otpService:  otpService,
		googleSvc:   googleSvc,
		appleSvc:    appleSvc,
		jwtManager:  jwtManager,
		appBaseURL:  appBaseURL,
	}
}

// GetUserProfile returns complete profile and active organization
func (s *AuthService) GetUserProfile(ctx context.Context, userID uuid.UUID) (*domain.User, *domain.Organization, string, []*domain.OrganizationMember, error) {
	user, err := s.userRepo.GetByID(ctx, userID)
	if err != nil {
		return nil, nil, "", nil, err
	}

	memberships, _ := s.memberRepo.GetUserMemberships(ctx, userID)
	var activeOrg *domain.Organization
	var activeRole string = "member"

	for _, m := range memberships {
		if m.Status == domain.MemberStatusActive {
			org, _ := s.orgRepo.GetByID(ctx, m.OrgID)
			if org != nil {
				activeOrg = org
				activeRole = string(m.Role)
				break
			}
		}
	}

	return user, activeOrg, activeRole, memberships, nil
}

func normalizeOtpPurpose(purpose string) domain.OtpPurpose {
	p := strings.ToLower(strings.TrimSpace(purpose))
	switch p {
	case "org_signup", "orgsignup":
		return domain.OtpPurposeOrgSignup
	case "employee_signup", "employeesignup":
		return domain.OtpPurposeEmployeeSignup
	case "user_signup", "usersignup":
		return domain.OtpPurposeUserSignup
	case "password_reset", "passwordreset":
		return domain.OtpPurposePasswordReset
	default:
		return domain.OtpPurposeLogin
	}
}

// SendOTP sends an email OTP for specified purpose
func (s *AuthService) SendOTP(ctx context.Context, email, purpose string) (string, error) {
	cleanEmail := strings.ToLower(strings.TrimSpace(email))
	if cleanEmail == "" {
		return "", errors.New("email is required")
	}

	otpPurpose := normalizeOtpPurpose(purpose)

	// Rate limiting check: max 5 OTP requests in 10 minutes
	count, err := s.otpService.otpRepo.CountRecentAttempts(ctx, cleanEmail, otpPurpose, 10*time.Minute)
	if err == nil && count >= 5 {
		return "", errors.New("too many OTP requests. Please wait 10 minutes before trying again.")
	}

	return s.otpService.GenerateAndSendOTP(ctx, cleanEmail, "User", otpPurpose, nil)
}

// VerifyOTP verifies email OTP code
func (s *AuthService) VerifyOTP(ctx context.Context, email, otpCode, purpose string) (*domain.User, *domain.TokenPair, []*domain.OrganizationMember, error) {
	cleanEmail := strings.ToLower(strings.TrimSpace(email))
	otpPurpose := normalizeOtpPurpose(purpose)

	_, err := s.otpService.VerifyOTP(ctx, cleanEmail, otpCode, otpPurpose)
	if err != nil {
		return nil, nil, nil, err
	}

	user, err := s.userRepo.GetByEmail(ctx, cleanEmail)
	now := time.Now().UTC()
	if err != nil || user == nil {
		// Auto-provision User with backend-generated UUID
		user = &domain.User{
			ID:              uuid.New(),
			Email:           cleanEmail,
			FullName:        strings.Split(cleanEmail, "@")[0],
			AuthProvider:    domain.AuthProviderEmail,
			IsEmailVerified: true,
			EmailVerifiedAt: &now,
			Status:          "active",
			GlobalRole:      domain.RoleUser,
			CreatedAt:       now,
			UpdatedAt:       now,
		}
		if err := s.userRepo.Create(ctx, user); err != nil {
			return nil, nil, nil, fmt.Errorf("failed to create user: %w", err)
		}

		// Link AuthIdentity for EMAIL provider
		identity := &domain.AuthIdentity{
			ID:              uuid.New(),
			UserID:          user.ID,
			Provider:        "EMAIL",
			ProviderSubject: cleanEmail,
			ProviderEmail:   cleanEmail,
			CreatedAt:       now,
		}
		_ = s.userRepo.LinkAuthIdentity(ctx, identity)
	} else {
		// Mark email verified
		_ = s.userRepo.UpdateEmailVerified(ctx, user.ID, true)
		user.IsEmailVerified = true

		// Ensure AuthIdentity exists for EMAIL provider
		identity := &domain.AuthIdentity{
			ID:              uuid.New(),
			UserID:          user.ID,
			Provider:        "EMAIL",
			ProviderSubject: cleanEmail,
			ProviderEmail:   cleanEmail,
			CreatedAt:       now,
		}
		_ = s.userRepo.LinkAuthIdentity(ctx, identity)
	}

	memberships, _ := s.memberRepo.GetUserMemberships(ctx, user.ID)
	var activeOrgID *uuid.UUID
	var role domain.MemberRole = domain.RoleMember
	for _, m := range memberships {
		if m.Status == domain.MemberStatusActive {
			activeOrgID = &m.OrgID
			role = m.Role
			break
		}
	}

	tokens, tokenHash, err := s.jwtManager.GenerateTokenPair(user, activeOrgID, role)
	if err != nil {
		return nil, nil, nil, err
	}

	rfRecord := &domain.RefreshToken{
		ID:        uuid.New(),
		UserID:    user.ID,
		TokenHash: tokenHash,
		ExpiresAt: time.Now().UTC().Add(7 * 24 * time.Hour),
	}
	_ = s.tokenRepo.CreateRefreshToken(ctx, rfRecord)
	_ = s.userRepo.UpdateLastLogin(ctx, user.ID)

	return user, tokens, memberships, nil
}

// GoogleAuth verifies Google ID token and links or creates User
func (s *AuthService) GoogleAuth(ctx context.Context, idToken string) (*domain.User, *domain.TokenPair, []*domain.OrganizationMember, error) {
	googleUser, err := s.googleSvc.ValidateIDToken(ctx, idToken)
	if err != nil {
		return nil, nil, nil, fmt.Errorf("invalid google token: %w", err)
	}

	cleanEmail := strings.ToLower(strings.TrimSpace(googleUser.Email))
	if cleanEmail == "" {
		return nil, nil, nil, errors.New("google account missing email")
	}

	// Check if already linked via AuthIdentity
	user, err := s.userRepo.GetUserByAuthIdentity(ctx, "GOOGLE", googleUser.Subject)
	if err != nil || user == nil {
		// Check by email
		user, _ = s.userRepo.GetByEmail(ctx, cleanEmail)
		now := time.Now().UTC()

		if user == nil {
			// Create new user
			user = &domain.User{
				ID:              uuid.New(),
				Email:           cleanEmail,
				FullName:        googleUser.Name,
				AuthProvider:    domain.AuthProviderGoogle,
				GoogleID:        &googleUser.Subject,
				AvatarURL:       &googleUser.Picture,
				IsEmailVerified: true,
				EmailVerifiedAt: &now,
				Status:          "active",
				GlobalRole:      domain.RoleUser,
				CreatedAt:       now,
				UpdatedAt:       now,
			}
			if err := s.userRepo.Create(ctx, user); err != nil {
				return nil, nil, nil, err
			}
		} else {
			_ = s.userRepo.UpdateEmailVerified(ctx, user.ID, true)
		}

		// Link AuthIdentity
		identity := &domain.AuthIdentity{
			ID:              uuid.New(),
			UserID:          user.ID,
			Provider:        "GOOGLE",
			ProviderSubject: googleUser.Subject,
			ProviderEmail:   cleanEmail,
			CreatedAt:       now,
		}
		_ = s.userRepo.LinkAuthIdentity(ctx, identity)
	}

	memberships, _ := s.memberRepo.GetUserMemberships(ctx, user.ID)
	var activeOrgID *uuid.UUID
	var role domain.MemberRole = domain.RoleMember
	for _, m := range memberships {
		if m.Status == domain.MemberStatusActive {
			activeOrgID = &m.OrgID
			role = m.Role
			break
		}
	}

	tokens, tokenHash, err := s.jwtManager.GenerateTokenPair(user, activeOrgID, role)
	if err != nil {
		return nil, nil, nil, err
	}

	rfRecord := &domain.RefreshToken{
		ID:        uuid.New(),
		UserID:    user.ID,
		TokenHash: tokenHash,
		ExpiresAt: time.Now().UTC().Add(7 * 24 * time.Hour),
	}
	_ = s.tokenRepo.CreateRefreshToken(ctx, rfRecord)
	_ = s.userRepo.UpdateLastLogin(ctx, user.ID)

	return user, tokens, memberships, nil
}

// Login with email & password
func (s *AuthService) Login(ctx context.Context, input domain.LoginInput) (*domain.User, *domain.TokenPair, []*domain.OrganizationMember, error) {
	cleanEmail := strings.ToLower(strings.TrimSpace(input.Email))
	user, err := s.userRepo.GetByEmail(ctx, cleanEmail)
	if err != nil {
		return nil, nil, nil, domain.ErrUserNotFound
	}

	if user.PasswordHash == nil || *user.PasswordHash == "" {
		return nil, nil, nil, errors.New("this account uses Google or OTP authentication. Please log in with Google or Email OTP.")
	}

	if !hasher.VerifyPassword(input.Password, *user.PasswordHash) {
		return nil, nil, nil, domain.ErrInvalidCredentials
	}

	memberships, _ := s.memberRepo.GetUserMemberships(ctx, user.ID)
	var activeOrgID *uuid.UUID
	var role domain.MemberRole = domain.RoleMember
	for _, m := range memberships {
		if m.Status == domain.MemberStatusActive {
			activeOrgID = &m.OrgID
			role = m.Role
			break
		}
	}

	tokens, tokenHash, err := s.jwtManager.GenerateTokenPair(user, activeOrgID, role)
	if err != nil {
		return nil, nil, nil, err
	}

	rfRecord := &domain.RefreshToken{
		ID:        uuid.New(),
		UserID:    user.ID,
		TokenHash: tokenHash,
		ExpiresAt: time.Now().UTC().Add(7 * 24 * time.Hour),
	}
	_ = s.tokenRepo.CreateRefreshToken(ctx, rfRecord)
	_ = s.userRepo.UpdateLastLogin(ctx, user.ID)

	return user, tokens, memberships, nil
}

// Complete Organization Signup Transaction
func (s *AuthService) CompleteOrganizationSignup(ctx context.Context, input domain.OrgSignupCompleteInput) (map[string]interface{}, error) {
	if input.OrganizationName == "" && input.OrgName != "" {
		input.OrganizationName = input.OrgName
	}
	if input.ApplicantName == "" && input.FullName != "" {
		input.ApplicantName = input.FullName
	}
	cleanEmail := strings.ToLower(strings.TrimSpace(input.Email))
	if cleanEmail == "" || input.OrganizationName == "" || input.ApplicantName == "" {
		return nil, errors.New("organization name, applicant name, and email are required")
	}

	// 1. Password validation (if password provided)
	var passwordHash *string
	if input.Password != "" {
		if err := validator.ValidatePassword(input.Password, cleanEmail, input.ApplicantName, input.OrganizationName); err != nil {
			return nil, err
		}
		hash, err := hasher.HashPassword(input.Password)
		if err != nil {
			return nil, err
		}
		passwordHash = &hash
	}

	// 2. GSTIN / Identifier validation & uniqueness check
	var identifier *domain.OrganizationIdentifier
	if input.IdentifierType != "" && input.IdentifierValue != "" {
		identType := strings.ToUpper(strings.TrimSpace(input.IdentifierType))
		cleanVal := strings.TrimSpace(input.IdentifierValue)
		normVal := strings.ToUpper(cleanVal)

		if identType == "GSTIN" {
			if !validator.ValidateGSTIN(cleanVal) {
				return nil, errors.New("invalid GSTIN format. Expected 15-character alphanumeric format (e.g. 29AAAAA0000A1Z5)")
			}
		} else if identType == "PAN" {
			if !validator.ValidatePAN(cleanVal) {
				return nil, errors.New("invalid PAN format. Expected 10-character format (e.g. AAAAA0000A)")
			}
		}

		// Check global uniqueness on normalized value
		existingIdent, err := s.identRepo.GetByNormalized(ctx, identType, normVal)
		if err == nil && existingIdent != nil {
			return nil, fmt.Errorf("an organization with this %s (%s) is already registered in the system", identType, cleanVal)
		}

		identifier = &domain.OrganizationIdentifier{
			ID:                 uuid.New(),
			Type:               identType,
			Value:              cleanVal,
			NormalizedValue:    normVal,
			VerificationStatus: "UNVERIFIED",
		}
	}

	// 3. User setup
	now := time.Now().UTC()
	user := &domain.User{
		ID:              uuid.New(),
		Email:           cleanEmail,
		FullName:        input.ApplicantName,
		PasswordHash:    passwordHash,
		AuthProvider:    domain.AuthProviderEmail,
		Phone:           &input.Phone,
		IsEmailVerified: true,
		EmailVerifiedAt: &now,
		Status:          "active",
		GlobalRole:      domain.RoleUser,
	}

	var authIdentity *domain.AuthIdentity
	if input.GoogleToken != "" {
		googleUser, err := s.googleSvc.ValidateIDToken(ctx, input.GoogleToken)
		if err == nil && googleUser != nil {
			user.AuthProvider = domain.AuthProviderGoogle
			user.GoogleID = &googleUser.Subject
			authIdentity = &domain.AuthIdentity{
				ID:              uuid.New(),
				UserID:          user.ID,
				Provider:        "GOOGLE",
				ProviderSubject: googleUser.Subject,
				ProviderEmail:   cleanEmail,
				CreatedAt:       now,
			}
		}
	} else {
		authIdentity = &domain.AuthIdentity{
			ID:              uuid.New(),
			UserID:          user.ID,
			Provider:        "EMAIL",
			ProviderSubject: cleanEmail,
			ProviderEmail:   cleanEmail,
			CreatedAt:       now,
		}
	}

	// 4. Generate 12-char Organization Code
	orgCode := utils.Generate12CharOrgCode()

	legalName := input.LegalName
	if legalName == "" {
		legalName = input.OrganizationName
	}
	officialEmail := input.OfficialEmail
	if officialEmail == "" {
		officialEmail = cleanEmail
	}
	officialPhone := input.OfficialPhone
	if officialPhone == "" {
		officialPhone = input.Phone
	}

	org := &domain.Organization{
		ID:                uuid.New(),
		OrgCode:           orgCode,
		Name:              input.OrganizationName,
		LegalName:         &legalName,
		OrgType:           input.OrganizationType,
		Industry:          input.Industry,
		Country:           input.Country,
		State:             input.State,
		City:              input.City,
		Website:           input.Website,
		OfficialEmail:     &officialEmail,
		OfficialPhone:     &officialPhone,
		YearEstablished:   input.YearEstablished,
		NumberOfEmployees: &input.NumberOfEmployees,
		BusinessType:      &input.BusinessType,
		Description:       input.Description,
		LogoURL:           input.LogoURL,
		Status:            domain.OrgStatusActive, // Owner is immediately active
	}
	if identifier != nil {
		org.TaxIDType = identifier.Type
		org.TaxIDNumber = identifier.Value
	}

	// 5. Supporting Document if supplied
	var doc *domain.OrganizationDocument
	if input.DocumentURL != "" {
		docType := input.DocumentType
		if docType == "" {
			docType = "GST Certificate"
		}
		docName := input.DocumentName
		if docName == "" {
			docName = "Supporting_Document.pdf"
		}
		doc = &domain.OrganizationDocument{
			ID:                 uuid.New(),
			OrganizationID:     org.ID,
			DocumentType:       docType,
			FileID:             uuid.New().String(),
			FileName:           docName,
			MimeType:           "application/pdf",
			FileSize:           1024,
			VerificationStatus: "UPLOADED",
		}
		org.DocumentURL = input.DocumentURL
		org.DocumentOriginalName = &docName
	}

	// 6. Organization Address
	var addr *domain.OrganizationAddress
	if input.AddressLine1 != "" {
		country := input.Country
		if country == "" {
			country = "India"
		}
		addr = &domain.OrganizationAddress{
			ID:             uuid.New(),
			OrganizationID: org.ID,
			Type:           "PRIMARY",
			AddressLine1:   input.AddressLine1,
			AddressLine2:   &input.AddressLine2,
			Locality:       &input.Locality,
			City:           input.City,
			District:       &input.District,
			State:          input.State,
			Country:        country,
			Pincode:        input.Pincode,
			Latitude:       input.Latitude,
			Longitude:      input.Longitude,
			IsPrimary:      true,
		}
	}

	// 7. Founder Membership with role OWNER
	member := &domain.OrganizationMember{
		ID:     uuid.New(),
		OrgID:  org.ID,
		UserID: user.ID,
		Role:   domain.RoleOwner,
		Status: domain.MemberStatusActive,
	}

	// 8. Default Invite Link
	rawToken, tokenHash := utils.GenerateInviteToken()
	preview := rawToken
	if len(preview) > 12 {
		preview = preview[:12]
	}
	invite := &domain.OrganizationInvite{
		ID:              uuid.New(),
		OrganizationID:  org.ID,
		TokenHash:       tokenHash,
		RawTokenPreview: preview,
		ExpiresAt:       time.Now().UTC().Add(30 * 24 * time.Hour), // 30 days
		MaxUses:         0,                                         // unlimited
	}

	// Execute atomic transaction
	if err := s.orgRepo.CreateOrganizationAtomic(ctx, user, authIdentity, org, identifier, doc, addr, member, invite); err != nil {
		return nil, fmt.Errorf("failed to create organization atomically: %w", err)
	}

	// Generate JWT session tokens with role OWNER
	tokens, tokenHashVal, err := s.jwtManager.GenerateTokenPair(user, &org.ID, domain.RoleOwner)
	if err != nil {
		return nil, err
	}
	rfRecord := &domain.RefreshToken{
		ID:        uuid.New(),
		UserID:    user.ID,
		TokenHash: tokenHashVal,
		ExpiresAt: time.Now().UTC().Add(7 * 24 * time.Hour),
	}
	_ = s.tokenRepo.CreateRefreshToken(ctx, rfRecord)

	inviteURL := fmt.Sprintf("%s/join/%s/%s", s.appBaseURL, org.OrgCode, rawToken)
	whatsAppMsg := fmt.Sprintf("You are invited to join %s.\nJoin the organization using this link:\n%s", org.Name, inviteURL)

	return map[string]interface{}{
		"token": tokens.AccessToken,
		"user":  user,
		"organization": map[string]interface{}{
			"id":         org.ID,
			"org_code":   org.OrgCode,
			"name":       org.Name,
			"legal_name": org.LegalName,
			"role":       "OWNER",
		},
		"tokens": tokens,
		"invite": map[string]interface{}{
			"invite_url":       inviteURL,
			"invite_token":     rawToken,
			"whatsapp_message": whatsAppMsg,
		},
	}, nil
}

// Submit Employee Join Request from invite link
func (s *AuthService) SubmitEmployeeJoinRequest(ctx context.Context, input domain.EmployeeSignupInput) (map[string]interface{}, error) {
	cleanOrgCode := strings.ToUpper(strings.TrimSpace(input.OrgCode))
	cleanEmail := strings.ToLower(strings.TrimSpace(input.Email))
	if cleanOrgCode == "" || cleanEmail == "" || input.FullName == "" {
		return nil, errors.New("org_code, email, and full_name are required")
	}

	// 1. Validate Organization by Code
	org, err := s.orgRepo.GetByCode(ctx, cleanOrgCode)
	if err != nil || org == nil {
		return nil, errors.New("invalid organization code")
	}

	// 2. Validate Invite Token if provided
	var invite *domain.OrganizationInvite
	if input.InviteToken != "" && input.InviteToken != "DIRECT_CODE" && input.InviteToken != "DIRECT_JOIN" {
		tokenHash := utils.HashInviteToken(input.InviteToken)
		inv, err := s.inviteRepo.GetByTokenHash(ctx, tokenHash)
		if err != nil || inv == nil {
			return nil, errors.New("invalid or expired invitation link")
		}
		if inv.IsRevoked || inv.ExpiresAt.Before(time.Now().UTC()) {
			return nil, errors.New("this invitation link has expired or been revoked")
		}
		if inv.OrganizationID != org.ID {
			return nil, errors.New("invitation token does not match organization")
		}
		invite = inv
	}

	// 3. Resolve or Create User
	now := time.Now().UTC()
	user, err := s.userRepo.GetByEmail(ctx, cleanEmail)
	if user == nil {
		var passwordHash *string
		if input.Password != "" {
			if err := validator.ValidatePassword(input.Password, cleanEmail, input.FullName, org.Name); err == nil {
				hash, _ := hasher.HashPassword(input.Password)
				passwordHash = &hash
			}
		}

		user = &domain.User{
			ID:              uuid.New(),
			Email:           cleanEmail,
			FullName:        input.FullName,
			PasswordHash:    passwordHash,
			AuthProvider:    domain.AuthProviderEmail,
			Phone:           &input.Phone,
			IsEmailVerified: true,
			EmailVerifiedAt: &now,
			Status:          "active",
			GlobalRole:      domain.RoleUser,
			CreatedAt:       now,
			UpdatedAt:       now,
		}
		if input.GoogleToken != "" {
			user.AuthProvider = domain.AuthProviderGoogle
		}
		if err := s.userRepo.Create(ctx, user); err != nil {
			return nil, err
		}
	} else {
		_ = s.userRepo.UpdateEmailVerified(ctx, user.ID, true)
	}

	// 4. Create Join Request with status PENDING
	var inviteID *uuid.UUID
	if invite != nil {
		inviteID = &invite.ID
	}
	joinReq := &domain.OrganizationJoinRequest{
		ID:             uuid.New(),
		OrganizationID: org.ID,
		UserID:         user.ID,
		InviteID:       inviteID,
		ApplicantName:  input.FullName,
		ApplicantEmail: cleanEmail,
		ApplicantPhone: input.Phone,
		RequestedRole:  "MEMBER",
		Status:         "PENDING",
	}

	if err := s.joinReqRepo.Create(ctx, joinReq); err != nil {
		return nil, err
	}

	if invite != nil {
		_ = s.inviteRepo.IncrementUse(ctx, invite.ID)
	}

	// Issue JWT token with no active org yet
	tokens, tokenHashVal, _ := s.jwtManager.GenerateTokenPair(user, nil, domain.RoleMember)
	rfRecord := &domain.RefreshToken{
		ID:        uuid.New(),
		UserID:    user.ID,
		TokenHash: tokenHashVal,
		ExpiresAt: time.Now().UTC().Add(7 * 24 * time.Hour),
	}
	_ = s.tokenRepo.CreateRefreshToken(ctx, rfRecord)

	return map[string]interface{}{
		"user": user,
		"organization": map[string]interface{}{
			"id":       org.ID,
			"org_code": org.OrgCode,
			"name":     org.Name,
		},
		"join_request": map[string]interface{}{
			"id":     joinReq.ID,
			"status": "PENDING",
		},
		"tokens": tokens,
	}, nil
}

// RefreshTokens refreshes JWT session
func (s *AuthService) RefreshTokens(ctx context.Context, refreshToken string) (*domain.TokenPair, error) {
	hash := jwt.HashRefreshToken(refreshToken)
	record, err := s.tokenRepo.GetRefreshToken(ctx, hash)
	if err != nil || record == nil || record.RevokedAt != nil || record.ExpiresAt.Before(time.Now().UTC()) {
		return nil, domain.ErrInvalidToken
	}

	user, err := s.userRepo.GetByID(ctx, record.UserID)
	if err != nil {
		return nil, domain.ErrUserNotFound
	}

	memberships, _ := s.memberRepo.GetUserMemberships(ctx, user.ID)
	var activeOrgID *uuid.UUID
	var role domain.MemberRole = domain.RoleMember
	for _, m := range memberships {
		if m.Status == domain.MemberStatusActive {
			activeOrgID = &m.OrgID
			role = m.Role
			break
		}
	}

	newPair, newHash, err := s.jwtManager.GenerateTokenPair(user, activeOrgID, role)
	if err != nil {
		return nil, err
	}

	_ = s.tokenRepo.RevokeRefreshToken(ctx, hash)
	rfRecord := &domain.RefreshToken{
		ID:        uuid.New(),
		UserID:    user.ID,
		TokenHash: newHash,
		ExpiresAt: time.Now().UTC().Add(7 * 24 * time.Hour),
	}
	_ = s.tokenRepo.CreateRefreshToken(ctx, rfRecord)
	return newPair, nil
}

// Logout revokes refresh token
func (s *AuthService) Logout(ctx context.Context, tokenHash string) error {
	return s.tokenRepo.RevokeRefreshToken(ctx, tokenHash)
}
