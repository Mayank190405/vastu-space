package tests

import (
	"context"
	"sync"
	"testing"
	"time"

	"vastu/backend/internal/domain"
	"vastu/backend/internal/pkg/events"
	"vastu/backend/internal/service"

	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// Mock Job Repository for Unit Tests
type mockJobSystemRepo struct {
	mu   sync.Mutex
	jobs map[uuid.UUID]*domain.ProcessingJob
	logs map[uuid.UUID][]*domain.JobLog
}

func newMockJobSystemRepo() *mockJobSystemRepo {
	return &mockJobSystemRepo{
		jobs: make(map[uuid.UUID]*domain.ProcessingJob),
		logs: make(map[uuid.UUID][]*domain.JobLog),
	}
}

func (m *mockJobSystemRepo) Create(ctx context.Context, job *domain.ProcessingJob) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.jobs[job.ID] = job
	return nil
}

func (m *mockJobSystemRepo) GetByID(ctx context.Context, id uuid.UUID) (*domain.ProcessingJob, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	j, ok := m.jobs[id]
	if !ok {
		return nil, assert.AnError
	}
	return j, nil
}

func (m *mockJobSystemRepo) ListByProject(ctx context.Context, projectID uuid.UUID) ([]*domain.ProcessingJob, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	var list []*domain.ProcessingJob
	for _, j := range m.jobs {
		if j.ProjectID == projectID {
			list = append(list, j)
		}
	}
	return list, nil
}

func (m *mockJobSystemRepo) UpdateProgress(ctx context.Context, id uuid.UUID, stage domain.JobStage, progress int, workerNodeID, errorCode, errorMessage *string) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	j, ok := m.jobs[id]
	if !ok {
		return assert.AnError
	}
	j.Stage = stage
	j.ProgressPercentage = progress
	j.WorkerNodeID = workerNodeID
	j.ErrorCode = errorCode
	j.ErrorMessage = errorMessage
	return nil
}

func (m *mockJobSystemRepo) AddLog(ctx context.Context, log *domain.JobLog) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.logs[log.JobID] = append(m.logs[log.JobID], log)
	return nil
}

func (m *mockJobSystemRepo) ListLogs(ctx context.Context, jobID uuid.UUID) ([]*domain.JobLog, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	return m.logs[jobID], nil
}

func TestProcessingJobSystem(t *testing.T) {
	ctx := context.Background()
	eventBus := events.NewEventBus(100)
	jobRepo := newMockJobSystemRepo()

	orchestrator := service.NewOrchestratorService(jobRepo, nil, nil, eventBus)
	projectID := uuid.New()
	captureID := uuid.New()

	t.Run("TC01: Job Creation and Idempotency", func(t *testing.T) {
		job1, err := orchestrator.SpawnReconstructionJob(ctx, projectID, &captureID, 5)
		require.NoError(t, err)
		assert.Equal(t, domain.JobStageQueued, job1.Stage)

		// Spawning again for same capture should return same active job
		job2, err := orchestrator.SpawnReconstructionJob(ctx, projectID, &captureID, 5)
		require.NoError(t, err)
		assert.Equal(t, job1.ID, job2.ID)
	})

	t.Run("TC02: Stage Progression and Event Emission", func(t *testing.T) {
		var receivedEvents []string
		var eventMu sync.Mutex

		eventBus.Subscribe("*", func(ctx context.Context, e events.DomainEvent) error {
			eventMu.Lock()
			receivedEvents = append(receivedEvents, e.Topic)
			eventMu.Unlock()
			return nil
		})

		job, err := orchestrator.SpawnReconstructionJob(ctx, projectID, nil, 5)
		require.NoError(t, err)

		workerID := "worker-gpu-01"
		err = orchestrator.TransitionStage(ctx, job.ID, domain.JobStagePreprocessing, 20, &workerID, nil)
		require.NoError(t, err)

		err = orchestrator.TransitionStage(ctx, job.ID, domain.JobStageTracking, 45, &workerID, nil)
		require.NoError(t, err)

		err = orchestrator.TransitionStage(ctx, job.ID, domain.JobStageCompleted, 100, &workerID, nil)
		require.NoError(t, err)

		time.Sleep(50 * time.Millisecond) // Allow async event dispatch

		eventMu.Lock()
		defer eventMu.Unlock()
		assert.Contains(t, receivedEvents, events.TopicFramesExtracted)
		assert.Contains(t, receivedEvents, events.TopicReconstructionStarted)
		assert.Contains(t, receivedEvents, events.TopicReconstructionCompleted)
		assert.Contains(t, receivedEvents, events.TopicModelCreated)
	})

	t.Run("TC03: Worker Heartbeat and Stale Job Reaping", func(t *testing.T) {
		job, err := orchestrator.SpawnReconstructionJob(ctx, projectID, nil, 5)
		require.NoError(t, err)

		// Record initial heartbeat
		orchestrator.RecordWorkerHeartbeat(job.ID, "worker-node-dead", domain.JobStageTracking)

		// Fast-forward reaper check with 1 millisecond threshold
		time.Sleep(5 * time.Millisecond)
		reaped := orchestrator.ReapStaleJobs(ctx, 1*time.Millisecond)
		assert.Equal(t, 1, reaped)
	})
}
