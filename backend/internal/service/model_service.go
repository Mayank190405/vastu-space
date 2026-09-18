package service

import (
	"context"
	"errors"
	"fmt"

	"vastu/backend/internal/domain"
	"vastu/backend/internal/repository"

	"github.com/google/uuid"
)

type ModelService struct {
	modelRepo   repository.ModelRepository
	projectRepo repository.ProjectRepository
}

func NewModelService(modelRepo repository.ModelRepository, projectRepo repository.ProjectRepository) *ModelService {
	return &ModelService{
		modelRepo:   modelRepo,
		projectRepo: projectRepo,
	}
}

func (s *ModelService) CreateModel(ctx context.Context, userID uuid.UUID, input domain.CreateModelInput) (*domain.SpatialModel, error) {
	if input.ProjectID == uuid.Nil {
		return nil, errors.New("project_id is required")
	}
	if input.Title == "" {
		return nil, errors.New("title is required")
	}

	version := input.Version
	if version == "" {
		version = "v1.0.0"
	}

	model := &domain.SpatialModel{
		ID:                   uuid.New(),
		ProjectID:            input.ProjectID,
		LevelID:              input.LevelID,
		SectionID:            input.SectionID,
		Version:              version,
		Title:                input.Title,
		Description:          input.Description,
		BoundingBox:          input.BoundingBox,
		CoordinateFrame:      input.CoordinateFrame,
		TotalVertices:        input.TotalVertices,
		TotalFaces:           input.TotalFaces,
		PointDensitySQM:      input.PointDensitySQM,
		PrecisionDeviationCM: input.PrecisionDeviationCM,
		LineageDepth:         1,
		IsActiveVersion:      true,
		CreatedBy:            &userID,
	}

	if err := s.modelRepo.Create(ctx, model); err != nil {
		return nil, err
	}

	// Insert artifacts
	for _, artInput := range input.Artifacts {
		artifact := &domain.ModelArtifact{
			ID:            uuid.New(),
			ModelID:       model.ID,
			ArtifactType:  artInput.ArtifactType,
			LODLevel:      artInput.LODLevel,
			FileFormat:    artInput.FileFormat,
			FileSizeBytes: artInput.FileSizeBytes,
			FileURL:       artInput.FileURL,
			SHA256Hash:    artInput.SHA256Hash,
		}
		_ = s.modelRepo.CreateArtifact(ctx, artifact)
		model.Artifacts = append(model.Artifacts, artifact)
	}

	return model, nil
}

func (s *ModelService) GetModel(ctx context.Context, id uuid.UUID) (*domain.SpatialModel, error) {
	return s.modelRepo.GetByID(ctx, id)
}

func (s *ModelService) GetActiveModel(ctx context.Context, projectID uuid.UUID) (*domain.SpatialModel, error) {
	return s.modelRepo.GetActiveByProject(ctx, projectID)
}

func (s *ModelService) ListModelsByProject(ctx context.Context, projectID uuid.UUID) ([]*domain.SpatialModel, error) {
	return s.modelRepo.ListByProject(ctx, projectID)
}

func (s *ModelService) AddArtifact(ctx context.Context, modelID uuid.UUID, input domain.CreateArtifactInput) (*domain.ModelArtifact, error) {
	artifact := &domain.ModelArtifact{
		ID:            uuid.New(),
		ModelID:       modelID,
		ArtifactType:  input.ArtifactType,
		LODLevel:      input.LODLevel,
		FileFormat:    input.FileFormat,
		FileSizeBytes: input.FileSizeBytes,
		FileURL:       input.FileURL,
		SHA256Hash:    input.SHA256Hash,
	}
	if err := s.modelRepo.CreateArtifact(ctx, artifact); err != nil {
		return nil, err
	}
	return artifact, nil
}

