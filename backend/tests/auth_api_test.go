package tests

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"vastu/backend/internal/domain"
	"vastu/backend/internal/handler"
	jwtpkg "vastu/backend/internal/pkg/jwt"
	"vastu/backend/internal/pkg/mailer"
	"vastu/backend/internal/service"

	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// ---------------------------------------------------------------------------
// In-memory mock repositories for Auth testing
// ---------------------------------------------------------------------------

type mockUserRepo struct {
	users map[string]*domain.User // keyed by email
}

func newMockUserRepo() *mockUserRepo {
	return &mockUserRepo{users: make(map[string]*domain.User)}
}

func (m *mockUserRepo) Create(ctx context.Context, u *domain.User) error {
	m.users[u.Email] = u
	return nil
}

func (m *mockUserRepo) GetByEmail(ctx context.Context, email string) (*domain.User, error) {
	u, ok := m.users[email]
	if !ok {
		return nil, domain.ErrUserNotFound
	}
	return u, nil
}

func (m *mockUserRepo) GetByID(ctx context.Context, id uuid.UUID) (*domain.User, error) {
	for _, u := range m.users {
		if u.ID == id {
			return u, nil
		}
	}
	return nil, domain.ErrUserNotFound
}

func (m *mockUserRepo) Update(ctx context.Context, u *domain.User) error {
	m.users[u.Email] = u
	return nil
}

func (m *mockUserRepo) UpdatePassword(ctx context.Context, id uuid.UUID, hash string) error {
	for _, u := range m.users {
		if u.ID == id {
			u.PasswordHash = &hash
			return nil
		}
	}
	return domain.ErrUserNotFound
}

func (m *mockUserRepo) UpdateEmailVerified(ctx context.Context, id uuid.UUID, verified bool) error {
	for _, u := range m.users {
		if u.ID == id {
			u.IsEmailVerified = verified
			return nil
		}
	}
	return domain.ErrUserNotFound
}

func (m *mockUserRepo) UpdateLastLogin(ctx context.Context, id uuid.UUID) error { return nil }

func (m *mockUserRepo) GetByGoogleID(ctx context.Context, googleID string) (*domain.User, error) {
	return nil, domain.ErrUserNotFound
}

func (m *mockUserRepo) GetByAppleID(ctx context.Context, appleID string) (*domain.User, error) {
	return nil, domain.ErrUserNotFound
}

func (m *mockUserRepo) GetUserByAuthProvider(ctx context.Context, provider, providerUserID string) (*domain.User, error) {
	return nil, domain.ErrUserNotFound
}

func (m *mockUserRepo) LinkAuthProvider(ctx context.Context, userID uuid.UUID, provider, providerUserID string) error {
	return nil
}

func (m *mockUserRepo) GetAuthProvider(ctx context.Context, provider, providerUserID string) (*domain.UserAuthProvider, error) {
	return nil, domain.ErrUserNotFound
}

// ---------------------------------------------------------------------------
// OTP Repository mock — implements repository.OTPRepository
// ---------------------------------------------------------------------------

type mockOTPRepo struct {
	otps map[string]*domain.EmailOTP // keyed by email:purpose
}

func newMockOTPRepo() *mockOTPRepo {
	return &mockOTPRepo{otps: make(map[string]*domain.EmailOTP)}
}

func (m *mockOTPRepo) Create(ctx context.Context, otp *domain.EmailOTP) error {
	m.otps[string(otp.Email)+":"+string(otp.Purpose)] = otp
	return nil
}

func (m *mockOTPRepo) GetValidOTP(ctx context.Context, email, otpCode string, purpose domain.OtpPurpose) (*domain.EmailOTP, error) {
	rec, ok := m.otps[email+":"+string(purpose)]
	if !ok || rec.OTPCode != otpCode || rec.IsUsed || rec.ExpiresAt.Before(time.Now()) {
		return nil, domain.ErrInvalidOTP
	}
	return rec, nil
}

func (m *mockOTPRepo) MarkAsUsed(ctx context.Context, id uuid.UUID) error {
	for _, rec := range m.otps {
		if rec.ID == id {
			rec.IsUsed = true
			return nil
		}
	}
	return nil
}

// ---------------------------------------------------------------------------
// Org Repository mock — implements repository.OrgRepository
// ---------------------------------------------------------------------------

type mockOrgRepo struct{}

