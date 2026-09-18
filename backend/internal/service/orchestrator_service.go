package service

import (
	"context"
	"errors"
	"fmt"
	"sync"
	"time"

	"vastu/backend/internal/domain"
	"vastu/backend/internal/pkg/events"
	"vastu/backend/internal/repository"

	"github.com/google/uuid"
)

type WorkerHeartbeat struct {
	WorkerNodeID string
	JobID        uuid.UUID
	Stage        domain.JobStage
	LastSeenAt   time.Time
}

type OrchestratorService struct {
	jobRepo     repository.JobRepository
	captureRepo repository.CaptureRepository
	modelRepo   repository.ModelRepository
	eventBus    *events.EventBus

	mu         sync.RWMutex
	heartbeats map[uuid.UUID]*WorkerHeartbeat
	retryCount map[uuid.UUID]int
	maxRetries int
}

func NewOrchestratorService(
	jobRepo repository.JobRepository,
	captureRepo repository.CaptureRepository,
	modelRepo repository.ModelRepository,
	eventBus *events.EventBus,
) *OrchestratorService {
	if eventBus == nil {
		eventBus = events.GetEventBus()
	}

	orchestrator := &OrchestratorService{
		jobRepo:     jobRepo,
		captureRepo: captureRepo,
		modelRepo:   modelRepo,
		eventBus:    eventBus,
		heartbeats:  make(map[uuid.UUID]*WorkerHeartbeat),
		retryCount:  make(map[uuid.UUID]int),
		maxRetries:  3,
	}

	orchestrator.registerEventHandlers()
	return orchestrator
}

func (s *OrchestratorService) registerEventHandlers() {
	// Auto-trigger reconstruction job when upload validation is approved
	s.eventBus.Subscribe(events.TopicValidationCompleted, func(ctx context.Context, event events.DomainEvent) error {
		captureIDRaw, ok := event.Payload["capture_id"]
		if !ok {
			return nil
		}
		captureIDStr, _ := captureIDRaw.(string)
		captureID, err := uuid.Parse(captureIDStr)
		if err != nil {
			return nil
		}

		projectIDRaw, _ := event.Payload["project_id"].(string)
		projectID, _ := uuid.Parse(projectIDRaw)

		priority := 5
		_, _ = s.SpawnReconstructionJob(ctx, projectID, &captureID, priority)
		return nil
	})
}

// SpawnReconstructionJob creates a job with idempotency check against duplicate active jobs
func (s *OrchestratorService) SpawnReconstructionJob(ctx context.Context, projectID uuid.UUID, captureID *uuid.UUID, priority int) (*domain.ProcessingJob, error) {
	if captureID != nil {
		existingJobs, err := s.jobRepo.ListByProject(ctx, projectID)
		if err == nil {
			for _, j := range existingJobs {
				if j.CaptureID != nil && *j.CaptureID == *captureID {
					if j.Stage != domain.JobStageCompleted && j.Stage != domain.JobStageFailed {
						// Idempotency: Active job already running for this capture
						return j, nil
					}
				}
			}
		}
	}

	now := time.Now().UTC()
	job := &domain.ProcessingJob{
		ID:                 uuid.New(),
		ProjectID:          projectID,
		CaptureID:          captureID,
		Stage:              domain.JobStageQueued,
		ProgressPercentage: 0,
		Priority:           priority,
		StageDurations:     make(map[string]interface{}),
		StartedAt:          &now,
		CreatedAt:          now,
		UpdatedAt:          now,
	}

	if err := s.jobRepo.Create(ctx, job); err != nil {
		return nil, err
	}

	_ = s.jobRepo.AddLog(ctx, &domain.JobLog{
		JobID:    job.ID,
		Stage:    string(domain.JobStageQueued),
		LogLevel: "info",
		Message:  "Reconstruction workflow initialized in orchestrator queue",
	})

	s.eventBus.Publish(ctx, events.TopicReconstructionStarted, job.ID, map[string]interface{}{
		"job_id":     job.ID.String(),
		"project_id": projectID.String(),
		"priority":   priority,
	})

	return job, nil
}

