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
	"vastu/backend/internal/pkg/geo"
	"vastu/backend/internal/service"

	"github.com/go-chi/chi/v5"
	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
)

type mockNavRepoDetailed struct {
	nodes map[uuid.UUID]*domain.NavNode
	edges []*domain.NavEdge
}

func newMockNavRepoDetailed() *mockNavRepoDetailed {
	return &mockNavRepoDetailed{
		nodes: make(map[uuid.UUID]*domain.NavNode),
		edges: []*domain.NavEdge{},
	}
}

func (m *mockNavRepoDetailed) CreateNode(ctx context.Context, n *domain.NavNode) error {
	m.nodes[n.ID] = n
	return nil
}

func (m *mockNavRepoDetailed) GetNodeByID(ctx context.Context, id uuid.UUID) (*domain.NavNode, error) {
	n, ok := m.nodes[id]
	if !ok {
		return nil, nil
	}
	return n, nil
}

func (m *mockNavRepoDetailed) ListNodesByProject(ctx context.Context, projectID uuid.UUID) ([]*domain.NavNode, error) {
	var list []*domain.NavNode
	for _, n := range m.nodes {
		if n.ProjectID == projectID {
			list = append(list, n)
		}
	}
	return list, nil
}

func (m *mockNavRepoDetailed) CreateEdge(ctx context.Context, e *domain.NavEdge) error {
	m.edges = append(m.edges, e)
	return nil
}

func (m *mockNavRepoDetailed) ListEdgesByProject(ctx context.Context, projectID uuid.UUID) ([]*domain.NavEdge, error) {
	var list []*domain.NavEdge
	for _, e := range m.edges {
		if e.ProjectID == projectID {
			list = append(list, e)
		}
	}
	return list, nil
}

func (m *mockNavRepoDetailed) DeleteNode(ctx context.Context, id uuid.UUID) error {
	delete(m.nodes, id)
	return nil
}

func (m *mockNavRepoDetailed) DeleteEdge(ctx context.Context, fromID, toID uuid.UUID) error {
	return nil
}

func (m *mockNavRepoDetailed) NearestNode(ctx context.Context, projectID uuid.UUID, pos geo.Point3D, wheelchairOnly bool) (*domain.NavNode, error) {
	var nearest *domain.NavNode
	minDist := 1e9
	for _, n := range m.nodes {
		if n.ProjectID != projectID {
			continue
		}
		if wheelchairOnly && !n.IsWheelchairAccessible {
			continue
		}
		dx := n.PosX - pos.X
		dy := n.PosY - pos.Y
		dz := n.PosZ - pos.Z
		dist := dx*dx + dy*dy + dz*dz
		if dist < minDist {
			minDist = dist
			nearest = n
		}
	}
	return nearest, nil
}

func setupNavRouter() (*chi.Mux, *mockNavRepoDetailed) {
	navRepo := newMockNavRepoDetailed()
	navSvc := service.NewNavigationService(navRepo, nil)
	navHdl := handler.NewNavigationHandler(navSvc)

	r := chi.NewRouter()
	r.Post("/api/v1/navigation/nodes", navHdl.CreateNode)
	r.Get("/api/v1/projects/{projectId}/navigation/nodes", navHdl.ListNodes)
	r.Post("/api/v1/navigation/edges", navHdl.CreateEdge)
	r.Get("/api/v1/projects/{projectId}/navigation/edges", navHdl.ListEdges)
	r.Post("/api/v1/navigation/route", navHdl.CalculateRoute)

	return r, navRepo
}

