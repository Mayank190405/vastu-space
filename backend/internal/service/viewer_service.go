package service

import (
	"context"
	"errors"
	"math"

	"vastu/backend/internal/domain"
	"vastu/backend/internal/repository"

	"github.com/google/uuid"
)

type ViewerService struct {
	viewerRepo  repository.ViewerRepository
	projectRepo repository.ProjectRepository
}

func NewViewerService(viewerRepo repository.ViewerRepository, projectRepo repository.ProjectRepository) *ViewerService {
	return &ViewerService{
		viewerRepo:  viewerRepo,
		projectRepo: projectRepo,
	}
}

func (s *ViewerService) CreateBookmark(ctx context.Context, userID uuid.UUID, input domain.CreateBookmarkInput) (*domain.ViewerBookmark, error) {
	if input.ProjectID == uuid.Nil {
		return nil, errors.New("project_id is required")
	}
	if input.Title == "" {
		return nil, errors.New("title is required")
	}

	fov := 60.0
	if input.CameraFOV != nil && *input.CameraFOV > 10 && *input.CameraFOV < 150 {
		fov = *input.CameraFOV
	}

	layers := input.VisibleLayers
	if len(layers) == 0 {
		layers = []string{"mesh", "pois", "annotations"}
	}

	isShared := false
	if input.IsShared != nil {
		isShared = *input.IsShared
	}

	bookmark := &domain.ViewerBookmark{
		ID:             uuid.New(),
		ProjectID:      input.ProjectID,
		UserID:         &userID,
		Title:          input.Title,
		CameraPosition: input.CameraPosition,
		CameraTarget:   input.CameraTarget,
		CameraFOV:      fov,
		VisibleLayers:  layers,
		IsShared:       isShared,
	}

	if err := s.viewerRepo.CreateBookmark(ctx, bookmark); err != nil {
		return nil, err
	}

	return bookmark, nil
}

func (s *ViewerService) ListBookmarks(ctx context.Context, projectID uuid.UUID) ([]*domain.ViewerBookmark, error) {
	return s.viewerRepo.ListBookmarksByProject(ctx, projectID)
}

func (s *ViewerService) DeleteBookmark(ctx context.Context, id uuid.UUID) error {
	return s.viewerRepo.DeleteBookmark(ctx, id)
}

func (s *ViewerService) CreateAnnotation(ctx context.Context, userID uuid.UUID, input domain.CreateAnnotationInput) (*domain.ViewerAnnotation, error) {
	if input.ProjectID == uuid.Nil {
		return nil, errors.New("project_id is required")
	}

	unit := "meters"
	if input.Unit != nil && *input.Unit != "" {
		unit = *input.Unit
	}

	colorHex := "#dfb873"
	if input.ColorHex != nil && *input.ColorHex != "" {
		colorHex = *input.ColorHex
	}

	calcVal := input.CalculatedValue
	if calcVal == nil && len(input.Points3D) >= 2 {
		if input.AnnotationType == "distance" {
			p1 := input.Points3D[0]
			p2 := input.Points3D[1]
			dx := p1[0] - p2[0]
			dy := p1[1] - p2[1]
			dz := p1[2] - p2[2]
			d := math.Sqrt(dx*dx + dy*dy + dz*dz)
			calcVal = &d
		}
	}

	annotation := &domain.ViewerAnnotation{
		ID:              uuid.New(),
		ProjectID:       input.ProjectID,
		UserID:          &userID,
		AnnotationType:  input.AnnotationType,
		Points3D:        input.Points3D,
		CalculatedValue: calcVal,
		Unit:            unit,
		Label:           input.Label,
		ColorHex:        colorHex,
	}

	if err := s.viewerRepo.CreateAnnotation(ctx, annotation); err != nil {
		return nil, err
	}

	return annotation, nil
}

func (s *ViewerService) ListAnnotations(ctx context.Context, projectID uuid.UUID) ([]*domain.ViewerAnnotation, error) {
	return s.viewerRepo.ListAnnotationsByProject(ctx, projectID)
}

func (s *ViewerService) DeleteAnnotation(ctx context.Context, id uuid.UUID) error {
	return s.viewerRepo.DeleteAnnotation(ctx, id)
}
