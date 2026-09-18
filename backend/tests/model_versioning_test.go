package tests

import (
	"context"
	"testing"
	"time"

	"vastu/backend/internal/domain"
	"vastu/backend/internal/service"

	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

type mockModelRepo struct {
	models    map[uuid.UUID]*domain.SpatialModel
	artifacts map[uuid.UUID][]*domain.ModelArtifact
}

func newMockModelRepo() *mockModelRepo {
	return &mockModelRepo{
		models:    make(map[uuid.UUID]*domain.SpatialModel),
		artifacts: make(map[uuid.UUID][]*domain.ModelArtifact),
	}
}

func (m *mockModelRepo) Create(ctx context.Context, model *domain.SpatialModel) error {
	m.models[model.ID] = model
	return nil
}

func (m *mockModelRepo) GetByID(ctx context.Context, id uuid.UUID) (*domain.SpatialModel, error) {
	model, ok := m.models[id]
	if !ok {
		return nil, domain.ErrModelNotFound
	}
	model.Artifacts = m.artifacts[id]
	return model, nil
}

func (m *mockModelRepo) ListByProject(ctx context.Context, projectID uuid.UUID) ([]*domain.SpatialModel, error) {
	var list []*domain.SpatialModel
	for _, mod := range m.models {
		if mod.ProjectID == projectID {
			list = append(list, mod)
		}
	}
	return list, nil
}

func (m *mockModelRepo) GetActiveByProject(ctx context.Context, projectID uuid.UUID) (*domain.SpatialModel, error) {
	for _, mod := range m.models {
		if mod.ProjectID == projectID && mod.IsActiveVersion {
			return mod, nil
		}
	}
	return nil, domain.ErrModelNotFound
}

func (m *mockModelRepo) SetActiveVersion(ctx context.Context, projectID uuid.UUID, modelID uuid.UUID) error {
	target, ok := m.models[modelID]
	if !ok || target.ProjectID != projectID {
		return domain.ErrModelNotFound
	}
	for _, mod := range m.models {
		if mod.ProjectID == projectID {
			mod.IsActiveVersion = false
		}
	}
	target.IsActiveVersion = true
	return nil
}

func (m *mockModelRepo) PublishModel(ctx context.Context, modelID uuid.UUID) error {
	model, ok := m.models[modelID]
	if !ok {
		return domain.ErrModelNotFound
	}
	now := time.Now().UTC()
	model.IsImmutable = true
	model.PublishedAt = &now
	return nil
}

func (m *mockModelRepo) Update(ctx context.Context, model *domain.SpatialModel) error {
	existing, ok := m.models[model.ID]
	if !ok {
		return domain.ErrModelNotFound
	}
	if existing.IsImmutable {
		return domain.ErrModelImmutable
	}
	m.models[model.ID] = model
	return nil
}

func (m *mockModelRepo) CreateArtifact(ctx context.Context, artifact *domain.ModelArtifact) error {
	m.artifacts[artifact.ModelID] = append(m.artifacts[artifact.ModelID], artifact)
	return nil
}

func (m *mockModelRepo) ListArtifactsByModel(ctx context.Context, modelID uuid.UUID) ([]*domain.ModelArtifact, error) {
	return m.artifacts[modelID], nil
}

func TestModelRegistryAndVersioning(t *testing.T) {
	ctx := context.Background()
	repo := newMockModelRepo()
	svc := service.NewModelService(repo, nil)

	projectID := uuid.New()
	userID := uuid.New()

	// -------------------------------------------------------------------------
	// Scenario 1: Publish Version (creates V1.0.0, marked immutable and active)
	// -------------------------------------------------------------------------
	t.Run("Scenario 1: Publish version creates active immutable V1", func(t *testing.T) {
		hash := "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
		input := domain.CreateModelInput{
			ProjectID: projectID,
			Version:   "v1.0.0",
			Title:     "Building HQ Ground Floor V1",
			Artifacts: []domain.CreateArtifactInput{
				{ArtifactType: "mesh_gltf", LODLevel: 0, FileFormat: "gltf", FileSizeBytes: 2048500, FileURL: "s3://vastu/v1/model.gltf", SHA256Hash: &hash},
				{ArtifactType: "point_cloud_ply", LODLevel: 1, FileFormat: "ply", FileSizeBytes: 1024000, FileURL: "s3://vastu/v1/cloud.ply"},
			},
		}

		v1, err := svc.CreateModel(ctx, userID, input)
		require.NoError(t, err)
		require.NotNil(t, v1)
		assert.Equal(t, "v1.0.0", v1.Version)
		assert.Equal(t, 1, v1.LineageDepth)

		// Publish V1
		publishedV1, err := svc.PublishVersion(ctx, projectID, v1.ID)
		require.NoError(t, err)
		assert.True(t, publishedV1.IsImmutable)
		assert.True(t, publishedV1.IsActiveVersion)
		assert.NotNil(t, publishedV1.PublishedAt)
	})

	// -------------------------------------------------------------------------
	// Scenario 2: Incremental Versioning (creates V1.1.0 with parent pointing to V1)
	// -------------------------------------------------------------------------
	var v2ID uuid.UUID
	t.Run("Scenario 2: Incremental child version links to parent and increments lineage depth", func(t *testing.T) {
		activeV1, err := svc.GetActiveModel(ctx, projectID)
		require.NoError(t, err)

		childInput := domain.CreateModelInput{
			ProjectID: projectID,
			Title:     "Building HQ Ground Floor V1.1 (Targeted Rescan Patch)",
		}

		v2, err := svc.CreateIncrementalVersion(ctx, userID, activeV1.ID, childInput)
		require.NoError(t, err)
		require.NotNil(t, v2)
		assert.Equal(t, &activeV1.ID, v2.ParentModelID)
		assert.Equal(t, 2, v2.LineageDepth)
		assert.Equal(t, "v1.1.0", v2.Version)
		assert.False(t, v2.IsActiveVersion, "New child version should not be active until promoted/published")
		assert.False(t, v2.IsImmutable, "Unpublished draft model should remain mutable")
		v2ID = v2.ID
	})

	// -------------------------------------------------------------------------
	// Scenario 3: Mutation Prevention (modifying immutable model fails)
	// -------------------------------------------------------------------------
	t.Run("Scenario 3: Attempting to update immutable model fails with ErrModelImmutable", func(t *testing.T) {
		activeV1, err := svc.GetActiveModel(ctx, projectID)
		require.NoError(t, err)
		require.True(t, activeV1.IsImmutable)

		// Try to mutate published V1 title
		_, err = svc.UpdateModel(ctx, activeV1.ID, "Tampered Title", nil)
		assert.ErrorIs(t, err, domain.ErrModelImmutable, "Mutation on published model must be blocked")

		// Mutating unpublished draft V2 should succeed
		desc := "Draft notes"
		updatedV2, err := svc.UpdateModel(ctx, v2ID, "Building HQ V1.1 Updated", &desc)
		require.NoError(t, err)
		assert.Equal(t, "Building HQ V1.1 Updated", updatedV2.Title)
	})

	// -------------------------------------------------------------------------
	// Scenario 4: Active Version Retrieval
	// -------------------------------------------------------------------------
	t.Run("Scenario 4: Active version retrieval and promotion", func(t *testing.T) {
		// Currently V1 is active
		active, err := svc.GetActiveModel(ctx, projectID)
		require.NoError(t, err)
		assert.Equal(t, "v1.0.0", active.Version)

		// Publish and promote V2
		publishedV2, err := svc.PublishVersion(ctx, projectID, v2ID)
		require.NoError(t, err)
		assert.True(t, publishedV2.IsActiveVersion)

		// Verify GetActiveModel now returns V2
		currentActive, err := svc.GetActiveModel(ctx, projectID)
		require.NoError(t, err)
		assert.Equal(t, "v1.1.0", currentActive.Version)
	})

	// -------------------------------------------------------------------------
	// Scenario 5: Rollback to Version
	// -------------------------------------------------------------------------
	t.Run("Scenario 5: Rollback to previous version restores V1 as active", func(t *testing.T) {
		allModels, err := svc.ListModelsByProject(ctx, projectID)
		require.NoError(t, err)
		require.Len(t, allModels, 2)

		var v1Model *domain.SpatialModel
		for _, m := range allModels {
			if m.Version == "v1.0.0" {
				v1Model = m
				break
			}
		}
		require.NotNil(t, v1Model)

		// Rollback active version to V1
		rolledBack, err := svc.RollbackToVersion(ctx, projectID, v1Model.ID)
		require.NoError(t, err)
		assert.Equal(t, "v1.0.0", rolledBack.Version)
		assert.True(t, rolledBack.IsActiveVersion)

		// Confirm V2 is no longer active
		v2Model, err := svc.GetModel(ctx, v2ID)
		require.NoError(t, err)
		assert.False(t, v2Model.IsActiveVersion)
	})

	// -------------------------------------------------------------------------
	// Scenario 6: Artifact Integrity Check
	// -------------------------------------------------------------------------
	t.Run("Scenario 6: Artifact integrity and multi-LOD manifest verification", func(t *testing.T) {
		allModels, err := svc.ListModelsByProject(ctx, projectID)
		require.NoError(t, err)

		var v1Model *domain.SpatialModel
		for _, m := range allModels {
			if m.Version == "v1.0.0" {
				v1Model = m
				break
			}
		}
		require.NotNil(t, v1Model)

		// Retrieve model artifacts
		mWithArtifacts, err := svc.GetModel(ctx, v1Model.ID)
		require.NoError(t, err)
		require.Len(t, mWithArtifacts.Artifacts, 2)

		lod0 := mWithArtifacts.Artifacts[0]
		assert.Equal(t, "mesh_gltf", lod0.ArtifactType)
		assert.Equal(t, 0, lod0.LODLevel)
		assert.NotNil(t, lod0.SHA256Hash)
		assert.Equal(t, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", *lod0.SHA256Hash)
	})
}