func (m *mockOrgRepo) Create(ctx context.Context, org *domain.Organization) error { return nil }
func (m *mockOrgRepo) GetByID(ctx context.Context, id uuid.UUID) (*domain.Organization, error) {
	return &domain.Organization{ID: id, Name: "Test Org"}, nil
}
func (m *mockOrgRepo) GetByCode(ctx context.Context, orgCode string) (*domain.Organization, error) {
	return &domain.Organization{ID: uuid.New(), Name: "Test Org", OrgCode: orgCode}, nil
}
func (m *mockOrgRepo) UpdateStatus(ctx context.Context, id uuid.UUID, status domain.OrgStatus) error {
	return nil
}
func (m *mockOrgRepo) UpdateOrgCode(ctx context.Context, id uuid.UUID, newCode string) error {
	return nil
}

// ---------------------------------------------------------------------------
// Member Repository mock — implements repository.MemberRepository
// ---------------------------------------------------------------------------

type mockMemberRepo struct{}

func (m *mockMemberRepo) Create(ctx context.Context, member *domain.OrganizationMember) error {
	return nil
}
func (m *mockMemberRepo) GetByOrgAndUser(ctx context.Context, orgID, userID uuid.UUID) (*domain.OrganizationMember, error) {
	return &domain.OrganizationMember{OrgID: orgID, UserID: userID, Role: domain.RoleOrgAdmin, Status: domain.MemberStatusActive}, nil
}
func (m *mockMemberRepo) GetByID(ctx context.Context, id uuid.UUID) (*domain.OrganizationMember, error) {
	return nil, nil
}
func (m *mockMemberRepo) GetUserMemberships(ctx context.Context, userID uuid.UUID) ([]*domain.OrganizationMember, error) {
	return []*domain.OrganizationMember{{UserID: userID, Role: domain.RoleOrgAdmin, Status: domain.MemberStatusActive}}, nil
}
func (m *mockMemberRepo) GetPendingMembersByOrg(ctx context.Context, orgID uuid.UUID) ([]*domain.OrganizationMember, error) {
	return nil, nil
}
func (m *mockMemberRepo) UpdateStatus(ctx context.Context, id uuid.UUID, status domain.MemberStatus, role domain.MemberRole, approvedBy uuid.UUID, approvedAt time.Time) error {
	return nil
}

// ---------------------------------------------------------------------------
// Token Repository mock — implements repository.TokenRepository
// ---------------------------------------------------------------------------

type mockTokenRepo struct{}

func (m *mockTokenRepo) CreateRefreshToken(ctx context.Context, token *domain.RefreshToken) error {
	return nil
}
func (m *mockTokenRepo) GetRefreshToken(ctx context.Context, tokenHash string) (*domain.RefreshToken, error) {
	return nil, nil
}
func (m *mockTokenRepo) RevokeRefreshToken(ctx context.Context, tokenHash string) error { return nil }
func (m *mockTokenRepo) RevokeUserTokens(ctx context.Context, userID uuid.UUID) error  { return nil }

// ---------------------------------------------------------------------------
// Setup helpers
// ---------------------------------------------------------------------------

