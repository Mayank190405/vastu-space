package service

import (
	"context"
	"errors"

	"vastu/backend/internal/domain"
	"vastu/backend/internal/repository"

	"github.com/google/uuid"
)

type CaptureService struct {
	captureRepo repository.CaptureRepository
	projectRepo repository.ProjectRepository
}

func NewCaptureService(captureRepo repository.CaptureRepository, projectRepo repository.ProjectRepository) *CaptureService {
	return &CaptureService{
		captureRepo: captureRepo,
		projectRepo: projectRepo,
	}
}

func (s *CaptureService) CreateCapture(ctx context.Context, operatorID uuid.UUID, input domain.CreateCaptureInput) (*domain.Capture, error) {
	if input.ProjectID == uuid.Nil {
		return nil, errors.New("project_id is required")
	}
	if input.DeviceModel == "" || input.DeviceOS == "" {
		return nil, errors.New("device model and OS are required")
	}

	// Verify project exists
	_, err := s.projectRepo.GetByID(ctx, input.ProjectID)
	if err != nil {
		return nil, errors.New("project not found")
	}

	mode := input.CaptureMode
	if mode == "" {
		mode = domain.CaptureModeRGBIMU
	}

	capture := &domain.Capture{
		ID:                     uuid.New(),
		ProjectID:              input.ProjectID,
		StructureID:            input.StructureID,
		LevelID:                input.LevelID,
		SectionID:              input.SectionID,
		OperatorID:             &operatorID,
		DeviceModel:            input.DeviceModel,
		DeviceOS:               input.DeviceOS,
		DeviceAppVersion:       input.DeviceAppVersion,
		CameraIntrinsics:       input.CameraIntrinsics,
		IMURateHz:              input.IMURateHz,
		HasLiDAR:               input.HasLiDAR,
		CaptureMode:            mode,
		DurationSeconds:        input.DurationSeconds,
		FramesCount:            input.FramesCount,
		FileSizeBytes:          input.FileSizeBytes,
		TrajectoryLengthMeters: input.TrajectoryLengthMeters,
		QualityScore:           input.QualityScore,
		BlurScore:              input.BlurScore,
		LightingScore:          input.LightingScore,
		Status:                 domain.CaptureStatusRecording,
		Notes:                  input.Notes,
	}

	if err := s.captureRepo.Create(ctx, capture); err != nil {
		return nil, err
	}

	return capture, nil
}

func (s *CaptureService) GetCapture(ctx context.Context, id uuid.UUID) (*domain.Capture, error) {
	return s.captureRepo.GetByID(ctx, id)
}

func (s *CaptureService) ListCapturesByProject(ctx context.Context, projectID uuid.UUID) ([]*domain.Capture, error) {
	return s.captureRepo.ListByProject(ctx, projectID)
}

func (s *CaptureService) UpdateCaptureStatus(ctx context.Context, id uuid.UUID, input domain.UpdateCaptureStatusInput) (*domain.Capture, error) {
	if err := s.captureRepo.UpdateStatus(ctx, id, input.Status, input.QualityScore, input.ManifestURL, input.VideoURL, input.IMUURL, input.LiDARURL); err != nil {
		return nil, err
	}
	return s.captureRepo.GetByID(ctx, id)
}
