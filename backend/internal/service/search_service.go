package service

import (
	"context"
	"errors"

	"vastu/backend/internal/domain"
	"vastu/backend/internal/pkg/geo"
	"vastu/backend/internal/repository"

	"github.com/google/uuid"
)

type SearchService struct {
	poiRepo     repository.POIRepository
	projectRepo repository.ProjectRepository
	navRepo     repository.NavigationRepository
}

func NewSearchService(poiRepo repository.POIRepository, projectRepo repository.ProjectRepository) *SearchService {
	return &SearchService{
		poiRepo:     poiRepo,
		projectRepo: projectRepo,
	}
}

func (s *SearchService) SetNavRepo(navRepo repository.NavigationRepository) {
	s.navRepo = navRepo
}

func (s *SearchService) SearchSpatial(ctx context.Context, q domain.SpatialSearchQuery) ([]*domain.SearchResultItem, error) {
	if q.ProjectID == uuid.Nil {
		return nil, errors.New("project_id is required")
	}

	results, err := s.poiRepo.Search(ctx, q)
	if err != nil {
		return nil, err
	}

	if s.navRepo != nil {
		for _, item := range results {
			if item.Position != nil {
				x := item.Position["x"]
				y := item.Position["y"]
				z := item.Position["z"]
				node, err := s.navRepo.NearestNode(ctx, q.ProjectID, geo.Point3D{X: x, Y: y, Z: z}, false)
				if err == nil && node != nil {
					item.NearestNavNodeID = &node.ID
				}
			}
		}
	}

	return results, nil
}
