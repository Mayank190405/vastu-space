package service

import (
	"context"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"vastu/backend/internal/domain"
	"vastu/backend/internal/pkg/queue"
	"vastu/backend/internal/repository"

	"github.com/google/uuid"
)

type JobService struct {
	jobRepo     repository.JobRepository
	projectRepo repository.ProjectRepository
	captureRepo repository.CaptureRepository
	asynqClient *queue.AsynqClient
	uploadDir   string
}

func NewJobService(jobRepo repository.JobRepository, projectRepo repository.ProjectRepository, captureRepo repository.CaptureRepository, asynqClient ...*queue.AsynqClient) *JobService {
	var client *queue.AsynqClient
	if len(asynqClient) > 0 {
		client = asynqClient[0]
	}
	return &JobService{
		jobRepo:     jobRepo,
		projectRepo: projectRepo,
		captureRepo: captureRepo,
		asynqClient: client,
		uploadDir:   "./uploads",
	}
}

func (s *JobService) SetUploadDir(dir string) {
	s.uploadDir = dir
}

func (s *JobService) SetAsynqClient(client *queue.AsynqClient) {
	s.asynqClient = client
}

func (s *JobService) CreateJob(ctx context.Context, input domain.CreateJobInput) (*domain.ProcessingJob, error) {
	return s.createJob(ctx, input, "", false)
}
func (s *JobService) CreateSessionJob(ctx context.Context, sessionID string, input domain.CreateJobInput) (*domain.ProcessingJob, error) {
	return s.createJob(ctx, input, sessionID, false)
}
func (s *JobService) CreateRetrySessionJob(ctx context.Context, sessionID string, input domain.CreateJobInput) (*domain.ProcessingJob, error) {
	return s.createJob(ctx, input, sessionID, true)
}
func (s *JobService) createJob(ctx context.Context, input domain.CreateJobInput, sessionID string, retry bool) (*domain.ProcessingJob, error) {
	if input.ProjectID == uuid.Nil {
		return nil, errors.New("project_id is required")
	}

	// Never submit a worker task without a persisted, verified capture input.
	if s.asynqClient != nil {
		if input.CaptureID == nil || s.captureRepo == nil {
			return nil, errors.New("VERIFIED_CAPTURE_REQUIRED")
		}
		capture, err := s.captureRepo.GetByID(ctx, *input.CaptureID)
		if err != nil || capture == nil {
			return nil, errors.New("CAPTURE_NOT_FOUND")
		}
		if capture.ProjectID != input.ProjectID {
			return nil, errors.New("CAPTURE_PROJECT_MISMATCH")
		}
		if capture.VideoURL == nil || capture.Status != domain.CaptureStatusUploaded {
			return nil, errors.New("UPLOAD_NOT_VERIFIED")
		}
		prefix := "/uploads/clean/"
		if !strings.HasPrefix(*capture.VideoURL, prefix) {
			return nil, errors.New("VERIFIED_VIDEO_PATH_REQUIRED")
		}
		name := strings.TrimPrefix(*capture.VideoURL, prefix)
		if name == "" || filepath.Base(name) != name {
			return nil, errors.New("INVALID_VIDEO_PATH")
		}
		info, err := os.Stat(filepath.Join(s.uploadDir, "clean", name))
		if err != nil || !info.Mode().IsRegular() || info.Size() == 0 {
			return nil, errors.New("VERIFIED_VIDEO_MISSING")
		}
	}

	priority := 5
	if input.Priority != nil && *input.Priority >= 1 && *input.Priority <= 10 {
		priority = *input.Priority
	}

	jobID := uuid.New()
	var existing *domain.ProcessingJob
	if sessionID != "" && !retry {
		jobID = uuid.NewSHA1(uuid.NameSpaceURL, []byte("vastu:job:"+sessionID))
		existing, _ = s.jobRepo.GetByID(ctx, jobID)
		if existing != nil && existing.Stage != domain.JobStageQueued {
			return existing, nil
		}
	}
	now := time.Now().UTC()
	job := &domain.ProcessingJob{
		ID:                 jobID,
		ProjectID:          input.ProjectID,
		CaptureID:          input.CaptureID,
		Stage:              domain.JobStageQueued,
		ProgressPercentage: 0,
		Priority:           priority,
		StageDurations:     make(map[string]interface{}),
		StartedAt:          &now,
		CreatedAt:          now,
		UpdatedAt:          now,
	}

	if existing == nil {
		if err := s.jobRepo.Create(ctx, job); err != nil {
			return nil, err
		}

	}
	// Add initial log
	_ = s.jobRepo.AddLog(ctx, &domain.JobLog{
		JobID:    job.ID,
		Stage:    string(domain.JobStageQueued),
		LogLevel: "info",
		Message:  "Spatial reconstruction job placed in processing queue",
	})

	// Enqueue to Asynq Redis queue if client is configured
	if s.asynqClient != nil {
		videoURL := ""
		imuURL := ""
		lidarURL := ""

		if input.CaptureID != nil && s.captureRepo != nil {
			if cap, err := s.captureRepo.GetByID(ctx, *input.CaptureID); err == nil && cap != nil {
				if cap.VideoURL != nil {
					videoURL = filepath.Join(s.uploadDir, "clean", filepath.Base(*cap.VideoURL))
				}
				if cap.IMUURL != nil {
					imuURL = *cap.IMUURL
				}
				if cap.LiDARURL != nil {
					lidarURL = *cap.LiDARURL
				}
			}
		}

		workDir := fmt.Sprintf("%s/scratch/%s", s.uploadDir, job.ID.String())
		_ = os.MkdirAll(workDir, 0755)

		payload := &queue.ReconstructionPayload{
			SessionID: sessionID,
			JobID:     job.ID,
			ProjectID: job.ProjectID,
			CaptureID: job.CaptureID,
			VideoURL:  videoURL,
			IMUURL:    imuURL,
			LiDARURL:  lidarURL,
			WorkDir:   workDir,
			Priority:  priority,
		}

		if _, err := s.asynqClient.EnqueueReconstructionJob(ctx, payload); err != nil {
			errMsg := fmt.Sprintf("Failed to enqueue task to Asynq queue: %v", err)
			errCode := "ERR_ENQUEUE_FAILED"
			_ = s.jobRepo.UpdateProgress(ctx, job.ID, domain.JobStageFailed, 0, nil, &errCode, &errMsg)
			_ = s.jobRepo.AddLog(ctx, &domain.JobLog{
				JobID:    job.ID,
				Stage:    string(domain.JobStageFailed),
				LogLevel: "error",
				Message:  errMsg,
			})
			return nil, fmt.Errorf("job created but queue submission failed: %w", err)
		}

		_ = s.jobRepo.AddLog(ctx, &domain.JobLog{
			JobID:    job.ID,
			Stage:    string(domain.JobStageQueued),
			LogLevel: "info",
			Message:  "Reconstruction task successfully submitted to Redis worker queue",
		})
	}

	return job, nil
}

