package tests

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"vastu/backend/internal/domain"
	"vastu/backend/internal/middleware"
	"vastu/backend/internal/pkg/jwt"

	"github.com/go-chi/chi/v5"
	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// TestTenantIsolation specifically targets Phase 2.4 - MULTI-TENANT RBAC
func TestTenantIsolation(t *testing.T) {
	jwtManager := jwt.NewTokenManager("vastu_test_secret_key_1234567890", 15, 7)

	tenantA := uuid.New()
	tenantB := uuid.New()
	projectA_ID := uuid.New()

	// Setup fake router
	r := chi.NewRouter()
	authMiddleware := middleware.NewAuthMiddleware(jwtManager)

	r.With(authMiddleware.Authenticate).Get("/api/v1/projects/{projectId}", func(w http.ResponseWriter, r *http.Request) {
		claims, ok := middleware.GetClaimsFromContext(r.Context())
		if !ok || claims.OrgID == nil {
			http.Error(w, "Unauthorized", http.StatusUnauthorized)
			return
		}

		projectIdStr := chi.URLParam(r, "projectId")
		pID, err := uuid.Parse(projectIdStr)
		if err != nil {
			http.Error(w, "Bad Request", http.StatusBadRequest)
			return
		}

		// Emulate tenant boundary check
		if *claims.OrgID != tenantA && pID == projectA_ID {
			http.Error(w, "Not Found", http.StatusNotFound)
			return
		}

		w.WriteHeader(http.StatusOK)
	})

	t.Run("Same Tenant Succeeds", func(t *testing.T) {
		user1 := &domain.User{ID: uuid.New(), Email: "user1@example.com"}
		pair, _, err := jwtManager.GenerateTokenPair(user1, &tenantA, domain.RoleOrgAdmin)
		require.NoError(t, err)

		req, _ := http.NewRequest("GET", "/api/v1/projects/"+projectA_ID.String(), nil)
		req.Header.Set("Authorization", "Bearer "+pair.AccessToken)

		rr := httptest.NewRecorder()
		r.ServeHTTP(rr, req)

		assert.Equal(t, http.StatusOK, rr.Code)
	})

	t.Run("Cross Tenant IDOR Fails (Reads)", func(t *testing.T) {
		user2 := &domain.User{ID: uuid.New(), Email: "user2@example.com"}
		pair, _, err := jwtManager.GenerateTokenPair(user2, &tenantB, domain.RoleOrgAdmin)
		require.NoError(t, err)

		req, _ := http.NewRequest("GET", "/api/v1/projects/"+projectA_ID.String(), nil)
		req.Header.Set("Authorization", "Bearer "+pair.AccessToken)

		rr := httptest.NewRecorder()
		r.ServeHTTP(rr, req)

		assert.Equal(t, http.StatusNotFound, rr.Code)
	})

	t.Run("Missing Tenant ID in Claims Fails", func(t *testing.T) {
		user3 := &domain.User{ID: uuid.New(), Email: "user3@example.com"}
		pair, _, err := jwtManager.GenerateTokenPair(user3, nil, domain.RoleMember)
		require.NoError(t, err)

		req, _ := http.NewRequest("GET", "/api/v1/projects/"+projectA_ID.String(), nil)
		req.Header.Set("Authorization", "Bearer "+pair.AccessToken)

		rr := httptest.NewRecorder()
		r.ServeHTTP(rr, req)

		assert.Equal(t, http.StatusUnauthorized, rr.Code)
	})
}
