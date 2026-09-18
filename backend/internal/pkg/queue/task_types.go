package queue

import (
	"encoding/json"
	"fmt"
	"time"

	"github.com/google/uuid"
)

// ---------------------------------------------------------------------------
// Task type constants
// ---------------------------------------------------------------------------

const (
	// Reconstruction pipeline stages — each maps to a distinct Asynq queue task
	TypePreprocessVideo     = "vastu:reconstruction:preprocess_video"
	TypeRunSFM              = "vastu:reconstruction:run_sfm"
	TypeRunDepthEstimation  = "vastu:reconstruction:run_depth_estimation"
	TypeFusePointCloud      = "vastu:reconstruction:fuse_point_cloud"
	TypeRunMeshReconstruction = "vastu:reconstruction:run_mesh_reconstruction"
	TypeRunTexturing          = "vastu:reconstruction:run_texturing"
	TypeRunSemanticSegmentation = "vastu:reconstruction:run_semantic_segmentation"
	TypeRunQualityAssurance = "vastu:reconstruction:run_quality_assurance"
	TypeFinalizeModel       = "vastu:reconstruction:finalize_model"

	// Standalone tasks
	TypeSendNotification  = "vastu:notification:send"
	TypeCleanupExpiredUploads = "vastu:maintenance:cleanup_expired_uploads"
)

// ---------------------------------------------------------------------------
// Queue priority names (mapped to Asynq queue priorities in asynq_server.go)
// ---------------------------------------------------------------------------

const (
	QueueCritical = "critical" // Real-time: notification, auth, upload-complete hooks
	QueueDefault  = "default"  // Normal reconstruction pipeline tasks
	QueueLow      = "low"      // Maintenance, cleanup, analytics
)

// ---------------------------------------------------------------------------
// Task payload structs
// ---------------------------------------------------------------------------

// ReconstructionPayload is the shared payload for all reconstruction pipeline tasks.
// Each stage reads the same payload and writes its output to the shared job paths.
type ReconstructionPayload struct {
	JobID      uuid.UUID  `json:"job_id"`
	ProjectID  uuid.UUID  `json:"project_id"`
	CaptureID  *uuid.UUID `json:"capture_id,omitempty"`
	VideoURL   string     `json:"video_url"`
	IMUURL     string     `json:"imu_url"`
	LiDARURL   string     `json:"lidar_url,omitempty"`
	WorkDir    string     `json:"work_dir"`  // scratch path for intermediate outputs
	Priority   int        `json:"priority"`
	RetryCount int        `json:"retry_count"` // incremented by Asynq automatically
}

func (p *ReconstructionPayload) Encode() ([]byte, error) {
	return json.Marshal(p)
}

func DecodeReconstructionPayload(data []byte) (*ReconstructionPayload, error) {
	var p ReconstructionPayload
	if err := json.Unmarshal(data, &p); err != nil {
		return nil, fmt.Errorf("queue: failed to decode ReconstructionPayload: %w", err)
	}
	return &p, nil
}

// NotificationPayload carries data for user notification tasks.
type NotificationPayload struct {
	UserID    uuid.UUID `json:"user_id"`
	EventType string    `json:"event_type"`
	Title     string    `json:"title"`
	Body      string    `json:"body"`
	DeepLink  string    `json:"deep_link,omitempty"`
}

func (p *NotificationPayload) Encode() ([]byte, error) {
	return json.Marshal(p)
}

func DecodeNotificationPayload(data []byte) (*NotificationPayload, error) {
	var p NotificationPayload
	if err := json.Unmarshal(data, &p); err != nil {
		return nil, fmt.Errorf("queue: failed to decode NotificationPayload: %w", err)
	}
	return &p, nil
}

// CleanupPayload carries parameters for periodic maintenance tasks.
type CleanupPayload struct {
	OlderThan time.Duration `json:"older_than"`
	DryRun    bool          `json:"dry_run"`
}

func (p *CleanupPayload) Encode() ([]byte, error) {
	return json.Marshal(p)
}
