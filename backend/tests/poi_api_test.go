package tests

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"vastu/backend/internal/domain"
	"vastu/backend/internal/handler"
	"vastu/backend/internal/middleware"
	"vastu/backend/internal/pkg/geo"
	"vastu/backend/internal/service"

	"github.com/go-chi/chi/v5"
	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

type mockPOIRepoDetailed struct {
	pois map[uuid.UUID]*domain.SpatialPOI
}

func newMockPOIRepoDetailed() *mockPOIRepoDetailed {
	return &mockPOIRepoDetailed{pois: make(map[uuid.UUID]*domain.SpatialPOI)}
}

func (m *mockPOIRepoDetailed) Create(ctx context.Context, poi *domain.SpatialPOI) error {
	m.pois[poi.ID] = poi
	return nil
}

func (m *mockPOIRepoDetailed) GetByID(ctx context.Context, id uuid.UUID) (*domain.SpatialPOI, error) {
	p, ok := m.pois[id]
	if !ok {
		return nil, domain.ErrPOINotFound
	}
	return p, nil
}

func (m *mockPOIRepoDetailed) ListByProject(ctx context.Context, projectID uuid.UUID) ([]*domain.SpatialPOI, error) {
	var list []*domain.SpatialPOI
	for _, p := range m.pois {
		if p.ProjectID == projectID {
			list = append(list, p)
		}
	}
	return list, nil
}

func (m *mockPOIRepoDetailed) Update(ctx context.Context, poi *domain.SpatialPOI) error {
	m.pois[poi.ID] = poi
	return nil
}

func (m *mockPOIRepoDetailed) Delete(ctx context.Context, id uuid.UUID) error {
	delete(m.pois, id)
	return nil
}

func (m *mockPOIRepoDetailed) Search(ctx context.Context, query domain.SpatialSearchQuery) ([]*domain.SearchResultItem, error) {
	var results []*domain.SearchResultItem
	for _, p := range m.pois {
		desc := ""
		if p.Description != nil {
			desc = *p.Description
		}
		results = append(results, &domain.SearchResultItem{
			ID:          p.ID,
			ResultType:  "poi",
			Title:       p.Title,
			Description: desc,
			Category:    string(p.Category),
			Position:    map[string]float64{"x": p.PosX, "y": p.PosY, "z": p.PosZ},
		})
	}
	return results, nil
}

func (m *mockPOIRepoDetailed) POIsWithinRadius(ctx context.Context, projectID uuid.UUID, center geo.Point3D, radiusM float64) ([]*domain.SearchResultItem, error) {
	var results []*domain.SearchResultItem
	for _, p := range m.pois {
		if p.ProjectID == projectID {
			dx := p.PosX - center.X
			dy := p.PosY - center.Y
			dz := p.PosZ - center.Z
			distSq := dx*dx + dy*dy + dz*dz
			if distSq <= radiusM*radiusM {
				desc := ""
				if p.Description != nil {
					desc = *p.Description
				}
				results = append(results, &domain.SearchResultItem{
					ID:          p.ID,
					ResultType:  "poi",
					Title:       p.Title,
					Description: desc,
					Category:    string(p.Category),
					Position:    map[string]float64{"x": p.PosX, "y": p.PosY, "z": p.PosZ},
				})
			}
		}
	}
	return results, nil
}

func setupPOIRouter() (*chi.Mux, *mockPOIRepoDetailed, uuid.UUID) {
	poiRepo := newMockPOIRepoDetailed()
	poiSvc := service.NewPOIService(poiRepo, nil)
	poiHdl := handler.NewPOIHandler(poiSvc)

	userID := uuid.New()
	r := chi.NewRouter()

	authMiddleware := func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, req *http.Request) {
			if req.Header.Get("Authorization") == "Bearer valid-token" {
				ctx := middleware.SetClaimsContext(req.Context(), &domain.TokenClaims{
					UserID:     userID,
					MemberRole: domain.RoleOrgAdmin,
				})
				next.ServeHTTP(w, req.WithContext(ctx))
			} else {
				next.ServeHTTP(w, req)
			}
		})
	}

	r.Use(authMiddleware)

	r.Post("/api/v1/pois", poiHdl.Create)
	r.Get("/api/v1/pois/{id}", poiHdl.Get)
	r.Get("/api/v1/projects/{projectId}/pois", poiHdl.ListByProject)
	r.Put("/api/v1/pois/{id}", poiHdl.Update)
	r.Delete("/api/v1/pois/{id}", poiHdl.Delete)

	return r, poiRepo, userID
}

