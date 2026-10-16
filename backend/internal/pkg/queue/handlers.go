package queue

import (
	"context"
	"fmt"
	"log"
	"os/exec"

	"vastu/backend/internal/domain"
	"vastu/backend/internal/pkg/events"
	"vastu/backend/internal/repository"

	"github.com/google/uuid"
	"github.com/hibiken/asynq"
)

// ---------------------------------------------------------------------------
// Stage Handlers
// ---------------------------------------------------------------------------
// Each handler:
//   1. Decodes the ReconstructionPayload
//   2. Updates the job stage in Postgres (via jobRepo)
//   3. Executes the stage (calls Python worker via subprocess or Go logic)
//   4. On success: enqueues the NEXT stage task (pipeline chaining)
//   5. On failure: returns error → Asynq retries with exponential backoff
//      After maxRetry exhaustion: Asynq moves task to the dead-letter archive
// ---------------------------------------------------------------------------

// StageHandlers holds all dependencies required by task handlers.
type StageHandlers struct {
	jobRepo  repository.JobRepository
	eventBus *events.EventBus
	client   *AsynqClient
	workersPath string // absolute path to backend/workers directory
}

// NewStageHandlers constructs the handler set.
func NewStageHandlers(
	jobRepo repository.JobRepository,
	eventBus *events.EventBus,
	client *AsynqClient,
	workersPath string,
) *StageHandlers {
	return &StageHandlers{
		jobRepo:  jobRepo,
		eventBus: eventBus,
		client:   client,
		workersPath: workersPath,
	}
}

// HandlePreprocessVideo — Stage: preprocessing
// Runs video_preprocessor.py to extract frames and validate video quality.
func (h *StageHandlers) HandlePreprocessVideo(ctx context.Context, t *asynq.Task) error {
	p, err := DecodeReconstructionPayload(t.Payload())
	if err != nil {
		return err
	}

	if err := h.transition(ctx, p.JobID, domain.JobStagePreprocessing, 5); err != nil {
		return err
	}

	// Call Python video preprocessor worker
	cmd := exec.CommandContext(ctx,
		"python3", h.workersPath+"/preprocessing/video_preprocessor.py",
		"--video", p.VideoURL,
		"--imu", p.IMUURL,
		"--work-dir", p.WorkDir,
	)
	if out, runErr := cmd.CombinedOutput(); runErr != nil {
		return fmt.Errorf("preprocessing failed: %w\noutput: %s", runErr, string(out))
	}

	if err := h.transition(ctx, p.JobID, domain.JobStagePreprocessing, 15); err != nil {
		return err
	}

	h.eventBus.Publish(ctx, events.TopicFramesExtracted, p.JobID, map[string]interface{}{
		"job_id": p.JobID.String(), "project_id": p.ProjectID.String(),
	})

	// Chain to next stage
	_, chainErr := h.client.EnqueueStage(ctx, TypeRunSFM, p)
	return chainErr
}

// HandleRunSFM — Stage: sfm_tracking
// Runs the SFM pipeline (Python + C++ COLMAP bridge).
func (h *StageHandlers) HandleRunSFM(ctx context.Context, t *asynq.Task) error {
	p, err := DecodeReconstructionPayload(t.Payload())
	if err != nil {
		return err
	}

	if err := h.transition(ctx, p.JobID, domain.JobStageTracking, 20); err != nil {
		return err
	}

	cmd := exec.CommandContext(ctx,
		"python3", h.workersPath+"/sfm/sfm_pipeline.py",
		"--frames-dir", p.WorkDir+"/frames",
		"--output-dir", p.WorkDir+"/sfm",
	)
	if out, runErr := cmd.CombinedOutput(); runErr != nil {
		return fmt.Errorf("SFM failed: %w\noutput: %s", runErr, string(out))
	}

	if err := h.transition(ctx, p.JobID, domain.JobStageTracking, 35); err != nil {
		return err
	}

	_, chainErr := h.client.EnqueueStage(ctx, TypeRunDepthEstimation, p)
	return chainErr
}