// RecordWorkerHeartbeat updates worker activity timestamp to prevent timeouts
func (s *OrchestratorService) RecordWorkerHeartbeat(jobID uuid.UUID, workerID string, stage domain.JobStage) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.heartbeats[jobID] = &WorkerHeartbeat{
		WorkerNodeID: workerID,
		JobID:        jobID,
		Stage:        stage,
		LastSeenAt:   time.Now().UTC(),
	}
}

// TransitionStage handles state machine progression and triggers topic events
func (s *OrchestratorService) TransitionStage(
	ctx context.Context,
	jobID uuid.UUID,
	targetStage domain.JobStage,
	progress int,
	workerNodeID *string,
	errorMessage *string,
) error {
	var errCode *string
	if targetStage == domain.JobStageFailed {
		code := "ERR_RECONSTRUCTION_FAILED"
		errCode = &code
	}

	if err := s.jobRepo.UpdateProgress(ctx, jobID, targetStage, progress, workerNodeID, errCode, errorMessage); err != nil {
		return err
	}

	// Emit corresponding domain events
	switch targetStage {
	case domain.JobStagePreprocessing:
		s.eventBus.Publish(ctx, events.TopicFramesExtracted, jobID, map[string]interface{}{"job_id": jobID.String(), "stage": targetStage})
	case domain.JobStageTracking:
		s.eventBus.Publish(ctx, events.TopicReconstructionStarted, jobID, map[string]interface{}{"job_id": jobID.String(), "stage": targetStage})
	case domain.JobStageQuality:
		s.eventBus.Publish(ctx, events.TopicQualityStarted, jobID, map[string]interface{}{"job_id": jobID.String(), "stage": targetStage})
	case domain.JobStageCompleted:
		s.eventBus.Publish(ctx, events.TopicReconstructionCompleted, jobID, map[string]interface{}{"job_id": jobID.String(), "stage": targetStage})
		s.eventBus.Publish(ctx, events.TopicModelCreated, jobID, map[string]interface{}{"job_id": jobID.String()})
	case domain.JobStageFailed:
		s.eventBus.Publish(ctx, events.TopicJobFailed, jobID, map[string]interface{}{
			"job_id": jobID.String(),
			"error":  errorMessage,
		})
	}

	return nil
}

// HandleFailureOrRetry manages automatic exponential retry or permanent failure transition
func (s *OrchestratorService) HandleFailureOrRetry(ctx context.Context, jobID uuid.UUID, failureReason string) (bool, error) {
	s.mu.Lock()
	currentRetries := s.retryCount[jobID]
	if currentRetries < s.maxRetries {
		s.retryCount[jobID] = currentRetries + 1
		s.mu.Unlock()

		backoffSec := 1 << currentRetries // 1s, 2s, 4s exponential backoff
		_ = s.jobRepo.AddLog(ctx, &domain.JobLog{
			JobID:    jobID,
			Stage:    "retry_handler",
			LogLevel: "warning",
			Message:  fmt.Sprintf("Job failed (%s). Retrying (attempt %d/%d) in %ds...", failureReason, currentRetries+1, s.maxRetries, backoffSec),
		})

		time.Sleep(time.Duration(backoffSec) * time.Second)
		_ = s.TransitionStage(ctx, jobID, domain.JobStageQueued, 0, nil, nil)
		return true, nil
	}
	s.mu.Unlock()

	// Permanent failure
	msg := fmt.Sprintf("Permanent failure after %d retry attempts: %s", s.maxRetries, failureReason)
	_ = s.TransitionStage(ctx, jobID, domain.JobStageFailed, 0, nil, &msg)
	return false, errors.New(msg)
}

// ReapStaleJobs watchdog finds jobs that stopped receiving heartbeats and resets or fails them
func (s *OrchestratorService) ReapStaleJobs(ctx context.Context, staleThreshold time.Duration) int {
	s.mu.Lock()
	defer s.mu.Unlock()

	now := time.Now().UTC()
	reapedCount := 0

	for jobID, hb := range s.heartbeats {
		if now.Sub(hb.LastSeenAt) > staleThreshold {
			reapedCount++
			delete(s.heartbeats, jobID)

			go func(jID uuid.UUID, lastHb *WorkerHeartbeat) {
				_, _ = s.HandleFailureOrRetry(context.Background(), jID, fmt.Sprintf("Worker node %s timed out / heartbeats stopped", lastHb.WorkerNodeID))
			}(jobID, hb)
		}
	}

	return reapedCount
}