// PublishVersion marks a model as immutable, assigns published timestamp, and activates it as the active version.
func (s *ModelService) PublishVersion(ctx context.Context, projectID uuid.UUID, modelID uuid.UUID) (*domain.SpatialModel, error) {
	model, err := s.modelRepo.GetByID(ctx, modelID)
	if err != nil {
		return nil, err
	}
	if model.ProjectID != projectID {
		return nil, errors.New("model does not belong to project")
	}

	if err := s.modelRepo.PublishModel(ctx, modelID); err != nil {
		return nil, err
	}
	if err := s.modelRepo.SetActiveVersion(ctx, projectID, modelID); err != nil {
		return nil, err
	}

	return s.modelRepo.GetByID(ctx, modelID)
}

// RollbackToVersion reverts the project's active model to a previous valid version atomically.
func (s *ModelService) RollbackToVersion(ctx context.Context, projectID uuid.UUID, targetModelID uuid.UUID) (*domain.SpatialModel, error) {
	targetModel, err := s.modelRepo.GetByID(ctx, targetModelID)
	if err != nil {
		return nil, err
	}
	if targetModel.ProjectID != projectID {
		return nil, errors.New("target model does not belong to project")
	}

	if err := s.modelRepo.SetActiveVersion(ctx, projectID, targetModelID); err != nil {
		return nil, err
	}

	return s.modelRepo.GetActiveByProject(ctx, projectID)
}

// CreateIncrementalVersion creates a child version derived from an existing parent version.
func (s *ModelService) CreateIncrementalVersion(ctx context.Context, userID uuid.UUID, parentID uuid.UUID, input domain.CreateModelInput) (*domain.SpatialModel, error) {
	parent, err := s.modelRepo.GetByID(ctx, parentID)
	if err != nil {
		return nil, fmt.Errorf("parent model not found: %w", err)
	}

	version := input.Version
	if version == "" {
		version = fmt.Sprintf("v1.%d.0", parent.LineageDepth)
	}

	model := &domain.SpatialModel{
		ID:                   uuid.New(),
		ProjectID:            parent.ProjectID,
		LevelID:              parent.LevelID,
		SectionID:            parent.SectionID,
		Version:              version,
		Title:                input.Title,
		Description:          input.Description,
		BoundingBox:          input.BoundingBox,
		CoordinateFrame:      input.CoordinateFrame,
		TotalVertices:        input.TotalVertices,
		TotalFaces:           input.TotalFaces,
		PointDensitySQM:      input.PointDensitySQM,
		PrecisionDeviationCM: input.PrecisionDeviationCM,
		ParentModelID:        &parent.ID,
		LineageDepth:         parent.LineageDepth + 1,
		IsActiveVersion:      false,
		IsImmutable:          false,
		CreatedBy:            &userID,
	}

	if err := s.modelRepo.Create(ctx, model); err != nil {
		return nil, err
	}

	for _, artInput := range input.Artifacts {
		artifact := &domain.ModelArtifact{
			ID:            uuid.New(),
			ModelID:       model.ID,
			ArtifactType:  artInput.ArtifactType,
			LODLevel:      artInput.LODLevel,
			FileFormat:    artInput.FileFormat,
			FileSizeBytes: artInput.FileSizeBytes,
			FileURL:       artInput.FileURL,
			SHA256Hash:    artInput.SHA256Hash,
		}
		_ = s.modelRepo.CreateArtifact(ctx, artifact)
		model.Artifacts = append(model.Artifacts, artifact)
	}

	return model, nil
}

// UpdateModel modifies model metadata, failing with ErrModelImmutable if the model is locked.
func (s *ModelService) UpdateModel(ctx context.Context, modelID uuid.UUID, title string, description *string) (*domain.SpatialModel, error) {
	model, err := s.modelRepo.GetByID(ctx, modelID)
	if err != nil {
		return nil, err
	}
	if model.IsImmutable {
		return nil, domain.ErrModelImmutable
	}

	model.Title = title
	model.Description = description
	if err := s.modelRepo.Update(ctx, model); err != nil {
		return nil, err
	}
	return model, nil
}
