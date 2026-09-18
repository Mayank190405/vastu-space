package service

import (
	"context"
	"errors"

	"vastu/backend/internal/domain"
	"vastu/backend/internal/repository"

	"github.com/google/uuid"
)

type POIService struct {
	poiRepo     repository.POIRepository
	projectRepo repository.ProjectRepository
}

func NewPOIService(poiRepo repository.POIRepository, projectRepo repository.ProjectRepository) *POIService {
	return &POIService{
		poiRepo:     poiRepo,
		projectRepo: projectRepo,
	}
}

func (s *POIService) CreatePOI(ctx context.Context, userID uuid.UUID, input domain.CreatePOIInput) (*domain.SpatialPOI, error) {
	if input.ProjectID == uuid.Nil {
		return nil, errors.New("project_id is required")
	}
	if input.Title == "" {
		return nil, errors.New("title is required")
	}

	category := input.Category
	if category == "" {
		category = domain.POICategoryCustom
	}

	iconKey := "map-pin"
	if input.IconKey != nil && *input.IconKey != "" {
		iconKey = *input.IconKey
	}

	colorHex := "#dfb873"
	if input.ColorHex != nil && *input.ColorHex != "" {
		colorHex = *input.ColorHex
	}

	var nx, ny, nz float64 = 0.0, 1.0, 0.0
	if input.NormalX != nil {
		nx = *input.NormalX
	}
	if input.NormalY != nil {
		ny = *input.NormalY
	}
	if input.NormalZ != nil {
		nz = *input.NormalZ
	}

	poi := &domain.SpatialPOI{
		ID:              uuid.New(),
		ProjectID:       input.ProjectID,
		LevelID:         input.LevelID,
		SectionID:       input.SectionID,
		Title:           input.Title,
		Description:     input.Description,
		Category:        category,
		PosX:            input.PosX,
		PosY:            input.PosY,
		PosZ:            input.PosZ,
		NormalX:         nx,
		NormalY:         ny,
		NormalZ:         nz,
		IconKey:         iconKey,
		ColorHex:        colorHex,
		Tags:            input.Tags,
		CustomMetadata:  input.CustomMetadata,
		Attachments:     input.Attachments,
		CameraViewpoint: input.CameraViewpoint,
		CreatedBy:       &userID,
	}

	if err := s.poiRepo.Create(ctx, poi); err != nil {
		return nil, err
	}

	return poi, nil
}

func (s *POIService) GetPOI(ctx context.Context, id uuid.UUID) (*domain.SpatialPOI, error) {
	return s.poiRepo.GetByID(ctx, id)
}

func (s *POIService) ListPOIsByProject(ctx context.Context, projectID uuid.UUID) ([]*domain.SpatialPOI, error) {
	return s.poiRepo.ListByProject(ctx, projectID)
}

func (s *POIService) UpdatePOI(ctx context.Context, id uuid.UUID, input domain.UpdatePOIInput) (*domain.SpatialPOI, error) {
	poi, err := s.poiRepo.GetByID(ctx, id)
	if err != nil {
		return nil, err
	}

	if input.Title != nil {
		poi.Title = *input.Title
	}
	if input.Description != nil {
		poi.Description = input.Description
	}
	if input.Category != nil {
		poi.Category = *input.Category
	}
	if input.PosX != nil {
		poi.PosX = *input.PosX
	}
	if input.PosY != nil {
		poi.PosY = *input.PosY
	}
	if input.PosZ != nil {
		poi.PosZ = *input.PosZ
	}
	if input.IconKey != nil {
		poi.IconKey = *input.IconKey
	}
	if input.ColorHex != nil {
		poi.ColorHex = *input.ColorHex
	}
	if input.Tags != nil {
		poi.Tags = input.Tags
	}
	if input.CustomMetadata != nil {
		poi.CustomMetadata = input.CustomMetadata
	}
	if input.Attachments != nil {
		poi.Attachments = input.Attachments
	}
	if input.CameraViewpoint != nil {
		poi.CameraViewpoint = input.CameraViewpoint
	}

	if err := s.poiRepo.Update(ctx, poi); err != nil {
		return nil, err
	}

	return poi, nil
}

func (s *POIService) DeletePOI(ctx context.Context, id uuid.UUID) error {
	return s.poiRepo.Delete(ctx, id)
}