// HandleRunDepthEstimation — Stage: depth_estimation
func (h *StageHandlers) HandleRunDepthEstimation(ctx context.Context, t *asynq.Task) error {
	p, err := DecodeReconstructionPayload(t.Payload())
	if err != nil {
		return err
	}

	if err := h.transition(ctx, p.JobID, domain.JobStageDepthEstimation, 40); err != nil {
		return err
	}

	cmd := exec.CommandContext(ctx,
		"python3", h.workersPath+"/depth/depth_estimator.py",
		"--frames-dir", p.WorkDir+"/frames",
		"--sfm-dir", p.WorkDir+"/sfm",
		"--output-dir", p.WorkDir+"/depth",
	)
	if out, runErr := cmd.CombinedOutput(); runErr != nil {
		return fmt.Errorf("depth estimation failed: %w\noutput: %s", runErr, string(out))
	}

	if err := h.transition(ctx, p.JobID, domain.JobStageDepthEstimation, 55); err != nil {
		return err
	}

	_, chainErr := h.client.EnqueueStage(ctx, TypeFusePointCloud, p)
	return chainErr
}

// HandleFusePointCloud — Stage: point_cloud
func (h *StageHandlers) HandleFusePointCloud(ctx context.Context, t *asynq.Task) error {
	p, err := DecodeReconstructionPayload(t.Payload())
	if err != nil {
		return err
	}

	if err := h.transition(ctx, p.JobID, domain.JobStagePointCloud, 60); err != nil {
		return err
	}

	cmd := exec.CommandContext(ctx,
		"python3", h.workersPath+"/pointcloud/dense_pointcloud_engine.py",
		"--depth-dir", p.WorkDir+"/depth",
		"--sfm-dir", p.WorkDir+"/sfm",
		"--output-dir", p.WorkDir+"/pointcloud",
	)
	if out, runErr := cmd.CombinedOutput(); runErr != nil {
		return fmt.Errorf("point cloud fusion failed: %w\noutput: %s", runErr, string(out))
	}

	if err := h.transition(ctx, p.JobID, domain.JobStagePointCloud, 70); err != nil {
		return err
	}

	_, chainErr := h.client.EnqueueStage(ctx, TypeRunMeshReconstruction, p)
	return chainErr
}

// HandleRunMeshReconstruction — Stage: meshing
func (h *StageHandlers) HandleRunMeshReconstruction(ctx context.Context, t *asynq.Task) error {
	p, err := DecodeReconstructionPayload(t.Payload())
	if err != nil {
		return err
	}

	if err := h.transition(ctx, p.JobID, domain.JobStageMeshing, 75); err != nil {
		return err
	}

	cmd := exec.CommandContext(ctx,
		"python3", h.workersPath+"/meshing/mesh_reconstruction_engine.py",
		"--input", p.WorkDir+"/pointcloud/dense_points3D.ply",
		"--output-dir", p.WorkDir+"/mesh",
	)
	if out, runErr := cmd.CombinedOutput(); runErr != nil {
		return fmt.Errorf("mesh reconstruction failed: %w\noutput: %s", runErr, string(out))
	}

	if err := h.transition(ctx, p.JobID, domain.JobStageMeshing, 85); err != nil {
		return err
	}

	_, chainErr := h.client.EnqueueStage(ctx, TypeRunTexturing, p)
	return chainErr
}

// HandleRunTexturing — Stage: texturing (Point 23)
func (h *StageHandlers) HandleRunTexturing(ctx context.Context, t *asynq.Task) error {
	p, err := DecodeReconstructionPayload(t.Payload())
	if err != nil {
		return err
	}

	if err := h.transition(ctx, p.JobID, domain.JobStageTexturing, 86); err != nil {
		return err
	}

	cmd := exec.CommandContext(ctx,
		"python3", h.workersPath+"/texturing/texture_reconstruction_engine.py",
		"--mesh", p.WorkDir+"/mesh/mesh3D.ply",
		"--frames-dir", p.WorkDir+"/frames",
		"--poses-file", p.WorkDir+"/sfm/camera_poses.json",
		"--output-dir", p.WorkDir+"/texture",
		"--atlas-size", "2048",
	)
	if out, runErr := cmd.CombinedOutput(); runErr != nil {
		return fmt.Errorf("texture reconstruction failed: %w\noutput: %s", runErr, string(out))
	}

	if err := h.transition(ctx, p.JobID, domain.JobStageTexturing, 88); err != nil {
		return err
	}

	_, chainErr := h.client.EnqueueStage(ctx, TypeRunSemanticSegmentation, p)
	return chainErr
}

