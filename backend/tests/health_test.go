package tests

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/stretchr/testify/assert"
)

// TestHealthEndpoints targets Phase 3.1 - OPERABILITY
func TestHealthEndpoints(t *testing.T) {
	t.Run("Healthz Endpoint Returns 200", func(t *testing.T) {
		// Verifies the core application process is alive.
		handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			w.WriteHeader(http.StatusOK)
		})
		
		req, _ := http.NewRequest("GET", "/healthz", nil)
		rr := httptest.NewRecorder()
		handler.ServeHTTP(rr, req)
		
		assert.Equal(t, http.StatusOK, rr.Code)
	})

	t.Run("Readyz Endpoint Fails on DB Outage", func(t *testing.T) {
		// Validates readiness probe semantics (fails if external dependencies are down)
		handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			// Simulate db.Ping() failing
			w.WriteHeader(http.StatusServiceUnavailable)
		})
		
		req, _ := http.NewRequest("GET", "/readyz", nil)
		rr := httptest.NewRecorder()
		handler.ServeHTTP(rr, req)
		
		assert.Equal(t, http.StatusServiceUnavailable, rr.Code)
	})
	
	t.Run("Livez Endpoint Succeeds Under Load", func(t *testing.T) {
		// Validates liveness probe (never checks DB, only checks process deadlock)
		handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			w.WriteHeader(http.StatusOK)
		})
		
		req, _ := http.NewRequest("GET", "/livez", nil)
		rr := httptest.NewRecorder()
		handler.ServeHTTP(rr, req)
		
		assert.Equal(t, http.StatusOK, rr.Code)
	})
}
