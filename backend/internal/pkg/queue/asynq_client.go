package queue

import (
	"context"
	"fmt"
	"time"

	"github.com/hibiken/asynq"
	"github.com/google/uuid"
)

// AsynqClient wraps the Asynq client for enqueuing reconstruction and
// maintenance tasks with configurable retry policies, deadlines, and queues.
type AsynqClient struct {
	client *asynq.Client
}

// NewAsynqClient creates an AsynqClient connected to the given Redis address.
// redisAddr example: "localhost:6379" or "vastu-redis:6379" (docker-compose service name).
func NewAsynqClient(redisAddr string) *AsynqClient {
	return &AsynqClient{
		client: asynq.NewClient(asynq.RedisClientOpt{Addr: redisAddr}),
	}
}

// Close closes the underlying Asynq client connection.
func (c *AsynqClient) Close() error {
	return c.client.Close()
}

// EnqueueReconstructionJob enqueues the full reconstruction pipeline starting
// from the preprocessing stage. Subsequent stages are chained by the handler
// (each stage handler enqueues the next stage on success).
//
// Options:
//   - MaxRetry: 3 (Asynq handles exponential backoff automatically)
//   - Timeout: 4 hours (long reconstruction jobs may take 30-90 min)
//   - Deadline: configurable per-job priority
//   - Queue: QueueDefault for normal priority, QueueCritical for P1
func (c *AsynqClient) EnqueueReconstructionJob(
	ctx context.Context,
	payload *ReconstructionPayload,
) (*asynq.TaskInfo, error) {
	data, err := payload.Encode()
	if err != nil {
		return nil, fmt.Errorf("AsynqClient.EnqueueReconstructionJob: encode failed: %w", err)
	}

	queue := QueueDefault
	if payload.Priority >= 8 {
		queue = QueueCritical
	}

	task := asynq.NewTask(TypePreprocessVideo, data)
	info, err := c.client.EnqueueContext(ctx, task,
		asynq.Queue(queue),
		asynq.MaxRetry(3),
		asynq.Timeout(4*time.Hour),
		asynq.TaskID(fmt.Sprintf("reconstruct:%s", payload.JobID.String())),
		asynq.Unique(30*time.Minute), // Deduplicate: same job ID won't be enqueued twice within 30 min
	)
	if err != nil {
		// Asynq returns ErrTaskIDConflict if deduplication kicks in — not a fatal error
		if err == asynq.ErrTaskIDConflict {
			return nil, fmt.Errorf("AsynqClient: reconstruction job %s already enqueued (dedup)", payload.JobID)
		}
		return nil, fmt.Errorf("AsynqClient.EnqueueReconstructionJob: enqueue failed: %w", err)
	}
	return info, nil
}

// EnqueueStage enqueues a specific pipeline stage task.
// Used by stage handlers to chain to the next stage on completion.
func (c *AsynqClient) EnqueueStage(
	ctx context.Context,
	taskType string,
	payload *ReconstructionPayload,
) (*asynq.TaskInfo, error) {
	data, err := payload.Encode()
	if err != nil {
		return nil, fmt.Errorf("AsynqClient.EnqueueStage: encode failed: %w", err)
	}
	task := asynq.NewTask(taskType, data)
	return c.client.EnqueueContext(ctx, task,
		asynq.Queue(QueueDefault),
		asynq.MaxRetry(3),
		asynq.Timeout(2*time.Hour),
	)
}

// EnqueueNotification enqueues a user notification task.
func (c *AsynqClient) EnqueueNotification(
	ctx context.Context,
	payload *NotificationPayload,
) (*asynq.TaskInfo, error) {
	data, err := payload.Encode()
	if err != nil {
		return nil, err
	}
	task := asynq.NewTask(TypeSendNotification, data)
	return c.client.EnqueueContext(ctx, task,
		asynq.Queue(QueueCritical),
		asynq.MaxRetry(5),
		asynq.Timeout(30*time.Second),
	)
}

// EnqueueCleanupExpiredUploads schedules a maintenance cleanup task.
func (c *AsynqClient) EnqueueCleanupExpiredUploads(ctx context.Context) (*asynq.TaskInfo, error) {
	payload := &CleanupPayload{OlderThan: 24 * time.Hour, DryRun: false}
	data, _ := payload.Encode()
	task := asynq.NewTask(TypeCleanupExpiredUploads, data)
	return c.client.EnqueueContext(ctx, task,
		asynq.Queue(QueueLow),
		asynq.MaxRetry(1),
		asynq.TaskID(fmt.Sprintf("cleanup:uploads:%s", uuid.New().String()[:8])),
	)
}