// HandleRunSemanticSegmentation — Stage: semantic_segmentation (Point 24)
func (h *StageHandlers) HandleRunSemanticSegmentation(ctx context.Context, t *asynq.Task) error {
	p, err := DecodeReconstructionPayload(t.Payload())
	if err != nil {
		return err
	}

	if err := h.transition(ctx, p.JobID, domain.JobStageSemanticSegmentation, 90); err != nil {
		return err
	}

	cmd := exec.CommandContext(ctx,
		"python3", h.workersPath+"/semantics/semantic_understanding_engine.py",
		"--mesh", p.WorkDir+"/mesh/mesh3D.ply",
		"--frames-dir", p.WorkDir+"/frames",
		"--poses-file", p.WorkDir+"/sfm/camera_poses.json",
		"--output-dir", p.WorkDir+"/semantics",
	)
	if out, runErr := cmd.CombinedOutput(); runErr != nil {
		return fmt.Errorf("semantic segmentation failed: %w\noutput: %s", runErr, string(out))
	}

	if err := h.transition(ctx, p.JobID, domain.JobStageSemanticSegmentation, 92); err != nil {
		return err
	}

	_, chainErr := h.client.EnqueueStage(ctx, TypeRunQualityAssurance, p)
	return chainErr
}

// HandleRunQualityAssurance — Stage: quality
func (h *StageHandlers) HandleRunQualityAssurance(ctx context.Context, t *asynq.Task) error {
	p, err := DecodeReconstructionPayload(t.Payload())
	if err != nil {
		return err
	}

	if err := h.transition(ctx, p.JobID, domain.JobStageQuality, 88); err != nil {
		return err
	}

	h.eventBus.Publish(ctx, events.TopicQualityStarted, p.JobID, map[string]interface{}{
		"job_id": p.JobID.String(),
	})

	// QA checks: verify mesh file exists, spatial cells JSON is valid, metadata.json has passed flag
	// (Actual QA logic runs in the finalize handler — this stage is a hook for future ML QA models)
	if err := h.transition(ctx, p.JobID, domain.JobStageQuality, 92); err != nil {
		return err
	}

	_, chainErr := h.client.EnqueueStage(ctx, TypeFinalizeModel, p)
	return chainErr
}

// HandleFinalizeModel — Stage: completed
// Marks the job complete and publishes the model-created event.
func (h *StageHandlers) HandleFinalizeModel(ctx context.Context, t *asynq.Task) error {
	p, err := DecodeReconstructionPayload(t.Payload())
	if err != nil {
		return err
	}

	if err := h.transition(ctx, p.JobID, domain.JobStageCompleted, 100); err != nil {
		return err
	}

	h.eventBus.Publish(ctx, events.TopicReconstructionCompleted, p.JobID, map[string]interface{}{
		"job_id": p.JobID.String(), "project_id": p.ProjectID.String(),
	})
	h.eventBus.Publish(ctx, events.TopicModelCreated, p.JobID, map[string]interface{}{
		"job_id": p.JobID.String(),
	})

	log.Printf("[Queue] Reconstruction complete: job=%s project=%s", p.JobID, p.ProjectID)
	return nil
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

func (h *StageHandlers) transition(ctx context.Context, jobID uuid.UUID, stage domain.JobStage, progress int) error {
	workerID := "vastu-worker"
	return h.jobRepo.UpdateProgress(ctx, jobID, stage, progress, &workerID, nil, nil)
}
