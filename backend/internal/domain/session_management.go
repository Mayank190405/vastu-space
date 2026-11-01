package domain

import (
	"time"

	"github.com/google/uuid"
)

type SessionStatus string

const (
	SessionStatusCreated    SessionStatus = "CREATED"
	SessionStatusAuthorized SessionStatus = "AUTHORIZED"
	SessionStatusRecording  SessionStatus = "RECORDING"
	SessionStatusUploading  SessionStatus = "UPLOADING"
	SessionStatusCompleted  SessionStatus = "COMPLETED"
	SessionStatusExpired    SessionStatus = "EXPIRED"
	SessionStatusRevoked    SessionStatus = "REVOKED"
)

type DeviceStatus string

const (
	DeviceStatusOnline    DeviceStatus = "ONLINE"
	DeviceStatusOffline   DeviceStatus = "OFFLINE"
	DeviceStatusRecording DeviceStatus = "RECORDING"
	DeviceStatusUploading DeviceStatus = "UPLOADING"
)

type StageExecutionStatus string

const (
	StageStatusPending   StageExecutionStatus = "PENDING"
	StageStatusRunning   StageExecutionStatus = "RUNNING"
	StageStatusCompleted StageExecutionStatus = "COMPLETED"
	StageStatusFailed    StageExecutionStatus = "FAILED"
	StageStatusRetrying  StageExecutionStatus = "RETRYING"
	StageStatusCancelled StageExecutionStatus = "CANCELLED"
	StageStatusSkipped   StageExecutionStatus = "SKIPPED"
)

// Standard 18-stage linear sequence for VĀSTU mobile & cloud reconstruction
var StandardPipelineStages = []string{
	"PROJECT_CREATED",
	"ROOM_CREATED",
	"QR_SESSION_GENERATED",
	"DEVICE_CONNECTED",
	"SESSION_AUTHORIZED",
	"ARKIT_CAPTURE_RUNNING",
	"LOCAL_AI_ANALYSIS",
	"CAPTURE_VALIDATION",
	"UPLOADING",
	"UPLOAD_VERIFIED",
	"RECONSTRUCTION_00",
	"RECONSTRUCTION_01",
	"RECONSTRUCTION_02",
	"RECONSTRUCTION_03",
	"RECONSTRUCTION_04",
	"RECONSTRUCTION_05",
	"RECONSTRUCTION_06",
	"RECONSTRUCTION_07",
	"RECONSTRUCTION_08",
	"RECONSTRUCTION_09",
	"RECONSTRUCTION_10",
	"RECONSTRUCTION_11",
	"RECONSTRUCTION_12",
	"RECONSTRUCTION_13",
	"RECONSTRUCTION_14",
	"RECONSTRUCTION_15",
	"RECONSTRUCTION_16",
	"RECONSTRUCTION_17",
	"RECONSTRUCTION_18",
	"RECONSTRUCTION_19",
	"RECONSTRUCTION_20",
	"RECONSTRUCTION_21",
	"RECONSTRUCTION_22",
	"RECONSTRUCTION_23",
	"RECONSTRUCTION_24",
	"VIEWER_PUBLISHING",
	"COMPLETED",
}