func TestPOIAPI(t *testing.T) {
	router, poiRepo, _ := setupPOIRouter()
	projectID := uuid.New()

	var createdPOIID uuid.UUID

	t.Run("POST /api/v1/pois - Unauthorized without token", func(t *testing.T) {
		input := domain.CreatePOIInput{
			ProjectID: projectID,
			Title:     "Main Altar",
			PosX:      1.5,
			PosY:      0.0,
			PosZ:      3.2,
		}
		data, _ := json.Marshal(input)
		req := httptest.NewRequest(http.MethodPost, "/api/v1/pois", bytes.NewReader(data))
		req.Header.Set("Content-Type", "application/json")
		rr := httptest.NewRecorder()

		router.ServeHTTP(rr, req)
		assert.Equal(t, http.StatusUnauthorized, rr.Code)
	})

	t.Run("POST /api/v1/pois - Create POI with 3D coordinates", func(t *testing.T) {
		input := domain.CreatePOIInput{
			ProjectID: projectID,
			Title:     "Main Altar",
			Category:  domain.POICategoryStructural,
			PosX:      1.5,
			PosY:      0.0,
			PosZ:      3.2,
		}
		data, _ := json.Marshal(input)
		req := httptest.NewRequest(http.MethodPost, "/api/v1/pois", bytes.NewReader(data))
		req.Header.Set("Content-Type", "application/json")
		req.Header.Set("Authorization", "Bearer valid-token")
		rr := httptest.NewRecorder()

		router.ServeHTTP(rr, req)
		assert.Equal(t, http.StatusCreated, rr.Code)

		var resp map[string]interface{}
		json.Unmarshal(rr.Body.Bytes(), &resp)
		dataMap := resp["data"].(map[string]interface{})
		parsedID, err := uuid.Parse(dataMap["id"].(string))
		require.NoError(t, err)
		createdPOIID = parsedID

		assert.Equal(t, "Main Altar", dataMap["title"])
		assert.Equal(t, 1.5, dataMap["pos_x"])
		assert.Equal(t, 3.2, dataMap["pos_z"])
	})

	t.Run("GET /api/v1/pois/{id} - Retrieve POI by ID", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodGet, "/api/v1/pois/"+createdPOIID.String(), nil)
		rr := httptest.NewRecorder()

		router.ServeHTTP(rr, req)
		assert.Equal(t, http.StatusOK, rr.Code)

		var resp map[string]interface{}
		json.Unmarshal(rr.Body.Bytes(), &resp)
		dataMap := resp["data"].(map[string]interface{})
		assert.Equal(t, createdPOIID.String(), dataMap["id"])
	})

	t.Run("GET /api/v1/projects/{projectId}/pois - List all POIs in Project", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodGet, "/api/v1/projects/"+projectID.String()+"/pois", nil)
		rr := httptest.NewRecorder()

		router.ServeHTTP(rr, req)
		assert.Equal(t, http.StatusOK, rr.Code)

		var resp map[string]interface{}
		json.Unmarshal(rr.Body.Bytes(), &resp)
		poisList := resp["data"].([]interface{})
		assert.Len(t, poisList, 1)
	})

	t.Run("PUT /api/v1/pois/{id} - Update POI attributes", func(t *testing.T) {
		newTitle := "Sanctum Altar (North Facing)"
		input := domain.UpdatePOIInput{
			Title: &newTitle,
		}
		data, _ := json.Marshal(input)
		req := httptest.NewRequest(http.MethodPut, "/api/v1/pois/"+createdPOIID.String(), bytes.NewReader(data))
		req.Header.Set("Content-Type", "application/json")
		rr := httptest.NewRecorder()

		router.ServeHTTP(rr, req)
		assert.Equal(t, http.StatusOK, rr.Code)

		poi, _ := poiRepo.GetByID(context.Background(), createdPOIID)
		assert.Equal(t, newTitle, poi.Title)
	})

	t.Run("DELETE /api/v1/pois/{id} - Delete POI", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodDelete, "/api/v1/pois/"+createdPOIID.String(), nil)
		rr := httptest.NewRecorder()

		router.ServeHTTP(rr, req)
		assert.Equal(t, http.StatusOK, rr.Code)

		_, err := poiRepo.GetByID(context.Background(), createdPOIID)
		assert.Error(t, err)
	})

	t.Run("Spatial Radius Query Test", func(t *testing.T) {
		// Populate two POIs at known distances
		p1 := &domain.SpatialPOI{
			ID:        uuid.New(),
			ProjectID: projectID,
			Title:     "Nearby Column",
			PosX:      2.0,
			PosY:      0.0,
			PosZ:      2.0,
		}
		p2 := &domain.SpatialPOI{
			ID:        uuid.New(),
			ProjectID: projectID,
			Title:     "Far Gate",
			PosX:      50.0,
			PosY:      0.0,
			PosZ:      50.0,
		}
		_ = poiRepo.Create(context.Background(), p1)
		_ = poiRepo.Create(context.Background(), p2)

		// Search within 5m radius of (0,0,0)
		results, err := poiRepo.POIsWithinRadius(context.Background(), projectID, geo.Point3D{X: 0, Y: 0, Z: 0}, 5.0)
		require.NoError(t, err)
		assert.Len(t, results, 1)
		assert.Equal(t, "Nearby Column", results[0].Title)
	})
}
