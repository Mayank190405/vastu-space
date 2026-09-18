package middleware

import (
	"net/http"

	"vastu/backend/internal/domain"
)

func RequireGlobalRole(allowedRoles ...domain.GlobalRole) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			claims, ok := GetClaimsFromContext(r.Context())
			if !ok {
				http.Error(w, `{"error":"unauthorized"}`, http.StatusUnauthorized)
				return
			}

			allowed := false
			for _, r := range allowedRoles {
				if claims.GlobalRole == r {
					allowed = true
					break
				}
			}

			if !allowed {
				http.Error(w, `{"error":"forbidden: insufficient platform privileges"}`, http.StatusForbidden)
				return
			}

			next.ServeHTTP(w, r)
		})
	}
}

func RequireMemberRole(allowedRoles ...domain.MemberRole) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			claims, ok := GetClaimsFromContext(r.Context())
			if !ok {
				http.Error(w, `{"error":"unauthorized"}`, http.StatusUnauthorized)
				return
			}

			allowed := false
			for _, r := range allowedRoles {
				if claims.MemberRole == r {
					allowed = true
					break
				}
			}

			if !allowed {
				http.Error(w, `{"error":"forbidden: insufficient organization privileges"}`, http.StatusForbidden)
				return
			}

			next.ServeHTTP(w, r)
		})
	}
}
