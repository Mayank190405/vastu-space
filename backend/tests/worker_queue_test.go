package tests

import (
	"context"
	"testing"

	"vastu/backend/internal/domain"
	"vastu/backend/internal/pkg/events"
	"vastu/backend/internal/pkg/queue"
	"vastu/backend/internal/service"

	"github.com/google/uuid"
	"github.com/hibiken/asynq"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// TestRedisConnOptParsing validates that Redis URIs, passwords, and addresses parse correctly
func TestRedisConnOptParsing(t *testing.T) {
	// Case 1: Standard URI with password and DB
	uri := "redis://:secret_pwd@vastu-redis:6379/1"
	opt := queue.ParseRedisConnOpt(uri)
	clientOpt, ok := opt.(asynq.RedisClientOpt)
	require.True(t, ok, "Expected RedisClientOpt from URI")
	assert.Equal(t, "vastu-redis:6379", clientOpt.Addr)
	assert.Equal(t, "secret_pwd", clientOpt.Password)
	assert.Equal(t, 1, clientOpt.DB)

	// Case 2: Plain host:port with separate password
	opt2 := queue.ParseRedisConnOpt("vastu-redis:6379", "my_redis_pwd")
	clientOpt2, ok2 := opt2.(asynq.RedisClientOpt)
	require.True(t, ok2, "Expected RedisClientOpt from host:port")
	assert.Equal(t, "vastu-redis:6379", clientOpt2.Addr)
	assert.Equal(t, "my_redis_pwd", clientOpt2.Password)

	// Case 3: Empty string defaults to localhost:6379
	opt3 := queue.ParseRedisConnOpt("")
	clientOpt3, ok3 := opt3.(asynq.RedisClientOpt)
	require.True(t, ok3, "Expected RedisClientOpt from empty string")
	assert.Equal(t, "localhost:6379", clientOpt3.Addr)
}

// TestReconstructionPayloadEncodeDecode validates serialization round-trip
func TestReconstructionPayloadEncodeDecode(t *testing.T) {
	jobID := uuid.New()
	projectID := uuid.New()
	captureID := uuid.New()

	original := &queue.ReconstructionPayload{
		JobID:      jobID,
		ProjectID:  projectID,
		CaptureID:  &captureID,
		VideoURL:   "https://storage.vastu.space/raw/video.mp4",
		IMUURL:     "https://storage.vastu.space/raw/imu.json",
		LiDARURL:   "https://storage.vastu.space/raw/lidar.pcd",
		WorkDir:    "/app/uploads/scratch/" + jobID.String(),
		Priority:   8,
		RetryCount: 1,
	}

	encoded, err := original.Encode()
	require.NoError(t, err, "Encoding payload must succeed")
	require.NotEmpty(t, encoded)

	decoded, err := queue.DecodeReconstructionPayload(encoded)
	require.NoError(t, err, "Decoding payload must succeed")
	assert.Equal(t, original.JobID, decoded.JobID)
	assert.Equal(t, original.ProjectID, decoded.ProjectID)
	assert.Equal(t, original.CaptureID, decoded.CaptureID)
	assert.Equal(t, original.VideoURL, decoded.VideoURL)
	assert.Equal(t, original.IMUURL, decoded.IMUURL)
	assert.Equal(t, original.LiDARURL, decoded.LiDARURL)
	assert.Equal(t, original.WorkDir, decoded.WorkDir)
	assert.Equal(t, original.Priority, decoded.Priority)
}

// TestJobServiceCreateJobEnqueueWithoutClient validates safe persistence when queue client is nil
func TestJobServiceCreateJobWithoutClient(t *testing.T) {
	jobRepo := newMockJobRepo()
	svc := service.NewJobService(jobRepo, nil, nil)

	projectID := uuid.New()
	prio := 7
	input := domain.CreateJobInput{
		ProjectID: projectID,
		Priority:  &prio,
	}

	job, err := svc.CreateJob(context.Background(), input)
	require.NoError(t, err)
	assert.NotNil(t, job)
	assert.Equal(t, domain.JobStageQueued, job.Stage)
	assert.Equal(t, 7, job.Priority)

	// Verify job persisted in mock repository
	persisted, err := jobRepo.GetByID(context.Background(), job.ID)
	require.NoError(t, err)
	assert.Equal(t, job.ID, persisted.ID)
}

// TestAsynqServerInitialization validates construction of AsynqServer
func TestAsynqServerInitialization(t *testing.T) {
	jobRepo := newMockJobRepo()
	eventBus := events.GetEventBus()

	cfg := queue.AsynqServerConfig{
		RedisURL:    "redis://:dummy_pass@127.0.0.1:6379/2",
		Concurrency: 3,
		WorkersPath: "/app/backend/workers",
	}

	server := queue.NewAsynqServer(cfg, jobRepo, eventBus)
	require.NotNil(t, server, "AsynqServer should be initialized successfully")
}
