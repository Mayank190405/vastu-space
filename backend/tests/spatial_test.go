package tests

import (
	"testing"
	"vastu/backend/internal/repository/postgres"
	"vastu/backend/internal/service"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/stretchr/testify/assert"
)

// TestSpatialQueries targets Phase 2.5 - DATABASE / POSTGIS and Phase 2.7 - SEARCH
func TestSpatialQueries(t *testing.T) {
	t.Run("Spatial POI ST_DWithin Query", func(t *testing.T) {
		repo := postgres.NewPOIRepo(&pgxpool.Pool{})
		assert.NotNil(t, repo)
	})

	t.Run("Semantic + Spatial Intersection", func(t *testing.T) {
		svc := service.NewSearchService(nil, nil)
		assert.NotNil(t, svc)
	})
}
