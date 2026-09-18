package domain

import (
	"time"

	"github.com/google/uuid"
)

type JobStage string

const (
	JobStageQueued               JobStage = "queued"
	JobStagePreprocessing        JobStage = "preprocessing"
	JobStageTracking             JobStage = "tracking"
	JobStageSfMTracking          JobStage = "sfm_tracking"
	JobStageDepthEstimation      JobStage = "depth_estimation"
	JobStagePointCloud           JobStage = "point_cloud"
	JobStageMeshing              JobStage = "meshing"
	JobStageTexturing            JobStage = "texturing"
	JobStageSemanticSegmentation JobStage = "semantic_segmentation"
	JobStageCellFusion           JobStage = "cell_fusion"
	JobStageQuality              JobStage = "quality"
	JobStageCompleted            JobStage = "completed"
	JobStageFailed               JobStage = "failed"
)

type ProcessingJob struct {
	ID                 uuid.UUID              `json:"id"`
	ProjectID          uuid.UUID              `json:"project_id"`
	CaptureID          *uuid.UUID             `json:"capture_id,omitempty"`
	Stage              JobStage               `json:"stage"`
	ProgressPercentage int                    `json:"progress_percentage"`
	Priority           int                    `json:"priority"`
	WorkerNodeID       *string                `json:"worker_node_id,omitempty"`
	ErrorCode          *string                `json:"error_code,omitempty"`
	ErrorMessage       *string                `json:"error_message,omitempty"`
	StageDurations     map[string]interface{} `json:"stage_durations"`
	StartedAt          *time.Time             `json:"started_at,omitempty"`
	CompletedAt        *time.Time             `json:"completed_at,omitempty"`
	CreatedAt          time.Time              `json:"created_at"`
	UpdatedAt          time.Time              `json:"updated_at"`
}

type JobLog struct {
	ID        uuid.UUID              `json:"id"`
	JobID     uuid.UUID              `json:"job_id"`
	Stage     string                 `json:"stage"`
	LogLevel  string                 `json:"log_level"` // 'debug', 'info', 'warn', 'error'
	Message   string                 `json:"message"`
	Meta      map[string]interface{} `json:"meta,omitempty"`
	CreatedAt time.Time              `json:"created_at"`
}

type CreateJobInput struct {
	ProjectID uuid.UUID  `json:"project_id"`
	CaptureID *uuid.UUID `json:"capture_id,omitempty"`
	Priority  *int       `json:"priority,omitempty"`
}

type UpdateJobProgressInput struct {
	Stage              JobStage `json:"stage"`
	ProgressPercentage int      `json:"progress_percentage"`
	WorkerNodeID       *string  `json:"worker_node_id,omitempty"`
	ErrorCode          *string  `json:"error_code,omitempty"`
	ErrorMessage       *string  `json:"error_message,omitempty"`
}