type CaptureSession struct {
	CaptureID         *uuid.UUID             `json:"capture_id,omitempty"`
	UploadID          *uuid.UUID             `json:"upload_id,omitempty"`
	JobID             *uuid.UUID             `json:"job_id,omitempty"`
	VideoURL          *string                `json:"video_url,omitempty"`
	RawObjectKey      *string                `json:"raw_object_key,omitempty"`
	UploadVerifiedAt  *time.Time             `json:"upload_verified_at,omitempty"`
	ViewerURL         *string                `json:"viewer_url,omitempty"`
	ID                string                 `json:"id"`
	SessionCode       string                 `json:"session_code"` // e.g. #S-1042
	ProjectID         uuid.UUID              `json:"project_id"`
	ProjectName       string                 `json:"project_name"`
	FloorID           *uuid.UUID             `json:"floor_id,omitempty"`
	FloorName         string                 `json:"floor_name,omitempty"`
	RoomID            *uuid.UUID             `json:"room_id,omitempty"`
	RoomName          string                 `json:"room_name"`
	OperatorName      *string                `json:"operator_name,omitempty"`
	ChallengeToken    string                 `json:"challenge_token"`
	Nonce             string                 `json:"nonce"`
	GrantToken        *string                `json:"grant_token,omitempty"`
	DeviceID          *string                `json:"device_id,omitempty"`
	Status            SessionStatus          `json:"status"`
	QRPayload         string                 `json:"qr_payload"` // vastu:// URI format
	ExpiresAt         time.Time              `json:"expires_at"`
	RedeemedAt        *time.Time             `json:"redeemed_at,omitempty"`
	CompletedAt       *time.Time             `json:"completed_at,omitempty"`
	CapturePackageURL *string                `json:"capture_package_url,omitempty"`
	QualitySummary    map[string]interface{} `json:"quality_summary,omitempty"`
	CreatedAt         time.Time              `json:"created_at"`
	UpdatedAt         time.Time              `json:"updated_at"`
}

type CreateCaptureSessionInput struct {
	ProjectID    uuid.UUID  `json:"project_id"`
	FloorID      *uuid.UUID `json:"floor_id,omitempty"`
	RoomID       *uuid.UUID `json:"room_id,omitempty"`
	RoomName     string     `json:"room_name"`
	OperatorName *string    `json:"operator_name,omitempty"`
	TTLMinutes   int        `json:"ttl_minutes"` // Default 60 mins
}

type RedeemChallengeInput struct {
	SessionID       string `json:"session_id"`
	ChallengeToken  string `json:"challenge_token"`
	Nonce           string `json:"nonce"`
	DeviceID        string `json:"device_id"`
	DeviceModel     string `json:"device_model"`
	DeviceOS        string `json:"device_os"`
	AppVersion      string `json:"app_version"`
	ClientTimestamp string `json:"client_timestamp"`
}

type RedeemChallengeResponse struct {
	SessionID          string `json:"session_id"`
	GrantToken         string `json:"grant_token"`
	ProjectID          string `json:"project_id"`
	ProjectName        string `json:"project_name"`
	RoomID             string `json:"room_id"`
	RoomName           string `json:"room_name"`
	Status             string `json:"status"`
	MaxDurationSeconds int    `json:"max_duration_seconds"`
}

type Device struct {
	ID                  uuid.UUID    `json:"id"`
	DeviceUUID          string       `json:"device_uuid"`
	DeviceModel         string       `json:"device_model"`
	DeviceOS            string       `json:"device_os"`
	AppVersion          string       `json:"app_version"`
	BatteryLevel        float64      `json:"battery_level"` // 0.0 - 1.0 (-1.0 if not reported)
	ARKitTrackingStatus string       `json:"arkit_tracking_status"`
	LocalAIStatus       string       `json:"local_ai_status"`
	NetworkType         string       `json:"network_type"`
	CurrentSessionID    *string      `json:"current_session_id,omitempty"`
	CurrentProjectID    *uuid.UUID   `json:"current_project_id,omitempty"`
	CurrentRoomID       *uuid.UUID   `json:"current_room_id,omitempty"`
	LastHeartbeatAt     time.Time    `json:"last_heartbeat_at"`
	Status              DeviceStatus `json:"status"` // Calculated dynamically from LastHeartbeatAt
	CreatedAt           time.Time    `json:"created_at"`
	UpdatedAt           time.Time    `json:"updated_at"`
}

