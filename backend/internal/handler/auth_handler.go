package handler

import (
	"encoding/json"
	"errors"
	"net/http"

	"vastu/backend/internal/domain"
	"vastu/backend/internal/middleware"
	"vastu/backend/internal/service"
)

type AuthHandler struct {
	authService *service.AuthService
}

func NewAuthHandler(authService *service.AuthService) *AuthHandler {
	return &AuthHandler{authService: authService}
}

// POST /api/v1/auth/signup/organization
func (h *AuthHandler) CompleteOrgSignup(w http.ResponseWriter, r *http.Request) {
	var input domain.OrgSignupCompleteInput
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		JSONError(w, http.StatusBadRequest, "invalid request body")
		return
	}

	result, err := h.authService.CompleteOrganizationSignup(r.Context(), input)
	if err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusCreated, "Organization created and founder registered successfully", result)
}

// POST /api/v1/auth/signup/emp or /api/v1/auth/join/org
func (h *AuthHandler) SubmitEmployeeJoin(w http.ResponseWriter, r *http.Request) {
	var input domain.EmployeeSignupInput
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		JSONError(w, http.StatusBadRequest, "invalid request body")
		return
	}

	result, err := h.authService.SubmitEmployeeJoinRequest(r.Context(), input)
	if err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Join request submitted. Pending organization admin approval.", result)
}

// POST /api/v1/auth/otp/send
func (h *AuthHandler) SendOTP(w http.ResponseWriter, r *http.Request) {
	var input struct {
		Email   string `json:"email"`
		Purpose string `json:"purpose"`
	}
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		JSONError(w, http.StatusBadRequest, "invalid request body")
		return
	}

	if input.Email == "" {
		JSONError(w, http.StatusBadRequest, "email is required")
		return
	}
	if input.Purpose == "" {
		input.Purpose = "LOGIN"
	}

	code, err := h.authService.SendOTP(r.Context(), input.Email, input.Purpose)
	if err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Verification OTP has been sent to your email address", map[string]interface{}{
		"email":     input.Email,
		"purpose":   input.Purpose,
		"debug_otp": code,
	})
}

// POST /api/v1/auth/otp/verify
func (h *AuthHandler) VerifyOTP(w http.ResponseWriter, r *http.Request) {
	var input struct {
		Email   string `json:"email"`
		OTPCode string `json:"otp_code"`
		Purpose string `json:"purpose"`
	}
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		JSONError(w, http.StatusBadRequest, "invalid request body")
		return
	}

	if input.Email == "" || input.OTPCode == "" {
		JSONError(w, http.StatusBadRequest, "email and otp_code are required")
		return
	}
	if input.Purpose == "" {
		input.Purpose = "LOGIN"
	}

	user, tokens, memberships, err := h.authService.VerifyOTP(r.Context(), input.Email, input.OTPCode, input.Purpose)
	if err != nil {
		JSONError(w, http.StatusUnauthorized, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "OTP verified successfully", map[string]interface{}{
		"user":        user,
		"tokens":      tokens,
		"token":       tokens.AccessToken,
		"memberships": memberships,
	})
}

// POST /api/v1/auth/login
func (h *AuthHandler) Login(w http.ResponseWriter, r *http.Request) {
	var input domain.LoginInput
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		JSONError(w, http.StatusBadRequest, "invalid request body")
		return
	}

	user, tokens, memberships, err := h.authService.Login(r.Context(), input)
	if err != nil {
		if errors.Is(err, domain.ErrUserNotFound) {
			JSONError(w, http.StatusNotFound, "Account with this email does not exist. Please sign up first.")
			return
		}
		JSONError(w, http.StatusUnauthorized, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Login successful", map[string]interface{}{
		"user":        user,
		"tokens":      tokens,
		"token":       tokens.AccessToken,
		"memberships": memberships,
	})
}

// POST /api/v1/auth/google
func (h *AuthHandler) GoogleAuth(w http.ResponseWriter, r *http.Request) {
	var input struct {
		IDToken string `json:"id_token"`
	}
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		JSONError(w, http.StatusBadRequest, "invalid request body")
		return
	}

	user, tokens, memberships, err := h.authService.GoogleAuth(r.Context(), input.IDToken)
	if err != nil {
		JSONError(w, http.StatusUnauthorized, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Google authentication successful", map[string]interface{}{
		"user":        user,
		"tokens":      tokens,
		"token":       tokens.AccessToken,
		"memberships": memberships,
	})
}

// POST /api/v1/auth/token/refresh or /api/v1/auth/refresh
func (h *AuthHandler) Refresh(w http.ResponseWriter, r *http.Request) {
	var input struct {
		RefreshToken string `json:"refresh_token"`
	}
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		JSONError(w, http.StatusBadRequest, "invalid request body")
		return
	}

	tokens, err := h.authService.RefreshTokens(r.Context(), input.RefreshToken)
	if err != nil {
		JSONError(w, http.StatusUnauthorized, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Token refreshed", tokens)
}

// POST /api/v1/auth/logout
func (h *AuthHandler) Logout(w http.ResponseWriter, r *http.Request) {
	var input struct {
		RefreshToken string `json:"refresh_token"`
	}
	_ = json.NewDecoder(r.Body).Decode(&input)

	if input.RefreshToken != "" {
		_ = h.authService.Logout(r.Context(), input.RefreshToken)
	}

	JSONSuccess(w, http.StatusOK, "Logged out successfully", nil)
}

// GET /api/v1/auth/me (Protected)
func (h *AuthHandler) GetMe(w http.ResponseWriter, r *http.Request) {
	claims, ok := middleware.GetClaimsFromContext(r.Context())
	if !ok {
		JSONError(w, http.StatusUnauthorized, "unauthorized")
		return
	}

	user, activeOrg, activeRole, memberships, err := h.authService.GetUserProfile(r.Context(), claims.UserID)
	if err != nil {
		JSONSuccess(w, http.StatusOK, "Current user claims", claims)
		return
	}

	JSONSuccess(w, http.StatusOK, "Current user profile", map[string]interface{}{
		"user":        user,
		"active_org":  activeOrg,
		"active_role": activeRole,
		"memberships": memberships,
		"claims":      claims,
	})
}

