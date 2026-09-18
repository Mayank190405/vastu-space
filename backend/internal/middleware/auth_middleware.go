package middleware

import (
	"context"
	"net/http"
	"strings"

	"vastu/backend/internal/domain"
	"vastu/backend/internal/pkg/jwt"
)

type contextKey string

const (
	UserClaimsKey contextKey = "user_claims"
)

type AuthMiddleware struct {
	jwtManager *jwt.TokenManager
}

func NewAuthMiddleware(jwtManager *jwt.TokenManager) *AuthMiddleware {
	return &AuthMiddleware{jwtManager: jwtManager}
}

func (m *AuthMiddleware) Authenticate(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		authHeader := r.Header.Get("Authorization")
		if authHeader == "" {
			http.Error(w, `{"error":"missing authorization header"}`, http.StatusUnauthorized)
			return
		}

		parts := strings.SplitN(authHeader, " ", 2)
		if len(parts) != 2 || !strings.EqualFold(parts[0], "Bearer") {
			http.Error(w, `{"error":"invalid authorization header format"}`, http.StatusUnauthorized)
			return
		}

		tokenStr := parts[1]
		claims, err := m.jwtManager.ValidateAccessToken(tokenStr)
		if err != nil {
			http.Error(w, `{"error":"invalid or expired token"}`, http.StatusUnauthorized)
			return
		}

		ctx := context.WithValue(r.Context(), UserClaimsKey, claims)
		next.ServeHTTP(w, r.WithContext(ctx))
	})
}

func GetClaimsFromContext(ctx context.Context) (*domain.TokenClaims, bool) {
	claims, ok := ctx.Value(UserClaimsKey).(*domain.TokenClaims)
	return claims, ok
}

func SetClaimsContext(ctx context.Context, claims *domain.TokenClaims) context.Context {
	return context.WithValue(ctx, UserClaimsKey, claims)
}
