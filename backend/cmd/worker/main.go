package main

import (
	"context"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"vastu/backend/internal/config"
	"vastu/backend/internal/pkg/events"
	"vastu/backend/internal/pkg/queue"
	"vastu/backend/internal/repository/postgres"
)

func main() {
	log.Println("=====================================================")
	log.Println("  VĀSTU Reconstruction Worker Daemon Initializing    ")
	log.Println("=====================================================")

	cfg := config.LoadConfig()

	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()

	// 1. Establish PostgreSQL database connection pool
	pool, err := postgres.NewDBPool(ctx, cfg.DatabaseURL)
	if err != nil {
		log.Fatalf("[Worker] Fatal: Failed to connect to PostgreSQL: %v", err)
	}
	defer pool.Close()
	log.Println("[Worker] ✓ Connected to PostgreSQL database")

	// 2. Initialize Repositories
	jobRepo := postgres.NewJobRepo(pool)

	// 3. Initialize Shared Event Bus
	eventBus := events.GetEventBus()

	// 4. Configure Asynq Worker Server
	serverCfg := queue.AsynqServerConfig{
		RedisURL:      cfg.RedisURL,
		RedisPassword: cfg.RedisPassword,
		Concurrency:   cfg.WorkerConcurrency,
		WorkersPath:   cfg.WorkersPath,
	}

	log.Printf("[Worker] Starting Asynq Server (WorkersPath=%s, Concurrency=%d)...", cfg.WorkersPath, cfg.WorkerConcurrency)
	asynqServer := queue.NewAsynqServer(serverCfg, jobRepo, eventBus)

	// 5. Start Server in separate goroutine
	errChan := make(chan error, 1)
	go func() {
		if err := asynqServer.Start(); err != nil {
			errChan <- err
		}
	}()
	log.Println("[Worker] ✓ Asynq Reconstruction Worker listening for processing tasks")

	// 6. Graceful Termination on OS Signal
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)

	select {
	case sig := <-sigChan:
		log.Printf("[Worker] Received signal %v, shutting down gracefully...", sig)
		asynqServer.Stop()
		log.Println("[Worker] Server stopped cleanly")
	case err := <-errChan:
		log.Fatalf("[Worker] Fatal: Asynq server terminated unexpectedly: %v", err)
	}
}