func setupAuthAPI() (*handler.AuthHandler, *mockUserRepo, *mockOTPRepo, *jwtpkg.TokenManager) {
	userRepo := newMockUserRepo()
	otpRepo := newMockOTPRepo()
	orgRepo := &mockOrgRepo{}
	memberRepo := &mockMemberRepo{}
	tokenRepo := &mockTokenRepo{}
	tokenMgr := jwtpkg.NewTokenManager("vastu-test-secret-32-bytes-long-key-!", 15, 7)

	otpService := service.NewOTPService(otpRepo, (*mailer.SMTPMailer)(nil))

	authService := service.NewAuthService(
		userRepo,
		orgRepo,
		memberRepo,
		tokenRepo,
		otpService,
		nil,
		nil,
		tokenMgr,
	)

	authHandler := handler.NewAuthHandler(authService)
	return authHandler, userRepo, otpRepo, tokenMgr
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

func TestAuthAPI(t *testing.T) {
	authHandler, userRepo, otpRepo, _ := setupAuthAPI()

	t.Run("POST /api/v1/auth/signup/user - Successful Registration triggers OTP", func(t *testing.T) {
		reqBody := domain.UserRegistrationInput{
			Email:    "architect@vastu.space",
			Password: "SecurePassword123!",
			FullName: "Ramesh Kumar",
		}
		data, _ := json.Marshal(reqBody)
		req := httptest.NewRequest(http.MethodPost, "/api/v1/auth/signup/user", bytes.NewReader(data))
		req.Header.Set("Content-Type", "application/json")
		rr := httptest.NewRecorder()

		authHandler.SignupUser(rr, req)

		assert.Equal(t, http.StatusOK, rr.Code)
		var resp map[string]interface{}
		err := json.Unmarshal(rr.Body.Bytes(), &resp)
		require.NoError(t, err)
		assert.True(t, resp["success"].(bool))

		// Verify user stored in unverified state
		u, err := userRepo.GetByEmail(context.Background(), "architect@vastu.space")
		require.NoError(t, err)
		assert.False(t, u.IsEmailVerified)
	})

	t.Run("POST /api/v1/auth/signup/user - Invalid JSON rejects 400", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodPost, "/api/v1/auth/signup/user", bytes.NewReader([]byte("{malformed")))
		req.Header.Set("Content-Type", "application/json")
		rr := httptest.NewRecorder()

		authHandler.SignupUser(rr, req)
		assert.Equal(t, http.StatusBadRequest, rr.Code)
	})

	t.Run("POST /api/v1/auth/verify-otp - Verify Signup OTP", func(t *testing.T) {
		// Seed OTP directly into mock repo
		otpRec := &domain.EmailOTP{
			ID:        uuid.New(),
			Email:     "architect@vastu.space",
			OTPCode:   "123456",
			Purpose:   domain.OtpPurposeUserSignup,
			ExpiresAt: time.Now().Add(10 * time.Minute),
			IsUsed:    false,
		}
		_ = otpRepo.Create(context.Background(), otpRec)

		verifyBody := domain.VerifyOTPInput{
			Email:   "architect@vastu.space",
			OTPCode: "123456",
			Purpose: domain.OtpPurposeUserSignup,
		}
		data, _ := json.Marshal(verifyBody)
		req := httptest.NewRequest(http.MethodPost, "/api/v1/auth/verify-otp", bytes.NewReader(data))
		req.Header.Set("Content-Type", "application/json")
		rr := httptest.NewRecorder()

		authHandler.VerifyUserOTP(rr, req)

		assert.Equal(t, http.StatusOK, rr.Code)
		u, _ := userRepo.GetByEmail(context.Background(), "architect@vastu.space")
		assert.True(t, u.IsEmailVerified)
	})

	t.Run("POST /api/v1/auth/verify-otp - Wrong OTP rejects 401", func(t *testing.T) {
		verifyBody := domain.VerifyOTPInput{
			Email:   "architect@vastu.space",
			OTPCode: "000000",
			Purpose: domain.OtpPurposeUserSignup,
		}
		data, _ := json.Marshal(verifyBody)
		req := httptest.NewRequest(http.MethodPost, "/api/v1/auth/verify-otp", bytes.NewReader(data))
		req.Header.Set("Content-Type", "application/json")
		rr := httptest.NewRecorder()

		authHandler.VerifyUserOTP(rr, req)
		assert.Equal(t, http.StatusUnauthorized, rr.Code)
	})

	t.Run("POST /api/v1/auth/login - Valid credentials return tokens", func(t *testing.T) {
		loginBody := domain.LoginInput{
			Email:    "architect@vastu.space",
			Password: "SecurePassword123!",
		}
		data, _ := json.Marshal(loginBody)
		req := httptest.NewRequest(http.MethodPost, "/api/v1/auth/login", bytes.NewReader(data))
		req.Header.Set("Content-Type", "application/json")
		rr := httptest.NewRecorder()

		authHandler.Login(rr, req)

		assert.Equal(t, http.StatusOK, rr.Code)
		var resp map[string]interface{}
		json.Unmarshal(rr.Body.Bytes(), &resp)
		resData := resp["data"].(map[string]interface{})
		assert.NotNil(t, resData["tokens"])
	})

	t.Run("POST /api/v1/auth/login - Wrong password rejects 401", func(t *testing.T) {
		loginBody := domain.LoginInput{
			Email:    "architect@vastu.space",
			Password: "WrongPassword!",
		}
		data, _ := json.Marshal(loginBody)
		req := httptest.NewRequest(http.MethodPost, "/api/v1/auth/login", bytes.NewReader(data))
		req.Header.Set("Content-Type", "application/json")
		rr := httptest.NewRecorder()

		authHandler.Login(rr, req)
		assert.Equal(t, http.StatusUnauthorized, rr.Code)
	})

	t.Run("POST /api/v1/auth/request-otp - Request login OTP succeeds", func(t *testing.T) {
		reqPayload := map[string]string{
			"email":   "architect@vastu.space",
			"purpose": string(domain.OtpPurposeLogin),
		}
		data, _ := json.Marshal(reqPayload)
		req := httptest.NewRequest(http.MethodPost, "/api/v1/auth/request-otp", bytes.NewReader(data))
		req.Header.Set("Content-Type", "application/json")
		rr := httptest.NewRecorder()

		authHandler.RequestOTP(rr, req)
		assert.Equal(t, http.StatusOK, rr.Code)
	})
}