type DeviceHeartbeatInput struct {
	DeviceUUID          string   `json:"device_uuid"`
	DeviceModel         string   `json:"device_model"`
	DeviceOS            string   `json:"device_os"`
	AppVersion          string   `json:"app_version"`
	SessionID           *string  `json:"session_id,omitempty"`
	BatteryLevel        *float64 `json:"battery_level,omitempty"`
	ARKitTrackingStatus string   `json:"arkit_tracking_status"`
	LocalAIStatus       string   `json:"local_ai_status"`
	RecordingState      string   `json:"recording_state"` // 'IDLE', 'RECORDING', 'PAUSED', 'UPLOADING'
	NetworkType         string   `json:"network_type"`
	StorageFreeMB       int64    `json:"storage_free_mb"`
}

type PipelineStageRecord struct {
	ID                 uuid.UUID            `json:"id"`
	SessionID          string               `json:"session_id"`
	JobID              *uuid.UUID           `json:"job_id,omitempty"`
	StageName          string               `json:"stage_name"`
	StageOrder         int                  `json:"stage_order"`
	Status             StageExecutionStatus `json:"status"`
	ProgressPercentage int                  `json:"progress_percentage"`
	ResponsibleWorker  string               `json:"responsible_worker"`
	ErrorDetails       *string              `json:"error_details,omitempty"`
	RetryCount         int                  `json:"retry_count"`
	StartedAt          *time.Time           `json:"started_at,omitempty"`
	CompletedAt        *time.Time           `json:"completed_at,omitempty"`
	UpdatedAt          time.Time            `json:"updated_at"`
}

type UpdatePipelineStageInput struct {
	Status             StageExecutionStatus   `json:"status"`
	ProgressPercentage *int                   `json:"progress_percentage,omitempty"`
	ResponsibleWorker  *string                `json:"responsible_worker,omitempty"`
	ErrorDetails       *string                `json:"error_details,omitempty"`
	Payload            map[string]interface{} `json:"payload,omitempty"`
}

type PipelineEvent struct {
	ID             uuid.UUID              `json:"id"`
	SessionID      string                 `json:"session_id"`
	StageName      string                 `json:"stage_name"`
	EventType      string                 `json:"event_type"`
	SequenceNumber int64                  `json:"sequence_number"`
	Payload        map[string]interface{} `json:"payload"`
	CreatedAt      time.Time              `json:"created_at"`
}

type RoomWithHierarchy struct {
	ID                      uuid.UUID              `json:"id"`
	LevelID                 uuid.UUID              `json:"level_id"`
	LevelNumber             int                    `json:"level_number"`
	LevelName               string                 `json:"level_name"`
	ProjectID               uuid.UUID              `json:"project_id"`
	ProjectName             string                 `json:"project_name"`
	Name                    string                 `json:"name"`
	SectionType             string                 `json:"section_type"`
	AreaSqm                 float64                `json:"area_sqm"`
	CaptureStatus           string                 `json:"capture_status"` // 'UNCAPTURED', 'CAPTURING', 'CAPTURED', 'PROCESSING', 'RECONSTRUCTED'
	ProvisionalFloorplanURL *string                `json:"provisional_floorplan_url,omitempty"`
	DimensionsValidated     map[string]interface{} `json:"dimensions_validated,omitempty"`
	CoveragePercentage      float64                `json:"coverage_percentage"`
	QualityScore            float64                `json:"quality_score"`
	ActiveSessionID         *string                `json:"active_session_id,omitempty"`
	ActiveSessionCode       *string                `json:"active_session_code,omitempty"`
	LastCaptureAt           *time.Time             `json:"last_capture_at,omitempty"`
	RescanRequested         bool                   `json:"rescan_requested"`
	Viewer3DURL             *string                `json:"viewer_3d_url,omitempty"`
	CaptureAttemptsCount    int                    `json:"capture_attempts_count"`
}

type CreateRoomInput struct {
	Name        string  `json:"name"`
	SectionType string  `json:"section_type"` // 'room', 'hall', 'corridor', etc.
	AreaSqm     float64 `json:"area_sqm"`
}
