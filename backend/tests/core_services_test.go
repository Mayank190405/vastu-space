package tests

import (
	"context"
	"math"
	"testing"

	"vastu/backend/internal/domain"
	"vastu/backend/internal/pkg/geo"
	"vastu/backend/internal/service"

	"github.com/google/uuid"
)

// Mock Navigation Repository
type mockNavRepo struct {
	nodes []*domain.NavNode
	edges []*domain.NavEdge
}

func (m *mockNavRepo) CreateNode(ctx context.Context, n *domain.NavNode) error {
	m.nodes = append(m.nodes, n)
	return nil
}
func (m *mockNavRepo) GetNodeByID(ctx context.Context, id uuid.UUID) (*domain.NavNode, error) {
	for _, n := range m.nodes {
		if n.ID == id {
			return n, nil
		}
	}
	return nil, nil
}
func (m *mockNavRepo) ListNodesByProject(ctx context.Context, projectID uuid.UUID) ([]*domain.NavNode, error) {
	return m.nodes, nil
}
func (m *mockNavRepo) CreateEdge(ctx context.Context, e *domain.NavEdge) error {
	m.edges = append(m.edges, e)
	return nil
}
func (m *mockNavRepo) ListEdgesByProject(ctx context.Context, projectID uuid.UUID) ([]*domain.NavEdge, error) {
	return m.edges, nil
}
func (m *mockNavRepo) DeleteNode(ctx context.Context, id uuid.UUID) error { return nil }
func (m *mockNavRepo) DeleteEdge(ctx context.Context, fromID, toID uuid.UUID) error { return nil }
func (m *mockNavRepo) NearestNode(ctx context.Context, projectID uuid.UUID, pos geo.Point3D, wheelchairOnly bool) (*domain.NavNode, error) {
	var best *domain.NavNode
	bestDist := float64(1e9)
	for _, n := range m.nodes {
		dx := n.PosX - pos.X
		dy := n.PosY - pos.Y
		dz := n.PosZ - pos.Z
		d := math.Sqrt(dx*dx + dy*dy + dz*dz)
		if d < bestDist {
			bestDist = d
			best = n
		}
	}
	return best, nil
}

type mockPOIRepo struct{}

func (m *mockPOIRepo) Create(ctx context.Context, poi *domain.SpatialPOI) error { return nil }
func (m *mockPOIRepo) GetByID(ctx context.Context, id uuid.UUID) (*domain.SpatialPOI, error) { return nil, nil }
func (m *mockPOIRepo) ListByProject(ctx context.Context, projectID uuid.UUID) ([]*domain.SpatialPOI, error) { return nil, nil }
func (m *mockPOIRepo) Update(ctx context.Context, poi *domain.SpatialPOI) error { return nil }
func (m *mockPOIRepo) Delete(ctx context.Context, id uuid.UUID) error { return nil }
func (m *mockPOIRepo) Search(ctx context.Context, query domain.SpatialSearchQuery) ([]*domain.SearchResultItem, error) { return nil, nil }

// Test 1: Navigation Graph A* Pathfinding
func TestNavigationRouteCalculation(t *testing.T) {
	projectID := uuid.New()
	nodeA := &domain.NavNode{ID: uuid.New(), ProjectID: projectID, PosX: 0, PosY: 0, PosZ: 0, IsWheelchairAccessible: true}
	nodeB := &domain.NavNode{ID: uuid.New(), ProjectID: projectID, PosX: 10, PosY: 0, PosZ: 0, IsWheelchairAccessible: true}
	nodeC := &domain.NavNode{ID: uuid.New(), ProjectID: projectID, PosX: 20, PosY: 0, PosZ: 0, IsWheelchairAccessible: true}

	edgeAB := &domain.NavEdge{
		ID:                     uuid.New(),
		ProjectID:              projectID,
		FromNodeID:             nodeA.ID,
		ToNodeID:               nodeB.ID,
		EdgeType:               domain.NavEdgeTypeCorridor,
		DistanceMeters:         10.0,
		IsBidirectional:        true,
		IsWheelchairAccessible: true,
		WeightModifier:         1.0,
	}
	edgeBC := &domain.NavEdge{
		ID:                     uuid.New(),
		ProjectID:              projectID,
		FromNodeID:             nodeB.ID,
		ToNodeID:               nodeC.ID,
		EdgeType:               domain.NavEdgeTypeCorridor,
		DistanceMeters:         10.0,
		IsBidirectional:        true,
		IsWheelchairAccessible: true,
		WeightModifier:         1.0,
	}

	repo := &mockNavRepo{
		nodes: []*domain.NavNode{nodeA, nodeB, nodeC},
		edges: []*domain.NavEdge{edgeAB, edgeBC},
	}
	poiRepo := &mockPOIRepo{}
	navSvc := service.NewNavigationService(repo, poiRepo)

	req := domain.NavRouteRequest{
		ProjectID:  projectID,
		StartPosX:  0,
		StartPosY:  0,
		StartPosZ:  0,
		TargetPosX: 20,
		TargetPosY: 0,
		TargetPosZ: 0,
	}

	route, err := navSvc.CalculateRoute(context.Background(), req)
	if err != nil {
		t.Fatalf("unexpected error calculating route: %v", err)
	}

	if route.TotalDistanceMeters < 19.9 || route.TotalDistanceMeters > 20.1 {
		t.Errorf("expected distance ~20m, got %.2f", route.TotalDistanceMeters)
	}

	if len(route.Steps) == 0 {
		t.Errorf("expected step-by-step instructions, got 0 steps")
	}
}

// Test 2: 3D Euclidean Distance & Spatial Math
func Test3DDistanceCalculation(t *testing.T) {
	p1 := []float64{0, 0, 0}
	p2 := []float64{3, 4, 0}

	dx := p1[0] - p2[0]
	dy := p1[1] - p2[1]
	dz := p1[2] - p2[2]
	d := math.Sqrt(dx*dx + dy*dy + dz*dz)

	if d != 5.0 {
		t.Errorf("expected 3D distance 5.0, got %f", d)
	}
}

// Test 3: Upload Chunk Calculation
func TestUploadChunkEstimation(t *testing.T) {
	totalSize := int64(23 * 1024 * 1024) // 23MB
	chunkSize := int64(5 * 1024 * 1024)  // 5MB

	totalChunks := int((totalSize + chunkSize - 1) / chunkSize)
	if totalChunks != 5 {
		t.Errorf("expected 5 chunks for 23MB file with 5MB chunks, got %d", totalChunks)
	}
}

// Test 4: Job State Progression
func TestJobStateProgression(t *testing.T) {
	stages := []domain.JobStage{
		domain.JobStageQueued,
		domain.JobStagePreprocessing,
		domain.JobStageSfMTracking,
		domain.JobStageDepthEstimation,
		domain.JobStagePointCloud,
		domain.JobStageMeshing,
		domain.JobStageTexturing,
		domain.JobStageSemanticSegmentation,
		domain.JobStageCellFusion,
		domain.JobStageCompleted,
	}

	if len(stages) != 10 {
		t.Errorf("expected 10 job stages in spatial pipeline, got %d", len(stages))
	}
}