func TestNavigationAPI(t *testing.T) {
	router, _ := setupNavRouter()
	projectID := uuid.New()

	nodeA_ID := uuid.New()
	nodeB_ID := uuid.New()
	nodeC_ID := uuid.New()

	t.Run("POST /api/v1/navigation/nodes - Create Nodes", func(t *testing.T) {
		nodes := []domain.NavNode{
			{ID: nodeA_ID, ProjectID: projectID, PosX: 0, PosY: 0, PosZ: 0, IsWheelchairAccessible: true},
			{ID: nodeB_ID, ProjectID: projectID, PosX: 5, PosY: 0, PosZ: 0, IsWheelchairAccessible: true},
			{ID: nodeC_ID, ProjectID: projectID, PosX: 10, PosY: 0, PosZ: 0, IsWheelchairAccessible: true},
		}

		for _, n := range nodes {
			data, _ := json.Marshal(n)
			req := httptest.NewRequest(http.MethodPost, "/api/v1/navigation/nodes", bytes.NewReader(data))
			req.Header.Set("Content-Type", "application/json")
			rr := httptest.NewRecorder()

			router.ServeHTTP(rr, req)
			assert.Equal(t, http.StatusCreated, rr.Code)
		}
	})

	t.Run("GET /api/v1/projects/{projectId}/navigation/nodes - List Nodes", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodGet, "/api/v1/projects/"+projectID.String()+"/navigation/nodes", nil)
		rr := httptest.NewRecorder()

		router.ServeHTTP(rr, req)
		assert.Equal(t, http.StatusOK, rr.Code)

		var resp map[string]interface{}
		json.Unmarshal(rr.Body.Bytes(), &resp)
		nodesList := resp["data"].([]interface{})
		assert.Len(t, nodesList, 3)
	})

	t.Run("POST /api/v1/navigation/edges - Create Connected Edges", func(t *testing.T) {
		edges := []domain.NavEdge{
			{
				ID:                     uuid.New(),
				ProjectID:              projectID,
				FromNodeID:             nodeA_ID,
				ToNodeID:               nodeB_ID,
				DistanceMeters:         5.0,
				IsBidirectional:        true,
				IsWheelchairAccessible: true,
			},
			{
				ID:                     uuid.New(),
				ProjectID:              projectID,
				FromNodeID:             nodeB_ID,
				ToNodeID:               nodeC_ID,
				DistanceMeters:         5.0,
				IsBidirectional:        true,
				IsWheelchairAccessible: true,
			},
		}

		for _, e := range edges {
			data, _ := json.Marshal(e)
			req := httptest.NewRequest(http.MethodPost, "/api/v1/navigation/edges", bytes.NewReader(data))
			req.Header.Set("Content-Type", "application/json")
			rr := httptest.NewRecorder()

			router.ServeHTTP(rr, req)
			assert.Equal(t, http.StatusCreated, rr.Code)
		}
	})

	t.Run("GET /api/v1/projects/{projectId}/navigation/edges - List Edges", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodGet, "/api/v1/projects/"+projectID.String()+"/navigation/edges", nil)
		rr := httptest.NewRecorder()

		router.ServeHTTP(rr, req)
		assert.Equal(t, http.StatusOK, rr.Code)

		var resp map[string]interface{}
		json.Unmarshal(rr.Body.Bytes(), &resp)
		edgesList := resp["data"].([]interface{})
		assert.Len(t, edgesList, 2)
	})

	t.Run("POST /api/v1/navigation/route - Calculate A* Route from Node A to Node C", func(t *testing.T) {
		routeReq := domain.NavRouteRequest{
			ProjectID:         projectID,
			StartPosX:         0,
			StartPosY:         0,
			StartPosZ:         0,
			TargetPosX:        10,
			TargetPosY:        0,
			TargetPosZ:        0,
			RequireWheelchair: false,
		}
		data, _ := json.Marshal(routeReq)
		req := httptest.NewRequest(http.MethodPost, "/api/v1/navigation/route", bytes.NewReader(data))
		req.Header.Set("Content-Type", "application/json")
		rr := httptest.NewRecorder()

		router.ServeHTTP(rr, req)
		assert.Equal(t, http.StatusOK, rr.Code)

		var resp map[string]interface{}
		json.Unmarshal(rr.Body.Bytes(), &resp)
		routeData := resp["data"].(map[string]interface{})

		assert.Equal(t, 10.0, routeData["total_distance_meters"])
		waypoints := routeData["waypoints"].([]interface{})
		assert.NotEmpty(t, waypoints)
		steps := routeData["steps"].([]interface{})
		assert.NotEmpty(t, steps)
	})
}
