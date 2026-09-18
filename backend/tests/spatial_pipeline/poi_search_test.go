package spatial_pipeline

import (
	"context"
	"math"
	"sort"
	"strings"
	"testing"

	"vastu/backend/internal/domain"
	"vastu/backend/internal/pkg/geo"
	"vastu/backend/internal/service"

	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

type mockSearchPOIRepo struct {
	pois []*domain.SpatialPOI
}

func (m *mockSearchPOIRepo) Create(ctx context.Context, poi *domain.SpatialPOI) error {
	m.pois = append(m.pois, poi)
	return nil
}

func (m *mockSearchPOIRepo) GetByID(ctx context.Context, id uuid.UUID) (*domain.SpatialPOI, error) {
	for _, p := range m.pois {
		if p.ID == id {
			return p, nil
		}
	}
	return nil, domain.ErrPOINotFound
}

func (m *mockSearchPOIRepo) ListByProject(ctx context.Context, projectID uuid.UUID) ([]*domain.SpatialPOI, error) {
	var list []*domain.SpatialPOI
	for _, p := range m.pois {
		if p.ProjectID == projectID {
			list = append(list, p)
		}
	}
	return list, nil
}

func (m *mockSearchPOIRepo) Update(ctx context.Context, poi *domain.SpatialPOI) error {
	for idx, p := range m.pois {
		if p.ID == poi.ID {
			m.pois[idx] = poi
			return nil
		}
	}
	return domain.ErrPOINotFound
}

func (m *mockSearchPOIRepo) Delete(ctx context.Context, id uuid.UUID) error {
	for idx, p := range m.pois {
		if p.ID == id {
			m.pois = append(m.pois[:idx], m.pois[idx+1:]...)
			return nil
		}
	}
	return domain.ErrPOINotFound
}

func (m *mockSearchPOIRepo) Search(ctx context.Context, q domain.SpatialSearchQuery) ([]*domain.SearchResultItem, error) {
	var results []*domain.SearchResultItem
	for _, p := range m.pois {
		if p.ProjectID != q.ProjectID {
			continue
		}
		if q.Category != nil && p.Category != *q.Category {
			continue
		}

		// Text filter if query present
		if q.Query != "" {
			term := strings.ToLower(q.Query)
			matches := strings.Contains(strings.ToLower(p.Title), term) ||
				(p.Description != nil && strings.Contains(strings.ToLower(*p.Description), term))
			if !matches {
				continue
			}
		}

		var dist *float64
		if q.CenterPosX != nil && q.CenterPosY != nil && q.CenterPosZ != nil {
			dx := p.PosX - *q.CenterPosX
			dy := p.PosY - *q.CenterPosY
			dz := p.PosZ - *q.CenterPosZ
			d := math.Sqrt(dx*dx + dy*dy + dz*dz)
			if q.RadiusMeters != nil && d > *q.RadiusMeters {
				continue
			}
			dist = &d
		}

		item := &domain.SearchResultItem{
			ID:         p.ID,
			ResultType: "poi",
			Title:      p.Title,
			Category:   string(p.Category),
			Position:   map[string]float64{"x": p.PosX, "y": p.PosY, "z": p.PosZ},
			DistanceM:  dist,
			Score:      1.0,
		}
		if p.Description != nil {
			item.Description = *p.Description
		}
		results = append(results, item)
	}

	if q.CenterPosX != nil && q.CenterPosY != nil && q.CenterPosZ != nil {
		sort.Slice(results, func(i, j int) bool {
			if results[i].DistanceM != nil && results[j].DistanceM != nil {
				return *results[i].DistanceM < *results[j].DistanceM
			}
			return false
		})
	}

	return results, nil
}

func (m *mockSearchPOIRepo) POIsWithinRadius(ctx context.Context, projectID uuid.UUID, center geo.Point3D, radiusM float64) ([]*domain.SearchResultItem, error) {
	var results []*domain.SearchResultItem
	for _, p := range m.pois {
		if p.ProjectID != projectID {
			continue
		}
		dx := p.PosX - center.X
		dy := p.PosY - center.Y
		dz := p.PosZ - center.Z
		dist := math.Sqrt(dx*dx + dy*dy + dz*dz)
		if dist <= radiusM {
			distCopy := dist
			item := &domain.SearchResultItem{
				ID:         p.ID,
				ResultType: "poi",
				Title:      p.Title,
				Category:   string(p.Category),
				Position:   map[string]float64{"x": p.PosX, "y": p.PosY, "z": p.PosZ},
				DistanceM:  &distCopy,
				Score:      10.0 - dist*0.5,
			}
			results = append(results, item)
		}
	}
	return results, nil
}

type mockNavRepoForSearch struct {
	nodes []*domain.NavNode
}

func (n *mockNavRepoForSearch) CreateNode(ctx context.Context, node *domain.NavNode) error { return nil }
func (n *mockNavRepoForSearch) GetNodeByID(ctx context.Context, id uuid.UUID) (*domain.NavNode, error) {
	return nil, nil
}
func (n *mockNavRepoForSearch) ListNodesByProject(ctx context.Context, projectID uuid.UUID) ([]*domain.NavNode, error) {
	return nil, nil
}
func (n *mockNavRepoForSearch) CreateEdge(ctx context.Context, edge *domain.NavEdge) error { return nil }
func (n *mockNavRepoForSearch) ListEdgesByProject(ctx context.Context, projectID uuid.UUID) ([]*domain.NavEdge, error) {
	return nil, nil
}
func (n *mockNavRepoForSearch) DeleteNode(ctx context.Context, id uuid.UUID) error { return nil }
func (n *mockNavRepoForSearch) DeleteEdge(ctx context.Context, fromID, toID uuid.UUID) error { return nil }
func (n *mockNavRepoForSearch) NearestNode(ctx context.Context, projectID uuid.UUID, pos geo.Point3D, wheelchairOnly bool) (*domain.NavNode, error) {
	var best *domain.NavNode
	bestDist := float64(1e9)
	for _, node := range n.nodes {
		dx := node.PosX - pos.X
		dy := node.PosY - pos.Y
		dz := node.PosZ - pos.Z
		d := math.Sqrt(dx*dx + dy*dy + dz*dz)
		if d < bestDist {
			bestDist = d
			best = node
		}
	}
	return best, nil
}

func TestPOIAndSpatialSearch(t *testing.T) {
	ctx := context.Background()
	projectID := uuid.New()

	poiRepo := &mockSearchPOIRepo{}
	navNode1ID := uuid.New()
	navNode2ID := uuid.New()
	navRepo := &mockNavRepoForSearch{
		nodes: []*domain.NavNode{
			{ID: navNode1ID, ProjectID: projectID, PosX: 5.0, PosY: 5.0, PosZ: 1.0},
			{ID: navNode2ID, ProjectID: projectID, PosX: 20.0, PosY: 20.0, PosZ: 1.0},
		},
	}

	searchSvc := service.NewSearchService(poiRepo, nil)
	searchSvc.SetNavRepo(navRepo)

	// Populate test POIs
	desc1 := "Executive boardroom on 2nd floor"
	desc2 := "Type ABC powder extinguisher near stairs"
	desc3 := "Male and female accessible restrooms"
	poi1 := &domain.SpatialPOI{ID: uuid.New(), ProjectID: projectID, Title: "Conference Room Alpha", Description: &desc1, Category: domain.POICategoryRoomLabel, PosX: 5.2, PosY: 5.1, PosZ: 1.0}
	poi2 := &domain.SpatialPOI{ID: uuid.New(), ProjectID: projectID, Title: "Fire Extinguisher FE-01", Description: &desc2, Category: domain.POICategoryEmergencyExit, PosX: 6.0, PosY: 4.8, PosZ: 1.2}
	poi3 := &domain.SpatialPOI{ID: uuid.New(), ProjectID: projectID, Title: "Restroom Suite", Description: &desc3, Category: domain.POICategoryRestroom, PosX: 20.5, PosY: 19.8, PosZ: 1.0}

	_ = poiRepo.Create(ctx, poi1)
	_ = poiRepo.Create(ctx, poi2)
	_ = poiRepo.Create(ctx, poi3)

	// -------------------------------------------------------------------------
	// Scenario 1: Search by exact name
	// -------------------------------------------------------------------------
	t.Run("Scenario 1: Search by exact name", func(t *testing.T) {
		res, err := searchSvc.SearchSpatial(ctx, domain.SpatialSearchQuery{
			ProjectID: projectID,
			Query:     "Conference Room Alpha",
		})
		require.NoError(t, err)
		require.Len(t, res, 1)
		assert.Equal(t, "Conference Room Alpha", res[0].Title)
	})

	// -------------------------------------------------------------------------
	// Scenario 2: Search by category
	// -------------------------------------------------------------------------
	t.Run("Scenario 2: Search by category", func(t *testing.T) {
		cat := domain.POICategoryEmergencyExit
		res, err := searchSvc.SearchSpatial(ctx, domain.SpatialSearchQuery{
			ProjectID: projectID,
			Category:  &cat,
		})
		require.NoError(t, err)
		require.Len(t, res, 1)
		assert.Equal(t, "Fire Extinguisher FE-01", res[0].Title)
	})

	// -------------------------------------------------------------------------
	// Scenario 3: Partial / fuzzy text search
	// -------------------------------------------------------------------------
	t.Run("Scenario 3: Partial text query finds matches", func(t *testing.T) {
		res, err := searchSvc.SearchSpatial(ctx, domain.SpatialSearchQuery{
			ProjectID: projectID,
			Query:     "extinguish",
		})
		require.NoError(t, err)
		require.Len(t, res, 1)
		assert.Equal(t, "Fire Extinguisher FE-01", res[0].Title)
	})

	// -------------------------------------------------------------------------
	// Scenario 4: 3D Coordinate Radius Query
	// -------------------------------------------------------------------------
	t.Run("Scenario 4: 3D coordinate radius query finds POIs within sphere", func(t *testing.T) {
		cx, cy, cz := 5.0, 5.0, 1.0
		rad := 3.0 // 3m radius
		res, err := searchSvc.SearchSpatial(ctx, domain.SpatialSearchQuery{
			ProjectID:    projectID,
			CenterPosX:   &cx,
			CenterPosY:   &cy,
			CenterPosZ:   &cz,
			RadiusMeters: &rad,
		})
		require.NoError(t, err)
		require.Len(t, res, 2)
		for _, item := range res {
			assert.LessOrEqual(t, *item.DistanceM, 3.0)
		}
	})

	// -------------------------------------------------------------------------
	// Scenario 5: Coordinates outside radius excluded
	// -------------------------------------------------------------------------
	t.Run("Scenario 5: Points outside search radius strictly excluded", func(t *testing.T) {
		cx, cy, cz := 5.0, 5.0, 1.0
		rad := 0.5 // only 50cm radius
		res, err := searchSvc.SearchSpatial(ctx, domain.SpatialSearchQuery{
			ProjectID:    projectID,
			CenterPosX:   &cx,
			CenterPosY:   &cy,
			CenterPosZ:   &cz,
			RadiusMeters: &rad,
		})
		require.NoError(t, err)
		require.Len(t, res, 1)
		assert.Equal(t, "Conference Room Alpha", res[0].Title)
	})

	// -------------------------------------------------------------------------
	// Scenario 6: Multiple matching POIs sorted by relevance and distance
	// -------------------------------------------------------------------------
	t.Run("Scenario 6: Results sorted by distance and score", func(t *testing.T) {
		cx, cy, cz := 5.0, 5.0, 1.0
		rad := 25.0
		res, err := searchSvc.SearchSpatial(ctx, domain.SpatialSearchQuery{
			ProjectID:    projectID,
			CenterPosX:   &cx,
			CenterPosY:   &cy,
			CenterPosZ:   &cz,
			RadiusMeters: &rad,
		})
		require.NoError(t, err)
		require.Len(t, res, 3)
		assert.LessOrEqual(t, *res[0].DistanceM, *res[1].DistanceM)
	})

	// -------------------------------------------------------------------------
	// Scenario 7: Nearest Navigation Node Attached
	// -------------------------------------------------------------------------
	t.Run("Scenario 7: Nearest indoor navigation node ID attached for wayfinding", func(t *testing.T) {
		res, err := searchSvc.SearchSpatial(ctx, domain.SpatialSearchQuery{
			ProjectID: projectID,
			Query:     "Restroom Suite",
		})
		require.NoError(t, err)
		require.Len(t, res, 1)
		require.NotNil(t, res[0].NearestNavNodeID)
		assert.Equal(t, navNode2ID, *res[0].NearestNavNodeID, "Should resolve to nearest nav node 2 at (20, 20)")
	})

	// -------------------------------------------------------------------------
	// Scenario 8: Combined multi-modal spatial + text search
	// -------------------------------------------------------------------------
	t.Run("Scenario 8: Multi-modal combined query with text and spatial radius", func(t *testing.T) {
		cx, cy, cz := 5.0, 5.0, 1.0
		rad := 10.0
		res, err := searchSvc.SearchSpatial(ctx, domain.SpatialSearchQuery{
			ProjectID:    projectID,
			Query:        "Room",
			CenterPosX:   &cx,
			CenterPosY:   &cy,
			CenterPosZ:   &cz,
			RadiusMeters: &rad,
		})
		require.NoError(t, err)
		require.Len(t, res, 1)
		assert.Equal(t, "Conference Room Alpha", res[0].Title)
	})
}
