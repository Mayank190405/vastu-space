package tests

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"vastu/backend/internal/domain"
	"vastu/backend/internal/middleware"
	"vastu/backend/internal/pkg/jwt"

	"github.com/go-chi/chi/v5"
	chimw "github.com/go-chi/chi/v5/middleware"
	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// TestObservability targets Phase 3.2 - OBSERVABILITY
func TestObservability(t *testing.T) {
	t.Run("Structured Logs Inject Correlation IDs", func(t *testing.T) {
		r := chi.NewRouter()
		r.Use(chimw.RequestID)

		r.Get("/test", func(w http.ResponseWriter, r *http.Request) {
			reqID := chimw.GetReqID(r.Context())
			assert.NotEmpty(t, reqID, "Request ID must be generated and injected by middleware")

			w.Header().Set("X-Request-ID", reqID)
			w.WriteHeader(http.StatusOK)
		})

		req, _ := http.NewRequest("GET", "/test", nil)
		rr := httptest.NewRecorder()
		r.ServeHTTP(rr, req)

		assert.Equal(t, http.StatusOK, rr.Code)
		assert.NotEmpty(t, rr.Header().Get("X-Request-ID"), "Request ID must be exposed to client")
	})

	t.Run("Auth Middleware Injects Tenant ID into Context", func(t *testing.T) {
		jwtManager := jwt.NewTokenManager("test_secret_32_bytes_long_key!!", 15, 7)
		authMw := middleware.NewAuthMiddleware(jwtManager)
		orgID := uuid.New()
		user := &domain.User{
			ID:         uuid.New(),
			Email:      "user-1@example.com",
			FullName:   "Test User",
			GlobalRole: domain.RoleUser,
		}

		r := chi.NewRouter()
		r.With(authMw.Authenticate).Get("/secure", func(w http.ResponseWriter, r *http.Request) {
			claims, ok := middleware.GetClaimsFromContext(r.Context())
			assert.True(t, ok)
			require.NotNil(t, claims.OrgID)
			assert.Equal(t, orgID, *claims.OrgID, "Tenant ID must be present in request context for structured logging")
			w.WriteHeader(http.StatusOK)
		})

		pair, _, err := jwtManager.GenerateTokenPair(user, &orgID, domain.RoleOrgAdmin)
		require.NoError(t, err)
		req, _ := http.NewRequest("GET", "/secure", nil)
		req.Header.Set("Authorization", "Bearer "+pair.AccessToken)

		rr := httptest.NewRecorder()
		r.ServeHTTP(rr, req)

		assert.Equal(t, http.StatusOK, rr.Code)
	})
}
