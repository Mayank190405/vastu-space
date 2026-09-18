package queue

import (
	"context"
	"log"

	"vastu/backend/internal/pkg/events"
	"vastu/backend/internal/repository"

	"github.com/hibiken/asynq"
)

// AsynqServerConfig configures the Asynq worker server.
type AsynqServerConfig struct {
	RedisAddr   string
	Concurrency int    // number of concurrent workers (default: 10)
	WorkersPath string // absolute path to backend/workers Python scripts
}

// AsynqServer wraps an asynq.Server with VĀSTU-specific task registration.
type AsynqServer struct {
	server   *asynq.Server
	mux      *asynq.ServeMux
	handlers *StageHandlers
}

// NewAsynqServer creates and configures the Asynq worker server with all
// reconstruction pipeline task handlers registered.
//
// Queue priorities:
//   critical: 6 — user-facing notifications, upload completion hooks
//   default:  3 — reconstruction pipeline stages
//   low:      1 — maintenance and cleanup
func NewAsynqServer(
	cfg AsynqServerConfig,
	jobRepo repository.JobRepository,
	eventBus *events.EventBus,
) *AsynqServer {
	if cfg.Concurrency == 0 {
		cfg.Concurrency = 10
	}

	srv := asynq.NewServer(
		asynq.RedisClientOpt{Addr: cfg.RedisAddr},
		asynq.Config{
			Concurrency: cfg.Concurrency,
			Queues: map[string]int{
				QueueCritical: 6,
				QueueDefault:  3,
				QueueLow:      1,
			},
			// Asynq's built-in retry scheduler handles exponential backoff.
			// Max retries are set per-task in the client (default: 3).
			ErrorHandler: asynq.ErrorHandlerFunc(func(ctx context.Context, task *asynq.Task, err error) {
				log.Printf("[AsynqServer] Task %q failed: %v", task.Type(), err)
			}),
		},
	)

	client := NewAsynqClient(cfg.RedisAddr)
	handlers := NewStageHandlers(jobRepo, eventBus, client, cfg.WorkersPath)

	mux := asynq.NewServeMux()

	// Register all reconstruction pipeline stage handlers
	mux.HandleFunc(TypePreprocessVideo,       handlers.HandlePreprocessVideo)
	mux.HandleFunc(TypeRunSFM,               handlers.HandleRunSFM)
	mux.HandleFunc(TypeRunDepthEstimation,   handlers.HandleRunDepthEstimation)
	mux.HandleFunc(TypeFusePointCloud,       handlers.HandleFusePointCloud)
	mux.HandleFunc(TypeRunMeshReconstruction, handlers.HandleRunMeshReconstruction)
	mux.HandleFunc(TypeRunTexturing,              handlers.HandleRunTexturing)
	mux.HandleFunc(TypeRunSemanticSegmentation,   handlers.HandleRunSemanticSegmentation)
	mux.HandleFunc(TypeRunQualityAssurance,       handlers.HandleRunQualityAssurance)
	mux.HandleFunc(TypeFinalizeModel,        handlers.HandleFinalizeModel)

	return &AsynqServer{
		server:   srv,
		mux:      mux,
		handlers: handlers,
	}
}

// Start launches the Asynq worker server. Blocks until the context is cancelled.
// Call in a separate goroutine.
func (s *AsynqServer) Start() error {
	log.Println("[AsynqServer] Starting VĀSTU reconstruction worker...")
	return s.server.Run(s.mux)
}

// Stop gracefully shuts down the server, waiting for in-flight tasks to complete.
func (s *AsynqServer) Stop() {
	s.server.Shutdown()
	log.Println("[AsynqServer] Gracefully stopped")
}