func (s *JobService) GetJob(ctx context.Context, id uuid.UUID) (*domain.ProcessingJob, error) {
	return s.jobRepo.GetByID(ctx, id)
}

func (s *JobService) ListJobsByProject(ctx context.Context, projectID uuid.UUID) ([]*domain.ProcessingJob, error) {
	return s.jobRepo.ListByProject(ctx, projectID)
}

func (s *JobService) UpdateProgress(ctx context.Context, id uuid.UUID, input domain.UpdateJobProgressInput) (*domain.ProcessingJob, error) {
	if err := s.jobRepo.UpdateProgress(ctx, id, input.Stage, input.ProgressPercentage, input.WorkerNodeID, input.ErrorCode, input.ErrorMessage); err != nil {
		return nil, err
	}

	logLevel := "info"
	msg := "Progress updated"
	if input.Stage == domain.JobStageFailed {
		logLevel = "error"
		if input.ErrorMessage != nil {
			msg = *input.ErrorMessage
		} else {
			msg = "Job failed during execution"
		}
	} else if input.Stage == domain.JobStageCompleted {
		msg = "Spatial model reconstruction and cell fusion completed successfully"
	}

	_ = s.jobRepo.AddLog(ctx, &domain.JobLog{
		JobID:    id,
		Stage:    string(input.Stage),
		LogLevel: logLevel,
		Message:  msg,
	})

	return s.jobRepo.GetByID(ctx, id)
}

func (s *JobService) AddLog(ctx context.Context, jobID uuid.UUID, stage, level, message string, meta map[string]interface{}) error {
	return s.jobRepo.AddLog(ctx, &domain.JobLog{
		JobID:    jobID,
		Stage:    stage,
		LogLevel: level,
		Message:  message,
		Meta:     meta,
	})
}

func (s *JobService) GetLogs(ctx context.Context, jobID uuid.UUID) ([]*domain.JobLog, error) {
	return s.jobRepo.ListLogs(ctx, jobID)
}
